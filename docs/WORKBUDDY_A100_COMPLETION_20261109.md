# A100 下一轮实验补全：2026-11-09

本轮目标：把现有 Mixtral 单卡图补成可复算的主结果和机制分析。先利用已有结果，不重跑整套旧队列。新运行只取实测值，不按论文里的目标数值调参数。

执行分支：`design/a100-experiment-completion-20261109`。基础结果与代码：`origin/gpu/a100-p0-gates-20261103@56da814`。本工作包连同执行代码、冻结输入和配置一起发布；不是等待本地实现的路线图。

## 1. 已有结果与本轮补什么

| 内容 | 已有证据 | 本轮动作 |
|---|---|---|
| 单卡主结果 | `a100-main-*` 的逐策略 result/run/status；WikiText-2 | 保留原记录。用统一物理内存上限、新协议补 WikiText-2、GSM8K、HumanEval 的 MECC/streaming，再在 WikiText-2 补固定 CPU、RF、本地普通独立 LRU |
| 初始放置 | E05 的 avg/global/per_layer 三次运行 | 旧代码的共现排序覆盖 `init_plan`，三臂的有效 placement 相同；不将其当作三种方法的消融。新协议显式关闭 M3，比较自然序+均分、逐层热度+均分、逐层热度+按统计分配 |
| CPU 保留 | E06、主结果中 fixed CPU / ours | 旧 `independent` 会取走 CPU 命中，且不补入冷读，逐渐排空；保留其历史数据。新加 `independent_inclusive`，CPU 冷读会入缓存、命中后保留，GPU/CPU 独立 LRU，各臂均记物理占用 |
| 任务切换 | E07/E08 真正的 WikiText-2↔GSM8K，但只存前后两个窗口，且只有 ours | 补 A→B、B→A、A→A × 固定初态/在线更新，保存每个请求的延迟、来源、字节及每层驻留集合 |
| 容量 | P2 主缓存槽位预算扫描 | 不拼进新曲线。新队列固定同一个 unit 物理上限，再扫主 CPU 池 8/16/24 GiB |
| 预取重叠 | 现有 ours_io，不同实现版本 | 新队列仅关闭 prefill HDD 预取，其他配置同主结果 ours；比较 TTFT、TPOT 和字节。它不是 CUDA 时间线中的纯 I/O/纯计算分解 |
| 输入长度 | 论文中目前有目标曲线 | 独立可选队列。要求真实 token 长度等于设置；不足即报告，不重复或补词凑长度 |
| 校准规模、batch、第二/第三模型、H100/多卡、外部完整系统 | 没有覆盖当前论文目标图的同协议实测 | 见 §8 后续队列；本轮不调用尚不存在的命令 |

## 2. 冻结协议

- A100 80GB PCIe，FP16 Mixtral-8×7B Instruct，snapshot `eba92302a2861cdc0098cc54bc9f17cb2c47eb61`。
- 原有 `/data/mecc_store_mixtral`，复用已验证的 store；不下载或重建权重。介质沿用本项目 HDD-backed RAID 命名；保留已有存储证据，不能把 RAID 设备名推断成物理盘型号或 SSD。无需为此等待新管理员证明才开始本轮测量。
- 主 HBM/CPU 槽位预算 50/16 GiB。**每个性能运行的整个 unit 都设 `MemoryMax=80 GiB`、`MemorySwapMax=0`**，包括模型装载、镜像、暂存、分配器和该 cgroup 计费的页缓存。所有策略使用同一张卡。实际峰值另报，不将主池预算叫作进程总内存。
- 80 GiB 是本轮冻结的待验证物理上限，不声称已经能运行。pilot 或装载被 OOM/oomd 杀时保留证据并停止；不单独给某策略加内存。下一配置需另起协议与 run ID。
- 默认每臂 **1 次独立运行**，不硬性三次。不画虚构误差线，4 条输入也不算 4 次独立重复。先补横向覆盖，再按差异大小和剩余时间决定是否另发重复实验。
- 默认每个任务 4 个独立输入，上限 64 input tokens、固定输出 16 tokens、batch=1；不提前 EOS 退出。输入短于上限时保留真实长度，作图不能声称固定 64 token。两种策略按 token hash 对齐。
- 离线输入：`e2e/data/completion_tasks_20261109.json`。真实 WikiText-2 test、真实 GSM8K test 前 8 题、OpenAI HumanEval 前 8 个函数提示。HumanEval 这里只量代码任务推理延迟；没有执行测试，不能报 pass@1。PPL 使用独立 WikiText-2 文本片段；不输出 `exact(lossless)` 字符串作为正确性证据。
- 关闭逐请求 warmup，第一条输入直接测试初始状态。模型初始化单独报告 `initialization_s`，请求响应时间不包含初始化。第一条 TTFT 含首轮 kernel 开销；所有臂协议相同，不把它解释成单独的 HDD 时间。
- 画像沿用已提交文件，只有 **346 个 calibration tokens**。不是 2048 样本。关闭跨层共现 M3。自适应容量使用该画像中真实拟合的每层 alpha，不生成随机 alpha。
- 放置消融把可用总槽数锁定为均分方案实际使用的总槽数，避免把利用额外零碎容量算成排序收益；实际 `per_layer_k_h/k_c` 和全部 placement 入结果。
- 新协议统一关闭绕过 policy 的批量提升快路径，使 CPU 来源不会在更新前被改记成 HBM 命中；这属于新测量协议，不与旧 E1 柱高混算。旧执行路径默认不变。
- 只操作本任务自己的 systemd unit；不停止其他用户的 GPU 进程，不改全局缓存/RAID/oomd，不使用全机 `drop_caches`，不申请 sudo。

