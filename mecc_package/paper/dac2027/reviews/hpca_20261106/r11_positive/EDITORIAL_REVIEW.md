# R11：以机制动作组织正文

2026-11-07，承接 R10。旧稿及其 PDF 保留。

## 正文重写

本轮修改摘要、引言末段、背景中的执行说明、第二/第三项洞察、Overview、三段运行机制和主结果分析。删除或替换围绕“保持不变”“共同执行路径”“原始路由”“匹配精度”的重复说明。配置和验证协议集中在第八页。

| 位置 | R10 表述 | R11 表述 |
|---|---|---|
| 摘要 | GPU-execution policies report matching perplexity. | The evaluated Mixtral perplexity is 3.427. |
| 引言 | …preserving the original router selections and FP16 computation. | The compiler and runtime address each weight block by its layer/expert ID. This key connects a profiled rank to its initial location, later cache updates, and FP16 execution. |
| 背景 | Caching changes the source … while preserving the routing weights and expert functions. | An expert request triggers a residency lookup, weight delivery, and execution on its assigned token rows. The gate weights then combine the expert outputs. |
| 框架图 | Router (unchanged) | Expert routing |
| 框架图注 | …resolves unchanged router selections… | …maps routed expert requests to HBM, CPU resident memory, or HDD… |
| 动态适应 | …a task switch changes demand while preserving the cache capacities. | …a task switch moves requests toward a new expert set. |
| 交付方法 | Both paths preserve the router's selected set and aggregation order. | The expert kernel processes its assigned rows, and the gate weights combine the resulting outputs. |
| 执行接口 | All policies use the same FP16 loader, model graph, and router. | The execution interface accepts a layer/expert ID and its assigned token rows. Lookup resolves the ID to resident tensors or a backing-store block. |

正文进一步解释 host mirror 如何供给 demotion、CPU MRU 如何延长 GPU victim 的驻留，以及 read future / H2D / expert kernel 的顺序。主结果分析改为 phase speedup、三层请求分布和跨层保留收益。段落以设计输入、状态变化及计算输出展开。

## 图与对比范围

- 主图采用 streaming、SwapMoE-style、Fiddler-style、MECC I/O、MECC 五个策略。
- 删除正文中的 FlashMoE-RF 分析段；跨模型设计图改为 streaming 与 MECC 两组。
- 第八页保留完整已测策略结果，包括 FlashMoE-RF 的绝对值及相对 streaming 的 1.81× decode、1.54× 首 token 比例。`RATIO_AUDIT.json` 保留全部六个运行及源哈希。正文没有宣称 MECC 优于所有策略或所有先前系统。
- 图 2 的第三项洞察改为 “Adapt residency to new requests”，描述实际的缓存成员更新。框架图的布局保留，路由标签改为操作名称。

所有原始测量、设计数组及黄色高亮数据性质说明保留。图中分子分母沿用 R10 审计，不增加实验或修改数值。

## 检查

机械扫描用于发现重复的否定/不变性措辞；逐段检查用于判断句子是否解释了方法。扫描结果不作为审稿评分或作者身份判断。页面、图文位置、引用、短行和哈希检查见 `RELATIVE_VALIDATION.json`。
