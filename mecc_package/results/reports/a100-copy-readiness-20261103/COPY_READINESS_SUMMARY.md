# 拷贝就绪屏障与短窗 PPL 诊断汇总（2026-11-03）

本报告只验证"使用前就绪"补丁与输出质量的**初步一致性**，不产出论文/PPT 性能数据；
不比较速度/命中率；相同 PPL **不等于**完整无损证明。

## 0. 环境与分支

- 干净 checkout：`/home/qinzy/mecc_a100_copy_readiness`
  （`git clone --branch design/a100-copy-readiness-20261103`，`git merge-base --is-ancestor 1aa0140 HEAD` 通过，工作区纯净）
- 结果分支：`gpu/a100-copy-readiness-20261103`
- 运行前 commit：`3a53c0b5c2476a632308db014a4a06a0523214b0`（三次运行 `run.json.git_commit` 全部一致）
- 模型：`.../Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61`
- store：`/data/mecc_store_mixtral`（manifest 校验通过、跳过物化）
- GPU：A100 80GB PCIe；运行前空闲独占（1 MiB / 0 %，无计算进程），各次运行后均释放
- 存储物理介质：仍为 `unknown`（沿用 `a100-storage-audit-20261103/STORAGE_AUDIT.md`）

## 1. 本地改动摘要（只读启用，未改策略/预算/精度/输入/revision）

1. `tiered_engine.py`：`load_experts()` 向计算方交付 CUDA 权重前 `sync_copy()`，并对 `w1/w3/w2`
   `record_stream(compute_stream)` —— 关闭"使用前就绪"风险（PROVENANCE X8 的静态风险项）。
2. `run_e2e.py`：新增 `[inputs]` 日志，打印 `prompts_sha256`、`ppl_text_sha256`、`ppl_input_tokens`。
3. `experiment_launcher.py`：新增 `ppl_tokens` 配置键与 `--ppl-tokens` CLI。
4. 预测近失预取沿用上一轮结论，保持关闭。

## 2. 门禁与运行状态

| 项 | run_id | 状态 | 说明 |
|---|---|---|---|
| CPU 回归 | `run_cpu_checks.py` | **PASS** | 5 个 active 策略均 `exact(lossless)`；L0 逻辑验证 |
| L0 | `a100-l0-copy-ready-20261103` | **COMPLETE** | `ExecMainStatus=0`，报告已导出 |
| PPL128 | `a100-copy-ready-ppl128-20261103` | **COMPLETE** | `ours,swapmoe`，1 输入、2 token、`ppl_tokens=128`、无 `--skip_ppl` |
| 4×16 稳定性 | `a100-copy-ready-p4t16-20261103` | **COMPLETE** | `ours`，4 输入、16 token、`--trace-memory`、`skip_ppl=true` |

三次运行均无 OOM、无 NaN、无异常堆栈（无失败项）。

## 3. PPL 诊断详情（短窗，初筛）

- **输入来源：内置文本诊断**。`load_prompts(use_wikitext=True)` 尝试下载 WikiText-2 时
  连续 `Connection reset by peer` 失败（`Couldn't reach 'wikitext' on the Hub`），
  自动回退到内置多领域 prompt/text。**因此本 PPL 不是 WikiText-2 质量实验。**
- `[inputs] prompts_sha256 = 2f36def157dd133c64ea7cf19b358aa055b0b9588c9b4485774826bd05e17581`
- `[inputs] ppl_text_sha256 = c425eba97673c93ec2f91c29c7fe4169588bd54b9f0a001161a199bc8585ae81`
- `[inputs] ppl_input_tokens = 77`（配置上限 128，内置文本实际只 tokenize 出 77 个 token）

| 策略 | TTFT(ms) | TPOT(ms) | **PPL** |
|---|---|---|---|
| ours | 90959.12 | 10428.92 | **24.569** |
| swapmoe | 104809.31 | 16332.45 | **24.569** |

- **PPL 差值 = 0.000**（两策略在同一 77-token 内置文本上完全一致）。
- 参考：历史 fp16 Mixtral PPL 记录为 24.57（`PROVENANCE`），本次诊断值同为 24.569 量级；
  但输入文本不同且窗口仅 77 token，**不能据此宣称复现历史质量结论**。
- `cold_ssd=true`（`config` 字段），近失预取关闭。

## 4. 4×16 稳定性检查（新屏障是否引入异常）

- run `a100-copy-ready-p4t16-20261103`：`phase=complete`，`ExecMainStatus=0`
- `ours`：TTFT 96098.22 ms、TPOT 7222.17 ms（仅诊断，**不比较速度**）
- **无 OOM、无 NaN、无异常堆栈**
- `skip_ppl=true`，结果中 `ppl="exact(lossless)"` 为占位字符串，**不算质量结果**
- 实际 `input_tokens`：各 prompt 为 12 / 12 / 12 / 11（`prompt_len=64` 非真实长度）

## 5. 显存范围（MEMTRACE，单位 GiB）

| 运行 | 行数 | `cuda_allocated` | `cuda_reserved` | `cuda_peak` | `gpu_pool_bytes` | `gpu_prefetch_bytes` | `gpu_nearmiss_bytes` |
|---|---|---|---|---|---|---|---|
| PPL128（ours） | 6 | 44.99 – 45.00 | 45.12 – 76.64 | 44.99 – 45.98 | 42.00 恒定 | 0.00 恒定 | **0.00**（entries 0） |
| 4×16（ours） | 88 | 44.99 – 45.00 | 45.12 – 76.64 | 44.99 – 45.98 | 42.00 恒定 | 0.00 恒定 | **0.00**（entries 0） |

- 与上一轮（近失预取停用）一致：近失缓冲保持 0，`allocated` 恒定约 45 GiB，未出现逐步增长。
- `cuda_reserved` 在 prefill 时升至 76.64 GiB 后保持恒定（PyTorch 缓存分配器），
  虽接近 79.25 GiB 物理上限但未继续增长，也未触发 OOM。

## 6. 判读与局限

1. 本轮只关闭"使用前就绪"的静态风险，并给出**一次相同 PPL 的初筛**；
   不能替代逐层路由、logits、token 的正式一致性证明，也不构成完整无损证明。
2. PPL 输入为**内置文本**（77 token，非 WikiText-2），且仅单次运行；不同输入/窗口下不得外推。
3. X7（物理容量/公平性）、X9（分相位计量）仍未关闭；存储介质仍 `unknown`。
4. 4×16 行的 `skip_ppl=true` 占位 `ppl` 不作为质量证据；本轮不做速度/命中率结论。
5. 每项仅一次运行，无重复测量。

## 7. 结论（本轮范围）

- 拷贝就绪屏障加入后：L0/PPL128/4×16 三项**全部完成**，无 OOM/NaN/异常堆栈。
- 在 77-token 内置文本上，`ours` 与 `swapmoe` 的短窗 PPL **完全相同（24.569）**，
  未观察到明显输出分叉；但这只是初筛。
- 近失缓冲仍为 0，显存恒定约 45 GiB，上一轮修复效果在新屏障下保持。
