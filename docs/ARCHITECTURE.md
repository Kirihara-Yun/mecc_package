# 架构 —— 编译器引导的三级缓存如何工作

> 配套阅读：科研叙事 [`RESEARCH_NARRATIVE.md`](./RESEARCH_NARRATIVE.md)、适用性边界
> [`APPLICABILITY.md`](./APPLICABILITY.md)、术语 [`GLOSSARY.md`](./GLOSSARY.md)。

---

## 1. 总体思想：先优化对象放置，再实例化为 expert 缓存

MECC 的架构对象是只读、可独立搬运的大对象集合。编译期根据 profile 给出三级初始放置，
运行期根据真实请求流动态修正。MoE 实例把“对象”映射为 expert 权重块，把“请求”映射为
router 选择；核心库的状态机与数学目标并不依赖 gate 或 top-k 的具体形式。

```
┌─────────────── 编译期（offline，CPU 即可）───────────────┐
│  Profile(估访问热度/Zipf α；MoE 中来自 router trace)       │
│        │                                                  │
│        ▼                                                  │
│  Optimize(用 Zipf/Theorem 在预算下解每层 K_H/K_C)         │  ← compiler.py / compile.py
│        │                                                  │
│        ▼                                                  │
│  Allocate(生成对象 → {HBM/CPU/SSD} 静态放置表)             │
└───────────────────────────────────────────────────────────┘
                         │ 编译产物（plan）
                         ▼
┌─────────────── 运行期（online，需 GPU）─────────────────┐
│  三级缓存：HBM(K_H) + CPU pinned(K_C) + SSD(其余)         │
│  miss 时：HBM/CPU 联合动态 LRU 升降级 + 异步 PCIe 预取    │  ← mecc_framework/cache, e2e/tiered_engine
│  应用适配：MoE 中为 gate routing → expert dispatch → 聚合 │  ← mecc_framework/layers/moe_forward
└───────────────────────────────────────────────────────────┘
                         │
                         ▼
        Validate(端到端 TTFT/TPOT/tokens·s + PPL，四策略对比)   ← e2e/run_e2e.py
```

---

## 2. 两套实现并存（重要！别混淆）

仓库里有**两套缓存实现**，定位不同：

| 实现 | 位置 | 定位 |
|------|------|------|
| **`mecc_framework/`** | `mecc_package/mecc_framework/` | 模块化、可复用的**核心库**（清晰分层 base/cache/layers/models/benchmark），架构无关，附带纯 CPU smoke test |
| **`e2e/`** | `mecc_package/e2e/` | 面向论文主表的**端到端 harness**（接真实 HF Mixtral、真实 generate、四策略 apples-to-apples），叙事见 `e2e/README_E2E.md` |

两者共享同一套方法论与编译器（`compiler.py`），但 `e2e/` 是为「出论文主表」服务的独立扁平脚本集，`mecc_framework/` 是为「工程化复用」服务的库。

两套实现的公共语义由 `e2e/test_cache_consistency.py` 守护：四个 active baseline 在同一微型
trace、相同初始放置和相同 K_H/K_C 下，逐次比较 HBM/CPU/static-CPU 驻留与四类命中计数。
该测试只验证缓存状态机一致性，不把微型 trace 的性能作为实验结论。

---

## 3. 核心库 `mecc_framework/` 模块结构

```
mecc_framework/
├── base/                       # 基础数据与底层存储
│   ├── config.py               # CachePolicy/QuantPolicy 枚举；ExpertSpec/ModelSpec/CacheBudget/OffloadConfig
│   ├── expert.py               # ExpertWeights：连续 storage + 零拷贝 view + SwiGLU 前向；EXPERT_SHAPES
│   └── store.py                # ExpertSSDStore：每 expert 一个 .bin，绕 page cache 的真冷读
├── cache/                      # 三级缓存与异步搬运
│   ├── engine.py               # LayerExpertCache：一引擎四策略（per-layer expert 缓存）
│   └── swap.py                 # AsyncSwapEngine：专用 copy_stream + 批量预取 + buffer pool
├── layers/
│   └── moe_forward.py          # UniversalSparseMoe：架构无关 MoE 前向（softmax_topk/sigmoid/pre_routed）
├── models/                     # 适配器（注册中心 get_adapter）
│   ├── base.py                 # ModelAdapter 抽象基类
│   ├── deepseek.py             # DeepSeekAdapter
│   └── mixtral.py              # MixtralAdapter
└── benchmark/
    ├── runner.py               # 端到端 benchmark CLI（TTFT/TPOT/吞吐/命中率 → JSON）
    └── smoke_test.py           # 纯 CPU 全链路自检（微型随机 MoE）
```

