# MECC 14 页组会汇报：讲述与证据说明

本稿沿用 1013.pptx 的版式。第二页比较已报告的部署功能；第 4–6 页是三个实验驱动的动机，第 7–9 页是逐一对应的洞察。图形均为可编辑 PowerPoint 对象。

| 页码 | 讲述重点 | 数据口径 |
|---|---|---|
| 1 | MoE 专家权重超过本任务快层预算时，SSD 冷读进入推理关键路径。 | 机制示意；适用边界见 docs/APPLICABILITY.md。 |
| 2 | 比较三级支撑、完整专家执行、预算规划、热点预热、冷读预估、在线适应六项功能。 | SSD-LLaMA 已报告前三者中的前两项及在线适应；中间三项部署前能力未见报告。叉号表示论文未报告，不表示无法实现。 |
| 3 | MECC 由离线编译、在线缓存和真机验证组成。 | docs/ARCHITECTURE.md。 |
| 4 | 动机一：三级取数延迟高度不对称。左图为 5090 真机单专家测量；右图为冷读关键路径示意。 | PROVENANCE L1；mecc_package/results/raw/measured_latency_5090.json：HBM 0.256ms、CPU 6.504ms、SSD 约 790ms。不能说成 A100 测量。 |
| 5 | 动机二：固定 CPU 驻留遗漏运行期可复用专家。左图为 A100 Mixtral 结果，右图解释显存淘汰后的二次保留。 | PROVENANCE M3/M4；mecc_package/results/raw/mixtral_real.json：对照 CPU/SSD 命中 23.3%/34.5%，MECC 为 38.0%/17.6%。对照为本项目实现的 SwapMoE-style 机制。 |
| 6 | 动机三：热点漂移会提高静态驻留对照的 SSD 访问。左图为静止 7.5% 与漂移 11.3%，右图是初始驻留与新热点错位的机制示意。 | PROVENANCE H3；mecc_package/results/raw/deepseek_real_e2e.json；**D1 缓存模拟器、DeepSeek 合成规模 N=64、K_H+K_C=64**。这是先导机制观察，不是 Mixtral 主场景；A100 真机替换计划见 docs/MOTIVATION_EXPERIMENT_PLAN.md。 |
| 7 | 洞察一：以访问概率和单任务预算决定初始分层，降低预期取数代价。 | 柱高仅为机制示意，不是测得的 Mixtral 路由频率；静态最优性受 docs/THEORY.md TH-004 假设约束。 |
| 8 | 洞察二：显存与 CPU 共同保留工作集，只有两层都未命中才冷读 SSD。 | 运行期联合 LRU 为在线启发式，不保证对任意请求序列全局最优。 |
| 9 | 洞察三：历史画像给初始先验，真实路由持续修正。 | 三项洞察属于同一个编译期先验与运行期反馈架构，不能包装成三个独立加速定理。 |
| 10–12 | 系统总览与两页方法。 | docs/ARCHITECTURE.md 与实现。 |
| 13 | A100 Mixtral 综合性能为本地 SwapMoE-style 对照的 1.33×。 | PROVENANCE M1；D2 真机；不是与外部 SSD-LLaMA 的跨平台直接比较。 |
| 14 | CPU 命中率提高、SSD 比例下降；MECC fp16 PPL 为 24.57。 | PROVENANCE M2a/M3/M4；对照 PPL 身份未核实，未进入质量对比。 |

图形口径：第 4 页左侧柱高按对数轴绘制，右侧时间条仅说明等待结构，长度不按实测比例；第 5–9 页及第 10–12 页的专家身份、路由轨迹和驻留矩阵是机制示意，不是逐 token 真机 trace。第 3 页右侧 1.33× 来自第 13 页同一 A100 主实验，不是新增实验。第 5、6、13 页实验条形图均从零开始并给出共用刻度；第 14 页 100% 堆叠图中显存份额由 100% 减去已核实的 CPU、SSD 比例得到，图内不标派生精确数值。

WorkBuddy 2026-10-11 的 Gate D 报告（GitHub `gpu/a100-20261010`/`5ebb83d`）与历史主结果不在同一预算/输入口径：新运行是 30/40 GB，WikiText 不可用并回退内置 prompt，且 PPL 异常。其 2.076× **不进入 PPT**。核查与补实验清单见 `docs/MOTIVATION_EXPERIMENT_PLAN.md`。

## 论文配图参考与本稿取舍

- [Fiddler（ICLR 2025）](https://proceedings.iclr.cc/paper_files/paper/2025/file/8cd1ce03ea58b3d7dfd809e4d42f08ea-Paper-Conference.pdf) Fig. 2 将初始化与执行并列，Fig. 4–6 在图题中写明指标与“越高/越低越好”，为多组实验保留一致的比较对象。本稿据此把编译期/运行期放在第 10 页并列，把结果页改为带共同刻度、直接数据标签的图；没有复刻原图。
- [MoE-Lightning（ASPLOS 2025）](https://pschafhalter.com/papers/2025-asplos-moe-lightning.pdf) Fig. 4 使用定量坐标与临界点解释机制，Fig. 7 使用同一组颜色跨多个实验场景编码系统，并直接标数值。本稿据此保持“灰=对照、蓝=MECC”一致，并让动机页定量图与右侧机制示意分栏；没有使用论文的任何实验数字。
- 论文中的一页可承载大量小字，组会投影不能照搬。这里保留大字号、只突出一项关系；缺少逐请求 trace 和重复实验方差时，不画伪造的折线、误差棒或置信区间。

第二页参考论文：SwapMoE（ACL 2024）、Fiddler（ICLR 2025）、MoE-Infinity（2024）、MoE-Lightning（2024）、SSD-LLaMA（2026-09）。SSD-LLaMA 原文：https://arxiv.org/html/2609.18110 。它确实实现原生 SSD–RAM–VRAM 缓存、动态保留、完整执行被选专家，以及对输入量化 checkpoint 无损的搬运与压缩；表格不把这些能力误标为缺位。MECC 预算计划、预热与冷读估计分别可查 e2e/compile_config.py、e2e/tiered_engine.py 与 compiler.py；预热依赖画像，缺画像时会回退自然顺序；静态估计不是端到端性能保证。

数字一致性检查：python mecc_package/scripts/verify_claims.py；当前 OK=30、WARN=8、FAIL=0。WARN 为仓库已登记的历史口径问题。
