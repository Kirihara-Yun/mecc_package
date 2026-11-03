# WorkBuddy A100：定位逐步增长的显存占用（2026-11-03）

本轮只验证显存占用的来源，不产出论文或 PPT 性能数据。先读 `AGENTS.md`、`WORKBUDDY.md`、`docs/EXPERIMENTS.md`、`docs/PROVENANCE.md`、上一轮的 `mecc_package/results/reports/a100-oom-recovery-20261103/RECOVERY_SUMMARY.md`。上一轮 B1 在 1 输入 × 16 token 时 OOM，B2 在 4 输入 × 2 token 时完成；物理存储介质仍为 `unknown`。

## 1. 代码与实验口径

从 `design/a100-memory-audit-20261103` 建立新的干净结果 checkout 和 `gpu/a100-memory-trace-20261103` 分支。记录运行前 commit；不要在旧结果 checkout 上修改代码。新代码只增加 `--trace_memory` 诊断开关，不改变缓存策略。每条日志以 `MEMTRACE ` 开头，包含实际 tokenized 输入长度、prefill/decode 步号、CUDA allocated/reserved/peak，以及专家 GPU 池、批量预取、预测预取缓冲的字节数。`gpu_nearmiss_bytes` 是否增长是要验证的假设，不是预设结论。

远端仍须先确认 GPU 空闲且可独占；若被他人使用，停在只读检查。模型 revision 和 store 与上一轮相同：

```text
/data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61
/data/mecc_store_mixtral
```

## 2. 执行顺序

1. 运行现有 `run_cpu_checks.py` 与一次 L0 smoke，确认新增可选参数没有破坏逻辑链路。使用新 run ID，导出报告。L0 只验证逻辑。
2. 先对 `diag_a100_50g_p1_t16_trace.json` 执行 `--dry-run`，核对固定配置仍是 `ours`、50/40 GB、1 输入、16 token、`skip_ppl=true`、`uniform=true`，且命令含 `--trace_memory`。再运行一次。无论 `complete` 或 `failed`，用 `report --tail-lines 10000` 导出完整 MEMTRACE 和堆栈。
3. 若 GPU 仍空闲，再对原 `diag_a100_50g_p4_t2.json` 加 `--trace-memory` 执行一次，作为短序列参照；同样先 `--dry-run`，再运行并导出报告。若前一步出现影响机器稳定的异常则停止，并记录原因。
4. 不运行 B3、正式主表、消融、第二模型；不调整预算、输入、预取策略或缓存代码。

建议的运行命令（每项使用新的 run ID）：

```bash
python3 mecc_package/scripts/experiment_launcher.py run a100-oom-trace-p1t16-20261103 \
  --config mecc_package/e2e/configs/diag_a100_50g_p1_t16_trace.json \
  --state-path /data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61 \
  --store-root /data/mecc_store_mixtral --gpu 0 --dry-run
# 检查命令后去掉 --dry-run，运行结束再执行：
python3 mecc_package/scripts/experiment_launcher.py report a100-oom-trace-p1t16-20261103 --tail-lines 10000

python3 mecc_package/scripts/experiment_launcher.py run a100-oom-trace-p4t2-20261103 \
  --config mecc_package/e2e/configs/diag_a100_50g_p4_t2.json --trace-memory \
  --state-path /data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61 \
  --store-root /data/mecc_store_mixtral --gpu 0 --dry-run
# 检查命令后去掉 --dry-run，运行结束再执行：
python3 mecc_package/scripts/experiment_launcher.py report a100-oom-trace-p4t2-20261103 --tail-lines 10000
```

## 3. 回传判据

在结果分支提交紧凑报告和 `MEMORY_TRACE_SUMMARY.md`。总结逐步列出 CUDA allocated/reserved/peak、`gpu_pool_bytes`、`gpu_prefetch_bytes`、`gpu_nearmiss_bytes`、`nearmiss_entries` 的变化，指出 OOM 发生的 `run_phase` 与 `step`。对 B1/B2 比较实际 `input_tokens`，不能把不同 prompt 长度误当成只改变了解码步数。若 `MEMTRACE` 丢失或异常，原样回传，不补造。

当前代码中 `_nearmiss_buf` 没有显式按步清理，CPU 命中又优先从 `cache.cpu` 取权重；这是本地静态审查发现的候选原因。只有轨迹显示相应缓冲增长，才能进一步归因。报告仍不能替代正确性、物理字节公平性和真实存储介质门禁。

推送新结果分支后回复：`branch / commit / run_id / L0、B1、B2 状态 / MEMTRACE 是否完整 / 一句话观察`。
