# PROVENANCE.md —— 数据溯源 · Claim↔证据对照 · 矛盾登记

> **定位**：本文件是仓库**唯一的"数字真伪权威源"**。它回答三个问题：
> 1. 每个对外宣称的数字**从哪来**（哪个 JSON / 脚本 / 命令）？
> 2. 论文 / README / AGENTS 里的每条 claim **由哪份证据支撑**，证据**可信到什么级别**？
> 3. 哪些数字**彼此矛盾、尚未核实**，引用时必须回避或加注？
>
> **为什么需要**：本仓库的论文 `tex` 与 `results/*.json` 之间存在**多处数字不一致**，且 `results/` 有
> [两种不兼容 schema](../mecc_package/results/SCHEMA.md) 混放。没有这张表，agent 极易引用到错误 / 模拟 / 过时数字。
>
> **铁律 P0**：任何 agent 在论文、README、对外材料、回答里**引用任何性能数字前，必须先在本文件 §3 对照表查到它，并确认状态为 `verified`**。
> 状态为 `discrepancy` / `unverified` 的数字，**禁止当作已核实结论引用**；如必须提及，须显式标注"待核实/存在分歧"。
>
> 配套：字段语义见 [`../mecc_package/results/SCHEMA.md`](../mecc_package/results/SCHEMA.md)；
> 自动体检见 [`../mecc_package/scripts/verify_claims.py`](../mecc_package/scripts/verify_claims.py)；
> 数据口径总表见 [`AGENTS.md §4`](../AGENTS.md)。

---

## 1. 数据可信度分级（L 级）

每个数字按其**生成方式**定级，决定它能撑起多强的结论：

| 级别 | 定义 | 能宣称什么 | 例 |
|------|------|-----------|----|
| **D2 真机实测** | GPU 上真实推理跑出，`mode=="real"` 的 A 类 JSON | 可作为主结论 / 论文主表 | `mixtral_real.json` 的 1.33× |
| **D1 缓存模拟器** | 命中率 + 延迟模型算出（B 类 `workloads` JSON），非真机推理 | 仅作**趋势/上界**，必须标"模拟器" | 漂移 9.50×（`deepseek_real_e2e.json`） |
| **D0 编译期理论值** | Zipf 模型预测（`compiled_plan.*_hit_pct`）、解析公式 | 仅作理论预期，需与实测并列 | `compiled_plan.hbm_hit_pct` |
| **D-（不可用）** | 冒烟 `mode=="smoke"`、随机 gate、占位值 | **禁止当任何性能证据** | `smoke_test.json` |

> 引用时**必须带级别**。例：「漂移场景 OURS vs FluxMoE 9.50×（**D1 模拟器**，DeepSeek 合成规模 N=64）」。
> **严禁把 D1/D0 数字当 D2 真机结论**——这是本仓库最易犯、危害最大的错误。

---

## 2. 状态标签

| 状态 | 含义 | 引用规则 |
|------|------|---------|
| `verified` | 已核对到具体 JSON 字段，文档/论文与数据一致 | 可引用，须带级别与出处 |
| `discrepancy` | 至少两处口径不一致（论文 vs JSON，或文件间） | **禁止当结论**；须注明分歧，以本表"采信值"为准 |
| `unverified` | 暂未找到产生它的 JSON/脚本，或来源不明 | **禁止引用**，先溯源或重跑 |

---

## 3. Claim ↔ 证据对照表（权威）

> 列含义：**Claim**=对外宣称；**采信值**=本表裁定可引用的值；**级别**=D2/D1/D0；**证据**=具体文件:字段；**状态**。

### 3.1 主场景 — Mixtral-8×7B（落 SSD，方法真正有效区）

