# AGENTS.md —— AI 协作者入口指南

> 本文件是 **AI coding agent 进入本仓库时应读的第一份文档**。
> 它告诉你：这个仓库是什么、核心约束是什么、文件在哪、改代码时绝对不能踩的雷。
> 人类读者请改看根 [`README.md`](./README.md) 与 [`docs/PROMPTS.md`](./docs/PROMPTS.md)。

---

## 1. 这是什么项目（30 秒理解）

**MECC（MoE Expert Cache Compiler）** 是一个面向 DAC 的科研 + 工程项目：为 MoE 大模型推理设计
**三级（HBM → CPU pinned → SSD）无损 expert 缓存**，由「编译器静态放置 + 运行期联合动态 LRU」驱动。

**核心论点（务必内化）**：
> 方法**只在「连 CPU 内存都装不下整个模型」时才有价值** —— 此时部分 expert 被迫落 SSD，
> 三级缓存才解决真实瓶颈。判断条件只有一个：**`模型 expert 总量 > 可用 CPU 内存`**。
> 详见 [`docs/APPLICABILITY.md`](./docs/APPLICABILITY.md)，回答任何「是否适用 / 效果」问题前**必须**先读它。

**主验证模型**：Mixtral-8x7B（~90GB，连 CPU 都装不下）。DeepSeek-V2-Lite 只是**对照场景**（CPU 装得下，不落 SSD，不能当主战场证据）。

---

## 2. 仓库地图

```
.
├── AGENTS.md                  # ← 你在这里
├── README.md                  # 人类入口（项目总览 + 导航）
├── docs/                      # 文档体系（AI + 人类共用）
│   ├── APPLICABILITY.md       # ★ 适用性边界与决策树（最重要的科研定位）
│   ├── RESEARCH_NARRATIVE.md  # ★ 统一科研叙事（三级缓存模型 → MoE 实例化）
│   ├── EXPERIMENTS.md         # ★ 实验运行规范（每次跑实验前必读：L0冒烟/L1对照/L2主实验）
│   ├── OPTIMIZATION.md        # ★ 优化指导规范（做任何优化前必读：算法/工程/评测三维度 + 注册表）
│   ├── THEORY.md              # ★ 数学论证与形式化（方法数学化 + 证明规范 + 命题注册表）
│   ├── PROVENANCE.md          # ★ 数字真伪权威源（引用任何数字前必读：claim↔证据对照 + 矛盾登记 + 可信度分级）
│   ├── PAPER_WRITING.md       # ★ 论文写作指导（写论文/对外材料前必读：逐章节SOP + 三诚实门禁 + 章节注册表 + 投稿检查清单）
│   ├── ARCHITECTURE.md        # 架构、模块、数据流、四策略
│   ├── GLOSSARY.md            # 术语表（α / K_H / K_C / TTFT / TPOT...）
│   ├── PROMPTS.md             # 人类用提示词库（多情景）
│   └── templates/
│       └── EXPERIMENT_LOG_TEMPLATE.md  # 每次实验的统一记录模板
│
├── mecc_package/              # 主项目
│   ├── README.md              # 详细结构与快速开始
│   ├── STRATEGY.md            # 四策略全量报告 + 实验结论
│   ├── tuning_log.md          # 调参历程（含失败记录，注意与最新结论对齐）
│   ├── compiler.py            # 编译器（库形式，被 e2e/ 与 runtime_spec 引用）★勿移动
│   ├── compile.py             # 编译器（standalone CLI 全功能版）
│   ├── runtime_spec.py        # 运行时 API 规范 + 可跑伪代码
│   ├── mecc_framework/        # 核心库：base/ cache/ layers/ models/ benchmark/
│   ├── e2e/                   # 正式端到端 harness（扁平 import，依赖根级 compiler.py）
│   ├── scripts/               # 离线脚本：profiling / 延迟测量 / 缓存模拟
│   ├── results/               # 实验数据（主表 + raw/ 中间产物 + logs/）
│   │   └── SCHEMA.md          # ★ results JSON 字段字典（两种不兼容 schema：真机 e2e vs 缓存模拟器）
│   ├── paper/                 # 论文：mecc_paper.tex（原稿）+ mecc_paper_example.md（★按 PAPER_WRITING 规范写的示例论文/活教材）
│   ├── archive/ third_party/
│   └── ...
└── mecc_ablation/             # 硬件优化消融（Mixtral A100 真实端到端）
    ├── scripts/ configs/ logs/
```

