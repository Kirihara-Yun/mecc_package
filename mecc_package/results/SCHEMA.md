# SCHEMA.md —— `results/` JSON 数据字典

> **定位**：本文件定义 `mecc_package/results/` 下所有实验 JSON 的字段含义、单位、取值约定与**来源类型**。
> **为什么需要**：`results/` 下的 JSON 实际有**两种互不兼容的结构**，且多个文件命名相似、参数不同，极易被误引用。
> 任何 agent 在引用 `results/*.json` 里的数字前 **必须先读本文件**，确认字段语义与该文件属于哪种 schema、是真机还是模拟器。
>
> 配套：数字 → 论文 claim 的对照与真伪登记见 [`../../docs/PROVENANCE.md`](../../docs/PROVENANCE.md)；
> 自动一致性体检见 [`../scripts/verify_claims.py`](../scripts/verify_claims.py)。

---

## 0. 一句话先记住

`results/` 下有**两类文件**，**不能混用、不能跨类比较**：

| 类 | 标志字段 | 含义 | 数字代表 |
|----|---------|------|---------|
| **A. 真机端到端（e2e）** | 顶层有 `"mode"` + `"compiled_plan"` + `"results"` | A100 真实推理实测（Mixtral 主结果；平台见顶层 `platform` 字段，`compiled_plan.hardware` 仅编译期配置串） | 真实 TTFT/TPOT/tok/s/PPL |
| **B. 缓存模拟器（simulator）** | 顶层有 `"workloads"`（无 `mode`/`results`） | 纯缓存命中率 + 延迟**模拟**，非真机推理 | 模拟器算出的 avg_lat / speedup |

> ⚠️ **铁律**：B 类（模拟器）的 `speedup` **不是真机加速比**，是命中率模型下的延迟比值。引用时**必须注明"模拟器"**。
> A 类与 B 类即使指标名相近（如 speedup）也**绝不可相互替代或拼表**。

---

## 1. Schema A —— 真机端到端（e2e）

**判定**：顶层同时存在 `mode`、`compiled_plan`、`results`。
**已知属于 A 的文件**：`raw/mixtral_real.json`、`main_table_5090.json`、`main_table_*.json`、`raw/deepseek_real_e2e.json` 中**带 `results.ours` 的那种**、`smoke_test.json`。

```jsonc
{
  "device": "cuda",                    // 运行设备；"cuda"=真机 GPU
  "mode": "real" | "smoke",            // ★ real=真机实测可引用；smoke=逻辑冒烟，禁止当性能证据
  "model": "<HF model id>",            // 被测模型
  "platform": "A100 80GB PCIe",        // ★【强制】实验真实平台权威字段（如 "A100 80GB"/"H100"/"RTX 5090"）。平台真值只认此字段，勿用 compiled_plan.hardware 反推
  "run_time": "2026-06-22T09:45:00+08:00",  // ★【强制】实验运行时间（ISO 8601）。落盘即写，杜绝事后对不上平台/时间
  "compiled_plan": {                   // 编译器（compiler.py）产出的静态放置方案
    "model": "...",
    "hardware": "rtx5090 (HBM_budget=..GB, CPU_budget=..GB)",  // 编译期配置串；★非平台权威（平台见顶层 platform 字段）。旧文件此处的 rtx5090 是历史配置串，平台真值=A100，见 PROVENANCE M5
    "alpha": 1.0,                      // 编译时使用的 Zipf α（注意：可能是占位/估计值，非 per-layer 实测）
    "n_layers": 32,
    "n_experts": 8,                    // 每层 expert 数 N
    "expert_mb": 336.0,                // ★ 单 expert 体积(MB)。注意与论文"理论体积"口径不同，见 §4
    "k_h": 4,                          // HBM 容纳 expert 数 K_H
    "k_c": 3,                          // CPU 容纳 expert 数 K_C
    "hbm_hit_pct": 76.7,               // 编译期 Zipf 模型预测的命中率（理论值，非运行实测）
    "cpu_hit_pct": 18.7,
    "ssd_hit_pct": 4.6,
    "hbm_gb_used": 42.0,
    "cpu_gb_used": 31.5
  },
  "config": {
    "max_new_tokens": 16,              // 每条 prompt 解码 token 数
    "prompt_len": 64,
    "n_prompts": 4,
    "cold_ssd": true                   // true=已用 F_NOCACHE/fadvise 清 page cache（冷 SSD）
  },
  "results": {
    "<policy>": {                      // policy ∈ {ours, swapmoe, fiddler}
      "ttft_ms": 168022.18,            // Time-To-First-Token，毫秒，运行实测
      "tpot_ms": 14226.94,             // Time-Per-Output-Token，毫秒，运行实测
      "tokens_per_s": 0.04,            // 吞吐，运行实测
      "ppl": 24.569,                   // 困惑度；数值=实测；"exact(lossless)"=与全量 fp16 逐位一致
      "hit_pct": {                     // ★ 运行期实测命中率（与 compiled_plan 的预测值区分！）
        "hbm": 44.4,
        "cpu": 38.0,
        "ssd": 17.6,
        "cpu_compute": 0.0             // Fiddler 专用：在 CPU 上直接算 expert 的占比
      },
      "speedup_vs": {                  // ★ 仅出现在 ours 下；为真机加速比
        "swapmoe": 1.333,              // = 对手 tpot / ours tpot（或等价口径，见该实验脚本）
        "fiddler": 2.474
      }
    }
  }
}
```

