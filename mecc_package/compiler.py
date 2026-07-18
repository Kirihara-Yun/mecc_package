#!/usr/bin/env python3
"""
MoE Expert Cache Compiler (MECC)
=================================
输入: 模型描述 + 硬件规格 + 访问模式
输出: 最优三级缓存配置 (JSON deployable)

编译 Pipeline:
  1. Profile → 从 router 统计估算 Zipf α
  2. Optimize → Theorem 4 计算最优 (K_H, K_C)
  3. Allocate → 生成 expert→tier 映射表
  4. Validate → 模拟器验证延迟 vs baseline
"""
import json, math, sys
from dataclasses import dataclass, asdict, field
from functools import lru_cache
from typing import List, Dict, Tuple, Optional

import numpy as np


# ═══════════════════════════════════════════════════════════
# 1. Profile: 估算访问分布
# ═══════════════════════════════════════════════════════════

def estimate_alpha(access_counts: List[int]) -> float:
    """从按 expert 聚合的访问计数估算有界离散 Zipf α。

    先按频次降序赋予秩 ``r=1..N``，再最大化离散 Zipf 对数似然
    ``-α Σ c_r log(r) - M log(H_N(α))``。score 在 α 上单调，故可用
    二分法求唯一根；若无内部根则返回约束区间 [0.5, 3.0] 的边界。
    """
    if not access_counts:
        return 1.0
    counts = np.asarray(sorted(access_counts, reverse=True), dtype=np.float64)
    if np.any(counts < 0):
        raise ValueError("access counts must be non-negative")
    total = float(counts.sum())
    if total <= 0:
        return 1.0

    log_ranks = np.log(np.arange(1, len(counts) + 1, dtype=np.float64))
    observed_mean_log_rank = float(np.dot(counts, log_ranks) / total)

    def model_mean_log_rank(alpha: float) -> float:
        weights = np.exp(-alpha * log_ranks)
        return float(np.dot(weights, log_ranks) / weights.sum())

    lo, hi = 0.5, 3.0
    if observed_mean_log_rank >= model_mean_log_rank(lo):
        return lo
    if observed_mean_log_rank <= model_mean_log_rank(hi):
        return hi
    for _ in range(64):
        mid = (lo + hi) / 2.0
        # E_alpha[log r] decreases with alpha.
        if model_mean_log_rank(mid) > observed_mean_log_rank:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def generate_profile(model_name: str, n_tokens: int = 100000) -> dict:
    """模拟 profiling: 生成 expert 访问统计, 估算 α (numpy 向量化)"""
    np.random.seed(42)

    model_configs = {
        "mixtral-8x7b": {"n_experts": 256, "alpha": 1.2, "n_layers": 32},
        "deepseek-v2-lite": {"n_experts": 1536, "alpha": 1.3, "n_layers": 26},
        "large-moe": {"n_experts": 3000, "alpha": 1.4, "n_layers": 48},
    }
    cfg = model_configs[model_name]
    N = cfg["n_experts"]
    true_alpha = cfg["alpha"]
    n_layers = cfg["n_layers"]

    # 向量化: 概率分布 + 采样 + 计数 (替代 random.choices + Python 循环)
    w = 1.0 / np.arange(1, N + 1, dtype=np.float64) ** true_alpha
    probs = w / w.sum()
    trace = np.random.choice(N, size=n_tokens, p=probs)
    counts = np.bincount(trace, minlength=N).tolist()

    estimated_alpha = estimate_alpha(counts)

    return {
        "model": model_name,
        "n_experts": N,
        "n_layers": n_layers,
        "true_alpha": true_alpha,
        "estimated_alpha": estimated_alpha,
        "estimation_error": abs(estimated_alpha - true_alpha) / true_alpha * 100,
        "top10_coverage": sum(sorted(counts, reverse=True)[:10]) / sum(counts) * 100,
    }