| # | Claim | 采信值 | 级别 | 证据（文件 : 字段） | 状态 |
|---|-------|--------|------|---------------------|------|
| M1 | OURS vs SwapMoE 加速 | **1.33×** | D2 | `raw/mixtral_real.json : results.ours.speedup_vs.swapmoe (=1.333)` | `verified` |
| M2a | OURS fp16 PPL | **24.57** | D2 | `raw/mixtral_real.json : results.ours.ppl` | `verified` |
| M2b | 对照行 PPL 及其“SwapMoE 2-bit”身份 | JSON 数值为 **36.12**；baseline 身份待核 | — | `raw/mixtral_real.json : results.swapmoe.ppl`；当前 e2e `SwapMoePolicy` 无量化调用 | `unverified`（数值存在，但“当前 SwapMoE 实现因 2-bit 得到该值”的语义无法由代码解释；见 X6） |
| M3 | SSD 命中 OURS vs Swap | **17.6% vs 34.5%** | D2 | `raw/mixtral_real.json : results.*.hit_pct.ssd` | `verified` |
| M4 | CPU 命中 OURS vs Swap | **38.0% vs 23.3%** | D2 | `raw/mixtral_real.json : results.*.hit_pct.cpu` | `verified` |
| M5 | 运行平台 | **A100 80GB** | D2 | 实验历史：先在 5090 上调试，**最终 Mixtral 主结果在 A100 上跑定**；与 `STRATEGY.md §2.2`（"A100 80GB 真实 / A100+Mixtral 物理极限"，1.33×/TPOT 14.2s/CPU 38.0% 均标 A100、HBM=50/CPU=40）一致。各真机 JSON 顶层已落 `platform="A100 80GB"` + `run_time` 字段 | `verified`（**采信 A100**；平台真值由 JSON 顶层 `platform` 字段承载，`compiled_plan.hardware=rtx5090` 仅为编译期配置串、非平台依据——见 X2） |
| M6 | OURS TPOT vs Swap | 见状态 | — | 论文 §5.5 写 **1.62×**；JSON `tpot_ms` 14226.94 vs 23092.2 ⇒ 比值 ≈ **1.62**，但 `speedup_vs.swapmoe=1.333` | `discrepancy`（TPOT 比 1.62 与综合加速 1.33 是**两个口径**，引用须指明是哪个） |
| M7 | Mixtral 单 expert 体积 | 见状态 | — | JSON `expert_mb=336`（实际张量）vs 论文 §2.1 `1407 MB`（3 矩阵理论） | `discrepancy`（口径不同，引用须注明） |

> **M6 关键澄清**：1.62× 是 **TPOT（每 token）比**，1.33× 是 `speedup_vs`（综合/吞吐口径）。二者都"真"，但**不是同一个指标**。对外默认用 **1.33×（综合）**，提 1.62× 时必须写"TPOT 比"。

| M8a | Mixtral **30/40GB 独立臂** OURS vs SwapMoE 加速（run1；K_H=2/K_C=3；**非 50/40 冻结复现**——50/40 在 A100-80g 因 ~79.1GiB 自分配 OOM，按 `MOTIVATION_EXPERIMENT_PLAN.md` §2.2 回退到明确命名的 30/40 臂） | **2.064×** | D2 | `reports/a100-mixtral-30g-1-20261011-2158/result.json : results.ours.speedup_vs.swapmoe (=2.064)`；platform=a100-80g, run_time=2026-10-11T23:39:50+08:00；`--skip-ppl`（无 PPL 可比） | `verified` |
| M8b | Mixtral 30/40GB 独立臂 OURS vs SwapMoE 加速（run2） | **1.948×** | D2 | `reports/a100-mixtral-30g-2-20261011-2343/result.json : results.ours.speedup_vs.swapmoe (=1.948)`；platform=a100-80g, run_time=2026-10-12T01:32:40+08:00 | `verified` |
| M8c | Mixtral 30/40GB 独立臂 OURS vs SwapMoE 加速（run3） | **1.744×** | D2 | `reports/a100-mixtral-30g-3-20261012-0137/result.json : results.ours.speedup_vs.swapmoe (=1.744)`；platform=a100-80g, run_time=2026-10-12T03:09:54+08:00 | `verified` |
| M8m | Mixtral 30/40GB 臂 OURS vs SwapMoE **中位数加速**（M8a/b/c 三份 ≥3 次独立真机取中位数；不挑最好一次） | **1.948×** | D2 | 派生自 `reports/a100-mixtral-30g-{1,2,3}-*/result.json` 三者 `speedup_vs.swapmoe` 中位数（2.064/1.948/1.744） | `verified` |

> **M8 臂口径说明**（关键，引用前必读）：M8a/b/c/m 来自 **30/40GB（K_H=2/K_C=3）** 的独立实验臂，是 50/40GB 冻结配置在 A100-80g OOM 后的**明确命名回退**，不构成历史 50/40 复现、也不替代 M1（M1 来自 `raw/mixtral_real.json`，为另一口径真机结果）。三次运行均 `mode=real`、`--skip-ppl`（WikiText-2 不可用，自动回退 `BUILTIN_PROMPTS`，PPL 不可对标，质量/PPL 实验已单独排队）。swapmoe 基线在 A100 上的自有加载/前向路径存在损耗（与 OURS 同输入下 swapmoe PPL 偏高，同 X6 类问题），**速度/speedup 为实测吞吐比仍有效**；质量口径未闭合前，M8 仅支撑"吞吐加速"结论，不支撑 PPL 质量结论。

### 3.2 对照场景 — DeepSeek-V2-Lite（CPU 装得下，不落 SSD，非主战场）

