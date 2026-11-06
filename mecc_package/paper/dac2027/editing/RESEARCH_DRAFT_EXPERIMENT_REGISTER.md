# 黄标研究稿：实验图与替换清单

当前文件：`MECC_DAC_research_draft.pdf`，六页正文加一页引用，15 张图，无表格。黄色与简短的 Illustrative 标识区分目标和实测；正文及图注已清除 to measure 和运行任务指令。

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
| 容量小节正文 | 已有两档预算发生什么变化？ | 保留 A100 实测 30/60 GB、4 prompts×16 outputs 数值，删去重复的两点图 | 保持同口径；不拼接早期不同输入的 20 GB 数据 |
| `fig:target_quota` | 冷层工作区间内中间容量如何变化？ | `cpu_budget_gb` 与 `budget_tpot_seconds` 五点理想曲线 | E10：一套完整冻结协议；不能与上述两点实测混接 |
| `fig:target_traffic` | 命中改善和交付调度有何区别？ | `narrative_targets.json` 中 demand/exposed 字段；来源占比和为 100%，时间和为 24/18/11/8 | E04/E14：同一运行计量来源及暴露时间，不能当物理字节 |
| `fig:target_sensitivity` | 画像规模、输入长度和批量怎样影响性能？ | 新增 profile/input/batch 理想数组；三图分别为 TPOT、TTFT、aggregate tokens/s | E09/E12：各面板独立固定协议，真实重复才允许误差条 |
| `fig:target_mismatch` | 画像是否可以迁移到不同任务？ | 新增 transfer_fixed/adaptive 理想矩阵，统一色阶 | E08/E11：固定画像任务及推理任务，记录前后窗口及 no-shift 对照 |

所有目标字段和两个源 JSON 的 SHA256 见 `completion_figures/SOURCE_MANIFEST.json`。这些字段从未写回 `results/`，也没有登记为 verified。两张检查／工作分类表已移除；PPL 数值保留在正文，物理资源与独立参考检查仍在原实验计划中。

未恢复的旧假设：物理内存图因 full-mirror 预算不成立而撤回；MECC 的多卡延迟点没有对应设计；人工 ±3% 波动没有实测来源。这些不能作为可提交的图使用。

新增目标曲线覆盖画像规模、输入长度、batch 和画像跨任务迁移；输出长度的目标分析仍由启动摊销图提供。所有新增值是图形设计输入，不是运行结果。
