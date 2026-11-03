# 论文引用核验记录

> 核验日期：2026-07-18。只记录已打开的主来源；标题、作者与标识符以链接页面为准。

| bib key | 核验主来源 | 裁决 |
|---------|------------|------|
| `shazeer2017outrageously` | [arXiv:1701.06538](https://arxiv.org/abs/1701.06538) | 标题、作者、2017 已核 |
| `jiang2024mixtral` | [arXiv:2401.04088](https://arxiv.org/abs/2401.04088) | 标题、作者、Mixtral 8 experts/top-2 已核 |
| `deepseek2024v2` | [arXiv:2405.04434](https://arxiv.org/abs/2405.04434) | 标题、团队作者、2024 已核 |
| `fedus2022switch` | [JMLR 23(120)](https://www.jmlr.org/papers/v23/21-0998.html) | 标题、作者、卷期页已核 |
| `mixtral_offloading` | [arXiv:2312.17238](https://arxiv.org/abs/2312.17238) | 应引用 Eliseev/Mazur 技术报告，而非把仓库作者写成单人 |
| `swapmoe2024` | [arXiv:2308.15030](https://arxiv.org/abs/2308.15030) | 旧稿“ACL 2024/Swap-based Expert Offloading”错误；已改真实标题与 2023 标识 |
| `fluxmoe2026` | [arXiv:2604.02715](https://arxiv.org/abs/2604.02715) | 旧稿“Streaming Expert Loading”非真实标题；已改真实标题与作者 |
| `fiddler` | [arXiv:2402.07033](https://arxiv.org/abs/2402.07033) | 标题、Kamahori/Gu/Zhu/Kasikci、2024 已核 |

本文未使用的旧 bib 条目已从 TeX 删除，避免“列了但未核/未引用”的投稿风险。引用核验不证明
本仓库 baseline 是相关工作原实现；实验中的适配身份仍以 `CONSISTENCY_AUDIT.md` 为准。

## 2026-10-28 汇报审稿修订补充

| 主来源 | 本次核实并用于第 2 页的事实 |
|---|---|
| [Fiddler ICLR2025 正式论文 §3.4](https://proceedings.iclr.cc/paper_files/paper/2025/file/8cd1ce03ea58b3d7dfd809e4d42f08ea-Paper-Conference.pdf) | 离线 expert popularity 参与 GPU 初始常驻选择；不能标为不具备画像预热 |
| [MoE-Lightning ASPLOS2025 §4.2](https://pschafhalter.com/papers/2025-asplos-moe-lightning.pdf) | 在内存约束下搜索执行/驻留策略；不能宽泛标为不具备预算规划 |
| [SSD-LLaMA arXiv2609.18110](https://arxiv.org/html/2609.18110) | 三级 SSD/RAM/VRAM 驻留与动态保留 |
| [FlashMoE arXiv2601.17063v2](https://arxiv.org/html/2601.17063v2) | 面向 SSD I/O 的学习式近期性/频率替换 |
| [MoE-CORE arXiv2610.01950v1](https://arxiv.org/html/2610.01950v1) | 离线领域画像、历史替换、逐层容量与预取组合；预印本，不虚构会议录用 |
| [ZipMoE ICML2026 官方页](https://proceedings.mlr.press/v306/yang26ds.html) | 无损压缩与缓存亲和调度协同 |

修订仅核文献机制，不借用其性能数字，不证明本仓库已复现其系统。具体审查意见见 `HPCA_REVIEW_AND_REVISION.md`。

## 2026-10-29 用户提供全文后的核对

用户提供 9 个 PDF，均可打开并提取正文；文件页数和哈希保留于本地 `paper/dac2027/editing/fulltext/manifest.json`。PRICE 用于写作参考，不新增无关技术引用。各篇的实际阅读范围与章节锚点见 `paper/dac2027/editing/FULLTEXT_READING_AND_REVISION.md`。

全文细化：FlashMoE §3.2 是以 recency/frequency 为输入的学习式距离/驱逐预测，不等于普通 RF heuristic；SSD-LLaMA §4.2 包含 transient admission、频率/近期性 VRAM 保留和 RAM LRU；MoE-Lightning §4.2 的搜索排除 disk 变量；MoE-CORE 的 exact path 与可选 expert substitution 分开。原文机制与本地适配性能不得互相替代。

## 2026-10-29 DAC 稿文献覆盖补充

DAC 稿从 11 项扩展为 27 项正文实际引用，新增 16 项的原始来源、出版版本及其论述范围见 [CITATION_COVERAGE.md](../mecc_package/paper/dac2027/CITATION_COVERAGE.md)。新增覆盖专家缓存/预测、异构内存规划、稀疏执行和 KV 管理；不借用外部性能数字作为 MECC 结果。此轮核验为元数据及摘要/官方页面，不声称对全部新增论文做了逐页全文精读。引用数量不构成接收保证。

随后的架构图修订核实并补入 Klotski（ASPLOS 2025，DOI `10.1145/3676641.3716261`），现为 28 项实际引用；具体版本及机制记录于上面覆盖文档末节。HPCA/ASPLOS 配图阅读范围与不采用 PRICE 图形的约束见 [VISUAL_POLISH_REVIEW.md](../mecc_package/paper/dac2027/editing/VISUAL_POLISH_REVIEW.md)。
