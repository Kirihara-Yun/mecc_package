# MECC：DAC 2027 论文与实验补全草稿

按用户指定主线写成：**单卡部署 MoE → 三项部署挑战 → 对应方法 → 未优化单卡 / MECC 单卡 / 多卡参考 → 消融与资源分析**。

## 直接阅读

- **11 月 8 日图 13/14 设计修订**：[R23 PDF](./reviews/hpca_20261106/r23_sensitivity_design/manuscript.pdf) / [第六页预览](./reviews/hpca_20261106/r23_sensitivity_design/page_6.png)。图 13 分别采用校准规模成对点图、输入长度双对数曲线和批量吞吐分组柱图；图 14 改用逐档容量的成对延迟端点。数据数组与黄色标记保留，字体与正文一致，已检查八页版式。

- **11 月 8 日图 5 轨迹重绘**：[R22 PDF](./reviews/hpca_20261106/r22_recency_tracks/manuscript.pdf) / [图 5 预览](./reviews/hpca_20261106/r22_recency_tracks/method_redesign/residency_cases.png)。用专家连续轨迹表示最近使用次序和 HBM/CPU 驻留变化；冷读的入口及淘汰的出口与轨迹相连。字体与正文一致，其余十五幅配图及已有数据保持不变，已检查实际栏宽与八页版式。

- **11 月 8 日图 5 字体与对齐修订**：[R21 PDF](./reviews/hpca_20261106/r21_state_figure/manuscript.pdf) / [图 5 预览](./reviews/hpca_20261106/r21_state_figure/method_redesign/residency_cases.png)。使用与正文相同的文字和数学字体，将淘汰 a4 写入第三行请求说明，三行均为两个 HBM 槽位和两个 CPU 槽位。正文、图 1 三列及其余配图保持不变。

- **11 月 8 日首图增加一列数据**：[R20 PDF](./reviews/hpca_20261106/r20_three_columns/manuscript.pdf) / [首图预览](./reviews/hpca_20261106/r20_three_columns/measured_figures/intro_evidence.png)。保留 R17 调整字号后的横向柱图配色、纹理、字体及柱高，增加同组实测的首 token 加速比；三列依次为解码、首 token、HDD 访问比例。

- **11 月 8 日引言柱图比例修订**：[R19 PDF](./reviews/hpca_20261106/r19_intro_bars/manuscript.pdf) / [图 1 预览](./reviews/hpca_20261106/r19_intro_bars/measured_figures/intro_evidence.png)。恢复原来的配色、纹理和双横向柱状图，调整柱宽、间距及坐标范围；原始数值保留，第一页右栏仍填充至距左栏底部不到一行。

- **11 月 8 日引言图重排**：[R18 PDF](./reviews/hpca_20261106/r18_intro_design/manuscript.pdf) / [三列备选图](./reviews/hpca_20261106/r18_intro_design/measured_figures/intro_alternative_three_columns.png)。主稿采用紧凑双面板：左侧解码加速，右侧 HBM/CPU/HDD 请求占比，全部沿用同组实测；其余配图保持 R17 原样。

- **11 月 8 日字号与第一页留白修订**：[R17 PDF](./reviews/hpca_20261106/r17_figure_type/manuscript.pdf)。按最新要求，只缩小四张图中超过正文大小的文字，其余十二张图保持原样，小字号不放大；第一页两栏正文底端相差不到一行。数值与图 11 配色保留。

- **11 月 8 日贡献对应修订**：[R16 PDF](./reviews/hpca_20261106/r16_contributions/manuscript.pdf)。三项贡献依次对应按层分配容量、保留 GPU 淘汰专家、按运行期请求更新驻留集合；实验验证不再单列为贡献，其余正文与配图保留。

- **11 月 8 日直接措辞修订**：[R15 PDF](./reviews/hpca_20261106/r15_direct_terms/manuscript.pdf)。正文和嵌入配图移除 victim、critical 等措辞，改为专家淘汰及权重到达后执行的具体描述；数值和图 11 配色保留。

- **11 月 8 日图 11 配色修订**：[R14 PDF](./reviews/hpca_20261106/r14_model_colors/manuscript.pdf)。三个模型使用蓝、青绿、橙三色与不同纹理，两个任务保持相同编码；数据和正文保持 R13 原样。

