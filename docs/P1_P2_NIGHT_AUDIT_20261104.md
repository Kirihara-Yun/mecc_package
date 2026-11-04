# 11 月 3–4 日 A100 回传冷读审计

审计源：`gpu/a100-p0-gates-20261103@6009409`，逐项核对 `docs/G0_CONTRACT_20261103.md`、P0/P1/P2 报告 JSON、代码和 P2 驱动。此文只校正证据口径，不改任何已运行结果。

## 已完成

1. `a100-p0-swapmoe-20261103` 在单独的 unit 中按 `naive,swapmoe` 运行，和此前 G1/G2b 的 `naive,ours` 组成同输入、同预算的短窗内部正确性证据。路由、logits、token、诊断 PPL 一致。此证据仍共享同仓库 MoE dispatch，不是独立 Hugging Face 全驻留对照。
2. P1 五策略各完成**一次** A100 真机运行，单独 unit 避免此前三策略顺序运行的 oomd。P1 固定内置四条输入、生成 16 token；PPL 采用 WikiText-2 下载失败后的 77-token 内置回退文本。结果可作试跑、估时与趋势诊断。
3. P2 已提交 `cpu_budget=20` 的 ours 结果；截至 `6009409`，`cpu_budget=20` 的 swapmoe 已启动，后续预算点和重复未见终态报告。仓库中的 `p1a-cpu*-run*` 是 10 月的旧数据，配置不同，不可充作 P2 重复。

## 需要立即校正的表述

| 项 | 原表述 | 核对后结论 |
|---|---|---|
| P1 ours / flashmoe | 1.015× | `0.078429 / 0.079564 = 0.986×`。1.014× 是反方向，且单次差异不能判稳定优劣。 |
| P1 五策略 PPL | 全无损、全等 | 四策略为 24.569；fiddler 为 24.589。数字差 0.020，需单独设质量判据；不能写全等。 |
| P1 作为正式主图 | `verified` 即可绘图 | 五策略每项仅一次，输入为内置回退，不含固定 QA/Code benchmark，物理预算峰值也未闭合。数据真实，但只达到初筛。 |
| X9 分阶段计量 | warmup/prefill/decode/PPL 已齐 | 代码仅有 warmup/decode/PPL；`measure_latency` 的 prefill 也在 decode 桶。`io_bytes.ssd_read` 由 miss 次数乘 expert 大小得到，是应用请求字节，未用块设备计数核对。 |
| X7 容量公平性 | `K_H/K_C`、初始池相同即通过 | 初始 CPU 存活 storage 为 73.50 GiB（镜像 42.00 + CPU 池 31.50），大于名义 40 GB 温层预算；运行中峰值及各策略页缓存尚未对齐。 |
| 存储介质 | HDD 物理盘已证实 | `/dev/sdb` 是 RAID 暴露设备，`ROTA=1` 仅说明系统报告旋转。未提交控制器后的物理盘型号清单；论文可写「RAID 块设备，操作系统报告旋转介质」。 |

P1 的其他单次吞吐比按原始 `result.json` 可复算：ours/swapmoe = 2.33×，ours/naive = 1.64×，ours/fiddler = 1.18×。这些值属于当前固定内置输入下的 D2 初筛，暂不进入正式论文/PPT 实验图。历史 `raw/mixtral_real.json` 的 1.33× 属另一预算和指标口径，不参与本轮平均。

## P2 驱动的停止条件

`p2_budget_driver.sh@6009409` 仅等待 `status.json.phase` 变成 `complete/failed`。systemd-oomd 杀掉进程时，status 可能停留在 `running_policy`，旧驱动会无限等待。此分支增加：检查 unit 是否仍 active、单任务两小时观察上限、失败即停、已完成 run ID 安全跳过；不会覆盖旧结果。脚本通过 `bash -n`。

**交接给 Workbuddy**：先检查当前 P2 unit 与旧 driver 的实际状态。正在运行的 GPU unit 继续由原进程完成；如 unit 已退出而 status 未终结，只停止旧 driver，保存该 run 的日志，再用本分支脚本继续。任何错误、OOM、超时均停止队列并回传。不要同时启动两个 driver，也不要重用已有 run ID。新的脚本不会自动修复已经启动的旧 shell 进程。

下一批正式实验的优先项：固定可离线复现的 QA/Code/PPL 输入及 token 哈希；同配置至少三次独立重复；各策略 GPU/CPU 物理峰值；prefill 与 decode 分桶；应用请求字节和块设备物理读字节的口径区分。先满足这些，再冻结论文/PPT 图格。

本地 `verify_claims.py` 仍有既存的 R1–R4 D1 证据一致性失败（`AssertionError`）；本次未改该证据或检查逻辑。正式对外引用前须另行修复并重跑全绿。
