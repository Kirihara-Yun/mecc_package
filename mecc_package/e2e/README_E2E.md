# MECC 端到端框架（真实 MoE「编译 → 运行」）

> 目标：和 SOTA（SwapMoE / Fiddler / Mixtral-offloading / MoE-Infinity）**同一套口径**做实验——
> 真实 Mixtral 模型、真实 prompt、真实 `generate()`，头条指标是 **TTFT / TPOT / tokens·s⁻¹ + PPL**，
> 四种策略跑在**同一份模型 + 同一批 prompt + 同一张 5090** 上，apples-to-apples。
> 产物 `main_table_5090.json` 可直接进 DAC 主表。

---

## 0. 这套框架复用了谁、改了什么

**复用** `dvmazur/mixtral-offloading` 的工程框架（学术上正当的框架复用，已在代码注释中标注来源）：

| 复用点 | 来源文件 | 我们怎么用 |
|---|---|---|
| `SparseMoeWrapper.forward` 的 expert dispatch | `custom_layers.py` | 照搬 forward（HF Mixtral 兼容，返回 `(hidden, router_logits)`），见 `mixtral_tiered.TieredSparseMoe` |
| expert 权重连续 storage、pinned、异步搬运思想 | `expert_wrapper.py` / `expert_cache.py` | 见 `tiered_engine.ExpertWeights` / `LayerExpertCache` |
| `init_empty_weights` 建无 expert 显存骨架，trunk/attn/gate 常驻 GPU | `build_model.py` | 见 `mixtral_tiered.build_tiered_model` |

**两处关键改造（这是我们的贡献，也是卖点）：**

1. **两级 → 三级**：原框架是 GPU + CPU 两级 LRU；Mixtral fp16 ~90GB 连 CPU 也装不下，必须落 **SSD**。
   我们扩成 **HBM + CPU pinned + SSD 冷存** 三级，由编译器静态放置 + 运行期联合动态 LRU。
2. **去掉 HQQ 2-bit 量化 → 全程 fp16 无损（lossless）**：原框架靠 2-bit 量化塞进消费卡，是**有损**方法；
   我们 expert 输出与原模型逐位一致（**0 精度损失**）——这是相对 SwapMoE/EdgeMoE 的核心卖点，
   同时绕开 5090（sm_120/Blackwell）上 triton 量化 kernel 的兼容性风险。

四种策略（同预算 K_H+K_C、同 store、同 trace）：

| policy | 机制 | 角色 |
|---|---|---|
| `ours` | HBM(K_H)+CPU(K_C) 联合**动态** LRU + 升降级，其余 SSD | **本文方法** |
| `swapmoe`（`swapmoe_fp16`） | 仅 HBM(K_H) 动态；CPU 驻留**静态** top-K_C；其余 SSD；同一 fp16 store | 同预算机制对照 |
| `fiddler` | HBM(K_H) 常驻；miss 时在 **CPU 上算 expert**（搬激活） | CPU-GPU 协同 |
| `naive` | 不常驻 expert，每次从 CPU/SSD **流式**搬权重 | 全 offload 下界 |

`swapmoe` 是为兼容历史 JSON 保留的策略 id，准确身份是 SwapMoE-style 静态 CPU 策略的
fp16 三层适配，不是独立 2-bit 实现。量化 baseline 预留名为 `swapmoe_quantized`，在版本、
命令与质量证据可追溯前保持 inactive（见 PROVENANCE X6）。

---

## 1. 文件清单

```
e2e/
├── tiered_engine.py      ← 三级缓存引擎（ExpertWeights / SSDExpertStore / LayerExpertCache）
├── mixtral_tiered.py     ← 接真实 HF Mixtral：safetensors 流式抽 expert + forward 钩子 + 4 策略
├── compile_config.py     ← 编译器接入（复用上层 compiler.py 的 Zipf 理论）→ 每层 (K_H,K_C)
├── run_e2e.py            ← 主 harness：TTFT/TPOT/tokens·s + PPL，四策略主表，含 --smoke 自检
├── run_5090.sh           ← 一键脚本
└── requirements_e2e.txt  ← 依赖
```

---

## 2. 第一步：本机/到机先跑 smoke（不下载，秒级，验证逻辑）

```bash
cd e2e
python run_e2e.py --smoke
# 或： bash run_5090.sh smoke
```
会造一个微型随机 MoE，在 CPU 上把「编译 → 物化到 SSD → 三级换页 → 四策略计时 → 出主表」整条链路跑一遍。
**目的只是验证代码逻辑通**（smoke 用随机 gate≈均匀访问，不体现加速；真实 Zipf 偏斜负载才是 tiering 的主场）。

---

## 3. 5090 上跑真实 Mixtral 端到端

