# 黄标研究稿：实验图与替换清单

当前文件：`MECC_DAC_research_draft.pdf`。黄色表示目标或待补实测字段。图内文字同时写明 target／to measure，灰度打印时也能识别数据身份。

| 图／表标签 | 回答的问题 | 当前数据身份与来源 | 替换条件 |
|---|---|---|---|
| `fig:intro` | 两层分别管理会丢掉多少复用？ | A100 实测，`DATA_AUDIT.json` 中 main／independent | 原值保留；有新匹配运行时整组替换 |
| `fig:insights` a,d | 同样容量为什么需要按层规划？ | a 为 `motivation.ssd_misses_*` 理想值；d 是示意 | E05：同运行期、同字节、独立画像；保存各层配额与冷需求 |
| `fig:insights` b,e | HBM victim 是否仍应留在 CPU？ | b 为 A100 实测来源计数；e 是示意 | E06：补镜像／唯一覆盖／迁移字节和分阶段窗口 |
| `fig:insights` c,f | profile 过期后怎样恢复？ | c 为 `motivation.*_windows` 理想序列；f 是示意 | E07/E08：distinct inputs、no-shift、fixed、online-only、profile+online |
| `fig:target_mechanisms` | 放置、保留、适应各自有没有增量？ | 三模型组件理想 TPOT，`insight_ablation_targets` | E04–E08：分别锁定运行期、初态和切换协议；不可与整系统 QA/Code 组混为同一配置 |
| `fig:performance` | 当前同机运行期实际怎样？ | A100 实测；RF 比 MECC 略快的结果保留 | 与原始 `result.json` 对齐，不用目标图覆盖 |
| `fig:target_ablation` a | 每一项优化做了什么？ | `ablation_tpot_seconds` 目标 24/18/11/8；miss 目标 46/33/20/20 | E04：addition + removal；最后一项是否仅改善暴露时间需真实阶段字节支持 |
| `fig:target_ablation` b | 初始开销多久摊平？ | `startup_cost_seconds` 与 decode targets 的解析组合；交点 9 token 是目标算术 | E13：分别计 profile、compile、load、TTFT、decode；不能把目标交点写成测量结论 |
| `fig:target_models` | 模型、QA/Code 是否影响收益？ | 原有 8x7B/8x22B QA/Code 理想数组 | E01/E02：冻结每个模型和输入、长度、精度、真实字节预算与基线实现 |
| `fig:target_gpu` | 单卡节省配置数时付出多少延迟？ | 原有 1-GPU MECC 与 2/4/8-GPU resident 理想值；GPU-s 为乘积 | E03：最少可驻留的配置必须测；不是 FlashMoE 文献数字；没有 MECC 多卡设计点 |
| `fig:budget` | 已有两档预算发生什么变化？ | A100 实测 30/60 GB、4 prompts×16 outputs | 保持同口径；不拼接早期不同输入的 20 GB 数据 |
| `fig:target_quota` | 冷层工作区间内中间容量如何变化？ | `cpu_budget_gb` 与 `budget_tpot_seconds` 五点理想曲线 | E10：一套完整冻结协议；不能与上述两点实测混接 |
| `tab:checks` | 是否保持计算、是否真的遵守内存预算？ | PPL 为实测；独立参考 exact/zero 是黄标目标；物理字节留待测量 | E14/E15：实际峰值、mirror/staging、phase bytes、independent logits/routes/tokens |

所有目标字段和源 JSON 的 SHA256 见 `completion_figures/SOURCE_MANIFEST.json`。这些字段从未写回 `results/`，也没有登记为 verified。

未恢复的旧假设：物理内存图因 full-mirror 预算不成立而撤回；MECC 的多卡延迟点没有对应设计；人工 ±3% 波动没有实测来源。这些不能作为可提交的图使用。

全套输入/输出长度、batch、画像规模敏感性仍在 E09/E11/E12 黄项中。当前已有目标文件没有它们的数值，因此不伪装成已有曲线。
