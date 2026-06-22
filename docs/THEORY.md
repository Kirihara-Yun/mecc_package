# 数学论证与形式化 —— MECC 的理论根基与证明规范

> **本文是什么**：MECC 方法的**形式化数学描述**（Part I），以及指导 agent 进行**形式化证明**的规范与可扩展的**命题注册表**（Part II–III）。
>
> **本文不是什么**：不是实验数据表（数字见 [`EXPERIMENTS.md`](./EXPERIMENTS.md) §7.5 与 `results/raw/*.json`），不是工程说明（见 [`ARCHITECTURE.md`](./ARCHITECTURE.md)）。
>
> **配套阅读**：适用性 [`APPLICABILITY.md`](./APPLICABILITY.md)、优化 [`OPTIMIZATION.md`](./OPTIMIZATION.md)、实验 [`EXPERIMENTS.md`](./EXPERIMENTS.md)、术语 [`GLOSSARY.md`](./GLOSSARY.md)。
>
> **代码锚点**：理论与实现一一对应。本文每条命题都标注其代码出处（如 `compiler.py:optimize`），**理论若与代码不符，以代码为准并回来修订本文**。

---

## 0. 阅读指南：理论与证据的分工

| 层次 | 回答什么 | 在哪里 | 性质 |
|------|---------|--------|------|
| **理论（本文 Part I）** | 在理想假设下「为什么 MECC 应该更快/不掉精度」 | `THEORY.md` | 可证明的命题，给出**上界 / 结构性优势** |
| **经验（EXPERIMENTS）** | 在真实硬件上「实际快了多少」 | `results/raw/*.json` | 可复现的测量，给出**真实数字** |

> **铁律 T0｜理论不替代实验**：本文任何定理都**不能**作为「MECC 在某模型上有效」的最终证据。理论给出*上界与方向*，主战场结论必须由 L2 真机实验（见 `EXPERIMENTS.md` §1 级别定义）确认。反之，实验数字也不写进本文正文（只引用）。

---

# Part I — MECC 方法的形式化

## 1. 系统模型（符号表）

> 代码锚点：`compiler.py`（编译期），`mecc_framework/cache/engine.py`（运行期），`mecc_framework/base/`（存储）。

### 1.1 对象

- 一个 MoE 模型有 $L$ 层；第 $\ell$ 层有 $N$ 个 expert（为简洁设各层同构，异构时对每层独立成立）。
- 单个 expert 权重大小 $s$（单位 GB），全程 **fp16**（见 §6 无损性）。
- 路由：每个 token 在每层由 gate 选 top-$k$ 个 expert（Mixtral $k{=}2$，DeepSeek $k{=}6$）。

### 1.2 三级存储与延迟模型

存储层级集合 $\mathcal{T}=\{H, C, S\}$（HBM / CPU pinned / SSD）。取一个 expert 的延迟按「固定延迟 + 传输时间」线性建模：

$$
T_t(s) \;=\; \mathrm{lat}_t \;+\; \frac{s}{\mathrm{bw}_t},\qquad t\in\{H,C,S\}
$$

代码锚点：`compiler.py:latency_us`（`lat_us + sz_gb/bw_gbs*1e6`）。硬件参数 $(\mathrm{lat}_t,\mathrm{bw}_t)$ 见 `MECC.hardware`（如 a100/h100/apple-mps）。

**假设 A1（延迟序）**：$T_H \le T_C \le T_S$。即 HBM 最快、SSD 最慢。这是 MECC 全部收益的物理前提（违反则方法无意义）。真实参数下成立。

### 1.3 容量预算

- HBM 容纳 $K_H=\lfloor \mathrm{hbm\_gb}/s\rfloor$ 个 expert（上限 $N$）。
- CPU 容纳 $K_C=\lfloor \mathrm{cpu\_gb}/s\rfloor$ 个（上限 $N-K_H$）。
- SSD 容纳其余 $N-K_H-K_C$ 个（视为无限冷存）。

代码锚点：`compiler.py:optimize`（`max_hbm/max_cpu`，`K_H=min(...)`，`K_C=min(...)`）。预算约束记作

$$
0 \le K_H,\; 0\le K_C,\quad K_H + K_C \le N. \tag{C}
$$

---

## 2. 路由热度模型与 α 估计

