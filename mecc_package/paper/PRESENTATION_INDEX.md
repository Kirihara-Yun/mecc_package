# MECC 演示文件索引

## 当前审阅版

**2026-11-08 当前组会版**：[可编辑 PPT](./current/MECC_HPCA_current.pptx) / [渲染 PDF](./current/MECC_HPCA_current.pdf) / [22 页预览](./talk_updates/20261108_r27/contact_sheet.png)。同步论文 R27，保留原有叙事和方法，更新第 13–20 页实验；含 21 页汇报和 1 页配置/数据附录。图中不使用黄色高亮，来源与目标值说明集中在第 22 页及逐页备注。[更新记录与检查](./talk_updates/20261108_r27/README.md)同时保留更新前的 17 页母版。

**2026-11-06 独立实测版**：[可编辑 PPT](./current/MECC_A100_measured.pptx) / [渲染 PDF](./current/MECC_A100_measured.pdf)。11 页；数值图只读取已提交的 A100 `result.json`，每点一次完整运行。主对比展示全部六种本地策略；预算图只比较同输入来源的 30/60 GB 两档。该版本保留原状。

**独立中文科普文章**：[可检索 Markdown](./current/MECC_单卡MoE专家一日讲义.md) / [排版 PDF](./current/MECC_单卡MoE专家一日讲义.pdf) / [浏览器版](./current/MECC_单卡MoE专家一日讲义.html)。从 MoE 路由、单卡／多卡容量与并行方式讲到 MECC 的生命周期、相关工作的实验和 A100 实测；不依赖 PPT 页码。用 `python build_expert_article.py` 重建 HTML 与 PDF。

**相关工作详解**：[可检索 Markdown](./current/MECC_相关工作实验与洞察详解.md) / [排版 PDF](./current/MECC_相关工作实验与洞察详解.pdf) / [浏览器版](./current/MECC_相关工作实验与洞察详解.html)。逐篇列出八项工作的动机、Insight、模型、硬件、benchmark、baseline、指标和代表结果，并解释它们与 MECC 的机制关系。

| 用途 | 文件 |
|---|---|
| 可编辑 PPT（22 页） | [MECC_HPCA_current.pptx](./current/MECC_HPCA_current.pptx) |
| 渲染检查 PDF | [MECC_HPCA_current.pdf](./current/MECC_HPCA_current.pdf) |
| 第 10 页 Overview | 使用论文英文框架图 [fig01_overview.png](./dac2027/figures/fig01_overview.png) |
| 第一页预览 | [current_page1_review.png](./hpca_clean_ideal_assets/current_page1_review.png) |
| 第三页 Overview 预览 | [current_page3_review.png](./hpca_clean_ideal_assets/current_page3_review.png) |
| 构建入口 | [update_talk_from_r27.py](./update_talk_from_r27.py) / [导出脚本](./export_group_talk.ps1) / [检查与发布](./check_talk_r27.py) |
| 图表数据与绘制 | [R27 封存论文](./dac2027/reviews/hpca_20261106/r27_savings_bars/manuscript.pdf)、[图表来源记录](./talk_updates/20261108_r27/UPDATE_MANIFEST.json) |

运行 `python update_talk_from_r27.py` 构建带日期的 PPT，经 PowerPoint 导出 PDF 后运行 `python check_talk_r27.py`，检查通过才更新 `current/`。旧 `refine_hpca_talk.py` 用于复现 11 月 6 日的 17 页母版；它依赖 `MECC_HPCA_review_revision.pptx` 与 `MECC_conference_talk.pptx`，参考源继续保留原位。

当前审阅版把冷存储统一标为 HDD，与 A100 测试机的旋转逻辑设备（`ROTA=1`）口径一致。RAID 控制器后的物理盘清单尚未取得；这里不包含 SSD/NVMe 测量或跨介质加速结论。`SSD-LLaMA` 等被引系统名称保留原名。E1 为单次实测，其余目标图的身份保留于附录和备注；取消高亮不改变其数据身份。

## 历史材料

- `MECC_HPCA_clean_ideal.pptx/.pdf`：上一轮审阅版。PPT 当前被 PowerPoint 占用，暂留原位；请以 `MECC_HPCA_current` 为准。
- `MECC_HPCA_review_revision.pptx/.pdf`、`MECC_conference_talk.pptx/.pdf`：可追溯的参考版本。
- `build_mecc_*.py`、`conference_assets/`、`hpca_revision_assets/`：旧版重建链；保留其相对路径，避免破坏历史复现。
- [archive_unused_20261102](./archive_unused_20261102/)：旧输出与候选图。新增的 27 张临时渲染预览位于 `ppt_preview_20261102/`；当前图表目录仅保留 7 组 PNG/PDF 和第 1、3 页预览。
- 中文 Framework 候选版已移至 [framework_zh_variant](./archive_unused_20261102/framework_zh_variant/)；组会只使用上表的英文主版。

当前 PPT 的来源与检查见 [本轮记录](./talk_updates/20261108_r27/README.md)。旧理想示例版的数据说明继续见 [原审阅说明](./MECC_HPCA_clean_ideal_README.md)。
