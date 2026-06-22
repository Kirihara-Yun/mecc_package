# 论文写作指导 —— 怎么把本仓库的工作写成一篇可信的论文

> **本文是什么**：指导 AI agent（与人类）把 MECC 的研究**组织成一篇结构完整、每个数字可追溯、每条断言可证伪**的论文的写作规范。
> 它定义：一篇论文有哪些**不变的章节角色**、每章「写什么 / 不写什么 / 数字与理论从哪取 / 怎么自检」，以及**诚实门禁**（数字必过 `PROVENANCE`、理论必过 `THEORY` 状态、叙事必合 `APPLICABILITY`）。
>
> **本文不是什么**：不是论文本身（实例见 [`../mecc_package/paper/mecc_paper_example.md`](../mecc_package/paper/mecc_paper_example.md)），不是数据表（数字见 [`PROVENANCE.md`](./PROVENANCE.md)），不是理论推导（见 [`THEORY.md`](./THEORY.md)）。
>
> **配套阅读**：定位 [`APPLICABILITY.md`](./APPLICABILITY.md)、理论 [`THEORY.md`](./THEORY.md)、实验 [`EXPERIMENTS.md`](./EXPERIMENTS.md)、数字真伪 [`PROVENANCE.md`](./PROVENANCE.md)、术语 [`GLOSSARY.md`](./GLOSSARY.md)、架构 [`ARCHITECTURE.md`](./ARCHITECTURE.md)。
>
> **配套实例**：本文每条规范都在示例论文 [`mecc_paper_example.md`](../mecc_package/paper/mecc_paper_example.md) 中示范了一遍——**那是一篇按本规范写、数字全部对齐 PROVENANCE 的活教材**，读规范时对照它看。

---

## 0. 三条铁律（写任何一句话前先内化）

> 论文是仓库里**唯一对外、且最难撤回**的产物。一旦把一个错数字、一个未证定理、一句不实有效性写进去，危害远超改坏一段代码。因此写论文的门禁比写代码更严。

- **铁律 W0｜数字必过 PROVENANCE**：论文里出现的**任何**性能数字（加速比、PPL、命中率、延迟、tok/s、体积…），必须能在 [`PROVENANCE.md §3`](./PROVENANCE.md) 对照表查到，且状态为 `verified`。
  - `discrepancy` / `unverified` 的数字**禁止写进正文结论**；非提不可时只能写"待核实/存在分歧"并放进 Limitations。
  - **D1 模拟器 / D0 理论值**写进论文时必须**显式标注**（如"缓存模拟器，合成规模"），**严禁与 D2 真机数字并列成同一张主表**。
  - 写完跑 `python3 mecc_package/scripts/verify_claims.py`，全绿才算数字关过。

- **铁律 W1｜理论必过 THEORY 状态**：论文里以"定理/命题/可证明"口吻出现的每条数学陈述，必须在 [`THEORY.md §9.2 注册表`](./THEORY.md) 查到，且状态为 `proven`。
  - `partial` 只能写成"在 … 假设下"并标注待补；`conjecture` 只能写成"我们观察到/猜测"，**严禁当定理**（仓库已示范把代码里叫 "Theorem 4" 的东西诚实降级为 `partial`）。
  - 论文正文**不复写理论推导的全文**，引用 `THEORY.md` 的命题编号（P1/T4/P8…）即可，避免与理论源不一致。

- **铁律 W2｜叙事必合 APPLICABILITY**：任何"方法有效 / 主场景 / 适用范围"的措辞，必须与 [`APPLICABILITY.md`](./APPLICABILITY.md) 一致。
  - **主战场只有一个**：`模型 expert 总量 > 可用 CPU 内存`（被迫落 SSD）。主结论只能由此场景（Mixtral，L2 真机）支撑。
  - **DeepSeek-V2-Lite 是对照（L1），不是主战场**——它的 2.59× 只能写成"算法上界/对照"，不能写成"方法有效性证据"。
  - 不得声称"在小模型 / 装得进 HBM 的模型上有效"。

> 一句话总规则：**论文的有效性叙事来自 APPLICABILITY，数字来自 PROVENANCE（且 verified/D2），理论来自 THEORY（且 proven）。三者任何一处不达标，宁可不写。**

---

## 1. 一篇论文的结构（不变的章节角色）

> 用户要求覆盖：摘要、引言、背景知识、motivation、insight、framework、method、experiment、讨论与总结、引用文献。
> 下表把每章的**角色**固定下来（不变），具体内容随工作进展生长（见 §3 章节注册表）。**章节顺序可按会议模板微调，但角色不可缺失、不可混淆。**