### 2.1 Zipf 假设

**假设 A2（Zipf 路由热度）**：把 expert 按访问频率降序排名，排名第 $i$ 的 expert 被一次路由命中的概率正比于 $i^{-\alpha}$：

$$
p_i \;=\; \frac{i^{-\alpha}}{H_N(\alpha)},\qquad
H_n(\alpha) \;\triangleq\; \sum_{i=1}^{n} i^{-\alpha},
$$

其中 $H_n(\alpha)$ 是**广义调和数**，$\alpha>0$ 是热度集中度（越大越集中）。

代码锚点：`compiler.py:generate_profile`（`w = 1/arange(1,N+1)**alpha; probs = w/w.sum()`），调和数 `compiler.py:_z_harmonic`。

### 2.2 命题 P1（命中率 = 调和数比）

> **命题 P1.** 在 A2 下，把容量 $k$ 的缓存装入最热的 $k$ 个 expert，则一次随机路由命中该缓存的概率（命中率）为
> $$
> \mathrm{HitRate}(k) \;=\; \frac{H_k(\alpha)}{H_N(\alpha)}.
> $$

**证明.** 命中当且仅当被选 expert 的排名 $\le k$。由 A2，$\Pr[\text{rank}\le k]=\sum_{i=1}^k p_i = \sum_{i=1}^k i^{-\alpha}/H_N(\alpha) = H_k(\alpha)/H_N(\alpha)$。$\qquad\blacksquare$

代码锚点：`compiler.py:zcdf`（`hk/hn`）。**这是整套理论的基石**：缓存命中率被解析地写成调和数之比，使 §4 的优化可闭式分析。

### 2.3 命题 P2（α 的 MLE）

代码 `compiler.py:estimate_alpha` 用 $\hat\alpha = 1 + N/\sum_{i}\log(\mathrm{rank}_i)$ 估计 α。

> **命题 P2（陈述）.** 设观测到的 expert 访问服从 A2 的离散 Zipf，则上式是 α 的（近似）极大似然估计。

**证明义务（未完成）.** 当前代码用的是**连续 Zipf/Pareto 的 MLE 近似式**（对秩取对数求和），其与离散 Zipf 精确 MLE 的偏差需要界定。**本命题状态为 `conjecture`**（见 §9 注册表 TH-002），证明义务：(a) 写出离散 Zipf 对数似然 $\ell(\alpha)=-\alpha\sum_i\log r_i - n\log H_N(\alpha)$；(b) 说明在何种近似（如 $H_N(\alpha)\!\approx\!\int$）下一阶条件退化为代码中的闭式；(c) 给出近似误差量级。这是一个**诚实标注的缺口**，不得在论文里把它当作已严格证明的定理。

---

## 3. 编译期目标函数

### 3.1 期望取数延迟

给定分配 $(K_H,K_C)$，由 P1，三级命中率为

$$
h_H = \mathrm{HitRate}(K_H),\quad
h_C = \mathrm{HitRate}(K_H{+}K_C) - h_H,\quad
h_S = 1 - h_H - h_C,
$$

期望单次取数延迟（编译期优化目标）为

$$
\boxed{\;\mathcal{L}(K_H,K_C) \;=\; h_H\,T_H \;+\; h_C\,T_C \;+\; h_S\,T_S\;}
\tag{$\star$}
$$

代码锚点：`compiler.py:optimize`（`avg_lat = T_H*hbm_hit + T_C*cpu_hit + T_S*ssd_hit`）。

> **命题 P3（目标良定义且单调）.** 在 A1 下，固定 $K_C$，$\mathcal{L}$ 关于 $K_H$ 单调不增；固定 $K_H$，$\mathcal{L}$ 关于 $K_C$ 单调不增。
>
> **证明.** 增大 $K_H$ 一格，把某概率质量 $\delta=p_{K_H+1}\ge 0$ 从 $T_C$ 或 $T_S$ 桶移到 $T_H$ 桶，$\Delta\mathcal{L}=\delta(T_H-T_{\bullet})\le 0$（A1）。$K_C$ 同理（$T_C\le T_S$）。$\qquad\blacksquare$

**推论**：在预算约束 (C) 下，$\mathcal{L}$ 的最小值必然在约束**边界**取得——即「能装多满就装多满」。这正是代码 `optimize` 直接令 $K_H=\min(K_H^{\max},N)$、$K_C=\min(K_C^{\max},N{-}K_H)$ 的理论依据。

