#!/usr/bin/env python3
"""
compile_config.py — 编译器接入: (模型 + 硬件 + profiled α) → 每层 (K_H, K_C) + 放置表
=====================================================================================
复用上层 compiler.py 的理论 (Zipf CDF 命中率 zcdf + Theorem-4 最优分配 optimize)。
本文件把"全模型级"配置落到端到端运行需要的"每层"粒度, 并产出每层 expert 的热度排序。

输出 CompiledPlan:
  k_h      : 每层常驻 HBM 的 expert 数
  k_c      : 每层常驻 CPU 的 expert 数
  placement: {layer_id: [按热度降序的 expert id]}  (warm-up 放置依据)
  预估命中率 / 延迟 (来自编译器解析模型, 供 sanity check)

M3 扩展 (路由感知联合放置):
  新增 cooc_data 参数与 joint_ranking 函数: 若提供层间专家共现矩阵, 则放置排序
  不仅按单层热度, 还按跨层共现加分 (与上一层 HBM 驻留专家共现的专家获得 boost)。
  无共现数据时退化为纯热度排序, 向后兼容。
"""
from __future__ import annotations
import json
import math
import os
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

# 复用上一层目录的 compiler.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from compiler import zcdf  # noqa: E402


@dataclass
class CompiledPlan:
    model: str
    hardware: str
    alpha: float
    n_layers: int
    n_experts: int
    expert_mb: float
    k_h: int                             # uniform 模式用的全局 K_H (向后兼容)
    k_c: int                             # uniform 模式用的全局 K_C
    per_layer_k_h: List[int] = field(default_factory=list)  # per-layer 自适应分配
    per_layer_k_c: List[int] = field(default_factory=list)
    per_layer_alpha: List[float] = field(default_factory=list)  # 编译期 profiled
    hbm_hit_pct: float = 0.0
    cpu_hit_pct: float = 0.0
    ssd_hit_pct: float = 0.0
    hbm_gb_used: float = 0.0
    cpu_gb_used: float = 0.0
    placement: Dict[int, List[int]] = field(default_factory=dict)


def _rank_from_profile(profile_path: Optional[str], n_layers: int, n_experts: int
                       ) -> Dict[int, List[int]]:
    """若有真实 profiling (profile_real_moe.py 产出), 用每层访问计数排热度;
    否则退化为自然序 0..n_experts-1 (warm-up 用, 运行期动态 LRU 会自适应)。"""
    if profile_path and os.path.exists(profile_path):
        try:
            prof = json.load(open(profile_path))
            per_layer = prof.get("per_layer_counts")  # 可选: {layer: [count_e0,...]}
            if per_layer:
                out = {}
                for L in range(n_layers):
                    counts = per_layer.get(str(L)) or per_layer.get(L)
                    if counts:
                        out[L] = sorted(range(len(counts)), key=lambda e: -counts[e])[:n_experts]
                    else:
                        out[L] = list(range(n_experts))
                return out
        except Exception as e:  # noqa: BLE001
            print(f"  [compile] profile parse failed ({e}), fall back to natural order")
    return {L: list(range(n_experts)) for L in range(n_layers)}


# ════════════════════════════════════════════════════════════════════
# M3: 路由感知的层间联合放置 (routing_aware_placement)
# ════════════════════════════════════════════════════════════════════

def build_cooccurrence_from_trace(per_layer_trace: Dict[int, List[List[int]]],
                                   n_layers: int, n_experts: int
                                   ) -> Dict[int, Dict[int, Dict[int, float]]]:
    """从 per-layer 路由 trace 构建层间专家共现矩阵。

    per_layer_trace: {layer_id: [[expert_ids_per_token], ...]}
        每层每 token 激活的 expert id 列表 (top-k 结果).

    Returns:
        cooc[L][e][e_next] = P(e_next in L+1 | e in L)
        即给定层 L 激活 expert e, 下一层 L+1 激活 e_next 的条件概率。
    """
    if not per_layer_trace:
        return {}
    cooc: Dict[int, Dict[int, Dict[int, float]]] = {}
    for L in range(n_layers - 1):
        trace_L = per_layer_trace.get(L)
        trace_next = per_layer_trace.get(L + 1)
        if not trace_L or not trace_next:
            continue
        n_tokens = min(len(trace_L), len(trace_next))
        # 先统计联合出现次数
        joint_counts: Dict[int, Dict[int, int]] = {}
        marginal_counts: Dict[int, int] = {}
        for t in range(n_tokens):
            experts_L = set(trace_L[t])
            experts_next = set(trace_next[t])
            for e in experts_L:
                marginal_counts[e] = marginal_counts.get(e, 0) + 1
                if e not in joint_counts:
                    joint_counts[e] = {}
                for e_next in experts_next:
                    joint_counts[e][e_next] = joint_counts[e].get(e_next, 0) + 1
        # 转为条件概率 P(e_next | e)
        cooc[L] = {}
        for e, total in marginal_counts.items():
            if total > 0:
                cooc[L][e] = {}
                for e_next in range(n_experts):
                    cnt = joint_counts.get(e, {}).get(e_next, 0)
                    if cnt > 0:
                        cooc[L][e][e_next] = cnt / total
    return cooc