| # | 章节 | 一句话角色（回答什么） | 主要素材来源 | 绝不能写 |
|---|------|----------------------|--------------|----------|
| A | **Abstract 摘要** | 用 5–8 句讲清"问题→方法→主结果→意义"，给出**一个**最硬的数字 | PROVENANCE 主场景 verified 数字 | 任何 D1/未核实数字；夸张形容词 |
| B | **Introduction 引言** | 为什么这个问题重要、现有方案缺什么、本文贡献（bullet） | APPLICABILITY §1 + 现状 | 把对照场景当主战场 |
| C | **Background 背景知识** | 读者读懂本文所需的前置（MoE 推理、三级存储、offload 现状） | ARCHITECTURE + GLOSSARY | 与 Related Work 重复（背景=知识，RW=对比） |
| D | **Motivation 动机** | "现状为什么不够用"——用**可观测的痛点/数据**而非空谈 | APPLICABILITY 决策树 + 痛点测量 | 没有证据的"我们认为很慢" |
| E | **Insight 关键洞察** | 本文**赖以成立的那一个想法**（一句话能说清） | THEORY §4（联合 LRU 结构性优势） | 把"工程实现"当洞察 |
| F | **Framework 总体框架** | 系统全貌：模块、数据流、编译期↔运行期分工（一张图） | ARCHITECTURE §架构/数据流 | 陷入单个函数细节 |
| G | **Method 方法** | 可复现的方法细节 + 形式化（命题引用 THEORY 编号） | THEORY §1–§6 + 代码锚点 | 把 `conjecture` 写成定理 |
| H | **Experiment 实验** | 主结果 + 消融 + 对照，严格区分 L2/L1/D1 | PROVENANCE §3 + EXPERIMENTS 分级 | 用 L0 smoke / D1 模拟器当主证据 |
| I | **Discussion & Conclusion 讨论与总结** | 适用边界、局限、未来工作、一句话收束 | APPLICABILITY §5 + PROVENANCE §4 矛盾 | 掩盖已知矛盾/局限 |
| J | **References 引用文献** | 支撑每条"现有工作"断言的出处 | §2.10 规范 | 凭记忆编造 bib（见 W3） |

> **关于 Related Work**：可独立成节，也可并入 Background/Introduction。无论放哪，**对比性断言（"SwapMoE 是有损的""Fiddler 不落 SSD"）必须能被引用文献支撑**，否则降级为"据我们所知"。

---

## 2. 逐章节写作 SOP（写什么 / 怎么取数 / 怎么自检）

> 每节给：**目标 → 内容清单 → 取数/取理论的来源 → 该节自检**。照着填，别即兴发挥。

### 2.1 Abstract（摘要）
- **目标**：让审稿人 30 秒决定"值得读"。结构：背景一句 → 问题一句 → 本文方法一句 → **主结果（含一个 verified 数字）** → 意义一句。
- **取数**：只用**主场景 D2 verified**（M1–M4）。默认用 **1.33×（综合加速，vs SwapMoE）+ 无损 PPL 24.57 vs 36.12**。
- **自检**：① 出现的数字在 PROVENANCE 是 `verified`？② 没把对照场景/模拟器数字写进摘要？③ 平台标注 = **A100 80GB**（M5 已采信；实验历史先 5090 后 A100，Mixtral 主结果在 A100；JSON `hardware` 字段的 rtx5090 是遗留值，勿据此写 5090）？

### 2.2 Introduction（引言）
- **目标**：建立"问题重要 + 现有不够 + 我们补上"的三段式，末尾给**贡献列表**。
- **内容清单**：(1) MoE 为何成主流但 expert 权重巨大；(2) 部署时三级放置的现实（HBM/CPU/SSD）；(3) 现有 offload 在"连 CPU 都装不下"时的失败模式；(4) 本文贡献 3–4 条 bullet，每条对应后文一节。
- **取数/叙事**：APPLICABILITY §1–§2。贡献里若提数字，仍受 W0 约束。
- **自检**：贡献列表的每一条，后文是否真有对应章节兑现？有没有把 DeepSeek 写成主战场（违反 W2）？

### 2.3 Background（背景知识）
- **目标**：补齐读者前置知识，**不做对比**（对比留给 Related Work / 实验）。
- **内容清单**：MoE 前向与 top-k 路由（GLOSSARY 的 k、α）；三级存储延迟量级（APPLICABILITY §1 表）；offload/缓存基本概念（命中率、LRU）。
- **取数**：延迟量级用 `PROVENANCE L1`（5090 三级延迟 255.8µs/6504µs/789739µs，D2 verified）。
- **自检**：术语首次出现是否有定义或指向 GLOSSARY？是否把"我们的方法"提前剧透（背景应中性）？

