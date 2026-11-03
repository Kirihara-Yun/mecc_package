# WorkBuddy A100：停用近失预测预取后的单变量复测（2026-11-03）

先读 `AGENTS.md`、`WORKBUDDY.md`、`docs/EXPERIMENTS.md`、`docs/PROVENANCE.md` 和 `mecc_package/results/reports/a100-memory-trace-20261103/MEMORY_TRACE_SUMMARY.md`。本轮只检验显存溢出的候选原因，不生成论文或 PPT 性能数据。

## 改动与假设

新设计分支 `design/a100-nearmiss-guard-20261103` 相对上一轮运行前提交 `1c71971`，只停用 Mixtral 前向里对 `prefetch_near_miss()` 的调用。三级缓存、预算、模型、输入、`batch_prefetch` 和追踪代码保持原样。预测预取缓冲曾随 decode 增长并在 B1 第 5 个 decode 步达到约 33.5 GiB；本轮检查停用后该缓冲是否为零、同配置能否完成。若仍 OOM，继续保留失败事实和轨迹，不再调整预算。

## 执行门禁

1. GPU 空闲且可独占时，从本设计分支建立**新的干净 checkout**和 `gpu/a100-nearmiss-ablation-20261103` 结果分支；记录运行前 commit、模型 snapshot 和 store manifest。旧报告目录不删除、不覆盖。
2. 运行 `run_cpu_checks.py` 和 `l0_smoke.json` 一次。L0 失败即停止 GPU 实验并回传。
3. 用 `diag_a100_50g_p1_t16_trace.json` 跑**一次** 1 输入 × 16 token。先 `--dry-run` 核对命令（50/40 GB、`ours`、`uniform`、`skip_ppl`、`trace_memory`），再运行；无论完成或 OOM，都导出报告。
4. 只有上一步完成且 GPU 仍空闲，才用冻结的 `diag_a100_50g_p4_t16.json` 加 `--trace-memory` 跑**一次** 4 输入 × 16 token，先 dry-run 后运行并导出报告。若出现 OOM，停止。

模型与 store 沿用上一轮：

```text
/data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61
/data/mecc_store_mixtral
```

每项用 `experiment_launcher.py run <new-run-id> --config <config> --state-path <snapshot> --store-root /data/mecc_store_mixtral --gpu 0 --dry-run` 检查，去掉 `--dry-run` 运行；随后用 `experiment_launcher.py report <new-run-id> --tail-lines 10000` 导出。第二项另加 `--trace-memory`。

## 回传

提交所有紧凑报告和 `NEARMISS_ABLATION_SUMMARY.md`，逐步比较：`cuda_allocated_bytes`、`cuda_reserved_bytes`、`cuda_peak_allocated_bytes`、`gpu_pool_bytes`、`gpu_prefetch_bytes`、`gpu_nearmiss_bytes`、`nearmiss_entries`。记录每个实际 `input_tokens`、完成/失败阶段与错误堆栈。把前轮 B1 轨迹当诊断参照，只判断该单变量是否消除了缓冲增长和 OOM；**不比较速度或命中率，也不把 `skip_ppl` 的占位字符串当质量结果**。存储物理介质仍记 `unknown`。

推送结果分支后回复 `branch / commit / run_id / L0、B1、B3 状态 / 近失缓冲与显存趋势 / 一句话观察`，然后停止，等待本地做正确性和物理预算审计。
