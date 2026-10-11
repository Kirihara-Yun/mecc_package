# Motivation 实验补证与 WorkBuddy 下一轮执行计划

日期：2026-10-11。用途：为组会 PPT 第 4–6 页补齐“左侧实验结果、右侧原因分析”的主场景证据。本文件是**待执行计划**，不是已完成结果；具体上机命令和门禁以 `docs/WORKBUDDY_A100_RUNBOOK.md`、`docs/EXPERIMENTS.md` 为准。

## 1. 已收到的远端结果：先审计，不直接纳入主图

GitHub 分支 [`gpu/a100-20261010`](https://github.com/Kirihara-Yun/mecc_package/tree/gpu/a100-20261010)，最新提交 `5ebb83d`，上传了 Gate A 主机审计、Gate B L0 启动记录、Gate C 预检、Gate D 首次 OOM 与 2026-10-11 完成运行的结构化报告。**Gate B 不能判 PASS**：其报告只有 `run.json`，`run_tail.log` 为 0 字节，没有 `status.json` 或 `result.json`；需要补齐 CPU checks 与 L0 的完成证据。Gate C 为 1 prompt / 2 token，只验证流程；Gate D 的完整报告位于 `mecc_package/results/reports/a100-mixtral-repro-20261011-1500/`。

最新 Gate D 确实是 A100 上 `mode=real`、两策略跑完，但**不是历史 50/40 GB 口径复现**：`run.json` 传入 HBM 30 GB、CPU 40 GB（`K_H=2,K_C=3`），而冻结配置 `l2_mixtral_repro.json` 为 HBM 50 GB、CPU 40 GB（历史 `K_H=4,K_C=3`）。上一次 50/40 GB 运行因同卡另一个进程占用约 9.85 GiB 而 OOM。最新运行中 WikiText-2 下载失败，脚本自动回退到内置提示词；报告的 PPL 为 OURS 92.953、对照 893.774，与历史 24.57 不可比，也需要排查同精度策略的输出一致性。完成运行报告的 2.076× 是**该 30/40 GB、当前输入条件下的单次报告值**，未经过重复实验、质量门禁与 `PROVENANCE` 登记，不进入 PPT 主结论。

## 2. 优先门禁：先恢复一条可信的 Mixtral 主线

1. **补齐早期门禁。** 回传 CPU checks 摘要、L0 的 `status.json`、`result.json` 与非空日志，确认真实完成而非只有启动元数据。L0 不作性能证据。
2. **独占 GPU 与配置冻结。** 在 50/40 GB 冻结配置下，只在 A100 无其他计算任务时启动一次；记录启动前、中、后 `nvidia-smi` 进程与显存。若仍 OOM，停止并回传；30/40 GB 另建明确命名的独立实验臂，绝不称为 50/40 GB 复现。
3. **固定离线输入。** 将生成 prompt 与 PPL 文本的来源、文件哈希、模型 revision、tokenizer revision、随机种子写入报告。不得让 WikiText 下载失败时静默切换到另一套质量评测文本；没有可核验的质量语料时 `--skip_ppl`，并把质量实验单独排队。
4. **语义检查。** 同一组 fp16 输入比较两策略 logits/生成 token 与不卸载 fp16 参考（或可证明等价的参考路径）；排查 PPL 异常。质量没过，速度和命中率只能作内部诊断。
5. **冷读与统计检查。** 保留 `cold_ssd=true`，记录 store 块设备、page-cache 处理方法、每策略相同的请求序列；至少 3 次独立运行，分别保留 JSON、日志、config fingerprint 和失败记录，报告中位数与每次原值，不挑最好的一次。
6. **事实登记。** 新数字先审 `results/SCHEMA.md`、登记 `docs/PROVENANCE.md` 的 D2/状态与命令，再运行 `verify_claims.py`；与历史结果冲突时登记 discrepancy，不静默覆盖历史文件。

## 3. 三张 Motivation 所需的实验

| 优先级 | PPT 页 | 要回答的“问题结果” | 左侧目标实验图 | 右侧原因分析图 | 控制变量与最低交付 |
|---|---:|---|---|---|---|
| P1 | 4：慢层代价 | SSD miss 是否真正放大 Mixtral 端到端 token 等待？ | A100 真机：固定 HBM、同输入，改变 CPU expert 预算造成不同 SSD miss 比例；横轴实测 SSD 访问/每 token 冷读次数，纵轴 TPOT，至少 3 个预算点及重复运行点。另附 HBM/CPU/SSD 单 expert 取数分布图。 | token 时间构成：路由/计算/CPU 传输/SSD 冷读的分段时间条；仅画实测可归因的分段，重叠部分单独标出。 | 同模型、revision、prompt、precision、策略、store、冷读语义；每点 p50/p95、原始重复值、命中率、I/O 字节和 TPOT。预算改变可能影响其他因素，因此只能说相关，不直接宣称纯 SSD 因果。 |
| P1 | 5：遗漏复用 | 固定 CPU 集合的再访为何落 SSD？ | A100 真机：同预算、同路由输入的固定 CPU 对照与联合缓存，分组展示 CPU 命中、SSD 访问和 TPOT；历史 23.3/38.0 与 34.5/17.6 仅作为待复核锚点。 | 真实 trace 的“专家×时间窗”访问热图与两策略 tier 驻留热图；标出同一专家被 HBM 淘汰后是否留在 CPU、下一次访问命中哪层。 | 输出逐专家匿名 ID、时间窗、访问 tier、提升/降级事件和计数；日志可紧凑聚合，不提交敏感 prompt/模型权重。 |
| P2 | 6：热点漂移 | 初始画像在请求阶段变化后是否失配，并增加静态策略 SSD miss/TPOT？ | A100 Mixtral 真机：相同预算下，按预定义的两组真实 prompt 顺序构造 A→B 阶段；画每时间窗静态与在线两策略的 SSD miss 比例和 TPOT 折线，至少 3 次顺序重复，并做 B→A 顺序对照。 | 真实路由热度热图与初始驻留掩码叠加，显示哪些新热点落在 SSD；不得用手画热区冒充 trace。 | 阶段 prompt 集、长度、顺序、路由计数与窗口边界均落盘。若实测没有漂移或无优势，按事实修改 Insight III；不要筛选“漂亮”的阶段。 |

当前 PPT 第 4 页用 5090 D2 单 expert 延迟、第 5 页用历史 A100 D2 缓存命中、第 6 页用 DeepSeek 合成规模 D1 缓存模拟器的 7.5%→11.3% 静态 SSD 访问趋势。它们**不构成三张 A100 Mixtral 真机因果实验的完整证据链**。上述 P1/P2 完成并过门禁后，替换对应页左图和右侧示意图；在此之前第 6 页始终标明“缓存模拟器”。

## 4. WorkBuddy 交付格式

沿用 `experiment_launcher.py report` 的 `run.json`、`status.json`、`result.json`、`report_manifest.json`、截断日志；新增每个实验的 `motivation_metrics.json`，明确 `experiment_id`、`run_id`、commit、平台、模型/输入哈希、预算、策略、冷读设置、窗口/重复编号、原始计数与计算口径。只在 `gpu/a100-*` 分支提交紧凑报告。若需要新增 instrumentation 或配置，先把设计/代码提交到本地设计分支，待审后再由 WorkBuddy 拉取执行；远端不得临时修改策略或筛选结果。