### 2.4 Motivation（动机）
- **目标**：用**可观测痛点**论证"现状不够"。动机 = 有证据的不满，不是抒情。
- **内容清单**：(1) 当 expert 总量 > CPU 内存时，朴素方案每次 miss 触发 SSD 冷读，量级 ~10–100ms（见背景延迟表）；(2) 两级方案（仅 HBM+CPU）在此场景容量不够；(3) 有损量化方案（SwapMoE/EdgeMoE 2-bit）省了空间却**掉精度**（PPL 36.12，D2）。→ 导出"既要装得下、又要不掉精度、还要快"的张力。
- **取数**：SSD 延迟 L1（D2）；有损 PPL 36.12（M2，D2）。
- **自检**：每个"慢/不够/掉精度"的断言后面是否跟着一个 verified 数字或一条 THEORY 命题？

### 2.5 Insight（关键洞察）—— **全文的灵魂，必须一句话说清**
- **目标**：点明本文成立所依赖的**那一个**想法。MECC 的洞察是：
  > **把 HBM 与 CPU 当作一个"联合动态 LRU 栈"**（HBM 淘汰→降级到 CPU，CPU 命中→升级回 HBM），让快层覆盖**运行期真实工作集**的前 K_H+K_C 个高频 expert，而不是编译期猜死的静态秩区间——于是更少 expert 落到昂贵的 SSD，且**全程 fp16 无损**。
- **取理论**：对应 `THEORY.md` P5/P6/TH-006（联合 LRU 包含性）。
- **自检**：洞察能否独立于实现被一句话复述？是否区分了"洞察（为什么应该更好）"与"实现（怎么做到）"？引用的命题状态是否如实标注（TH-006 当前 `conjecture`，写成"我们论证/观察"而非"已证明"）？

### 2.6 Framework（总体框架）
- **目标**：给系统全貌——**编译期静态放置** + **运行期联合动态 LRU**两阶段，配一张数据流图。
- **内容清单**：模块（compiler / engine / 三级存储）、数据流（profile→编译期分配 K_H,K_C→运行期 LRU 升降级）、四种策略位置（ours/swapmoe/fiddler/naive 在同一框架下的差异）。
- **取材**：ARCHITECTURE.md 的架构图与数据流、四策略对比。
- **自检**：图里每个模块在 Method 里是否都有展开？编译期/运行期分工是否与 `compiler.py` / `engine.py` 代码锚点一致？

### 2.7 Method（方法）—— 形式化引用 THEORY，别复写
- **目标**：让人能复现。结构：系统模型与符号 → 编译期目标 → 运行期策略 → 无损性论证。
- **内容清单（对应 THEORY 命题，引用编号即可）**：
  - 系统模型与三级延迟 $T_t(s)=\mathrm{lat}_t+s/\mathrm{bw}_t$（THEORY §1）；
  - Zipf 热度与命中率 $\mathrm{HitRate}(k)=H_k(\alpha)/H_N(\alpha)$（**P1 / TH-001, proven**）；
  - 编译期目标 $\mathcal{L}=h_H T_H+h_C T_C+h_S T_S$ 与贪心填满（**P3 proven / T4 `partial`**——T4 必须写"在 … 假设下，容量贪心版本"）；
  - 运行期联合 LRU 升降级（**P5 `partial` / P6 `conjecture`**——写成"结构性优势/我们论证"）；
  - 无损性（**P8 / TH-008, proven**：搬运是 fp16 恒等映射 → PPL 不变，可作定理陈述）。
- **取理论**：全部引用 THEORY 命题编号 + 状态；正文不重抄证明。
- **自检**：每条以定理口吻出现的陈述，THEORY 注册表里状态是否 `proven`？`partial`/`conjecture` 是否都降了口吻？方法步骤是否有代码锚点（`file:func`）支撑可复现？

### 2.8 Experiment（实验）—— 严格区分 L2 / L1 / D1
- **目标**：用证据支撑贡献，按级别分区，不混淆。
- **内容清单与分区**：
  - **主结果（L2 真机，D2）**：Mixtral-8x7B 落 SSD，OURS vs SwapMoE **1.33×**、PPL **24.57 无损 vs 36.12 有损**、SSD 命中 **17.6% vs 34.5%**、CPU 命中 **38.0% vs 23.3%**（M1–M4）。这是**唯一的对外有效性证据**。
  - **对照（L1，D2 但仅算法上界）**：DeepSeek-V2-Lite，无优化 2.59×（D1 行）/ e2e 2.55×（D3）——**必须标注"对照场景，CPU 装得下、不落 SSD，非主战场"**。
  - **趋势/上界（D1 模拟器）**：热点漂移 9.50×/5.68×、静止 6.26×/3.99×（H1/H2）——**必须标注"缓存模拟器，DeepSeek 合成规模 N=64"，单独成表，绝不与真机表并列**。
  - **消融**：联合 LRU vs 静态 CPU（解释 CPU 命中 0% vs 38%，对应 TH-005/006）。
