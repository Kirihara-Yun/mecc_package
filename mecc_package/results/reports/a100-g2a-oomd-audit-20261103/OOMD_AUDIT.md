# G2a：G1 systemd-oomd 事件只读审计

> 只读审计，2026-11-03。基础结果为 `gpu/a100-g1-correctness-20261103@02cc4f6`。
> 本轮未启动 GPU 实验，未修改代码、缓存策略、预算、门限或输入。
> 目的：保全并核对 G1 被 systemd-oomd 终止的系统证据，回答工作包 §1 的四个问题。

## 1. 审计元信息

| 项 | 值 |
|---|---|
| 审计分支 | `gpu/a100-g2a-oomd-audit-20261103`（追踪 `origin/design/a100-g2a-oomd-audit-20261103`） |
| 审计 commit | `823fcc7cbb6e2039bdba78172dd52a718583382d` |
| 被审计结果 | `gpu/a100-g1-correctness-20261103@02cc4f6`，run `a100-g1-correctness-20261103` |
| 命令运行时间 | 2026-11-03 约 17:27（事发时间窗 16:35–17:12） |
| 采集目录 | `mecc_package/results/reports/a100-g2a-oomd-audit-20261103/` |

**日志可用性与权限限制**：

| 日志 | 状态 | 说明 |
|---|---|---|
| `g1_unit_journal.txt` | **可用**（1423 B，5 条） | user manager（`systemd[2013343]`）日志，无需特权 |
| `oomd_journal.txt` | **unavailable** | `-- No entries --`；stderr 提示需 `adm`/`systemd-journal` 组才能看系统消息 |
| `kernel_journal.txt` | **unavailable** | `-- No entries --`；同上权限提示，无法确认是否有内核 OOM 事件 |

> systemd-oomd 系统日志与内核日志因权限不可读，未请求 sudo、未猜测数值。

## 2. 事发时间线（每条事实对应文件与原文行）

来源文件：`g1_unit_journal.txt`、`run_tail.log`、`status.json`、`partial_result.json`（均在 `results/reports/a100-g1-correctness-20261103/`）。

1. **16:42:40 启动** — `g1_unit_journal.txt`：
   `Started /usr/bin/python3 correctness_probe.py --model mistralai/Mixtral-8x7B-Instruct-v0.1 ... --policies naive,ours,swapmoe ... --hbm_budget 50.0 --cpu_budget 40.0`
2. **16:42:43 结果落盘起点** — `partial_result.json`：`run_time=2026-11-03T16:42:43`。
3. **naive 完成** — `run_tail.log`：`[policy] naive passed= True ppl= 20.443230408996836`；`partial_result.json` naive `passed=true`。
4. **ours 完成** — `run_tail.log`：`[policy] ours passed= True ppl= 20.443230408996836`；`partial_result.json` ours `passed=true`。
5. **swapmoe 开始装载** — `run_tail.log`：
   `[phase] running_policy {'policy': 'swapmoe', 'completed_policies': ['naive', 'ours']}` →
   `[build] loaded 227 trunk/gate tensors → cuda`（这是 `run_tail.log` 的最后一行，之后无输出）。
6. **17:03:09 状态快照** — `status.json`：`phase=running_policy`、`policy=swapmoe`、`completed_policies=[naive, ours]`。
7. **17:05:47 被杀** — `g1_unit_journal.txt`（原文）：
   ```
   mecc-exp-a100-g1-correctness-20261103.service: systemd-oomd killed 196 process(es) in this unit.
   mecc-exp-a100-g1-correctness-20261103.service: Main process exited, code=killed, status=9/KILL
   mecc-exp-a100-g1-correctness-20261103.service: Failed with result 'signal'.
   mecc-exp-a100-g1-correctness-20261103.service: Consumed 1h 8min 21.982s CPU time.
   ```

> 注意：`Consumed 1h 8min` 为**累计 CPU 时间**（多核/多进程），非墙钟时间；墙钟约 23 分钟（16:42:40 → 17:05:47）。

## 3. systemd-oomd vs 内核 OOM：已证实 / 未证实

- **已证实：终止者是 systemd-oomd（用户态 cgroup 定向 kill）。**
  证据 = user manager journal 明确记录 `systemd-oomd killed 196 process(es) in this unit` 与
  `Main process exited, code=killed, status=9/KILL`（SIGKILL）、`Failed with result 'signal'`。
  这是 systemd-oomd 基于压力策略向目标 unit/cgroup 发送 SIGKILL 的典型记录，非 CUDA 显存 OOM。
- **未证实：内核 OOM killer 是否参与。**
  `kernel_journal.txt` 因权限不可读（`-- No entries --` + 权限提示），**无法确认**是否有内核级 OOM 事件。
  `user.slice/memory.events` 的 `oom_kill 11` 为**历史累计**（见 §4），不能归因于本次事件。

**触发机制判断（候选，非已证实）**：unit 级 `MemoryMax/MemoryHigh/MemorySwapMax=infinity`（见 §4），
所有祖先 cgroup 也均为 `max`，即**不存在任何 cgroup 硬内存上限**。因此 systemd-oomd 的触发更可能来自
`ManagedOOMMemoryPressure=auto` / `ManagedOOMSwap=auto` 下的 **PSI 内存压力或 swap 压力**，而非硬限制超限。
这一判断仅基于"无硬限制 + oomd 默认压力管理"的静态配置推断，**未获得事发时 PSI/压力值的直接证据**。

## 4. 目标 cgroup 与当前内存快照（非事发峰值）

**目标 unit cgroup**：

