# Workbuddy G2b：保留 OOM 前内存轨迹并补齐三策略正确性

> 冻结工作包，基础证据 `gpu/a100-g2a-oomd-audit-20261103@0292ea1`。本轮在 G1 的同一模型、store、输入、预算、门限和策略顺序上**只添加计量**。目的有二：找出 systemd-oomd 终止前的内存/压力轨迹；若进程完成，补齐 `swapmoe` 的同仓库短窗正确性。这里的速率一律不作性能结果。

## 1. 本轮新增的证据

- `resource_trace.jsonl`：独立子进程每秒写入一次进程 RSS/VmHWM/VmLck/VmPin、目标 cgroup 的 `memory.current/peak/events/pressure` 和 swap、宿主 MemAvailable/PSI。每行 `fsync`；整个 unit 再被 SIGKILL 时，最后一个已写入样本仍应保留。
- `memory_checkpoints.jsonl`：每个策略装载前、装载后、释放前、释放后的 CUDA allocated/reserved 和存活 expert 权重 storage 去重字节。角色分别为 GPU 池、CPU 镜像、CPU 池、预取/近失缓冲。角色之间可能共享 storage；用 `all_unique_*` 看总量。这是**张量存活账**，不是进程 RSS，也不包括 trunk、分配器、页缓存。
- 原 G1 的两个短 prompt、128-token 仓库自写 PPL 输入、50/40 GB 预算、`naive,ours,swapmoe` 顺序和比较门限完全不变。

## 2. 上机门禁

1. 从设计分支创建干净结果分支：`gpu/a100-g2b-memory-trace-20261103`。运行前记下 commit、GPU 占用、当前 `MemAvailable`/swap、store manifest 哈希和模型 revision。GPU 非空闲或有其他 MECC unit 时报告 `BLOCKED`，不启动。
2. 阅读 `AGENTS.md`、`WORKBUDDY.md`、`docs/EXPERIMENTS.md`、`docs/PROVENANCE.md`。运行 `python3 mecc_package/scripts/run_cpu_checks.py`，失败即停。原 G1 的 L0 已通过；本轮仍对本分支跑一次 L0，失败即停。
3. `--dry-run` 核对 `correctness_probe.py`、`--resource_trace`、`naive,ours,swapmoe`、50/40 GB、3 个生成 token、128 PPL token、GPU 0、snapshot 和 fixture。`resource_trace.jsonl` 在启动后应出现；若 15 秒内不出现，停止该 unit 并回传，不继续等待。
4. `/data` 的物理存储介质尚未确认。本轮仅诊断，不发布 SSD/NVMe 性能数字。

## 3. 固定命令

在仓库根目录执行。只允许把 `STATE` 换成实际核实的**同 revision** snapshot 路径；其余参数与配置不得修改。

```bash
git fetch origin
git switch -c gpu/a100-g2b-memory-trace-20261103 origin/design/a100-g2b-memory-trace-20261103
git status --short
git rev-parse HEAD
python3 mecc_package/scripts/run_cpu_checks.py

STATE=/data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61
LAUNCHER=mecc_package/scripts/experiment_launcher.py

python3 "$LAUNCHER" run a100-g2b-l0-20261103 \
  --config mecc_package/e2e/configs/l0_smoke.json --gpu 0 --dry-run
python3 "$LAUNCHER" run a100-g2b-l0-20261103 \
  --config mecc_package/e2e/configs/l0_smoke.json --gpu 0
python3 "$LAUNCHER" status a100-g2b-l0-20261103
python3 "$LAUNCHER" report a100-g2b-l0-20261103 --tail-lines 10000
```

仅在 L0 `complete` 后执行：

```bash
python3 "$LAUNCHER" run a100-g2b-memory-20261103 \
  --config mecc_package/e2e/configs/diag_a100_g2b_memory_v1.json \
  --state-path "$STATE" --gpu 0 --dry-run
python3 "$LAUNCHER" run a100-g2b-memory-20261103 \
  --config mecc_package/e2e/configs/diag_a100_g2b_memory_v1.json \
  --state-path "$STATE" --gpu 0
```

确认 `mecc_package/results/runs/a100-g2b-memory-20261103/resource_trace.jsonl` 开始增长。之后只查询运行状态和日志，不重复启动同一 run ID。结束后执行：

```bash
python3 "$LAUNCHER" status a100-g2b-memory-20261103
python3 "$LAUNCHER" report a100-g2b-memory-20261103 --tail-lines 10000
```

如 unit 被 systemd-oomd 再次终止，保留 trace、unit journal 和 `partial_result.json`；**停止，不改预算或顺序重跑**。如 `resource_trace.jsonl` 缺失或格式损坏，也停止并报告。若任一策略一致性失败，照样保存首次分叉、停止后续性能队列。勿使用 `--allow-concurrent`。

## 4. 回传与 G2c/G3 门禁

在 `results/reports/a100-g2b-memory-20261103/G2B_SUMMARY.md` 记录：运行前 commit、GPU/系统资源门禁；L0/G2b 状态；每个策略的正确性与 PPL 差值；每个策略装载前/后/释放后的 CPU RSS、cgroup memory.current/peak、swap、PSI、CUDA 和去重池字节；`memory.events` 增量；最后一个已持久化样本的时间和距 unit 终止的间隔。若 oomd 再发生，区分“trace 显示的压力变化”与“oomd 触发策略”两个结论，后者可能仍需系统日志。

只提交 L0 和 G2b 的 report 目录及本次相关 unit journal 摘录；检查无权重、store、令牌或无关用户信息后推送结果分支。回复 `branch / commit / run IDs / 三策略状态 / oomd 是否复现 / 最后样本 / 内存峰值 / 阻塞项`。

**正式性能实验的门禁**：必须先有三个策略完成的正确性结果、G2 的物理容量及分阶段计量、基线容量/预取对齐，以及可验证的存储介质信息。G2b 完成后先停在此处，等待本地审核并领取 G2c/G3 工作包；不得自行将 G2b 的时间数据画成性能图。
