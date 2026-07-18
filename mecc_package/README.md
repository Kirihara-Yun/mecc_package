# MECC — MoE Expert Cache Compiler (DAC)

三级 (HBM→CPU→SSD) 无损 Expert 缓存编译器，首次量化 "Expert 权重 vs KV Cache 争抢 HBM" 的 trade-off。

> **适用边界（务必先读）**：MECC 只在「连 CPU 内存都装不下整个模型」时有效（`expert 总量 > CPU 内存`，被迫落 SSD）。
> 详见 [`../docs/APPLICABILITY.md`](../docs/APPLICABILITY.md)。AI 协作请先读 [`../AGENTS.md`](../AGENTS.md)。

## 核心结果

### 主场景：Mixtral-8x7B（~90GB，连 CPU 都装不下，被迫落 SSD）
来源 [`results/raw/mixtral_real.json`](./results/raw/mixtral_real.json)（A100 80GB, cold SSD；平台/时间见 JSON 顶层 `platform`+`run_time` 字段，见 PROVENANCE M5）

| 指标 | OURS | SwapMoE |
|------|------|---------|
| 加速比 | **1.33×** | 1.0 |
| PPL（精度） | **24.57（fp16）** | 36.12（JSON 对照值；baseline 身份待核） |
| SSD 命中率 | **17.6%** | 34.5% |

> 当前 verified 结论是 fp16 OURS 的综合吞吐优势与 SSD 命中下降。36.12 对照 PPL
> 的“2-bit/SwapMoE”身份与当前 fp16 harness 不一致，已登记 PROVENANCE X6，核验前
> 不作为组合质量 claim。这仍是 MECC 真正成立的主场景。

### 对照场景：DeepSeek-V2-Lite（A100 80GB, α=0.73；CPU 装得下，几乎不落 SSD）

| 优化层级 | Ours (tok/s) | SwapMoE | Fiddler | Ours/Swap |
|----------|-------------|---------|---------|-----------|
| 无优化 | 2.38 | 0.92 | 0.98 | **2.59×** |
| +AMP | 2.18 | 2.50 | 0.97 | 0.87× |
| **+批量预取** | **5.58** | **5.06** | — | **1.10×** |

> ⚠️ 此组仅展示**算法层面的结构性上界**，因 DeepSeek-V2-Lite 不会打满 CPU、几乎不落 SSD，
> **不作为 MECC 主战场的证据**。完整 4-strategy 数据见 [results/](./results/)。

## 项目结构

```
mecc_package/
├── README.md                       # 本文件
├── STRATEGY.md                     # 策略全量报告（四策略 / 实验结论 / 调参指南）
├── tuning_log.md                   # 调参与优化历程记录
├── requirements.txt
├── run_all.sh                      # 一键 demo (compiler → cache sim → runtime → profiling)
│
├── compiler.py                     # MECC 编译器（库形式，被 e2e / runtime_spec 引用）
├── compile.py                      # MECC 编译器（standalone CLI，全功能版）
├── runtime_spec.py                 # 运行时 API 规范 + 伪代码（CPU 可跑）
│
├── mecc_framework/                 # 核心框架（模块化实现）
│   ├── base/                       # config / expert / store
│   ├── cache/                      # engine / swap（AsyncSwapEngine）
│   ├── layers/                     # moe_forward
│   ├── models/                     # deepseek / mixtral / base 适配
│   └── benchmark/                  # runner / smoke_test
│
├── e2e/                            # 正式端到端框架（扁平 import，依赖根级 compiler.py）
│   ├── run_e2e.py                  # 主 harness
│   ├── run_5090.sh                 # 一键脚本
│   ├── tiered_engine.py            # 三级缓存引擎
│   ├── deepseek_tiered.py          # DeepSeek 适配器
│   ├── mixtral_tiered.py           # Mixtral 适配器
│   ├── compile_config.py           # 编译器接入（sys.path → 父目录 compiler.py）
│   └── policy_plugin.py            # 策略插件
│
├── scripts/                        # 离线脚本（自检 / profiling / 延迟测量 / 缓存模拟）
│   ├── check_env.py                # 环境 + 适用性 + import 链自检（零依赖）
│   ├── profile_deepseek.py         # DeepSeek α profiling
│   ├── profile_real_moe.py         # Switch α profiling
│   ├── profile_gpu.py              # GPU profiling
│   ├── measure_tiers.py            # 三级延迟真实测量
│   ├── tiered_cache.py             # 缓存解析模拟器
│   ├── real_tiered_cache.py        # 真机缓存（串行）
│   └── concurrent_tiered_cache.py  # 真机缓存（并发，依赖 real_tiered_cache）
│
├── results/                        # 实验数据归档
│   ├── README.md                   # 主表实验文档
│   ├── main_table_*.json / e2e_*.log   # 正式主表 ablation 结果
│   ├── real_e2e_*.json / smoke_test.json
│   ├── raw/                        # 中间 / 子系统级实验产物（JSON）
│   └── logs/                       # 运行日志
│
├── archive/                        # 历史文档 & Apple UMA 早期数据
├── paper/                          # 论文 (mecc_paper.tex)
└── third_party/                    # 第三方参考实现
    └── mixtral_offloading/         # mixtral-offloading 上游源码
```

## 快速开始

```bash
# 0. 一键 demo (CPU)
bash run_all.sh

# 1. α profiling
python3 scripts/profile_deepseek.py --out results/raw/real_alpha_deepseek.json

# 2. 端到端 (无优化 baseline)
python3 e2e/run_e2e.py \
  --model deepseek-ai/DeepSeek-V2-Lite --model_type deepseek \
  --state_path /data/models/deepseek-ai/DeepSeek-V2-Lite \
  --store_root /tmp/mecc_store --hbm_budget 8 --cpu_budget 30 --alpha 0.73

# 3. 端到端 (全优化 + 批量预取)
python3 e2e/run_e2e.py \
  --model deepseek-ai/DeepSeek-V2-Lite --model_type deepseek \
  --state_path /data/models/deepseek-ai/DeepSeek-V2-Lite \
  --store_root /tmp/mecc_store --hbm_budget 8 --cpu_budget 30 --alpha 0.73 \
  --baseline_opts --policies "ours,swapmoe"
```

## Pipeline

```
Profile(估 α) → Optimize(Theorem 4) → Allocate(tier map) → Validate(端到端)
```
