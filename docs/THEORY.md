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

### 2.3 命题 P2（有界离散 Zipf MLE）

代码 `compiler.py:estimate_alpha` 先按观测频次降序赋予秩 $r=1,\ldots,N$，
再在 $\alpha\in[0.5,3]$ 上最大化离散 Zipf 对数似然

$$
\ell(\alpha)=-\alpha\sum_r c_r\log r-M\log H_N(\alpha),
\qquad M=\sum_r c_r.
$$

> **命题 P2.** 当 $M>0$ 时，上述有界最大似然问题是凹优化；若 score 在区间内有根，
> `estimate_alpha` 的二分法收敛到该唯一根，否则收敛到相应边界。

**证明.** 一阶条件为
$\ell'(\alpha)=M\left(\mathbb{E}_{p_\alpha}[\log r]-\overline{\log r}\right)=0$，
其中 $\overline{\log r}=\sum_r c_r\log r/M$。又有
$\ell''(\alpha)=-M\operatorname{Var}_{p_\alpha}(\log r)\le 0$，
故 $\ell$ 为凹函数，且非退化 $N>1$ 时 score 严格递减，内部根唯一；无内部根时有界凹函数的最大值在边界。
代码按 score 符号进行固定次数二分，故得到该有界 MLE。$\qquad\blacksquare$

注意：把 expert 按观测频次重新排序本身会引入有限样本的 rank-selection bias；P2 证明的是
“给定该观测排序后”的有界离散 MLE，不声称消除了这一统计偏差。

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

**证明（TH-004，`proven`）.** 这里的硬件预算是两个独立上限
$K_H\le B_H=\lfloor\mathrm{hbm}/s\rfloor$ 与
$K_C\le B_C=\lfloor\mathrm{cpu}/s\rfloor$，并非可在 HBM/CPU 间兑换的共享预算。
由 P3，未填满且仍有未缓存 expert 时，增加任一 tier 容量不增大目标，因此最优解可取
$K_H=\min(B_H,N)$、$K_C=\min(B_C,N-K_H)$。再证按秩分配：若较高概率
$p_i\ge p_j$ 的 expert 位于较慢 tier $b$，而较低概率 expert 位于较快 tier $a$，交换二者
引起的目标变化为
$(p_iT_a+p_jT_b)-(p_iT_b+p_jT_a)=(p_i-p_j)(T_a-T_b)\le0$。
反复交换所有逆序对，即得到最热 $K_H$ 个放 HBM、随后 $K_C$ 个放 CPU 的全局最优排序。
这证明了代码实际实现的“独立容量上限 + 按秩填满”版本。若未来改成 HBM/CPU 可兑换的
共享成本预算，则需另立边际平衡命题，T4 不直接适用。$\qquad\blacksquare$

---

## 4. 为什么 OURS 优于静态放置（核心定理）

这是 MECC 相对 SwapMoE 的**结构性优势**所在，对应 `tuning_log.md` 实验 3 的关键现象：**OURS 的 CPU 命中率 5.5%，而 swapmoe/fiddler 的 CPU 命中率 = 0%**。下面给出数学解释。

### 4.1 两种 CPU 管理

- **静态（swapmoe）**：CPU 池在编译期固定为热度秩 $[K_H, K_H{+}K_C)$ 的 expert，运行期不变。代码锚点：`engine.py:_warmup`（`static_cpu`），`_access_swapmoe`（HBM miss 后**不**回填 CPU，CPU 只读静态池）。
- **联合动态（ours）**：HBM 与 CPU 是**一个联合 LRU 栈**——HBM 淘汰的 expert **降级**到 CPU（spill），CPU 命中的 expert **升级**回 HBM。代码锚点：`engine.py:_access_ours`（CPU 命中则 `cpu.pop` 升级）、`_evict_hbm_if_needed(spill_to_cpu=True)`（HBM 溢出降级到 CPU）。

### 4.2 命题 P5（静态 CPU 命中率普遍趋零——已反驳）

> **原命题 P5（refuted）.** 当 HBM 使用动态 LRU 时，静态 CPU 池命中率普遍趋于 0。