- **11 月 7 日实验一致性核对稿**：[R13 PDF](./reviews/hpca_20261106/r13_experiment_audit/manuscript.pdf) / [修改记录](./reviews/hpca_20261106/r13_experiment_audit/EXPERIMENT_AUDIT.md)。明确任务切换，补三模型两任务和候选策略目标，修正初始化摊销口径。实测保持不变，新增目标标黄，数据身份集中于第八页附录。

- **11 月 7 日实验分析修订稿**：[R09 PDF](./reviews/hpca_20261106/r09_analysis/manuscript.pdf) / [修改与检查记录](./reviews/hpca_20261106/r09_analysis/ANALYSIS_REVIEW.md)。移除第六页独立相关工作，必要引用并入前文；深化关键路径分量、画像迁移、容量增量、批处理及初始化摊销分析。逐段删去重复说明，保留 44 个引用、15 幅图、既有数组和六加一加一页结构。配置及数据性质说明集中于第八页，黄色高亮保留。

- **11 月 7 日图文排版修订稿**：[R08 PDF](./reviews/hpca_20261106/r08_layout/manuscript.pdf) / [逐页检查记录](./reviews/hpca_20261106/r08_layout/LAYOUT_REVIEW.md)。修正图 1 顶部位置、图 2 两排标题样式、Overview 章标题位置和方法栏底断行，复核前七页并处理段尾孤词及跨页说明；保留六页正文、第七页引用和第八页附录。既有数值、数组、引用及旧版均保留。

- **11 月 7 日逐段英文审阅与终校稿**：[R07 PDF](./reviews/hpca_20261106/r07_proof/manuscript.pdf) / [终校记录](./reviews/hpca_20261106/r07_proof/EDITORIAL_REVIEW.md)。R06 重写机械串联和重复解释，R07 继续核对主语、动作、术语和图文关系；保留四段引言、六页正文、第七页引用和第八页附录。冻结稿、配图、数据和附录均未覆盖。

- **11 月 7 日表达修订版**：[R05 PDF](./reviews/hpca_20261106/r05_direct/manuscript.pdf) / [修改记录](./reviews/hpca_20261106/r05_direct/CHANGELOG.md)。保留四段引言，正文直接说明问题、方法和结果；配置、计时、数据来源与黄色高亮含义统一移至第八页附录。仍为六页正文，第七页参考文献，图形和数值来源保持不变，冻结版未覆盖。

- **用户认可版已冻结，另存四轮修订**：[版本与评审索引](./reviews/hpca_20261106/README.md) / [冻结 PDF](./reviews/hpca_20261106/r00_frozen/MECC_DAC_title_highlight.pdf) / [最新冷读稿](./reviews/hpca_20261106/r04_coldread/manuscript.pdf)。每轮保存独立 PDF、源文件、评审、差异和检查记录；不覆盖冻结版，不改理想数组。最新稿完成方法语义、叙事和短句修订，总体条件推荐仍为 3/5；未将文字评分当作 strong accept。具体技术补强见索引。

- **当前黄标研究草稿**：[论文 PDF](./MECC_DAC_research_draft.pdf) / [LaTeX](./MECC_DAC_research_draft.tex) / [整篇预览](./editing/research_review/MECC_research_contact_sheet.png)。IEEE 9 pt、六页正文加一页引用。Introduction 保留四段结构，贡献分项换行；背景、三项动机和 Overview 按“初始放置—跨层级复用—在线更新”展开。保留 Overview 之前的图形设计，Method 重绘容量分配、缓存状态和传输时序三图。两张表均已删除，共 15 张图；新增来源／暴露时间分解、画像规模／输入长度／批量敏感性、跨任务画像矩阵。已逐页渲染，核对全部 12 个正文栏底部和图文位置。未实测数值用黄色及简短的 Illustrative 标识区分，正文清除 to measure 等编辑指令。
- 对这版的判断与处理见 [体系结构会议标准自审](./editing/ARCHITECTURE_REVIEW_20261106.md)。黄色占位如何逐项替换见 [实验图替换清单](./editing/RESEARCH_DRAFT_EXPERIMENT_REGISTER.md)。此稿用于补齐证据，不能据理想图宣称新增实测收益。
- 重建黄标稿：`python build_method_redesign.py` → `python build_completion_figures.py` → `python build_research_draft.py` → `latexmk -pdf -interaction=nonstopmode -halt-on-error MECC_DAC_research_draft.tex` → `python check_research_draft.py`。正文主线见 [conference_story.py](./conference_story.py)；目标字段及两个源文件的哈希在 [SOURCE_MANIFEST.json](./completion_figures/SOURCE_MANIFEST.json)。新增图的数组集中保存在 [narrative_targets.json](./narrative_targets.json)，未写回实测目录。

