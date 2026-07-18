# 实验运行规范（EXPERIMENTS Runbook）

> 本文件是 **AI agent 每次跑实验前必须读的执行手册**。
> 它定义：实验按什么**不变的语义**分级、每级「为什么跑 / 怎么跑 / 怎么判成功 / 失败怎么办」，
> 以及**会增长的维度（baseline / benchmark / 平台 / 模型）如何登记，而不是写死在流程里**。
> 每次实验都按统一格式记录（模板见 [`templates/EXPERIMENT_LOG_TEMPLATE.md`](./templates/EXPERIMENT_LOG_TEMPLATE.md)）。
>
> 先读 [`APPLICABILITY.md`](./APPLICABILITY.md)（方法何时有效）与 [`../AGENTS.md`](../AGENTS.md)（硬约束）再动手。

---

## 设计原则：可扩展，不写死

> **未来一定会有更多 baseline、更多 benchmark、更多实验平台、更多模型。**
> 因此本规范把"会变的"和"不变的"分开：

| | 不变（写进流程，长期稳定） | 会增长（登记进 §7 注册表，随时追加） |
|---|---|---|
| 分级语义 | L0=验证**逻辑**通不通、L1=展示**算法上界**、L2=证明**主战场（落 SSD）有效性** | —— |
| 判据骨架 | 「退出码 / 指标齐全 / 无损 / 命中合理 / 口径正确」 | 具体指标项、具体阈值 |
| 维度 | —— | Baselines、Benchmarks/指标、平台、模型矩阵、基线快照 |

**给 agent 的总规则：**
1. **级别由"实验回答什么问题"决定，不由"用哪个模型"决定。** 模型只是某一级的*实例*（见 §7.4 模型矩阵）。
2. **新增 baseline / benchmark / 平台 / 模型时，去 §7 对应注册表追加一行，不要改动 §1–§5 的流程文字。**
3. **任何具体数字（加速比、PPL、命中率）都可能过期。** 它们只活在 §7.5「基线快照」一处，且以 `results/raw/*.json` 为唯一事实来源；正文一律只**引用**、不**复写**。
4. 命令里的策略集合、指标集合、设备都用**变量/占位**表达，能从注册表实例化，而不是把 `ours,swapmoe,fiddler,naive` 焊死在心里。

---

## 0. 一张表看懂实验分级（按"回答什么问题"分，与模型解耦）

| 级别 | 名称 | 回答的问题（不变语义） | 典型实例（**可替换，见 §7.4**） | 设备/耗时 | 是不是性能证据 |
|------|------|------------------------|----------------------------------|-----------|----------------|
| **L0** | **冒烟测试 (smoke)** | 「编译→三级换页→所有策略→PPL」整条**逻辑链路通不通** | 微型随机 MoE（2 层 8 专家） | CPU，**秒级**，不下载 | ❌ **不是**。微型/随机模型无真实局部性，OURS 可能比 baseline 慢，属正常 |
| **L1** | **对照实验 (control)** | 算法层面的**结构性上界**（被测模型在"装得下、几乎不落 SSD"时的算法价值） | 当前：DeepSeek-V2-Lite | 看模型，分钟级 | ⚠️ **仅算法上界**，非主战场证据 |
| **L2** | **主实验 (full / real)** | MECC 在**真正主战场（连 CPU 都装不下、被迫落 SSD）**是否有效 | 当前：Mixtral-8x7B（~90GB） | GPU + 大 NVMe + 下载，小时级 | ✅ **是**，对外结论的唯一来源 |

> **铁律**
> - 报告「加速 / 有效性」只能引用 **L2**；事实数字以 §7.5 + `results/raw/` 为准。
> - **L0 永远只回答一件事：逻辑通不通。** 不把 L0 的 tok/s 写进任何结论。
> - 换了模型不代表换了级别：**判断级别看"是否被迫落 SSD"**——装得下就是 L1，装不下就是 L2（见 §7.4）。

---

## 1. L0 — 冒烟测试（agent 默认入口）

**什么时候跑**：改了 `mecc_framework/`、`e2e/`、`compiler.py`、缓存/策略逻辑之后；或本机无 GPU/大模型时验证改动没把链路改坏。

**前置条件**：只需 `torch`（CPU 版即可），无需 GPU、无需下载模型。

**命令**（策略集合从 §7.1 注册表取，此处用默认全集）：
```bash
cd mecc_package/e2e
python3 run_e2e.py --smoke --n_prompts 4 --store_root /tmp/mecc_store_smoke --out smoke_table.json
# 默认对比 §7.1 注册表中所有 active 策略；如需子集用 --policies <逗号分隔>
```

