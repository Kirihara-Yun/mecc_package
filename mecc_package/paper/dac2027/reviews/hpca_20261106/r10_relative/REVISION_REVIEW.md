# R10：以相对收益呈现主结果，并恢复对比机制的工作来源

日期：2026-11-07。承接 R09；已冻结的各版保留。

## 结果呈现

摘要、引言、主结果图和结论以加速比呈现 A100 实验。图 1、图 7 采用 `streaming latency / policy latency`，分别计算 decode 与 first-token speedup。虚线为 streaming 的 1.0。图 1 的 HDD 需求仍使用百分比。绝对延迟保存在第八页及 `RATIO_AUDIT.json`，原始运行 JSON 未改。

摘要以 streaming 的 1.77× decode 与 Fiddler 风格适配的 2.86× 首 token 为两个明确区分指标的结果。正文同时报告 Fiddler 风格的 1.12× decode 对比。主图保留全部六个完成策略，含 MECC I/O 与 FlashMoE-RF；没有通过删除竞争策略改变结论。FlashMoE-RF 相对 streaming 的 decode 为 1.81×，MECC 为 1.77×。

## 对比工作核查

已 fetch GitHub 远端，并核对版本控制内的结果、策略实现和复现审计。上一版的简写隐藏了来源，本轮恢复引用和工作名称：

| 运行 id | 正文身份 | 图中简称 | 证据 |
|---|---|---|---|
| `swapmoe` | SwapMoE-style FP16 adapter | Swap-style | `a100-main-swapmoe-20261104` |
| `fiddler` | Fiddler-style CPU-compute adapter | Fiddler-style | `a100-main-fiddler-20261104` |
| `flashmoe_rf_adaptation` | FlashMoE-RF adapter | Flash-RF | `a100-main-flashmoe_rf_adaptation-20261104` |

这些结果是已执行的共享 harness 机制适配。MoE-Infinity 有 benchmark 入口，但未发现可用结果；MoE-CORE 只有文献分析，没有已完成运行。因此没有把其他策略改名冒充两者的完整复现。

Streaming 的 `NaivePolicy.access` 保留初始 HBM 专家；miss 读取权重，但不插入 GPU 缓存。它并非完全没有缓存。SwapMoE 风格适配更新 GPU LRU、保留固定 CPU 集合。GPU/CPU 成员重叠是其覆盖效率的结构因素，不能只按“有无缓存”解释胜负。正文说明该差异，并保留其 0.60× streaming 的实测比例。第八页仍区分名义槽位与实际主存字节。

## 叙事调整

- 将 “rather than model loading alone” 改为请求复用与放置的正面因果关系。
- 将 “not equal demand” 改为层间需求分布及边际覆盖。
- 删除重复的独立缓存与联合缓存身份辩解，解释 victim 的 MRU→LRU 生命周期。
- 将 “does not require another reduction” 改为传输次数与暴露时长两个作用点。
- 将实测主存扫描改为相对 streaming 的收益，保留 HDD 需求变化。
- 正文解释方法和结果；第八页集中配置、复现身份、数据来源及黄色高亮含义。

## 保留与验证

保留 Introduction 四个部分、44 个引用键、15 张图、六页正文加一页引用和一页附录。设计数组及其黄色高亮保留，未新增实验结果。新比例登记在 `docs/PROVENANCE.md` MAIN-9–11，逐项原始数据检查列在 `RELATIVE_VALIDATION.json`。
