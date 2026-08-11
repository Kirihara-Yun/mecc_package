# MECC — Compiler-Guided Lossless Three-Tier Caching

> 一个由编译期概率放置与运行期在线迁移协同驱动的 HBM → CPU pinned → SSD
> **无损三级缓存架构**。MoE expert 推理是当前最重要的实例化与验证场景，而不是方法抽象的边界。

MECC 研究的第一性问题是：当只读大对象的总工作集超过 HBM 与 CPU 可用容量、SSD
不可避免地进入关键路径时，如何在容量约束下最小化暴露访问代价，同时保持对象数值语义不变。
统一科研叙事与数学抽象见 **[`docs/RESEARCH_NARRATIVE.md`](./docs/RESEARCH_NARRATIVE.md)**。

## TL;DR —— 从三级缓存到 MoE 实例

在当前 MoE 实例中，**MECC 只在「连 CPU 内存都装不下全部 expert」时才有价值**：此时部分 expert 被迫落 SSD，
三级缓存（HBM→CPU→SSD）才解决真实瓶颈。判断条件只有一个：

> **`模型 expert 总量 > 可用 CPU 内存` → MECC 有效**

不是「只有 Mixtral 有效」，而是**任何大到能打满 CPU 内存、被迫落 SSD 的 MoE 模型**都适用。
Mixtral-8x7B（~90GB）只是当前最具代表性的验证模型。完整边界与决策树见
**[`docs/APPLICABILITY.md`](./docs/APPLICABILITY.md)**。

一行判断你的模型是否适用：
```bash
python3 mecc_package/scripts/check_env.py --applies \
    --n-layers 32 --n-experts 8 --expert-gb 0.336 --cpu-gb 64 --hbm-gb 32
```

## 核心结果

**主场景 — Mixtral-8x7B（~90GB，连 CPU 都装不下，被迫落 SSD）**
来源 `mecc_package/results/raw/mixtral_real.json`（A100 80GB, cold SSD；平台以 JSON 顶层
`platform` 为准，`compiled_plan.hardware` 仅为历史编译配置串）

| 指标 | OURS | SwapMoE |
|------|------|---------|
| 加速比 | **1.33×** | 1.0 |
| PPL（精度） | **24.57（fp16）** | 未核实（历史 JSON 值 36.12 的 baseline 身份待核） |
| SSD 命中率 | **17.6%** | 34.5% |

> 当前 verified 卖点：OURS 保持 fp16 路径，并把 SSD 命中从 34.5% 压到 17.6%，
> 综合吞吐为同预算静态 CPU 机制对照的 1.33×。历史 PPL 36.12 的 baseline 身份正在按
> PROVENANCE X6 核验，关闭前不将其与当前 fp16 `SwapMoePolicy` 合成质量 claim。

> 数据真伪：以上为 **D2 真机实测**（`mixtral_real.json`）。引用任何数字前请查
> **[`docs/PROVENANCE.md`](./docs/PROVENANCE.md)** 确认级别与状态——热点漂移的 9.50×/5.68× 属 **D1 缓存模拟器**，
> 论文表3 DeepSeek e2e 数字目前 **unverified**，均不可当真机结论外引。

> 对照场景 DeepSeek-V2-Lite（CPU 装得下、几乎不落 SSD）的 2.59× 仅展示**算法上界**，
> **不作为主战场证据**，详见 [`docs/APPLICABILITY.md`](./docs/APPLICABILITY.md)。

## 文档导航

