# MECC 项目总结 & RTX 5090 实验计划

> 方向: MoE Expert Cache Compiler (MECC) — 三级 Expert 缓存 (HBM→CPU→SSD)
> 目标会议: DAC 2027 (投稿截止 ~2026.11)
> 文档生成: 2026-06-17 | 状态: Apple 阶段收尾，准备迁移到 RTX 5090

---

## 第一部分 · 全部文档与成果盘点

### 1. 一句话定位

把经典三级缓存层级 **首次** 应用于 MoE expert 权重，并 **首次量化** "expert 权重 vs KV Cache 争抢 HBM" 这个 trade-off。核心是一个编译器 MECC：`Profile(估 α) → Optimize(Theorem 4 最优分配) → Allocate(tier map) → Validate`，输出可部署的 expert→tier JSON 配置。

### 2. 理论资产 (proofs.md) — 项目最硬的部分

| 定理 | 内容 | 意义 |
|------|------|------|
| Lemma 1+2 | Zipf 访问 + K-tier LRU 闭式命中率 `H(K)=H_{K,α}/H_{N,α}` | 建模基础 |
| Theorem 1 | `E₃ < E₂`，差值 `=(T_S−T_C)(1−H_{K_H,α}/H_{N,α})` | 三级严格优于两级 |
| Theorem 2 | 加速比 `η ≈ E₂/E₃` | 加速来源；HBM 极限时 η→T_S/T_C≈14× |
| Theorem 3 | `T*(M)` 存在唯一最优 HBM 分配 | expert vs KV 预算可解 |
| Theorem 4 | Lagrangian 闭式解 `(T_j−T_{j+1})/C_j · K_j^{α−1}=const` | 可计算最优配置 |

**关键依赖**：所有定理的加速比都正比于两个独立因子相乘——
- 硬件因子：层级间延迟落差 `T_S−T_C` / `T_C−T_H`
- 分布因子：偏斜带来的命中率项 `H_{K,α}/H_{N,α}`（由 α 决定）

### 3. 新颖性 (novelty_check.md + timeline.md)

- 对比 30 篇 SOTA：FluxMoE / SwapMoE / FineMoE / ElasticMoE / CRAFT / Janus / ZipMoE / D²MoE …
- **护城河 = 主张 1 + 2 的组合**：没人把"三级缓存"和"HBM 竞争量化"放在一起。FluxMoE 最接近（提到 KV 竞争）但只当 motivation、未量化，且设计是"用后即弃"（与我们相反）。
- **时间窗口成立**：FluxMoE(2026.04) 之后、DAC 投稿(2026.11) 之前有约 6 个月空白。
- ⚠️ 待办：提交前手动复跑一次 arXiv + Google Scholar 终检（之前搜索全被 429 限流，结论基于已得 30 篇 + 训练知识）。

### 4. 实测成果与状态

#### 4.1 层级延迟 (measured_latency.json，Apple UMA 真机)
| 层 | 延迟 | vs HBM |
|---|---|---|
| HBM hit | 1830.8 μs | 1× |
| CPU hit | 5679.9 μs | **3.10×** |
| SSD miss | 45376.1 μs | 24.8× |

#### 4.2 真机端到端 (real_e2e_results.json，96 experts / MPS)
| 场景 | vs FluxMoE | vs SwapMoE |
|---|---|---|
| stationary | 0.80× (输) | 0.70× (输) |
| drift | 1.16× (赢) | 1.00× (打平) |

#### 4.3 投影到数据中心硬件 (projection_results.json)
| 硬件 | HBM:CPU 落差 | drift vs_swap | stationary vs_swap |
|---|---|---|---|
| A100 PCIe4 | 116× | **1.24×** | 0.95 |
| H100 PCIe5 | 87× | **1.24×** | 0.95 |
| Apple UMA | 3.1× | 1.25× | 0.95 |

#### 4.4 真实 α 测量 (与硬件无关，可直接信)
| 模型 | 全局 α | 每层 α | 备注 |
|---|---|---|---|
| switch-base-8 | 0.352 | 深层最高 1.93 | 小模型 artifact |
| **switch-base-128** | **0.689** | **均值 1.19**，解码深层 1.33–1.75 | ✅ 新测 |

### 5. 三条已确认的核心判断

1. **Apple UMA 不是目标场景，不能用来证伪方法。** UMA 把 HBM/CPU 落差压到 3.1×，而方法收益正比于该落差；A100/H100 上落差是 ~100×，drift 场景投影即可翻到 1.24–1.72×。stationary 仍输（0.95），那是低偏斜啃掉的，靠硬件补不回来。
2. **"全局 α 低"是统计假象，理论吃的是"每层 α"。** 把 11 层计数池在一起会互相抹平；缓存是逐层发生的。switch-base-128 每层 α 均值 **1.19 ≈ 假设的 1.2**，解码深层高达 1.75 —— 真实大模型实测背书了原始假设。
3. **方法的甜区是 drift（访问分布漂移）+ 深层 + 独显**，不是 stationary。这点应直接写进论文定位。

