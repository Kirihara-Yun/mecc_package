#!/usr/bin/env python3
"""
tier_sim.py — 受真实数据验证的跨硬件投影模拟器
================================================
方法论 (诚实的系统评测):
  观察: **缓存命中率与硬件延迟无关** —— 它只取决于 trace + 缓存策略 + 容量。
  因此: 用 real_tiered_cache.py 在真实硬件上实测得到的命中率 (硬件无关),
        代入不同硬件的 tier 延迟参数, 即可投影各硬件上的平均延迟。

  - Apple (measured): 用本机实测 tier 延迟 → 应能复现真实原型的平均延迟 (验证线性模型)。
  - A100 / H100 (projected): 用厂商公开规格 → 投影目标硬件收益。

延迟模型: T_tier = compute + transfer_tier
  HBM hit : 权重常驻 GPU → transfer = 0, 仅 GEMM compute
  CPU hit : PCIe/UMA host→device 传输 + compute
  SSD miss: NVMe 读 + host→device 传输 + compute

硬件规格来源 (公开):
  A100-80GB HBM2e   : 2039 GB/s   (NVIDIA datasheet)
  H100-80GB HBM3    : 3350 GB/s   (NVIDIA datasheet)
  PCIe 4.0 x16      : ~25 GB/s 有效 (CPU→GPU pinned)
  PCIe 5.0 x16      : ~50 GB/s 有效
  NVMe Gen4 SSD     : ~7 GB/s 顺序读
  NVMe Gen5 SSD     : ~14 GB/s 顺序读
  Apple M-series    : 本机 measure_tiers.py 实测
"""
import json, os, argparse


def expert_size_mb(hidden, ffn, dtype_bytes=2):
    return 3 * hidden * ffn * dtype_bytes / 1e6


# ─────────────────────────────────────────────────────────────
# 硬件 tier 延迟模型 (μs), 给定 expert 大小 (MB)
# ─────────────────────────────────────────────────────────────

def tier_latencies(hw, esz_mb):
    """返回 (T_H, T_C, T_S) μs。T = compute + transfer。"""
    comp = hw["compute_us"]
    def xfer(bw_gbs, lat_us):
        return lat_us + (esz_mb / 1024) / bw_gbs * 1e6
    T_H = comp                                              # HBM 常驻, 仅 compute
    T_C = comp + xfer(hw["h2d_bw"], hw["h2d_lat"])          # +PCIe/UMA
    T_S = comp + xfer(hw["ssd_bw"], hw["ssd_lat"]) + xfer(hw["h2d_bw"], hw["h2d_lat"])
    return T_H, T_C, T_S


HARDWARE = {
    # name: compute(GEMM), host→device BW/lat, SSD BW/lat
    "A100-PCIe4-NVMeGen4": {
        "compute_us": 120, "h2d_bw": 25, "h2d_lat": 10, "ssd_bw": 7, "ssd_lat": 100},
    "H100-PCIe5-NVMeGen5": {
        "compute_us": 80, "h2d_bw": 50, "h2d_lat": 8, "ssd_bw": 14, "ssd_lat": 80},
    # Apple: 实测填入 (compute=HBM hit total; h2d 由 transfer-only 反推)
    "Apple-M-UMA(measured)": None,  # 运行时从 measured_latency.json 注入
}


def load_apple_measured(path, esz_mb_proto):
    """从 measure_tiers.py 的输出构造 Apple 的 tier 延迟 (按 expert 大小线性缩放)。"""
    if not os.path.exists(path):
        return None
    d = json.load(open(path))
    base_mb = d["expert_size_mb"]
    scale = esz_mb_proto / base_mb
    tl = d["tier_latency_us"]; xf = d["transfer_only_us"]
    comp = tl["hbm_hit"] * scale                       # HBM hit ≈ compute
    cpu_x = xf["cpu_to_device"] * scale
    ssd_r = xf["ssd_read"] * scale
    return {"_direct": (comp, comp + cpu_x, comp + ssd_r + cpu_x),
            "_raw_336mb": (tl["hbm_hit"], tl["cpu_hit"], tl["ssd_miss"])}


