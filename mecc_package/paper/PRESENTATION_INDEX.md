# MECC 演示文件索引

## 当前审阅版

**2026-11-06 组会实测版**：[可编辑 PPT](./current/MECC_A100_measured.pptx) / [渲染 PDF](./current/MECC_A100_measured.pdf)。11 页；数值图只读取已提交的 A100 `result.json`，每点一次完整运行。主对比展示全部六种本地策略；预算图只比较同输入来源的 30/60 GB 两档。原 17 页理想示例版保留在下表，供设计对照。

**专家一日讲义**：[可检索 Markdown](./current/MECC_单卡MoE专家一日讲义.md) / [排版 PDF](./current/MECC_单卡MoE专家一日讲义.pdf) / [浏览器版](./current/MECC_单卡MoE专家一日讲义.html) / [首页预览](./current/MECC_expert_guide_first_page_check.png)。以 17 页 `MECC_HPCA_current.pptx` 为讲述顺序，补充相关工作原论文、MECC 代码路径和 A100 实测证据索引。

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

当前审阅版把冷存储统一标为 HDD，与 A100 测试机的旋转逻辑设备（`ROTA=1`）口径一致。RAID 控制器后的物理盘清单尚未取得；这里不包含 SSD/NVMe 测量或跨介质加速结论。`SSD-LLaMA` 等被引系统名称保留原名。图表数字仍是既有理想示例，未因介质名称调整而重算。

## 历史材料

- `MECC_HPCA_clean_ideal.pptx/.pdf`：上一轮审阅版。PPT 当前被 PowerPoint 占用，暂留原位；请以 `MECC_HPCA_current` 为准。
- `MECC_HPCA_review_revision.pptx/.pdf`、`MECC_conference_talk.pptx/.pdf`：可追溯的参考版本。
- `build_mecc_*.py`、`conference_assets/`、`hpca_revision_assets/`：旧版重建链；保留其相对路径，避免破坏历史复现。
- [archive_unused_20261102](./archive_unused_20261102/)：旧输出与候选图。新增的 27 张临时渲染预览位于 `ppt_preview_20261102/`；当前图表目录仅保留 7 组 PNG/PDF 和第 1、3 页预览。
- 中文 Framework 候选版已移至 [framework_zh_variant](./archive_unused_20261102/framework_zh_variant/)；组会只使用上表的英文主版。

当前 PPT 使用理想示例数字，数据身份见 [审阅说明](./MECC_HPCA_clean_ideal_README.md)。
