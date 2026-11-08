# R13 实验一致性与覆盖检查

## 修正内容

- E1 的 1.77× 保留原始测量。E3 的 3.00–3.26× 对应不同任务、初始化及容量，两组结果分开叙述。
- E2 将切换定义为 GSM8K→HumanEval，两个窗口各八个输入，画像来自 GSM8K。分配控制定义为等额、经验计数和秩模型分配；原柱高保留。
- E3 增加 Qwen2-57B-A14B 的两个任务目标点，形成三个模型×两个任务。Mixtral 原目标保留。
- E5 增加 MoEpic、Diff-MoE 候选路径和 HumanEval 目标。图中先按任务和阶段归一化，再跨任务计算几何均值。
- 初始化控制统一为 uniform/compiled 计划：目标解码成本为 12/8 s/token，与校准图一致。额外放置 18 s，交点为 4.5 token，首次整数收益在第五 token；64 token 时为 12.19/8.47 s/token。
- 初始化曲线仅含放置和解码，不含 prefill，不再称总响应成本。
- 补 E6–E10 默认配置和单变量范围。主机配额统一 GiB。迁移图中 Code 对应 HumanEval，缩写 HEval。

## 覆盖及身份

| 内容 | 模型及任务 | 当前身份 |
|---|---|---|
| E1 主结果与适配器 | Mixtral-8x7B / WikiText-2 | 原始单次 A100 测量 |
| E4 容量端点 | Mixtral-8x7B / WikiText-2 | 原始单次 A100 测量，输出长度与 E1 不同 |
| G1 短窗正确性 | 两个固定输入 | 已测路径诊断，非独立 HF 全驻留证明 |
| E2 分配、保留、切换 | 三模型 / GSM8K→HumanEval | 标黄的作者目标 |
| E3 跨模型 | 三模型 / GSM8K、HumanEval | 标黄的作者目标 |
| E5 六个候选基线与 MECC | Mixtral-8x7B / GSM8K、HumanEval | 标黄的作者目标，非完整原系统复现 |
| E6–E10 配额、校准、输入、batch、迁移 | Mixtral-8x7B / 三任务 | 标黄的作者目标 |
| 多卡参照 | 部署示例 | 标黄的作者目标 |

E1 所有测量图、原始结果和 RATIO_AUDIT.json 保持字节不变。FlashMoE-RF 更快的记录、MECC I/O 和其余策略完整保留于附录；未用目标数覆盖不利测量。E5 的排序不代表实测名次逆转。

MoEpic 的 whole-expert 控制不等于其完整分段系统。Diff-MoE 只核实出版元数据，全文和实现仍需检查。正式证据仍缺原系统对齐复现、多模型端到端、任务精度、独立正确性、重复测量及物理内存公平性。补图不等于补齐真机证据。

## 溯源和检查

新目标独立存于 EXPERIMENT_TARGETS.json。旧 ideal_assumptions.json、narrative_targets.json、BASELINE_TARGETS.json 原样保留。R00–R12 封存哈希逐项验证。

文献核对：[MoEpic 原文](https://arxiv.org/abs/2509.08342)；[Diff-MoE 出版记录](https://doi.org/10.1145/3712285.3759903)。后者通过出版者存入 Crossref 的元数据核实题名、作者、SC 2025 和 1951–1965 页；未据此推断未阅读的算法细节。

复建由 build_r13_experiment_audit.py 和 appendix_r13.tex 提供。在新目录运行 latexmk，封存前运行 check_r13_experiment_audit.py。检查涵盖比值、来源、旧版哈希、连续缓存状态、页数、图文同页、溢出和孤词。

verify_claims.py：OK=85、WARN=11、FAIL=0，警告为既有事项。该检查不把目标验证为真机结果，目标身份由本轮独立检查覆盖。
