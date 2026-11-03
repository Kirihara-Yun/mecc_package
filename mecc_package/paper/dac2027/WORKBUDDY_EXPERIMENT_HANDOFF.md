# WorkBuddy：把 DAC 2027 理想稿换成真实证据

2026-10-29。目标不是证明手填数字，而是按照固定语义完成比较，保留所有结果。先读仓库 AGENTS.md、docs/EXPERIMENTS.md、docs/PROVENANCE.md、docs/OPTIMIZATION.md。当前新稿未修生产推理代码。

**完整覆盖清单见 [EXPERIMENT_MATRIX.md](./EXPERIMENT_MATRIX.md)**：包含主比较、三项动机、双向消融、既有 zero-copy/pin/batch-H2D/prefetch 工程项、HBM/CPU 预算、输入/输出/batch、画像失配、时间分解、完整开销与质量。不能只执行本文件的主比较就宣告实验完成。

## 先完成的正确性与资源工作

**2026-10-29 冷读补充**：先执行 [reviews/REVISION_RESPONSE.md](./reviews/REVISION_RESPONSE.md) 的 P0 门禁。当前端到端入口的逐层 alpha 可来自随机生成，`compile_config.py` 的 M3/co-occurrence 默认开关须显式记录；不得把其运行结果直接当作正文中真实 profile 分配算法的验证。按每层实际容量重新统计字节，不能用平均槽数代替总量。全 CPU 镜像会使主存镜像字节至少等于相应 GPU 专家字节；原 42GB GPU 专家/6GB 镜像示例已撤回。先证实预算可行，再跑性能。

按 `docs/HPCA_REVIEW_AND_REVISION.md` G0–G4 执行，尤其先关闭 X7–X9：

1. 权重使用前等待 copy-stream readiness event；同步参考 vs 异步路径逐项比较 logits、router IDs、tokens、PPL。静态风险不直接判定为历史 PPL 异常原因。
2. 按 storage 去重记账：pinned/pageable、驻留、GPU 镜像、staging、near-miss、临时缓冲，测 CPU/GPU 实际峰值。超过 cap 的运行是无效配置，不算性能胜出。
3. 初始化、warmup、prefill、decode、PPL 分窗；demand 到达时的原始来源和实际 SSD/H2D/D2H 物理流量分别计数。
4. 冻结离线输入。下载失败不能静默切换语料；没有质量运行不能写 `exact(lossless)` 当实验已过。

## 主比较矩阵

| ID | 系统 | 卡数 | 比较意义 |
|---|---|---|---|
| S0 | 未优化 FP16 单卡 demand streaming | 1 | 同模型/同输入/同精度，关闭画像放置、动态 CPU 专家保留、copy/compute overlap |
| S1 | 普通三级 LRU | 1 | 避免只打过弱 streaming 对照 |
| S2 | MECC 完整配置 | 1 | 与 S0/S1 同物理预算、同 SSD store、同执行核 |
| S3 | RF / SSD-native 本地适配 | 1 | 明确版本和适配范围，不称外部系统原版 |
| S4 | 至少一个最近强系统原实现 | 适配可比配置 | 优先锁定 SSD-LLaMA / FlashMoE / MoE-CORE；记录不支持模式 |
| R2/R4/R8 | 完整模型驻留的多 GPU 参考 | 2 / 4 / 8 | 同模型精度输入；报告 TP/EP、NVLink/PCIe、软件栈。容量不足如实 OOM |

**多卡不是同预算加速基线。** 主要贡献看 S0/S1/S3/S4；多卡用于部署前沿，必须报告最少能装下的配置，不能仅挑 8 卡。FlashMoE 的卡数和秒数不能引用用户示例充当实测。

**全文核对补充**：FlashMoE 的替换是 recency/frequency 输入 FFN 的学习式预测，普通 RF 启发式不能按其原系统报告。SSD-LLaMA 包含 admission、频率/近期性 VRAM 缓存及 RAM LRU，普通三级 LRU 也不等价。除固定预算下比速度，按 EXPERIMENT_MATRIX 的 E17 增加固定 TPOT 限制下的最小可行 host cap；不得从未测区间推断资源最优。

**外部设置不要直接拼表**：SSD-LLaMA §5.1 使用量化 checkpoint；MoE-CORE §4.1 在 Ascend 950PR 上评测，其表 1 对不同对照采用不同 output cap。A100 FP16 本地适配须独立命名，不能称作这些原系统的同设置复现。新的端到端比较统一模型、精度、输出上限和实际生成 token 统计；exact 与 AES/substitution 结果分列。

首个模型 Mixtral-8x7B；确认端到端正确后扩展 Mixtral-8x22B。若存储/下载/执行适配不可用，记录失败，不用生成器模拟冒充。主实验必须真正有冷 SSD 读；CPU 可全容场景只作两级对照。

## 三项挑战的配对实验

| 目的 | 固定 | 只改变 | 输出 |
|---|---|---|---|
| C1 逐层容量 | 总 HBM/CPU 实际字节、同 trace、同替换 | uniform vs planned | 每层冷读/需求 miss、整体 TPOT，保留变差层 |
| C2 跨层保留 | 同 trace、初态、同物理字节、预取关闭 | fixed / independent / exclusive / global LRU | 需求 miss、独特覆盖、重复量、H2D/D2H/SSD 字节 |
| C3 两个时间尺度 | 同在线规则、训练/测试严格分离 | profile vs random 初态 × static/adaptive | startup 累计 miss、shift 前后窗口、uniform/no-shift 负对照 |
| C4 等待重叠 | 同 trace、初态、admission/驻留、物理 cap | overlap off/on | 使用前正确性；需求 miss 应相同，暴露拷贝时间可不同 |

真实 MoE 漂移不能预设。先采集完整按序路由；若没有自然漂移，采用明确标识的任务切换，或缩小该主张。阶段内保频乱序仅能支持顺序作用的因果对照，不等于自然负载。

## 计量和分析

- 首轮建议 batch=1、input=128、output=128；固定模型 revision、tokenizer、prompt IDs、tokenized 输入哈希、seed。参数可在执行前因资源更改，但须登记新冻结矩阵。
- 至少三次独立重复，报告每次原值、均值和真实标准差；随机策略顺序。不采用理想稿 ±3% 噪声。
- 主表：TTFT、TPOT(s/token)、tok/s、请求总时间、GPU数、峰值显存、CPU峰值、SSD bytes/token、H2D/D2H bytes/token。
- 初始化、画像、编译、预热、模型加载、prefill 分项计费；输出长度扫描计算真实成本回收点。不同负载不能共用手填 break-even。
- GPU-time = GPU数 × 总时间 / 生成 token 数，仅是设备时间代理。耗电要测能量，金钱要指定计价方案。
- 多卡 OOM/不能复现/不兼容精度单列，不补零、不造柱子。

## 必须回传

原始 JSON、完整命令和版本、退出码、开始/结束时间、stdout/stderr、数据及模型哈希、阶段计数、物理峰值、逐次质量对比、失败清单、解释结论的 Markdown。新实验 JSON 带 `platform` 与 `run_time`。

按 docs/PROVENANCE.md 登记真实 claim；不要给 `ideal_assumptions.json` 加 verified。执行 `verify_claims.py`。仅将已过正确性/公平性门禁的真数据换入正文和图；不保留有利假设压掉不利真实结果。
