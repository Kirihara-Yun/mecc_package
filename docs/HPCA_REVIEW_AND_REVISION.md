# 三视角模拟 HPCA 审查与修订记录

修订日期：2026-10-28。审查由三个独立 AI 协作者完成，分别承担体系结构、实验计量、基线有效性视角；不是实际 HPCA 审稿，不代表程序委员会决定。审查对象是 PPT 的论证及其代码/数据支撑，不能用美化或反复角色扮演保证任何真实审稿人接受。

HPCA [2026 投稿指南的评价说明](https://hpca-conf.org/2026/wp-content/uploads/2025/07/sample_paper.pdf)接受建模、模拟、原型和真实系统等多类方法。这里的问题不是“模拟一概不合格”，而是结论必须与其证据范围匹配。

## 1. 独立首轮意见

| 模拟审稿人 | 首轮判断 | 最关键的问题 | 修订动作 |
|---|---|---|---|
| A：体系结构与新颖性 | Reject | 三级缓存、画像与在线替换不是 2026 年独有机制；历史 uniform 配置没有隔离编译器价值 | 更新最新机制事实表；把中心问题收窄为有限请求时域中先验的独立收益；加入全局 LRU 参考 |
| B：因果实验与计量 | Reject | 曲线是手填预期，实际字节、预取和计数窗口未对齐，异步正确性未验证 | 实际运行隔离 D1 回放；固定 trace/容量；混杂项进入 X7–X9 和硬件 P0 清单 |
| C：基线公平性与外部有效性 | Reject | 相关工作错标；同一历史结果同时作动机与验证；缺真实 MoE 时序和强基线执行 | 纠正文献事实；动机改用独立 D1 characterization；历史结果标为参考；增加负对照与真实 trace 采集要求 |

三位都指出：“更多内存降低等待”“SSD 慢”“热点可能变化”是背景；“我们的完整方案更好”的曲线也不能自动成为动机。新的问题必须在相同条件下能够被实验推翻。

## 2. 三个动机的实际修改

1. **初态贡献**：保持相同联合 LRU，只改变独立画像/随机初态。左图为前若干请求的累计 SSD demand misses，右图为固定种子中初始覆盖与 held-out 请求热度。观察的是初态效应，不把长期在线缓存收益算给编译器。画像、编译和预热的成本须在硬件验证中另计。
2. **时序与覆盖**：同阶段逐对象频次不变，只打乱阶段内请求顺序；比较固定 CPU、两层独立 LRU、排他联合 LRU。左图为 SSD misses/千请求，右图为实际生成序列的不同对象再访距离 CDF。动态性、跨层去重、实际唯一覆盖一起记录，不把整体规则比较称为单独 LRU 更新的净效应。
3. **先验与在线交互**：独立画像 × 固定/联合规则的 2×2；阶段切换事先定义，不按漂亮结果选段。图里保留画像静态失配、无画像联合臂接近完整臂等现象；右侧热图来自原始合成 trace，不手画热点。

三张动机图与第 14 页控制图均为**实际运行的 D1 抽象回放**，不再使用手填占位数组。它们没有真实 GPU、权重或 SSD 计时，不能外推为 A100 tok/s/TPOT。8 个合成种子的误差棒表示合成请求变异。

## 3. 二轮审查与协议修正

第一版 D1 的训练 iid Zipf 与测试局部工作集生成器不同。v2 改为相同生成机制、独立 RNG 的训练与测试；保留 v1 文件并披露修订。增加两层独立 LRU，记录实际跨层重复和唯一驻留数；增加普通全局 LRU，逐请求验证其 SSD miss 与排他联合模型一致。此结果表明该模型中联合 LRU 本身不是新替换算法。

首轮后已关闭：手填曲线；测试未来频率作为画像；没有同 trace 配对；仅展示有利情形；训练生成机制不一致；省略常规缓存机制对照。尚未关闭：真实 MoE 请求代表性、CUDA 正确性、物理字节公平性、端到端净收益、近期强系统基线与可辨识的新颖性。

二轮模拟结论是：**可复现机制证据与论证结构改善，但当前整体材料仍不具备可信的 Accept 证据链。** 不生成虚构的“三票 Accept”。

## 4. 文献事实纠正

- [Fiddler，ICLR 2025 §3.4](https://proceedings.iclr.cc/paper_files/paper/2025/file/8cd1ce03ea58b3d7dfd809e4d42f08ea-Paper-Conference.pdf)使用离线专家热度指导 GPU 常驻，旧表“历史热点预热 ✗”不准确。
- [MoE-Lightning，ASPLOS 2025 §4.2](https://pschafhalter.com/papers/2025-asplos-moe-lightning.pdf)具有内存约束下的策略规划，旧表“预算生成驻留方案 ✗”维度过宽。
- [SSD-LLaMA](https://arxiv.org/html/2609.18110)已有原生三级驻留与动态保留；[FlashMoE](https://arxiv.org/html/2601.17063v2)研究 SSD I/O 与学习式近期性/频率替换。
- [MoE-CORE](https://arxiv.org/html/2610.01950v1)明确组合离线领域画像、路由历史替换、逐层容量和预取；[ZipMoE（ICML 2026）](https://proceedings.mlr.press/v306/yang26ds.html)采用无损压缩和缓存亲和调度协同。

第 2 页因此改为机制/目标/比较地位的事实表。没有为实现“只有 MECC 全勾”而重新挑维度。列出系统不代表已完成公平性能比较。

## 5. 真机 P0：在新性能实验之前处理

以下为静态审查发现或证据缺口，均未擅自改动生产缓存实现。风险已登记 `PROVENANCE` X7–X9；历史 JSON 不修改。

1. **正确性**：`tiered_engine.py:253–268,360–364` 在 copy_stream 拷贝后 yield，`mixtral_tiered.py:85–92` 随即计算，加载迭代结束才同步。与[PyTorch 跨流依赖规范](https://docs.pytorch.org/docs/stable/notes/cuda.html#cuda-streams)对照，需验证使用前 event/wait 契约。先以同步路径为参考，比相同输入下 logits、router 选择、token；只有静态风险，未证明它是异常 PPL 根因。`skip_ppl` 输出的 exact(lossless) 也不等于实际等价检查。
2. **物理预算**：`tiered_engine.py:229–236`、`policy_plugin.py:76–123` 的 CPU 镜像，与 near-miss/staging 一并计费。区分 pinned/pageable，去重 storage，测 peak；同 K_H/K_C 不能自动称同物理字节。默认关闭所有预测/异步预取，再单独消融。
3. **计量窗口**：`run_e2e.py:210–238` 的 warmup/生成/PPL 分相位计数；`tiered_engine.py:351–364` 预取后被记为 HBM hit 的事件应按 demand 到来前来源另记。时间、SSD/H2D/D2H 字节与命中计数必须覆盖同一段工作。
4. **请求与输入**：采集真实 Mixtral route trace 和完整模型/输入哈希；当前本地只有聚合频次，不能重建再访距离。固定离线评测文本，下载失败不得静默更换质量语料。

## 6. WorkBuddy 执行次序与接收证据

G0：先回传 CPU/L0 完成记录、同步/异步等价对比、物理内存记账与分相位计数。没有 G0，通过的吞吐数字也不进入主结论。

G1：采集独立 profiling split 与 held-out split 的真实路由；保存时间顺序、每层 expert ID、窗口边界、模型/输入哈希，不只保存直方图。用相同 trace 跑四臂与普通三级 LRU/独立 LRU，先确认新 D1 观察是否在真实路由存在。若没有明显漂移，撤去“自然强漂移”叙事。

G2：独占 A100、按实际资源上限运行至少 3 次独立重复。报告绝对 TTFT/TPOT/吞吐、SSD bytes/token、迁移字节、峰值显存/CPU、初始化与画像成本。将先验的节省与额外成本都计入服务请求时域；不得筛最佳运行。

G3：锁版本执行至少一个近期强外部系统；记录可比配置和无法对齐的模式。FlashMoE 的 RF 适配不能称官方实现，历史本地 fp16 对照不能称外部 SwapMoE 原系统。统一 checkpoint、精度、输入、actual bytes、冷读语义。

G4：在真实 workload、预算扫描、短/长 horizon、低偏斜和无漂移对照中保留全部结果。若画像增量仍小，应缩小编译器主张或重新寻找真实可测差异，不能靠措辞声称取得新颖性。

达到上述条件后再请求三视角复审；审查结果由证据决定，不能预先约定 Accept。

## 7. 交付与复现

- PPT：`mecc_package/paper/MECC_HPCA_review_revision.pptx`，PDF 同名。
- 数据：`mecc_package/results/raw/motivation_causal_replay_20261027_v2.json`；协议 `docs/HPCA_CAUSAL_REPLAY_PROTOCOL.md`。
- 回放：`python mecc_package/scripts/motivation_causal_replay.py`。
- 制图：`python mecc_package/paper/build_mecc_hpca_revision.py`。
- 数字自检：`python mecc_package/scripts/verify_claims.py`。检查数值与原始文件一致，不表示 G0–G4 已通过。
