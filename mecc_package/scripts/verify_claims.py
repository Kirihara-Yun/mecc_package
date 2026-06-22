#!/usr/bin/env python3
"""
MECC 数字一致性体检（claim ↔ 证据）
====================================
零第三方依赖（仅标准库）。在引用 / 发布任何性能数字、或新增实验数据后运行：

  python3 scripts/verify_claims.py            # 体检全部已登记断言
  python3 scripts/verify_claims.py --strict   # 有任何 FAIL/UNVERIFIED 即退出码 1（CI 门禁用）

它做什么：
  把 docs/PROVENANCE.md §3 对照表里**状态为 verified** 的关键数字，
  编码成可机检断言，逐条回到 results/*.json 实测字段核对，
  防止文档 / 论文里出现与数据对不上的数字。

它不做什么：
  不重跑实验、不判断 discrepancy 谁对谁错（那需要真机重测）。
  discrepancy / unverified 项只做提醒，不当 FAIL（除非 --strict）。

权威源：docs/PROVENANCE.md（数字真伪）、results/SCHEMA.md（字段语义）。
若本脚本与 PROVENANCE 不一致，以 PROVENANCE 为准并同步修订本文件 CLAIMS。
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # mecc_package/
RESULTS = os.path.join(ROOT, "results")

PASS = WARN = FAIL = 0


def _ok(msg):
    global PASS; PASS += 1; print(f"  [ OK ] {msg}")


def _warn(msg):
    global WARN; WARN += 1; print(f"  [WARN] {msg}")


def _fail(msg):
    global FAIL; FAIL += 1; print(f"  [FAIL] {msg}")


def _load(rel):
    """加载 results/ 下的 json；找不到返回 None。"""
    path = os.path.join(RESULTS, rel)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get(d, dotted):
    """按 'a.b.c' 路径取值；任一级缺失返回 None。"""
    cur = d
    for k in dotted.split("."):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur


def _close(a, b, tol):
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# 可机检断言：每条 = PROVENANCE §3 里一条 verified claim
#   (claim_id, 文件, 字段路径, 期望值, 容差, 人读说明)
# 新增 verified claim 时，在 PROVENANCE §3 登记后，这里补一行即可。
# ---------------------------------------------------------------------------
CLAIMS = [
    # --- 主场景 Mixtral（D2 真机，mixtral_real.json）---
    ("M1", "raw/mixtral_real.json", "results.ours.speedup_vs.swapmoe", 1.333, 0.01,
     "Mixtral OURS vs SwapMoE 加速 1.33×"),
    ("M2a", "raw/mixtral_real.json", "results.ours.ppl", 24.569, 0.01,
     "Mixtral OURS 无损 PPL 24.57"),
    ("M2b", "raw/mixtral_real.json", "results.swapmoe.ppl", 36.116, 0.01,
     "Mixtral SwapMoE 有损 PPL 36.12"),
    ("M3a", "raw/mixtral_real.json", "results.ours.hit_pct.ssd", 17.6, 0.1,
     "Mixtral OURS SSD 命中 17.6%"),
    ("M3b", "raw/mixtral_real.json", "results.swapmoe.hit_pct.ssd", 34.5, 0.1,
     "Mixtral SwapMoE SSD 命中 34.5%"),
    ("M4a", "raw/mixtral_real.json", "results.ours.hit_pct.cpu", 38.0, 0.1,
     "Mixtral OURS CPU 命中 38.0%"),
    ("M4b", "raw/mixtral_real.json", "results.swapmoe.hit_pct.cpu", 23.3, 0.1,
     "Mixtral SwapMoE CPU 命中 23.3%"),
    # --- 对照场景 DeepSeek（D2 真机，main_table_5090.json）---
    ("D3", "main_table_5090.json", "results.ours.speedup_vs.swapmoe", 2.554, 0.01,
     "DeepSeek e2e OURS vs SwapMoE 2.55×"),
    # --- 热点漂移（D1 模拟器，deepseek_real_e2e.json）---
    ("H1a", "raw/deepseek_real_e2e.json", "workloads.1.speedup.vs_flux", 9.502, 0.01,
     "漂移 OURS vs FluxMoE 9.50×（模拟器）"),
    ("H1b", "raw/deepseek_real_e2e.json", "workloads.1.speedup.vs_swap", 5.68, 0.01,
     "漂移 OURS vs SwapMoE 5.68×（模拟器）"),
    ("H2a", "raw/deepseek_real_e2e.json", "workloads.0.speedup.vs_flux", 6.26, 0.01,
     "静止 OURS vs FluxMoE 6.26×（模拟器）"),
    # --- 三级延迟（D2 实测）---
    ("L1h", "raw/measured_latency_5090.json", "tier_latency_us.hbm_hit", 255.8, 0.5,
     "5090 HBM 命中延迟 255.8µs"),
    ("L1s", "raw/measured_latency_5090.json", "tier_latency_us.ssd_miss", 789738.9, 1.0,
     "5090 SSD miss 延迟 ~790ms"),
]

# 提醒型：PROVENANCE 登记为 discrepancy/unverified 的数字，禁止当结论引用。
REMINDERS = [
    ("X1", "论文表3 DeepSeek e2e（TTFT 7426/tok/s 0.92/1.56×）无对应 JSON —— unverified，禁止外引"),
    ("X2", "Mixtral 平台 [已澄清]：实验先 5090 后 A100，主结果在 A100 跑定（STRATEGY §2.2 佐证）—— 平台真值已写入各 JSON 顶层 platform=A100；compiled_plan.hardware 降级为编译期配置串，不再作平台依据"),
    ("X3", "加速口径：1.33×(综合) 与 1.62×(TPOT) 是两个指标，引用须标口径"),
    ("X4", "expert 体积：336MB(实测张量) vs 1407MB(理论3矩阵)，口径不同"),
    ("X5", "results/README.md 顶部硬件 A100 [已澄清，正确] —— 各 JSON 顶层 platform=A100 已与之一致；以 platform 字段为平台真值"),
]


def _support_dotted(d, dotted):
    """支持路径里的数组下标，如 'workloads.1.speedup.vs_flux'。"""
    cur = d
    for k in dotted.split("."):
        if isinstance(cur, list):
            try:
                cur = cur[int(k)]
            except (ValueError, IndexError):
                return None
        elif isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur


def check_claims():
    print("== Claim ↔ 证据 一致性体检（仅 verified 项） ==")
    cache = {}
    for cid, rel, path, expect, tol, desc in CLAIMS:
        if rel not in cache:
            cache[rel] = _load(rel)
        data = cache[rel]
        if data is None:
            _fail(f"{cid}: 证据文件缺失 results/{rel} —— {desc}")
            continue
        actual = _support_dotted(data, path)
        if actual is None:
            _fail(f"{cid}: 字段缺失 {rel}:{path} —— {desc}")
        elif _close(actual, expect, tol):
            _ok(f"{cid}: {desc}（{rel}:{path} = {actual}）")
        else:
            _fail(f"{cid}: 不一致！期望 {expect}±{tol}，实际 {actual}"
                  f"（{rel}:{path}）—— {desc}")


def check_reminders():
    print("\n== 已登记矛盾 / 未核实项（禁止当结论引用，详见 docs/PROVENANCE.md §4）==")
    for xid, desc in REMINDERS:
        _warn(f"{xid}: {desc}")


def check_platform_time():
    """SCHEMA §5 铁律：每个真机 JSON 顶层须有 platform + run_time（吸取 5090/A100 平台对不上、时间无记录的教训）。
    缺字段记 WARN（提醒回填），不记 FAIL，避免破坏既有全绿；新实验应一律带齐。"""
    print("\n== 平台/时间字段体检（SCHEMA §5 强制；真机 JSON 须有 platform + run_time）==")
    scanned = miss = 0
    for dirpath, _dirs, files in os.walk(RESULTS):
        for fn in files:
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            # 仅校验真机文件（含顶层 mode 字段）；模拟器(B类)无 mode，跳过
            if not (isinstance(data, dict) and "mode" in data):
                continue
            scanned += 1
            rel = os.path.relpath(fp, RESULTS)
            lack = [k for k in ("platform", "run_time") if not data.get(k)]
            if lack:
                miss += 1
                _warn(f"{rel}: 缺字段 {'+'.join(lack)} —— 旧遗留文件请回填（平台真值见 PROVENANCE M5），"
                      f"新实验落盘必须带齐 platform + run_time")
            else:
                _ok(f"{rel}: platform={data['platform']!r} run_time={data['run_time']!r}")
    if scanned == 0:
        _warn("未扫描到任何真机 JSON（含 mode 字段）")
    else:
        print(f"  （真机文件 {scanned} 个，缺平台/时间 {miss} 个）")


def check_docs_present():
    print("\n== 权威文档存在性 ==")
    for rel, note in [
        (os.path.join("results", "SCHEMA.md"), "JSON 字段字典"),
        (os.path.join("..", "docs", "PROVENANCE.md"), "数字真伪权威源"),
    ]:
        p = os.path.join(ROOT, rel)
        (_ok if os.path.exists(p) else _fail)(f"{note}: {os.path.normpath(rel)}")


def main():
    ap = argparse.ArgumentParser(description="MECC 数字一致性体检")
    ap.add_argument("--strict", action="store_true",
                    help="有 FAIL 或任何提醒即返回非零退出码（CI 门禁）")
    args = ap.parse_args()

    print("MECC 数字一致性体检 —— 权威源 docs/PROVENANCE.md\n")
    check_docs_present()
    check_claims()
    check_platform_time()
    check_reminders()

    print(f"\n== 小结 ==\n  OK={PASS}  WARN={WARN}  FAIL={FAIL}")
    if FAIL:
        print("  ✗ 存在不一致：文档/论文数字与 results/*.json 对不上，"
              "请按 docs/PROVENANCE.md 修订后再引用。")
    else:
        print("  ✓ 所有 verified 数字与实测 JSON 一致。")

    if FAIL or (args.strict and WARN):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
