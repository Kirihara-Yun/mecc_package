#!/usr/bin/env python3
"""M3 验证脚本: 编译器级命中率对比 (有/无 层间联合放置)

用 compiler.py 的 generate_profile_per_layer 生成带层间相关性的合成 profile，
然后分别用纯热度排序 vs 联合排序 编译, 对比 per-layer 命中率分布。

这是 M3 Phase 1 的 L1 验证 (算法上界观测)。
"""
import json
import os
import sys
import tempfile

# e2e 目录的 import
from compile_config import (
    compile_plan, joint_ranking, build_cooccurrence_from_trace,
    _extract_per_layer_counts, _extract_per_layer_trace, _rank_from_profile,
)
# 父目录 compiler.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from compiler import generate_profile_per_layer, zcdf


def main():
    # ── 生成带层间相关性的合成 profile ──
    print("=" * 60)
    print("M3 验证: 编译器级命中率对比")
    print("=" * 60)

    model_name = "deepseek-v2-lite"
    profile = generate_profile_per_layer(
        model_name, n_tokens=5000, inter_layer_corr=0.4)
    # 截断为 8 层以加速测试
    n_layers_test = 8
    profile["n_layers"] = n_layers_test
    profile["per_layer_counts"] = {
        str(L): profile["per_layer_counts"][str(L)]
        for L in range(n_layers_test)
    }
    profile["per_layer_trace"] = {
        str(L): profile["per_layer_trace"][str(L)]
        for L in range(n_layers_test)
    }

    # 写入临时文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(profile, f)
        profile_path = f.name

    print(f"\nProfile: {model_name}")
    print(f"  layers={n_layers_test}, experts={profile['n_experts']}")
    print(f"  alpha={profile['true_alpha']}, inter_layer_corr={profile['inter_layer_corr']}")
    print(f"  tokens={profile['n_tokens']}")

    # ── HBM/CPU 预算 (模拟受限场景) ──
    hbm_gb = 8.0
    cpu_gb = 12.0
    n_experts = profile["n_experts"]

    # ── 方案 A: 纯热度排序 (baseline, 无 M3) ──
    print(f"\n{'─' * 50}")
    print("方案 A: 纯热度排序 (baseline, 无 M3)")
    print(f"{'─' * 50}")

    plan_baseline = compile_plan(
        model_name, hbm_budget_gb=hbm_gb, cpu_budget_gb=cpu_gb,
        alpha=profile["estimated_alpha"],
        profile_path=profile_path,
        n_layers=n_layers_test, n_experts=n_experts,
        expert_mb=16.5,
        enable_m3=False,  # 禁用 M3 → 纯热度排序
    )

    # ── 方案 B: 联合排序 (M3) ──
    print(f"\n{'─' * 50}")
    print("方案 B: 路由感知联合排序 (M3)")
    print(f"{'─' * 50}")

    # 直接调用 M3 函数
    per_layer_trace = _extract_per_layer_trace(profile_path, n_layers_test)
    cooc_data = build_cooccurrence_from_trace(
        per_layer_trace, n_layers_test, n_experts)
    per_layer_counts = _extract_per_layer_counts(
        profile_path, n_layers_test, n_experts)

    if cooc_data and per_layer_counts:
        placement_m3 = joint_ranking(
            per_layer_counts, cooc_data,
            plan_baseline.per_layer_k_h,
            n_layers_test, n_experts,
            boost_factor=0.5)
        print(f"  Co-occurrence layers: {len(cooc_data)}")
        print(f"  M3 joint ranking active ✓")
    else:
        print("  ⚠ Co-occurrence data not available, cannot test M3")
        placement_m3 = None

    # ── 对比 per-layer 命中率 ──
    print(f"\n{'=' * 60}")
    print("对比: Per-layer 命中率分布 (纯热度 vs M3 联合排序)")
    print(f"{'=' * 60}")

    placement_baseline = _rank_from_profile(profile_path, n_layers_test, n_experts)

    print(f"\n{'Layer':>5} | {'K_H':>4} {'K_C':>4} | "
          f"{'HBM_hit(baseline)':>16} {'HBM_hit(M3)':>16} | "
          f"{'CPU_hit(baseline)':>16} {'CPU_hit(M3)':>16}")
    print("-" * 95)

    total_hbm_delta = 0.0
    total_cpu_delta = 0.0

    for L in range(n_layers_test):
        kh = plan_baseline.per_layer_k_h[L]
        kc = plan_baseline.per_layer_k_c[L]

        # Baseline: 纯热度排序命中率
        # 用 zcdf 计算 (Zipf 模型下的期望命中)
        hbm_hit_bl = zcdf(kh, n_experts, profile["true_alpha"])
        cpu_hit_bl = zcdf(kh + kc, n_experts, profile["true_alpha"]) - hbm_hit_bl

        # M3: 由于 placement 重排, 实际命中率可能与 Zipf 期望有偏差
        # 这里用 empirical 方式: 计算 M3 placement 中前 kh 个 expert 的实际访问覆盖
        if placement_m3 and L in placement_m3 and L in per_layer_counts:
            m3_ranked = placement_m3[L]
            counts = per_layer_counts[L]
            total = sum(counts) or 1

            # HBM 命中: M3 placement 前 kh 的覆盖
            m3_hbm_hit = sum(counts[e] for e in m3_ranked[:kh]) / total
            # CPU 命中: 前 kh+kc 的覆盖 - 前 kh
            m3_cpu_hit = sum(counts[e] for e in m3_ranked[:kh + kc]) / total - m3_hbm_hit

            hbm_hit_bl_emp = sum(counts[e] for e in placement_baseline[L][:kh]) / total
            cpu_hit_bl_emp = sum(counts[e] for e in placement_baseline[L][:kh + kc]) / total - hbm_hit_bl_emp
        else:
            m3_hbm_hit = hbm_hit_bl
            m3_cpu_hit = cpu_hit_bl
            hbm_hit_bl_emp = hbm_hit_bl
            cpu_hit_bl_emp = cpu_hit_bl

        delta_hbm = m3_hbm_hit - hbm_hit_bl_emp
        delta_cpu = m3_cpu_hit - cpu_hit_bl_emp
        total_hbm_delta += delta_hbm
        total_cpu_delta += delta_cpu

        marker_hbm = " ↑" if delta_hbm > 0.001 else (" ↓" if delta_hbm < -0.001 else "  ")
        marker_cpu = " ↑" if delta_cpu > 0.001 else (" ↓" if delta_cpu < -0.001 else "  ")

        print(f"{L:>5} | {kh:>4} {kc:>4} | "
              f"{hbm_hit_bl_emp*100:>15.1f}% {m3_hbm_hit*100:>15.1f}%{marker_hbm} | "
              f"{cpu_hit_bl_emp*100:>15.1f}% {m3_cpu_hit*100:>15.1f}%{marker_cpu}")

    print("-" * 95)
    print(f"{'SUM':>5} | {'':>4} {'':>4} | "
          f"{'ΔHBM:':>15} {total_hbm_delta*100:+.1f}% | "
          f"{'ΔCPU:':>15} {total_cpu_delta*100:+.1f}%")

    # ── 共现矩阵统计 ──
    print(f"\n{'=' * 60}")
    print("共现矩阵统计")
    print(f"{'=' * 60}")
    if cooc_data:
        for L in sorted(cooc_data.keys())[:3]:
            n_pairs = sum(len(inners) for inners in cooc_data[L].values())
            mean_prob = 0.0
            count = 0
            for e, inners in cooc_data[L].items():
                for _, prob in inners.items():
                    mean_prob += prob
                    count += 1
            mean_prob = mean_prob / count if count > 0 else 0
            print(f"  L{L}→L{L+1}: {len(cooc_data[L])} source experts, "
                  f"{n_pairs} edges, mean cooc prob={mean_prob:.4f}")
    else:
        print("  (no co-occurrence data)")

    # 清理
    os.unlink(profile_path)
    print(f"\nM3 验证完成 ✓")


if __name__ == "__main__":
    main()
