# Insight 页消融图：实验替换说明

第 7–9 页的右侧柱状图读取 `../dac2027/ideal_assumptions.json` 中的
`insight_ablation_targets`。**现有数值是设计目标，不是实测、模拟器输出或统计估计**。
源图由 `../build_insight_pairs.py` 生成。左侧机制图同样是示意。

Insight I 的目标流程是：用代表性输入运行模型，统计 `(layer_id, expert_id)` 的
路由次数；在每层内部对该层全部 expert 排序，再按容量决定初始显存、CPU、SSD 驻留。
不同层的相同 expert 编号对应不同权重。当前 `e2e/run_e2e.py` 只在显式传入兼容的
`--profile`（含数字层号键的 `per_layer_counts`）时执行热度排序；不传时按专家编号
自然序初始化。当前主结果 JSON 未保存画像文件路径或具体 `placement`，因此不能把
这张理想消融图说成已经由主实验验证。`profile_real_moe.py` 当前也不输出
`per_layer_counts`，需要补齐或使用另一个兼容的画像生成器后才能执行这项消融。

| 页码 | 要验证的想法 | 三个方案 | 横轴模型 | 必须固定的条件 |
|---|---|---|---|---|
| 7 | 按层画像是否改善初始放置 | 平均分配、全局排序、逐层画像 | Mixtral-8×7B / Qwen2-57B-A14B / Mixtral-8×22B | 每个模型内部固定权重精度、显存/CPU 实际可用字节、运行期缓存规则、预取策略和请求序列；只改初始放置 |
| 8 | CPU 层是否承接显存淘汰 | CPU 固定、独立更新、联合更新 | 同上三个模型 | 每个模型内部固定初始放置和实际缓存字节；只改运行期替换规则；记录 CPU 命中、SSD demand 读取及 H2D/D2H 字节 |
| 9 | 路由变化后能否及时跟进 | 固定驻留、独立更新、联合更新 | 同上三个模型 | 每个模型内部固定初始放置、WikiText-2→GSM8K 切换点、请求长度和缓存字节；只统计切换后的等长 decode 窗口 |

图中的模型名称指被测系统承载的 **MoE 模型**。WikiText-2 和 GSM8K 是构造输入的公开数据集；平均分配等三种策略才是这组消融的比较方案。Qwen2-57B-A14B 与 Mixtral-8×22B 尚未在本仓库端到端验证，当前柱高仍是理想目标。

右图指标为每 token 时间（TPOT，秒），越低越好。真实实验替换时，每个柱应来自
相同计时阶段和相同统计口径；多次重复应保存原始值，不能沿用设计目标的高度或推断误差线。
模型是否实际落 SSD、各策略能否在同一预算下运行，需要先按 `docs/APPLICABILITY.md`
与 `docs/EXPERIMENTS.md` 核验。正式发表或对外展示前，将数值登记到
`docs/PROVENANCE.md` 并运行 `mecc_package/scripts/verify_claims.py`。
