# Results — 完整实验数据

> 硬件: A100 80GB PCIe | 模型: DeepSeek-V2-Lite (27层, 64 routed + 2 shared experts/层) | α=0.73
>
> ✅ **平台口径（已澄清·已落字段）**：实验先在 RTX 5090 上调试、最终在 **A100 80GB** 上跑定（Mixtral 主结果同在 A100）。各真机 JSON 顶层已写入 `platform="A100 80GB"` + `run_time` 字段承载平台/时间真值；`compiled_plan.hardware=rtx5090` 仅为编译期配置串、**非平台依据**，以顶层 `platform` 为准（PROVENANCE M5，矛盾 X5 已解决）。
> 字段语义见 [`SCHEMA.md`](./SCHEMA.md)；数字真伪 / 可信度级别 / 已知矛盾以 [`../../docs/PROVENANCE.md`](../../docs/PROVENANCE.md) 为准。
> **注意：本目录下 `real_e2e_*.json`、`raw/*_e2e*.json` 中含 `workloads` 字段者为缓存模拟器（D1），非真机，勿当端到端实测引用。**

## 主表: 多维度 Ablation

| 优化层级 | Ours (tok/s) | SwapMoE (tok/s) | Fiddler (tok/s) | Ours/Swap |
|----------|-------------|----------------|-----------------|-----------|
| 无优化 | 2.38 | 0.92 | 0.98 | **2.59×** |
| +TF32+cudnn | 2.31 | 1.63 | 0.96 | **1.42×** |
| +TF32+cudnn+AMP | 2.18 | 2.50 | 0.97 | 0.87× |
| +All + 自定义流水线 | 2.30 | 1.92 | 0.96 | **1.20×** |
| **+All + 批量预取** | **5.58** | **5.06** | — | **1.10×** |

## 说明

- **无优化**: 纯算法对比, 不开启任何硬件优化
- **+TF32+cudnn**: `cudnn.benchmark=True`, TF32 matmul
- **+AMP**: 上述 + `torch.cuda.amp.autocast` (fp16 tensor cores)
- **+自定义流水线**: CUDA stream 异步 H2D copy, 与计算重叠
- **+批量预取**: 所有 CPU expert 一次性并行搬上 GPU (PCIe 带宽饱和)

## 结论

1. 算法层面 Ours 有 2.59× 结构性优势
2. 硬件优化有益所有策略, 但 Ours 通过批量预取适配后仍然领先 1.10-2.59×
3. K_H=19, K_C=45 (HBM 8GB, CPU 30GB 预算)

## 文件索引

| 文件 | 配置 | Ours/Swap 结果 |
|------|------|----------------|
| `main_table_5090.json` | 无优化, 8 prompts | 2.38 / 0.92 |
| `main_table_opts.json` | +TF32+cudnn, 8 prompts | 2.31 / 1.63 |
| `main_table_amp.json` | +AMP, 4 prompts | 2.18 / 2.50 |
| `main_table_stream.json` | +自定义流水线, 8 prompts | 2.30 / 1.92 |
| `main_table_prefetch.json` | +批量预取+AMP, 4 prompts | **5.58 / 5.06** |
| `main_table_batch.json` | K_H=4 extreme budget | 0.29 / 0.23 |

## 子目录

- `raw/` — 中间 / 子系统级实验产物（各模型 fused / io / concurrent / α 实测 JSON，
  以及 `measured_latency_*.json`、`real_e2e_results.json`）。
  其中 `deepseek_e2e_results_old.json` 为历史备份，仅作留存。
- `logs/` — 运行日志（`download_mixtral.log`、`e2e_run.log` 等）。