**关键依赖方向**：`benchmark` → `models` / `layers` → `cache` → `base`（单向，base 不反向依赖）。
公共 API 由顶层 `__init__.py` 与 `models/__init__.py`（`get_adapter`）暴露。

---

## 4. 三级缓存的数据流（一次 expert 访问）

```
gate 选中 expert e（第 L 层）
        │
        ▼
   在 HBM(K_H)?  ──命中──▶ 直接计算（最快，~µs）
        │ miss
        ▼
   在 CPU pinned(K_C)? ──命中──▶ AsyncSwapEngine 异步 H2D 搬上 GPU（~ms），LRU 升级
        │ miss
        ▼
   在 SSD?  ──▶ ExpertSSDStore 冷读到 CPU（~10–100ms）→ 再搬 GPU（最慢，瓶颈所在）
        │
        ▼
   计算后按 LRU 更新三级驻留；批量预取把同层将用到的 CPU expert 一次性搬上去（饱和 PCIe）
```

> SSD 命中率是核心指标：MECC 的目标就是**通过更好的放置 + 动态 LRU 压低 SSD 命中率**。
> 主场景 Mixtral 上 MECC 把 SSD 命中从 SwapMoE 的 34.5% 压到 17.6%。

---

## 5. 四种策略（同预算下对比，apples-to-apples）

| policy | HBM(K_H) | CPU(K_C) | miss 行为 | 角色 |
|--------|----------|----------|-----------|------|
| **`ours`** | 动态 LRU | 动态 LRU（与 HBM 联合升降级） | 落 SSD | **本文方法** |
| `swapmoe`（显示名 `swapmoe_fp16`） | 动态 | **静态** top-K_C 驻留 | 落 SSD | 同预算、同精度的机制对照 |
| `fiddler` | 常驻 | — | miss 时**在 CPU 上算 expert**（搬激活而非权重） | CPU-GPU 协同 |
| `naive` | 不常驻 | — | 每次从 CPU/SSD **流式**搬权重 | 全 offload 下界 |

当前四策略 harness 全程使用同一 fp16 store；其中 `swapmoe` 是 **SwapMoE-style 静态 CPU
机制的同预算 fp16 适配**，不是外部论文量化实现。未来若重建可追溯的低比特系统基线，必须用
独立 id `swapmoe_quantized`、独立命令和独立结果行，不能与当前 `swapmoe` 合并。

---

## 6. 编译器（compiler.py / compile.py）

- `compiler.py`：**库形式**，被 `e2e/compile_config.py`（`from compiler import ...`）与 `runtime_spec.py` 引用。**勿移动**（依赖 `sys.path` 指向 e2e 父目录）。
- `compile.py`：**standalone CLI 全功能版**，独立运行，无人 import。
- 核心：基于 profiled 路由热度（Zipf α）在 HBM/CPU 预算约束下，为每层求最优 `(K_H, K_C)` 切分，使预期取数延迟最小。

---

## 7. 端到端 harness `e2e/`（出论文主表）

```
e2e/
├── tiered_engine.py    # 三级缓存引擎（ExpertWeights / SSDExpertStore / LayerExpertCache）
├── mixtral_tiered.py   # 接真实 HF Mixtral：safetensors 流式抽 expert + forward 钩子 + 4 策略
├── deepseek_tiered.py  # DeepSeek 适配器（对照场景）
├── compile_config.py   # 编译器接入（复用根级 compiler.py 的 Zipf 理论）→ 每层 (K_H,K_C)
├── policy_plugin.py    # 策略插件
├── run_e2e.py          # 主 harness：TTFT/TPOT/tokens·s + PPL，四策略，含 --smoke
└── run_5090.sh         # 一键脚本
```

跑法见 [`../mecc_package/e2e/README_E2E.md`](../mecc_package/e2e/README_E2E.md)。

---

## 8. 出数口径（论文用）

`main_table_*.json.results[policy]`：`ttft_ms` / `tpot_ms` / `tokens_per_s` / `ppl` / `hit_pct{hbm,cpu,ssd,cpu_compute}` / `speedup_vs`。
报**端到端**指标（与 SOTA 同口径），子系统级 micro-benchmark 仅作附录 ablation。