入口建议：理解科研故事→`docs/RESEARCH_NARRATIVE.md`；理解方法→`docs/ARCHITECTURE.md`；理解代码→`mecc_package/mecc_framework/`；**跑任何实验前→必读 `docs/EXPERIMENTS.md`**（L0/L1/L2 分级、命令、判据、记录模板）；**做任何优化前→必读 `docs/OPTIMIZATION.md`**（算法/工程/评测分维度、收益证据落在哪级、优化注册表）；**做任何数学论证 / 形式化证明前→必读 `docs/THEORY.md`**（方法已数学化、证明级别与状态、命题注册表）；**引用任何性能数字 / 写论文或对外材料前→必读 `docs/PROVENANCE.md`**（claim↔证据对照、矛盾登记、可信度分级 D2/D1/D0），并跑 `python3 mecc_package/scripts/verify_claims.py` 做一致性体检；**动手写论文（摘要/引言/背景/motivation/insight/framework/method/experiment/讨论总结/引用）前→必读 `docs/PAPER_WRITING.md`**（逐章节写作 SOP + 三诚实门禁 + 投稿检查清单），可对照示例论文 `mecc_package/paper/mecc_paper_example.md` 照葫芦画瓢。

---

## 3. 硬约束（改动前必须遵守，违反会破坏运行）

1. **`mecc_package/compiler.py` 必须留在 `e2e/` 的父目录（即 `mecc_package/` 根级）**。
   `e2e/compile_config.py` 通过 `sys.path.insert(0, 父目录)` + `from compiler import ...` 引用它。移动它会断 e2e。
2. **`e2e/` 内部是扁平 import**（同目录直接 `import tiered_engine` 等），不要改成包相对 import，也别把 e2e 文件拆到子目录。
3. **`scripts/concurrent_tiered_cache.py` 依赖同目录 `scripts/real_tiered_cache.py`**，两者必须同目录。
4. **不要删除任何 `results/` 下的实验数据**（含 `*_old.json` 历史备份）——这些是论文证据。
5. **`compiler.py`（库）与 `compile.py`（CLI）是两个文件，别合并**，除非用户明确要求。
6. 改文档时**叙事必须与 `docs/APPLICABILITY.md` 一致**：别把 DeepSeek 当主战场，别声称小模型上方法有效。

---

## 4. 真实数据口径（引用结果时用这些，别编）

> ⚠️ **下表只是速查。引用任何数字前必须先查 [`docs/PROVENANCE.md`](./docs/PROVENANCE.md)** 确认其**可信度级别（D2 真机 / D1 模拟器 / D0 理论）与状态（verified / discrepancy / unverified）**；
> `results/` 下 JSON 有[两种不兼容 schema](./mecc_package/results/SCHEMA.md)，命名相似但真假/规模不同，极易误引。

| 场景 | 数据来源 | 关键数字 |
|------|----------|---------|
| **主场景** Mixtral-8x7B（落 SSD） | `mecc_package/results/raw/mixtral_real.json` | OURS vs SwapMoE **1.33×**（D2）；OURS PPL **24.57（fp16）**；SSD 命中 17.6% vs 34.5%。对照行 PPL 36.12 的“2-bit/SwapMoE”身份为 `unverified`（PROVENANCE X6），暂禁合成质量 claim |
| 对照 DeepSeek-V2-Lite（不落 SSD） | `mecc_package/results/` 主表 | 无优化 2.59×；+批量预取后 1.10×（仅算法上界，非主战场） |
| 热点漂移 9.50×/5.68× | `raw/deepseek_real_e2e.json` | **D1 缓存模拟器**（DeepSeek 合成规模），引用须标"模拟器"，**勿当真机** |