## 3. 拉取及上机前检查

在服务器创建新的干净 worktree，保留正在使用的目录：

```bash
git fetch origin
git worktree add -b gpu/a100-completion-20261109 ../mecc_a100_completion_20261109 origin/design/a100-experiment-completion-20261109
cd ../mecc_a100_completion_20261109
git status --short
git rev-parse HEAD
```

先读 `AGENTS.md`、本文件、`docs/EXPERIMENTS.md` 和 `docs/GPU_HANDOFF.md`。本文件更新了本轮的 HDD 介质、1 次重复与物理上限要求；不再执行旧 COPY_READINESS 任务，也不恢复旧 driver。

```bash
nvidia-smi --query-gpu=index,name,memory.total,memory.used,utilization.gpu --format=csv,noheader
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader
df -h /data
python3 mecc_package/scripts/test_completion_protocol.py
python3 mecc_package/e2e/run_e2e.py --smoke --policies naive,ours,swapmoe,fiddler,flashmoe_rf_adaptation,frozen_placement,independent_inclusive --n_prompts 2 --store_root /tmp/mecc_completion_smoke --out /tmp/mecc_completion_smoke_result.json
```

这里的 smoke 只检逻辑和 lossless，不将速度入图。GPU 有其他计算进程时等待，不启动实验。运行前核对 model、store manifest、256 个 expert 文件可读。

## 4. 新路径的短窗正确性门禁

配置文件已发布：`mecc_package/e2e/configs/diag_a100_completion_20261109.json`。先用 `naive,ours`，再用 `naive,frozen_placement` 和 `naive,independent_inclusive`，每组独立 unit，避免顺序装载积累。三个 unit 必须串行完成，不能一次粘贴同时启动：

```bash
STATE=/data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61
python3 mecc_package/scripts/experiment_launcher.py run a100-c11-gate-ours-r1 --config mecc_package/e2e/configs/diag_a100_completion_20261109.json --state-path "$STATE" --policies naive,ours --gpu 0
# 等待 complete 且 result.passed=true，report 后再启动下一组。
python3 mecc_package/scripts/experiment_launcher.py run a100-c11-gate-frozen-r1 --config mecc_package/e2e/configs/diag_a100_completion_20261109.json --state-path "$STATE" --policies naive,frozen_placement --gpu 0
# 同样等待通过，再启动下一组。
python3 mecc_package/scripts/experiment_launcher.py run a100-c11-gate-independent-r1 --config mecc_package/e2e/configs/diag_a100_completion_20261109.json --state-path "$STATE" --policies naive,independent_inclusive --gpu 0
```

每组用 `experiment_launcher.py status <run-id>` 核对；导出 `report <run-id> --tail-lines 250`。必须检查 `result.passed`、route/token 一致及预设 logits/PPL 容差，不能只看退出码。容差与现有 G1 相同，不放宽。该诊断启用 `completion-sequential`，与新性能队列的 policy 路径一致；仍是内部参考，不冒充独立 HF 等价性证明。

## 5. 性能队列：命令已经就绪

先列出冻结队列，只读、不启动 GPU：

```bash
python3 mecc_package/scripts/completion_queue.py --state-path "$STATE" --stages pilot,main,placement,shift,capacity,overlap
```

默认 **23 个运行**，顺序如下；同配置的主结果臂直接复用，不重复消耗 GPU：

