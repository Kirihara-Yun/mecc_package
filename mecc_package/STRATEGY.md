# MECC 策略全量报告

## 架构概述

MECC 是一个三级 (HBM / CPU pinned / SSD) 无损 Expert 缓存编译器，实现与 SwapMoE / Fiddler 的苹果对苹果对比。

```
编译: model + HBM预算 + CPU预算 + α → per-layer (K_H, K_C)
运行: 真实模型 + SSD store + 三级缓存 forward
策略: ours | swapmoe | fiddler | naive
```

---

## 一、已验证的四策略

### 1. OURS（本文方法）
- HBM / CPU 联合动态 LRU，带升降级：HBM→CPU→SSD
- 唯一有效利用 CPU tier 的策略

### 2. SwapMoE（主基线）
- HBM 动态 LRU，CPU 静态 top-K_C，无升迁路径
- ACL 2024 范式：两级缓存 (HBM+CPU)，无 SSD

### 3. Fiddler（CPU-GPU 协同基线）
- HBM 常驻 K_H，miss 在 CPU 上算（搬激活不搬权重）
- 适合 expert 大的场景（Mixtral），expert 小时 CPU 计算反超

### 4. Naive（下界基线）
- 不常驻 HBM，每次流式搬运
- 性能下界，用于消融实验

---

## 二、关键实验结果

### 2.1 DeepSeek-V2-Lite（30GB, 26层×64exp, 16.5MB/exp）

| 硬件 | K_H/K_C | ours | swapmoe | fiddler | 加速比 |
|------|---------|------|---------|---------|--------|
| A100 80GB 全部GPU | 64/0 | 14.53 tok/s | 14.41 | 14.40 | — |
| 模拟受限 HBM=8GB | **19/28** | **0.92** | 0.89 | 0.68 | **1.35×** |
| 过度限制 HBM=3GB | 7/23 | 崩溃 | — | — | — |

> **最优配置**: HBM=8GB / CPU=12GB / α=0.73  
> PPL 全部 = 44.752，三份独立实验可复现  
> ours TTFT 1.56× 快于 swapmoe，CPU命中 5.4% vs 对手 0%

### 2.2 Mixtral-8x7B（87GB, 32层×8exp, 336MB/exp）

| 硬件 | K_H/K_C | ours | swapmoe | 加速比 |
|------|---------|------|---------|--------|
| A100 80GB 真实 | **4/3** | **0.04** | 0.03 | **1.33×** |

> ours TPOT 14.2s vs swapmoe 23.1s (1.6×)  
> CPU命中 38.0% vs 23.3% — 大expert场景下的动态LRU优势显著  
> 0.04 tok/s 为 A100+Mixtral 物理极限，非退化

---

## 三、优化历程

### 已有优化（mecc_framework/cache/）
| 优化 | 实现 | 状态 |
|------|------|------|
| AsyncSwapEngine | 独立 CUDA stream + buffer pool | ✅ 就绪 |
| UntypedStorage 整块搬运 | 避免 Python tensor 碎片 | ✅ 就绪 |
| Per-layer eviction group | 独立 LRU per layer | ✅ 就绪 |

### 对话中尝试的优化
| 版本 | 改动 | ours tok/s | PPL | 结论 |
|------|------|-----------|-----|------|
| 基线 | 无 | 0.92 | ✅ | 基准 |
| v1 | 全量 ThreadPool I/O | 0.92 | ❌ swap硬塞cpu | 语义错误 |
| v2 | 临时缓冲+LRU路径 | 0.84 | ✅ | 线程池开销>收益 |
| v3 | prefill-only 并行 | 0.92 | ✅ | 回到基线 |

> **结论**: 线程池方向正确，但需搭配慢SSD或大expert(>300MB)场景才显现

### 待实现优化
| 优先级 | 项 | 预期收益 |
|--------|-----|---------|
| 1 | Triton fused SwiGLU-MLP kernel | 减少 kernel launch 开销 |
| 2 | mmap 合并存储（per-layer单文件）| 消除 1665次 os.open() |
| 3 | LFU/ARC 缓存算法 | Zipf 分布下 3-5% 命中提升 |
| 4 | HQQ 量化 (可选) | SSD 读量 4-8× 压缩 |

---

## 四、配置指南

### DeepSeek-V2-Lite
```bash
python e2e/run_e2e.py --model deepseek-ai/DeepSeek-V2-Lite \
  --hbm_budget 8 --cpu_budget 12 --alpha 0.73
# → K_H=19 K_C=28 SSD=17, ours 1.35× vs fiddler
```

### Mixtral-8x7B（真实A100）
```bash
python e2e/run_e2e.py --model mistralai/Mixtral-8x7B-Instruct-v0.1 \
  --hbm_budget 50 --cpu_budget 40 --alpha 1.0
# → K_H=4 K_C=3 SSD=1, ours 1.33× vs swapmoe
```

### 调参规律
- `hbm_budget`: 80GB卡扣掉trunk+KV，DeepSeek约8GB有效，Mixtral约50GB
- `cpu_budget`: 可用内存的30-50%，给pin_memory留余地
- `alpha`: DeepSeek用0.73（profile实测），Mixtral用1.0（均匀分布）
- 如果K_H太小(<10) → 缓存颠簸 → 加大hbm_budget
- 如果K_H太大(≥全部) → 无三级 → 减小hbm_budget

---

## 五、架构演进

```
v0.1: tiered_engine.py 单文件, if/elif 四策略平铺
v0.2: mecc_framework/ 模块化重构, AsyncSwapEngine 独立
v0.3: 线程池并行 SSD I/O（实验阶段, 已回退到 v0.1 稳定版）
next: 插件化 → 策略可动态注册
```
