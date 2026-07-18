# 优化指导规范（OPTIMIZATION Runbook）

> 本文件是 **AI agent 做任何「优化」前必须读的执行手册**。
> 「优化」不止工程提速——它分多个维度：**算法/学术、工程/系统、实验/评测**。
> 不同维度的优化，**收益证据落在不同实验级别、能写进什么结论也不同**。
> 本文件定义：优化分哪几类、每类「改什么 / 收益在哪验证 / 能宣称什么 / 不能碰什么」，
> 以及**会增长的优化项如何登记，而不是写死成固定几条**。
>
> 联动阅读：[`EXPERIMENTS.md`](./EXPERIMENTS.md)（怎么跑实验、L0/L1/L2 语义）、
> [`APPLICABILITY.md`](./APPLICABILITY.md)（方法何时有效、结论口径）、[`../AGENTS.md`](../AGENTS.md)（硬约束）、
> [`OPTIMIZATION_METHODS.md`](./OPTIMIZATION_METHODS.md)（**具体优化方法的设计稿**：把本文件 §6.2 的 candidate 展开成可落地方案，含机理/锚点/预期/风险/验证路径）。
> 优化的"验证"复用 EXPERIMENTS 的级别与记录模板，本文件不另造一套实验流程。
>
> **分工**：本文件 = 规范层（分几类、怎么验证、铁律、注册表台账）；`OPTIMIZATION_METHODS.md` = 设计层（每个 candidate "怎么改"的设计稿，不跑）。设计 → 实现并跑出 L2 证据 → 回本文件 §6.1 标 adopted/rejected。

---

## 设计原则：可扩展，不写死

> **未来一定会有更多优化方向**（新算法、新系统手段、新评测）。
> 沿用 EXPERIMENTS.md 的范式：**"不变的"写进流程，"会增长的"登记进 §6 优化注册表，随时追加。**

| | 不变（长期稳定） | 会增长（登记进 §6，随时追加） |
|---|---|---|
| 维度划分 | 算法/学术、工程/系统、实验/评测 | 各维度下的**具体优化项** |
| 方法学 | 单变量 → 选证据级别 → 消融 → 可解释才保留 → 记录 | —— |
| 铁律 | 无损不可破坏、链路不可断、L0 不算性能、results 不删、叙事与 APPLICABILITY 一致 | —— |
| 口径映射 | "哪类优化的收益能写进哪级结论" | 具体优化项、具体收益数字（数字以 results/raw 为准） |

**给 agent 的总规则：**
1. **先归类再动手**：任何优化先判断属于哪个维度（§1），因为这决定了"收益在哪验证、能宣称什么"。
2. **新增优化项时，去 §6 注册表追加一行，不要改 §1–§4 的流程文字。**
3. **收益数字会过期**：正文只描述"怎么验证、口径是什么"，具体加速比/PPL 一律引用 `EXPERIMENTS.md §7.5` + `results/raw/*.json`，不在本文件复写。

---

## 1. 优化的三个维度（先归类，再决定怎么验证）

| 维度 | 改的是什么 | 收益证据落在（EXPERIMENTS 级别） | 能写进什么结论 | 例子 |
|------|-----------|----------------------------------|----------------|------|
| **A. 算法 / 学术** | 方法本身：热度建模 α、K_H/K_C 分配、动态 LRU 策略、放置算法 | **L1 看上界 + L2 定论**（算法改进先在 L1 观察结构性收益，**最终必须 L2 验证主战场仍成立**） | 算法贡献、相对 baseline 的**结构性**优势；**未经 L2 不得宣称"主战场有效"** | α 热度建模、编译期 K_H/K_C 分配、CPU tier 动态 LRU（对手静态放置=0% 命中） |
| **B. 工程 / 系统** | 实现效率：拷贝/搬运、I/O 调度、并发、预取、内存布局 | **L2 真机消融**（`ablation.sh`：每加一项立刻在真实 Mixtral 上跑 E2E 记录 tok/s 变化） | 端到端**性能/延迟/吞吐**改善（且不改变精度） | 零拷贝 HBM 淘汰、批量预取、pinned buffer 复用、SSD 异步读 |
| **C. 实验 / 评测** | 证据强度：更强 baseline、更全 benchmark、更严对照 | 不产生"方法收益"，而是**提升结论可信度**；按 EXPERIMENTS §7 注册表登记 | 不宣称加速，只让现有结论**更可信/可复现** | 新增 baseline、加 MMLU/长上下文、apples-to-apples 对齐 |