**A 类引用规则**：
- 真机加速比 **只认 `results.ours.speedup_vs.*`**；不要自己用 tok/s 反算（口径可能不同）。
- 命中率引用 **运行实测 `results.<p>.hit_pct`**，不要用 `compiled_plan.*_hit_pct`（那是编译期 Zipf 预测）。
- `mode=="smoke"` 的文件（如 `smoke_test.json`）**任何性能数字都不可引用**，只证明链路通。

---

## 2. Schema B —— 缓存模拟器（simulator）

**判定**：顶层存在 `workloads`，**没有** `mode`/`results`。
**已知属于 B 的文件**：`real_e2e_5090.json`、`real_e2e_a100.json`、`raw/real_e2e_results.json`、`raw/deepseek_real_e2e.json`（带 `workloads` 的那种）、`raw/concurrent_results.json`、`raw/deepseek_concurrent.json`。

> ⚠️ **命名陷阱**：文件名带 `real_e2e` **不代表真机**！B 类是**缓存命中率模拟器**的产物（policy 名为 `TieredLRU`/`FluxMoE`/`SwapMoE`，用 `avg_lat_us` 而非 `ttft_ms`）。真假以**结构**判定，不以文件名判定。

```jsonc
{
  "device": "cuda",
  "config": {
    "n_experts": 64,                   // ★ 模拟规模 N（不同文件差异巨大：64 / 96 ...）
    "expert_mb": 7.1,                  // ★ 模拟用的 expert 体积（合成值，可能远小于真实模型）
    "hidden": 576, "ffn": 2048,        // 模拟用结构参数（合成，未必等于真实模型）
    "batch": 64,
    "alpha": 0.73,                     // 模拟用 Zipf α
    "requests": 600,                   // 模拟请求数
    "k_h": 19, "k_c": 45,
    "phases": 4,                       // 漂移阶段数
    "fast_fraction": 1.0
  },
  "workloads": [
    {
      "workload": "stationary" | "drift",   // 静止负载 / 热点漂移
      "results": [
        {
          "policy": "FluxMoE"|"SwapMoE"|"TieredLRU",  // TieredLRU = MECC(ours) 在模拟器中的名字
          "hbm_hit_pct": 49.2,
          "cpu_hit_pct": 50.8,
          "ssd_hit_pct": 0.0,
          "avg_lat_us": 501.4,         // 模拟平均延迟(µs)，由命中率 × 各级延迟模型算出
          "p50_us": 838.1,
          "p99_us": 1053.2,
          "wall_s": 0.3                // 模拟器墙钟（不是真机推理时间）
        }
      ],
      "speedup": {                     // ★ 模拟器加速比 = 对手 avg_lat / TieredLRU avg_lat
        "vs_flux": 6.26,               // = FluxMoE.avg_lat_us / TieredLRU.avg_lat_us
        "vs_swap": 3.99                // 引用时必须写明"（模拟器）"
      }
    }
  ]
}
```

**B 类引用规则**：
- `speedup.vs_*` 必须标注 **"缓存模拟器，非真机"**，且**必须带上该文件的 `config`**（N、expert_mb、alpha）——否则无法解释这个数字代表哪个规模。
- 不同 B 文件 `config` 不同（见下表），**数字不可跨文件比较**。

---

## 3. 文件归属速查表（防张冠李戴）