| 阶段 | 运行数 | 输出用途 |
|---|---:|---|
| pilot | 1 | 单输入、2 output tokens、不测 PPL；确认物理上限可运行与计量存在，不作为论文主结果 |
| main | 9 | 三任务×ours/naive，加 WikiText-2 上 swapmoe/RF/普通独立 LRU；替换主图、补任务覆盖和保留对照 |
| placement | 2 | 逐层排序+均分、逐层排序+按统计分配；复用 main GSM8K 的自然序+均分作为第三臂 |
| shift | 6 | A→B / B→A / A→A × frozen_placement/ours；每个任务段 4 条、总 8 条，逐请求曲线 |
| capacity | 4 | 8/24 GiB×ours/naive；16 GiB 使用 main WikiText-2；形成三个预算点 |
| overlap | 1 | 关闭 prefill HDD 预取，与 main WikiText-2 ours 配对；其余规则不变 |

用持久 controller 启动，避免断网中断队列：

```bash
mkdir -p mecc_package/results/reports/completion_20261109
systemd-run --user --unit=mecc-plan-20261109 --collect \
  --property="WorkingDirectory=$PWD" \
  --property="StandardOutput=append:$PWD/mecc_package/results/reports/completion_20261109/controller.log" \
  --property="StandardError=append:$PWD/mecc_package/results/reports/completion_20261109/controller.log" \
  --setenv=PYTHONUNBUFFERED=1 \
  "$(command -v python3)" "$PWD/mecc_package/scripts/completion_queue.py" \
  --state-path "$STATE" --gpu 0 --hours 24 --execute
```

`--hours 24` 是队列时间上限，不保证 23 个运行在 24 小时完成。超时会停止**当前本任务 unit**、导出已完成和部分结果；未完成图格仍列待补，不能拿部分结果当完整点。单个运行另有 8 小时上限。第一次 main 结束后，以真实耗时更新剩余工作量。

```bash
tail -n 60 mecc_package/results/reports/completion_20261109/controller.log
systemctl --user status mecc-plan-20261109 --no-pager
```

不删除旧 run 目录或覆盖原 ID。controller 重启会跳过已完成且验证通过的 run；若存在未完成 run，先回传并处理，不自动重跑。失败后使用新编号需要在冻结 matrix 的 `run_prefix` 下新起协议并记录原因，不能让旧失败消失。

## 6. 采集与成图标准

每个完成运行包含：

- `run.json`：commit、完整命令、GPU、配置指纹和申请的物理内存上限。
- `result.json`：数值 PPL、每请求 TTFT/TPOT/整请求时间、真实 token 长度与 token hash、初始化耗时、每层初态、CUDA allocated/reserved 峰值。
- `requests.jsonl`：逐请求原始行，prefill/decode 分开的需求次数、HDD/H2D 逻辑字节、每层统计及驻留集合。
- `resource_trace.jsonl`：装载及运行期间每秒采样，CPU RSS/HWM/locked/pinned、cgroup memory.current/peak/max、memory.stat 的 anon/file、PSI、swap。**完整 trace 留远端**。
- 紧凑 `resource_summary.json`：物理峰值与实际 memory.max/swap.max；队列要求确认 80 GiB 和零 swap 的限制确实生效。1 秒样本峰值不等于连续峰值，另报 kernel memory.peak。
- `contract.json`、日志尾与本 unit journal。完整日志、权重、token IDs、store 不入 Git。

图格审核：

1. 首次放置只看第一条真实请求及随后请求，不用预热后的均值代替启动成本；初始化、TTFT、decode 分列。放置消融先验证三臂最终 plan 确实不同，且总槽数相同。
2. 保留对照以同一任务、相同输入 hash、相同物理上限为前提。`independent_inclusive` 是本仓库的普通缓存对照；不沿用旧 E06 为它命名。
3. task shift 每个请求一个点，绘制真实切换位置；fixed/online 必须配对。没有明显变化也是结果，不人为制造热点。
4. HDD demand 分母为**当前 phase 中 cache access 请求次数**，不是 token 数或所有阶段总和；同时给逻辑读取字节。prefill 的一次 access 可供一组 token 使用，不能把它等同于每 token 的路由次数。
5. `/proc/self/io:read_bytes` 是归属于进程的存储读取，纯页缓存命中不计；`rchar` 才包含逻辑读取。块设备 `/proc/diskstats` 读量包含同盘其他工作，不当作本进程独占物理 I/O。三个口径分列。
6. 阶段边界的 wall time 含计量开销；正式 TTFT/TPOT 来自同步后的计时字段。未采 CUDA event/时间线时，不编出 HDD、H2D、计算的可相加耗时饼图。
7. 单次测量不画方差；不要筛掉比 MECC 快的对照或改写不利数字。所有成功与失败臂都保留，按预先定义的问题选择展示图。
8. 作图须将旧协议 E1/P2 与新协议 C11 分开。先回传原始数据，本地审核后更新论文/PPT。

