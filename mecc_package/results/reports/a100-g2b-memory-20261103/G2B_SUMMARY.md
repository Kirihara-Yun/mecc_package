# G2b：保留 OOM 前内存轨迹并补齐三策略正确性

> 冻结工作包，基础证据 `gpu/a100-g2a-oomd-audit-20261103@0292ea1`。
> 本轮在 G1 的同一模型、store、输入、预算、门限和策略顺序上**只添加计量**（每秒内存轨迹 + 张量存活账），
> 未改任何预算/顺序/输入。速率数据一律不作为性能结果。

## 0. 运行前门禁（Gate A/B）

| 项 | 值 | 判据 |
|---|---|---|
| 运行前 commit | `b1f6b99b8e28d44c8dee5e9aa1dc5535a46d9e13` | 设计分支 `design/a100-g2b-memory-trace-20261103` |
| GPU | A100 80GB PCIe，1 MiB / 81920 MiB，0 % | **空闲** ✓ |
| 其他 MECC unit | 无（`systemctl --user list-units 'mecc-exp-*'` 为空） | ✓ |
| 活动 GPU 进程 | 无 | ✓ |
| MemAvailable | 1031938600 kB ≈ 984 GiB | 充足 ✓ |
| Swap | Total 2097148 kB ≈ 2.0 GiB，Free 1755876 kB | ✓ |
| store manifest SHA256 | `c943c4173e1c6dbac73fe12a8d5f03d51e52acbffabb476e2e3a1cd994b71255` | 与 G1 一致 ✓ |
| 模型 revision | `eba92302a2861cdc0098cc54bc9f17cb2c47eb61`（路径已核实） | 与 G1 一致 ✓ |
| fixture SHA256 | `913c816407bfd5fa9aacb8476f34648238dd749ff384c1bd96876f8fef6fa3f6` | 与 G1 一致 ✓ |
| CPU 回归 `run_cpu_checks.py` | **PASS**（5 策略均 `exact(lossless)`） | ✓ |

## 1. L0 与 G2b 状态

| run | 状态 |
|---|---|
| `a100-g2b-l0-20261103` | **COMPLETE**（`phase=complete`，`ExecMainStatus=0`；5 策略均 `exact(lossless)`） |
| `a100-g2b-memory-20261103` | **PARTIAL**（naive/ours 完成；swapmoe 再次被 systemd-oomd 终止） |

## 2. 三策略正确性（`partial_result.json`，`mode=diagnostic_correctness`）

| 策略 | 状态 | PPL | PPL 差(vs naive) |
|---|---|---|---|
| naive | **passed=true**（参考） | 20.443230408996836 | 0.0 |
| ours | **passed=true** | 20.443230408996836 | **0.0** |
| swapmoe | **未完成（18:06:11 被 systemd-oomd 杀）** | — | — |

> naive 与 ours 结果与 G1 完全一致（PPL 相同、差值 0）。swapmoe 正确性**仍未能补齐**，三策略正确性门禁仍未完整通过。

## 3. 内存轨迹（`resource_trace.jsonl`，1279 样本，17:44:33.597 → 18:06:00.136）

每秒采样：进程 `VmRSS/VmHWM/VmLck/VmPin`、目标 unit cgroup `memory.current/peak/events/pressure`、swap、宿主 `MemAvailable/PSI`。

| 阶段 | 样本数 | VmRSS 峰值 | cgroup.current 峰值 | cgroup.peak | PSI some avg10 |
|---|---|---|---|---|---|
| naive before_load | 90 | 79.67 GiB | 91.51 GiB | 91.51 GiB | ≈ 0 |
| naive after_load | 516 | 81.29 GiB | 93.38 GiB | 93.43 GiB | ≈ 0 |
| ours before_load | 152 | 80.97 GiB | 144.03 GiB | 144.03 GiB | ≈ 0 |
| ours after_load | 370 | 85.71 GiB | 146.22 GiB | 146.43 GiB | ≈ 0 |
| swapmoe before_load | 150 | 103.35 GiB | **159.75 GiB** | 159.75 GiB | 53.14→**62.66%** |

**关键观察**：

1. **cgroup 内存在跨策略累积**：naive ~93 GiB → ours ~146 GiB → swapmoe ~160 GiB。
   每个策略 `policy_released` 后（CUDA allocated 回落 8.5 MB、pool=null），cgroup `memory.current` 并未回落到基线，而是逐策略抬升。