### 3.1 装依赖
```bash
pip install -r requirements_e2e.txt
# 若 torch 不识别 5090 (sm_120)：
# pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu124
```

### 3.2 下载模型（~90GB，需 HF 授权 Mixtral）
```bash
huggingface-cli login            # 首次需登录并同意 Mixtral 协议
huggingface-cli download mistralai/Mixtral-8x7B-Instruct-v0.1 \
  --include "*.safetensors" "*.json" "tokenizer*" \
  --local-dir /data/mixtral
```
> 也可不预下载，`run_e2e.py` 会用 `snapshot_download` 自动拉到 HF cache（但建议显式 `--state_path` 控制位置）。

### 3.3 一键跑主表
```bash
STATE_PATH=/data/mixtral STORE_ROOT=/data/mecc_store \
HBM_BUDGET=22 CPU_BUDGET=40 \
bash run_5090.sh full
```
或直接：
```bash
python run_e2e.py \
  --model mistralai/Mixtral-8x7B-Instruct-v0.1 \
  --state_path /data/mixtral \
  --store_root /data/mecc_store \
  --hbm_budget 22 --cpu_budget 40 --alpha 1.0 \
  --prompt_len 64 --max_new_tokens 64 --n_prompts 8 \
  --out main_table_5090.json
```

**首次运行**会把 256 个 expert（32 层 × 8）流式物化到 `STORE_ROOT`（~90GB fp16，幂等可断点续跑），
完成后原子写入 `STORE_ROOT/manifest.json`，记录模型、snapshot revision、源文件清单和 expert
布局。后续运行只有在 manifest 与全部 expert 文件均通过校验后才复用该 store；有数据但没有
manifest 的历史目录会被拒绝，需人工核实来源后迁移或改用新目录。结束输出
`main_table_5090.json` 与终端主表。

---

## 4. 关键参数

| 参数 | 含义 | 建议 |
|---|---|---|
| `--hbm_budget` | 留给 expert 的 HBM(GB) | 5090 是 32GB，trunk+KV 约占 8–10GB，留 **22** |
| `--cpu_budget` | 留给 expert 的系统内存(GB) | 视机器，**40** 起；越大 CPU 命中越高 |
| `--alpha` | profiled Zipf α（编译器算 K_H/K_C 命中预估用） | Mixtral 实测偏均匀，默认 **1.0** |
| `--profile` | 传 `profile_real_moe.py` 产出（含 `per_layer_counts` 可选）按真实热度做静态放置 | 有则更优 |
| `--max_new_tokens` | decode token 数（影响 TPOT 统计稳定性） | 64–128 |
| `--cold_ssd / --warm_ssd` | SSD 是否真冷读（默认冷读 = 真实 NVMe 延迟） | 论文用 `--cold_ssd` |

---

## 5. 输出口径（可直接写进论文）

`main_table_5090.json.results[policy]`：
- `ttft_ms`：prefill 首 token 延迟（TTFT）
- `tpot_ms`：decode 每 token 延迟（TPOT / ITL）
- `tokens_per_s`：端到端吞吐
- `ppl`：WikiText-2 困惑度 —— 四策略均为 `exact(lossless)`，这正是卖点（**同精度更快**）
- `hit_pct`：HBM / CPU / SSD / CPU-compute 命中分布（ablation 佐证）
- `results.ours.speedup_vs`：OURS 相对各 baseline 的端到端吞吐加速

> 注：本框架报的是**端到端** TTFT/TPOT/tokens·s⁻¹（和 SOTA 同口径），
> 不再是子系统级取数延迟。子系统级 micro-benchmark（原 `real_tiered_cache.py`）降级为附录 ablation。

---

## 6. 注意事项 / 已知边界

- **架构兼容**：当前 `materialize_experts_to_ssd` 按 Mixtral 命名（`...block_sparse_moe.experts.{e}.w{1,2,3}.weight`）解析。
  换 Qwen-MoE/DeepSeek-MoE 需改 `_parse_expert_key` 与 MoE 块替换逻辑。
- **bf16 → fp16**：Mixtral 原权重 bf16，落盘按 fp16 存（numpy 无 bf16）。推理全程 fp16，相对 fp16 基线无损；
  若要严格 bf16，可把 `SSDExpertStore` 改为裸 bytes 存 bf16 并用 `torch.frombuffer`。
- **SSD 真冷读很慢**：`--cold_ssd` 下每次 miss 都强制 NVMe 读，decode 会偏慢——这是**有意为之**（反映真实 offloading 瓶颈，
  也正是 tiering 价值所在）。要看「缓存暖」上界可加 `--warm_ssd`。
- **磁盘**：`STORE_ROOT` 需 ~90GB 空闲，且建议在 NVMe 上（别放 tmpfs，否则测的是内存不是 SSD）。
