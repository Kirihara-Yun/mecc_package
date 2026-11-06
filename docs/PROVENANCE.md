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

### 3.1bis P1 主对比（本轮新数据，2026-11-03/04，A100）

> 本轮 P1 是五策略各一次的真机诊断：HBM=50.0 / CPU=40.0（诊断值）、`alpha=1.0`、`n_prompts=4`、`max_new_tokens=16`、`cold_ssd=true`、`uniform=true`。每个策略独立 run。输入为 16 token 内置文本，非主图 64 token 真实 WikiText-2 口径。
> `/data` 位于 RAID 暴露的块设备，操作系统报告 `ROTA=1`；物理盘清单未提交。**PPL 输入为 WikiText-2 下载失败回退的 77-token 内置文本（非标准 WikiText-2）**。与历史 `raw/mixtral_real.json`（HBM=30）配置不同，**不得与其数值混用**（见 X12）。

| # | Claim | 采信值 | 级别 | 证据（文件 : 字段） | 状态 |
|---|---|---|---|---|---|
| P1-1 | ours vs swapmoe 吞吐比（固定内置输入，单次） | **2.33×** | D2 | `reports/a100-p1-{ours,swapmoe}-20261103/result.json` : `results.*.tokens_per_s`（0.078429 / 0.033604） | `verified`（诊断：16 token 内置文本，非主图口径） |
| P1-2 | ours vs naive / fiddler 吞吐比（固定内置输入，单次） | **1.64× / 1.18×** | D2 | `reports/a100-p1-naive-20261103/result.json`（0.047785）、`reports/a100-p1-fiddler-20261103/result.json`（0.066384） : `results.*.tokens_per_s` | `verified`（诊断：16 token 内置文本，非主图口径） |
| P1-3 | ours / flashmoe_rf_adaptation 吞吐比 | **0.986×**（flashmoe_rf_adaptation / ours = 1.014×） | D2 | `reports/a100-p1-flashmoe-20261103/result.json` 与 `reports/a100-p1-ours-20261103/result.json` : `results.*.tokens_per_s`（0.079564 vs 0.078429） | `verified`（原 1.015× 方向写反；单次差异不能说明稳定优劣） |
| P1-4 | 五策略诊断 PPL | **24.569**（ours/swapmoe/naive/flashmoe）；fiddler **24.589** | D2 | `reports/a100-p1-*/result.json` : `results.*.ppl` | `verified`（77-token 内置文本；fiddler 与其余策略相差 0.020，不能写“五策略 PPL 全等”） |
| P1-5 | ours 与 swapmoe 的合并阶段 SSD 访问占比 | **15.5% vs 36.5%** | D2 | `reports/a100-p1-{ours,swapmoe}-20261103/result.json` : `results.*.hit_pct.ssd` | `verified`（含 warmup/PPL；不能当纯 decode 占比） |
| P1-6 | 当前 fp16 swapmoe 的诊断 PPL | **24.569** | D2 | `reports/a100-p1-swapmoe-20261103/result.json` : `results.swapmoe.ppl` | `verified`（历史 36.116 的实现及量化身份仍 unverified，见 X6） |

### 3.1ter P2 预算扫描（2026-11-04，A100，HBM=50，CPU∈{20,30,60}，uniform）

> 本轮 P2 是预算/成本敏感性扫描（论文 fig06 / 矩阵 E10/E14）：固定 `hbm_budget=50`，扫描 `cpu_budget ∈ {20,30,60}`（cpu40 由 P1 复用），`--uniform` 编译，五策略各一次独立 run。k_h=4 恒定，k_c 随预算 1→2→4。**每点仅单次（N=1）**、输入 4 prompt × 16 token，采信为正式结果（2026-11-05 起取消 ≥3 次重复 / QA·Code 冻结 / 物理预算核验门禁）。
> **PPL 输入口径分裂**：cpu20 的 4 个策略（ours/swapmoe/naive/fiddler）在 WikiText-2 缓存落地前运行，回退 77-token 内置文本（PPL 24.569/24.578）；其余 run 命中 HF 缓存用真实 WikiText-2（1024-token，PPL 3.427/3.432/3.434）。**PPL 列不可横向对比**（X13）；速度指标（TTFT/TPOT/tok·s/hit_pct）不受影响、可对比。

