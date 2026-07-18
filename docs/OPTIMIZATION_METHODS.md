# 优化方法设计稿（OPTIMIZATION METHODS，针对 MECC 本研究）

> **本文是什么**：把 [`OPTIMIZATION.md §6.2`](./OPTIMIZATION.md) 注册表里那些只占一行的 **candidate** 优化项，
> 展开成**有机理、有代码锚点、有预期指标、有风险、有验证路径**的完整方案设计稿。
> 它是「想清楚怎么改」的设计文档，**不是实验记录**。
>
> **本文不是什么**：不是已验证收益（数字一律见 [`EXPERIMENTS.md §7.5`](./EXPERIMENTS.md) + `results/raw/*.json`）；
> 不重造流程（流程/铁律/口径以 [`OPTIMIZATION.md`](./OPTIMIZATION.md) 为唯一权威）；不重证数学（命题见 [`THEORY.md`](./THEORY.md)）。
>
> **状态约定**：本文每个方法默认 `status = candidate（设计稿，未跑）`。这是用户明确要求——**只留设计文档，先不真跑**。
> 任何一项**真的实现并跑出 L2 证据后**，才把它从这里"毕业"到 `OPTIMIZATION.md §6.1`、状态改 `adopted/rejected`，并补 `evidence` 指针。
>
> **配套阅读**：方法学/铁律 [`OPTIMIZATION.md`](./OPTIMIZATION.md)、为什么有效 [`THEORY.md`](./THEORY.md)、何时有效 [`APPLICABILITY.md`](./APPLICABILITY.md)、级别语义 [`EXPERIMENTS.md`](./EXPERIMENTS.md)、架构 [`ARCHITECTURE.md`](./ARCHITECTURE.md)。

---

## 0. 怎么读这份设计稿（与现有体系的关系）

```
OPTIMIZATION.md          ← 规范层：优化分几类、怎么验证、铁律、注册表（权威，稳定）
       │  §6.2 candidate 只有一行「想法」
       ▼
OPTIMIZATION_METHODS.md  ← 设计层（本文）：把每个 candidate 展开成可落地的方案设计稿（不跑）
       │  实现并跑出 L2 证据后 →
       ▼
OPTIMIZATION.md §6.1     ← 已落地层：adopted/rejected + evidence 指针
```

- 本文**不新增**优化维度或铁律——完全沿用 `OPTIMIZATION.md §1` 的 **A 算法 / B 工程 / C 评测** 三分法，
  以及 §3 七条铁律（无损不可破坏、链路不可断、L0 不算性能、收益按维度认级别、results 不删、叙事一致、单变量）。
- 本文每个方法都标注：**维度 → 假设/机理 → 改哪（代码锚点）→ 预期指标与方向 → 验证路径（L0/L1/L2）→ 风险与回退判据 → 与 THEORY 命题的关系**。
- **MECC 主战场前提（不可忘）**：所有"收益"只有在 [`APPLICABILITY.md`](./APPLICABILITY.md) 的有效区
  （**模型 expert 总量 > 可用 CPU 内存、被迫落 SSD**）才有意义；在 L1（DeepSeek-V2-Lite，CPU 装得下、几乎不落 SSD）上只能看算法上界，**不得当主战场证据**。

> 每个方法卡片末尾给出**落盘提醒**：真跑时产出的 JSON 必须按新规范带顶层 `platform` + `run_time` 字段（见 [`SCHEMA.md §5`](../mecc_package/results/SCHEMA.md)），杜绝再次出现"平台/时间对不上"。

---

## 1. 优化机会全景（MECC 的瓶颈在哪，就往哪优化）

MECC 的端到端延迟由 [`THEORY.md §5`](./THEORY.md) 的取数延迟模型主导：
\[
\mathcal{L} = h_H T_H + h_C T_C + h_S T_S,\qquad T_S \gg T_C \gg T_H .
\]
由命题 **TH-007（SSD 命中率主导端到端延迟）**，降本质上有两条正交主线：