### 3.2 定理 T4（最优分配 / "Theorem 4"）

代码注释把 `optimize` 称为 *Theorem 4*。其严格陈述应为：

> **定理 T4（拟陈述）.** 在 A1–A2 与预算 (C) 下，使 ($\star$) 最小的分配满足贪心填满：先把 HBM 填到容量上限 $K_H^\star=\min(\lfloor\mathrm{hbm}/s\rfloor,N)$，再把 CPU 填到 $K_C^\star=\min(\lfloor\mathrm{cpu}/s\rfloor,N-K_H^\star)$，且 expert 按热度秩分配到 tier。

**证明状态：`partial`（见注册表 TH-004）.** P3 的单调性给出了「填满边界最优」的方向，但**完整证明还需**：(i) 论证「按秩贪心」在两级预算耦合下仍全局最优（交换论证 exchange argument）；(ii) 处理 $K_H$ 的边际收益 $p_{K_H{+}1}(T_C{-}T_H)$ 与 $K_C$ 的边际收益 $p_{K_H{+}K_C{+}1}(T_S{-}T_C)$ 的比较——代码注释提到「HBM 边际收益 = CPU 边际收益」的 KKT 直觉，但当前实现是**容量贪心而非边际平衡**，二者在「预算恰好用尽」时一致、在「预算未用尽」时退化。**agent 若要把 T4 写进论文，必须补 (i)(ii) 并明确实现采用的是容量贪心版本。**

---

## 4. 为什么 OURS 优于静态放置（核心定理）

这是 MECC 相对 SwapMoE 的**结构性优势**所在，对应 `tuning_log.md` 实验 3 的关键现象：**OURS 的 CPU 命中率 5.5%，而 swapmoe/fiddler 的 CPU 命中率 = 0%**。下面给出数学解释。

### 4.1 两种 CPU 管理

- **静态（swapmoe）**：CPU 池在编译期固定为热度秩 $[K_H, K_H{+}K_C)$ 的 expert，运行期不变。代码锚点：`engine.py:_warmup`（`static_cpu`），`_access_swapmoe`（HBM miss 后**不**回填 CPU，CPU 只读静态池）。
- **联合动态（ours）**：HBM 与 CPU 是**一个联合 LRU 栈**——HBM 淘汰的 expert **降级**到 CPU（spill），CPU 命中的 expert **升级**回 HBM。代码锚点：`engine.py:_access_ours`（CPU 命中则 `cpu.pop` 升级）、`_evict_hbm_if_needed(spill_to_cpu=True)`（HBM 溢出降级到 CPU）。

### 4.2 命题 P5（静态 CPU 在去重访问流下命中率塌缩）

> **命题 P5.** 当 HBM 用动态 LRU 且其容量 $K_H$ 足以覆盖工作集的高频部分时，静态 CPU 池的命中率趋于 0。

**证明（直觉 + 形式）.** 静态 CPU 池装的是秩 $[K_H,K_H{+}K_C)$ 的「次热」expert。但这些次热 expert 一旦被访问，在动态 HBM 的 LRU 下会被提升进 HBM 并**长期驻留**（因为它们恰是仅次于最热的高频项）。于是后续对它们的访问都在 HBM 命中，**几乎不再回落到 CPU 池**；而真正落到 SSD 的是更冷的尾部，CPU 静态池对尾部无能为力。两头都不沾，故 CPU 命中 $\to 0$。形式化需对 LRU 栈在 Zipf 流下的稳态分布建模（见证明义务）。$\qquad\blacksquare$（直觉级）

代码佐证：`_access_swapmoe` 中 HBM miss 命中 `static_cpu` 计 `hits[1]`，但因上述提升效应，该分支命中频次极低 → 与实测 0% 一致。**证明状态 `partial`（TH-005）**：需补 LRU-Zipf 稳态命中的马氏链/计数论证。

### 4.3 命题 P6（联合 LRU 的包含性 / 自适应优势）