def joint_ranking(per_layer_counts: Dict[int, List[int]],
                  cooc: Dict[int, Dict[int, Dict[int, float]]],
                  per_layer_k_h: List[int],
                  n_layers: int,
                  n_experts: int,
                  boost_factor: float = 0.5,
                  min_cooc_prob: float = 0.05) -> Dict[int, List[int]]:
    """层间联合排序: 在单层热度的基础上, 对与上一层 HBM 驻留专家高频共现的
    专家进行加分, 使其优先进入快层。

    Args:
        per_layer_counts: {layer: [count_per_expert]}  — 各 expert 的独立访问计数
        cooc: 共现条件概率矩阵, build_cooccurrence_from_trace 产出
        per_layer_k_h: 每层 HBM 槽位数 (决定上一层哪些专家在 HBM)
        n_layers, n_experts: 模型维度
        boost_factor: 共现加分强度 (0 = 退化为纯热度排序)
        min_cooc_prob: 忽略低于此概率的共现 (过滤噪声)

    Returns:
        {layer_id: [expert_ids in joint-heat order]}
    """
    placement: Dict[int, List[int]] = {}

    for L in range(n_layers):
        raw_counts = list(per_layer_counts.get(L, [0.0] * n_experts))
        # 确保长度为 n_experts
        if len(raw_counts) < n_experts:
            raw_counts.extend([0.0] * (n_experts - len(raw_counts)))
        adjusted = list(raw_counts)

        # 若有上一层 HBM 驻留信息, 计算共现加分
        if L > 0 and (L - 1) in cooc and (L - 1) in placement:
            prev_placement = placement[L - 1]
            prev_k_h = per_layer_k_h[L - 1] if L - 1 < len(per_layer_k_h) else 0
            hbm_experts_prev = set(prev_placement[:prev_k_h])
            prev_cooc = cooc[L - 1]

            max_raw = max(raw_counts) if max(raw_counts) > 0 else 1.0
            for e in range(n_experts):
                cooc_score = 0.0
                for prev_e in hbm_experts_prev:
                    prob = prev_cooc.get(prev_e, {}).get(e, 0.0)
                    if prob >= min_cooc_prob:
                        cooc_score += prob
                if cooc_score > 0:
                    # 共现得分归一化后加权叠加到原始计数
                    adjusted[e] = raw_counts[e] + boost_factor * max_raw * cooc_score

        # 按调整后分数降序排列
        ranked = sorted(range(n_experts), key=lambda e: -adjusted[e])
        placement[L] = ranked

    return placement


def _extract_per_layer_counts(profile_path: Optional[str],
                               n_layers: int, n_experts: int
                               ) -> Dict[int, List[int]]:
    """从 profile JSON 提取每层访问计数, 兼容 str/int 两种 layer key。"""
    counts: Dict[int, List[int]] = {}
    if profile_path and os.path.exists(profile_path):
        try:
            prof = json.load(open(profile_path))
            per_layer = prof.get("per_layer_counts")
            if per_layer:
                for L in range(n_layers):
                    c = per_layer.get(str(L)) or per_layer.get(L)
                    if c:
                        counts[L] = list(c)
        except Exception:
            pass
    return counts


def _extract_per_layer_trace(profile_path: Optional[str],
                              n_layers: int
                              ) -> Optional[Dict[int, List[List[int]]]]:
    """从 profile JSON 提取每层路由 trace (若存在)。"""
    if not (profile_path and os.path.exists(profile_path)):
        return None
    try:
        prof = json.load(open(profile_path))
        trace = prof.get("per_layer_trace")
        if trace:
            return {int(k): v for k, v in trace.items()}
    except Exception:
        pass
    return None


# 已知 MoE 模型规格 (expert fp16 单层单 expert 大小)
MODEL_SPECS = {
    # name: (n_layers, n_experts, top_k, expert_mb_fp16)
    "mistralai/Mixtral-8x7B-Instruct-v0.1": (32, 8, 2, 336.0),
    "mistralai/Mixtral-8x7B-v0.1":          (32, 8, 2, 336.0),
    "deepseek-ai/DeepSeek-V2-Lite":         (26, 64, 6, 16.5),   # 27 层中 26 MoE 层
    "smoke":                                (2,  8, 2, 0.2),
}

