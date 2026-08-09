<!--
  示例论文 —— 按 docs/PAPER_WRITING.md 规范撰写的活教材。
  ★ 本文所有性能数字均取自 docs/PROVENANCE.md §3 且状态为 verified；
    D1 模拟器 / D0 理论值已显式标注；论文表3 那组 unverified 数字(X1)已回避。
  ★ 理论以定理口吻出现者，均对应 docs/THEORY.md §9.2 状态为 proven 的命题；
    partial/conjecture 已降口吻为"我们论证/观察"。
  ★ 引用文献凡未经外部核实者一律标 [TODO: verify cite]（铁律 W3）。
  阅读时请对照 docs/PAPER_WRITING.md 的逐章 SOP。
-->

# MECC: Compiler-Guided Lossless Three-Tier Caching, Instantiated for MoE Inference

> **示例论文（活教材）**。撰写规范见 [`../../docs/PAPER_WRITING.md`](../../docs/PAPER_WRITING.md)；数字真伪以 [`../../docs/PROVENANCE.md`](../../docs/PROVENANCE.md) 为准；理论命题见 [`../../docs/THEORY.md`](../../docs/THEORY.md)。
> 每个数字旁的方括号（如 `[M1, D2]`）是其在 PROVENANCE 对照表中的 claim 编号与可信度级别，**这是规范要求的可追溯标注，正式投稿时移入脚注或删除**。

---

## Abstract（摘要）

现代推理系统越来越多地访问规模超过快速存储容量的只读参数块；当工作集进一步超过 CPU 内存时，SSD 被迫进入关键路径，系统性能由少量慢层访问主导。本文提出 **MECC**，一个编译器引导的无损三级（HBM→CPU pinned→SSD）缓存架构。我们将对象请求建模为带容量约束的随机放置问题：编译期由 profile 估计访问分布并最小化期望取数成本，运行期用 HBM↔CPU 联合升降级修正分布漂移，同时把跨层搬运约束为同精度恒等映射。对于等大小对象与独立 tier 容量上限，我们证明按访问概率排序并依次填满快层的静态最优性；在线策略则明确作为无任意-trace 支配保证的启发式。MoE expert 推理天然满足“大、稀疏激活、只读、访问偏斜”这些条件，因此成为该架构的核心实例化。在 Mixtral-8×7B 的 SSD 强制场景中（A100 80GB，冷 SSD），MECC 相对同预算静态 CPU 机制对照取得 **1.33× 综合加速** `[M1, D2]`，OURS 的 fp16 PPL 为 **24.57** `[M2a, D2]`，并将 SSD 命中率从 **34.5% 降至 17.6%** `[M3, D2]`。

> 自检（对照 PAPER_WRITING §2.1）：摘要仅含 M1/M2/M3（D2 verified）；未出现 D1/unverified 数字；平台为 A100 80GB（M5，已采信；实验历史先 5090 后 A100，Mixtral 主结果在 A100 跑定）。

---

## 1. Introduction（引言）

现代加速器节点形成 HBM、CPU pinned memory 与 NVMe SSD 的深层异构存储。对一组只读大对象而言，困难不只是“放不进 HBM”，而是工作集超过 HBM 与 CPU 后，如何决定哪些对象占据稀缺快层，以及当访问分布偏离离线 profile 时如何在线修正。这个问题同时包含容量约束、随机请求成本、迁移成本与语义保持约束。

MoE 是该抽象的一种自然实例，而非问题定义本身。它通过“每个 token 只激活少数 expert”放大模型容量；expert 权重只读且可分块，router 暴露可 profile 的请求流，而总权重又可能大到无法整体放进 HBM 与 CPU。

部署时，expert 权重只能落在三个层级，其取数延迟相差悬殊：

- **HBM**（GPU 显存，容量最小）：已在卡上，~µs 级；
- **CPU pinned 内存**（容量中等）：经 PCIe H2D 搬运，~ms 级；
- **SSD/NVMe 冷存**（容量最大）：真冷读 ~10–100ms 级。