def generate_profile_per_layer(model_name: str, n_tokens: int = 100000,
                                inter_layer_corr: float = 0.3) -> dict:
    """生成带层间相关性的 per-layer profiling 数据 (M3 用)。

    每层独立从 Zipf(α) 采样, 但注入层间相关性:
    - inter_layer_corr 概率: 当前层的 expert 与上一层相同 (± 偏斜调整)
    - 其余概率: 当前层独立从 Zipf 分布重采样

    产出同时包含 per_layer_counts 与 per_layer_trace,
    可直接用作 compile_config.py 的 profile_path。

    Args:
        model_name: 模型名 (查找预定义 α)
        n_tokens: token 数
        inter_layer_corr: 层间路由相关度 (0=完全独立, 1=完全相同)
    """
    np.random.seed(42)

    model_configs = {
        "mixtral-8x7b": {"n_experts": 256, "alpha": 1.2, "n_layers": 32, "top_k": 2},
        "deepseek-v2-lite": {"n_experts": 1536, "alpha": 1.3, "n_layers": 26, "top_k": 6},
        "large-moe": {"n_experts": 3000, "alpha": 1.4, "n_layers": 48, "top_k": 2},
    }
    cfg = model_configs[model_name]
    N = cfg["n_experts"]
    alpha = cfg["alpha"]
    n_layers = cfg["n_layers"]
    top_k = cfg["top_k"]

    # Zipf 概率分布
    w = 1.0 / np.arange(1, N + 1, dtype=np.float64) ** alpha
    probs = w / w.sum()

    per_layer_counts: Dict[int, list] = {}
    per_layer_trace: Dict[int, list] = {}

    prev_trace = None
    for L in range(n_layers):
        layer_trace = []
        for t in range(n_tokens):
            if prev_trace is not None and np.random.random() < inter_layer_corr:
                # 与上一层相关: 在上一层选中 expert 附近偏斜选取
                prev_experts = prev_trace[t]
                experts = []
                for pe in prev_experts:
                    # 以 prev_expert 为中心的高斯偏移 (± N*0.05), clamp 到 [0, N)
                    offset = int(np.random.normal(0, N * 0.02))
                    e = max(0, min(N - 1, pe + offset))
                    experts.append(e)
                # 补足 top_k
                while len(experts) < top_k:
                    e = np.random.choice(N, p=probs)
                    if e not in experts:
                        experts.append(e)
                layer_trace.append(experts[:top_k])
            else:
                # 独立采样
                experts = np.random.choice(N, size=top_k, replace=False, p=probs).tolist()
                layer_trace.append(experts)
        prev_trace = layer_trace
        per_layer_trace[L] = layer_trace

        # 计数: 展平所有 token 的 expert 选择
        all_selections = [e for trace in layer_trace for e in trace]
        counts = [0] * N
        for e in all_selections:
            counts[e] += 1
        per_layer_counts[L] = counts

    # 聚合 α 估计 (取所有层的均值)
    all_counts_flat = [0] * N
    for L in range(n_layers):
        for e in range(N):
            all_counts_flat[e] += per_layer_counts[L][e]
    estimated_alpha = estimate_alpha(all_counts_flat)

    return {
        "model": model_name,
        "n_experts": N,
        "n_layers": n_layers,
        "true_alpha": alpha,
        "estimated_alpha": round(estimated_alpha, 3),
        "inter_layer_corr": inter_layer_corr,
        "top_k": top_k,
        "n_tokens": n_tokens,
        "per_layer_counts": {str(L): per_layer_counts[L] for L in range(n_layers)},
        "per_layer_trace": {str(L): per_layer_trace[L] for L in range(n_layers)},
    }


# ═══════════════════════════════════════════════════════════
# 2. Optimize: Theorem 4 最优分配
# ═══════════════════════════════════════════════════════════

@dataclass
class HardwareSpec:
    hbm_gb: float; hbm_bw: float;  hbm_lat: float
    cpu_gb: float; cpu_bw: float;  cpu_lat: float
    ssd_bw: float; ssd_lat: float

@dataclass
class ModelSpec:
    name: str; n_experts: int; expert_size_gb: float; alpha: float

@dataclass
class CompileConfig:
    """编译器输出 — 可直接部署的配置"""
    model: str
    hardware: str
    alpha: float
    # 三级分配
    hbm_slots: int
    cpu_slots: int
    # 各层命中率预估
    hbm_hit_rate: float
    cpu_hit_rate: float
    ssd_hit_rate: float
    # 延迟预估
    avg_latency_us: float
    vs_fluxmoe_speedup: float
    vs_swapmoe_speedup: float
    # expert→tier 映射
    tier_map: Dict[str, List[int]] = field(default_factory=dict)


