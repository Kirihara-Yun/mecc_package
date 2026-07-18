# 术语表 —— MECC

> 给 AI 与新读者快速对齐概念。按主题分组。

## 核心概念

| 术语 | 含义 |
|------|------|
| **MECC** | MoE Expert Cache Compiler。本项目：三级无损 expert 缓存编译器。 |
| **MoE** | Mixture-of-Experts。每层有多个 expert（FFN），gate 每个 token 只激活 top-k 个。 |
| **Expert** | MoE 层里的一个独立 FFN 子网络（本项目用 SwiGLU：gate/up/down 三权重 w1/w3/w2）。 |
| **三级缓存** | HBM（GPU 显存）→ CPU pinned 内存 → SSD 冷存，三层 expert 放置层级。 |
| **无损 / lossless** | 全程 fp16，expert 输出与原模型逐位一致，PPL 不退化（相对量化方案的卖点）。 |

## 适用性（最重要）

| 术语 | 含义 |
|------|------|
| **有效边界** | MECC 仅在「模型 expert 总量 > 可用 CPU 内存」（被迫落 SSD）时有价值。见 `APPLICABILITY.md`。 |
| **主场景** | 能打满 CPU 内存、必须落 SSD 的大 MoE（如 Mixtral-8x7B ~90GB）。 |
| **对照场景** | CPU 能装下、几乎不落 SSD 的模型（如 DeepSeek-V2-Lite），仅展示算法上界，非主战场。 |

## 缓存与放置

| 术语 | 含义 |
|------|------|
| **K_H** | 每层常驻 HBM 的 expert 数（HBM 预算决定）。 |
| **K_C** | 每层常驻 CPU pinned 的 expert 数（CPU 预算决定）；其余落 SSD。 |
| **α (alpha)** | profiled 路由热度的 Zipf 偏斜系数；越大越偏斜（少数 expert 极热），tiering 收益越高。Mixtral 实测偏均匀，默认 1.0。 |
| **静态放置** | 编译期根据 α 一次性决定每层 expert 的初始层级。 |
| **动态 LRU** | 运行期按最近使用情况在 HBM/CPU 间升降级 expert。 |
| **命中率 hit_pct** | 一次 expert 访问命中在 hbm/cpu/ssd/cpu_compute 各层的占比；SSD 命中越低越好。 |
| **冷读 / cold SSD** | 绕过 page cache 强制读 NVMe，反映真实 offloading 延迟（论文用 `--cold_ssd`）。 |

## 四策略

| 术语 | 含义 |
|------|------|
| **ours** | 本文方法：HBM+CPU 联合动态 LRU，其余 SSD。 |
| **swapmoe / swapmoe_fp16** | 历史策略 id / 推荐显示名：SwapMoE-style 静态 CPU 策略的同预算 fp16 三层适配；不是量化实现。 |
| **swapmoe_quantized** | 预留的独立有损系统 baseline id；当前无可追溯实现，保持 inactive。 |
| **fiddler** | miss 时在 CPU 上算 expert（搬激活而非权重）。 |
| **naive** | 全 offload 下界：每次流式搬权重。 |

## 性能指标

| 术语 | 含义 |
|------|------|
| **TTFT** | Time To First Token，prefill 首 token 延迟（ms）。 |
| **TPOT / ITL** | Time Per Output Token，decode 每 token 延迟（ms）。 |
| **tokens/s** | 端到端吞吐。 |
| **PPL** | Perplexity（WikiText-2 困惑度），衡量精度；无损方法应与原模型一致。 |
| **speedup_vs** | OURS 相对某 baseline 的端到端吞吐加速比。 |

## 工程

| 术语 | 含义 |
|------|------|
| **AsyncSwapEngine** | 异步 PCIe 搬运引擎：专用 copy_stream + 批量预取 + buffer pool，重叠搬运与计算。 |
| **批量预取** | 把同层将用到的 CPU expert 一次性并行搬上 GPU，饱和 PCIe 带宽。 |
| **pinned memory** | 锁页内存，使 H2D 拷贝可异步、更快。 |
| **连续 storage** | 把 w1/w3/w2 拼成一块连续 UntypedStorage，便于整体快速搬运（沿用 mixtral-offloading 思路）。 |
| **smoke test** | 纯 CPU 微型随机 MoE 全链路自检；验证逻辑通，**不体现加速**（随机 gate≈均匀）。 |
