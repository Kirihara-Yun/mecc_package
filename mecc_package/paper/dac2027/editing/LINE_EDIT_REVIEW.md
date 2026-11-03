# 逐章逐句润色记录

**本轮更新**：用户现已提供 9 篇完整 PDF。PRICE 正文已通读，其余关键章节核对范围见 [FULLTEXT_READING_AND_REVISION.md](./FULLTEXT_READING_AND_REVISION.md)。下文“未获取全文”是上一轮访问状态，已被本轮记录取代。

日期：2026-10-29。对象：摘要、七个正文章节、所有图表标题/图注、AI 内容披露。修改涉及句式、段落功能和重复信息；假设数组、图形、基线身份及证据级别不变。

## 写作规则

1. 少用 however、nevertheless 等强转折；直接说明条件或因果。
2. 每句话承担一个动作或结论。主语和动词靠近，状态转换分步写。
3. 删除 promising、valuable、particularly close 等评价性修饰。
4. 一段不连续改写同一个意思。摘要回扣与必要定义保留，重复解释归位。
5. 结果段按“比较对象—数字—含义”组织。执行指令放入独立实验矩阵。
6. 精简不省略技术前提、假设标识、引用、理论范围及物理预算口径。

句长和词频仅帮助复查，不替代技术判断。

## 王福宇相关参考材料的实际范围

本次核对了中山大学、Minghua Shen 合作与体系结构方向，排除同名作者。

用户补充：PRICE 是用户的第一篇论文；其中两章方法部分由用户撰写，其余部分由王福宇师兄撰写。因此，后续取得全文后，优先将 PRICE 的引言、背景、实验和结论作为写作参照；方法章按 MECC 的实际设计组织。此作者分工来自用户说明，不写入匿名 MECC 稿，也不将公开摘要访问记录升级为已读全文。

| 材料 | 实际访问 | 参考用途 |
|---|---|---|
| [PRICE，DAC 2026 官方介绍](https://63dac.conference-program.com/presentation/?id=RESEARCH863&sess=sess146) | 公开摘要和作者 | 问题 → 编译期建模 → 运行期机制 → 实验对象与指标 |
| [SFD，IEEE 条目](https://xplorestaging.ieee.org/document/11408456) | 搜索返回的公开摘要；再次打开返回 418 | 将限制对应到 mapper、segmenter、scheduler，各机制有具体动作 |
| [Soter，作者仓库](https://github.com/FuyuWang/Soter) | README、项目结构 | 核实项目身份和研究方向，不作为全文样本 |
| [会议作者资料](https://2026.cgo.org/profile/fuyuwang) | 单位和 SFD 贡献 | 同名消歧 |
| [DATE 2025 官方目录](https://past.date-conference.com/proceedings-archive/2025/START.pdf) | Poros 的题目与作者；所链接 DATA/772.pdf 返回 404 | 仅核实作品 |

**未获取这些论文的全文，不声称已归纳其全篇写作风格。** 本稿参考公开摘要的组织方式；短句、少修饰、少转折和去重直接遵照用户要求。没有复制他人原句，也没有将写作样本作为不相关技术引用加入论文。

## 各章审阅结果

| 部分 | 原问题 | 修改 |
|---|---|---|
| 摘要 | 多层并列，末句强调不追平多卡 | 场景、SSD 等待、机制、保精度、假设结果分句表达 |
| I 引言 | 多次解释单卡价值；提前讲完整 8 GPU-s 成本例子 | 每段分别负责交付问题、任务预算、两条评测轴、挑战、架构、贡献；数字例子集中到实验 |
| II 部署与挑战 | however/yet 和“不是 X 而是 Y”较多 | 每项挑战分为原因与对应比较；保留独立画像和受控条件 |
| III 方法 | 一句承载多次升降级；反复解释理论不能做什么 | 编译输入/目标/命题/启发式/产物分开；传输拆成 event wait、source lifetime、resident lifetime |
| IV 实现 | 内存、命中语义、计时混杂，像执行手册 | 分为共享路径、storage 计费、阶段和指标定义 |
| V 实验 | 结果中夹杂“应该如何写”的指令；重复解释弱基线 | 身份集中在 setup；结果给数值与一次解释；完整待补实验留在矩阵 |
| VI 相关工作 | 每项文献介绍后重复防御性说明 | 按研究线陈述机制；集中交代本地适配与外部复现的区别 |
| VII 结论 | 重复实现列表和投稿提示 | 一段回扣静态/动态协同及两条评测轴 |
| 图表与披露 | 图注反复铺陈正文；披露重复真实性说明 | 图注给子图比较、控制条件和假设标识；披露给模型/范围/作者责任 |

额外澄清：方法中将任务总预算与扣除镜像/缓冲后的 residency budget 区分，后者写成 `bar B_t`。这是符号口径澄清，不是新增算法或最优性结论。静态等大小命题与逐层启发式范围仍分开。

## 典型改句

以下均为本稿句子，不是他人论文引文。

| 原表达 | 修改/处理 | 目的 |
|---|---|---|
| This sparsity creates a promising deployment opportunity... | A single GPU can execute these experts without keeping the full model in high-bandwidth memory... | 条件代替评价 |
| However, sparse computation does not eliminate the need to retain, locate, and deliver... | It requires a mechanism to deliver each selected expert before computation. | 正面说明依赖 |
| The opportunity is valuable for shared servers... | 删除；下一段直接讲任务 host-memory allowance | 避免价值与场景重复 |
| A useful evaluation therefore needs two complementary comparisons. | The deployment goal has two evaluation axes. | 删除修饰，给出结构 |
| Yet the benefit of another slot depends... | The value of a cache slot depends... | 删除不必要转折 |
| Once the route distribution changes, however... | Fixed placement can become stale when the working set shifts. | 主语与因果明确 |
| 一句包含复制就绪、source buffer、resident weights 三种依赖 | 分三句逐一说明 | 降低阅读负担 |
| The large difference ... should not be used as the only headline. | 删除；强基线仍在主图与实验矩阵 | 移出写作指令 |
| It does not demonstrate an eightfold improvement in GPU efficiency. | Both use 8 GPU-s/token. | 用数字说明同一事实 |
| The first integer output length with strictly lower MECC cost is ten. | MECC is lower from ten tokens onward. | 简化，保留严格回收点 |

## 交付与检查

- 修改前源码：`before_lineedit.tex`；逐行对照：`lineedit_diff.html`。
- 从 abstract 到 AI 披露（含图注和 TeX 记号）的空白分词：约 4.2k → 3.1k。此为源码规模对照，不是严格语言学词数。
- 同范围 however：2 → 0；rather than：7 → 0。这些计数只用于复查，不作为质量分数。
- 全文逐段复核并重编译；跨栏图提前放置，避免文末出现仅放一图的页面。
- 当前 5 页正文 + 1 页参考文献。IEEE 9 pt 默认版心未改，不用重复文字填满 6 页。
- 验证依据是“最多 6 页正文 + 最多 1 页参考文献”，无需刚好占满 7 页。
- 假设数组未修改。工程消融、画像/负载敏感性等完整清单继续保留在 EXPERIMENT_MATRIX.md。