**反例.** 取 $N=3,K_H=1,K_C=1$，静态 CPU 保存 expert 1，并无限重复 trace
$[1,2]$。每次访问 1 都从静态 CPU 命中并进入 HBM，随后的 2 又将其从 HBM 淘汰；因此
静态 CPU 每两次访问命中一次，渐近命中率为 $1/2$，并不趋零。故“普遍塌缩”是错误的。
真实实验中的低静态 CPU 命中只能作为特定访问分布、容量和初始放置下的经验现象；若要形成
理论，必须显式给出 IRM/Zipf 参数、工作集与 $K_H$ 条件并证明定量界。

### 4.3 命题 P6（联合 LRU 的普遍包含性——已反驳）

> **原命题 P6（refuted）.** 对任意 trace 和相同总容量，OURS 的
> $(h_H+h_C)$ 不低于动态 HBM + 静态 CPU 拆分方案。

**反例（TH-006，`refuted`）.** 取 $N=3,K_H=1,K_C=1$，编译期排序为
$[0,1,2]$，故初始 HBM 为 $\{0\}$、CPU 为 $\{1\}$。访问 trace $[2,1]$：

1. 访问 2 时两方案均 SSD miss。OURS 将 2 升入 HBM、0 降到 CPU，并从 CPU 淘汰 1；
   静态拆分将 2 升入 HBM，但静态 CPU 仍保留 1。
2. 随后访问 1 时，OURS 发生 SSD miss，而静态方案 CPU hit。

因此静态方案的快层命中集合并不总被联合 LRU 包含，原普遍包含命题为假。机器可复核穷举器
为 `scripts/search_th006_counterexample.py`，回归测试固定了上述最小 witness。

**收窄方向.** 实验中观察到的优势仍可能在 IRM/Zipf 稳态、足够长 horizon、或满足特定
drift 条件时以**期望 miss 数**成立，但这需要新命题和独立证明；在完成前只能表述为经验观察，
不能再借用 Mattson 的单一 LRU 容量栈性质推到“两种不同策略”的包含关系。

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

**这是 MECC 相对任何改变权重数值的量化方案的定义性区别。** 当前 OURS fp16
PPL 24.57 已 verified；历史对照 PPL 36.12 的具体 baseline 身份为 unverified
（PROVENANCE X6），因此本定理不依赖、也不引用该归因。

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
| TH-002 | 给定观测排序的有界离散 Zipf MLE | proposition | A2 | **proven** | §2.3 | `compiler.py:estimate_alpha` |
| TH-003 | 期望延迟 $\mathcal{L}$ 对 $K_H,K_C$ 单调不增 | proposition | A1,A2 | **proven** | §3.1 | `compiler.py:optimize` |
| TH-004 | 独立 tier 容量下最优分配 = 按秩贪心填满 | theorem | A1,A2,(C) | **proven** | §3.2 | `compiler.py:optimize` |
| TH-005 | 静态 CPU 池命中率普遍塌缩→0 | proposition | A1,A2 | **refuted** | §4.2 | `engine.py:_access_swapmoe` |
| TH-006 | 联合 LRU 普遍包含性 ⇒ $h_S^{ours}\le h_S^{swap}$ | theorem | A1,A2 | **refuted** | §4.3 | `engine.py:_access_ours`; `scripts/search_th006_counterexample.py` |
| TH-007 | SSD 命中率主导端到端延迟 | proposition | A1 | **proven** | §5.1 | `compiler.py:optimize` |
| TH-008 | 无损 / fp16 恒等 ⇒ PPL 不变 | theorem | A3 | **proven** | §6 | `engine.py`,`base/expert.py` |

## 9.3 待攻关清单（优先级建议）

> 这是给 agent 的"选题池"。证完后把对应行状态改为 `proven` 并补正文证明；被推翻则改 `refuted` 并记录反例。

| 优先级 | 目标 | 为什么重要 | 建议工具 |
|--------|------|-----------|----------|
| 已反驳 | **TH-006**（联合 LRU 普遍包含性）| 最小反例 $N=3,K_H=K_C=1$, trace $[2,1]$；保留为教训 | 若继续，另立带 IRM/Zipf 稳态或 drift 条件的期望命题 |
| 已反驳 | **TH-005**（静态池普遍塌缩）| 周期 trace $[1,2]$ 下静态 CPU 渐近命中率 $1/2$ | 若继续，另立带分布与容量条件的定量命题 |
| 已证明 | **TH-004**（独立容量下按秩填满）| P3 + 交换论证已闭合；不覆盖可兑换共享预算 | 若改预算模型则另立命题 |
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
