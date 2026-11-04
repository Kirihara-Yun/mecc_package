# MECC：DAC 2027 理想结果论文设计稿

按用户指定主线写成：**单卡部署 MoE → 三项部署挑战 → 对应方法 → 未优化单卡 / MECC 单卡 / 多卡参考 → 消融与资源分析**。

## 直接阅读

- **内部审阅版论文**：[无过程标记 PDF](./mecc_dac2027_clean.pdf) / [LaTeX 源文件](./mecc_dac2027_clean.tex)。沿用理想数字和 IEEE 9 pt 排版，共 6 页正文 + 1 页参考文献；数据身份与投稿要求保存在 [独立说明](./clean_review/SOURCE_NOTE.json)。配套 PPT 是基于现有 `MECC_HPCA_review_revision.pptx` 修改的 [17 页版本](../current/MECC_HPCA_current.pptx) / [PDF](../current/MECC_HPCA_current.pdf)。
- 当前论文与 PPT 将 MECC 的冷存储统一称为 HDD。A100 测试机提供的是 `ROTA=1` 的 RAID 逻辑设备，控制器后的物理盘清单尚未取得；目前没有 SSD/NVMe 对照测量。被引工作的 `SSD-LLaMA` 名称及其 SSD 设计描述不改动。此次只调整介质口径和配图标注，理想示例数值未重算。
- **历史配图候选**：[HPCA / ASPLOS / OSDI 三套设计](../archive_unused_20261102/dac2027_variants/venue_designs/MECC_venue_design_chooser.html) / [早期 A/B/C 版](../archive_unused_20261102/dac2027_variants/figure_variants/MECC_figure_chooser.html)。两组候选均已归档，当前论文未使用。
- **零基础中文解读**：[浏览器阅读版](./MECC_BEGINNER_GUIDE_ZH.html) / [Markdown 原文](./MECC_BEGINNER_GUIDE_ZH.md)。从 MoE、显存和主存讲起，包含完整缓存例子、七图导读、公式拆解和自测题；明确区分假设目标与实测证据。
- **历史带标记版**：[mecc_dac2027_polished.pdf](../archive_unused_20261102/dac2027_previews/mecc_dac2027_polished.pdf)，保留原来的高亮标记和 AI 披露，供核对理想数字来源。
- 历史配图预览见 [figure_gallery_polished.pdf](../archive_unused_20261102/dac2027_previews/figure_gallery_polished.pdf)。
- `mecc_dac2027.tex`、`references.bib`：可编辑论文源文件。
- `ideal_assumptions.json`：全部理想数字集中列出，**不是实验数据**。
- `REQUIREMENTS_AND_FIGURE_STUDY.md`：DAC 2027 要求、截止时间、获奖论文配图研究和引用核实。
- `WORKBUDDY_EXPERIMENT_HANDOFF.md`：将理想稿变成真实结果的具体实验清单。
- `EXPERIMENT_MATRIX.md`：完整实验覆盖矩阵，逐项标明当前正文覆盖和未展开项，并包含原项目工程消融。
- `editing/LINE_EDIT_REVIEW.md`：逐章润色记录与参考材料范围；`editing/lineedit_diff.html` 可逐行对照修改前后。
- `editing/FULLTEXT_READING_AND_REVISION.md`：收到 9 篇原文后的阅读范围、事实核对与第二轮修订；`editing/fulltext_revision_diff.html` 为本轮对照。
- `validation.json`：页数、9 pt、匿名元数据、引用和数值内部一致性检查。
- `CITATION_COVERAGE.md`：新增 17 项文献的原始来源、版本与正文作用。
- `FILL_IN_GUIDE.md`：高亮颜色、正文/图表数值对应关系与填写顺序。
- `editing/VISUAL_POLISH_REVIEW.md`：本轮 HPCA/ASPLOS 原图阅读范围、图形/写作修订与复核清单；没有采用 PRICE 图形。
- `visual_validation.json`：框架图所属页、字体、矢量输出、文字边界、术语和第六页利用情况。
- `reviews/REVISION_RESPONSE.md`：四个独立模拟审稿视角、逐项修改及待完成的证据门禁；`reviews/round0/` 与 `reviews/round1/` 保存冻结稿和评审记录。

## 当前状态

用户明确要求先写理想实验结果。因此全文、图注、PDF 元数据、每页页脚和每张数字图均标识假设状态；真实 D1 / 历史 D2 数据保留独立，未被替换，未将假设值登记为 verified。此版用于确定论文形态，**不能直接投稿**。

审稿修订进一步撤回了全镜像模式下不成立的主存分项示例，以及没有相应系统设计的 MECC 多卡曲线。原始假设数组为可追溯性保留，不代表经过资源验证。格式、引用及算术检查通过也不等于科研结论成立，更不等于接收保证。

“8 卡 1 秒、1 卡 8 秒”统一定义为 **TPOT 秒/token** 的目标示例，不能误认成请求总耗时或 FlashMoE 的实测结果。两者都是 8 GPU-s/token，仅说明加速卡占用与响应延迟的取舍，不说明电能或金钱成本降低 8 倍。最少可行的 2/4 卡参考也列入计划，避免只挑 8 卡构造有利比较。

## 构建

依赖：Python + matplotlib + numpy；TeX Live（IEEEtran、newtx、hyperref、BibTeX 等）；PyMuPDF 用于验证/图册。

在本目录执行：

```powershell
python build_ideal_figures.py
pdflatex -interaction=nonstopmode -halt-on-error mecc_dac2027.tex
bibtex mecc_dac2027
pdflatex -interaction=nonstopmode -halt-on-error mecc_dac2027.tex
pdflatex -interaction=nonstopmode -halt-on-error mecc_dac2027.tex
python verify_draft.py
```

图 1、图 3 是机制示意图，已附 PDF/SVG，可直接编译。如需重画：

```powershell
python -c "import build_figures; build_figures.overview(); build_figures.retention()"
```

`build_figures.py` 的完整执行另外依赖仓库中的冻结真实证据 JSON，只重画隔离的可核验图，不执行 GPU 推理、不改实验数据。图内字体与正文分别控制，正文 9 pt 不代表图标签必须和正文一样大。

模板使用原版 IEEEtran 类文件。原始许可证见 `template/IEEEtran.cls`。未改版心/行距。投稿要求以 2027 官网为准，而不是 2026 的 ACM 模板。AI 生成披露保留在正文末尾，不能在未经重新评估真实使用范围时随意删去。

## 实现与设计的对应

- 画像排序、Zipf 模型、放置计划：仓库已有；逐层顺序分配是启发式，不声称全局最优。
- HBM/CPU 升降级：仓库已有；实际 CPU 镜像/缓冲尚需物理字节闭环。
- 使用前 readiness event、完整阶段计数、总物理 cap 与强基线复现：本文描述目标契约，**不声称现有 CUDA 代码已经全部达成**。以仓库 `docs/PROVENANCE.md` 的 X7–X9 与 handoff 为准。
- 8x22B、多 GPU、理想吞吐/TPOT、三次假设波动、零质量差与资源峰值：均未作为真实新实验执行。

原稿 `../mecc_paper.tex`、PPT、真实结果均保持原样。新稿全部在独立目录，便于回滚或换入真数据。