| 主线 | 物理含义 | 降的是 | 对应方法（本文编号） |
|------|---------|--------|----------------------|
| **(I) 压低 \(h_S\)** | 让更少 expert 落到 SSD（更准的放置 / 更聪明的动态升降级） | 命中率分布 | M3 路由感知放置、M4 自适应 α（**A 算法**） |
| **(II) 压低 \(T_S, T_C\) 的有效值** | 同样落 SSD/CPU，但把延迟藏进计算、或减少搬运量 | 单次取数延迟 | M1 SSD 异步读 overlap、M2 pinned buffer 池、M5 同层批量预取增强（**B 工程**） |
| **(III) 增强证据** | 不改方法，让结论更可信 | 可信度 | M6 更强 baseline、M7 更全 benchmark（**C 评测**） |

> 工程主线 (II) 的收益**只认 L2 真机消融**（铁律 4）；算法主线 (I) 先 L1 看上界、**最终必须 L2 兑现**；评测主线 (III) 不宣称加速。

---

## 2. 方法卡片（每张 = 一个可落地的优化设计稿）

> 卡片字段固定：**维度 / 注册表 id / 机理 / 改哪（代码锚点）/ 预期指标方向 / 验证路径 / 风险与回退 / THEORY 关系 / 落盘提醒**。
> 全部 `status = candidate（设计稿，未跑）`。

### M1 · SSD 异步读与计算 overlap（`async_ssd_read`）

| 字段 | 内容 |
|------|------|
| **维度** | B 工程 |
| **id** | `async_ssd_read`（已实现候选；因未运行正式 L2，状态 `parked`） |
| **机理** | 现状：SSD miss 时「冷读盘 → CPU → H2D → 计算」是**串行**的，冷读 ~10–100ms 直接压在关键路径上（`ARCHITECTURE.md §4` 标注的瓶颈）。本方法把 SSD 冷读放到独立 I/O 线程/`aio`，与**当前 token 的 HBM/CPU 命中专家的 GEMM 计算**及 PCIe 搬运 overlap，用"读完成屏障"保证数据就绪后才参与聚合。目标是把 \(T_S\) 的可见部分从「全量串行」降到「仅暴露未被计算掩盖的尾部」。 |
| **改哪（代码锚点）** | 当前候选落在论文主表路径：`e2e/tiered_engine.py:submit_load_to_cpu/prefetch_ssd_batch/_load_from_ssd` 提交 Future 并在消费时等待；`e2e/policy_plugin.py:OursPolicy` 消费。保持 expert 遍历/聚合顺序不变。核心库对应接入留待该候选取得 L2 正收益后再统一，避免扩大未验证改动。 |
| **预期指标方向** | TPOT ↓ / tokens·s ↑（SSD 命中率 \(h_S\) 不变，但 \(T_S\) 的有效暴露下降）；PPL **不变**（无损）。 |
| **验证路径** | L0 冒烟（`run_e2e.py --smoke`）确认读完成屏障没把链路改坏、PPL 仍 PASS → **L2 真机消融**（在真实 Mixtral、cold SSD 上 vs baseline，看 tok·s delta）。**L0 的 tok/s 不算收益**（铁律 3）。 |
| **风险与回退** | ① 读完成屏障若缺失 → 用到未就绪权重 → **破坏无损/正确性**（最高风险）；② overlap 收益取决于「同 step 内有足够的计算/HBM 命中可掩盖冷读」，若 batch 太小或 \(h_S\) 太高，掩盖不足、收益趋零；③ I/O 线程与 PCIe copy_stream 争用。**回退判据**：L2 tok·s 未正向或 PPL 偏移即回退（铁律 1/2）。 |
| **THEORY 关系** | 不改 \(h_S\)，只压 \(T_S\) 有效值；属 TH-007 中"\(T_S\) 项"的工程性削减。不触及 TH-006/TH-008（无损性 P8 须保持）。 |
| **落盘提醒** | 消融 JSON（如 `mecc_ablation/0X_async_ssd_read.json`）须带顶层 `platform` + `run_time`，并入 `ablation.sh` 作为新 `Opt N` 段。 |

---

### M2 · Pinned buffer 池复用（`pinned_buffer_pool`）

