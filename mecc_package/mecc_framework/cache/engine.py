#!/usr/bin/env python3
"""
mecc_framework.cache.engine — 三级 Per-Layer Expert 缓存引擎
=============================================================
融合 mixtral-offloading 的 per-layer LRU eviction group 与 MECC 的三级缓存:
  HBM (K_H 槽) + CPU pinned (K_C 槽) + SSD (无限冷存)

四种策略 (同一引擎, policy 参数切换):
  ours    — 联合动态 LRU + 升降级 HBM↔CPU↔SSD
  swapmoe — HBM 动态 LRU + CPU 静态 + SSD
  fiddler — HBM 常驻 + miss 在 CPU 上算 (搬激活)
  naive   — 不常驻, 每次流式搬运
"""
from __future__ import annotations
from collections import OrderedDict
from typing import Dict, Iterator, List, Optional, Tuple

import torch

from ..base.config import CachePolicy, OffloadConfig, CacheBudget
from ..base.expert import ExpertWeights
from ..base.store import ExpertSSDStore
from .swap import AsyncSwapEngine

ExpertUID = Tuple[int, int]


class LayerExpertCache:
    """单层 expert 缓存: 按照 policy 管理 HBM / CPU / SSD 三个 tier。

    mixtral-offloading 的 eviction_group 概念: 每个 layer 独立 LRU,
    不同层间互不干扰 — 这与真实 offload 系统一致 (每层热的 expert 独立)。
    """

    def __init__(self,
                 layer_id: int,
                 store: ExpertSSDStore,
                 budget: CacheBudget,
                 device: torch.device,
                 config: OffloadConfig,
                 ranked_uids: Optional[List[ExpertUID]] = None):
        self.layer_id = layer_id
        self.store = store
        self.k_h = budget.k_hbm
        self.k_c = budget.k_cpu
        self.device = device
        self.policy = config.policy
        self.cold_ssd = config.cold_ssd

        # 三个 tier 的存储: 都用 OrderedDict 维护 LRU 顺序
        self.hbm: OrderedDict[ExpertUID, ExpertWeights] = OrderedDict()
        self._hbm_cpu_mirror: Dict[ExpertUID, ExpertWeights] = {}
        self.cpu: OrderedDict[ExpertUID, ExpertWeights] = OrderedDict()
        self.static_cpu: Dict[ExpertUID, ExpertWeights] = {}   # swapmoe 静态池
        self.hits = [0, 0, 0, 0]  # [hbm, cpu, ssd, cpu_compute]

        # 异步搬运引擎
        self._swap = AsyncSwapEngine(device, buffer_count=4)

        # 编译期预热: static placement
        if ranked_uids is None:
            ranked_uids = [(layer_id, e) for e in range(config.model_spec.n_experts)]
        self._warmup(ranked_uids)

    def _warmup(self, ranked_uids: List[ExpertUID]):
        """编译期静态放置: 最热 K_H 入 HBM, 次热 K_C 入 CPU。"""
        for uid in ranked_uids[:self.k_h]:
            ws = self.store.load_to_cpu(uid, cold=False)
            self.hbm[uid] = ws.to(self.device)
            self._hbm_cpu_mirror[uid] = ws
        if self.policy == CachePolicy.SWAPMOE:
            for uid in ranked_uids[self.k_h:self.k_h + self.k_c]:
                self.static_cpu[uid] = self.store.load_to_cpu(uid, cold=False).pin_memory()
        else:
            for uid in ranked_uids[self.k_h:self.k_h + self.k_c]:
                self.cpu[uid] = self.store.load_to_cpu(uid, cold=False).pin_memory()
        self._swap.sync_device()

    # ----------------------------------------------------------------
    # 公共接口: 与 mixtral-offloading SparseMoeWrapper 契约一致
    # ----------------------------------------------------------------

    def load_experts(self, *uids: ExpertUID,
                     unordered: bool = True
                     ) -> Iterator[Tuple[ExpertUID, ExpertWeights]]:
        """加载 expert 权重, 配合 MoE forward 使用。

        与 mixtral-offloading 的 load_experts 接口一致:
          for (_lid, expert_idx), expert_layer in cache.load_experts(...):
              result += expert_layer(x) * gate_weight
        """
        # 批量预取: 找出所有在 CPU 的 expert, 异步搬上 GPU
        if self.device.type == "cuda":
            cpu_miss_uids = {uid: ws for uid, ws in self._get_cpu_ws_all(uids).items()
                             if uid not in self.hbm}
            if cpu_miss_uids:
                self._swap.batch_prefetch(cpu_miss_uids)

        for uid in uids:
            ws = self._access(uid)
            yield uid, ws

        self._swap.sync_copy()

    def _get_cpu_ws_all(self, uids: Tuple[ExpertUID, ...]
                        ) -> Dict[ExpertUID, ExpertWeights]:
        """获取所有在 CPU 上的 expert (用于批量预取)。"""
        result = {}
        for uid in uids:
            if uid in self.cpu:
                result[uid] = self.cpu[uid]
            elif uid in self.static_cpu:
                result[uid] = self.static_cpu[uid]
        return result

    # ----------------------------------------------------------------
    # 策略实现
    # ----------------------------------------------------------------

    def _access(self, uid: ExpertUID) -> ExpertWeights:
        """按当前 policy 访问一个 expert。"""
        if self.policy == CachePolicy.NAIVE:
            return self._access_naive(uid)
        elif self.policy == CachePolicy.FIDDLER:
            return self._access_fiddler(uid)
        elif self.policy == CachePolicy.SWAPMOE:
            return self._access_swapmoe(uid)
        else:
            return self._access_ours(uid)

    def _access_naive(self, uid: ExpertUID) -> ExpertWeights:
        """Naive: 不常驻 HBM, 每次 streaming 搬运。"""
        if uid in self.hbm:
            self.hbm.move_to_end(uid)
            self.hits[0] += 1
            return self.hbm[uid]
        src = self.store.load_to_cpu(uid, cold=self.cold_ssd)
        self.hits[2] += 1
        return self._swap.copy_to_gpu(src)

    def _access_fiddler(self, uid: ExpertUID) -> ExpertWeights:
        """Fiddler: HBM 常驻 K_H; miss 在 CPU 上算 (搬激活而非权重)。"""
        if uid in self.hbm:
            self.hbm.move_to_end(uid)
            self.hits[0] += 1
            return self.hbm[uid]
        if uid in self.cpu:
            self.cpu.move_to_end(uid)
            self.hits[3] += 1
            return self.cpu[uid]
        src = self.store.load_to_cpu(uid, cold=self.cold_ssd)
        self.cpu[uid] = src.pin_memory()
        self.cpu.move_to_end(uid)
        self._evict_cpu_if_needed()
        self.hits[2] += 1
        return src

    def _access_swapmoe(self, uid: ExpertUID) -> ExpertWeights:
        """SwapMoE: 仅 HBM 动态 LRU; CPU 静态; 其余 SSD。"""
        if uid in self.hbm:
            self.hbm.move_to_end(uid)
            self.hits[0] += 1
            return self.hbm[uid]
        if uid in self.static_cpu:
            g = self._swap.copy_to_gpu(self.static_cpu[uid])
            self.hits[1] += 1
        else:
            g = self._swap.copy_to_gpu(
                self.store.load_to_cpu(uid, cold=self.cold_ssd))
            self.hits[2] += 1
        self.hbm[uid] = g
        self._hbm_cpu_mirror[uid] = self.static_cpu.get(uid)
        self.hbm.move_to_end(uid)
        self._evict_hbm_if_needed(spill_to_cpu=False)
        return g

    def _access_ours(self, uid: ExpertUID) -> ExpertWeights:
        """OURS: 联合动态 LRU, HBM↔CPU↔SSD 升降级。"""
        if uid in self.hbm:
            self.hbm.move_to_end(uid)
            self.hits[0] += 1
            return self.hbm[uid]
        if uid in self.cpu:
            ws_cpu = self.cpu.pop(uid)
            g = self._swap.copy_to_gpu(ws_cpu)
            self.hits[1] += 1
        else:
            ws_cpu = self.store.load_to_cpu(uid, cold=self.cold_ssd)
            g = self._swap.copy_to_gpu(ws_cpu)
            self.hits[2] += 1
        self.hbm[uid] = g
        self._hbm_cpu_mirror[uid] = ws_cpu
        self.hbm.move_to_end(uid)
        self._evict_hbm_if_needed(spill_to_cpu=True)
        return g

    # ----------------------------------------------------------------
    # LRU 淘汰
    # ----------------------------------------------------------------

    def _evict_hbm_if_needed(self, spill_to_cpu: bool):
        """HBM 满时淘汰最久未用的 expert。

        OURS keeps a CPU mirror for promoted experts, so demotion can reuse
        that read-only copy instead of copying weights back from GPU.
        """
        while len(self.hbm) > self.k_h:
            ev_uid, ev_ws = self.hbm.popitem(last=False)
            ev_cpu = self._hbm_cpu_mirror.pop(ev_uid, None)
            if spill_to_cpu and self.k_c > 0:
                self.cpu[ev_uid] = ev_cpu if ev_cpu is not None else ev_ws.to("cpu")
                self.cpu.move_to_end(ev_uid)
                self._evict_cpu_if_needed()

    def _evict_cpu_if_needed(self):
        """CPU 满时淘汰最久未用的 expert (丢引用, 数据在 SSD)。"""
        while len(self.cpu) > self.k_c:
            self.cpu.popitem(last=False)

    # ----------------------------------------------------------------
    # 统计
    # ----------------------------------------------------------------

    def hit_summary(self) -> Dict[str, float]:
        tot = sum(self.hits) or 1
        return {
            "hbm_pct": round(self.hits[0] / tot * 100, 1),
            "cpu_pct": round(self.hits[1] / tot * 100, 1),
            "ssd_pct": round(self.hits[2] / tot * 100, 1),
            "cpu_compute_pct": round(self.hits[3] / tot * 100, 1),
            "total_accesses": tot,
        }
