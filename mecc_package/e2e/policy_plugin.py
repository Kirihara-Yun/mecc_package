#!/usr/bin/env python3
"""
policy_plugin.py — MECC 缓存策略插件化
========================================
策略从 if/elif 平铺提取为独立插件类，支持动态注册。
每个插件只暴露 access() + name() + supports() 三个接口。

使用:
    from policy_plugin import get_policy

    cache = LayerExpertCache(..., policy=get_policy("ours"))
    cache._access(uid)   # → 走 OursPolicy.access()

扩展新策略:
    class MyPolicy(CachePolicy):
        name = "my_policy"
        def access(self, cache, uid): ...

    register(MyPolicy)
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Optional, Type

# 前向引用，避免循环导入
from tiered_engine import ExpertUID, ExpertWeights  # noqa: F401


class CachePolicy(ABC):
    """缓存策略基类。

    access(cache, uid) → ExpertWeights
        cache: LayerExpertCache 实例 (提供 .gpu / .cpu / .store 等)
        uid:   (layer_id, expert_idx)
    """

    name: str = "base"

    @abstractmethod
    def access(self, cache: "LayerExpertCache", uid: "ExpertUID") -> "ExpertWeights":  # type: ignore
        ...

    @classmethod
    def supports_device(cls, device_type: str) -> bool:
        return True


# ── 策略注册表 ────────────────────────────────────────────

_registry: Dict[str, Type[CachePolicy]] = {}


def register(policy_cls: Type[CachePolicy]) -> Type[CachePolicy]:
    _registry[policy_cls.name] = policy_cls
    return policy_cls


def get_policy(name: str) -> CachePolicy:
    cls = _registry.get(name)
    if cls is None:
        raise KeyError(f"Unknown policy: {name}. Registered: {list(_registry)}")
    return cls()


def list_policies() -> list:
    return list(_registry.keys())


# ── 四基线策略 ────────────────────────────────────────────

@register
class OursPolicy(CachePolicy):
    """OURS: HBM + CPU 联合动态 LRU, 带升降级 HBM→CPU→SSD"""
    name = "ours"

    def access(self, cache: "LayerExpertCache", uid) -> "ExpertWeights":
        if uid in cache.gpu:
            cache.gpu.move_to_end(uid)
            cache.hits[0] += 1
            return cache.gpu[uid][0]                     # (gpu_ws, cpu_ws) 对
        if uid in cache.cpu:
            ws_cpu = cache.cpu.pop(uid)
            g = cache._to_gpu(ws_cpu)
            cache.hits[1] += 1
        else:
            # Router-logit 预测预取: near-miss 缓冲命中 → 免冷读, 算 CPU hit
            ws_cpu = cache.consume_nearmiss(uid)
            if ws_cpu is not None:
                g = cache._to_gpu(ws_cpu)
                cache.hits[1] += 1                       # 预取命中 = CPU hit
            else:
                ws_cpu = cache.store.load_to_cpu(uid, cold=cache.cold_ssd)
                g = cache._to_gpu(ws_cpu)
                cache.hits[2] += 1
        cache.gpu[uid] = (g, ws_cpu)
        cache.gpu.move_to_end(uid)
        cache._evict_gpu_if_needed(spill_to_cpu=True)
        return g


@register
class SwapMoePolicy(CachePolicy):
    """SwapMoE: 仅 HBM 动态 LRU; CPU 静态 top-K_C; 不回写 CPU"""
    name = "swapmoe"

    def access(self, cache: "LayerExpertCache", uid) -> "ExpertWeights":
        if uid in cache.gpu:
            cache.gpu.move_to_end(uid)
            cache.hits[0] += 1
            return cache.gpu[uid][0]
        if uid in cache.static_cpu:
            g = cache._to_gpu(cache.static_cpu[uid])
            cache.hits[1] += 1
        else:
            g = cache._to_gpu(cache.store.load_to_cpu(uid, cold=cache.cold_ssd))
            cache.hits[2] += 1
        cache.gpu[uid] = (g, None)                        # swapmoe 不保留 CPU 镜像
        cache.gpu.move_to_end(uid)
        cache._evict_gpu_if_needed(spill_to_cpu=False)
        return g


@register
class FiddlerPolicy(CachePolicy):
    """Fiddler: HBM 常驻 K_H; miss 在 CPU 上算 (搬激活不搬权重)"""
    name = "fiddler"

    def access(self, cache: "LayerExpertCache", uid) -> "ExpertWeights":
        if uid in cache.gpu:
            cache.gpu.move_to_end(uid)
            cache.hits[0] += 1
            return cache.gpu[uid][0]
        if uid in cache.cpu:
            cache.cpu.move_to_end(uid)
            cache.hits[3] += 1    # cpu_compute
            return cache.cpu[uid]
        src = cache.store.load_to_cpu(uid, cold=cache.cold_ssd)
        cache.cpu[uid] = src.pin()
        cache.cpu.move_to_end(uid)
        while len(cache.cpu) > cache.k_c:
            cache.cpu.popitem(last=False)
        cache.hits[2] += 1
        return src


@register
class NaivePolicy(CachePolicy):
    """Naive: 不常驻 HBM; 每次从 SSD/CPU 流式搬运"""
    name = "naive"

    def access(self, cache: "LayerExpertCache", uid) -> "ExpertWeights":
        if uid in cache.gpu:
            cache.gpu.move_to_end(uid)
            cache.hits[0] += 1
            return cache.gpu[uid][0]
        src = cache.store.load_to_cpu(uid, cold=cache.cold_ssd)
        cache.hits[2] += 1
        return cache._to_gpu(src)


# ── ours_io: OURS + 并行 SSD I/O ────────────────────────────

@register
class OursIOPolicy(CachePolicy):
    """OURS + ThreadPool 并行 SSD I/O: prefill 阶段多路磁盘读"""
    name = "ours_io"

    def access(self, cache: "LayerExpertCache", uid) -> "ExpertWeights":
        if uid in cache.gpu:
            cache.gpu.move_to_end(uid)
            cache.hits[0] += 1
            return cache.gpu[uid]
        if uid in cache.cpu:
            ws_cpu = cache.cpu.pop(uid)
            g = cache._to_gpu(ws_cpu)
            cache.hits[1] += 1
        else:
            g = cache._to_gpu(cache._load_from_ssd(uid))
            cache.hits[2] += 1
        cache.gpu[uid] = g
        cache.gpu.move_to_end(uid)
        cache._evict_gpu_if_needed(spill_to_cpu=True)
        return g


# ── 注册预定义策略组 ──

BASELINE_POLICIES = ["ours", "swapmoe", "fiddler", "naive"]
OUR_POLICIES = ["ours", "ours_io"]
COMPETITOR_POLICIES = ["swapmoe", "fiddler", "naive"]
