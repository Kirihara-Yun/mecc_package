# 冻结基线与逐轮修订

冻结版保持不变。每轮有独立 PDF、LaTeX、评审、差异、语言检查、版式记录和预览。

| 版本 | 本轮工作 | PDF | 审阅记录 | 条件技术推荐 |
|---|---|---|---|---|
| R00 | 冻结用户认可的版本 | [冻结 PDF](./r00_frozen/MECC_DAC_title_highlight.pdf) | [冷读](./BASELINE_REVIEW.md) | 2/5 |
| R01 | 方法定义、预算、镜像、prefill/decode 与同步语义 | [PDF](./r01_method/manuscript.pdf) | [评审](./r01_method/REVIEW.md) | 2/5 |
| R02 | 四段引言、生命周期叙事、最近邻工作 | [PDF](./r02_story/manuscript.pdf) | [评审](./r02_story/REVIEW.md) | 3/5 |
| R03 | 短句、重复内容、三项动机、框架标签 | [PDF](./r03_language/manuscript.pdf) | [评审](./r03_language/REVIEW.md) | 3/5 |
| R04 | 逐句冷读、缩写、计时、公式解释、版式收口 | [最新审阅稿](./r04_coldread/manuscript.pdf) | [评审](./r04_coldread/REVIEW.md) | 3/5 |
| R05 | 11 月 7 日：直接陈述、删除自我辩护、配置与数据说明移至第八页 | [最新表达修订稿](./r05_direct/manuscript.pdf) | [修改记录](./r05_direct/CHANGELOG.md) | 本轮不评分 |

分数来自单一模拟评审，不是 HPCA 官方意见。按 [本轮协议](./PROTOCOL.md)，评审暂时接受图中的理想结果，不因它们缺少实测扣分，也不自动假定未展示的技术已成立。理想数组和已有实测均未改变，没有重新加入图内横条。

四轮之后，英文和结构问题已完成本轮处理；总体推荐仍未到 5。决定性问题是与最近邻系统的技术区别，以及编译、镜像预算和执行接口的闭合。见 [下一步技术工作](./TECHNICAL_NEXT_STEPS.md)。不通过修改评分或放大理想数字宣称达标。

R00 的冻结 SHA-256：`fe021a5c17de8588fb76a25f4411255764a31e885a98ab0b50eb57be59caf89a`。

R01–R04 均为六页正文加一页参考文献。R05 按最新要求另加第八页附录，配置、数据来源和黄色高亮含义集中在该页。各版保留 44 篇引用、15 张图和 Introduction 的四个部分。R02/R03 为中间稿，R04/R05 已重新利用前两页空间。各轮详情见 `VALIDATION.json` 和 `LANGUAGE_AUDIT.json`。

重建某一轮：在其目录运行 `latexmk -pdf -interaction=nonstopmode -halt-on-error manuscript.tex`。快照只读；需要继续修改时，先创建下一编号目录，避免覆盖。
