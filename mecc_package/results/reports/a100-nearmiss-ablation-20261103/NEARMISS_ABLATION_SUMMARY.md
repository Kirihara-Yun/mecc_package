# 停用近失预测预取后的单变量复测汇总（2026-11-03）

本报告只检验 OOM 的候选原因，不产出论文/PPT 性能数据；**不比较速度或命中率**，不把 `skip_ppl` 的占位字符串当质量结果。

## 0. 环境与分支

- 干净 checkout：`/home/qinzy/mecc_a100_nearmiss_ablation`
  （`git clone --branch design/a100-nearmiss-guard-20261103`，`git merge-base --is-ancestor 1aa0140 HEAD` 通过，工作区纯净）
- 结果分支：`gpu/a100-nearmiss-ablation-20261103`
- 运行前 commit：`8a092f2e1cf03da318e53194f079cb796ba1dc67`（两次有效运行 `run.json.git_commit` 均为此值）
- 模型 / store：`.../snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61`、`/data/mecc_store_mixtral`（manifest 校验通过、跳过物化）
- GPU：A100 80GB PCIe；运行前空闲（1 MiB / 0 %，无计算进程），两次运行后均释放
- 存储物理介质：仍为 `unknown`（沿用 `a100-storage-audit-20261103/STORAGE_AUDIT.md`）

## 1. 单变量改动

相对上一轮运行前提交 `1c71971`，`design/a100-nearmiss-guard-20261103` 只删除了
`mecc_package/e2e/mixtral_tiered.py` 中对 `self.experts.prefetch_near_miss(...)` 的调用（7 行）。
三级缓存、预算、模型、输入、`batch_prefetch`、追踪代码均未改。

## 2. 门禁与运行状态

| 项 | run_id | 配置 | 输入×token | 状态 | 备注 |
|---|---|---|---|---|---|
| L0 | `a100-l0-nearmiss-20261103` | `l0_smoke.json` | — | **COMPLETE** | `run_cpu_checks.py` PASS；L0 只验证逻辑 |
| B1 | `a100-nearmiss-b1-p1t16-20261103` | `diag_a100_50g_p1_t16_trace.json` | 1 × 16 | **COMPLETE** | 前轮同配置在 decode step 5 OOM |
| B3 | `a100-nearmiss-b3-p4t16-20261103-retry1` | `diag_a100_50g_p4_t16.json` + `--trace-memory` | 4 × 16 | **COMPLETE** | 前轮同配置 OOM 78.47 GiB |

> 操作员失误记录：首次 B3 启动时我把 `--state-path` 误写为 `...Mixtral-8x7B-Instruct-20261103`（漏 `-v0.1`），
> 该次 run（`a100-nearmiss-b3-p4t16-20261103`）以 `HFValidationError` 失败，**模型未加载、无 GPU 占用、无 MEMTRACE**，
> 报告已原样导出，**不参与对照**；随后用正确路径以 `...-retry1` 重跑。

结果指标（仅诊断，不作性能结论）：B1 TTFT 88204.91 ms / TPOT 6820.61 ms；B3 TTFT 73589.23 ms / TPOT 6851.08 ms。
`skip_ppl=true`，`ppl="exact(lossless)"` 为占位串。

## 3. 与前轮（`1c71971`，未停用）的对照

| 指标 | 前轮 B1（1×16，未停用） | 本轮 B1（1×16，已停用） | 本轮 B3（4×16，已停用） |
|---|---|---|---|
| 结果 | **FAILED (OOM)** @ measure/oom_decode step 5 | **COMPLETE**（15 步） | **COMPLETE**（4×15 步） |
| `cuda_allocated` | 44.99 → **78.47** GiB（单调增） | **45.00 恒定** | **44.99–45.00 恒定** |
| `cuda_reserved` | 45.12 → 78.61 GiB | 45.12 → 74.67 GiB（达峰后恒定） | 峰值 76.64 GiB（恒定） |
| `cuda_peak_allocated` | 44.99 → 78.47 GiB | 45.98 GiB | 45.98 GiB |
| `gpu_pool_bytes` | 42.00 恒定 | 42.00 恒定 | 42.00 恒定 |
| `gpu_prefetch_bytes` | 0.00 恒定 | 0.00 恒定 | 0.00 恒定 |
| `gpu_nearmiss_bytes` | 0 → **33.47** GiB | **0.00 全程** | **0.00 全程** |
| `nearmiss_entries` | 0 → **109** | **0 全程** | **0 全程** |

