# MECC 演示文件索引

## 当前审阅版

| 用途 | 文件 |
|---|---|
| 可编辑 PPT（17 页） | [MECC_HPCA_current.pptx](./current/MECC_HPCA_current.pptx) |
| 渲染检查 PDF | [MECC_HPCA_current.pdf](./current/MECC_HPCA_current.pdf) |
| 第 10 页 Overview | 使用论文英文框架图 [fig01_overview.png](./dac2027/figures/fig01_overview.png) |
| 第一页预览 | [current_page1_review.png](./hpca_clean_ideal_assets/current_page1_review.png) |
| 第三页 Overview 预览 | [current_page3_review.png](./hpca_clean_ideal_assets/current_page3_review.png) |
| 构建入口 | [refine_hpca_talk.py](./refine_hpca_talk.py) |
| 图表数据与绘制 | [ideal_assumptions.json](./dac2027/ideal_assumptions.json)、[build_hpca_clean_talk.py](./build_hpca_clean_talk.py) |

运行 `python refine_hpca_talk.py` 构建 PPT；当前导出 PDF 使用 PowerPoint。脚本依赖同目录的两份参考源：`MECC_HPCA_review_revision.pptx`（旧版布局）和 `MECC_conference_talk.pptx`（第 2 页表格），因此保留在原位。

## 历史材料

- `MECC_HPCA_clean_ideal.pptx/.pdf`：上一轮审阅版。PPT 当前被 PowerPoint 占用，暂留原位；请以 `MECC_HPCA_current` 为准。
- `MECC_HPCA_review_revision.pptx/.pdf`、`MECC_conference_talk.pptx/.pdf`：可追溯的参考版本。
- `build_mecc_*.py`、`conference_assets/`、`hpca_revision_assets/`：旧版重建链；保留其相对路径，避免破坏历史复现。
- [archive_unused_20261102](./archive_unused_20261102/)：旧输出与候选图。新增的 27 张临时渲染预览位于 `ppt_preview_20261102/`；当前图表目录仅保留 7 组 PNG/PDF 和第 1、3 页预览。
- 中文 Framework 候选版已移至 [framework_zh_variant](./archive_unused_20261102/framework_zh_variant/)；组会只使用上表的英文主版。

当前 PPT 使用理想示例数字，数据身份见 [审阅说明](./MECC_HPCA_clean_ideal_README.md)。