- **A100 实测阅读版**：[新版论文 PDF](./MECC_DAC_visual_revision.pdf) / [LaTeX 源文件](./mecc_dac2027_measured.tex)；配套 [组会 PPT](../current/MECC_A100_measured.pptx) / [PDF](../current/MECC_A100_measured.pdf)。实验图由 [build_measured_a100.py](./build_measured_a100.py) 从已提交的单次 A100 原始 JSON 生成，来源及哈希见 [DATA_AUDIT.json](./measured_figures/DATA_AUDIT.json)。主对比使用统一初态，反映当前运行期缓存机制；逐层画像、任务切换和多卡性能尚无可纳入的同口径实测。此前理想结果版保留在下项。

实测阅读版共六页正文加一页参考文献：第 1 页为摘要、四段引言和实测图；第 2 页为 Background、三项 Motivation/Insight 及同页英文机制图；第 3 页为正式框架图、Overview 和编译方法；第 4 页为运行期缓存及权重交付；第 5 页为主结果与缓存对照；第 6 页为容量扫描、Related Work 与总结；第 7 页仅为 44 篇参考文献。正文使用 IEEE 9 pt 双栏版式。机制图是示意，实验图来自已提交的 A100 JSON。章节与论述调整见 [measured_narrative.py](./measured_narrative.py)，图文位置及相关工作扩充见 [visual_revision.py](./visual_revision.py)。

摘要现为 98 词，参考 [Token-Picker 摘要](https://arxiv.org/abs/2407.15131) 的“问题—缺口—机制—结果”组织。Introduction 严格为四段：研究问题；相关工作及实测暴露的问题；MECC 的设计与解决方式；以（1）（2）（3）列出的贡献。第二段对应的 [引言实验图](./measured_figures/intro_evidence.pdf) 使用已提交的同机 A100 结果，并区分 decode latency 与包含各阶段的 HDD-demand share。

新版图形由 [build_manuscript_visuals.py](./build_manuscript_visuals.py) 绘制。三项 Insight 保留 PPT 的热度分区、联合缓存栈曲线和路由/驻留矩阵设计，改用英文与 Times New Roman；Method 新绘逐层放置、CPU-hit 状态变化和读盘/拷贝/执行时序图。Overview 使用项目正式 `figures/fig01_overview.pdf`。实验图的论文尺寸由 [build_compact_results.py](./build_compact_results.py) 控制。

重建新版：`python build_manuscript_visuals.py` → `python build_measured_a100.py` → `python build_measured_paper.py` → `latexmk -pdf -jobname=MECC_DAC_visual_revision -interaction=nonstopmode -halt-on-error mecc_dac2027_measured.tex`。

编译后运行 `python check_measured_layout.py`：核对六加一页、四段引言、44 篇引用，以及全部 9 张图与首次解释是否同页。当前 Motivation 的正文与图均在第 2 页；相关工作长比较移至第 6 页。检查结果见 [visual_revision_validation.json](./visual_revision_validation.json)，整篇版面见 [七页预览](./editing/layout_review/MECC_layout_contact_sheet.png)。

论文图借鉴 PPT 的颜色、纹理和并列比较方式，以英文和论文尺寸绘制。实测主图采用单栏 TPOT／TTFT 对比，缓存对照图展示延迟及 HBM／CPU／HDD 访问来源，容量扫描图随对应实验小节排布。PPT 第二页另标明相关工作与同机单卡对照的区别。

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