| # | Claim | 采信值 | 级别 | 证据 | 状态 |
|---|-------|--------|------|------|------|
| D1 | 算法上界 OURS/Swap（无优化） | **2.59×** | D2 | `results/README.md` 主表 + `main_table_5090.json`（tok/s 2.38/0.92） | `verified`（但**仅算法上界**，APPLICABILITY 已声明非主战场） |
| D2 | +批量预取后 OURS/Swap | **1.10×** | D2 | `main_table_prefetch.json`（5.58/5.06） | `verified` |
| D3 | DeepSeek e2e 真机 OURS vs Swap | **2.55×** | D2 | `main_table_5090.json : results.ours.speedup_vs.swapmoe (=2.554)` | `verified` |
| D4 | 论文表3 的 TTFT 7426/11569/8598 ms、tok/s 0.92、TTFT 1.56× | — | — | **任何 JSON 都对不上**：`main_table_5090.json` 是 tok/s 2.38、`raw/deepseek_real_e2e.json` 是 ttft 3816/7998 | `discrepancy` ⚠️ |

> **D4 严重**：论文表3 的这组数字**当前无对应实测 JSON**。在找到来源或重跑前，**论文表3 数字一律 `unverified`，禁止外引**。对外讲 DeepSeek 真机请用 D3（2.55×，来自 `main_table_5090.json`）。

### 3.3 热点漂移（缓存模拟器，D1）

| # | Claim | 采信值 | 级别 | 证据 | 状态 |
|---|-------|--------|------|------|------|
| H1 | 漂移 OURS vs FluxMoE / SwapMoE | **9.50× / 5.68×** | **D1** | `raw/deepseek_real_e2e.json : workloads[drift].speedup (vs_flux=9.502, vs_swap=5.68)` | `verified`（**模拟器**，DeepSeek 合成 N=64/expert 7.1MB） |
| H2 | 静止 OURS vs FluxMoE / SwapMoE | **6.26× / 3.99×** | **D1** | `raw/deepseek_real_e2e.json : workloads[stationary].speedup` | `verified`（模拟器） |
| H3 | 静态驻留对照在静止/漂移负载下的 SSD 访问比例 | **7.5% / 11.3%** | **D1** | `raw/deepseek_real_e2e.json : workloads[0/1].results[policy=SwapMoE].ssd_hit_pct` | `verified`（缓存模拟器；DeepSeek 合成 N=64、K_H=19、K_C=45；只支持“漂移增加该对照的 SSD 访问”这一机制观察，不是 Mixtral 真机结论） |

> **H1/H2 是 D1 模拟器值**，论文表7 标题已注明"模拟器"。引用务必带"（模拟器，DeepSeek 合成规模）"，**不可与真机加速比并列成一张表**。
> ⚠️ 易混：`real_e2e_5090.json`/`real_e2e_a100.json`/`raw/real_e2e_results.json` 也是 B 类模拟器，但 `config`（N=96 等）不同，漂移 speedup 仅 ~1.6×，**不是论文表7 的来源**，勿引用为漂移主结果。

### 3.4 延迟与 α（D2 实测 / D0 理论）

| # | Claim | 采信值 | 级别 | 证据 | 状态 |
|---|-------|--------|------|------|------|
| L1 | 三级延迟 HBM/CPU/SSD | **255.8µs / 6504µs / 789739µs** | D2 | `raw/measured_latency_5090.json : tier_latency_us`（**该延迟标尺在 5090 上测得**，文件名即平台；Mixtral 端到端主结果另在 A100，见 M5） | `verified`（延迟标尺平台=5090，与 A100 端到端结果是两个量级实验，引用三级延迟时注明"5090 标尺"） |
| L2 | per-layer α 实测区间 | **[0.63, 0.91]，均值≈0.72** | D2 | `raw/real_alpha_deepseek.json`（需核字段） | `unverified`（待核对具体字段后转 verified） |

---

## 4. 矛盾登记表（待解决，按危害排序）

