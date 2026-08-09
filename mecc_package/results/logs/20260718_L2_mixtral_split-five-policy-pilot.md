# 实验记录：Mixtral 五策略短 pilot 中止与 FlashMoE 补跑

- **日期 / 执行者**：2026-07-18 · Codex
- **级别**：L2 主场景短 pilot（不作为正式性能证据）
- **目的**：在 A100 / Mixtral / 冷 SSD 路径上预演五策略对比；按用户指示跳过很慢的 `naive`，并只补跑尚未完成的 FlashMoE 策略
- **关联改动**：N/A（本记录只登记实验执行状态）
- **本次引入的新维度**：N/A

---

## 1. 环境

| 项 | 值 |
|----|----|
| 平台 id | `a100-80g` |
| 加速器 / 显存 | NVIDIA A100 80GB；FlashMoE-only run 中观测到 GPU 进程运行 |
| torch / CUDA | 见 run log / 环境快照 |
| store_root | `/data/qinzy/mecc_tmp/mixtral_store`，真实 `/data` 文件系统；manifest 已验证并跳过重复 materialization |

## 2. 配置

| 参数 | 值 |
|------|----|
| 模型 repo / model_type | `mistralai/Mixtral-8x7B-Instruct-v0.1` / `mixtral` |
| 默认 tier 判定 | L2：CPU 预算不足，SSD 被触发 |
| hbm_budget / cpu_budget (GB) | 30 / 40 |
| alpha | 1.0；`--uniform` |
| 编译产出 K_H / K_C | 每层 2 / 3 |
| prompt_len / max_new_tokens / n_prompts | 8 / 8 / 1 |
| 数据集 / benchmark | 内置短 prompt；`--skip_ppl`，只记录 `exact(lossless)` 路径标记 |
| cold_ssd | true |
| 参与对比的策略 | 原计划：`ours,swapmoe,fiddler,naive,flashmoe_rf_adaptation`；实际完整落盘：`flashmoe_rf_adaptation` 单策略 |

## 3. 命令

原五策略 pilot：

```bash
python3 mecc_package/scripts/experiment_launcher.py run \
  five-policy-pilot-20260718 \
  --config mecc_package/e2e/configs/l2_mixtral_main.json \
  --state-path /data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61 \
  --store-root /data/qinzy/mecc_tmp/mixtral_store \
  --hbm-budget 30 --cpu-budget 40 --prompt-len 8 \
  --max-new-tokens 8 --n-prompts 1 \
  --policies ours,swapmoe,fiddler,naive,flashmoe_rf_adaptation \
  --skip-ppl --uniform \
  --runs-root /data/qinzy/mecc_tmp/runs
```

用户指示 `naive` 很慢、可以不用测后停止：

```bash
python3 mecc_package/scripts/experiment_launcher.py stop five-policy-pilot-20260718
```

FlashMoE-only 补跑：

```bash
python3 mecc_package/scripts/experiment_launcher.py run \
  flashmoe-only-pilot-20260718 \
  --config mecc_package/e2e/configs/l2_mixtral_main.json \
  --state-path /data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61 \
  --store-root /data/qinzy/mecc_tmp/mixtral_store \
  --hbm-budget 30 --cpu-budget 40 --prompt-len 8 \
  --max-new-tokens 8 --n-prompts 1 \
  --policies flashmoe_rf_adaptation \
  --skip-ppl --uniform \
  --runs-root /data/qinzy/mecc_tmp/runs
```

产出文件：`/data/qinzy/mecc_tmp/runs/flashmoe-only-pilot-20260718/result.json`

## 4. 结果

| 策略\指标 | ttft_ms | tpot_ms | tok/s | ppl | HBM/CPU/SSD% |
|-----------|--------:|--------:|------:|-----|--------------|
| `flashmoe_rf_adaptation` | 113698.24 | 16770.88 | 0.034618 | exact(lossless) | 35.1 / 37.4 / 27.5 |

- **OURS speedup_vs**：N/A，本次没有同一原子主表中的对照策略结果
- **关键观察**：原五策略 pilot 在 `naive` 阶段被停止；`ours`、`swapmoe`、`fiddler` 仅在 `status.json` 中显示阶段完成，但 harness 只在全部策略完成后发布最终 `result.json`，因此这些阶段不能作为可引用数字表使用

## 5. 成功判据核对

- [x] FlashMoE-only run 退出码 0，原子 `result.json` 存在
- [x] Schema A 复核通过
- [x] PPL/质量为 `exact(lossless)` 路径标记
- [x] 三级命中合计 100%，SSD 路径被触发
- [ ] 未覆盖全部 active 策略；`naive` 按用户指示跳过
- [ ] 仅 1 prompt / 8 tokens，且 `--skip_ppl`，不满足正式 L2 结论要求
- **判定**：FlashMoE 路径 pilot PASS；正式性能证据 FAIL（按设计不升级）

## 6. 结论

FlashMoE 论文机制适配在 Mixtral / A100 / 冷 SSD 路径上可以完整跑通，并产生合规 Schema A JSON。
本次不能与已中止五策略作业中已完成阶段拼成正式对比，因为那些阶段没有最终原子主表。后续正式对比应跳过 `naive` 或先实现逐策略 checkpoint，再重新运行同配置的 active 策略集合。

## 7. 异常与后续

| 现象 | 排查 | 处理 / 待办 |
|------|------|-------------|
| `naive` 阶段运行过慢 | `five-policy-pilot-20260718/status.json` 停在 `policy=naive`，已完成策略为 `ours,swapmoe,fiddler` | 按用户指示停止该服务，不再测 `naive` |
| 已完成阶段无可引用数值 | 当前 harness 完成全部策略后才原子发布 `result.json` | 不重跑已完成阶段；记录为阶段完成但无主表数字 |
| FlashMoE 未包含在原五策略最终表 | 原作业在到达 FlashMoE 前停止 | 单独补跑 `flashmoe_rf_adaptation`，只作为路径 pilot |

## 8. 注册表维护确认

- [x] 未新增 baseline / benchmark / 平台 / 模型
- [x] 未刷新 `EXPERIMENTS.md §7.5` 正式基线快照
- [x] 未将本 pilot 写入论文主结论或正式 L2 证据