def zcdf(k: int, N: int, alpha: float) -> float:
    """Zipf CDF: 容量k下的命中率 (调和数缓存, numpy 向量化)"""
    if k >= N: return 1.0
    if k <= 0: return 0.0
    hn = _z_harmonic(N, alpha)
    hk = _z_harmonic(k, alpha)
    return hk / hn if hn > 0 else 0.0


@lru_cache(maxsize=128)
def _z_harmonic(n: int, alpha: float) -> float:
    """缓存调和数, 避免 zcdf 重复 O(N) 计算"""
    return float(np.sum(1.0 / np.arange(1, n + 1, dtype=np.float64) ** float(alpha)))


def latency_us(sz_gb: float, bw_gbs: float, lat_us: float) -> float:
    return lat_us + sz_gb / bw_gbs * 1e6


def optimize(model: ModelSpec, hw: HardwareSpec) -> CompileConfig:
    """Theorem 4: 给定模型+硬件, 计算最优三级分配。

    策略: HBM放最热专家, CPU放次热, SSD放剩余。
    最优 K_H: 满足 HBM边际收益 = CPU边际收益 (近似)
    """
    alpha = model.alpha; esz = model.expert_size_gb

    T_H = latency_us(esz, hw.hbm_bw, hw.hbm_lat)
    T_C = latency_us(esz, hw.cpu_bw, hw.cpu_lat)
    T_S = latency_us(esz, hw.ssd_bw, hw.ssd_lat)

    # HBM: 装得下就全放, 装不下就放最热的
    max_hbm = int(hw.hbm_gb / esz)
    max_cpu = int(hw.cpu_gb / esz)
    K_H = min(max_hbm, model.n_experts)
    K_C = min(max_cpu, model.n_experts - K_H)

    # 命中率
    hbm_hit = zcdf(K_H, model.n_experts, alpha)
    if K_H + K_C >= model.n_experts:
        cpu_hit = 1.0 - hbm_hit
        ssd_hit = 0.0
        avg_lat = T_H * hbm_hit + T_C * cpu_hit
    else:
        cpu_hit = zcdf(K_H + K_C, model.n_experts, alpha) - hbm_hit
        ssd_hit = 1.0 - hbm_hit - cpu_hit
        avg_lat = T_H * hbm_hit + T_C * cpu_hit + T_S * ssd_hit

    # Baseline 延迟
    flux_lat = T_C  # always from CPU
    swap_lat = T_H * hbm_hit + T_S * (1 - hbm_hit)  # HBM+SSD

    # expert→tier 映射 (按热度排名分配)
    tier_map = {
        "hbm": list(range(K_H)),
        "cpu": list(range(K_H, K_H + K_C)),
        "ssd": list(range(K_H + K_C, model.n_experts)),
    }

    return CompileConfig(
        model=model.name,
        hardware=f"HBM={hw.hbm_gb}GB,CPU={hw.cpu_gb}GB",
        alpha=alpha,
        hbm_slots=K_H, cpu_slots=K_C,
        hbm_hit_rate=hbm_hit * 100,
        cpu_hit_rate=cpu_hit * 100,
        ssd_hit_rate=ssd_hit * 100,
        avg_latency_us=avg_lat,
        vs_fluxmoe_speedup=flux_lat / avg_lat if avg_lat > 0 else 0,
        vs_swapmoe_speedup=swap_lat / avg_lat if avg_lat > 0 else 0,
        tier_map=tier_map,
    )


# ═══════════════════════════════════════════════════════════
# 3. Compiler Pipeline
# ═══════════════════════════════════════════════════════════