2. **cgroup.current（146 GiB）远大于进程 RSS（85 GiB）与张量存活账（73.5 GiB）**：差值 ~60–72 GiB
   疑似 store 文件的 **page cache**（`cgroup memory.current` 含文件页，`VmRSS`/张量账不含）。这是 CPU 侧内存压力的主要来源，非进程匿名内存。

## 4. 张量存活账（`memory_checkpoints.jsonl`）

naive/ours 装载后（`after_load`）的去重字节（仅存活张量 storage，不含 trunk/分配器/页缓存）：

| 角色 | 字节 | GiB |
|---|---|---|
| gpu | 45097156608 | 42.00 |
| cpu_mirror | 45097156608 | 42.00 |
| cpu_pool | 33822867456 | 31.50 |
| cpu_staging | 0 | 0 |
| **all_unique_cpu_bytes** | **78920024064** | **73.50** |

- ours `before_release` 时 `all_unique_cpu_pinned_bytes = 63065554944`（≈58.73 GiB，pinned 有增长）。
- 每个策略 `after_release` 后 CUDA allocated 回落 8519680 B（8.5 MB）、pool=null，**张量释放成功**。

## 5. memory.events / swap 增量

- unit cgroup `memory.events`：全程 `oom 0 / oom_kill 0 / oom_group_kill 0`，**无变化**。
  即 systemd-oomd 是**用户态定向 SIGKILL**，不增加内核 OOM killer 的 cgroup 计数。
- unit cgroup `swap.events`：全程 `high 0 / max 0 / fail 0`；`swap.current` 全程 0（无 swap 使用）。
- `user.slice/memory.events`：`oom_kill 11` 全程无变化（历史累计，本次无内核 OOM）。

## 6. 最后已持久化样本

- 时间：`2026-11-03T18:06:00.136+08:00`，`pid_alive=True`，phase=`swapmoe/before_load`。
- 距 unit 终止（18:06:11）间隔 **≈ 11 秒**。
- 最后样本：`VmRSS=108374732 kB`（≈103.3 GiB）、`cgroup.current=171530579968`（≈159.75 GiB）、
  `unit PSI some avg10=62.66%`、`host.MemAvailable=923387264 kB`（≈880 GiB）。

## 7. oomd 复现：trace 压力变化 vs oomd 触发策略

**trace 显示的压力变化（已证实）**：

- swapmoe 装载阶段，unit cgroup `memory.current` 增长到 ≈159.75 GiB；
- 被杀前 5 秒 PSI some 快速上升：`avg10 53.14% → 55.29% → 62.66%`，`avg60 38.01% → 40.76%`；
- 宿主 `MemAvailable` 全程 ≈880–984 GiB，**宿主内存未耗尽**。

**oomd 触发策略（推断，非最终证实）**：

- unit/祖先 cgroup 均 `memory.max/high=infinity`（无硬上限），`ManagedOOMMemoryPressure=auto`、`ManagedOOMSwap=auto`；
- 触发极可能来自 **ManagedOOMMemoryPressure 的 PSI "some" > 50% 阈值**（trace 的 62.66% 与其一致）；
- 但 systemd-oomd 的**系统日志仍因权限不可读**，触发条件/阈值未经 oomd 自身日志最终确认。

## 8. 结论与阻塞项

- **达成**：完整保留了 swapmoe 终止前每秒内存轨迹与张量存活账，首次量化了
  「三策略顺序装载 → cgroup 内存累积（93→146→160 GiB）+ page cache 差额（~60 GiB）+ PSI some 飙升 62%」这条证据链。
- **未达成**：swapmoe 正确性结果再次缺失（同 G1 位置：`loaded 227 trunk/gate tensors → cuda` 之后的 expert 装载阶段被杀），三策略正确性仍不完整。
- **阻塞项**：systemd-oomd 系统日志不可读（需 `adm`/`systemd-journal` 权限）；宿主仅 2 GiB swap；
  cgroup 内存累积的根因（page cache 未被及时回收 / 策略间未完全释放）尚未定位到具体分配路径。

**按工作包要求：到此停止，不改预算或顺序重跑。等待本地审核并领取 G2c/G3 工作包。**
