# Workbuddy G2a：G1 的 systemd-oomd 事件只读审计

> 冻结工作包，2026-11-03。基础结果为 `gpu/a100-g1-correctness-20261103@02cc4f6`。本轮**不启动 GPU 实验**，不修改代码、缓存策略、预算、门限或输入；只保全和核对 G1 被终止的系统证据。完成后等待本地 G2b 内存追踪补丁与配置。

## 1. 已知事实与待回答问题

G1 的 `partial_result.json` 已保存 `naive`、`ours` 两个策略；两者在两个短输入上的路由、logits、token 与诊断 PPL 一致。`swapmoe` 开始装载模型后，进程被 `SIGKILL`，没有 `result.json`。Workbuddy 汇总称 `systemd-oomd` 在 2026-11-03 17:05:47 终止该 unit；原始 journal 摘录尚未随报告提交。

这轮只需回答：

1. 是否能从 journal 明确确认 **systemd-oomd**、目标 unit/cgroup、时间和触发条件？是否有内核 OOM 记录？
2. 当前用户 slice / 可访问的祖先 cgroup 的 `memory.max`、`memory.high`、`memory.swap.max`、`memory.events` 和 PSI 配置是什么？**当前值不能当作事发时峰值。**
3. 原 G1 报告中实际能确认的最后一个阶段、策略和 GPU 内存值是什么？哪些 CPU/锁页内存事实尚无采样？
4. 下一轮监测必须覆盖哪些路径/阈值，才能在可能再次被杀时留下足够证据？

“三个策略顺序装载导致 CPU 内存累积”仍是**候选解释**，不得在本轮写成已证实根因。

## 2. 分支与只读命令

从干净 checkout 执行；不要复用正在运行其他任务的目录。以下命令只查询日志和系统状态，不含模型前向或写 store：

```bash
git fetch origin
git switch -c gpu/a100-g2a-oomd-audit-20261103 origin/design/a100-g2a-oomd-audit-20261103
git status --short
git rev-parse HEAD

RUN=a100-g1-correctness-20261103
UNIT=mecc-exp-${RUN}.service
OUT=mecc_package/results/reports/a100-g2a-oomd-audit-20261103
mkdir -p "$OUT"

journalctl --user -u "$UNIT" --since '2026-11-03 16:35:00' \
  --until '2026-11-03 17:12:00' --no-pager -o short-iso \
  > "$OUT/g1_unit_journal.txt" 2> "$OUT/g1_unit_journal_error.txt" || true

journalctl -u systemd-oomd --since '2026-11-03 16:35:00' \
  --until '2026-11-03 17:12:00' --no-pager -o short-iso \
  > "$OUT/oomd_journal.txt" 2> "$OUT/oomd_journal_error.txt" || true

journalctl -k --since '2026-11-03 16:35:00' \
  --until '2026-11-03 17:12:00' --no-pager -o short-iso \
  > "$OUT/kernel_journal.txt" 2> "$OUT/kernel_journal_error.txt" || true

systemctl --user show "$UNIT" \
  -p ActiveState -p Result -p ExecMainStatus -p ControlGroup \
  -p MemoryMax -p MemoryHigh -p MemorySwapMax \
  -p ManagedOOMMemoryPressure -p ManagedOOMSwap \
  > "$OUT/unit_properties.txt" 2>&1 || true

systemctl --user show --property=ControlGroup,MemoryMax,MemoryHigh,MemorySwapMax,ManagedOOMMemoryPressure,ManagedOOMSwap \
  > "$OUT/user_manager_properties.txt" 2>&1 || true
```

仅为判断**当前**资源约束，再采一次快照：

```bash
cat /proc/self/cgroup > "$OUT/current_cgroup.txt"
cat /proc/meminfo > "$OUT/current_meminfo.txt"
cat /proc/pressure/memory > "$OUT/current_memory_pressure.txt"
CG=$(sed -n 's/^0:://p' /proc/self/cgroup)
while :; do
  for file in memory.current memory.max memory.high memory.swap.current memory.swap.max memory.events memory.pressure; do
    if test -r "/sys/fs/cgroup$CG/$file"; then
      { echo "=== $CG / $file ==="; cat "/sys/fs/cgroup$CG/$file"; } >> "$OUT/current_cgroup_ancestors.txt"
    fi
  done
  test "$CG" = / && break
  CG=$(dirname "$CG")
done
nvidia-smi --query-gpu=name,memory.used,utilization.gpu --format=csv,noheader \
  > "$OUT/gpu_after_event.txt" 2>&1 || true
```

`systemd-oomd` 系统日志或旧 unit 属性若因权限/回收不可读，保留错误文件并在总结中写 `unavailable`；不要请求 sudo、不要猜数值。可用的 journal 可能包含别人的进程信息；提交前只保留与本次 unit/oomd 判定直接相关的行，删去无关用户及路径，但保留原始时间、unit 名和触发文字。完整日志可留在远端。

## 3. 对照原报告与判定

阅读而不改动：

```bash
cat mecc_package/results/reports/a100-g1-correctness-20261103/status.json
cat mecc_package/results/reports/a100-g1-correctness-20261103/run.json
cat mecc_package/results/reports/a100-g1-correctness-20261103/G1_SUMMARY.md
```

写 `$OUT/OOMD_AUDIT.md`，依次列：

- 审计分支/commit、命令运行时间、日志可用性和权限限制；
- 事发时间线（至少 `naive complete → ours complete → swapmoe build → kill`），每条事实对应文件和原文行；
- `systemd-oomd` 与内核 OOM 的**已证实 / 未证实**区分；目标 cgroup、压力策略、触发文字；
- 当前 cgroup 与系统内存快照及“非事发峰值”的说明；
- 原 G1 `partial_result` 中两个已完成策略的 `cuda_allocated/reserved`（这些是 GPU 值，不能替代 CPU RSS/pinned 账）；
- 下一轮 G2b 需要采集的最小字段：目标 cgroup 的 current/max/high/events/pressure、进程 RSS/VmLck、宿主 MemAvailable、GPU allocated/reserved、各缓存池去重字节；每个策略的装载前/装载后/释放后时间点；
- 结论是否足以定位 oomd 触发范围；若不能，明确列出缺失的事发时采样。

检查报告中没有模型权重、store 数据、令牌或无关用户信息后，仅提交 `$OUT` 并推送结果分支：

```bash
git add "$OUT"
git commit -m "results: audit G1 systemd-oomd event"
git push -u origin HEAD
```

最终回复：`branch / commit / 事发日志是否可用 / oomd 是否确认 / 目标 cgroup 是否确认 / 当前内存限制 / 尚缺的证据`。到此停止。**不得启动新的 G1 或 G2 GPU 运行。**