由此自然分出三种部署情形：(i) 模型能塞进 HBM —— 无需 offload；(ii) 塞不进 HBM 但塞得进 CPU 内存 —— 两级（HBM+CPU）方案足矣；(iii) **连 CPU 内存都塞不下** —— 必须有一部分 expert 落 SSD。情形 (iii) 才是本文的战场：此时朴素换页每次未命中都触发昂贵的 SSD 冷读，而以量化压缩规避落盘又会损失精度。**判断是否进入该战场的条件只有一个：`expert 总量 > 可用 CPU 内存`**（详见适用性边界）。

**本文贡献**：

1. 形式化 sub-CPU 内存预算下的三级对象缓存问题，给出容量约束、访问成本与迁移成本组成的目标，并在当前等大小特例中得到 Zipf 命中率闭式与静态最优放置（§4，P1/T4）。
2. 提出“编译期先验放置 + 运行期在线纠偏”的两时间尺度架构；联合动态 LRU 是当前在线实现，其理论边界被显式保留（§5–§6）。
3. 给出恒等搬运的语义保持证明，并在 MoE 实例中映射为 fp16 expert 权重与前向图不变（§6.4，P8）。
4. 将架构实例化到 MoE，在 Mixtral-8×7B 的 SSD 强制场景中相对同预算静态 CPU 机制对照取得 1.33× 综合加速（§7）。

> 自检（§2.2）：贡献 1–4 各有对应章节兑现；主战场叙事与适用性一致；未把对照场景当主战场。

---

## 2. Background（背景知识）

**MoE 前向与路由。** 一个 MoE 层含 $N$ 个 expert，每个 token 由门控网络（gate）选出 top-$k$ 个 expert 参与计算（Mixtral $k{=}2$，DeepSeek $k{=}6$），输出为被选 expert 输出的加权和 $\sum_e g_e\,\mathrm{Expert}_e(x)$。推理时计算量由 $k$ 决定，但**驻留内存由全部 $N$ 个 expert 决定**——这正是内存压力的来源。

**三级存储与延迟量级。** 取一个 expert 的延迟可线性建模为"固定延迟 + 传输时间"。三级取数延迟实测为 HBM **255.8 µs**、CPU **6504 µs**、SSD **789739 µs** `[L1, D2]`（延迟标尺在 RTX 5090 上测得），呈现 $T_H \ll T_C \ll T_S$，SSD 比 HBM 慢约四个数量级。这一悬殊比例是后文一切收益的物理前提。

**Offload 与缓存。** 把暂不用的 expert 移到慢层、用时再取回，即 offload；用有限的快层容量缓存高频 expert，即缓存。缓存的核心指标是**命中率**与替换策略（如 LRU）。术语定义（α、$K_H$、$K_C$、TTFT、TPOT 等）见术语表。

> 自检（§2.3）：延迟量级用 L1（D2）；术语指向 GLOSSARY；本节保持中性，未剧透方法优势。

---

## 3. Motivation（动机）

现状在情形 (iii)（expert 总量 > CPU 内存）下存在三重张力，每一重都有可观测证据：

1. **SSD 冷读昂贵。** 由背景延迟可知 SSD 取数 ~789 ms 量级 `[L1, D2]`，比 HBM 高约四个数量级。一旦高频 expert 落到 SSD 且频繁未命中，decode 的每 token 延迟（TPOT）将被 SSD I/O 主导。

2. **两级方案容量不足。** 仅用 HBM+CPU 的方案在"连 CPU 都装不下"时无处安放溢出的 expert，无法覆盖该场景。

3. **有损压缩改变权重数值。** 以低比特量化（如 2-bit）压缩 expert 可省空间，但不再满足本文的 fp16 恒等搬运定义；具体质量损失必须由独立、可溯源的量化实验支撑。当前 verified 的 OURS fp16 PPL 为 **24.57** `[M2a, D2]`。

这三者共同导出本文要解决的张力：**既要在 sub-CPU 预算下装得下，又不能损失精度，还要足够快**。