| 文件 | Schema | N | expert_mb | α | 代表 | 备注 |
|------|--------|---|-----------|---|------|------|
| `raw/mixtral_real.json` | A 真机 | 8 | 336 | 1.0 | **Mixtral 主场景**（落 SSD） | 主表唯一真机 Mixtral 证据 |
| `main_table_5090.json` | A 真机 | 64 | 16.5 | 0.73 | DeepSeek e2e（5090, K_H19/K_C45） | 见 PROVENANCE 关于与论文表3口径的差异 |
| `main_table_*.json`（amp/batch/opts/prefetch/stream） | A 真机 | — | — | — | DeepSeek 优化消融各档 | 与 `results/README.md` 主表对应 |
| `smoke_test.json` | A（mode=smoke） | — | — | — | 冒烟 | **禁止当性能证据** |
| `raw/deepseek_real_e2e.json` | **B 模拟器** | 64 | 7.1 | 0.73 | **论文表7（漂移 9.50×/5.68×）来源** | DeepSeek-scale 合成 |
| `real_e2e_5090.json` | B 模拟器 | 96 | 352.3 | 1.2 | Mixtral-scale 模拟 | 漂移 vs_flux 1.677 |
| `real_e2e_a100.json` | B 模拟器 | 96 | 352.3 | 1.2 | Mixtral-scale 模拟 | 漂移 vs_flux 1.635 |
| `raw/real_e2e_results.json` | B 模拟器 | 96 | 100.7 | 1.2 | 中等规模模拟 | 漂移 vs_flux 1.632 |

> 同名 `real_e2e_*` 的 B 文件因 `config`（N/expert_mb）不同，speedup 差异巨大且**都不是真机**。
> **论文表7 的 9.50×/5.68× 唯一对应 `raw/deepseek_real_e2e.json`（N=64, expert_mb=7.1 的合成 DeepSeek 规模）**，引用时务必注明"模拟器、DeepSeek 合成规模"。

---

## 4. 已知口径差异（引用前必读）

| 量 | JSON 实测 | 论文/文档另一处口径 | 处理 |
|----|----------|--------------------|------|
| Mixtral 单 expert 体积 | `expert_mb=336`（实际加载体积） | 论文 §2.1 `S_expert≈1407 MB`（3 矩阵理论体积） | 二者口径不同：论文是 \(3 d d_{ff}\) 理论上界，JSON 是实际张量。引用须说明口径。 |
| Mixtral 平台 | 顶层 `platform="A100 80GB"`（权威）；`compiled_plan.hardware=rtx5090`（编译期配置串，非平台） | 论文表5/摘要、`STRATEGY.md §2.2` 写 "A100 80GB"（真实A100，1.33×等数字标在 A100 行） | **以顶层 `platform` 为准（A100）**：实验先在 5090 调试、Mixtral 主结果最终在 A100 跑定。各 JSON 已回填 `platform`+`run_time`；`hardware` 仅为编译期配置串、不再作平台依据。已在 PROVENANCE 标 M5 采信 A100、矛盾 X2/X5 已澄清。 |
| Mixtral OURS vs Swap | `speedup_vs.swapmoe=1.333` | 论文 §5.5 正文 "TPOT 1.62×" | 数值不一致，已登记 discrepancy；对外口径以 **1.33×（JSON）** 为准。 |
| DeepSeek e2e 主数字 | `main_table_5090`: tok/s 2.38, OURS/Swap 2.59× | 论文表3: tok/s 0.92, 加速比 1.00/1.03/1.35, TTFT 1.56× | 两套数字对不上，已登记 discrepancy；详见 PROVENANCE §对照表。 |

> 这些差异**不是要立刻改数字**，而是要求任何引用都**带出处+口径**，并在 [`docs/PROVENANCE.md`](../../docs/PROVENANCE.md) 的登记表里查状态（`verified`/`discrepancy`/`unverified`），**严禁把 discrepancy 数字当已核实结论引用**。

---

## 5. 新增实验 JSON 时（SOP）

1. 先确定属于 **A（真机）还是 B（模拟器）**，沿用对应结构，不要发明第三种。
2. **真机文件必须有 `mode` 字段**（`real`/`smoke`）；模拟器文件**不要**加 `mode`，以免被误当真机。
3. **【强制】每个新落盘 JSON 顶层必须写 `platform` 与 `run_time` 两个字段**——这是吸取「5090/A100 平台对不上、时间无记录」教训定下的铁律：
   - `platform`：实验真实平台权威字段，如 `"A100 80GB"`/`"H100"`/`"RTX 5090"`。**平台真值只认此字段**，不要再靠 `compiled_plan.hardware`（那是编译期配置串、会过时/遗留）。
   - `run_time`：实验运行时间，**ISO 8601 带时区**（如 `"2026-06-22T09:45:00+08:00"`）。落盘当下即写，杜绝事后对不上。
   - 缺任一字段的新文件视为不合规，体检会 WARN。
4. 文件落到 `results/`（主表级）或 `results/raw/`（中间产物）；**不要删旧文件**（`*_old.json` 是论文证据备份）。
5. 在 [`docs/PROVENANCE.md`](../../docs/PROVENANCE.md) 的溯源表登记：文件 → 产生脚本/命令 → **平台 + 运行时间** → 它支撑哪条 claim → 状态。
6. 跑 `python3 scripts/verify_claims.py` 做一致性体检（见该脚本）。