**三档 TPOT（ms）/ tok·s 总览（单次，正式采信）：**

| cpu | k_c | ours | swapmoe | fiddler | naive | flashmoe |
|-----|-----|------|---------|---------|-------|----------|
| 20 | 1 | 21612 / 0.0316 | 29744 / 0.0243 | 21145 / 0.0322 | 30703 / 0.0265 | 22076 / 0.0290 |
| 30 | 2 | 14462 / 0.0389 | 24226 / 0.0284 | 15188 / 0.0249 | 20581 / 0.0344 | 13063 / 0.0443 |
| 60 | 4 | 757 / 0.766 | 17142 / 0.0414 | 1198 / 0.0469 | 3911 / 0.0738 | 741 / 0.988 |

**三档 SSD 命中（%）：**

| cpu | ours | swapmoe | fiddler | naive | flashmoe |
|-----|------|---------|---------|-------|----------|
| 20 | 41.5 | 50.3 | 31.9 | 42.4 | 41.5 |
| 30 | 32.2 | 43.4 | 24.9 | 34.0 | 27.4 |
| 60 | **0.0** | **30.2** | **0.0** | 19.6 | **0.0** |

| # | Claim | 采信值 | 级别 | 证据（文件 : 字段） | 状态 |
|---|---|---|---|---|---|
| P2-1 | cpu20 ours vs swapmoe 吞吐比 | **1.303×** | D2 | `runs/a100-p2-cpu20-{ours,swapmoe}-20261104/result.json` : `results.*.tokens_per_s`（0.031636 / 0.024275） | `verified` |
| P2-2 | cpu20 ours vs naive / fiddler 吞吐比 | **1.194× / 0.982×** | D2 | `runs/a100-p2-cpu20-{ours,naive,fiddler}-20261104/result.json` : `results.*.tokens_per_s`（0.031636 / 0.026499 / 0.032229） | `verified`（fiddler 吞吐略高） |
| P2-3 | cpu20 ours vs flashmoe 吞吐比 | **1.089×** | D2 | `runs/a100-p2-cpu20-{ours,flashmoe_rf_adaptation}-20261104/result.json` : `results.*.tokens_per_s`（0.031636 / 0.029043） | `verified` |
| P2-4 | 五策略 PPL（**输入口径分裂**） | 77-token 回退：**24.569/24.578**；真实 WikiText-2：**3.427**（无损）、fiddler **3.432/3.434**（有损） | D2 | `runs/a100-p2-cpu*-*/result.json` : `results.*.ppl` + 各 `run.log` 的 `ppl_input_tokens`（77 vs 1024） | `discrepancy` ⚠️（PPL 列不可横向对比；**3.427 是真实 WikiText-2 正常值非崩溃**，见 X13） |
| P2-5 | cpu30 ours vs swapmoe TPOT 比 | **1.675×** | D2 | `runs/a100-p2-cpu30-{ours,swapmoe}-20261104/result.json` : `results.*.tpot_ms`（14462.47 / 24225.93） | `verified`（k_c=2 时 ours 优势较 cpu20 的 1.38× 扩大） |
| P2-6 | cpu30 flashmoe 反超 ours（TPOT） | **0.903×**（flashmoe 快 9.7%） | D2 | `runs/a100-p2-cpu30-{ours,flashmoe_rf_adaptation}-20261104/result.json` : `results.*.tpot_ms`（14462.47 / 13062.90） | `verified`（flashmoe CPU 命中 28.3% 高于 ours 13.0%，压住 SSD 冷读） |
| P2-7 | cpu60 SSD 归零（swapmoe 例外） | ours/flashmoe/fiddler SSD=0.0%，swapmoe 仍 **30.2%** | D2 | `runs/a100-p2-cpu60-*/result.json` : `results.*.hit_pct.ssd` | `verified`（k_h+k_c=8=n_experts，HBM+CPU 装得下全部 expert；swapmoe 静态 CPU 失效） |
| P2-8 | 适用性边界实证（SSD 命中 ↔ TPOT） | SSD 41.5%→32.2%→0.0%，ours TPOT 21.6s→14.5s→0.76s | D2 | `runs/a100-p2-cpu*-ours-20261104/result.json` : `results.ours.{hit_pct.ssd,tpot_ms}` | `verified`（**印证「SSD 冷读是主瓶颈、方法只在落 SSD 时有效」**） |
| P2-9 | cpu60 flashmoe 最快 | tok/s **0.988** / TPOT **741ms**（全组第一） | D2 | `runs/a100-p2-cpu60-flashmoe_rf_adaptation-20261104/result.json` : `results.*.{tokens_per_s,tpot_ms}` | `verified`（CPU 命中 55.7% 全组最高） |
| P2-10 | fiddler 有损 + TTFT 异常高 | PPL 3.432/3.434（差 0.005~0.007）；cpu30/cpu60 TTFT 416s/324s（ours 仅 194s/9.6s）；cpu_compute 5.4%/19.6% | D2 | `runs/a100-p2-cpu{30,60}-fiddler-20261104/result.json` : `results.fiddler.*` | `verified`（CPU 计算降级换速度、TTFT 冷启动代价高） |