> 自检（§2.4）：每个"慢/不足/掉精度"断言后均跟 verified 数字（L1/M2，D2）。

---

## 4. Problem Formalization（问题形式化）

> 本节命题均引用理论文档编号；完整证明见 [`THEORY.md`](../../docs/THEORY.md)，正文不复写。

首先定义一般对象集合 $\mathcal D=\{1,\ldots,N\}$，对象 $i$ 大小为 $s_i$、访问概率为 $p_i$。令 $x_{i,t}\in\{0,1\}$ 表示对象放在 $t\in\{H,C,S\}$，静态目标为
$$
\min_x\sum_i p_i\sum_t x_{i,t}T_t(s_i),\qquad
\sum_t x_{i,t}=1,\quad \sum_i s_i x_{i,t}\le B_t\;(t\in\{H,C\}).
$$
运行期策略还需最小化有限时域内的命中层级成本与迁移成本之和。当前实现求解上述问题的等大小对象特例：$s_i=s$，三级延迟 $T_t(s)=\mathrm{lat}_t+s/\mathrm{bw}_t$ 满足 $T_H\le T_C\le T_S$；HBM/CPU 分别容纳 $K_H,K_C$ 个对象。映射到 MoE 后，对象即单层单 expert 权重块。

**路由热度（假设 A2，Zipf）。** 把 expert 按访问频率降序排名，排名第 $i$ 者被一次路由命中的概率 $p_i = i^{-\alpha}/H_N(\alpha)$，其中 $H_n(\alpha)=\sum_{i=1}^n i^{-\alpha}$ 为广义调和数，$\alpha$ 为热度集中度。

**命题 P1（命中率 = 调和数比，TH-001，已证）.** 把容量 $k$ 的缓存装入最热的 $k$ 个 expert，则一次随机路由的命中率为
$$
\mathrm{HitRate}(k)=\frac{H_k(\alpha)}{H_N(\alpha)}.
$$
这是整套理论的基石，使命中率可闭式分析。

**编译期目标。** 由 P1，三级命中率 $h_H=\mathrm{HitRate}(K_H)$、$h_C=\mathrm{HitRate}(K_H{+}K_C)-h_H$、$h_S=1-h_H-h_C$，期望单次取数延迟为
$$
\mathcal{L}(K_H,K_C)=h_H T_H + h_C T_C + h_S T_S.
$$

**命题 P3（单调性，TH-003，已证）.** 在 A1 下，$\mathcal{L}$ 关于 $K_H$、$K_C$ 各自单调不增——即"快层能装多满就装多满"最优。

**定理 T4（最优分配，TH-004，已证明）.** *在 A1–A2 与独立 HBM/CPU 容量上限下，使 $\mathcal{L}$ 最小的分配为容量贪心填满：$K_H^\star=\min(\lfloor\mathrm{hbm}/s\rfloor,N)$，再 $K_C^\star=\min(\lfloor\mathrm{cpu}/s\rfloor,N-K_H^\star)$。* P3 给出填满性，交换论证给出按热度秩分配的最优性；该定理不覆盖可在 tier 间兑换的共享成本预算。

> 自检（§2.7）：P1/P3/T4 均按 THEORY 中的 `proven` 状态陈述，并明确 T4 只覆盖独立容量上限与当前等大小特例。

---

## 5. Insight（关键洞察）

> **本文成立所依赖的一个想法，一句话：**
> **把 profile 当作访问分布的先验，把真实请求流当作在线观测：编译期优化三级初始放置，运行期通过 HBM↔CPU 升降级纠正先验偏差，同时以恒等搬运保持对象语义。**

这与静态放置（如 SwapMoE-style 策略把 CPU 池固定为编译期的"次热"区间）不同。但 P5/P6 的普遍优势版本已被短 trace 反例推翻，因此这里只陈述经验洞察：

