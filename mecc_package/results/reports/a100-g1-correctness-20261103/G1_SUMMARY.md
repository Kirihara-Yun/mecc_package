# G1 正确性诊断汇总（2026-11-03）

只检验**同仓库 fp16 缓存策略**的短窗输出一致性；不产出论文/PPT 速度、命中率、质量 benchmark 结果。
即使通过，也只写"同仓库 fp16 策略的短窗输出一致"，不写"已证明完整无损"。

## 0. 环境与分支

- 干净 checkout：`/home/qinzy/mecc_a100_g1`（`git clone --branch design/a100-g1-correctness-20261103`，`1aa0140` 祖先校验通过，工作区纯净）
- 结果分支：`gpu/a100-g1-correctness-20261103`
- 运行前 commit：`40ecb879845df8631dfa378d98bd7de2a4b463ed`
- GPU：A100 80GB PCIe；运行前空闲（1 MiB / 0 %，无计算进程）；被 oomd 杀掉后 GPU 已释放回 1 MiB
- 模型 snapshot：`.../snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61`（19 分片）
- store：`/data/mecc_store_mixtral`，`manifest.json` SHA256=`c943c4173e1c6dbac73fe12a8d5f03d51e52acbffabb476e2e3a1cd994b71255`，256 个 expert `.bin`；本轮只读，未重新物化
- 存储物理介质：仍为 `unknown`

## 1. 门禁

| 项 | 结果 |
|---|---|
| CPU 回归 `run_cpu_checks.py` | **PASS**（5 策略均 `exact(lossless)`） |
| L0 `a100-g1-l0-20261103` | **COMPLETE**（`ExecMainStatus=0`，报告已导出） |
| G1 `a100-g1-correctness-20261103` | **PARTIAL**（详见下） |

## 2. G1 输入（冻结 fixture）

- 文件：`mecc_package/e2e/fixtures/correctness_diagnostic_v1.json`
  - `file_sha256 = 913c816407bfd5fa9aacb8476f34648238dd749ff384c1bd96876f8fef6fa3f6`
  - `prompts_sha256 = 97b17e92cf83e6f8b47d6a5ee1a13fa44ca48e4e1d62cbb85ff063a7aca17eda`
  - `ppl_text_sha256 = f1fb591f14d55de30d72c69db05b8e3bc22346fa60c838fb04561812cbcc5fc5`
  - `prompt_input_tokens = [21, 22]`
  - `prompt_token_sha256 = 5547e1b9…1cd`、`59146108…3aa`
  - `ppl_input_tokens = 128`，`ppl_token_sha256 = fadd0d38…538`
- **来源为仓库自写诊断文本，非 WikiText-2**，工具未访问网络。

## 3. G1 结果（`partial_result.json`，`mode=diagnostic_correctness`）

| 策略 | 状态 | PPL | PPL 差(vs naive) |
|---|---|---|---|
| naive | **passed=true**（参考） | 20.443230408996836 | 0.0 |
| ours | **passed=true** | 20.443230408996836 | **0.0** |
| swapmoe | **未完成（被 systemd-oomd 杀掉）** | — | — |

### naive vs ours（两个 prompt，各 3 个贪心 token）

- prompt 0：`route_equal=true`、`logits_allclose=true`、`max_logit_abs_error=0.0`、`max_gate_abs_error=0.0`、`tokens_equal=true`、`first_*_mismatch=null`；greedy_tokens `[272, 3332, 263]`
- prompt 1：同上全等；greedy_tokens `[272, 5116, 1580]`
- **首次分叉：无**（naive 与 ours 逐层路由 ID 完全一致、logits 最大绝对误差 0.0、token 完全一致、PPL 完全一致）

## 4. 异常与失败（必须记录）

- swapmoe 在 expert 装载阶段被 **systemd-oomd** 终止：
  - `systemd-oomd killed 196 process(es) in this unit.`
  - `Main process exited, code=killed, status=9/KILL`，`Failed with result 'signal'`
  - 时间 `2026-11-03 17:05:47`，此时 naive、ours 已 `passed` 并写入 `partial_result.json`
- 这是**系统级内存压力 OOM（systemd-oomd）**，不是之前已修复的 CUDA 显存 OOM。
  三种策略顺序装载时，CPU 侧 pinned/镜像/临时缓冲可能跨策略累积，触发 cgroup 内存压力。
  这正是 G2"物理内存与分阶段计量"要处理的范畴，本轮不自行改预算/策略来重试。
- 无 `result.json`（进程未走到写终态即被 kill）；`status.json` 停留在 `running_policy swapmoe`；
  `partial_result.json` 完整保存 naive/ours 结果，报告已原样导出。

## 5. 判读（严格限定）

- 本轮仅证明：**同仓库 fp16 策略下，`naive` 与 `ours` 在冻结的 2 个短 prompt（21/22 token）+ 128-token 离线诊断文本上的短窗输出一致**（路由、logits、token、PPL 全等）。
- 这**不能**证明与独立 HuggingFace 全驻留实现完全等价，也不构成完整无损证明。
- swapmoe 因系统 OOM 未评估；缺失项如实保留，不补造。

## 6. 下一步（供本地）

- G2：为三策略顺序运行增加 CPU 侧 pinned/pageable/镜像/staging 去重记账与分阶段释放，定位并消除 systemd-oomd 触发点；
- 在消除该系统 OOM 后，重跑 swapmoe（新 run ID），补全三策略正确性对照。