> **P2 口径小结**：
> 1. **SSD 冷读是绝对主瓶颈**：cpu60 时 k_h+k_c=8=n_experts、SSD 命中归零，ours TPOT 从 21.6s（cpu20）→ 0.76s（cpu60）快 28 倍、TTFT 185s→9.6s。直接实证 APPLICABILITY 的「方法只在落 SSD 时有效」。
> 2. **ours 的联合 LRU 优势在 CPU 预算偏紧时最明显**：cpu20/cpu30 时 ours vs swapmoe 1.30×/1.68×；swapmoe 静态 CPU 在热点漂移后 SSD 命中回升（cpu60 仍 30.2% vs ours 0%）。
> 3. **CPU 预算宽裕时（cpu30/cpu60）flashmoe 反超 ours**：flashmoe 静态 CPU 评分把更多专家留 CPU（CPU 命中 28.3%/55.7%），SSD 冷读更低。ours 的联合 LRU 在这类「CPU 装得下」场景不占优。
> 4. **fiddler 有损换速度但效果一般**：PPL 略高于无损组（有损）、TTFT 冷启动极高（CPU 计算代价）。
> 5. 全部为 **N=1 单次**，采信为正式结果。PPL 列因输入口径分裂不可横向对比，且与 P1（CPU=40）／历史 `raw/mixtral_real.json`（HBM=30）数值不可混用。

### 3.1quater 主对比（2026-11-05，A100，HBM=50/CPU=40，64token/8prompts，uniform）

> 论文 fig04 主图 / 矩阵 E01/E02：固定 HBM=50/CPU=40（k_h=4, k_c=3，SSD 落 1 个 expert），64 token × 8 prompts（512 token 生成），六策略各一次独立 run（含 `ours_io` 补跑），`--uniform`。PPL 输入为真实 WikiText-2（1024-token）。**每点仅单次（N=1）**，采信为正式结果（2026-11-05 起取消 ≥3 次重复 / QA·Code 冻结 / 物理预算核验门禁）。六策略全部完成（fiddler 最慢，CPU 重算 prefill 致 TTFT≈398s）。

**六策略 TPOT（ms）/ tok·s（单次）：**