- **静态 CPU 池低利用是条件性现象（TH-005，已反驳普遍版）.** 特定 profile、容量与 trace 下可观察到低命中，但周期 trace 可使其保持正命中率。
- **联合 LRU 可适应 drift，但无普遍包含保证（TH-006，已反驳）.** $N=3,K_H=K_C=1$、trace $[2,1]$ 已足以使联合 LRU 比静态拆分多一次 SSD miss。真实优势必须由 L2 与带条件的新命题支撑。

> 自检（§2.5）：洞察一句话可独立复述；区分了洞察与实现；P5/P6 的普遍版本如实标为 refuted，未冒充定理。

---

## 6. Framework & Method（框架与方法）

### 6.1 总体框架（Framework）

MECC 分两阶段（数据流详见架构文档）：

```
profile(路由热度, α)
      │ 编译期 (compiler.py:optimize)
      ▼
静态放置: 解 K_H,K_C, 按热度秩分配 expert 到 HBM/CPU/SSD
      │ 运行期 (engine.py)
      ▼
联合动态 LRU: HBM 淘汰→降级 CPU; CPU 命中→升级 HBM; 冷项落 SSD
```

同一 fp16 框架可实例化四种策略以作对照：**ours**（联合动态 LRU）、**swapmoe-style**（静态 CPU 池）、**fiddler**、**naive**。它们的差异仅在"运行期如何管理 CPU 层"；独立 2-bit baseline 不属于当前 harness。

### 6.2 编译期静态放置

依据 §4 的 P3/T4，编译器把 HBM、CPU 按容量贪心填满，并按 Zipf 热度秩把最热的 expert 分到 HBM、次热分到 CPU、其余落 SSD。代码锚点：`compiler.py:optimize`。

### 6.3 运行期联合动态 LRU

运行期不固定 CPU 内容：HBM 满时淘汰的 expert **降级**写入 CPU；当某 expert 在 CPU 命中时，将其**升级**回 HBM。这使快层覆盖随真实访问流动态调整（§5 的洞察）。代码锚点：`engine.py:_access_ours`（CPU 命中升级）、`_evict_hbm_if_needed(spill_to_cpu=True)`（HBM 溢出降级）。

### 6.4 无损性（Method 的核心保证）

**定理 P8（无损 / fp16 恒等，TH-008，已证）.** MECC 的三级缓存只改变 expert 权重的**存放位置与搬运时机**，不改变其数值与 MoE 前向的计算图。搬运算子是 fp16 恒等映射 $\mathrm{copy}:W\mapsto W$，命中与否只影响**何时**取到 $W$、不影响取到的 $W$ 本身。因此对任意输入，MECC 输出与原模型逐比特相同，PPL 不变。

这是 MECC 相对 2-bit 量化等有损方案的核心区别：**同精度下更快**，而非"用精度换速度"。

> 自检（§2.6/§2.7）：框架图每模块在 Method 展开；编译/运行分工有代码锚点；P8 引用为 proven，可作定理。

---

## 7. Experiment（实验）

> 严格按级别分区：§7.1 主结果为 **L2 真机（D2）**，是唯一对外有效性证据；§7.2 为**对照（L1）**；§7.4 为**缓存模拟器（D1）**，单独成表、不与真机并列。

### 7.1 主结果 — Mixtral-8×7B，被迫落 SSD（L2 真机，D2）

平台 A100 80GB、冷 SSD。Mixtral-8×7B（~90GB）连 CPU 都装不下，部分 expert 必须落 SSD——这是 MECC 的真正主战场。来源 `results/raw/mixtral_real.json`（实验历史先在 5090 调试、最终在 A100 跑定，见 PROVENANCE M5）。

| 指标 | OURS (MECC) | SwapMoE | claim |
|------|-------------|---------|-------|
| 综合加速比（vs SwapMoE） | **1.33×** | 1.0 | `[M1, D2]` |
| PPL（精度） | **24.57（fp16）** | 未核实；历史 36.12 的 baseline 身份不可溯源 | `[M2a, D2] / [M2b, unverified]` |
| SSD 命中率 | **17.6%** | 34.5% | `[M3, D2]` |
| CPU 命中率 | **38.0%** | 23.3% | `[M4, D2]` |