> **命题 P6.** OURS 的「HBM 降级→CPU、CPU 命中→升级 HBM」使有效快层覆盖的是**运行期真实工作集的前 $K_H{+}K_C$ 个高频项**，而非编译期猜测的静态秩区间。当真实工作集与编译期 profile 存在偏移（drift）时，OURS 的 $(h_H{+}h_C)$ 不低于静态方案，且偏移越大优势越大。

**证明义务（TH-006，`conjecture`）.** 关键是论证联合 LRU 满足类似**栈式包含性质（stack inclusion property，Mattson 1970）**：容量 $K_H{+}K_C$ 的联合 LRU 命中集合 $\supseteq$ 任意把同样容量拆成「动态 $K_H$ + 静态 $K_C$」方案的命中集合。若该包含成立，则 $h_H^{ours}+h_C^{ours}\ge h_H^{swap}+h_C^{swap}$，从而 $h_S^{ours}\le h_S^{swap}$（更少落 SSD）——这正是 `ARCHITECTURE.md` §4「压低 SSD 命中率」的理论表述。**这是 MECC 最值得严格证明的命题**，建议优先攻关。

---

## 5. 从命中率到端到端收益

### 5.1 命题 P7（SSD 命中率主导端到端延迟）

> **命题 P7.** 在 A1 的极端比例下（$T_S \gg T_C \gg T_H$，真实参数 $T_S$ 比 $T_H$ 大 4–5 个数量级），期望延迟 ($\star$) 由 SSD 项主导：$\mathcal{L}\approx h_S T_S + O(T_C)$。故**降低 $h_S$ 近似线性降低端到端延迟**。

**证明.** 直接由 ($\star$) 与 $T_S\gg T_C,T_H$。$\qquad\blacksquare$

**衔接**：这把「§4 压低 $h_S$ 的结构性优势」与「端到端 tok/s 提升」连起来，但 $T_S$ 是否真的主导取决于 expert 大小 $s$ 与 SSD 带宽——这正是 `APPLICABILITY.md` 的边界（expert 太大如 Mixtral 336MB 时 SSD I/O 爆炸；CPU 装得下时 $h_S{=}0$ 则本命题空洞）。**理论上界 ≠ 任意场景都成立**，务必引用 APPLICABILITY 的判据。

---

## 6. 无损性（精度不变）

> **命题 P8（无损 / fp16 恒等）.** MECC 的三级缓存只改变 expert 权重的**存放位置与搬运时机**，不改变其**数值**与 MoE 前向的**计算图**。因此对任意输入，MECC 的输出与原模型逐比特相同（同 fp16 下），故 PPL 与原模型一致。

**证明.** 搬运算子是恒等映射 $\mathrm{copy}:W\mapsto W$（H2D/D2H 不改 fp16 值，代码 `_swap.copy_to_gpu` / `expert.py` 零拷贝 view），缓存命中/未命中只影响**何时**取到 $W$，不影响取到的 $W$ 本身；MoE 聚合 $\sum_e g_e\,\mathrm{Expert}_e(x)$ 的算子与权重均不变。故输出函数不变。$\qquad\blacksquare$

**这是 MECC 相对 SwapMoE/EdgeMoE（2-bit 量化、有损）的核心卖点**（见 `APPLICABILITY.md` §4.1：PPL 24.57 无损 vs 36.12 有损）。

> **铁律 T1｜无损是定义性的**：任何"优化"若改变数值（量化/剪枝/近似）就**破坏 P8**，那就不再是 MECC 优化，而是变成了一个有损 baseline（见 `OPTIMIZATION.md` 铁律）。涉及精度的改动必须先在本文重新审视 P8 是否仍成立。

---

# Part II — 指导 agent 进行形式化证明的规范

> 本部分是给后续 agent 的**作业规范**：怎么提出、组织、检验一条数学论证，怎样诚实标注缺口，怎样与实验衔接。

## 7. 命题的级别与状态

每条数学陈述必须标两个标签：**级别**（重要性/角色）与**状态**（证明进度）。

**级别（role）**：
| 级别 | 含义 |
|------|------|
| `axiom/assumption` | 假设（如 A1 延迟序、A2 Zipf）。不证明，但必须**显式列出**并说明现实依据 |
| `lemma` | 引理，为定理服务的中间结论 |
| `proposition` | 命题，独立成立的结论（如 P1 命中率公式）|
| `theorem` | 定理，核心结论（如 T4 最优分配、P6 联合 LRU 优势）|
| `corollary` | 推论，由上面直接得出 |

