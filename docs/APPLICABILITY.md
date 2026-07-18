# 适用性边界 —— MECC 何时有效、何时无效

> **一句话**：MECC 的价值**只在「连 CPU 内存都装不下整个模型」时才成立**。
> 此时模型必须有一部分权重落到 SSD，三级缓存（HBM → CPU → SSD）才有用武之地。
> 模型类型不重要，**关键是它能不能把 CPU 内存打满**。

---

## 1. 为什么是这个边界

MoE 推理时，绝大部分参数集中在 expert 权重上。部署时只有三种放置层级：

| 层级 | 容量 | 单 expert 取数延迟（量级） |
|------|------|---------------------------|
| HBM（GPU 显存） | 最小（如 24–80GB） | ~µs（已在卡上） |
| CPU pinned 内存 | 中（如 64–512GB） | ~ms（PCIe H2D） |
| SSD（NVMe 冷存） | 最大（TB 级） | ~10–100ms（真冷读） |

- **如果模型能塞进 HBM** → 不需要任何 offload，MECC 无意义。
- **如果模型塞不进 HBM、但能塞进 CPU 内存** → 两级（HBM+CPU）方案（如原版 mixtral-offloading、SwapMoE）就够了，**第三级 SSD 用不上，MECC 相对两级方案没有结构性优势**。
- **如果模型连 CPU 内存都塞不下** → 必须有一部分 expert 落 SSD。此时：
  - 朴素方案每次 miss 都触发昂贵的 SSD 冷读，decode 极慢；
  - **MECC** 用「编译器静态放置 + 运行期 HBM/CPU 联合动态 LRU」把热 expert 钉在快层、冷 expert 才落 SSD，显著降低 SSD 命中率 → 这正是 MECC 的主场。

**所以判断 MECC 是否适用，只看一个条件：`模型 expert 总量 > 可用 CPU 内存`。**

---

## 2. 决策树

```
模型 expert 权重总量 = n_layers × n_experts × expert_size
            │
            ▼
  能塞进 HBM?  ──是──▶ 不用 offload，MECC 无意义
            │否
            ▼
  能塞进 CPU 内存? ──是──▶ 两级方案足够，MECC 无结构性优势
            │否（CPU 也装不下，必须落 SSD）
            ▼
   ★ MECC 有效区 ★   ──▶ 三级缓存 + 编译器放置带来收益
```

---

## 3. 具体例子（按「能否打满 CPU」分类）

| 模型 | expert 总量(fp16) | 典型 CPU 内存 | 落 SSD? | MECC 适用? |
|------|------------------|--------------|---------|-----------|
| **Mixtral-8x7B** | ~90GB | 32–64GB | **是** | ✅ **主场景**（实测 1.33× vs SwapMoE，且无损） |
| Qwen-MoE / DeepSeek-MoE 大档 | 数十~上百 GB | 视机器 | 视机器 | ✅ 只要总量 > CPU 内存即适用 |
| DeepSeek-V2-Lite | ~小（CPU 可容） | 30GB+ | 基本否 | ⚠️ **对照场景**：CPU 装得下，SSD 几乎不触发，仅用于展示算法上界 |
| 任意能塞进单卡的稠密/小 MoE | < HBM | — | 否 | ❌ 不适用 |

> **结论**：不是「只有 Mixtral 有效」，而是「只要模型大到能打满 CPU 内存、被迫落 SSD，MECC 就有效」。Mixtral 只是当前手头最具代表性的验证模型。

---

## 4. 两个场景的真实实验对照

### 4.1 主场景：Mixtral-8x7B（90GB，连 CPU 都装不下，被迫落 SSD）
来源：`mecc_package/results/raw/mixtral_real.json`（A100 80GB, cold SSD；平台以 JSON 顶层
`platform` 为准）

| 指标 | OURS | SwapMoE |
|------|------|---------|
| tokens/s | — | — |
| **加速比** | **1.33× vs SwapMoE** | 1.0 |
| **PPL（精度）** | **24.57（fp16）** | 36.12（JSON 对照值；2-bit/SwapMoE 身份待核） |
| SSD 命中率 | 17.6% | 34.5% |

> MECC 的当前实现全程 fp16，并把 SSD 命中从 34.5% 压到 17.6%（更多 expert
> 命中快层）。对照行 PPL 36.12 的 2-bit/SwapMoE 身份无法由当前 fp16 harness
> 解释，已登记 PROVENANCE X6；关闭前不将二者合成“同一 baseline 的速度+质量”结论。

### 4.2 对照场景：DeepSeek-V2-Lite（CPU 装得下，SSD 几乎不触发）
来源：`mecc_package/results/`（A100 80GB, α=0.73）

| 优化层级 | Ours (tok/s) | SwapMoE | Ours/Swap |
|----------|-------------|---------|-----------|
| 无优化 | 2.38 | 0.92 | **2.59×** |
| +批量预取 | 5.58 | 5.06 | 1.10× |

> 这组数字展示的是**算法层面的结构性上界**（路由热度建模的价值），但因为 DeepSeek-V2-Lite 不会真正打满 CPU、几乎不落 SSD，**它不能作为 MECC「主战场」的证据**，只作为算法有效性的对照参考。

---

## 5. 给使用者 / AI 的检查清单

在声称「MECC 在某模型上有效」之前，先确认：

- [ ] 模型 expert 权重总量 **> 目标机器可用 CPU 内存**（否则两级就够）。
- [ ] 实验确实开启了 **SSD 冷存层**（`--store_root` 指向真实 NVMe，且 `--cold_ssd`）。
- [ ] 对比的 baseline 在**同预算（K_H+K_C）、同 store、同 prompt、同卡**上跑（apples-to-apples）。
- [ ] 报告**端到端 TTFT/TPOT/tokens·s 与 PPL**，而非仅子系统取数延迟。

只要以上成立，MECC 的三级缓存才是在解一个真实存在的瓶颈。
