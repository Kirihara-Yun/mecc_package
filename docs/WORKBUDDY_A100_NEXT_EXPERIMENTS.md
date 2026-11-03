# WorkBuddy A100 下一轮实验需求（2026-11-03）

本文件是给远端 WorkBuddy 的执行请求。本地负责设计与代码审查；WorkBuddy 负责在空闲 A100 上运行、记录和回传。先读根目录 `AGENTS.md`、`WORKBUDDY.md`、`docs/APPLICABILITY.md`、`docs/EXPERIMENTS.md`、`docs/PROVENANCE.md`、`docs/WORKBUDDY_A100_RUNBOOK.md`。本文件的分支选择与本轮范围优先于旧 runbook 的 `main`/Gate D 终点约定，其余安全门禁保持有效。

## 1. 当前证据缺口与优先级

| 优先级 | 实验/门禁 | 需要回答的问题 | 当前状态 | 本轮处理 |
|---|---|---|---|---|
| P0 | 输入与历史运行复核 | 50/40 GB 的 Mixtral 主结果能否在独占 A100、冻结输入和相同 fp16 设置下复现？ | 先前 50/40 GB OOM；30/40 GB 完成运行不能代替历史复现；PPL 输入曾回退 | 先做主机审计、L0、最小 L2 预检；条件满足再做诊断性复现 |
| P0 | 输出正确性 | 同步参考、异步 MECC 和对照策略的路由、logits、token、PPL 是否一致？ | 跨流就绪屏障风险尚未关闭（PROVENANCE X8），旧 PPL 对照身份不明（X6） | 现有 harness 不足；先回传代码/运行诊断，待本地补丁后执行正式比较 |
| P0 | 物理容量公平 | 镜像、锁页、暂存、预取和临时缓冲计入后，各策略是否满足同一 CPU/GPU 物理 cap？ | 旧实验只对齐逻辑槽数，X7 未关闭 | 待本地计量补丁后测峰值，超预算的配置不进性能图 |
| P0 | 分相位与真实冷读 | decode 计时窗的 demand 来源、SSD 物理读取和 H2D/D2H 字节能否对应？ | warmup/PPL 混入命中统计，X9 未关闭 | 待本地计量补丁；单独报告启动、prefill、decode、PPL |
| P1 | 单卡主比较 | 未优化 FP16 单卡、普通三级 LRU、MECC、已适配的强对照在同预算下的 TTFT/TPOT/吞吐如何？ | 当前 PPT/论文中的跨模型柱高为理想目标 | 正确性与公平性门禁通过后先跑 Mixtral-8×7B，至少 3 次独立重复 |
| P1 | Insight I：初始放置 | 平均逐层配额、全局热度、逐层真实画像三种初态，哪种减少启动期 SSD miss 与 TPOT？ | 现有入口未自动产出兼容的 `per_layer_counts`；主 JSON 未保存画像身份 | 本地先接通画像和冻结训练/评测划分；再跑配对消融 |
| P1 | Insight II：缓存更新 | 固定 CPU、独立更新、联合更新在相同初态和物理字节下如何影响再访、SSD 流量及 TPOT？ | 仅有历史聚合命中与 D1 抽象回放，没有完整配对真机结果 | 待分相位计量后跑，增加容量 H+C 的普通全局 LRU 参考 |
| P1 | Insight III：任务切换 | WikiText-2→GSM8K 和反向切换后，在线规则是否在等长窗口内降低冷读与 TPOT？ | 真实 MoE 顺序路由 trace/分窗数据缺失 | 固定 prompt ID、切换点，含 no-shift 对照；没有漂移也照实回传 |
| P1 | 预算、开销和质量 | 任务 CPU 额度变化、初始化/画像/编译成本与无损质量如何？ | 论文图中仍是理想数字 | 与主实验共用同一输入和计量；扫描实际安全预算，不挑最优点 |
| P2 | 第二/第三模型 | Qwen2-57B-A14B、Mixtral-8×22B 能否形成真正落 SSD 的 L2 横轴？ | 仓库未完成 Qwen loader；8×22B 未完成端到端与存储核验 | 本轮仅回传可行性/磁盘/模型状态；禁止把 Mixtral 数据改名填入这些柱 |
| 资源依赖 | 多卡驻留参考 | 1 卡 MECC 与最少能驻留的 2/4/8 卡延迟—资源取舍如何？ | 只有一张可用 A100，无法在这台机上测多卡 | 记录 `not available`；不要把 8 卡 1 s / 单卡 8 s 示例当实测 |

完整论文覆盖还包括输入/输出长度、batch、画像样本量/失配、时间分解、工程项（zero-copy、pin、batch H2D、预取）及共享内存额度敏感性。它们在 P0 和首个 Mixtral P1 结果稳定后再排队；缺少资源时标 `blocked`，不生成占位结果。

