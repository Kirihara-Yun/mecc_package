#!/usr/bin/env python3
"""
MECC Runtime Specification
===========================
Compiler 输出 JSON → Runtime 加载配置 → 管理三级 Expert 缓存。

本文件是 Runtime API 的**规范 + 伪代码**, 不依赖 GPU — 在 CPU 上演示完整的 runtime 逻辑。
GPU 实现只需将 transfer_* 函数替换为 cudaMemcpy / NCCL 调用。
"""
import json, time, heapq
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ═══════════════════════════════════════════════════════════
# Runtime Config (Compiler 输出)
# ═══════════════════════════════════════════════════════════

@dataclass
class RuntimeConfig:
    """Compiler 输出的 JSON → Runtime 反序列化此结构"""
    hbm_slots: int
    cpu_slots: int
    tier_map: Dict[str, List[int]]  # {"hbm": [0..113], "cpu": [114..844], ...}
    alpha: float
    # 延迟参数 (μs)
    hbm_latency_us: float = 176
    cpu_latency_us: float = 3510
    ssd_latency_us: float = 50100

    @classmethod
    def from_compiler_json(cls, path: str) -> "RuntimeConfig":
        """Runtime 启动时加载 compiler 输出的 JSON"""
        with open(path) as f:
            data = json.load(f)
        return cls(
            hbm_slots=data["hbm_slots"],
            cpu_slots=data["cpu_slots"],
            tier_map={k: list(range(v[0], v[-1]+1)) if isinstance(v, list) and v else []
                      for k, v in data["tier_map"].items()},
            alpha=data["alpha"],
        )


# ═══════════════════════════════════════════════════════════
# GPU Runtime: ExpertCacheManager
# ═══════════════════════════════════════════════════════════

class ExpertCacheManager:
    """Runtime 核心: 管理三级 Expert 缓存。

    这是 "伪代码 API" — 每个方法标注了 GPU 实现时应调用的 CUDA 原语。
    CPU 上完整可运行 (用 dict 模拟 HBM/CPU/SSD)。

    Usage:
        cfg = RuntimeConfig.from_compiler_json("cache_config.json")
        mgr = ExpertCacheManager(cfg)
        for layer in model.layers:
            for expert_id in layer.router( hidden_states ):
                expert_weights = mgr.get_expert( expert_id )  # async transfer
            # ... compute with expert_weights ...
    """

    def __init__(self, cfg: RuntimeConfig):
        self.cfg = cfg
        self.clock = 0  # 逻辑时钟 (GPU实现: 真实时间)

        # 三级缓存
        self.hbm: OrderedDict = OrderedDict()  # expert_id → weights (GPU实现: CUDA buffer)
        self.cpu: OrderedDict = OrderedDict()  # expert_id → weights (GPU实现: pinned host memory)
        self.on_ssd = set(cfg.tier_map.get("ssd", []))  # (GPU实现: NVMe paths)

        # 统计
        self.hits = {"hbm": 0, "cpu": 0, "ssd": 0}
        self.transfers = {"cpu→hbm": 0, "ssd→cpu": 0, "hbm→cpu": 0}

        # Pre-load: 编译时确定的 HBM 层 expert
        self._preload()

    def _preload(self):
        """启动时预加载 HBM-tier expert 权重到 GPU 显存。

        GPU 实现: cudaMemcpy(host→device, expert_weights[i], HBM_buffer[i])
        对 tier_map["hbm"] 中的每个 expert, 执行一次 CPU→GPU 传输。
        """
        for eid in self.cfg.tier_map.get("hbm", []):
            self.hbm[eid] = f"expert_{eid}_weights"  # (GPU: CUDA buffer pointer)
            self.hbm.move_to_end(eid)

    def get_expert(self, expert_id: int):
        """运行时: 获取 expert 权重 (可能触发传输)。

        GPU 实现:
          if expert_id in HBM: return HBM_buffer[expert_id]
          elif expert_id in CPU: cudaMemcpyAsync(CPU→HBM); return
          else: read NVMe → CPU → cudaMemcpyAsync(CPU→HBM); return

        返回 (weights, latency_us) — 调用者可用 latency 做性能记账。
        """
        self.clock += 1

        # --- HBM hit (0.5μs lookup + 175μs read) ---
        if expert_id in self.hbm:
            self.hbm.move_to_end(expert_id)  # LRU: 移到末尾
            self.hits["hbm"] += 1
            return self.hbm[expert_id], self.cfg.hbm_latency_us

        # --- CPU hit (10μs + 3500μs PCIe transfer) ---
        if expert_id in self.cpu:
            lat = self.cfg.cpu_latency_us
            self._promote_to_hbm(expert_id)  # 提升到 HBM, 可能触发 HBM→CPU 淘汰
            self.hits["cpu"] += 1
            self.transfers["cpu→hbm"] += 1
            return self.hbm[expert_id], lat

        # --- SSD miss (100μs + 50000μs NVMe read + PCIe) ---
        lat = self.cfg.ssd_latency_us
        self._load_from_ssd(expert_id)  # SSD→CPU→HBM
        self.hits["ssd"] += 1
        self.transfers["ssd→cpu"] += 1
        self.transfers["cpu→hbm"] += 1
        return self.hbm[expert_id], lat

    def _promote_to_hbm(self, expert_id: int):
        """从 CPU 提升到 HBM, LRU 淘汰 (如果 HBM 满了)。

        GPU 实现:
          weights = cpu_buffer[expert_id]
          cudaMemcpyAsync(weights, hbm_buffer[new_slot], H2D)
          如果 HBM 满了: 淘汰 LRU → cudaMemcpyAsync(HBM→CPU, evicted)
        """
        self.cpu.pop(expert_id, None)
        self.hbm[expert_id] = f"expert_{expert_id}_weights"
        self.hbm.move_to_end(expert_id)

        # LRU eviction
        if len(self.hbm) > self.cfg.hbm_slots:
            evicted_id, evicted_weights = self.hbm.popitem(last=False)  # LRU
            self.cpu[evicted_id] = evicted_weights
            self.transfers["hbm→cpu"] += 1

            # CPU 满了 → 淘汰到 SSD
            if len(self.cpu) > self.cfg.cpu_slots:
                old_id, _ = self.cpu.popitem(last=False)
                self.on_ssd.add(old_id)

    def _load_from_ssd(self, expert_id: int):
        """从 SSD 加载 expert 权重 (SSD → CPU → HBM)。

        GPU 实现:
          1. NVMe read: read(ssd_fd, cpu_buffer, expert_size)
          2. cudaMemcpyAsync(cpu_buffer, hbm_buffer, H2D)
          3. 触发 LRU 淘汰 (同 _promote_to_hbm)
        """
        # SSD → CPU
        self.cpu[expert_id] = f"expert_{expert_id}_weights"
        self.on_ssd.discard(expert_id)
        # CPU → HBM
        self._promote_to_hbm(expert_id)

    def prefetch(self, expert_ids: List[int]):
        """预取: 提前将即将需要的 expert 从 SSD→CPU 或 CPU→HBM。

        GPU 实现: 使用独立的 CUDA stream 做异步传输, 与当前计算重叠。
        """
        for eid in expert_ids:
            if eid in self.hbm or eid in self.cpu:
                continue
            # SSD → CPU (async)
            self.cpu[eid] = f"expert_{eid}_weights"
            self.on_ssd.discard(eid)
            self.transfers["ssd→cpu"] += 1

    def stats(self) -> dict:
        """返回运行时统计"""
        total = sum(self.hits.values())
        return {
            "hbm_hit_rate": self.hits["hbm"] / total * 100 if total else 0,
            "cpu_hit_rate": self.hits["cpu"] / total * 100 if total else 0,
            "ssd_hit_rate": self.hits["ssd"] / total * 100 if total else 0,
            "total_accesses": total,
            "transfers": self.transfers,
        }