| 字段 | 内容 |
|------|------|
| **维度** | B 工程 |
| **id** | `pinned_buffer_pool`（OPTIMIZATION §6.2 已登记） |
| **机理** | 现状：`AsyncSwapEngine` 已有 GPU 端 `buffer pool`（`allocate_buffers`），但 **CPU 侧 pinned（page-locked）host 内存的注册/分配**仍可能在搬运路径上反复发生。每次 `pin_memory()` / cudaHostRegister 都有不可忽略开销，且 pageable 内存会把 PCIe 有效带宽打到 ~6–7GB/s（见 `measure_tiers.py` 的 pinned 修正说明）。本方法预分配一组**固定的 pinned host buffer 环**，SSD→CPU 与 CPU→GPU 都复用同一组 pinned 槽位，避免运行期分配/注册。 |
| **改哪（代码锚点）** | `mecc_framework/cache/swap.py:AsyncSwapEngine`（新增 pinned host buffer 环，与现有 `_gpu_buffers` 对称）；`base/store.py` 冷读落点直接写入 pinned 槽；`base/expert.py:ExpertWeights`（连续 storage，便于整块 pin）。 |
| **预期指标方向** | CPU→GPU 有效带宽 ↑、per-token 搬运抖动 ↓ → TPOT ↓；PPL **不变**。 |
| **验证路径** | 先用 `scripts/measure_tiers.py` 做 **micro-benchmark**（对比有/无 pinned 池的 transfer-only 带宽，属附录 ablation，不是主表）→ L0 冒烟 → **L2 真机消融**看端到端 tok·s。 |
| **风险与回退** | ① pinned 内存常驻会**抬高 CPU budget 占用**——必须测它是否挤占 \(K_C\)（可容纳的 CPU expert 数）从而**反而推高 \(h_S\)**；这是典型"局部优化全局变差"的陷阱；② buffer 环大小需与并发预取深度匹配。**回退判据**：若 CPU budget 被挤导致 L2 净收益为负 → 回退。 |
| **THEORY 关系** | 压 \(T_C\) 有效值；但若挤占 \(K_C\) 则间接抬高 \(h_S\)（TH-007），**净收益须 L2 统一裁决**，不能只看 micro-benchmark 带宽。 |
| **落盘提醒** | 同 M1：消融 JSON 带 `platform` + `run_time`；micro-benchmark 产物落 `results/raw/` 并标 `mode` 区分。 |

---

### M3 · 路由感知的层间/专家间联合放置（`routing_aware_placement`）

| 字段 | 内容 |
|------|------|
| **维度** | A 算法（**改方法本身，影响论文叙事**） |
| **id** | `routing_aware_placement`（OPTIMIZATION §6.2 已登记） |
| **机理** | 现状编译器 `optimize` 对**每层独立**按该层 Zipf α 做容量贪心 \((K_H,K_C)\) 切分（`THEORY.md §3` TH-004）。但真实路由存在**层间相关性与专家共现**：某些专家常被连续层一起激活。本方法把放置从"逐层独立"升级为"**联合热度**"——用 profile 出的层间共现/转移统计，把高共现专家组**优先同驻快层**，减少跨层 miss 链。 |
| **改哪（代码锚点）** | `compiler.py:generate_profile`（扩展为采集层间共现/转移矩阵，而非仅单层频率）；`compiler.py:optimize`（目标函数从逐层 \(\mathcal{L}\) 扩展到带共现项的联合目标）；运行期 `cache/engine.py` 的预取顺序据此调整。 |
| **预期指标方向** | SSD 命中率 \(h_S\) ↓（更准的快层覆盖）→ TPOT ↓ / tok·s ↑；PPL **不变**（仅改放置，不改数值）。 |
| **验证路径** | **A 类双级**：先 L1（DeepSeek-V2-Lite）观察 \(h_S\)/命中分布的**结构性上界**改善 → **必须 L2（Mixtral，落 SSD）兑现**才能宣称主战场有效（铁律 4 + `OPTIMIZATION.md §4`）。**禁止只拿 L1 上界当主战场证据。** |
| **风险与回退** | ① 共现统计需额外 profile，且对 prompt 分布敏感——**泛化性存疑**，换 workload 可能失效；② 联合目标可能破坏 TH-004 的"容量贪心最优"结构，需回 `THEORY.md` 复核命题是否仍成立（`OPTIMIZATION.md §7` 要求算法优化回 THEORY 复核）；③ 改放置算法 = 改方法，**必须 L2 重验**。**回退判据**：L2 未正向或机理不可解释 → rejected。 |
| **THEORY 关系** | 直接作用于 \(h_S\)（TH-007 主线 I）；若改变目标函数结构，需重审 **TH-003/TH-004**（单调性与最优分配），并检查是否削弱 **TH-006**（联合 LRU 包含性优势）。**这是本文里最"伤筋动骨"的算法改动，动它前先读 THEORY §3–§4。** |
| **落盘提醒** | L1/L2 产物都带 `platform` + `run_time`；L2 须满足 `EXPERIMENTS §3` 的"`ours` 的 SSD 命中率显著低于换页类 baseline"成功判据。 |

