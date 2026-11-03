# 文献覆盖补充与核验（2026-10-29）

参考文献从 11 项扩展到 27 项。新增条目均在正文实际引用，没有使用 `nocite{*}` 堆积文献。增加引用的目的，是补全最近专家缓存/预测系统、异构内存规划、稀疏执行和 KV 管理之间的关系；篇数本身不构成接收依据。

下表记录本次打开的原始来源及其在正文承担的论述。核验范围为元数据、摘要/官方出版页和相应可见内容；不将此记录描述为对全部新增论文逐页全文精读。机制细节比较仍需结合完整原文，不能把摘要核验当作复现验证。既有 11 项的记录见 `REQUIREMENTS_AND_FIGURE_STUDY.md` 与仓库 `docs/CITATION_AUDIT.md`。

| 新增 bib key | 核验主来源 | 正文用途 |
|---|---|---|
| switch | [JMLR 23(120), 2022](https://www.jmlr.org/papers/v23/21-0998.html) | 总参数规模与稀疏激活计算分离 |
| gshard | [作者预印本](https://arxiv.org/abs/2006.16668)、[ICLR 2021 正式 PDF](https://openreview.net/pdf/cdb90e31da8446076492c5aef0c8c6ae35dd472a.pdf) | 条件计算与自动分片背景 |
| deepseekmoe | [ACL 2024 正式页](https://aclanthology.org/2024.acl-long.70/) | 细粒度与共享专家；不是本稿实测模型 |
| deepspeedmoe | [ICML 2022 / PMLR 162](https://proceedings.mlr.press/v162/rajbhandari22a.html) | 分布式 MoE 推理系统 |
| tutel | [MLSys 2023 正式 PDF](https://proceedings.mlsys.org/paper_files/paper/2023/file/5616d34cf8ff73942cfd5aa922842556-Paper-mlsys2023.pdf)、[作者版](https://arxiv.org/abs/2206.03382) | 动态并行与流水，不伪装为 SSD 缓存对照 |
| megablocks | [MLSys 2023 正式 PDF](https://proceedings.mlsys.org/paper_files/paper/2023/file/5a54f79333768effe7e8927bcccffe40-Paper-mlsys2023.pdf)、[作者版](https://arxiv.org/abs/2211.15841) | 稀疏训练 kernel，与专家交付问题区分 |
| flexgen | [ICML 2023 / PMLR 202](https://proceedings.mlr.press/v202/sheng23a.html) | GPU/CPU/磁盘张量规划、吞吐导向调度 |
| zeroinfinity | [作者预印本](https://arxiv.org/abs/2104.07857) | GPU/CPU/NVMe 训练先例；本条保守采用已核预印本元数据 |
| powerinfer | [作者版，注明 SOSP 2024](https://arxiv.org/abs/2312.12456) | 热神经元 GPU / 冷神经元 CPU 执行，不能与原生 MoE 完全等同 |
| llmflash | [ACL 2024 正式页](https://aclanthology.org/2024.acl-long.678/) | 超 DRAM 权重访问、窗口复用、flash 友好布局 |
| promoe | [作者版](https://arxiv.org/abs/2410.22134) | 通过中间结果预测后续专家；未猜测正式会议归属 |
| pregated | [Microsoft Research 正式出版页](https://www.microsoft.com/en-us/research/publication/pre-gated-moe-an-algorithm-system-co-design-for-fast-and-scalable-mixture-of-expert-inference/) | ISCA 2024 的预门控协同设计，与未改 router 的 demand-only 控制区分 |
| moeinfinity | [arXiv v3](https://arxiv.org/abs/2401.14361v3) | 激活 trace 引导替换/预取；采用 v3 标题与 2025 版本年份，不混用旧标题 |
| dsinference | [作者版](https://arxiv.org/abs/2207.00032)、[作者官方仓库出版清单](https://github.com/deepspeedai/DeepSpeed/blob/master/docs/index.md) | SC 2022；GPU/CPU/NVMe 推理，与多卡驻留参考区分 |
| pagedattention | [作者版](https://arxiv.org/abs/2309.06180) | SOSP 2023；KV 分配，与 expert 缓存区分 |
| sglang | [NeurIPS 2024 正式页](https://proceedings.neurips.cc/paper_files/paper/2024/hash/724be4472168f31ba1c9ac630f15dec8-Abstract-Conference.html) | RadixAttention / prefix KV 复用，与权重交付区分 |

新引用没有引入任何外部性能数字来充当本项目结果，也没有宣称已经复现这些系统。正式发表条目按核验到的出版版本引用；仅核实预印本的条目保留预印本身份。

## 架构图修订后的第 28 项引用

补入 `klotski`：[作者正式 ASPLOS 2025 PDF](https://yuyue.github.io/res/paper/Klotski-ASPLOS2025.pdf)，DOI `10.1145/3676641.3716261`。核对了作者列表、正式发表信息，以及 expert-aware multi-batch execution、constraint-sensitive planner、correlation-aware prefetcher 的对应描述。正文据此补充相关工作，不引用其性能数字。新增总数由 16 项变为 17 项，全文实际引用为 28 项。该论文的图形阅读另见 `editing/VISUAL_POLISH_REVIEW.md`。