> 已知矛盾（**禁止当结论引用**，详见 PROVENANCE §4）：论文表3 DeepSeek e2e 数字无对应 JSON（unverified）；加速口径 1.33×(综合) vs 1.62×(TPOT)；主 JSON 的 36.12 对照 PPL 无法由当前 fp16 `SwapMoePolicy` 解释（X6）。Mixtral 平台已裁定为 A100，`compiled_plan.hardware=rtx5090` 仅为历史配置串。

---

## 5. 验证与自检（改完代码怎么确认没坏）

```bash
# A. import 链完整性（无需 GPU；报 torch 缺失属正常，说明本地模块已找到）
cd mecc_package/e2e && python3 -c "import compile_config"          # 验证 e2e → compiler 跨目录引用
cd mecc_package      && python3 -c "import runtime_spec"           # 验证 runtime_spec → compiler
cd mecc_package/scripts && python3 -c "import concurrent_tiered_cache"  # 验证 scripts 内部链

# B. 全链路逻辑 smoke（CPU，秒级，不下载模型）—— 即 L0 冒烟测试
cd mecc_package/e2e && python3 run_e2e.py --smoke
#   ↑ 这是 agent 的默认验证入口；它只验证「逻辑链路通不通」，
#     绝不能拿它的 tok/s 当性能/加速证据。完整规范见 docs/EXPERIMENTS.md。

# C. 适用性 / 环境自检
python3 mecc_package/scripts/check_env.py        # 见第 4 个 todo 产出

# D. 数字一致性体检（引用/发布数字前必跑）—— 核对文档数字与 results/*.json 是否对得上
python3 mecc_package/scripts/verify_claims.py    # 全绿才可对外引用；详见 docs/PROVENANCE.md
```

---

## 6. 改动准则

- **最小侵入**：优先 `replace_in_file` 做定向编辑；不要大规模重写用户的研究代码或重排实验数据。
- **优化先归类**：做任何优化（算法/工程/评测）前读 `docs/OPTIMIZATION.md`——先判断维度以确定"收益在哪级验证、能写什么结论"，单变量改动，可解释才保留，并在其 §6 注册表登记。
- **叙事一致**：任何涉及「方法有效性 / 主场景 / 结果数字」的措辞，都以 `docs/APPLICABILITY.md` 与第 4 节数据为准。
- **保守移动**：移动文件前先 grep 引用（`import`、`sys.path`、`.sh`、`.md`），确认无断链。
- **科研诚实**：区分「实测数据」与「理论/伪代码/模拟」；smoke 用随机 gate≈均匀访问，**不体现加速**，别拿它当性能证据。
- **理论诚实**：做任何数学论证按 `docs/THEORY.md` 规范——命题须标级别+状态，没证完只能标 `conjecture`/`partial`，**严禁把未证结论当定理**；理论给上界，真实数字仍以第 4 节实测为准，并在其 §9.2 注册表登记。
- **数据诚实**：引用任何数字前查 `docs/PROVENANCE.md` 确认级别+状态——**D1 模拟器 / D0 理论值禁止当 D2 真机结论**，`discrepancy`/`unverified` 数字禁止外引；新增数据须登记溯源表并跑 `verify_claims.py`；发现矛盾**先登记、不静默改数字**。
- **论文诚实**：写论文/对外材料按 `docs/PAPER_WRITING.md` 三铁律——数字必过 PROVENANCE（verified/D2，模拟器须标注）、理论必过 THEORY（仅 `proven` 可作定理，`partial`/`conjecture` 降口吻）、叙事必合 APPLICABILITY（主战场=落 SSD，DeepSeek 仅对照）；引用文献凡未核实一律标 `[TODO: verify cite]`，**严禁凭记忆编造**；投稿前过 `PAPER_WRITING §4` 检查清单。示例见 `mecc_package/paper/mecc_paper_example.md`。
