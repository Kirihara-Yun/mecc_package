# 架构图、术语与六页版面复核（2026-10-29）

交付稿：`mecc_dac2027_polished.pdf`。本轮是编辑、图形和版式复核，不冒充新的独立审稿分数。虚拟数值、待验证内容和 AI 使用说明继续高亮。作者占位及两行空机构栏已移除；9pt、版心与行距未缩小。

## 按用户最新要求采用的绘图参考

**本轮没有查看或参考 PRICE 配图。** 先前 Fiddler/FlexGen/MoE-Lightning 的阅读记录不等于本轮采用的主要画风。随后按用户指定改为以下原始论文图形参考：

| 来源 | 实际查看 | 采用的表达规则 |
|---|---|---|
| [FACIL, HPCA 2025，作者 PDF](https://seonghoonseo.github.io/files/pdf/research/2025-hpca-facil.pdf) | PDF pp.5–6 的 Fig.7–9；p.9 的 Fig.13 与实验设置表 | 清楚的系统边界；相同对象在不同操作中保持形状和位置；有限配色；细线表格与紧凑分组柱状图 |
| [Klotski, ASPLOS 2025，作者 PDF](https://yuyue.github.io/res/paper/Klotski-ASPLOS2025.pdf) | PDF p.4 Fig.3；p.5 Fig.4–5；p.6 Fig.6 系统总览；p.9 Fig.9 执行时序 | 离线/在线分区；具体权重块与缓存对象；元数据和权重流区分；用分轨时序说明依赖而非只画模块框 |

以上是组织方式参考，不复制原图、原配色布局或外部实验结果。原始 PDF 和截图仅保存在忽略目录 `editing/visual_references/`，不进入源码包。

## 本轮完成的修订

- 增设独立 Overview 章节。框架图与该章同在第二页，展示 placement compiler、residency plan、router、residency lookup、三级存储、weight delivery 与 GPU execution。不把热度图误当系统总览。
- 框架图中虚线只承载控制/计划信息，实线承载权重；SSD 明确保留全部 backing weights。图内占用与专家 ID 是示意，不是内存可行性证据。
- 方法补入物理内存约束与执行依赖时序。图中 SSD read → H2D → readiness event 的先后关系与正文一致；不暗示未观测到的下层路由已知。
- 重画所有活动图：缓存状态、三项动机、TPOT 主比较、局部基线加速比、累积消融和资源敏感性。MECC 使用一致蓝色；CPU/传输路径使用一致青色；控制对照以灰色为主。
- 统一正文和图内称谓：TPOT (s/token)、SSD demand-miss share (%)、Task host-memory cap (GB)、HBM、CPU pinned memory、SSD backing store。旧的 Token latency、Decode time / token、Task CPU budget 不再用于活动图。
- 文字统一 Times 系列，数学标注使用与 Times 协调的 STIX；不再在同一图中混用无衬线标签。所有活动图输出矢量 PDF/SVG。
- 主实验图右面板改为相同 TPOT 目标推得的局部 SSD-native adapter 加速比，避免再次重复八卡对比。多卡比较仍完整保留 2/4/8-GPU resident references。
- 增加组件对照表，分开 allocation、initialization、retention、overlap 的变量；保留完整请求开销、profile horizon 和质量验证要求。压缩重复相关工作表述，正文实质性填充至第六页。
- 新核实 Klotski 的正式 ASPLOS 元数据及相关机制，正文实际引用共 28 项。没有增加任何虚拟测量值。

## 严格复核清单

自动复核见 `validation.json` 和 `visual_validation.json`：页数/9pt/匿名/引用、框架图所属页、旧术语排除、字体族、矢量输出及图内文字边界。逐页渲染目录为 `preview_polished/`。

人工检查重点为：图例不压数据、文字不与箭头相交、图注与面板内容一致、同一缓存状态的专家顺序一致、需要 readiness 的数据依赖没有被控制箭头替代。自动格式通过不能证明机制新颖或实验有效；独立审稿中尚未关闭的强基线、内存可行性和真实实验问题仍保留，不因画风修改而视为解决。