**解读**：MECC 在**同精度（无损）**下取得 1.33× 加速，关键机制是把 SSD 命中从 34.5% 压到 17.6%（更多 expert 命中快层），同时 CPU 命中从 23.3% 升到 38.0%——后者正是联合动态 LRU 相对静态 CPU 池的直接体现。

> 口径说明（X3）：本文"1.33×"指**综合加速**；若按 **TPOT（每 token）比** 则为 1.62×。二者口径不同，本文主结论统一采用综合加速 1.33×。

### 7.2 对照 — DeepSeek-V2-Lite（L1，算法上界，非主战场）

DeepSeek-V2-Lite 较小，CPU 装得下、几乎不落 SSD。此场景**不能作为主战场证据**，仅用于展示算法层面的结构性上界：无优化档 OURS/SwapMoE 约 **2.59×** `[D1, D2]`，端到端 **2.55×** `[D3, D2]`。

> 注意：本仓库早期论文表3 中另一组 DeepSeek e2e 数字（TTFT、tok/s、1.56×）在当前数据中**找不到对应 JSON（X1，unverified）**，按写作铁律 W0 **本文不予采用**，对外 DeepSeek 真机一律引用上述 2.55×（D3, verified）。

### 7.3 消融 — 联合动态 LRU vs 静态 CPU 池

主结果中 OURS 的 CPU 命中率 38.0% 而 SwapMoE-style 对照为 23.3% `[M4, D2]`。这支持“动态 CPU tier 在该配置下更活跃”的经验解释，但 TH-005 的普遍塌缩版本已被反例推翻，不能从该单次实测外推为任意 trace 的结构性保证。

### 7.4 趋势分析 — 热点漂移（缓存模拟器，D1，非真机）

为考察工作集随时间漂移时的鲁棒性，我们用**缓存模拟器**（基于命中率 + 延迟模型，DeepSeek 合成规模 N=64、expert 7.1MB）评估趋势。来源 `results/raw/deepseek_real_e2e.json`。

| 工作负载 | OURS vs FluxMoE | OURS vs SwapMoE | claim |
|----------|------------------|------------------|-------|
| 热点漂移（drift） | 9.50× | 5.68× | `[H1, D1]` |
| 静止（stationary） | 6.26× | 3.99× | `[H2, D1]` |

> **重要标注**：本表为 **D1 缓存模拟器**结果（合成规模），**非真机端到端实测**，仅用于说明"漂移越大、联合 LRU 自适应优势越显著"的**趋势**，不可与 §7.1 真机主表并列、不作为主结论。

> 自检（§2.8）：每表标级别与平台；模拟器(D1)单独成表未混入真机；对照(L1)明确标注；X1 unverified 已回避。

---

## 8. Related Work（相关工作）

MoE offloading 与 expert 缓存已有若干工作，按"是否落 SSD"与"是否无损"可分类对比。据我们所知，多数两级方案聚焦 HBM+CPU、不覆盖 sub-CPU 预算；部分以低比特量化压缩 expert，属有损路线。MECC 的差异在于**三级 + 无损 + 编译期/运行期协同**。

> 写作说明（铁律 W3）：本节具体文献条目（如 SwapMoE、Fiddler、EdgeMoE、mixtral-offloading 的标题/作者/年份/出处）**须经外部核实后再补**，当前一律标记如下，不凭记忆编造：
> - SwapMoE `[TODO: verify cite]`
> - Fiddler `[TODO: verify cite]`
> - EdgeMoE `[TODO: verify cite]`
> - mixtral-offloading `[TODO: verify cite]`
> - Mattson et al., stack inclusion property (1970) `[TODO: verify cite]`

---

## 9. Discussion & Conclusion（讨论与总结）