# 模型类型标识 (用于 run_e2e 自动选择 tiered 模块)
MODEL_TYPE = {
    "mistralai/Mixtral-8x7B-Instruct-v0.1": "mixtral",
    "mistralai/Mixtral-8x7B-v0.1":          "mixtral",
    "deepseek-ai/DeepSeek-V2-Lite":         "deepseek",
}


def compile_plan(model_name: str,
                 hbm_budget_gb: float,
                 cpu_budget_gb: float,
                 alpha: float = 1.0,
                 per_layer_alpha: Optional[List[float]] = None,
                 profile_path: Optional[str] = None,
                 n_layers: Optional[int] = None,
                 n_experts: Optional[int] = None,
                 expert_mb: Optional[float] = None,
                 hw_name: str = "rtx5090",
                 enable_m3: bool = True) -> CompiledPlan:
    """给定 expert 可用的 HBM / CPU 预算 (GB), 计算 (K_H, K_C)。

    若提供 per_layer_alpha, 使用 Theorem 4 per-layer 自适应分配:
      偏斜度高的层少给 slots, 偏斜度低的层多给, 总约束 ∑K_H_l ≤ total_HBM_slots。
    否则退化为均匀分配。
    """
    if model_name in MODEL_SPECS:
        nl, ne, _tk, emb = MODEL_SPECS[model_name]
    else:
        nl, ne, emb = 32, 8, 336.0
    n_layers = n_layers or nl
    n_experts = n_experts or ne
    expert_mb = expert_mb or emb
    esz_gb = expert_mb / 1024.0

    total_hbm_slots = int(hbm_budget_gb / esz_gb)
    total_cpu_slots = int(cpu_budget_gb / esz_gb)

    # ── Per-layer 自适应分配 (Theorem 4) ──
    per_k_h = []
    per_k_c = []
    per_alpha = []

    if per_layer_alpha and len(per_layer_alpha) == n_layers:
        per_alpha = list(per_layer_alpha)
        # 水塘分配: 从每个 layer 基础 1 slot 开始, 贪心地把剩余 slots 给边际收益最大的层
        layer_kh = [1] * n_layers          # 每层至少 1 个 HBM slot
        remaining = total_hbm_slots - n_layers

        while remaining > 0:
            best_layer, best_gain = -1, -1.0
            for L in range(n_layers):
                if layer_kh[L] >= n_experts:
                    continue
                # 边际收益 = 从 K 增加到 K+1 带来的 Zipf hit rate 提升
                cur_hit = zcdf(layer_kh[L], n_experts, per_alpha[L])
                next_hit = zcdf(layer_kh[L] + 1, n_experts, per_alpha[L])
                gain = next_hit - cur_hit
                if gain > best_gain:
                    best_gain, best_layer = gain, L
            if best_layer < 0:
                break
            layer_kh[best_layer] += 1
            remaining -= 1

        per_k_h = layer_kh

        # CPU: 同样贪心分配 (次热 experts 去 CPU)
        layer_kc = [1] * n_layers
        remaining_cpu = total_cpu_slots - n_layers
        while remaining_cpu > 0:
            best_layer, best_gain = -1, -1.0
            for L in range(n_layers):
                if layer_kc[L] >= n_experts - per_k_h[L]:
                    continue
                cur_hit = zcdf(per_k_h[L] + layer_kc[L], n_experts, per_alpha[L])
                next_hit = zcdf(per_k_h[L] + layer_kc[L] + 1, n_experts, per_alpha[L])
                gain = next_hit - cur_hit
                if gain > best_gain:
                    best_gain, best_layer = gain, L
            if best_layer < 0:
                break
            layer_kc[best_layer] += 1
            remaining_cpu -= 1
        per_k_c = layer_kc

        # 聚合命中率预估
        avg_hbm_hit = sum(zcdf(per_k_h[L], n_experts, per_alpha[L]) for L in range(n_layers)) / n_layers
        avg_cpu_hit = sum(zcdf(per_k_h[L] + per_k_c[L], n_experts, per_alpha[L]) -
                          zcdf(per_k_h[L], n_experts, per_alpha[L]) for L in range(n_layers)) / n_layers
        hbm_hit, cpu_hit = avg_hbm_hit, avg_cpu_hit
        ssd_hit = max(0.0, 1.0 - hbm_hit - cpu_hit)

        # 向后兼容的全局 k_h/k_c
        k_h = round(sum(per_k_h) / n_layers)
        k_c = round(sum(per_k_c) / n_layers)
    else:
        # ── 均匀分配 (fallback) ──
        per_layer_hbm_gb = hbm_budget_gb / n_layers
        per_layer_cpu_gb = cpu_budget_gb / n_layers
        k_h = max(0, min(n_experts, int(per_layer_hbm_gb / esz_gb)))
        k_c = max(0, min(n_experts - k_h, int(per_layer_cpu_gb / esz_gb)))
        per_k_h = [k_h] * n_layers
        per_k_c = [k_c] * n_layers

        hbm_hit = zcdf(k_h, n_experts, alpha)
        cpu_hit = zcdf(k_h + k_c, n_experts, alpha) - hbm_hit
        ssd_hit = max(0.0, 1.0 - hbm_hit - cpu_hit)

    # ── M3: 尝试层间联合排序 (路由感知放置) ──
    cooc_data = None
    if enable_m3:
        per_layer_trace = _extract_per_layer_trace(profile_path, n_layers)
        if per_layer_trace and len(per_layer_trace) >= 2:
            cooc_data = build_cooccurrence_from_trace(per_layer_trace, n_layers, n_experts)

    if cooc_data and enable_m3:
        # 有共现数据 → 联合排序
        per_layer_counts = _extract_per_layer_counts(profile_path, n_layers, n_experts)
        if not per_layer_counts:
            per_layer_counts = {L: [1] * n_experts for L in range(n_layers)}
        placement = joint_ranking(per_layer_counts, cooc_data, per_k_h,
                                  n_layers, n_experts)
        print(f"  [M3] Routing-aware joint placement active "
              f"(cooc layers={len(cooc_data)}, boost={0.5})")
    else:
        # 无共现数据或 M3 禁用 → 纯热度排序 (向后兼容)
        placement = _rank_from_profile(profile_path, n_layers, n_experts)

    plan = CompiledPlan(
        model=model_name,
        hardware=f"{hw_name} (HBM_budget={hbm_budget_gb}GB, CPU_budget={cpu_budget_gb}GB)",
        alpha=round(alpha, 3),
        n_layers=n_layers, n_experts=n_experts, expert_mb=round(expert_mb, 1),
        k_h=k_h, k_c=k_c,
        per_layer_k_h=per_k_h, per_layer_k_c=per_k_c,
        per_layer_alpha=[round(a, 3) for a in per_alpha],
        hbm_hit_pct=round(hbm_hit * 100, 1),
        cpu_hit_pct=round(cpu_hit * 100, 1),
        ssd_hit_pct=round(ssd_hit * 100, 1),
        hbm_gb_used=round(k_h * esz_gb * n_layers, 2),
        cpu_gb_used=round(k_c * esz_gb * n_layers, 2),
        placement=placement,
    )
    return plan