**产出**：`e2e/smoke_table.json`，结构（策略键 = §7.1 中登记的 baseline id，**数量不固定**）：
```json
{
  "mode": "smoke", "model": "smoke-tiny-moe",
  "compiled_plan": { "k_h": 2, "k_c": 3, "n_layers": 2, "n_experts": 8 },
  "results": {
    "ours": { "ppl": "exact(lossless)", "hit_pct": {"ssd": ...}, "tokens_per_s": ... }
    /* 其余 baseline 各占一键，随 §7.1 增减 */
  }
}
```

**成功判据（语义级，与具体 baseline 数量无关）**：
- [ ] 进程退出码 0，无 traceback。
- [ ] `results` 覆盖 §7.1 注册表中**所有 active 策略**（不是固定四个，而是"注册表里有几个就该有几个"）。
- [ ] 每个策略都跑出 §7.2 中标记为 L0 必采的指标（默认：`ttft_ms / tpot_ms / tokens_per_s / hit_pct`）。
- [ ] `ours.ppl == "exact(lossless)"`，且所有标注 exact 的策略 PPL 均 lossless。
- [ ] `hit_pct` 三级（hbm/cpu/ssd）≈ 100%，且 **ssd 命中 > 0**（K_H=2/K_C=3 强制溢出，证明三级换页被触发）。

**不该做的判定**：
- ⛔ 不因 `ours.tokens_per_s` 低于某 baseline 就判「方法退化」——L0 随机模型无路由局部性，慢是正常的。
- ⛔ 不把 L0 的 `speedup_vs` 写进任何对外结论。

**失败排查**：
| 现象 | 可能原因 | 处理 |
|------|----------|------|
| `ModuleNotFoundError: torch` | 未装 torch | `pip install torch`（CPU 版即可） |
| `ImportError: cannot import name 'compile_plan'` | `compiler.py` 被移动/改名 | 见 [`AGENTS.md`](../AGENTS.md) 硬约束 1，恢复位置 |
| 某策略缺失 / KeyError | §7.1 新登记的策略没在 `run_e2e.py` 实现对应分支 | 补 `POLICIES` 与 `run_policy` 分支，或先把它在 §7.1 标 `inactive` |
| `ssd` 命中为 0 | 预算没触发溢出 / store 落 tmpfs | 确认 smoke 内固定 `k_h=2,k_c=3`；`--store_root` 指向真实磁盘 |
| `ppl` 不是 lossless | 无损前向被改坏 | 检查 `measure_ppl` 与缓存读路径 |

---

## 2. L1 — 对照实验（算法上界）

**什么时候跑**：想展示「路由热度建模」的算法价值（结构性上界），或与历史主表对齐。

**前置条件**：能加载所选 L1 模型的 GPU + 模型可用（具体型号见 §7.4 模型矩阵中 `tier=L1` 的行）。

**命令**（模型/设备/指标都来自注册表实例化，下面是模板）：
```bash
cd mecc_package/e2e
python3 run_e2e.py \
  --model <§7.4 中 tier=L1 的模型 repo> \
  --model_type <对应 loader 类型> \
  --state_path <模型 snapshot 目录> \
  --store_root <NVMe 目录> \
  --hbm_budget <GB> --cpu_budget <GB> --alpha <编译用 α> \
  --prompt_len 64 --max_new_tokens 64 --n_prompts 8 \
  --policies <从 §7.1 取的策略集合> \
  --out main_table_<model>.json
```

**成功判据**：覆盖 §7.1 全部 active 策略；`ours.ppl` 为数值且与其它 exact 策略一致（无损）；§7.2 标 L1 必采指标完整。

**结论口径（必须写进记录）**：
> 该模型在本配置下 **CPU 装得下、几乎不落 SSD**，数字仅代表**算法结构性上界**，
> **不作为 MECC 主战场（落 SSD）有效性的证据**。详见 `APPLICABILITY.md` §4.2。

---

## 3. L2 — 主实验（论文主表）

**什么时候跑**：产出/复现对外主表（唯一可宣称「有效 / 加速」的实验）。

**前置条件（缺一不可）**：
- 满足所选模型显存需求的 GPU（平台见 §7.3）。
- **足够空闲 NVMe**（`--store_root` 必须真实盘，**不能 tmpfs**；按模型大小 `df -h` 自查，Mixtral 约需 ~90GB）。
- 模型已下载或可 `snapshot_download`。详细步骤见 [`../mecc_package/e2e/README_E2E.md`](../mecc_package/e2e/README_E2E.md)。

**命令**（一键脚本，模型/预算/平台用变量传入）：
```bash
cd mecc_package/e2e
MODEL=<§7.4 中 tier=L2 的模型 repo> \
STATE_PATH=<模型 snapshot 目录> \
STORE_ROOT=<足量 NVMe 目录> \
HBM_BUDGET=<GB> CPU_BUDGET=<GB> \
bash run_5090.sh full
# 产出 main_table_*.json
```