---

### M4 · 运行期自适应 α（`adaptive_alpha`）

| 字段 | 内容 |
|------|------|
| **维度** | A 算法 |
| **id** | `adaptive_alpha`（OPTIMIZATION §6.2 已登记） |
| **机理** | 现状 α（路由热度集中度）在**编译期**由 `estimate_alpha` 一次性估出并固定（`THEORY.md §2.3` TH-002，状态 `conjecture`）。当运行期真实负载与编译期 profile **漂移（drift）** 时，静态 α 导致放置失配。本方法在运行期用滑动窗口统计实际路由，**在线更新 α 估计**，触发阈值后**增量调整** \((K_H,K_C)\) 或 LRU 权重，使快层覆盖跟随真实工作集。 |
| **改哪（代码锚点）** | `compiler.py:estimate_alpha`（抽成可在线调用）；`cache/engine.py`（新增运行期路由计数 + 阈值触发的再分配钩子）；与 M3 共享 profile 采集基建。 |
| **预期指标方向** | 在 drift 场景下 \(h_S\) ↓；稳态无 drift 时应**至少不劣化**（净收益须 > 运行期统计/再分配开销）；PPL **不变**。 |
| **验证路径** | L1 观察"drift 注入下 OURS 对静态 α 的相对优势"（算法上界）→ **L2 兑现**。需专门构造/标注 drift workload，否则收益不可见。 |
| **风险与回退** | ① 运行期统计 + 再分配有**额外开销**，可能吃掉收益（典型"自适应反而更慢"）；② 频繁再分配引发**颠簸（thrashing）**——须加滞后/冷却；③ 与 TH-006 的稳态分析耦合，理论上界未定。**回退判据**：稳态场景净收益为负或出现颠簸 → 回退或仅在检测到 drift 时启用。 |
| **THEORY 关系** | TH-006 的普遍包含版本已被反例推翻；本方法只能检验特定 drift 分布下的经验收益。若要形成理论，须另立带 IRM/Zipf 稳态或 drift 条件的期望命题，实验不能替代证明。 |
| **落盘提醒** | drift workload 的定义、α 更新轨迹建议一并落 `results/raw/`；主 JSON 带 `platform` + `run_time`。 |

---

### M5 · 同层批量预取增强（`batch_prefetch` 的进一步）

| 字段 | 内容 |
|------|------|
| **维度** | B 工程 |
| **id** | `batch_prefetch_plus`（**新候选**，见 §3 注册表追加） |
| **机理** | `batch_prefetch` 已 adopted（同层将用专家一次性搬上、饱和 PCIe，`swap.py:batch_prefetch`/`consume_prefetched`）。增强点：① **跨 step 预测预取**——用 gate logits 的早期信号在 routing 完全确定前预取高概率专家；② 与 M1 的 SSD 异步读**联动**，对预测会 miss 到 SSD 的专家提前发起冷读。本质是把预取从"同层 reactive"升级为"前瞻 proactive"。 |
| **改哪（代码锚点）** | `swap.py:batch_prefetch`（接受预测候选集）；`cache/engine.py` / `e2e/tiered_engine.py`（在 gate 计算后、dispatch 前插入预测预取点）；与 M1 共享 SSD 读线程。 |
| **预期指标方向** | TPOT ↓（更多搬运被计算掩盖）；PPL **不变**。 |
| **验证路径** | L0 冒烟 → **L2 真机消融**；建议作为 `ablation.sh` 的独立 `Opt N`，与 baseline 的 `batch_prefetch` 行对比增量。 |
| **风险与回退** | ① 预测错误 → **无效搬运浪费 PCIe 带宽**，反而拖慢；预测命中率须先离线评估；② 与 M1 抢 I/O。**回退判据**：L2 净收益为负 → 回退。 |
| **THEORY 关系** | 压 \(T_C/T_S\) 有效暴露（TH-007 主线 II）；不改 \(h_S\) 与无损性。 |
| **落盘提醒** | 同 M1/M5：消融 JSON 带 `platform` + `run_time`。 |

