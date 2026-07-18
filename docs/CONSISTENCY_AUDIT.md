# MECC 全仓口径与 Baseline 语义审计

> 首次审计：2026-07-18
> 范围：平台、加速口径、模型/Expert 体积、四策略精度与存储语义。
> 规则：本文件登记发现与处置，不替代 `PROVENANCE.md` 的数字裁决。

## 1. 权威层级

发生冲突时按以下顺序处理：

1. 数字、平台与时间：`PROVENANCE.md` + 结果 JSON 顶层字段；
2. 实验语义：`EXPERIMENTS.md` + 产生该 JSON 的实际命令/代码 revision；
3. 当前实现行为：`e2e/` 与 `mecc_framework/` 代码和 trace 测试；
4. 理论口吻：`THEORY.md` 命题状态；
5. README、STRATEGY、论文和汇报材料只能引用以上事实，不能反向定义事实。

## 2. 审计结论总表

| ID | 主题 | 权威/当前事实 | 冲突位置 | 状态 | 处置 |
|----|------|---------------|----------|------|------|
| CA-001 | Mixtral 主平台 | A100 80GB（PROVENANCE M5；JSON 顶层 `platform`） | 根 README、APPLICABILITY 曾写 RTX 5090 | **resolved** | 已统一为 A100；保留 `compiled_plan.hardware=rtx5090` 为历史配置串 |
| CA-002 | PAPER_WRITING 平台规则 | A100 80GB | §2/§4 检查清单采信 A100，§5 雷区表曾要求统一 RTX 5090 | **resolved** | §5 已修正为 A100 |
| CA-003 | 1.33× 与 1.62× | 1.33×=JSON 综合/吞吐口径；约1.62×=TPOT 比 | 多处写 1.6× 但未总是明确指标 | confirmed | 所有出现处强制带指标名；默认主 claim 用 1.33× |
| CA-004 | Expert 体积 | 336MB=实际加载张量；1407MB=论文理论三矩阵口径 | 论文与 JSON | explained | 两者可保留，但必须标口径，不直接比较 |
| CA-005 | 当前 e2e `swapmoe` 数值路径 | 当前实现没有量化，使用与 OURS 相同的 fp16 store | EXPERIMENTS 曾称其 2-bit 有损 | **resolved (naming split)** | 历史 id 保留、显示名定为 `swapmoe_fp16`；外部低比特基线预留独立 inactive id `swapmoe_quantized` |
| CA-006 | 主 JSON 的 SwapMoE PPL | JSON 确有 36.116，但当前 fp16 `swapmoe` 代码不能解释该差异 | `mixtral_real.json` vs `tiered_engine.py`/`policy_plugin.py` | **repository-untraceable** | M2b 已降为 unverified；仓库历史和日志均无独立量化命令，除非取得外部原始记录或重建独立 baseline，否则不得恢复主 claim |
| CA-007 | “同精度下更快”措辞 | 当前主表写的是 OURS fp16 vs 被标作 2-bit 的 36.116 基线，并非同精度 | README/APPLICABILITY/论文示例 | confirmed wording error | 分开写“OURS 无损”和“相对该有损基线的速度/质量折中”；同精度加速需 fp16 baseline 证据 |
| CA-008 | SwapMoE 存储层级 | 当前 e2e 模拟为动态 HBM + 静态 CPU + SSD fallback | STRATEGY 称原工作 HBM+CPU 无 SSD，ARCHITECTURE 表写其余落 SSD | explained but naming-risk | 明确“相关工作原语义”与“本 harness 在同容量约束下的适配语义” |
| CA-009 | `exact(lossless)` 字段 | `--skip_ppl` 时的路径标记，不是数值 PPL 测量 | 多个历史 JSON/日志可能被读成质量测量 | confirmed | schema/论文中称“fp16 路径标记”；只有数值 PPL 才算质量实测 |
| CA-010 | 旧 DeepSeek 论文表 3 | 无对应 JSON | PROVENANCE X1 | known | 禁止外引；按用户决定暂不复现时只能改用 verified D3 或删除该表述 |