- **取数**：全部来自 PROVENANCE §3，逐个核对状态。**论文表3 那组 DeepSeek e2e 数字（TTFT 7426/tok·s 0.92/1.56×，X1/D4）目前 `unverified`，禁止写入**——要么重跑落盘升级为 verified，要么改用 D3 的 2.55×。
- **自检**：① 每张表标了级别（D2/D1）与平台？② 模拟器数字有没有混进真机主表？③ 跑 `verify_claims.py` 全绿？④ baseline 是否 apples-to-apples（同预算/同 store/同 prompt/同卡，APPLICABILITY §5 清单）？

### 2.9 Discussion & Conclusion（讨论与总结）
- **目标**：诚实划定边界 + 收束贡献。**这是体现科研诚实的章节，不是自夸。**
- **内容清单**：
  - **适用边界**：重申主战场判据（APPLICABILITY），明说"装得进 CPU 时本方法无结构性优势"。
  - **局限（Limitations）**：如实写——理论 TH-004/005/006 尚 `partial`/`conjecture`（THEORY §9.3）；部分对照数字仍是 D1 模拟器；已知口径矛盾（PROVENANCE §4 的 X1–X5，尤其 X1 论文表3 待重跑）。
  - **未来工作**：攻关 TH-006 联合 LRU 包含性证明；补 X1 真机 e2e。
  - **结论**：一段话回扣 Insight + 主结果。
- **自检**：是否把 PROVENANCE §4 的相关矛盾、THEORY §9.3 的未证命题如实列入局限？有没有在结论里偷偷把对照/模拟器结果升格为主结论？

### 2.10 References（引用文献）—— 见 §W3 防编造
- **目标**：每条"现有工作"断言可溯源。
- **规范**：
  1. 引用的论文**标题/作者/年份/出处**必须真实；不确定就**标 `[TODO: verify cite]`**，**绝不凭记忆编 bibkey 或 DOI**（见铁律 W3）。
  2. 对比性断言（"X 是有损的"）必须落到具体引用；做不到就改成"据我们所知"。
  3. 本仓库内部证据（数字/理论）不进 References，而是引用 PROVENANCE/THEORY 的编号或脚注。

> **铁律 W3｜不编造引用**：LLM 极易"幻觉"出看似合理实则不存在的文献。**任何 bib 条目在没有外部核实前一律标 `[TODO: verify cite]`**，由人类或联网检索确认后再去标记。宁可留 TODO，不可造假引用。

---

## 3. 章节内容注册表（可扩展，不写死）

> 与 `EXPERIMENTS.md §7` / `THEORY.md §9` / `OPTIMIZATION.md §6` 同范式：**章节角色（§1）稳定不变，具体内容靠注册表生长**。
> 工作有新进展时，**在此追加/更新一行**（指明该章引用了哪些 PROVENANCE claim、哪些 THEORY 命题），不改 §1/§2 的规范本身。

| 章节 | 当前主要内容锚点 | 引用的 PROVENANCE claim | 引用的 THEORY 命题 | 待补 |
|------|------------------|-------------------------|--------------------|------|
| Abstract | 主场景 1.33× + 无损 | M1, M2 | — | — |
| Introduction | 三级存储动机 + 贡献 | （叙事，APPLICABILITY） | — | — |
| Background | MoE/三级延迟/LRU | L1 | — | — |
| Motivation | SSD 冷读 + 有损掉精度 | L1, M2 | — | — |
| Insight | 联合 LRU 覆盖真实工作集 | — | P5, P6 / TH-006(conjecture) | TH-006 证成后升口吻 |
| Framework | 编译期+运行期两阶段 | — | （ARCHITECTURE） | — |
| Method | 命中率/目标/无损 | M3, M4 | TH-001✔ T4(partial) P8✔ | T4 补交换论证 |
| Experiment | Mixtral 主表 + 消融 | M1–M4(D2), D1/D3, H1/H2(D1) | TH-005, TH-006 | **X1：重跑 DeepSeek e2e 升 verified** |
| Discussion | 边界 + 局限 + 未来 | §4 矛盾 X1–X5 | §9.3 待攻关 | 随证明/重跑更新 |
| References | — | — | — | **多条 `[TODO: verify cite]` 待人工核实** |