# ═══════════════════════════════════════════════════════════
# Demo: Runtime 执行编译器输出的配置
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("MECC Runtime Demo")
    print("=" * 70)

    # 1. 用编译器生成配置
    import sys; sys.path.insert(0, '.')
    from compiler import MECC
    compiler = MECC()
    config = compiler.compile("mixtral-8x7b", "a100")

    # 2. Runtime 加载配置
    cfg = RuntimeConfig(
        hbm_slots=config.hbm_slots,
        cpu_slots=config.cpu_slots,
        tier_map=config.tier_map,
        alpha=config.alpha,
    )
    mgr = ExpertCacheManager(cfg)

    print(f"\n[Config] HBM={cfg.hbm_slots}slots CPU={cfg.cpu_slots}slots")
    print(f"  Pre-loaded {len(mgr.hbm)} experts in HBM")

    # 3. 模拟 serving: 1000 次 expert 访问 (Zipf 分布)
    import random; random.seed(42)
    N = 256; alpha = 1.2
    w = [1.0 / i**alpha for i in range(1, N+1)]
    probs = [x / sum(w) for x in w]
    trace = random.choices(range(N), weights=probs, k=1000)

    total_lat = 0
    for i, eid in enumerate(trace):
        _, lat = mgr.get_expert(eid)
        total_lat += lat

    # 4. 报告
    s = mgr.stats()
    print(f"\n[Results] 1000 accesses:")
    print(f"  HBM: {s['hbm_hit_rate']:.1f}%  CPU: {s['cpu_hit_rate']:.1f}%  SSD: {s['ssd_hit_rate']:.1f}%")
    print(f"  Avg latency: {total_lat/1000:.0f}μs")
    print(f"  Transfers: {s['transfers']}")
    print(f"  vs FluxMoE(always CPU=3510μs): {3510/(total_lat/1000):.1f}×")

    print(f"\n{'='*70}")
    print("Runtime API 总结:")
    print("  get_expert(eid)    → (weights, latency) — 主接口")
    print("  prefetch([eids])   → 异步预取 (可与计算重叠)")
    print("  stats()            → 运行时统计")
    print("")
    print("GPU 实现映射:")
    print("  HBM     → cudaMalloc + cudaMemcpy(H2D) on preload")
    print("  CPU     → cudaHostAlloc (pinned memory)")
    print("  SSD     → NVMe read via io_uring / SPDK")
    print("  get_expert → cudaMemcpyAsync + CUDA stream overlap")
    print("  LRU eviction → cudaMemcpyAsync(D2H) for evicted expert")
    print("=" * 70)