## 3. Baseline 语义矩阵（当前代码）

| 策略 id | HBM | CPU | SSD fallback | 当前权重精度 | 当前代码锚点 |
|---------|------|-----|--------------|--------------|--------------|
| `ours` | 动态 LRU | 动态 LRU，HBM 淘汰降级、CPU 命中升级 | 是 | fp16 | `e2e/policy_plugin.py:OursPolicy` |
| `swapmoe` | 动态 LRU | 静态 top-K_C，不接收 HBM 回写 | 是 | **fp16（未发现量化调用）** | `e2e/policy_plugin.py:SwapMoePolicy` |
| `fiddler` | 热 expert 常驻/缓存 | 冷 expert 在 CPU 计算 | 是 | fp16 | `e2e/policy_plugin.py:FiddlerPolicy` |
| `naive` | 无持久快层优势 | 无动态 CPU 缓存 | 是 | fp16 | `e2e/policy_plugin.py:NaivePolicy` |

当前 harness 的 `swapmoe` 推荐显示名为 `swapmoe_fp16`，准确身份是“**SwapMoE-style 静态 CPU 策略的 fp16
同预算适配**”。第三方 `mixtral_offloading` 中确有 HQQ 2-bit 实现，但当前
`run_e2e.py` 没有调用该实现。除非找到主 JSON 的原始生成 revision/命令证明量化路径，
不能把 36.116 自动归因给当前 `swapmoe` policy。

## 4. 对外措辞临时规则

在 CA-005/006 关闭前：

- 可写：MECC 主结果文件记录 OURS 1.33×、OURS PPL 24.57、对照行 PPL 36.12；
- 必须加注：对照行的 2-bit/SwapMoE 实现映射正在核验；
- 不写：“当前四策略 harness 中的 fp16 SwapMoE 因 2-bit 导致 PPL 36.12”；
- 不写：“同精度下相对 36.12 基线更快”——24.57 与 36.12 显然不是同精度；
- 若要证明同精度更快，应使用同一 fp16 权重、相同 PPL 的 baseline 性能结果；
- 若要证明速度/质量 Pareto，应把外部 2-bit baseline 独立命名、独立实现和独立落盘。

## 5. P0 修复顺序

1. 修正 CA-001/002：纯文档平台错误。
2. 修正 CA-003/004/009：为口径补标签，不改历史数据。
3. 将 CA-005/006 登记到 PROVENANCE，临时降级 M2b 的语义状态。
4. [已完成] 从 git 历史、实验日志和旧脚本追查 `mixtral_real.json`：`36.116`
   与“去掉 HQQ、全 fp16”的 harness 同时首次出现在初始提交 `06381a3`；没有更早
   revision，已提交日志也无 Mixtral 数值 PPL 或独立量化命令。因此仓库内无法恢复
   该 baseline 身份。
5. 后续二选一：
   - 找到独立 2-bit baseline：拆分 policy id、命令、结果和论文行；
   - 找不到：保留原 JSON 作为历史未核实数据，移出主 claim，当前 fp16 harness 重建质量对照。
6. [已完成] `e2e/test_cache_consistency.py` 用共同微型 trace 逐访问验证四策略的
   HBM/CPU/static-CPU 驻留与命中类别在核心库和 e2e 之间一致。

## 6. 关闭条件

- 根 README、APPLICABILITY、PAPER_WRITING 与 PROVENANCE 的平台一致；
- 每个加速数字都带明确派生口径；
- `swapmoe` 的 fp16 策略结果与 2-bit 外部质量基线不再共用模糊身份；
- M2b 能定位到具体量化实现、代码 revision 和生成命令，或正式降为不可用；
- `verify_claims.py` 不只核对 JSON 数值，还能检查上述高风险文本规则。