### 6. 代码资产
- `compiler.py` / `compile.py` — MECC 编译器主流程
- `tiered_cache.py` / `tier_sim.py` — 缓存模拟器（5 策略）
- `real_tiered_cache.py` / `concurrent_tiered_cache.py` — 真机缓存实现（含并发）
- `measure_tiers.py` — 层级延迟真机测量
- `profile_gpu.py` — 三步 profiling（**已含 CUDA 分支**，但 α 用 Mixtral，需改）
- `profile_real_moe.py` — 真实 MoE α 测量（router hook，已跑出 base8/base128）
- `runtime_spec.py` — 运行时规格

---

## 第二部分 · 为什么必须上 RTX 5090

Apple 已经把"与硬件无关的成果"榨干了（α 测量完成）。剩下所有关键证据都卡在同一个瓶颈：**Apple UMA 的层级落差太小，端到端跑出来不算数。** 5090 是独立 GDDR7 + PCIe5，VRAM↔主机内存的落差恢复到数量级级别——这正是定理预测方法获胜的目标硬件。

**5090 上要回答的核心问题：在真实独显落差 + switch-base-128 实测的每层 α(≈1.2) 下，端到端到底能不能赢、赢多少？** 这是把"投影"变成"真跑"的唯一一步，决定论文能否立住。

---

## 第三部分 · 5090 实验计划（按优先级）

### Step 0 · 环境搭建（迁移到 5090 机器后）
- [ ] 安装 CUDA 版 PyTorch（匹配 5090 / Blackwell，需较新 CUDA 12.x+ 与对应 torch nightly）
- [ ] `pip install transformers accelerate`
- [ ] 拷贝整个 `mecc_package/`（含已测的 `real_alpha_base128.json` 等历史结果，勿覆盖）
- [ ] 预下载模型：switch-base-128 已有缓存可直接拷；端到端建议再备一个更大的真实 MoE（见 Step 3）

### Step 1 · 真机层级延迟（最优先，定标尺）
**目的**：在 5090 上测出真实的 `T_HBM / T_CPU / T_SSD`，替换 `measured_latency.json` 里的 Apple 数。
- [ ] 用 `measure_tiers.py` / `profile_gpu.py` 的 CUDA 分支跑层级延迟
- [ ] **关键修正**：CUDA 是独显，`T_CPU` 必须是 **真实 PCIe H2D 传输延迟**（`tensor.to('cuda')` 计时），不能复用 Apple 的"CPU compute"口径
- [ ] 预期：HBM:CPU 落差应在 ~50–120×（对齐 A100/H100 量级），证实 UMA 假说

### Step 2 · 真实 α 复核（已基本完成，可选加强）
- [ ] base128 的 α 已测（每层均值 1.19）。如需更强证据，可换更大真实 MoE（如 Mixtral-8x7B / Qwen-MoE）在 5090 上跑 `profile_real_moe.py` 同款 router-hook 逻辑
- [ ] α 与硬件无关，此步主要为"更大模型上每层 α 是否更高"补证据

### Step 3 · 真机端到端（最关键，决定成败）
**目的**：在真实落差 + 真实 α 下跑 FluxMoE / SwapMoE / TieredLRU 三方对比，得到**真跑**的加速比（替代投影）。
- [ ] 用 `real_tiered_cache.py` / `concurrent_tiered_cache.py` 跑端到端
- [ ] 工作负载：**stationary + drift 两个都要**（drift 是甜区）
- [ ] 模型规模：用能撑出"HBM 装不下全部 expert"(K_H<N) 的配置，否则三级优势体现不出
- [ ] 预期/验收：drift 场景 vs SwapMoE 达到投影的 **1.2–1.7×**；若达成，论文主结果成立

### Step 4 · 结果固化与论文对接
- [ ] 把 5090 真测数写回新 JSON（`real_e2e_5090.json` / `measured_latency_5090.json`），**不要覆盖 Apple 历史数据**——两平台对比本身就是"UMA 假说"的有力论据
- [ ] 更新 README 核心结果表：区分"理论/模拟"与"5090 真测"
- [ ] 在论文 limitation/平台说明里写入 Apple UMA 的负结果 + 解释（落差被压扁），化被动为主动

### 风险与对策
| 风险 | 对策 |
|---|---|
| stationary 仍输 (0.95) | 论文定位聚焦 drift + 深层；stationary 如实报告 |
| 5090 Blackwell torch 支持不稳 | 优先 torch nightly + CUDA 12.x；必要时退 H100/A100 验证 |
| SSD 层在真机难复现 | 可用显式 NVMe 读 (F_NOCACHE/O_DIRECT) 或先聚焦 HBM↔CPU 两层落差 |

---

## 一句话交接

理论 + 新颖性 + 真实 α(每层≈1.2) 三块已立住；**唯一未完成的关键证据是"独显真机端到端"**——这正是 5090 要跑的。把 Step 1(标尺) → Step 3(端到端 drift) 跑出 1.2× 以上，论文主结果即闭环。