- `systemctl --user show mecc-exp-a100-g1-correctness-20261103.service -p ControlGroup` → **空**，
  且 `ActiveState=inactive`。即 unit 的 cgroup 已被 systemd 回收，**事发时 unit 级 cgroup 内存值无法读取**。
- 当前 systemctl 属性为 `Result=success`、`ExecMainStatus=0`，与 journal 的 `Failed with result 'signal'` 不一致。
  原因：unit 已 inactive + cgroup 已回收，该属性为回收后残留值，**不能反映事发时状态**；以 journal 原文为准。

**unit / manager 级内存配置（当前）** — `unit_properties.txt`：

```
MemoryHigh=infinity   MemoryMax=infinity   MemorySwapMax=infinity
ManagedOOMSwap=auto   ManagedOOMMemoryPressure=auto
```

**祖先 cgroup 当前快照** — `current_cgroup_ancestors.txt`（⚠️ 均为事件后当前值，非事发峰值）：

| cgroup | memory.current | memory.max | memory.high | swap.max | events 关键项 |
|---|---|---|---|---|---|
| `/user.slice/user-1002.slice/session-17857.scope`（当前 shell） | 3.3 GiB | max | max | max | 全 0 |
| `/user.slice/user-1002.slice` | 342.6 GiB | max | max | max | 全 0 |
| `/user.slice` | 569.7 GiB | max | max | max | `oom_kill 11`（历史累计） |
| `/` | — | — | — | — | pressure total≈23.3B（历史累计） |

**系统内存当前快照** — `current_meminfo.txt`（事件后）：

```
MemTotal ≈ 1007 GiB   MemAvailable ≈ 984 GiB   SwapTotal ≈ 2.0 GiB
```

- 所有层级 `memory.max`/`memory.high` 均为 `max`，**无硬内存上限**。
- `user.slice/memory.events` 的 `oom_kill=11` 是 slice 级**历史累计计数**，非本次专属，且无法读内核日志以拆分归属。
- 当前快照发生在事件后、GPU 已释放、其他任务并存，**不能当作事发时峰值**。

## 5. 原 G1 partial_result 的 GPU 内存值（非 CPU 账）

来源 `results/reports/a100-g1-correctness-20261103/partial_result.json`：

| 策略 | passed | ppl | cuda_allocated_bytes_after | cuda_reserved_bytes_after |
|---|---|---|---|---|
| naive | true | 20.443230408996836 | 48316948480（≈45.0 GB） | 83372277760（≈77.6 GB） |
| ours | true | 20.443230408996836 | 48316948480（≈45.0 GB） | 82348867584（≈76.7 GB） |
| swapmoe | 未完成 | — | 无 | 无 |

> 这些是 **GPU/CUDA 值**（`allocated≈45 GB`、`reserved≈77 GB`，均低于 80 GB 显存），
> **不能替代 CPU RSS / VmLck / pinned 页账**。G1 全程无 CPU 侧物理内存采样，这正是 G2 要补的计量。

## 6. 下一轮 G2b 最小采集字段

为在可能再次被杀时留下足够证据，需在每个策略的 **装载前 / 装载后 / 释放后** 三个时间点采样：

- 目标 unit cgroup：`memory.current` / `memory.max` / `memory.high` / `memory.events` / `memory.pressure`；
- 进程级：`RSS`、`VmLck`（`/proc/<pid>/status`）；
- 宿主：`MemAvailable`（`/proc/meminfo`）、`/proc/pressure/memory`；
- GPU：`nvidia-smi` allocated / reserved；
- 各缓存池**去重后字节**（pinned / pageable / 镜像 / staging 分离）；
- swap：`memory.swap.current` 与宿主 `SwapFree`；
- 每个策略完成后的 `cuda_allocated/reserved_bytes_after` 与 CPU 峰值快照。

## 7. 结论与缺失的事发时采样

**已能确认（已证实）**：

1. G1 的 `swapmoe` 未完成，进程于 17:05:47 被 **systemd-oomd** 以 SIGKILL 终止（`systemd-oomd killed 196 process(es)`），非 CUDA 显存 OOM。
2. `naive`、`ours` 已完成并通过（路由/logits/token/PPL 全等），已落 `partial_result.json`。
3. 事发时 swapmoe 停在 `loaded 227 trunk/gate tensors → cuda`（expert 装载阶段），此后无任何输出。
4. 全链路**无 cgroup 硬内存上限**（unit 与祖先均 `max`），oomd 触发机制更可能为压力/swap 管理而非硬限制超限。

**未能确认（缺失的事发时采样）**：

1. 事发时 **unit cgroup 的 memory.current / events / pressure**（cgroup 已回收，无留存采样）。
2. 事发时 **进程 RSS / VmLck / pinned 字节**（G1 未采集 CPU 侧内存账）。
3. **systemd-oomd 系统日志**与**内核 OOM 日志**（权限不可读，`unavailable`）。
4. 事发时 **PSI 压力值 / swap 峰值**（当前快照为事件后，不能替代）。

**定位结论**：现有证据**足以确认"systemd-oomd 是终止者 + 触发点位于 swapmoe 装载阶段"**，但
**不足以定位触发 oomd 的具体 cgroup 内存/压力来源**。工作包 §1 提出的
「三策略顺序装载导致 CPU 内存累积」仍为**候选解释，未证实**；需按 §6 的采样方案在 G2b 复测中取证。

---

**不启动新的 G1 或 G2 GPU 运行。到此停止，等待本地 G2b 内存追踪补丁与配置。**
