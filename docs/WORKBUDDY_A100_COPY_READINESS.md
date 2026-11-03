# WorkBuddy A100：专家拷贝就绪与短窗 PPL 诊断（2026-11-03）

先读 `AGENTS.md`、`WORKBUDDY.md`、`docs/EXPERIMENTS.md`、`docs/PROVENANCE.md`，以及上一轮 `mecc_package/results/reports/a100-nearmiss-ablation-20261103/NEARMISS_ABLATION_SUMMARY.md`。本轮只验证拷贝就绪补丁和输出质量的初步一致性；**不产出论文或 PPT 的性能柱高**。

## 1. 本地变更与判断范围

从设计分支 `design/a100-copy-readiness-20261103` 建立新的干净 checkout，再建结果分支 `gpu/a100-copy-readiness-20261103`。本地代码在 `load_experts()` 向计算者交付 CUDA 专家权重前，等待 copy stream 完成，并登记计算流使用；同时给 launcher 增加可配置的短窗 `ppl_tokens`，在日志中记录输入哈希。预测近失预取继续关闭。

这解决的是静态代码中的**使用前就绪风险**。一次相同 PPL 只能初筛输出是否明显分叉，不能替代逐层路由、logits 和 token 的正式一致性证明；X7 物理容量、X9 分相位计量仍未关闭。

## 2. 门禁与顺序

1. 确认 A100 空闲独占、模型 snapshot 与 store manifest 与上一轮相同；记录运行前 commit。GPU 忙则仅回传 `BLOCKED`。
2. 运行 `python3 mecc_package/scripts/run_cpu_checks.py` 与 launcher L0（`l0_smoke.json`，新 run ID），保存完整报告。任一失败则停止。
3. 对 `diag_a100_copy_readiness_ppl128.json` 先执行 `--dry-run`，确认命令包含 `ours,swapmoe`、50/40 GB、1 输入、2 token、`ppl_tokens=128`、`trace_memory`，且**没有** `--skip_ppl`。然后运行一次，结束后 `report --tail-lines 10000`。记录结果中两策略的实测 PPL 数字、差值、`[inputs]` 的两个 SHA256 与 `ppl_input_tokens`。若日志出现 WikiText-2 fallback，明确标“内置文本诊断”，不得称为 WikiText-2 质量实验。
4. 若第三步完成、GPU 仍空闲，再对原 `diag_a100_50g_p4_t16.json` 加 `--trace-memory` 做一次 4 输入 × 16 token 的 `ours` 稳定性检查。先 dry-run，再运行并导出报告。它只检查新同步屏障是否引入 OOM 或异常；不比较速度。

模型 snapshot：

```text
/data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61
```

store：`/data/mecc_store_mixtral`。所有运行使用新的 run ID，建议分别命名 `a100-l0-copy-ready-20261103`、`a100-copy-ready-ppl128-20261103`、`a100-copy-ready-p4t16-20261103`。运行命令沿用 `experiment_launcher.py run <ID> --config <CONFIG> --state-path <snapshot> --store-root /data/mecc_store_mixtral --gpu 0 --dry-run`，核对后去掉 `--dry-run`；每项执行 `experiment_launcher.py report <ID> --tail-lines 10000`。

## 3. 回传与停止

把紧凑报告和 `COPY_READINESS_SUMMARY.md` 提交到新结果分支。总结逐项列：`complete/failed`、PPL 输入来源与哈希、两策略 PPL、是否出现 OOM/NaN、`cuda_allocated/reserved/peak` 与 `gpu_nearmiss_bytes` 的范围、失败堆栈。`skip_ppl=true` 的 4×16 行不算质量结果。首次路径或配置输入错误时保留失败报告，用新 run ID 修正，并解释偏差。

结果推送后回复 `branch / commit / 最后 run_id / L0、PPL、4×16 状态 / 一句话异常或观察`，然后停止。不得自行改缓存策略、预算、精度、输入、模型 revision 或冷读设置；不要把这轮 PPL 相近写成完整无损证明。
