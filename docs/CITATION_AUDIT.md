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