## 4. B1 逐步轨迹（已停用，单位 GiB）

| phase | stage | step | input_tokens | alloc | reserved | peak | pool | prefetch | nearmiss | entries |
|---|---|---|---|---|---|---|---|---|---|---|
| warmup | before_forward | -1 | 12 | 44.99 | 45.12 | 44.99 | 42.00 | 0.00 | 0.00 | 0 |
| warmup | prefill | 0 | 12 | 45.00 | 74.67 | 45.98 | 42.00 | 0.00 | 0.00 | 0 |
| warmup | decode | 1 | 12 | 45.00 | 51.04 | 45.66 | 42.00 | 0.00 | 0.00 | 0 |
| warmup | decode | 2 | 12 | 45.00 | 55.97 | 45.66 | 42.00 | 0.00 | 0.00 | 0 |
| warmup | decode | 3 | 12 | 45.00 | 57.28 | 45.66 | 42.00 | 0.00 | 0.00 | 0 |
| measure | before_forward | -1 | 12 | 45.00 | 57.28 | 45.66 | 42.00 | 0.00 | 0.00 | 0 |
| measure | prefill | 0 | 12 | 45.00 | 74.67 | 45.98 | 42.00 | 0.00 | 0.00 | 0 |
| measure | decode | 1–15 | 12 | 45.00 | 74.67 | 45.66 | 42.00 | 0.00 | 0.00 | 0 |

（measure 的 decode 1–15 每一步数值完全一致；前轮在第 5 步即 OOM。）

## 5. B3 分 prompt 统计（已停用，单位 GiB）

| prompt | input_tokens | MEMTRACE 行数 | alloc min..max | reserved max | peak max | nearmiss max | entries max |
|---|---|---|---|---|---|---|---|
| p0 | 12 | 22 | 44.99..45.00 | 74.67 | 45.98 | 0.00 | 0 |
| p1 | 12 | 22 | 45.00..45.00 | 76.64 | 45.98 | 0.00 | 0 |
| p2 | 12 | 22 | 45.00..45.00 | 76.64 | 45.98 | 0.00 | 0 |
| p3 | 11 | 22 | 45.00..45.00 | 76.64 | 45.98 | 0.00 | 0 |

## 6. 实际输入长度（防止误判）

- 本轮 B1 实际 `input_tokens=12`；B3 各 prompt 为 12 / 12 / 12 / 11。
- 配置 `prompt_len=64` **不是**实际 token 长度。B1 与 B3 的输入长度基本一致，
  因此二者差异来自**请求数**（1 vs 4），而与上一轮"解码步数驱动"的结论可并列使用。

## 7. 观察（只陈述事实）

1. 停用近失预测预取调用后，`gpu_nearmiss_bytes` 与 `nearmiss_entries` **全程为 0**。
2. `cuda_allocated` 不再随 decode 步增长（45.00 GiB 恒定），前轮同配置的 78.47 GiB OOM **未再现**。
3. `gpu_pool_bytes` 仍恒定 42.00 GiB、`gpu_prefetch_bytes` 仍恒 0，说明池与批量预取未被本次改动影响。
4. `cuda_reserved` 在 prefill 时升到 74.67–76.64 GiB 后保持恒定（PyTorch 缓存分配器行为），
   虽接近 79.25 GiB 上限但未继续增长；`allocated` 仅 45 GiB。该余量需在后续正式配置中复核。

## 8. 局限

1. 每项只跑一次；不构成统计或性能结论，不做速度/命中率比较。
2. `skip_ppl=true`，PPL 未实测。
3. 存储物理介质 `unknown`。
4. `cuda_peak_allocated_bytes` 为每步重置后的峰值，非全程峰值。
5. 本轮只证明"停用该单变量消除了缓冲增长与 OOM"；**正确性（PPL/输出一致性）与物理字节公平性仍待本地审计**。
6. 首次 B3 因操作员路径笔误失败（`HFValidationError`，无模型加载），已单列记录，未纳入对照。

## 9. 结论（单变量）

停用 Mixtral 前向的 `prefetch_near_miss()` 调用后，同 50/40 GB 冻结配置下：
- 近失缓冲保持 0，`cuda_allocated` 恒定约 45 GiB；
- 1×16 与 4×16 均**完成**，前轮 OOM 未再现。

这支持"近失缓冲逐步累积是 OOM 的直接来源"这一单变量判断；根因是否仅为该调用、以及停用后对命中/延迟的代价，仍待本地在修复正确性与物理预算计量后另行审计。