**适用边界。** MECC 的价值**只在 `expert 总量 > 可用 CPU 内存`（被迫落 SSD）时成立**。当模型装得进 HBM（无需 offload）或装得进 CPU（两级方案足矣）时，MECC 无结构性优势。叙事以适用性边界文档为准，不外推到小模型。

**局限（Limitations，如实列出）。**
1. **理论边界**：独立容量下的最优分配 T4（TH-004）已证明；静态池普遍塌缩（TH-005）与联合 LRU 普遍包含（TH-006）均已被反例推翻。后两者只能作为特定实测条件下的观察，不能作为定理。
2. **部分对照为模拟器**：§7.4 的漂移结果是 D1 缓存模拟器（合成规模），尚无对应真机端到端实测。
3. **已知数据口径问题**：早期论文表3 的 DeepSeek e2e 数字无对应 JSON（待重跑落盘）。**平台口径已澄清并落入数据**：实验先在 RTX 5090 上调试、Mixtral 主结果最终在 **A100 80GB** 上跑定（PROVENANCE M5；矛盾 X2/X5 已解决）；各真机 JSON 顶层已写入 `platform` + `run_time` 字段承载平台/时间真值，`compiled_plan.hardware` 仅为编译期配置串，不影响 1.33× 综合加速等 D2 结论。

**未来工作。** (a) 为联合 LRU 建立带 IRM/Zipf 稳态或 drift 条件的期望 miss 命题；(b) 重跑 DeepSeek e2e，把 §7.2 待核数字落盘为 D2 verified；(c) 在更多真正超过 CPU 容量的大 MoE 上扩展 L2；(d) 扩展实验平台并验证不同 PCIe/HBM 配比。

**结论。** 我们提出 MECC——一个带静态先验、在线纠偏与语义不变量的三级缓存架构。MoE expert 推理把该抽象中的容量压力、稀疏请求和慢层代价同时具体化；在 Mixtral 的 SSD 强制场景中，fp16 实例相对同预算静态 CPU 机制对照取得 1.33× 综合加速，并把 SSD 命中率从 34.5% 降至 17.6%。当前结果验证的是这一架构在 MoE 中的有效实例，而非对任意对象或任意 trace 的普遍最优性。

> 自检（§2.9）：如实列入 THEORY 未证命题与 PROVENANCE 矛盾；结论未把对照/模拟器结果升格为主结论。

---

## References（引用文献）

> 按铁律 W3：以下条目在外部核实前一律为占位，**禁止凭记忆补全为看似真实的 bib**。核实后替换并去除 `[TODO: verify cite]`。

1. SwapMoE: ... `[TODO: verify cite]`
2. Fiddler: ... `[TODO: verify cite]`
3. EdgeMoE: ... `[TODO: verify cite]`
4. Mixtral / Mixture-of-Experts LLM: ... `[TODO: verify cite]`
5. DeepSeek-V2 / DeepSeek-MoE: ... `[TODO: verify cite]`
6. Mattson, R. L. et al. *Evaluation techniques for storage hierarchies* (stack inclusion property), IBM Systems Journal, 1970. `[TODO: verify cite]`

---

> **本示例论文的内部证据索引**（非对外 References，供 agent 核对）：
> - 数字 M1–M4 / L1 / D1 / D3 / H1 / H2 → [`../../docs/PROVENANCE.md §3`](../../docs/PROVENANCE.md)
> - 命题 P1/P3/T4/P5/P6/P8（TH-001/003/004/005/006/008）→ [`../../docs/THEORY.md §9.2`](../../docs/THEORY.md)
> - 适用性叙事 → [`../../docs/APPLICABILITY.md`](../../docs/APPLICABILITY.md)
> - 实验分级 L0/L1/L2 → [`../../docs/EXPERIMENTS.md`](../../docs/EXPERIMENTS.md)
> - 写作规范 → [`../../docs/PAPER_WRITING.md`](../../docs/PAPER_WRITING.md)
>
> 运行 `python3 ../scripts/verify_claims.py`（在 `mecc_package/` 下）可一致性体检本文引用的 D2 数字。