| ID | 矛盾 | 涉及 | 危害 | 建议处理 |
|----|------|------|------|---------|
| **X1** | 论文表3 DeepSeek e2e（TTFT 7426/tok/s 0.92/1.56×）无对应 JSON | 论文 §5.3 vs `results/` | **高**：论文主表数字无证据 | 重跑 e2e 落盘，或改用 D3（2.55×）改写论文表3 |
| ~~X2~~ → **已澄清·已落字段** | Mixtral 平台 A100 vs rtx5090 | 论文表5/摘要(A100) vs `mixtral_real.json` | ~~中~~ → 解决 | **已采信 A100 并写入数据**：实验先 5090 后 A100，主结果在 A100 跑定（`STRATEGY.md §2.2` 佐证）。各真机 JSON 顶层已新增 `platform="A100 80GB"` + `run_time`（2026-06，回填自 mtime）承载平台真值；`compiled_plan.hardware=rtx5090` 降级为编译期配置串，不再作平台依据。 |
| X3 | 加速口径混用：1.33×(综合) / 1.62×(TPOT) | 论文 §5.5 vs JSON | 中：易被当矛盾 | 论文/文档明确标注每个数字的口径 |
| X4 | expert 体积 336MB(实测) vs 1407MB(理论) | SCHEMA vs 论文 §2.1 | 低：口径不同非错误 | 论文注明"理论体积"，JSON 注明"实际张量" |
| ~~X5~~ → **已澄清·已落字段** | `results/README.md` 顶部硬件写 A100，主表 JSON 写 rtx5090 | README(A100) vs JSON | ~~中~~ → 解决 | **README 的 A100 正确**（DeepSeek 对照场景同在 A100），各 JSON 顶层 `platform=A100` 已与之一致；以 `platform` 字段为平台真值，`hardware` 仅为编译期配置串。同 X2。 |
| **X6** | 主 JSON 将 `swapmoe.ppl=36.116` 解释为 2-bit 有损，但 e2e `SwapMoePolicy` 复用 fp16 store、无量化调用 | `raw/mixtral_real.json` / README / EXPERIMENTS vs `e2e/tiered_engine.py` / `policy_plugin.py` | **高**：速度、质量与 baseline 身份可能来自不同实现，却被合成一个主 claim | **仓库内追溯失败**：数值与“去掉 HQQ、全 fp16”的 harness 同时首次出现在初始提交 `06381a3`，无更早 revision；已提交日志也无独立 Mixtral 量化命令。M2b 保持 unverified，除非取得外部原始记录或重建独立 baseline。详见 `CONSISTENCY_AUDIT.md` CA-005/006。 |

> **处理矛盾的纪律**：发现新矛盾→**先登记到本表（标 `discrepancy`/`unverified`）**，不要静默改数字；
> 只有重跑实测拿到 D2 证据后，才可更新对照表为 `verified` 并同步改正文。

---

## 5. SOP：引用一个数字 / 新增一条 claim

**A. 引用已有数字（agent 写论文/README/回答前）**
1. 在 §3 对照表按 Claim 找到行 → 看**采信值 + 级别 + 状态**。
2. 状态 `verified` → 可引用，**带出处与级别**（如"1.33×，D2 真机，`mixtral_real.json`"）。
3. 状态 `discrepancy`/`unverified` → **不引用**，或显式标"待核实"，并不要写进结论。
4. D1/D0 数字 → 引用时**强制加注**"模拟器/理论值"。

**B. 新增一条 claim（产生了新数据）**
1. 数据落盘到 `results/`，确认其 [schema 类型](../mecc_package/results/SCHEMA.md)与 `mode`。
2. **【铁律】落盘 JSON 顶层必须带 `platform` + `run_time`**（平台真值 + ISO 8601 运行时间）——吸取「5090/A100 平台对不上、时间无记录」的教训，**平台只认 `platform` 字段，勿用 `compiled_plan.hardware`**（详见 SCHEMA §5）。
3. 在 §3 增行：Claim / 采信值 / 级别（D2/D1/D0）/ 证据(文件:字段) / **平台 + 运行时间** / 状态。
4. 记录**产生命令**（见 §6 复现台账），让数字可追溯。
5. 运行 `python3 mecc_package/scripts/verify_claims.py`，确保新数字与 JSON 一致、且平台/时间字段齐全。

---

## 6. 复现台账（数字 → 命令）

> 让每个 D2 数字可一键回溯到产生它的命令。**新增实测必须补一行**。

| 证据文件 | 产生命令（在 `mecc_package/` 下） | 级别 | 备注 |
|----------|----------------------------------|------|------|
| `raw/mixtral_real.json` | `cd e2e && python3 run_e2e.py`（真机 Mixtral，需 GPU+~90GB NVMe；细节见 `e2e/README_E2E.md`） | D2 | 主场景 |
| `main_table_5090.json` 等主表 | `cd e2e && python3 run_e2e.py`（DeepSeek，各优化档见 `results/README.md`） | D2 | DeepSeek e2e |
| `raw/measured_latency_5090.json` | `python3 scripts/measure_tiers.py` | D2 | 三级延迟 |
| `raw/deepseek_real_e2e.json` | `python3 scripts/tiered_cache.py`（缓存模拟器，DeepSeek 合成规模） | D1 | 漂移 9.50× 来源 |
| `real_e2e_*.json` / `raw/real_e2e_results.json` | `python3 scripts/tiered_cache.py`（不同 N/expert 配置） | D1 | 模拟器，非真机 |
| `raw/real_alpha_deepseek.json` | `python3 scripts/profile_deepseek.py` | D2 | α 实测 |

> 命令未经本环境重跑验证（无 GPU），如与脚本实际入参不符，请以脚本 `--help` 为准并在此订正。