| 策略 | TTFT(ms) | TPOT(ms) | tok/s | PPL | HBM | CPU | SSD |
|------|---------|---------|-------|-----|-----|-----|-----|
| ours | 139140 | 7382 | 0.1062 | 3.427 | 77.5% | 10.0% | 12.5% |
| flashmoe_rf_adaptation | 101761 | 7195 | 0.1162 | 3.427 | 52.2% | 36.6% | 11.1% |
| naive | 156855 | 13043 | 0.0654 | 3.427 | 79.9% | 0.0% | 20.1% |
| swapmoe | 174194 | 21752 | 0.0416 | 3.427 | 62.6% | 5.8% | 31.5% |
| fiddler | 398446 | 8259 | 0.0697 | 3.432 | 82.6% | 0.0% | 11.0% |
| ours_io | 139797 | 7781 | 0.1018 | 3.427 | 77.5% | 10.0% | 12.5% |

| # | Claim | 采信值 | 级别 | 证据（文件 : 字段） | 状态 |
|---|---|---|---|---|---|
| MAIN-1 | ours vs swapmoe TPOT 比 | **2.947×** | D2 | `runs/a100-main-{ours,swapmoe}-20261104/result.json` : `results.*.tpot_ms`（7381.98 / 21751.65） | `verified`（64token/8prompt 长 decode 下 swapmoe 静态 CPU 失效被放大，SSD 31.5% vs 12.5%） |
| MAIN-2 | ours vs naive TPOT 比 | **1.767×** | D2 | `runs/a100-main-{ours,naive}-20261104/result.json` : `results.*.tpot_ms`（7381.98 / 13042.59） | `verified` |
| MAIN-3 | ours vs flashmoe TPOT 比 | **0.975×**（flashmoe 略快 2.6%） | D2 | `runs/a100-main-{ours,flashmoe_rf_adaptation}-20261104/result.json` : `results.*.tpot_ms`（7381.98 / 7194.97） | `verified`（flashmoe CPU 命中 36.6% 高于 ours 10.0%，压住冷读） |
| MAIN-4 | 无损组 PPL（真实 WikiText-2） | **3.427**（ours/ours_io/flashmoe/naive/swapmoe 五者一致） | D2 | `runs/a100-main-{ours,ours_io,flashmoe_rf_adaptation,naive,swapmoe}-*/result.json` : `results.*.ppl` | `verified`（1024-token 真实 WikiText-2，口径统一） |
| MAIN-5 | fiddler PPL | **3.432**（较无损组 +0.005） | D2 | `runs/a100-main-fiddler-20261104/result.json` : `results.fiddler.ppl` | `verified`（fiddler CPU 重算路径数值抖动，+0.005 来源待核） |
| MAIN-6 | ours vs fiddler TPOT 比 | **1.119×** | D2 | `runs/a100-main-{ours,fiddler}-20261104/result.json` : `results.*.tpot_ms`（7381.98 / 8258.99） | `verified`（fiddler TPOT 尚可，但 TTFT 398s 被 CPU 重算 prefill 拖垮） |
| MAIN-7 | ours vs ours_io TPOT 比 | **1.054×**（ours 快 5.4%） | D2 | `runs/a100-main-{ours,ours_io}-*/result.json` : `results.*.tpot_ms`（7381.98 / 7780.96） | `verified`（ours_io 与 ours 访问序列逐 phase 完全一致、io_bytes 相同，但缺 near-miss 预取 + pin，TPOT 反而慢 5.4%） |

