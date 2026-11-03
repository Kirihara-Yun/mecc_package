# A100 逐 token 显存追踪汇总（2026-11-03）

本报告只用于**显存来源诊断**，不产出论文/PPT 性能数据，不用于加速或命中率主张。
未调整预算、输入、预取策略或缓存代码；仅启用 `--trace_memory` 只读诊断开关。

## 0. 环境与分支

- 干净 checkout：`/home/qinzy/mecc_a100_memory_trace`
  （`git clone --branch design/a100-memory-audit-20261103`，`git merge-base --is-ancestor 1aa0140 HEAD` 通过，工作区纯净）
- 结果分支：`gpu/a100-memory-trace-20261103`
- 运行前 commit：`1c7197176525d29d981652ab804e6731236e560d`（三次运行 `run.json.git_commit` 均为此值）
- GPU：A100 80GB PCIe，运行前空闲（1 MiB / 0 %，无计算进程）；两次追踪运行后均释放至 1 MiB
- 模型与 store：与上一轮相同（snapshot `eba92302...`；`/data/mecc_store_mixtral`，manifest 校验通过、跳过物化）
- 存储介质：仍为 `unknown`（见上一轮 `a100-storage-audit-20261103/STORAGE_AUDIT.md`）

## 1. L0（新增可选参数回归）

- `run_cpu_checks.py`：**PASS**（含内部 L0 smoke，5 个 active 策略均 `exact(lossless)`）。
- launcher L0 `a100-l0-trace-20261103`（`l0_smoke.json`）：`phase=complete`，`ExecMainStatus=0`，报告已导出。
- 结论：新增 `--trace_memory` 可选参数未破坏逻辑链路。L0 数字不构成性能证据。

## 2. 运行状态

| 项 | run_id | 配置 | 输入×token | 状态 | OOM 位置 |
|---|---|---|---|---|---|
| B1 | `a100-oom-trace-p1t16-20261103` | `diag_a100_50g_p1_t16_trace.json` | 1 × 16 | **FAILED (OOM)** | `run_phase=measure`, `stage=oom_decode`, `step=5` |
| B2 | `a100-oom-trace-p4t2-20261103` | `diag_a100_50g_p4_t2.json` + `--trace-memory` | 4 × 2 | **COMPLETE** | — |

B1 报错：`CUDA out of memory ... 79.25 GiB total, 16.75 MiB free, 78.47 GiB allocated by PyTorch`。
B2 指标（仅诊断）：TTFT 86448.24 ms，TPOT 13938.07 ms，0.020161 tok/s，hit HBM/CPU/SSD = 33.0 / 47.9 / 19.1 %。
注意：`skip_ppl=true` 时 `ppl="exact(lossless)"` 是**占位字符串，PPL 未实测**。

## 3. B1 逐 step 轨迹（单位 GiB，除特别注明）

| phase | stage | step | input_tokens | alloc | reserved | peak | pool | prefetch | nearmiss | nm_cpu | entries |
|---|---|---|---|---|---|---|---|---|---|---|---|
| warmup | before_forward | -1 | 12 | 44.99 | 45.12 | 44.99 | 42.00 | 0.00 | 0.00 | 0.00 | 0 |
| warmup | prefill | 0 | 12 | 46.97 | 77.62 | 47.95 | 42.00 | 0.00 | 1.97 | 0.98 | 9 |
| warmup | decode | 1 | 12 | 53.53 | 62.20 | 53.86 | 42.00 | 0.00 | 8.53 | 1.64 | 31 |
| warmup | decode | 2 | 12 | 58.45 | 70.73 | 58.78 | 42.00 | 0.00 | 13.45 | 2.95 | 50 |
| warmup | decode | 3 | 12 | 64.03 | 74.34 | 64.36 | 42.00 | 0.00 | 18.70 | 2.62 | 65 |
| measure | before_forward | -1 | 12 | 64.03 | 74.34 | 64.36 | 42.00 | 0.00 | 18.70 | 2.62 | 65 |
| measure | prefill | 0 | 12 | 63.05 | 73.03 | 65.34 | 42.00 | 0.00 | 15.42 | 0.98 | 50 |
| measure | decode | 1 | 12 | 66.00 | 72.04 | 66.99 | 42.00 | 0.00 | 19.03 | 1.97 | 64 |
| measure | decode | 2 | 12 | 70.59 | 74.67 | 71.25 | 42.00 | 0.00 | 23.62 | 2.95 | 81 |
| measure | decode | 3 | 12 | 72.89 | 73.36 | 73.22 | 42.00 | 0.00 | 26.58 | 2.62 | 89 |
| measure | decode | 4 | 12 | 76.50 | 77.62 | 76.83 | 42.00 | 0.00 | 31.17 | 1.97 | 101 |
| measure | **oom_decode** | **5** | 12 | **78.47** | 78.61 | 78.47 | 42.00 | 0.00 | **33.47** | 2.30 | **109** |