---

### M6 · 引入更强 / 更新的 offload baseline（`stronger_baselines`）

| 字段 | 内容 |
|------|------|
| **维度** | C 评测（**不宣称加速，只增强结论可信度**） |
| **id** | `stronger_baselines`（OPTIMIZATION §6.2 已登记） |
| **机理** | 当前对手为 SwapMoE / Fiddler / naive（`ARCHITECTURE.md §5`）。引入更新的 SSD-offload / 换页 baseline，使"MECC 压低 \(h_S\)、同精度更快"的结论在更强对照下仍成立。 |
| **改哪（代码锚点）** | `e2e/policy_plugin.py`（新增策略插件）；先到 [`EXPERIMENTS.md §7.1`](./EXPERIMENTS.md) **登记 baseline**再实现（C 类扩展规则）。 |
| **预期指标方向** | 不产生方法收益；目标是"加入更强 baseline 后，OURS 的相对优势/无损卖点仍成立"。 |
| **验证路径** | 按 `EXPERIMENTS.md §7` 登记 → 在 L2 同条件（同预算 \(K_H{+}K_C\)、同 store、同 prompt、同卡）重跑 apples-to-apples。 |
| **风险与回退** | ① 必须**同预算同口径**对齐，否则不可比（`APPLICABILITY.md §5` 清单）；② 若新 baseline 是**有损**（量化），须单独归类、不能与无损 OURS 直接比加速而忽略精度（铁律 1 + `THEORY.md` P8）。 |
| **THEORY 关系** | 不改任何命题，只强化 P8（无损卖点）与 TH-006（结构性优势）的经验说服力。 |
| **落盘提醒** | 新对照 JSON 带 `platform` + `run_time`；baseline 是否有损须在文件与 PROVENANCE 标清。 |

---

### M7 · 扩充 benchmark（`extra_benchmarks`：MMLU / 长上下文吞吐）

| 字段 | 内容 |
|------|------|
| **维度** | C 评测 |
| **id** | `extra_benchmarks`（OPTIMIZATION §6.2 已登记） |
| **机理** | 当前以 PPL + 端到端 TTFT/TPOT/tok·s 为主。补充 MMLU（任务精度，进一步坐实"无损"）、长上下文吞吐（放大 SSD 压力、贴近主战场），让结论覆盖更多场景。 |
| **改哪（代码锚点）** | `e2e/run_e2e.py`（新增 benchmark 采集）；先到 [`EXPERIMENTS.md §7.2`](./EXPERIMENTS.md) 登记必采指标。 |
| **预期指标方向** | 不产生加速；MMLU 应显示 OURS 与原模型一致（坐实无损 P8）；长上下文应放大 OURS vs 换页 baseline 的 \(h_S\) 差距。 |
| **验证路径** | 按 `EXPERIMENTS.md §7.2` 登记后，在对应级别重跑；长上下文吞吐尤其要在 **L2（落 SSD）** 上跑才有意义。 |
| **风险与回退** | ① 长上下文显著拉长实验耗时与 SSD 磨损；② MMLU 等任务需正确的评测脚手架，避免口径错误被当成"精度下降"。 |
| **THEORY 关系** | 强化 P8（无损）与 TH-007（SSD 主导，长上下文下更明显）的经验证据。 |
| **落盘提醒** | 各 benchmark 结果 JSON 带 `platform` + `run_time`；指标先在 SCHEMA/EXPERIMENTS 登记字段。 |

---

## 3. 设计稿 → 注册表的衔接（落到 OPTIMIZATION.md §6）

本文 M1–M7 与 `OPTIMIZATION.md §6.2` 的对应关系（**本文负责"怎么改"的设计，注册表负责"状态/证据"的台账**）：