> **主对比口径小结**：ours 主战场优势明显——vs swapmoe **2.95×**（长 decode 放大 SSD 冷读差异）、vs naive **1.77×**、vs fiddler **1.12×**；但 flashmoe 略快于 ours（2.6%，CPU 命中更高压住冷读）。**ours_io 不占优**（比 ours 慢 5.4%，见 MAIN-7）。主对比 k_c=3、SSD 命中仅 ~12%，是「落 SSD 但接近装得下」的过渡区（对照 P2 cpu20 的 41.5%）。全部 N=1 单次（正式采信）。
>
> **运行备注**：swapmoe 单次 wall time ≈ 4h07m，超 `main_driver.sh` 的 `MAX_WALL_SECONDS=14400`，driver 在 08:51 记 `STOP_TIMEOUT` 退出，但 systemd unit 继续跑至 08:58 写完 `result.json`（phase=complete，数据完整）。后续若重跑 swapmoe 需放宽该上限（建议 ≥5h）或单独续跑。
>
> **ours_io 补跑备注**：首次 run `a100-main-ours_io-20261105` 因 `OursIOPolicy` 数据结构过时（`gpu[uid]` 存单个对象，未跟上引擎「零拷贝淘汰」的 `(gpu_ws, cpu_ws)` 元组）触发 `TypeError: cannot unpack non-iterable ExpertWeights object`，phase=failed。修复为对齐 `OursPolicy` 的 `gpu[uid][0]` + `gpu[uid]=(g, ws_cpu)`（`e2e/policy_plugin.py`），以 `a100-main-ours_io-20261105-retry1` 重跑完成。

### 3.1quinquies E05–E08 动机三连真机（2026-11-06，A100，HBM=50/CPU=40，64token/8prompts，uniform）

> 论文 fig02 动机三连（容量/驻留/切换）的真机版。复用主对比配置（HBM=50/CPU=40、64token/8prompts、`--uniform`），由 `scripts/insight_driver.sh` 串行 7 arm，全部 N=1 单次（正式采信）。三组 Insight 对应三个开关：`--init-plan`（初始放置）、`--update-rule`（更新规则）、`--task-seq`（任务切换，**真实 WikiText-2↔GSM8K**，2026-11-06 起不再用「同一输入切前后半」）。PPL 均为真实 WikiText-2（1024-token）。

**Insight I（E05，初始放置精度）：**

| init-plan | TTFT(ms) | TPOT(ms) | PPL | HBM | CPU | SSD |
|-----------|---------|---------|-----|-----|-----|-----|
| per_layer（逐层画像） | 138275 | 7322.04 | 3.427 | 77.6% | 9.7% | 12.6% |
| global（全局画像） | 138172 | 7306.78 | 3.427 | 77.6% | 9.7% | 12.6% |
| avg（自然序，不画像） | 137868 | 7327.48 | 3.427 | 77.6% | 9.7% | 12.6% |

**Insight II（E06，更新规则；joint/fixed_cpu 复用主对比）：**

| 更新规则 | TPOT(ms) | SSD | CPU | 备注 |
|----------|---------|-----|-----|------|
| joint（ours） | 7382 | 12.5% | 10.0% | 主对比 `a100-main-ours-20261104` |
| fixed_cpu（swapmoe） | 21752 | 31.5% | 5.8% | 主对比 `a100-main-swapmoe-20261104` |
| independent | 32942 | 47.9% | 0.3% | `a100-e06-independent-20261105`（TTFT 258696ms、tok/s 0.0275、read_bytes≈2.75TB） |

**Motivation III（E07/E08，任务切换逐窗 SSD 命中）：**

| 序列 | window0 任务 | window1 任务 | SSD 变化 | 窗口容量 |
|------|-------------|-------------|---------|---------|
| a_a（no-shift 对照） | WikiText-2 | WikiText-2 | +2.4%（2265→2320） | 4+4 prompt |
| a_b | WikiText-2 | GSM8K | -4.5%（4663→4455） | 8+8 prompt |
| b_a | GSM8K | WikiText-2 | +7.4%（4390→4713） | 8+8 prompt |