> **核心区别（必须内化）**：
> - **A 类（算法）**改了"方法是什么"，可能影响论文叙事，**收益必须最终在 L2 兑现**，不能只拿 L1 上界当数；
> - **B 类（工程）**不改方法、不改精度，只改"跑得多快"，**收益只认 L2 真机消融**；
> - **C 类（评测）**不改方法本身，只增强证据，遵循 EXPERIMENTS §6/§7 的"扩展"规则。
> - 三类都**绝不允许破坏无损路径**（见 §3 铁律）。

---

## 2. 统一优化方法学（任何维度都按此走）

```
1. 归类：判定本次优化属于 A(算法) / B(工程) / C(评测)（§1），据此确定"收益在哪验证、能写什么结论"。
2. 立假设：写清"改什么、为什么会更好、预期在哪个指标上、预期方向"。
   —— 例：零拷贝淘汰 → 省去 D2H 拷贝 → TPOT 下降 / tok·s 上升（B 类，L2 验证）。
3. 单变量改动：一次只改一处（对齐 ablation.sh 的 00_baseline → 01_xxx 模式），最小侵入（优先 replace_in_file）。
4. 选证据级别并验证：
     - 先 L0 冒烟确认"没把链路改坏"（必做，但 L0 数字不算收益）；
     - A 类 → L1 观察上界 + L2 定论；B 类 → L2 真机消融；C 类 → 按 EXPERIMENTS §7 登记后重跑对照。
5. 消融对比：与 baseline 同条件对比目标指标，得到带方向的 delta（ablation.sh 会自动汇总 vs baseline 的 %）。
6. 决策（可解释才保留）：
     - 收益为正且能解释机理 → 保留，进 §6 注册表标 status=adopted；
     - 收益为负/持平/不可解释 → 回退，并在记录里写清原因（标 rejected/parked），不硬留。
7. 记录：用 templates/EXPERIMENT_LOG_TEMPLATE.md 填一份，存 results/logs/；并在 §6 优化注册表追加/更新该项。
```

> 工程优化的现成骨架就是 [`../mecc_package/e2e/ablation.sh`](../mecc_package/e2e/ablation.sh)：
> `git checkout` 干净基线 → 逐步 `sed`/patch 一处优化 → 每步 `run_e2e.py` 跑真实 Mixtral → 末尾汇总 vs baseline。
> **新增工程优化就往这个脚本里追加一个 `Opt N` 段落**，不要另起炉灶。

---

## 3. 铁律（任何优化都不能违反，违反即作废）

1. **无损不可破坏**：`ours` 路径必须保持 fp16 无损（PPL 与其它 exact 策略一致）。
   任何"提速"若以掉精度为代价，**它就不再是 MECC 的优化**，而是变成了有损 baseline（如 SwapMoE 那类），必须如实标注、单独归类。
2. **逻辑链路不可断**：改完先过 L0 冒烟（`run_e2e.py --smoke`）——四级换页/四策略/PPL 链路必须仍 PASS。
3. **L0 不算性能**：冒烟只回答"通不通"，**绝不能拿 L0 的 tok/s 当任何优化的收益证据**。
4. **收益证据按维度认级别**：B 类工程收益只认 **L2 真机**；A 类算法收益最终也要 **L2** 兑现，L1 仅作上界参考（口径见 APPLICABILITY §4）。
5. **results/ 不删**：消融产物、历史 json/log 都是证据，只追加不删除（AGENTS.md 硬约束 4）。
6. **叙事一致**：任何"优化带来有效性/加速"的措辞，主战场口径以 APPLICABILITY.md 为准——**别把 DeepSeek(L1) 上的上界当主战场证据**。
7. **单变量**：一次一处，便于归因；多处同时改导致无法定位收益来源时，结论无效。

---

## 4. 各维度的收益口径速查（写结论时对照）

| 维度 | 验证级别 | 可以写 | 不可以写 |
|------|---------|--------|---------|
| A 算法 | L1(上界)+**L2(定论)** | "该算法改进在主战场 L2 带来 X（引用 results/raw）"；L1 仅称"算法结构性上界" | 仅凭 L1 就宣称"主战场更快/有效" |
| B 工程 | **L2 真机消融** | "在真实 Mixtral 上相对 baseline，目标指标变化 X%（引用消融 json）" | 凭 L0 或推断宣称提速；改了精度还称"无损提速" |
| C 评测 | EXPERIMENTS §7 登记后重跑 | "新增 baseline/benchmark 后，原结论仍成立/更可信" | 把"加了对照"说成"方法变快了" |

---

## 5. Agent 优化 SOP（精简版，贴着用）

```
归类(§1) → 立假设 → 单变量改(最小侵入) → L0 冒烟(必过) →
按维度取证据级别(§4) 跑消融 → 可解释才保留 →
填 EXPERIMENT_LOG_TEMPLATE 存 results/logs/ → 更新 §6 注册表。
任何一步触碰 §3 铁律 → 立即回退。
```

---