**成功判据（语义级）**：
- [ ] `mode == "real"`，`model` 为所选 L2 模型。
- [ ] 覆盖 §7.1 全部 active 策略；§7.2 标 L2 必采指标完整（端到端 TTFT/TPOT/tok·s + 所有登记 benchmark）。
- [ ] `ours` 路径**无损**，且有损 baseline 的质量指标明显更差（具体阈值见 §7.5 该模型的基线快照行）。
- [ ] `ours` 的 **SSD 命中率显著低于内存换页类 baseline**（主战场核心证据：压住冷读）。
- [ ] 报告 `speedup_vs`，并与 §7.5 同模型基线快照同量级（差异大→先查环境再下结论）。

**失败排查**：
| 现象 | 处理 |
|------|------|
| 磁盘写满 / store 在 tmpfs | 换 `STORE_ROOT` 到真实 NVMe，`df -h` 确认余量足够 |
| OOM（HBM/CPU） | 调小 `HBM_BUDGET` / `CPU_BUDGET`；确认预算 < 实际可用 |
| 下载失败 | 预先 `snapshot_download` 或指定本地 `STATE_PATH` |
| SSD 命中异常高 | 确认 `--cold_ssd`（默认开），store 是冷盘非缓存 |

---

## 4. 消融实验（优化逐项验证）

逐项叠加优化、每加一项在所选 L2 模型上跑 E2E 记录性能，脚本见
[`../mecc_package/e2e/ablation.sh`](../mecc_package/e2e/ablation.sh)（每步只改一处，产出 `*.json + *.log` 并自动汇总相对 baseline 的百分比）。

**成功判据**：每步成功产出 json/log；汇总表里相对 baseline 的目标指标变化方向与预期一致（优化为正，或解释清楚回退原因）。

---

## 5. Agent 执行 SOP（每次实验都按此走）

```
1. 读 APPLICABILITY.md + 本文件 §0，按"实验回答什么问题"确定级别（L0/L1/L2/消融），
   再去 §7.4 选模型实例、§7.3 选平台、§7.1 选策略集合、§7.2 选要采的指标。
2. 核对前置条件（设备 / 磁盘 / 模型）。不满足就降级到 L0 或如实报告阻塞，不要伪造数据。
3. 用对应级别的命令模板，按注册表把 <占位> 实例化。
4. 跑完逐条对照"成功判据"打勾；任一不满足 → 进"失败排查"，修复后重跑。
5. 用 templates/EXPERIMENT_LOG_TEMPLATE.md 填记录，存到 results/logs/
   （命名：YYYYMMDD_<level>_<model>_<简述>.md）。
6. 写结论严守口径：只有 L2 能宣称「有效/加速」；L0 只说「逻辑 PASS/FAIL」；L1 只说「算法上界」。
7. 若本次引入了新 baseline/benchmark/平台/模型 → 顺手在 §7 对应注册表补一行（见各表的"如何新增")。
```

---

## 6. 怎么扩展（给 agent 的明确许可与边界）

- **加 baseline**：在 §7.1 追加一行 + 在 `run_e2e.py` 的 `POLICIES`/`run_policy` 实现分支。**不要**回头去改 §1–§3 的判据文字（它们说的是"覆盖注册表全部 active"，自动生效）。
- **加 benchmark / 指标**：在 §7.2 追加一行，标明它在哪些级别必采。结果表（模板 §4）按列追加，不替换旧列。
- **加平台**：在 §7.3 追加一行（型号 / 显存 / 适配的级别 / 注意事项）。正文里的设备字段一律写"见 §7.3"，不焊型号。
- **加模型**：在 §7.4 追加一行，并据"是否被迫落 SSD"标 `tier=L1/L2`。**模型变了，级别语义不变。**
- **更新数字**：只动 §7.5，并附 `results/raw/*.json` 来源；正文不复写数字。

> 原则：**流程靠语义稳定，事实靠注册表生长。** agent 默认"追加"，只有改语义时才动 §0–§6。

---

## 7. 注册表（会增长的维度都登记在这里）

### 7.1 Baselines / 策略注册表

> 新增规则：追加一行；`status=active` 才会进入"成功判据"的覆盖检查；未实现分支时先标 `inactive`。