## 7. 回传与停止条件

任一数据哈希/模型/store 不符、CPU 回归/L0/正确性失败、GPU 被他人使用、CUDA OOM、oomd/SIGKILL、物理上限不生效、计量缺失或超时，停止队列并导出本任务报告。不改预算、精度、输入或门限来绕过问题。

每个阶段完成后可先提交紧凑结果，避免断网丢失反馈。不等待全队列结束才回传。

```bash
git add mecc_package/results/reports/completion_20261109
git add 'mecc_package/results/runs/a100-c11-*/result.json' 'mecc_package/results/runs/a100-c11-*/run.json' 'mecc_package/results/runs/a100-c11-*/status.json'
# 再逐个 add 本轮 reports/a100-c11-* 紧凑报告；不要 git add 全部大型 trace。
git diff --cached --stat
git commit -m "results: A100 C11 measured experiment completion"
git push -u origin HEAD
```

回传格式：`branch / commit / 完成与失败 run IDs / 各图格状态 / CPU与GPU峰值 / 本轮真实耗时 / 下一阶段估时`。因时间上限未启动的臂记 `pending`，资源缺失记 `blocked`；二者不能算失败或完成。

## 8. 后续实验队列与资源需求

| 顺序 | 实验 | 当前缺口 | 执行条件与产物 |
|---|---|---|---|
| P1 | 校准规模 | 当前画像只有 346 tokens；没有 32/128/512/2048 独立样本曲线 | 固定训练/校准输入、按样本与 token 双计数；保存每一档真实路由统计和 profile 时间，统一 holdout。先实现 tiered profiling，避免 HF `device_map=auto` 使用整个 1 TB host 绕过任务预算 |
| P1 | 更长生成和启动摊销 | 本轮初始化及逐请求数据能做实测起点，但没有完整长度扫描 | 同协议 16/64/128 output；分别报初始化+生成与纯请求时间，不把 `I/n+D` 当端到端。先按真实 pilot 估时 |
| P1 | 输入长度 | 新包另有 6 个可选运行 | `--stages length`；先确认所选输入足够长。不足则冻结独立长文本再跑，不能自动拼接或 padding |
| P1 | batch 1/2/4/8 | 当前 harness 无真正批量接口 | 本地增加批量 token/KV/路由计量后再发布。连续运行 8 条输入不算 batch=8；同时报告 aggregate tokens/s 与每序列进展 |
| P1 | MoE-CORE、MoE-Infinity、SSD-LLaMA 完整系统 | 只有部分本地缓存机制，未具备这些系统完整、同协议原始结果 | 固定上游仓库 commit、依赖、量化与执行设备，按原实现独立启动，先正确性和物理预算。无法在同精度/同硬件运行时单独记录，不拿现有 policy 改名顶替 |
| P2 | Qwen2-57B-A14B / Mixtral-8×22B | 没有该两模型在当前 loader/store 下的可靠结果；剩余磁盘约束 | Workbuddy 先只读 inventory：权重是否已有、空闲磁盘、精度、模型结构。不要下载新大模型。实现各自 loader、检查专家体积，再冻结新模型配置和 G1 |
| P2 | H100 1 卡 vs 4 卡 | 当前服务器只有 A100 | 需要独占 1/4 H100 节点、同 checkpoint/输入/精度/并发；端到端测完整响应，模块测同步最慢 rank 的 MoE 层，通信与权重准备范围分清。不能从 A100 倍率换算 |
| P2 | 独立 HF 正确性与任务精度 | G1 是共享本地 dispatch 的内部参考；HumanEval 本轮不执行测试 | 在能完整加载参考模型的机器/独立诊断环境做 HF 对照；固定 logits/router/token 样本和 GSM8K exact-match/HumanEval pass@1。参考环境的内存不能混入部署性能上限 |

Workbuddy 本轮先执行 §3–§7，同时回传 §8 的模型/磁盘/可用 GPU **只读清单**。不自行开发新的大模型 loader 或完整外部系统，不擅自扩展正式队列。

## 9. 本地验证状态

本地缺少 torch/transformers，也无 A100；已完成标准库/NumPy 下的协议回归、真实输入哈希检查、全部冻结配置解析、launcher 命令生成和 Python 语法检查。GPU 实验均未在本地执行。上面的 CPU/L0/G1 是本次变更的必要上机门禁。
