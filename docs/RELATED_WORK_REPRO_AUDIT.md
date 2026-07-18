# 相关工作复现忠实度审计

> 审计日期：2026-07-18。目的不是否定已有对比，而是区分作者原实现、论文机制适配和
> 模拟器，避免把不同证据等级合并成“官方复现”。

| 策略 | 当前覆盖 | 忠实度裁决 | 可支持的结论 |
|------|----------|------------|----------------|
| SwapMoE | e2e 真机路径 | fp16、同三层预算的静态 CPU 机制适配；不是原系统完整复现 | 可作同预算机制对照，不可代表原论文全部优化 |
| Fiddler | e2e 真机路径 | CPU 计算冷 Expert 的机制适配 | 可比较本 harness 下 CPU-compute 路径 |
| FluxMoE | cache/I/O 模拟与并发脚本 | 机制模拟；没有当前 e2e 主表行 | 只支持 D1 趋势，不支持 D2 真机系统胜负 |
| MoE-Infinity | 未跟踪 benchmark 草稿 | 外部包入口未锁版本、预算和 schema | inactive，不引用结果 |
| FlashMoE | `flashmoe_rf_adaptation` | 公开 recency/frequency 特征的确定性等权适配；作者训练 FFN 权重/代码未公开 | 可作单变量缓存机制对照；不得称官方实现或完整复现 |

## FlashMoE 适配边界

主来源：[FlashMoE, arXiv:2601.17063](https://arxiv.org/abs/2601.17063)。论文公开了
recency 特征 `1/r_t`、frequency 特征 `f_t/max(f)`、三层 FFN 结构与 Belady 标签生成思路，
但未公开训练后参数或可执行实现。本仓适配保持 HBM LRU、SSD/store、fp16 权重、输入和
`K_H/K_C` 不变，只把 CPU tier 淘汰改为 recency/frequency 等权评分。等权是明确的本仓
假设，不冒充论文训练出的预测器。

因此比较分两级：

1. 共同 trace/L0：验证状态转移、容量、命中记账和无损权重；不引用速度；
2. L2：同一 Mixtral store 与相同预算下比较端到端指标；预检不能代替正式重复实验。

若后续取得作者代码/权重，应新建独立 id（例如 `flashmoe_official`），不得静默替换本适配。