**状态（status）**：
| 状态 | 含义 | 能否写进论文 |
|------|------|------------|
| `proven` | 给出完整严格证明（每步可检验）| ✅ 可作为定理陈述 |
| `partial` | 方向/特例已证，关键步骤待补 | ⚠️ 只能写「在 … 假设下」并标注待补 |
| `conjecture` | 仅有直觉/数值支持，无证明 | ❌ 只能写作「猜想/观察」，**严禁**当定理 |
| `refuted` | 已被反例推翻 | 记录反例，保留教训 |

> **铁律 T2｜诚实标注**：宁可标 `conjecture` 也不要把没证完的当 `proven`。本文 §2.3 / §3.2 / §4 已示范——把代码里叫 "Theorem 4" 的东西诚实降级为 `partial` 并列出证明义务。**虚假定理比缺口更有害。**

## 8. 一条证明的标准结构（SOP）

新增或完善一条数学论证时，**逐项填齐**：

1. **编号与标签**：分配 `TH-00X` 编号，标级别 + 状态（§9 注册表登记）。
2. **依赖的假设**：显式列出用到哪些 A*（如「依赖 A1, A2」）。**不得隐藏假设**。
3. **符号**：复用 §1 符号表；引入新符号必须在此定义。
4. **陈述**：精确、可证伪。涉及"更优/更快"必须写清**在什么度量、什么约束下**（如「$h_S^{ours}\le h_S^{swap}$ 在同预算 $K_H{+}K_C$、同 Zipf α 下」）。
5. **证明 / 证明义务**：
   - `proven`：给出每步可检验的推导。
   - `partial`/`conjecture`：明确列出**还差哪几步**（证明义务清单），以及打算用什么工具（交换论证 / 马氏链稳态 / KKT / 凸性…）。
6. **代码锚点**：指出对应实现位置（`file:func`）。**理论必须与代码一致**；不一致时记录差异并以代码为准。
7. **反例义务**：尝试构造反例或边界场景（如 P7 在 $h_S{=}0$ 时空洞、P5 在 $K_H$ 过小时失效）。**一个好命题必须知道自己何时不成立。**
8. **经验衔接**：指出该理论对应 `EXPERIMENTS.md` 哪个级别的哪个测量（理论上界 vs 实测落差）。

## 9. 理论与实验的关系（不可越界）

- 理论给**上界 / 方向 / 解释**；实验给**真实数字**。
- 形如「OURS 应更快」的命题，其经验确认在 **L2 真机**（`EXPERIMENTS.md` §1）；本文不得引用未跑出的数字。
- 若实测与理论矛盾：**先怀疑假设**（A1/A2 是否在该场景成立？α 估计是否偏？），在本文记录"假设失效场景"，而非粉饰数据。这与 `OPTIMIZATION.md`「可解释才保留」一脉相承。
- 所有具体数字一律引用 `EXPERIMENTS.md §7.5 基线快照` 与 `results/raw/*.json`，**本文正文不复写数字**（避免过期、自相矛盾）。

---

# Part III — 定理 / 命题注册表（可扩展，不写死）

> 与 `EXPERIMENTS.md §7` / `OPTIMIZATION.md §6` 同范式：**流程靠规范稳定，命题靠注册表生长**。新增数学结论只**追加一行**并按 §8 SOP 补全，不改 Part I/II 的规范本身。

## 9.1 假设登记表（先声明前提）

| ID | 假设 | 现实依据 / 何时失效 |
|----|------|---------------------|
| A1 | 延迟序 $T_H\le T_C\le T_S$ | 真实硬件成立；异构内存或 SSD 极快时需复核 |
| A2 | 路由热度服从 Zipf(α) | profile 拟合良好时成立；路由近均匀（α→0）时 P1/P3 退化、MECC 收益趋零 |
| A3 | expert 大小 $s$ 同构、fp16 | 异构 expert 需对每个 $s_e$ 重写延迟项；非 fp16 触发 P8 复核 |

> 新增假设：追加一行，并在所有依赖它的命题的「依赖」字段引用。

## 9.2 命题注册表

> 状态：`proven` / `partial` / `conjecture` / `refuted`。**新增命题在此追加一行，并在 Part I 写正文 + 按 §8 填齐八项。**