> 新增一章内容时：在对应行更新"内容锚点 / 引用 claim / 引用命题 / 待补"，并确保引用的 claim 状态 `verified`、命题状态匹配口吻。

---

## 4. 投稿前总检查清单（提交/对外前必须逐项打勾）

```
[数字关 · 铁律 W0]
[ ] 正文每个数字都能在 PROVENANCE §3 查到，且状态 = verified
[ ] D1 模拟器 / D0 理论值已显式标注，且未与 D2 真机并列成主表
[ ] discrepancy/unverified 数字未进结论（如 X1 论文表3 已回避或重跑升级）
[ ] 平台标注 = A100 80GB（M5 已采信；Mixtral 主结果在 A100，JSON hardware 字段的 rtx5090 为遗留值，勿照搬）
[ ] 已运行 python3 mecc_package/scripts/verify_claims.py 且全绿

[理论关 · 铁律 W1]
[ ] 每条"定理/命题"口吻陈述在 THEORY §9.2 状态 = proven
[ ] partial/conjecture 命题已降为"在…假设下"/"我们观察/猜测"
[ ] 方法步骤有代码锚点 (file:func)，可复现

[叙事关 · 铁律 W2]
[ ] 主战场叙事 = "expert 总量 > CPU 内存（被迫落 SSD）"，与 APPLICABILITY 一致
[ ] DeepSeek-V2-Lite 标为对照(L1)，未当主战场证据
[ ] 未声称在小模型/装得进 HBM 的模型上有效

[引用关 · 铁律 W3]
[ ] 无凭记忆编造的文献；未核实的一律 [TODO: verify cite]
[ ] 对比性断言均有引用支撑或降级为"据我们所知"

[结构关]
[ ] 摘要/引言/背景/motivation/insight/framework/method/experiment/讨论总结/引用 角色齐全
[ ] 引言贡献列表每条都有对应正文章节兑现
[ ] Insight 能用一句话独立复述
[ ] Limitations 如实列入 THEORY 未证命题 + PROVENANCE 矛盾
```

---

## 5. 常见雷区（本仓库尤其容易犯）

| 雷区 | 后果 | 正确做法 |
|------|------|----------|
| 把 D1 模拟器 9.50×/5.68× 当真机主结果 | 审稿人复现失败，可信度崩 | 标"缓存模拟器，合成规模"，单独成表，主结论只用 Mixtral D2 |
| 把对照 DeepSeek 2.59× 写成"方法有效性" | 违反 APPLICABILITY，被指错位 | 写成"算法上界/对照"，明说不落 SSD |
| 写论文表3 那组 TTFT/tok·s（X1） | 无对应 JSON，数据造假风险 | 重跑落盘升 verified，或改用 D3 的 2.55× |
| 把代码注释里的 "Theorem 4" 当已证定理 | 虚假定理，比缺口更有害 | 标 `partial`，写"容量贪心版本，待补交换论证" |
| 平台写 A100（沿用旧摘要） | 与 JSON(rtx5090) 矛盾 X2 | 统一 RTX 5090 |
| 凭记忆写 [Author et al. 2023] 引用 | 文献幻觉 | `[TODO: verify cite]`，人工/联网核实 |
| 1.33× 与 1.62× 混用不标口径（X3） | 自相矛盾 | 明标：1.33×=综合加速，1.62×=TPOT 比 |

---

## 附：本文与其他文档的闭环

```
APPLICABILITY (何时有效 → 决定论文"主战场叙事"，铁律 W2)
      │
      ▼
THEORY (为什么有效 → 提供 Method/Insight 的命题与状态，铁律 W1)
      │
      ▼
EXPERIMENTS (怎么测、分级 L0/L1/L2 → 决定 Experiment 章哪些能当证据)
      │
      ▼
PROVENANCE (数字真不真 → 论文每个数字的唯一出处，铁律 W0)
      │
      ▼
PAPER_WRITING (本文：怎么把上面四者组织成一篇可信论文)
      │  按规范写
      ▼
mecc_paper_example.md (活教材：一篇已对齐全部门禁的示例论文)
```

> **一句话总规则**：**论文不创造事实，它只忠实组织已被 APPLICABILITY/THEORY/PROVENANCE 确认过的事实。** 写作时你的工作是"组织 + 表达 + 诚实标注边界"，而不是"为了好看而调高数字或升格结论"。