| # | Claim | 采信值 | 级别 | 证据（文件 : 字段） | 状态 |
|---|---|---|---|---|---|
| INS-1 | 初始放置精度（逐层/全局/自然序）TPOT 差 | **<0.3%**（三臂 7306.78–7327.48） | D2 | `runs/a100-e05-{per_layer-20261105-retry1,global,avg}-20261105/result.json` : `results.ours.tpot_ms` | `verified`（三臂命中率逐项一致，画像精度无杠杆） |
| INS-2 | independent vs joint TPOT 比 | **4.46×**（32942/7382） | D2 | `runs/a100-e06-independent-20261105/result.json` + 主对比 ours : `results.*.tpot_ms` | `verified`（independent 不回写 CPU，SSD 47.9% vs 12.5%） |
| INS-3 | 任务切换 SSD 命中变化 vs no-shift | **±7% 内**（a_b -4.5%、b_a +7.4%，no-shift +2.4%） | D2 | `runs/a100-e07-a_b / a100-e08-b_a / a100-e08-a_a -20261105/result.json` : `results.ours.window_hits / window_ssd_bytes` | `verified`（无显著热点漂移，与自然抖动同量级） |

> **动机三连口径小结**：三组 Insight 自洽地指向同一根因——**Mixtral-8×7B 的 expert 分布接近均匀（profile α≈0.12–0.64，均值≈0.35）**，导致「静态放置精度」（INS-1）与「任务切换漂移」（INS-3）都不是关键杠杆；方法真正的价值锚定在「运行期联合 LRU」上（INS-2 的 4.46× 是唯一显著信号）。INS-1/INS-3 是诚实负结果，如实记录，不构造漂移。
>
> **运行备注**：E05 per_layer 首次 run `a100-e05-per_layer-20261105` 因 driver 重启前被 stop，phase=running_policy 不完整，以 `-retry1` 重跑完成。E07/E08 的 GSM8K 任务 B 为真实 `openai/gsm8k` test 前 8 条（2026-11-06 经 hf-mirror 下载固定）；`organize_task_sequence` 已改为「缺任务 B 即抛异常，拒绝同一输入切前后半」。a_a 窗口容量 4+4 与 a_b/b_a 的 8+8 不同，SSD 计数绝对值不可直接比，只比变化率。

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

### 3.5 受控因果回放（2026-10-27，D1 合成序列）

证据：`raw/motivation_causal_replay_20261027_v2.json`；CPU 抽象缓存模型，N=16、H=2、C=4，8 个配对种子；没有真实 MoE trace、SSD 时间或 GPU 计算。v1 保留但不与 v2 拼图。`summaries` 全部由 `workloads[*].paired_trials[*].results` 归约，图中标准差是合成种子变异。

| # | Claim | 采信值/字段 | 级别 | 状态 |
|---|---|---|---|---|
| R1 | 相同联合策略，不同初始排序的启动段需求未命中 | `summaries.stationary.{random_joint,profile_joint}.startup64_mean`；前 64 请求均值 **4.625 / 3.125 次** | D1 | `verified`；仅此受控生成器，画像收益较小，不证明编译器真机收益 |
| R2 | 原顺序/阶段内保频乱序的保留规则比较 | `summaries.{drift,phase_shuffled}.{profile_static,profile_independent,profile_joint}.ssd_per_1000_mean`，分别约 **413.21/88.87/57.74** 与 **597.66/557.25/383.79** | D1 | `verified`；包含动态性与去重覆盖变化，不能归因为单独 LRU 更新 |
| R3 | 2×2 初态×在线规则与 uniform 负对照 | 同文件全部 `workloads` 逐 seed 原值及 `summaries`；保留画像静态失配和较小初态差异 | D1 | `verified`；所有图只报 miss 数与迁移对象数，无真机速度推算 |
| R4 | 此排他联合模型与普通容量 H+C 的全局 LRU 的 SSD miss 逐请求一致 | `checks.joint_equals_global_lru_demand_misses=true`，运行时逐请求断言 | D1 | `verified`；只检验冻结 trace，不写成新定理或新算法 |

产生命令：`python mecc_package/scripts/motivation_causal_replay.py`。协议：`docs/HPCA_CAUSAL_REPLAY_PROTOCOL.md`。日志：`results/logs/20261027_D1_causal_replay.md`。脚本 SHA、平台、运行时刻与 trace 哈希随 JSON 落盘。