| 策略 id | 类别 | 是否无损 | 一句话 | status | 实现位置 |
|---------|------|----------|--------|--------|----------|
| `ours` | MECC 本方法 | 无损 | 编译式三级放置 + 四策略协同 | active | `e2e/run_e2e.py` |
| `swapmoe` | 内存换页 + 量化 | 有损(如2-bit) | 按需换入 + 低比特 | active | 同上 |
| `fiddler` | CPU 协同计算 | 无损 | 部分专家 CPU 上算 | active | 同上 |
| `naive` | 朴素基线 | 无损 | 无优化按需加载 | active | 同上 |
| `<新baseline>` | <类别> | <是/否> | <一句话> | active/inactive | <文件:函数> |

### 7.2 Benchmarks / 指标注册表

> 新增规则：追加一行，标明"哪些级别必采"。模板 §4 结果表按此增列。

| 指标/benchmark id | 含义 | 方向 | L0 必采 | L1 必采 | L2 必采 | 采集位置 |
|-------------------|------|------|:------:|:------:|:------:|----------|
| `ttft_ms` | 首 token 延迟 | 越小越好 | ✅ | ✅ | ✅ | run_e2e |
| `tpot_ms` | 每 token 延迟 | 越小越好 | ✅ | ✅ | ✅ | run_e2e |
| `tokens_per_s` | 吞吐 | 越大越好 | ✅ | ✅ | ✅ | run_e2e |
| `ppl` | 困惑度（质量/无损校验） | 越小越好 | ✅(lossless) | ✅ | ✅ | measure_ppl |
| `hit_pct{hbm,cpu,ssd}` | 三级命中率 | ssd 越低越好 | ✅ | ✅ | ✅ | 缓存计数 |
| `speedup_vs` | 相对各 baseline 加速比 | 越大越好 | ⛔(不可引用) | ⚠️ | ✅ | 派生 |
| `<新benchmark>` | <如 MMLU/长上下文吞吐> | <方向> | | | | <位置> |

### 7.3 实验平台注册表

> 新增规则：上新机器/集群就追加一行；正文设备字段统一写"见 §7.3"。

| 平台 id | 加速器 / 显存 | 适配级别 | 注意事项 |
|---------|---------------|----------|----------|
| `cpu-local` | 仅 CPU | L0 | 默认冒烟入口 |
| `a100-80g` | A100 80GB | L1 / L2 | 历史主表与消融常用 |
| `rtx5090` | RTX 5090 | L2 | `run_5090.sh` 默认目标 |
| `<新平台>` | <型号/显存> | <L?> | <NVMe/驱动/注意> |

### 7.4 模型矩阵（级别由"是否被迫落 SSD"决定，不由模型名决定）

> 新增规则：追加一行并按判定标 `tier`：本配置下 **CPU 装得下→L1；连 CPU 都装不下、被迫落 SSD→L2**。同一模型在不同预算下可能落不同 tier，按实际配置记。

| 模型 repo | model_type | 规模/权重 | 默认 tier | 判定依据 |
|-----------|-----------|-----------|:---------:|----------|
| `smoke-tiny-moe`（内置随机） | smoke | 2层8专家 | L0 | 仅验证逻辑 |
| `deepseek-ai/DeepSeek-V2-Lite` | deepseek | 较小 | L1 | CPU 装得下，几乎不落 SSD |
| `mistralai/Mixtral-8x7B-Instruct-v0.1` | mixtral | ~90GB | L2 | 连 CPU 都装不下，被迫落 SSD |
| `<新模型>` | <loader> | <规模> | <L1/L2> | <装得下=L1 / 落SSD=L2> |

### 7.5 基线快照（**可过期；以 `results/raw/*.json` 为唯一事实来源**）

> 这里只记"截至某次真机的参考值"，供对账（新数偏离很大先查环境）。**不要把这些数字复写进 §0–§6 的正文或对外结论里**——要引用就引用文件。

| 级别 | 模型 | 来源文件 | 快照日期 | 参考值（会变） |
|------|------|----------|----------|----------------|
| L2 | Mixtral-8x7B | `../mecc_package/results/raw/mixtral_real.json` | 见文件内 `meta` | OURS vs SwapMoE ≈ **1.33×**；OURS fp16 PPL **24.57**；SSD 命中 **17.6% vs 34.5%**。对照 PPL 36.12 的 baseline 身份为 unverified（X6），不作快照 claim |
| L1 | DeepSeek-V2-Lite | `../mecc_package/results/` 主表 | 见文件 | 无优化 ≈2.59×；+批量预取 ≈1.10×（**仅算法上界**） |
| L0 | smoke-tiny-moe | `../mecc_package/results/smoke_test.json`、`e2e/smoke_table.json` | —— | 仅作链路样例，**不可引用为性能** |
| <新> | <模型> | <results/raw/...> | <日期> | <值> |

> 跑出的新数与快照偏差很大时，先怀疑环境/配置（预算、cold_ssd、store 是否真盘），再下结论，并在记录里写清差异原因。