| ID | 名称 | 级别 | 依赖 | 状态 | 正文 | 代码锚点 |
|----|------|------|------|------|------|----------|
| TH-001 | 命中率 = 调和数比 $H_k/H_N$ | proposition | A2 | **proven** | §2.2 | `compiler.py:zcdf` |
| TH-002 | α 的 MLE 闭式 $1+N/\sum\log r_i$ | proposition | A2 | **conjecture** | §2.3 | `compiler.py:estimate_alpha` |
| TH-003 | 期望延迟 $\mathcal{L}$ 对 $K_H,K_C$ 单调不增 | proposition | A1,A2 | **proven** | §3.1 | `compiler.py:optimize` |
| TH-004 | 最优分配 = 容量贪心填满（"Theorem 4"）| theorem | A1,A2,(C) | **partial** | §3.2 | `compiler.py:optimize` |
| TH-005 | 静态 CPU 池命中率塌缩→0 | proposition | A1,A2 | **partial** | §4.2 | `engine.py:_access_swapmoe` |
| TH-006 | 联合 LRU 包含性 ⇒ $h_S^{ours}\le h_S^{swap}$ | theorem | A1,A2 | **conjecture** | §4.3 | `engine.py:_access_ours` |
| TH-007 | SSD 命中率主导端到端延迟 | proposition | A1 | **proven** | §5.1 | `compiler.py:optimize` |
| TH-008 | 无损 / fp16 恒等 ⇒ PPL 不变 | theorem | A3 | **proven** | §6 | `engine.py`,`base/expert.py` |

## 9.3 待攻关清单（优先级建议）

> 这是给 agent 的"选题池"。证完后把对应行状态改为 `proven` 并补正文证明；被推翻则改 `refuted` 并记录反例。

| 优先级 | 目标 | 为什么重要 | 建议工具 |
|--------|------|-----------|----------|
| ★★★ | **TH-006**（联合 LRU 包含性）| MECC 相对 SwapMoE 的**结构性优势**全靠它；证成则 §4 从"直觉"升级为"定理" | 栈式包含性质（Mattson stack algorithm）、LRU 在 Zipf 流下的稳态分析 |
| ★★ | **TH-005**（静态池塌缩）| 解释实测 "CPU 命中 0%"，与 TH-006 互补 | LRU-Zipf 马氏链稳态 / 计数论证 |
| ★★ | **TH-004**（Theorem 4 全局最优）| 编译器的合法性背书；补交换论证 + 边际/容量两版关系 | 交换论证、KKT、凸/次模性 |
| ★ | **TH-002**（α MLE 严格性）| 让 profile 估计有理论保证；界定连续近似误差 | 离散 Zipf 对数似然、渐近正态 |

## 9.4 如何新增一条命题（给 agent 的 SOP 摘要）

1. 在 **§9.2** 追加一行，分配 `TH-00X`，填级别 / 依赖 / 状态(`conjecture` 起步) / 代码锚点。
2. 在 **Part I** 适当章节写正文：陈述 + 证明（或证明义务），按 **§8** 八项填齐。
3. 若引入新前提，先在 **§9.1** 登记假设。
4. 完成严格证明后把状态改 `proven`；若找到反例改 `refuted` 并在正文记录反例与教训。
5. 指出它对应 `EXPERIMENTS.md` 哪个级别的测量（理论↔经验衔接，§9 越界禁令）。
6. **不改 Part I §0–§6 的既有命题语义、也不改 Part II 规范**——除非发现错误（那属于修订，需在提交说明里写清"为何旧陈述错"）。

---

## 附：本文与其他文档的闭环

```
APPLICABILITY (何时有效，A1/A2 何时成立的现实边界)
      │
      ▼
THEORY (本文：为什么有效——上界与结构性优势，命题注册表)
      │  理论给方向/上界
      ▼
OPTIMIZATION (怎么改进——算法优化要回本文复核命题是否仍成立)
      │  改完去验证
      ▼
EXPERIMENTS (实际多少——L2 真机给真实数字，理论的经验确认)
```

> **一句话总规则**：**理论负责"为什么应该成立"并给上界，实验负责"实际成立多少"并给数字；二者各司其职、互不冒充。** 数学缺口诚实标注，命题靠注册表生长，规范保持稳定。