## 2. 本轮现在可执行的工作包：A100 诊断

**先确认 GPU 空闲。** 如果其他作业仍在用 A100，只做只读主机审计并报告 `BLOCKED: GPU busy`，不启动 GPU 实验，不干扰他人。若可独占，沿用 `docs/WORKBUDDY_A100_RUNBOOK.md` 的 Gate A→B→C→D 顺序，但本轮从下述设计分支创建自己的结果分支：

```bash
git fetch origin
git switch -c gpu/a100-next-20261103 origin/design/hpca-review-20261028
git rev-parse HEAD
git status --short
```

1. **Gate A：主机与模型/存储审计。** 运行 `collect_host_report.py`。记录 A100 型号/空闲显存、其他进程、CPU `MemAvailable`、`/data` 所在块设备和空闲容量、Mixtral checkpoint revision、store manifest、系统页缓存设置。检查 50 GB expert HBM + trunk/KV/运行余量以及 40 GB expert CPU + 其他实际分配是否可行。模型或磁盘路径未知时报告实际位置，不猜测。
2. **Gate B：CPU checks + L0。** 运行 `run_cpu_checks.py` 和 `configs/l0_smoke.json`。回传完整 `status/result`、非空日志尾、退出码。L0 只证明链路，不引用性能。
3. **Gate C：最小 L2 预检。** 独占 GPU 和真实 NVMe 满足门禁时，使用 `configs/l2_mixtral_preflight.json`，先 `--dry-run`，再启动。检查 fp16、`cold_ssd=true`、50/40 GB、模型/存储 revision、无 OOM/NaN。此步仅诊断，不能用于论文。
4. **Gate D：历史口径诊断性复现。** 仅 Gate C 通过后，用 `configs/l2_mixtral_repro.json` 的 **50/40 GB** 原配置运行一次并回传所有原始结果。若 WikiText-2 无法固定下载/本地读取，记录输入回退及其哈希，`PPL` 标为不可比较；不得把内置提示词 PPL 当作 WikiText-2 PPL。若 50/40 GB 仍 OOM，停止；不要静默改成 30/40 GB。此步当前仍是诊断，不会自动升级为正式论文数字。

任一 gate 失败，导出该 run 的紧凑报告，提交并推送结果分支后停止。不得为了得到预想加速比改变预算、输入、精度、策略、冷读方式，或反复筛选运行。

## 3. 后续正式实验的冻结协议（等待本地代码就绪）

- **模型与输入**：先 Mixtral-8×7B。固定模型/tokenizer revision、fp16 权重、离线 prompt manifest（数据集、split、样本 ID、tokenized hash）；画像数据与评测数据不得重叠。第 7、8 页使用固定输入集合，第 9 页使用预先定义的 WikiText-2→GSM8K、GSM8K→WikiText-2 和 no-shift 序列。
- **每个图内配对**：同一模型、同一实际 HBM/CPU 字节上限、同一 NVMe/store、prompt 顺序、生成上限、确定性解码、预取与同步语义。仅改变该图的一个机制。记录策略顺序并在重复间轮换。
- **正式结果**：每臂至少 3 次独立重复，保存每次原值和失败记录；报告 TTFT、TPOT、tok/s、请求总耗时、真实峰值 HBM/锁页/可分页内存、SSD demand 读次数/字节、H2D/D2H 字节、质量对照、初始化/画像/编译时间。报告中位数与离散度，不补造误差线。
- **第二模型门禁**：先确认对应 loader、权重大小、NVMe 余量与单任务 CPU cap 确实使一部分 expert 落 SSD。任一条件不满足，回传可行性报告，状态记 `blocked`；不使用模拟数字填 PPT。
- **多卡**：需要真实 2/4/8 卡且同模型同输入，另行申请机器；单 A100 仅可报告该项资源受限。

## 4. 回传与验收

每个 gate / 正式实验在 `mecc_package/results/reports/<run-id>/` 提交紧凑报告：`run.json`、`status.json`、`result.json`（如有）、`report_manifest.json`、日志尾、`WORKBUDDY_NOTES.md`。额外提交一份 `A100_GAP_STATUS.md`，按上表逐项标 `measured / configured / blocked / not started`，写明阻塞原因、需要本地补的代码、下一步。报告必须标明 commit、完整命令、模型/输入哈希、GPU 占用和物理预算。完整日志保留远端；不得提交权重、store、token、`.env`。

最终只回复：`branch`、`commit`、最后一个 `run_id`、通过的 gate、`PASS/FAILED/BLOCKED` 和一行原因。新的结果先由本地端审计 `docs/PROVENANCE.md` 和 `verify_claims.py`，再决定是否替换论文/PPT 的理想目标值。