| 本文 | OPTIMIZATION §6.2 id | 维度 | 状态（现） | 实现并跑出 L2 证据后 |
|------|----------------------|------|-----------|----------------------|
| M1 | `async_ssd_read` | B | candidate（设计稿） | 移入 §6.1，标 adopted/rejected + evidence |
| M2 | `pinned_buffer_pool` | B | candidate（设计稿） | 同上 |
| M3 | `routing_aware_placement` | A | candidate（设计稿） | 先 L1 上界 → L2 定论，移入 §6.1 注两级证据 |
| M4 | `adaptive_alpha` | A | candidate（设计稿） | 同 M3 |
| M5 | `batch_prefetch_plus`（**新**） | B | candidate（设计稿） | 移入 §6.1 |
| M6 | `stronger_baselines` | C | candidate（设计稿） | 先 EXPERIMENTS §7.1 登记 |
| M7 | `extra_benchmarks` | C | candidate（设计稿） | 先 EXPERIMENTS §7.2 登记 |

> **流转规则（不变，引自 OPTIMIZATION §7）**：`candidate（本文设计稿）→ parked（开工待验证）→ adopted（L2 验证为正且可解释）/ rejected（为负，记原因）`。
> 每流转一次，**同步更新 `OPTIMIZATION.md §6` 那一行**——本文只维护设计，台账与证据指针归 §6。

---

## 4. 优先级建议（给后续要真跑的人）

> 纯建议，按"收益确定性 × 实现风险 × 与主战场相关度"排序。**用户当前要求是只留文档、不跑**，故此处不触发任何执行。

| 优先级 | 方法 | 理由 |
|--------|------|------|
| ★★★ | **M1 `async_ssd_read`** | 直击 `ARCHITECTURE.md §4` 标注的真瓶颈（SSD 冷读串行在关键路径）；纯工程、无损风险可控、L2 收益最可能显著。 |
| ★★ | **M3 `routing_aware_placement`** | 直接压 \(h_S\)（主线 I），与论文叙事和 TH-006 强相关；但改方法、需 L2 重验、泛化性存疑，工作量大。 |
| ★★ | **M5 `batch_prefetch_plus`** | 在已 adopted 的预取上增量，骨架现成（`ablation.sh`），低风险。 |
| ★ | **M2 `pinned_buffer_pool`** | 收益看 CPU budget 权衡，可能被 \(K_C\) 挤占抵消，需谨慎测净收益。 |
| ★ | **M4 `adaptive_alpha`** | 想法漂亮、与 TH-006 呼应，但运行期开销/颠簸风险高，理论上界未定，宜在 M1/M3 之后。 |
| 评测 | **M6 / M7** | 不产生加速，但显著提升论文可信度；M6 注意有损 baseline 的归类，M7 注意长上下文须在 L2 跑。 |

---

## 5. 通用红线（任何一项真跑前必须自检，引自 OPTIMIZATION §3）

- [ ] **无损不破坏**：`ours` 全程 fp16，PPL 与其它 exact 策略一致（违反 → 不再是 MECC 优化，见 `THEORY.md` P8）。
- [ ] **链路不断**：先过 L0 冒烟（`run_e2e.py --smoke`），四级换页/四策略/PPL 全 PASS。
- [ ] **L0 不算性能**：冒烟只回答"通不通"，其 tok/s 不进任何结论。
- [ ] **收益按维度认级别**：B 类只认 L2 真机；A 类 L1 仅上界、**最终 L2 兑现**；C 类不宣称加速。
- [ ] **单变量**：一次只改一处（对齐 `ablation.sh` 的 `Opt N` 模式）。
- [ ] **results 不删**：消融/历史 JSON/log 只追加。
- [ ] **落盘带平台+时间**：产物 JSON 顶层必须有 `platform` + `run_time`（`SCHEMA.md §5` 铁律，体检 `verify_claims.py` 会查）。
- [ ] **叙事一致**：主战场口径以 `APPLICABILITY.md` 为准，别把 L1 上界当主战场证据。

> 任意一条触红 → 立即回退，并在 `EXPERIMENT_LOG_TEMPLATE` 与 `OPTIMIZATION.md §6` 记清原因（标 rejected/parked）。

---

> **一句话总规则**：本文把"想怎么优化"写清楚（设计稿、不跑）；真要落地时，按 `OPTIMIZATION.md` 的流程跑、按 `EXPERIMENTS.md` 的级别取证、按 `THEORY.md` 复核命题、按 `SCHEMA.md` 带齐 platform+run_time 落盘——**设计与执行分离，规范保持稳定，方法靠注册表生长。**