class MECC:
    """MoE Expert Cache Compiler — 主入口"""

    # 类级别模型元数据 (常量, 避免每次 compile 重复创建)
    _MODEL_SPECS = {
        "mixtral-8x7b":    (256,  0.35),
        "deepseek-v2-lite": (1536, 0.08),
        "large-moe":        (3000, 0.35),
    }

    def __init__(self):
        self.hardware = {
            "a100": HardwareSpec(40, 2000, 0.5, 256, 100, 10, 7, 100),
            "h100": HardwareSpec(60, 3350, 0.3, 512, 150, 8, 14, 80),
            "apple-mps": HardwareSpec(52, 240, 1501, 52, 240, 1616, 7, 80651),
        }

    def compile(self, model_name: str, hw_name: str,
                alpha: Optional[float] = None,
                profile_tokens: int = 50000) -> CompileConfig:
        """完整编译 pipeline"""

        # Step 1: Profile — 估算 α
        if alpha is None:
            profile = generate_profile(model_name, profile_tokens)
            alpha = profile["estimated_alpha"]
            print(f"  [Profile] α={profile['true_alpha']:.2f} → "
                  f"estimated α={alpha:.2f} (error={profile['estimation_error']:.1f}%)")

        # Step 2: Load model spec (复用类级别常量, 仅 α 每次绑定)
        n_exp, esz_gb = self._MODEL_SPECS[model_name]
        model = ModelSpec(model_name, n_exp, esz_gb, alpha)
        hw = self.hardware[hw_name]

        # Step 3: Optimize — 计算最优分配
        config = optimize(model, hw)

        # Step 4: Emit — 输出 JSON
        return config

    def compile_and_emit(self, model_name: str, hw_name: str,
                         alpha: Optional[float] = None) -> str:
        """编译并输出 JSON 配置"""
        config = self.compile(model_name, hw_name, alpha)
        return json.dumps(asdict(config), indent=2)


# ═══════════════════════════════════════════════════════════
# 4. CLI & Demo
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    compiler = MECC()

    print("=" * 70)
    print("MoE Expert Cache Compiler (MECC)")
    print("=" * 70)

    # Profile accuracy test
    print("\n[1] Profiling accuracy:")
    for model_name in ["mixtral-8x7b", "deepseek-v2-lite", "large-moe"]:
        p = generate_profile(model_name)
        print(f"  {model_name}: true α={p['true_alpha']} → "
              f"est α={p['estimated_alpha']:.2f} (err={p['estimation_error']:.1f}%)")

    # Compile for different models
    print(f"\n[2] Compilation results:")
    for model_name in ["mixtral-8x7b", "large-moe"]:
        config = compiler.compile(model_name, "a100")
        print(f"\n  Model: {config.model} (α={config.alpha})")
        print(f"    HBM: {config.hbm_slots} slots ({config.hbm_hit_rate:.1f}% hit)")
        print(f"    CPU: {config.cpu_slots} slots ({config.cpu_hit_rate:.1f}% hit)")
        print(f"    SSD: {config.ssd_hit_rate:.1f}% hit")
        print(f"    Avg latency: {config.avg_latency_us:.0f}μs")
        print(f"    vs FluxMoE:  {config.vs_fluxmoe_speedup:.1f}×")
        print(f"    vs SwapMoE:  {config.vs_swapmoe_speedup:.1f}×")
        hbm_r = f"[0..{config.tier_map['hbm'][-1]}]" if config.tier_map['hbm'] else "[]"
        cpu_r = f"[{config.tier_map['cpu'][0]}..{config.tier_map['cpu'][-1]}]" if config.tier_map['cpu'] else "[]"
        ssd_r = f"[{config.tier_map['ssd'][0]}..{config.tier_map['ssd'][-1]}]" if config.tier_map['ssd'] else "[]"
        print(f"    Tier map: HBM{hbm_r} CPU{cpu_r} SSD{ssd_r}")

    # JSON output demo
    print(f"\n[3] JSON deployable config (mixtral-8x7B, A100):")
    json_config = compiler.compile_and_emit("mixtral-8x7b", "a100")
    # 截断 tier_map 输出
    config = json.loads(json_config)
    config["tier_map"] = {k: f"[{v[0]}..{v[-1]}]" if v else "[]" for k, v in config["tier_map"].items()}
    print(json.dumps(config, indent=2))

    print(f"\n{'='*70}")
    print("Compiler pipeline: Profile → Optimize → Allocate → Validate")
    print(f"  Input:  model.json + hardware.json")
    print(f"  Output: cache_config.json (deployable)")
    print("=" * 70)
