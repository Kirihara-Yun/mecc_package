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
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # mecc_package/
REPO_ROOT = os.path.dirname(ROOT)
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
    ("M3a", "raw/mixtral_real.json", "results.ours.hit_pct.ssd", 17.6, 0.1,
     "Mixtral OURS SSD 命中 17.6%"),
    ("M3b", "raw/mixtral_real.json", "results.swapmoe.hit_pct.ssd", 34.5, 0.1,
     "Mixtral SwapMoE SSD 命中 34.5%"),
    ("M4a", "raw/mixtral_real.json", "results.ours.hit_pct.cpu", 38.0, 0.1,
     "Mixtral OURS CPU 命中 38.0%"),
    ("M4b", "raw/mixtral_real.json", "results.swapmoe.hit_pct.cpu", 23.3, 0.1,
     "Mixtral SwapMoE CPU 命中 23.3%"),
    # --- 主场景 Mixtral 30/40GB 独立臂（D2 真机，A100-80g；50/40 冻结配置 OOM 后的明确命名回退臂，K_H=2/K_C=3）---
    ("M8a", "reports/a100-mixtral-30g-1-20261011-2158/result.json", "results.ours.speedup_vs.swapmoe", 2.064, 0.01,
     "Mixtral 30/40GB 臂 OURS vs SwapMoE 2.064× (run1)"),
    ("M8b", "reports/a100-mixtral-30g-2-20261011-2343/result.json", "results.ours.speedup_vs.swapmoe", 1.948, 0.01,
     "Mixtral 30/40GB 臂 OURS vs SwapMoE 1.948× (run2)"),
    ("M8c", "reports/a100-mixtral-30g-3-20261012-0137/result.json", "results.ours.speedup_vs.swapmoe", 1.744, 0.01,
     "Mixtral 30/40GB 臂 OURS vs SwapMoE 1.744× (run3)"),
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
    ("H3a", "raw/deepseek_real_e2e.json", "workloads.0.results.1.ssd_hit_pct", 7.5, 0.1,
     "静态对照静止负载 SSD 访问 7.5%（模拟器）"),
    ("H3b", "raw/deepseek_real_e2e.json", "workloads.1.results.1.ssd_hit_pct", 11.3, 0.1,
     "静态对照漂移负载 SSD 访问 11.3%（模拟器）"),
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
    ("X6", "mixtral_real.json 的 swapmoe.ppl=36.116 数值存在，但当前 e2e SwapMoePolicy 为 fp16、无量化调用；2-bit baseline 身份未核实，禁止合成主 claim"),
    ("X5", "results/README.md 顶部硬件 A100 [已澄清，正确] —— 各 JSON 顶层 platform=A100 已与之一致；以 platform 字段为平台真值"),
]

# 正式入口/论文材料。PROVENANCE 与审计文档故意描述禁用 claim，不参与扫描。
TEXT_CLAIM_FILES = [
    "AGENTS.md",
    "README.md",
    "docs/APPLICABILITY.md",
    "docs/EXPERIMENTS.md",
    "docs/PAPER_WRITING.md",
    "docs/THEORY.md",
    "mecc_package/README.md",
    "mecc_package/STRATEGY.md",
    "mecc_package/paper/mecc_paper.tex",
    "mecc_package/paper/mecc_paper_example.md",
]


def _text_claim_violations(rel, text):
    """返回高风险文本 claim，规则对应 CONSISTENCY_AUDIT CA-001/003/005/006。"""
    violations = []
    for lineno, line in enumerate(text.splitlines(), 1):
        lower = line.lower()
        # M5: 主结果平台已经裁定为 A100。仅拦明确把 Mixtral 主结果归到 5090 的句子。
        if ("mixtral" in lower and "5090" in lower
                and "a100" not in lower
                and not any(word in lower for word in ("勿", "不得", "非平台", "仅为"))
                and any(word in lower for word in ("主结果", "主场景", "来源"))):
            violations.append((lineno, "M5_PLATFORM",
                               "Mixtral 主结果平台应为 A100 80GB，不得写 RTX 5090"))
        # X6: 当前仓库不能把 36.12 归因给 SwapMoE 2-bit。
        if ("36.12" in line and "swapmoe" in lower
                and re.search(r"2\s*[- ]?bit|有损", lower)
                and not re.search(r"待核|unverified|无法|禁止", lower)):
            violations.append((lineno, "X6_BASELINE_IDENTITY",
                               "36.12 的 SwapMoE/2-bit baseline 身份未核实"))
        # X3: 1.62x 只能作为 TPOT 比出现。
        if (re.search(r"1\.62\s*[×x]", line)
                and "tpot" not in lower and "每 token" not in lower):
            violations.append((lineno, "X3_SPEEDUP_SCOPE",
                               "1.62× 必须明确标注为 TPOT（每 token）比"))
        if ("deepseek" in lower and "主实验" in line
                and not any(word in lower for word in ("非主", "不是主"))):
            violations.append((lineno, "W2_DEEPSEEK_SCOPE",
                               "DeepSeek-V2-Lite 只能标 L1 对照，不能称主实验"))
        if (re.search(r"联合.*lru.*(不低于|普遍.*优)", lower)
                and not any(word in lower for word in
                            ("反例", "推翻", "已被", "已反驳", "refuted", "无普遍",
                             "不具有", "不得", "不能", "不构成"))):
            violations.append((lineno, "TH006_REFUTED",
                               "TH-006 普遍包含性已被反例推翻"))
        if (rel.endswith("mecc_paper.tex")
                and (re.search(r"边际收益\s*=\s*.*边际收益", line)
                     or re.search(r"独立计算每层.*最优.*k_?\{?h", lower)
                     or ("theorem" in lower and "共享预算" in line
                         and not any(word in lower for word in
                                     ("不覆盖", "不适用", "不可兑换"))))):
            violations.append((lineno, "TH004_SCOPE",
                               "TH-004 仅证明不可兑换的独立 tier 容量上限下按秩填满"))
        if (rel.endswith("mecc_paper.tex")
                and re.search(r"7,?426|11,?569|8,?598|1\.56\s*[×倍]", line)
                and not any(word in lower for word in ("todo", "x1", "d4", "不可追溯"))):
            violations.append((lineno, "X1_UNVERIFIED_TABLE",
                               "DeepSeek 旧表 X1/D4 数字无对应 JSON"))
    return violations


def check_text_claims():
    print("\n== 高风险文本 claim 体检（正式入口与论文材料）==")
    checked = total_violations = 0
    for rel in TEXT_CLAIM_FILES:
        path = os.path.join(REPO_ROOT, rel)
        if not os.path.exists(path):
            _fail(f"文本扫描目标缺失: {rel}")
            continue
        checked += 1
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        violations = _text_claim_violations(rel, text)
        total_violations += len(violations)
        for lineno, rule, desc in violations:
            _fail(f"{rule}: {rel}:{lineno} —— {desc}")
    if checked and total_violations == 0:
        _ok(f"{checked} 个正式文本通过平台/加速口径/baseline 身份规则")


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
    check_text_claims()
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