def avg_latency(hits_pct, T):
    p = [h / 100 for h in hits_pct]
    return p[0] * T[0] + p[1] * T[1] + p[2] * T[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--e2e", default="real_e2e_results.json")
    ap.add_argument("--measured", default="measured_latency.json")
    ap.add_argument("--hidden", type=int, default=4096, help="投影用 expert 尺寸 (Mixtral=4096)")
    ap.add_argument("--ffn", type=int, default=14336)
    ap.add_argument("--out", default="projection_results.json")
    args = ap.parse_args()

    e2e = json.load(open(args.e2e))
    esz_mb = expert_size_mb(args.hidden, args.ffn)
    proto_mb = e2e["config"]["expert_mb"]

    print("=" * 78)
    print("Cross-Hardware Projection (hit rates = REAL measured; latencies = per-hardware)")
    print("=" * 78)
    print(f"Projection expert size : {esz_mb:.0f} MB (hidden={args.hidden}, ffn={args.ffn})")
    print(f"Real hit rates from    : {args.e2e} (measured on {e2e['device']}, "
          f"proto expert {proto_mb:.0f}MB)")

    # 组装硬件 tier 延迟
    apple = load_apple_measured(args.measured, esz_mb)
    hw_lat = {}
    for name, spec in HARDWARE.items():
        if spec is None:
            continue
        hw_lat[name] = tier_latencies(spec, esz_mb)
    if apple:
        hw_lat["Apple-M-UMA(measured)"] = apple["_direct"]

    print(f"\nTier latencies (μs) for {esz_mb:.0f}MB expert:")
    print(f"  {'Hardware':<26} {'T_HBM':>9} {'T_CPU':>9} {'T_SSD':>9}  {'C/H':>5} {'S/H':>6}")
    for name, (TH, TC, TS) in hw_lat.items():
        print(f"  {name:<26} {TH:>9.0f} {TC:>9.0f} {TS:>9.0f}  {TC/TH:>5.1f} {TS/TH:>6.1f}")

    out = {"projection_expert_mb": round(esz_mb, 1), "hardware_latencies_us": {},
           "workloads": []}
    for name, T in hw_lat.items():
        out["hardware_latencies_us"][name] = {"T_HBM": round(T[0], 1),
                                              "T_CPU": round(T[1], 1), "T_SSD": round(T[2], 1)}

    for wl in e2e["workloads"]:
        label = wl["workload"]
        rows = {r["policy"]: r for r in wl["results"]}
        print(f"\n{'─'*78}\n[{label}] hit rates (H/C/S %):")
        for p in ["FluxMoE", "SwapMoE", "TieredLRU"]:
            r = rows[p]
            print(f"  {p:<11} {r['hbm_hit_pct']:>4.0f}/{r['cpu_hit_pct']:>4.0f}/{r['ssd_hit_pct']:>4.0f}")
        wl_out = {"workload": label, "projections": {}}
        print(f"\n  Projected OURS speedup (avg latency):")
        print(f"  {'Hardware':<26} {'vs FluxMoE':>12} {'vs SwapMoE':>12}")
        for name, T in hw_lat.items():
            def al(p):
                r = rows[p]
                return avg_latency([r["hbm_hit_pct"], r["cpu_hit_pct"], r["ssd_hit_pct"]], T)
            f, s, t = al("FluxMoE"), al("SwapMoE"), al("TieredLRU")
            sp_f, sp_s = f / t, s / t
            wl_out["projections"][name] = {
                "flux_us": round(f, 1), "swap_us": round(s, 1), "ours_us": round(t, 1),
                "speedup_vs_flux": round(sp_f, 3), "speedup_vs_swap": round(sp_s, 3)}
            mark = " ★" if sp_s > 1.15 else (" ✓" if sp_s > 1.02 else "")
            print(f"  {name:<26} {sp_f:>11.2f}× {sp_s:>11.2f}×{mark}")
        out["workloads"].append(wl_out)

    # 验证: Apple 投影 vs 真实原型实测
    print(f"\n{'═'*78}")
    print("VALIDATION — Apple linear model vs real prototype (proto expert size):")
    apple_proto = load_apple_measured(args.measured, proto_mb)
    if apple_proto:
        Tp = apple_proto["_direct"]
        for wl in e2e["workloads"]:
            rows = {r["policy"]: r for r in wl["results"]}
            print(f"  [{wl['workload']}]  policy   model_pred   measured   err")
            for p in ["FluxMoE", "SwapMoE", "TieredLRU"]:
                r = rows[p]
                pred = avg_latency([r["hbm_hit_pct"], r["cpu_hit_pct"], r["ssd_hit_pct"]], Tp)
                meas = r["avg_lat_us"]
                print(f"           {p:<11} {pred:>9.0f}μs {meas:>9.0f}μs  {(pred-meas)/meas*100:>+5.0f}%")
    print("═" * 78)

    json.dump(out, open(args.out, "w"), indent=2, ensure_ascii=False)
    print(f"Saved → {args.out}")


if __name__ == "__main__":
    main()