## 6. 优化注册表（会增长的优化项都登记在这里）

> 新增规则：追加一行。`status`：`adopted`(已验证保留) / `parked`(搁置,待验证) / `rejected`(验证后回退) / `candidate`(候选,未做)。
> `evidence` 列指向证据文件（消融 json / results/raw / 实验记录），**数字本身不写在这，引用文件**。
> 改了某项状态时同步更新本表，不要在 §1–§5 正文里硬列优化项。

### 6.1 已落地 / 在途

| id | 维度 | 一句话 | 改动位置 | 预期指标 | status | evidence |
|----|------|--------|----------|----------|--------|----------|
| `zero_copy_evict` | B 工程 | 淘汰时复用 CPU 镜像，免去 D2H 拷贝 | `mecc_framework/cache/engine.py`（见 ablation.sh Opt1） | TPOT↓ / tok·s↑ | adopted | `mecc_ablation/01_zero_copy_evict.json` |
| `alpha_heat_model` | A 算法 | α 路由热度建模驱动编译期放置 | `compiler.py` / `compile.py` | SSD 命中↓ | adopted | `results/raw/mixtral_real.json`（L2） |
| `kh_kc_alloc` | A 算法 | 编译期 K_H/K_C 预算分配（避免颠簸） | `compiler.py` | 命中分布合理化 | adopted | `tuning_log.md` 实验3（L1 上界） |
| `cpu_tier_lru` | A 算法 | CPU tier 联合动态 LRU（对手静态=0%命中） | `mecc_framework/cache/engine.py` | CPU 命中>0 | adopted | `tuning_log.md` 实验3 / L2 主表 |
| `batch_prefetch` | B 工程 | 批量预取降低 per-token 搬运 | E2E 预取路径 | tok·s↑ | adopted | `results/` 对照(+批量预取行，L1 上界) |

### 6.2 候选 / 待探索（agent 可从这里挑题，做完移到 6.1 并更新 status）

> **设计稿**：下表每个 candidate 的完整方案（机理 / 代码锚点 / 预期 / 风险 / 验证路径）见 [`OPTIMIZATION_METHODS.md`](./OPTIMIZATION_METHODS.md) 对应 M 卡片。本表只维护 id/状态台账。

| id | 维度 | 想法 | 设计稿 | 风险/注意 | status |
|----|------|------|--------|-----------|--------|
| `async_ssd_read` | B 工程 | SSD 读 futures 与 expert 计算 overlap，消费时设完成屏障 | METHODS §M1 | 已实现并过 L0；正式 L2 已取消，不能判断收益 | parked |
| `pinned_buffer_pool` | B 工程 | 复用 pinned buffer 减少分配/注册开销 | METHODS §M2 | 内存占用上升，需测 CPU budget | candidate |
| `routing_aware_placement` | A 算法 | 更细的层间/专家间热度联合放置 | METHODS §M3 | 改放置算法需 L2 重验主战场 | candidate |
| `adaptive_alpha` | A 算法 | 运行期自适应 α（随负载调热度权重） | METHODS §M4 | 增加运行期开销，需净收益 | candidate |
| `batch_prefetch_plus` | B 工程 | 前瞻预取（gate 信号预测 + 与 SSD 异步读联动） | METHODS §M5 | 预测错则浪费 PCIe；与 async_ssd_read 抢 I/O | candidate |
| `stronger_baselines` | C 评测 | 引入更新的 offload baseline | METHODS §M6 | 先在 EXPERIMENTS §7.1 登记 | candidate |
| `extra_benchmarks` | C 评测 | MMLU / 长上下文吞吐等 | METHODS §M7 | 先在 EXPERIMENTS §7.2 登记 | candidate |
| `<新优化>` | A/B/C | <想法> | METHODS §M* | <风险> | candidate |

---

## 7. 怎么扩展（给 agent 的明确许可与边界）

- **加一个工程优化**：往 `ablation.sh` 追加 `Opt N` 段 + 在 §6 追加一行。**不改 §1–§5**。
- **加一个算法优化**：改 `compiler.py`/`engine.py` 相应处，**先 L1 看上界，再 L2 定论**，§6 追加一行并注明两级证据。
- **加 baseline/benchmark（C 类）**：到 `EXPERIMENTS.md §7.1/§7.2` 登记，本文件 §6 只记一行指针。
- **状态流转**：candidate → (做了) parked → (L2 验证为正且可解释) adopted；为负则 rejected 并写清原因。
- **更新收益数字**：只动 `EXPERIMENTS.md §7.5` 基线快照 + `results/raw`，本文件正文不复写数字。

> 原则同 EXPERIMENTS：**流程靠语义稳定，优化项靠注册表生长。** agent 默认"追加"，只有改方法学/铁律时才动 §1–§5。