def print_plan(plan: CompiledPlan):
    print("-" * 70)
    print(f"COMPILED PLAN  model={plan.model}")
    print(f"  α={plan.alpha}  layers={plan.n_layers}  experts/layer={plan.n_experts}  "
          f"expert={plan.expert_mb}MB")
    if plan.per_layer_alpha:
        print(f"  per-layer adaptive: K_H∈[{min(plan.per_layer_k_h)}..{max(plan.per_layer_k_h)}]  "
              f"K_C∈[{min(plan.per_layer_k_c)}..{max(plan.per_layer_k_c)}]  "
              f"α∈[{min(plan.per_layer_alpha):.2f}..{max(plan.per_layer_alpha):.2f}]")
        print(f"  total HBM={sum(plan.per_layer_k_h)} slots  CPU={sum(plan.per_layer_k_c)} slots")
    else:
        print(f"  per-layer  K_H={plan.k_h} (HBM)  K_C={plan.k_c} (CPU)  "
              f"SSD={plan.n_experts - plan.k_h - plan.k_c}")
    print(f"  total HBM for experts ≈ {plan.hbm_gb_used}GB | CPU ≈ {plan.cpu_gb_used}GB")
    print(f"  predicted hit  HBM={plan.hbm_hit_pct}%  CPU={plan.cpu_hit_pct}%  SSD={plan.ssd_hit_pct}%")
    print("-" * 70)


if __name__ == "__main__":
    # demo: 为 5090(32GB) 编译 Mixtral 计划 (假设 trunk+KV 用 ~8GB, 留 22GB 给 expert)
    p = compile_plan("mistralai/Mixtral-8x7B-Instruct-v0.1",
                     hbm_budget_gb=22.0, cpu_budget_gb=40.0, alpha=1.0)
    print_plan(p)
    print(json.dumps({k: v for k, v in asdict(p).items() if k != "placement"}, indent=2))