## 4. B2 逐 prompt 轨迹（节选 measure 阶段 decode 行，单位 GiB）

| prompt | stage | step | input_tokens | alloc | reserved | peak | pool | prefetch | nearmiss | entries |
|---|---|---|---|---|---|---|---|---|---|---|
| p0 | decode | 1 | 12 | 60.09 | 74.34 | 60.42 | 42.00 | 0.00 | 14.44 | 52 |
| p1 | decode | 1 | 12 | 64.69 | 75.33 | 65.67 | 42.00 | 0.00 | 18.38 | 67 |
| p2 | decode | 1 | 12 | 68.30 | 74.01 | 69.28 | 42.00 | 0.00 | 22.64 | 79 |
| p3 | decode | 1 | 11 | 71.25 | 74.34 | 71.91 | 42.00 | 0.00 | 22.64 | 83 |

B2 全程未 OOM：`alloc` 峰值 71.25 GiB、`reserved` 峰值 78.28 GiB、`nearmiss` 峰值 22.64 GiB。

## 5. 观察（只陈述轨迹事实）

1. **`gpu_pool_bytes` 全程恒定 42.00 GiB；`gpu_prefetch_bytes` 全程 0.00 GiB**（`prefetch_entries` 恒 0）。
2. **`gpu_nearmiss_bytes` 单调增长**：B1 从 0 → 1.97 → 8.53 → … → 31.17(step4) → **33.47(OOM step5)**；
   `nearmiss_entries` 同步 0 → 9 → 31 → … → 101 → **109**。B2 增长较慢，峰值 22.64 GiB / 83 项。
3. `cuda_allocated_bytes` 的增长与 `gpu_nearmiss_bytes` 同步（B1：64.03 → 66.00 → 70.59 → 72.89 → 76.50 → 78.47）。
4. warmup 阶段的近失缓冲**未在进入 measure 前释放**：measure 的 `before_forward`（step=-1）直接继承 warmup 末值 18.70 GiB。
5. prefill 会让 `nearmiss` 小幅回落（如 B1 measure prefill 15.42 < warmup 末 18.70），随后每个 decode 步再增长约 2.3–4.6 GiB。

## 6. 关键对照：输入长度 vs 解码步数

- **B1 实际 `input_tokens=12`，B2 实际 `input_tokens=12`（p3 为 11）** —— 两者输入长度几乎相同。
  配置里的 `prompt_len=64` **不是**实际 token 长度（内置 prompt 经 tokenizer 后约 11–12）。
- 因此 B1（OOM）与 B2（完成）的差异**不能归因于输入长度**，只能归因于**解码步数**
  （B1：16 token → 15 个 decode 步；B2：2 token → 每相位仅 1 个 decode 步）。
- 这与上一轮"解码长度驱动、请求数不是决定因素"的推论一致，并进一步指向近失缓冲的逐步累积。

## 7. 候选原因（静态审查，需修复后验证）

- 当前代码 `_nearmiss_buf` 没有显式按步清理；CPU 命中又优先从 `cache.cpu` 取权重。
  若命中的专家权重被留在 GPU 侧近失缓冲且不清除，就会随 decode 步单调累积 —— 与轨迹一致。
- 但本轨迹只能**支持**该候选，不能单独证明根因（未做修复对照实验）。

## 8. 局限

1. 每项只跑一次，无重复测量；不做统计结论。
2. `skip_ppl=true`，PPL 未实测；`ppl` 字段为占位。
3. 存储物理介质 `unknown`，不得表述为 NVMe SSD 性能。
4. `prompt_len=64` 与实际 tokenized 长度（11–12）不一致，是本 harness 的混杂因素。
5. `cuda_peak_allocated_bytes` 为**每步重置后**的峰值，不是全程峰值。
6. 本轮数字均为诊断用，不得进入论文/PPT。

## 9. 建议的下一步（本地开发）

1. 在 decode 步间显式清理/上限 `_nearmiss_buf`（或改为可驱逐的 LRU），并复测 B1 是否仍 OOM。
2. 为 `gpu_pool/prefetch/nearmiss` 增加显式字节上限与驱逐日志，使其可被正式指标采集。
3. 修复后重跑 L0 → preflight → 4×16 复现，验证正确性（PPL）与显存稳定性，再谈正式主表。