| 你是… | 从这里开始 |
|-------|-----------|
| **AI coding agent** | [`AGENTS.md`](./AGENTS.md)（入口、硬约束、数据口径） |
| **想了解项目接管后的推进规划** | **[`docs/PROJECT_TAKEOVER_PLAN.md`](./docs/PROJECT_TAKEOVER_PLAN.md)（阶段路线、验收门禁、风险与第一批任务）** |
| 想判断方法是否适用 | [`docs/APPLICABILITY.md`](./docs/APPLICABILITY.md) |
| 想理解科研故事与贡献边界 | [`docs/RESEARCH_NARRATIVE.md`](./docs/RESEARCH_NARRATIVE.md) |
| 想理解架构与数据流 | [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) |
| 不懂术语 | [`docs/GLOSSARY.md`](./docs/GLOSSARY.md) |
| 想用提示词驱动 AI 做事 | [`docs/PROMPTS.md`](./docs/PROMPTS.md) |
| **想跑实验 / 让 agent 跑实验** | **[`docs/EXPERIMENTS.md`](./docs/EXPERIMENTS.md)（实验规范：L0冒烟/L1对照/L2主实验 + 记录模板）** |
| **想在 GPU 机器运行并回传日志** | **[`docs/GPU_HANDOFF.md`](./docs/GPU_HANDOFF.md)（拉取、持久运行、状态查看、紧凑报告回传）** |
| **想做优化 / 让 agent 做优化** | **[`docs/OPTIMIZATION.md`](./docs/OPTIMIZATION.md)（算法/工程/评测三维度 + 收益证据级别 + 优化注册表）** |
| **想做数学论证 / 形式化证明** | **[`docs/THEORY.md`](./docs/THEORY.md)（方法数学化 + 证明级别与状态 + 命题注册表）** |
| **想引用数字 / 写论文 / 核对真伪** | **[`docs/PROVENANCE.md`](./docs/PROVENANCE.md)（claim↔证据对照 + 矛盾登记 + 可信度分级；配 `scripts/verify_claims.py` 体检）** |
| **想写论文 / 组织对外材料** | **[`docs/PAPER_WRITING.md`](./docs/PAPER_WRITING.md)（逐章节写作 SOP + 三诚实门禁 + 投稿检查清单）；示例论文 [`mecc_package/paper/mecc_paper_example.md`](./mecc_package/paper/mecc_paper_example.md)** |
| 真机复现 Mixtral 主表的细节 | [`mecc_package/e2e/README_E2E.md`](./mecc_package/e2e/README_E2E.md) |
| 想看方法与策略全量报告 | [`mecc_package/STRATEGY.md`](./mecc_package/STRATEGY.md) |
| 想看论文 | [`mecc_package/paper/mecc_paper.tex`](./mecc_package/paper/mecc_paper.tex)（原稿）；[`mecc_package/paper/mecc_paper_example.md`](./mecc_package/paper/mecc_paper_example.md)（★按写作规范写的示例，数字已对齐 PROVENANCE） |

## 仓库布局

```
.
├── AGENTS.md             # AI 协作者入口（必读）
├── README.md             # 本文件（人类入口）
├── docs/                 # 文档体系
│   ├── APPLICABILITY.md  # ★ 适用性边界与决策树
│   ├── PROJECT_TAKEOVER_PLAN.md # ★ 项目接管与推进路线图
│   ├── PLAN_COMPLETION_AUDIT.md  # 路线图逐项完成度与剩余外部门禁
│   ├── CITATION_AUDIT.md         # 论文外部引用的主来源核验记录
│   ├── RELATED_WORK_REPRO_AUDIT.md # 相关方法的原实现/机制适配/模拟器分级
│   ├── EXPERIMENTS.md    # ★ 实验运行规范（每次跑实验前必读）
│   ├── OPTIMIZATION.md   # ★ 优化指导规范（做任何优化前必读：算法/工程/评测）
│   ├── THEORY.md         # ★ 数学论证与形式化（方法数学化 + 证明规范 + 命题注册表）
│   ├── PROVENANCE.md     # ★ 数字真伪权威源（claim↔证据对照 + 矛盾登记 + 可信度分级）
│   ├── PAPER_WRITING.md  # ★ 论文写作指导（逐章节 SOP + 三诚实门禁 + 投稿检查清单）
│   ├── ARCHITECTURE.md   # 架构、模块、数据流、四策略
│   ├── GLOSSARY.md       # 术语表
│   ├── PROMPTS.md        # 人类用提示词库（多情景）
│   └── templates/        # 实验记录模板等
├── mecc_package/         # 主项目：编译器 + 核心库 + 端到端 harness + 实验数据
│   └── README.md         # 详细结构、快速开始、Pipeline
└── mecc_ablation/        # 硬件优化消融（Mixtral A100 真实端到端）
    └── README.md
```

## 快速开始

```bash
# 0. 环境 + 适用性自检（零依赖）
python3 mecc_package/scripts/check_env.py --applies --cpu-gb 64 --hbm-gb 32

# 1. L0 冒烟测试：全链路逻辑验证（CPU，秒级，不下载模型）
#    注意：smoke 只验证逻辑链路通不通，不是性能证据。
cd mecc_package/e2e && python3 run_e2e.py --smoke

# 2. 真机复现 Mixtral 主表（L2 主实验，需 GPU + ~90GB NVMe）
#    完整规范见 docs/EXPERIMENTS.md，真机细节见 mecc_package/e2e/README_E2E.md
```
