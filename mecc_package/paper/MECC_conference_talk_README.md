# MECC 会议汇报版（2026-10-27）

交付：`MECC_conference_talk.pptx`、`MECC_conference_talk.pdf`。共 14 页，沿用 `1013.pptx` 的白底、蓝色横线与标题结构。此名称表示会议汇报设计目标，不表示论文获得过 Best Paper 奖项。

## 数据与占位

| 页 | 用途 | 图表状态 | 后续替换 |
|---|---|---|---|
| 3 | 工作概览中的主结果缩图 | 历史 A100 D2，PROVENANCE M1 | 已核实新主结果经过登记后再替换 |
| 4 | CPU 预算—输出 token 延迟扫描 | **占位数字** | 固定显存预算，至少 3 个 CPU 预算点，独立重复并保存 TPOT 原值 |
| 5 | CPU 命中 / SSD 访问对比 | 历史 A100 D2，PROVENANCE M3/M4 | 同预算、同输入、质量检查通过的新真机结果 |
| 6 | 请求阶段切换后的 SSD 访问曲线 | **占位数字** | A100 Mixtral 真实请求分阶段的逐窗命中计数与 TPOT |
| 13 | 综合性能与缓存行为并列 | 历史 A100 D2，PROVENANCE M1/M3/M4 | 同一组正式主实验；不使用异常 PPL 运行 |
| 14 | 画像、在线、组合的组件消融 | **占位数字** | 同配置下固定驻留 / 仅画像 / 仅在线 / 完整方案四臂实验 |

占位图在图片中标明“示例数据 · 待实测替换”，PowerPoint 演讲者备注也标记 MOCK。原值集中在 `conference_assets/presentation_data.json`，每项包含 `status`；占位文件不存入实验 `results/`，也不登记为实测。图中趋势只用于排版与讲述预演，不是预测结论。当前没有重复测量数据，因此不画虚构误差棒、置信区间或显著性星号。

右侧专家与驻留图、Insight、系统总览和方法图都是机制示意：使用原生 PowerPoint 形状，可编辑；其专家编号和时间顺序不冒充真实逐 token trace。实验图由 Matplotlib 生成，并同时保留 PNG 和矢量 PDF。改数后可重新运行构建脚本。

## 讲述顺序

问题 → 相关工作功能比较 → MECC 总体贡献 → 三个动机 → 三个对应洞察 → 系统总览 → 静态放置与联合缓存 → 主结果 → 消融与核心观点。

每张动机页都按“结果图、原因图、核心问题”组织。结果图采用零起点柱状图、带标记折线、共享单位/比例、浅网格与直接数值标注；灰色表示对照，蓝色表示 MECC。阶段切换用淡色背景和虚线表达，层级/专家状态采用矩阵与分类时间轨迹，避免把机制画成文字流程图。

图形组织参考此前阅读的 [Fiddler（ICLR 2025）Fig. 4–6](https://proceedings.iclr.cc/paper_files/paper/2025/file/8cd1ce03ea58b3d7dfd809e4d42f08ea-Paper-Conference.pdf) 与 [MoE-Lightning（ASPLOS 2025）Fig. 7](https://pschafhalter.com/papers/2025-asplos-moe-lightning.pdf)。本稿未复制其图片和实验数据。

第 2 页沿用既有功能对照表：叉号表示参考论文未报告该项能力，不表示系统技术上无法扩展实现。对应文献口径见 `MECC_paper_talk_14slides_notes.md`；公开投稿前仍应随论文版本复核。

## 再生成

```powershell
python mecc_package/paper/build_mecc_conference_talk.py
```

依赖 Python、python-pptx、Matplotlib、NumPy，以及模板 `C:/Users/zhaoy/Desktop/1013.pptx`。A100 补实验细节见 `docs/MOTIVATION_EXPERIMENT_PLAN.md`。构建后的所有占位数字、图内标签和备注应同步替换，完成后再移除 MOCK 标识。
