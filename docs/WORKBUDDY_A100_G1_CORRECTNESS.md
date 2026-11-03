# Workbuddy A100 G1：固定输入下的缓存策略正确性诊断

> 这是 [实验补全总计划](MECC_EXPERIMENT_COMPLETION_PLAN.md) 中**第一份可执行工作包**。只检验同仓库 fp16 缓存策略的输出一致性；不产出论文或 PPT 的速度、命中率、质量 benchmark 结果。执行前仍需阅读 `AGENTS.md`、`WORKBUDDY.md`、`docs/EXPERIMENTS.md` 和 `docs/PROVENANCE.md`。

## 1. 冻结内容与比较范围

- 设计分支：`design/a100-g1-correctness-20261103`。从它建立新的、干净的 `gpu/a100-g1-correctness-20261103` 结果分支。
- 配置：`mecc_package/e2e/configs/diag_a100_g1_correctness_v1.json`；输入：`mecc_package/e2e/fixtures/correctness_diagnostic_v1.json`。两文件在本轮不得修改。
- 单卡 A100 80GB、Mixtral-8×7B-Instruct-v0.1 snapshot `eba92302a2861cdc0098cc54bc9f17cb2c47eb61`、现有 `/data/mecc_store_mixtral`；expert HBM/CPU 预算为 50/40 GB、fp16、冷盘读取路径、统一逐层配额、预测近失预取继续关闭。
- 三个策略的顺序固定为 `naive,ours,swapmoe`。`naive` 是同仓库 fp16 参考路径。三者共享 MoE dispatch 代码，因此本轮能检查**缓存策略是否改变输出**，不能证明与独立 Hugging Face 全驻留实现完全等价。
- 两个仓库自写的短 prompt，贪心生成 3 token；另用仓库自写的**离线诊断文本**计算 128-token PPL。它不是 WikiText-2，也不是质量 benchmark。工具不访问数据集网络，输入不足 128 token 会报错停止。
- 比较相同输入下每层每步的 top-k 专家 ID、最终 logits、贪心 token 和 PPL。后续策略的 decode 输入固定采用 `naive` 产生的 token，因此即使输出分叉，仍能定位第一处分叉。门限冻结为：路由 ID 和 token 完全一致，logits `allclose(atol=0.05, rtol=0.001)`，PPL 与参考之差不超过 `0.01`。结果中保存首次路由分叉位置、最大 gate/logit 误差和输入 token 哈希。

## 2. 上机前门禁

1. 确认 GPU 空闲、独占且无其他 MECC 作业；否则只回传 `BLOCKED: GPU busy`。
2. 确认模型 snapshot 目录、19 个 safetensors 分片、store manifest 和 256 个 expert 文件未变化；记录实际路径与运行前 commit。此轮只读使用现有 store，不重新物化。
3. 确认新结果分支工作区干净；运行 `python3 mecc_package/scripts/run_cpu_checks.py`。失败即停止。
4. 先对下面两个 launcher 命令做 `--dry-run`，检查程序是 `correctness_probe.py`、政策顺序、50/40 GB、2 个输入、3 个新 token、PPL 128、输入文件路径与 GPU 0。dry-run 不创建 run ID。
5. `/data` 的物理介质仍为 `unknown`；本轮仅正确性诊断，允许使用该 store，但不得称为 NVMe SSD 性能实验。

## 3. 固定命令

在仓库根目录执行。模型路径如果与下例不同，只能用实际已核实的**同 revision** snapshot 路径替换，并在报告中写明；其余配置不改。

```bash
git fetch origin
git switch -c gpu/a100-g1-correctness-20261103 origin/design/a100-g1-correctness-20261103
git status --short
git rev-parse HEAD
python3 mecc_package/scripts/run_cpu_checks.py

STATE=/data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61
STORE=/data/mecc_store_mixtral
LAUNCHER=mecc_package/scripts/experiment_launcher.py

python3 "$LAUNCHER" run a100-g1-l0-20261103 \
  --config mecc_package/e2e/configs/l0_smoke.json --gpu 0 --dry-run
python3 "$LAUNCHER" run a100-g1-l0-20261103 \
  --config mecc_package/e2e/configs/l0_smoke.json --gpu 0
python3 "$LAUNCHER" status a100-g1-l0-20261103
python3 "$LAUNCHER" report a100-g1-l0-20261103 --tail-lines 10000
```

只有 L0 `complete` 且无异常时才执行：

```bash
python3 "$LAUNCHER" run a100-g1-correctness-20261103 \
  --config mecc_package/e2e/configs/diag_a100_g1_correctness_v1.json \
  --state-path "$STATE" --store-root "$STORE" --gpu 0 --dry-run
python3 "$LAUNCHER" run a100-g1-correctness-20261103 \
  --config mecc_package/e2e/configs/diag_a100_g1_correctness_v1.json \
  --state-path "$STATE" --store-root "$STORE" --gpu 0
python3 "$LAUNCHER" status a100-g1-correctness-20261103
python3 "$LAUNCHER" report a100-g1-correctness-20261103 --tail-lines 10000
```

运行可持续较久，使用 `status` 和远端日志查看进度；不得因暂时无日志而重复启动同一 run ID。若遇 OOM、非有限值、输入/manifest 不匹配或任何一致性失败，导出原报告后停止，不改预算、门限、输入或策略来追求通过。首次操作路径笔误保留失败报告，用**新 run ID**修正并在总结中说明。

## 4. 报告与回传

将两个 `results/reports/<run-id>/` 目录和一份 `results/reports/a100-g1-correctness-20261103/G1_SUMMARY.md` 提交到结果分支。总结必须列出：

- 运行前 commit、GPU 是否空闲、snapshot revision、store manifest SHA256、输入文件 SHA256、prompt 与 PPL 实际 token 数及 token 哈希。
- CPU checks、L0、G1 各自 `PASS/FAILED/BLOCKED`；三个策略的 PPL、PPL 差值、每个 prompt 的路由/logit/token 比较结果，首次分叉位置和最大误差。
- OOM/NaN/异常、GPU 运行前后占用；若失败，保存完整堆栈和 `partial_result.json`。
- 明确写“仓库自写文本诊断，非 WikiText-2”；即使全部通过，也只写“同仓库 fp16 策略的短窗输出一致”，不写“已证明完整无损”。

推送后回复：`branch / commit / run IDs / L0 与 G1 状态 / 首次分叉或无分叉 / 一句话异常`。然后停止，等待本地审核与 G2 物理字节/分相位计量工作包。