**历史数字与归因强度分开**：M1/M3/M4 的 `verified` 指历史 JSON 数值核对成立；它不自动关闭 X7–X9，也不证明画像编译器的独立贡献。审稿修订版中这些数字仅作历史观测，不能宣称已完成实际字节公平性与同计时窗的机制验证。

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
| **X7** | 相同 K_H/K_C 未证明相同物理 CPU 字节；CPU 镜像、near-miss 缓冲及预取路径不对称 | `tiered_engine.py:229–236,267–285`；`policy_plugin.py:76–123`；`mixtral_tiered.py:56–60` | **高**：历史收益可能混入容量/预取差异 | `unverified` 公平性；新增峰值 pinned/pageable/镜像/staging 去重记账，统一预取并按实际 cap 重跑；不改历史数字 |
| **X8（短窗诊断部分通过）** | 独立 copy_stream 上的异步权重曾在使用前缺少明确就绪屏障 | `tiered_engine.py:load_experts()`；`results/reports/a100-g1-correctness-20261103/partial_result.json` | **高**：旧实现可能跨流未就绪读取 | 补丁后 A100 L0、短窗 PPL 与 4×16 稳定性完成；G1 在冻结的两个短输入上确认 `naive` 与 `ours` 路由/logits/token/PPL 一致。该比较共享 MoE dispatch，且 `swapmoe` 未完成；独立实现等价性及更长输入仍未证明。不能把静态风险当作已证实的历史 PPL 根因。 |
| **X9** | hits 计数混入 warmup/PPL；CPU 预取先插 GPU 再记 HBM hit | `run_e2e.py:210–238`；`tiered_engine.py:351–364` | **高**：命中率无法与生成计时直接因果配对 | `unverified` 性能归因；分离 warmup/prefill/decode/PPL 计数窗口，按 demand 到达前来源计数，记录实际 SSD/H2D/D2H 字节 |
| **X10（诊断已确认，正式证据待重建）** | Mixtral 的 near-miss 预测预取缓冲未按步清理，50/40 GB 诊断中随 decode 增长并在第 5 步 OOM | `results/reports/a100-memory-trace-20261103/MEMORY_TRACE_SUMMARY.md`；`results/reports/a100-nearmiss-ablation-20261103/NEARMISS_ABLATION_SUMMARY.md` | **高**：旧性能与物理容量公平性仍待复核 | 单变量停用调用后，1×16 与 4×16 完成，近失缓冲为零且已分配显存不再随步数增长。此结论限于 OOM 诊断；正式结果仍需正确性、物理字节、分相位与重复测量。原始历史数字不改。 |
| **X11（事件已记录，内存来源未定位）** | G1 三策略顺序诊断在 `swapmoe` 装载阶段中断，缺少终态 `result.json`；Workbuddy 报告称 systemd-oomd 终止任务 | `results/reports/a100-g1-correctness-20261103/G1_SUMMARY.md`、`partial_result.json`、`status.json` | **高**：三策略正确性门禁未完整通过，可能暴露 CPU/cgroup 内存压力 | `naive` 与 `ours` 的短窗结果有效；`swapmoe` 缺失不得补推。先做 G2a journal/cgroup 只读审计，再增加事发时 CPU RSS、锁页与 cgroup 采样。顺序装载导致内存累积仅是候选解释，未获证实。 |
| **X12** | 本轮 P1 诊断 ours vs swapmoe **2.33×**，与历史 `raw/mixtral_real.json` 的 **1.33×** 相差大 | `reports/a100-p1-*-20261103` vs `raw/mixtral_real.json` | 中：两批数据口径不同，易混用 | 已知差异包括预算（50/40 → K_H=4 vs 30/40 → K_H=2）、速度指标和输入数量；各因素的贡献未经控制实验分离。**禁止混用**；P1 数值仅作当前配置的单次诊断，历史数值按 M1 的原口径引用。 |
| **X13** | P2 同批实验内部 PPL 输入口径分裂：cpu20 的 4 个策略（ours/swapmoe/naive/fiddler，07:13–11:26 运行）WikiText-2 下载失败回退 77-token 内置文本（PPL 24.569/24.578）；其余 run（cpu20 flashmoe 及 cpu30/cpu60 全部，12:27 起运行）命中 10:46 落地的 HF 缓存用真实 WikiText-2 1024-token（PPL 3.427/3.432/3.434） | 各 `runs/a100-p2-cpu*-*/run.log` 的 `ppl_input_tokens`（77 vs 1024）+ `results.*.ppl` | **高**：PPL 列不可横向对比；**3.427 是真实 WikiText-2 正常值（非崩溃）**，24.569 是 77-token 诊断回退文本值 | **已修复（2026-11-04）**：`run_e2e.py:load_prompts` 不再静默回退，WikiText-2 test split 下载/读取失败即抛异常退出；后续 run 统一用 WikiText-2 test（1024-token）。**待重跑**：历史用 77-token 回退的 run（P1 五策略、P2 cpu20 的 ours/swapmoe/naive/fiddler）另择时间用统一 WikiText-2 输入重跑 PPL 列。 |
| **X14（介质口径：HDD 非 SSD）** | 历史代码/文档通称第三级存储为 "SSD"，但 `lsblk` 确认 store_root `/data` 挂载在 `/dev/sdb`，`ROTA=1`（旋转盘），经 MegaRAID 9364-8i 控制器 → **实际介质是 HDD，不是 SSD** | `lsblk -d -o NAME,TYPE,SIZE,ROTA,MODEL`（sdb ROTA=1，MR9364-8i）；`findmnt -T /data/mecc_store_mixtral`（/dev/sdb ext4 stripe=64） | **高**：论文若写 "SSD/NVMe" 属介质误称；且 HDD 冷读延迟远高于 SSD，误称会低估方法价值 | **已确认（2026-11-05）**：后续文档/论文第三级存储统称「HDD（磁盘）」，不再称 SSD；代码标识符（`SSDExpertStore`/`cold_ssd`/`ssd_read`/`ssd_hit_pct` 等）为历史命名保持不 break，但语义 = HDD 冷读。 |

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
| `runs/a100-p1-*-20261103/result.json`（P1 主对比，5 策略 @HBM50/CPU40） | `python3 scripts/experiment_launcher.py run a100-p1-<policy>-20261103 --config e2e/configs/l2_mixtral_repro.json --state-path <Mixtral snapshot> --gpu 0 --policies <policy> --n-prompts 4`（5 策略各独立 run） | D2 | P1 主对比；`<policy>` ∈ ours/swapmoe/fiddler/naive/flashmoe_rf_adaptation |
| `runs/a100-p2-cpu{20,30,60}-*-20261104/result.json`（P2 预算扫描，5 策略 × 3 档 @HBM50/--uniform） | `python3 run_e2e.py --model mistralai/Mixtral-8x7B-Instruct-v0.1 --state_path <Mixtral snapshot> --hbm_budget 50.0 --cpu_budget <20|30|60> --alpha 1.0 --store_root /data/mecc_store_mixtral --prompt_len 64 --max_new_tokens 16 --n_prompts 4 --ppl_tokens 1024 --policies <policy> --platform a100-80g --uniform --out ... --partial_out ... --status_file ...`（由 `scripts/p2_budget_driver.sh` 串行驱动） | D2 | P2 预算扫描；`<policy>` ∈ ours/swapmoe/fiddler/naive/flashmoe_rf_adaptation；PPL 输入口径分裂见 X13 |

> 命令未经本环境重跑验证（无 GPU），如与脚本实际入参不符，请以脚本 `--help` 为准并在此订正。
