# 实验记录：FlashMoE 论文机制适配真实 Mixtral 路径预检

- **日期 / 执行者**：2026-07-18 · Codex
- **级别**：L2 主场景的最小预检（不作为正式性能证据）
- **目的**：验证 `flashmoe_rf_adaptation` 能在 A100、Mixtral、冷 SSD 三级路径完整运行
- **关联改动**：`58ee95a`（策略）、`2c1cc72`（launcher CLI 优先级）、`f82f869`（旧 store 迁移）、`6c3f4df`（uniform 透传）
- **本次引入的新维度**：`flashmoe_rf_adaptation`，已登记到 `EXPERIMENTS.md §7.1`

---

## 1. 环境

| 项 | 值 |
|----|----|
| 平台 id | `a100-80g` |
| 加速器 / 显存 | NVIDIA A100 80GB；观测峰值约 73.6GB |
| torch / CUDA | 见 run metadata / 环境快照 |
| store_root | `/data/qinzy/mecc_tmp/mixtral_store`，真实 `/data` 文件系统；约 85GB |

## 2. 配置

| 参数 | 值 |
|------|----|
| 模型 | `mistralai/Mixtral-8x7B-Instruct-v0.1` / mixtral |
| tier | L2：CPU 预算不足，SSD 被触发 |
| hbm_budget / cpu_budget | 30GB / 40GB |
| alpha | 1.0；`--uniform` |
| K_H / K_C | 每层 2 / 3 |
| prompt_len / max_new_tokens / n_prompts | 8 / 2 / 1 |
| 数据 | 内置 prompt；`--skip_ppl`，只记录 `exact(lossless)` 路径标记 |
| cold_ssd | true |
| 策略 | `flashmoe_rf_adaptation` |

## 3. 命令

```bash
python3 mecc_package/scripts/experiment_launcher.py run \
  flashmoe-rf-preflight3-20260718 \
  --config mecc_package/e2e/configs/l2_mixtral_main.json \
  --state-path /data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61 \
  --store-root /data/qinzy/mecc_tmp/mixtral_store \
  --hbm-budget 30 --cpu-budget 40 --prompt-len 8 \
  --max-new-tokens 2 --n-prompts 1 \
  --policies flashmoe_rf_adaptation --skip-ppl --uniform \
  --runs-root /data/qinzy/mecc_tmp/runs
```

产物：`/data/qinzy/mecc_tmp/runs/flashmoe-rf-preflight3-20260718/result.json`

## 4. 结果

| 策略 | TTFT(ms) | TPOT(ms) | tok/s | PPL | HBM/CPU/SSD% |
|------|---------:|---------:|------:|-----|--------------|
| `flashmoe_rf_adaptation` | 188163.48 | 52298.36 | 0.008317 | exact(lossless) | 17.5 / 35.1 / 47.4 |

作为后续实验设计参考，同配置的历史四策略预检中 OURS 为 0.00931 tok/s、SSD 33.6%；跨 run
派生比约 1.1194×，SSD 差 13.8 个百分点。该派生值不是同进程正式对比，禁止外引。

## 5. 成功判据核对

- [x] 成功 run 退出且原子结果 JSON 存在
- [x] Schema A 复核通过
- [x] fp16 路径保持 `exact(lossless)`
- [x] 三级命中合计 100%，SSD 路径被触发
- [ ] 只运行单策略，未覆盖全部 active 策略
- [ ] 仅 1 prompt / 2 token，无数值 PPL，不满足正式 L2 结论要求
- **判定**：路径预检 PASS；性能证据 FAIL（按设计不升级）

## 6. 结论

FlashMoE 论文机制适配可以在 MECC 的真实 Mixtral/A100/冷 SSD 路径完整运行。初步命中数据
支持开展同进程五策略 pilot，但当前结果不能写入论文主结论。

## 7. 异常与后续

| 现象 | 排查 | 处理 / 待办 |
|------|------|-------------|
| 第一次 run 联网找 snapshot 失败 | launcher 未传本地 `state_path` | 第二次显式绑定 revision `eba923…` |
| 第二次 run 拒绝旧 store | 旧 85GB store 无 manifest | 新增显式迁移工具，256 文件数量/大小验证后原子绑定 snapshot |
| config 覆盖 CLI | `apply_config` 无条件覆盖显式参数 | `2c1cc72` 修复为 CLI > config > built-in default |
| uniform 无法透传 | launcher 未暴露参数 | `6c3f4df` 增加并测试 `--uniform` |
| systemd 表面 success 与阶段失败可能不一致 | transient unit 状态不足以代表应用结果 | 必须同时检查 `status.json` 和原子 `result.json` |

## 8. 注册表维护确认

- [x] 新 baseline 已加入 `EXPERIMENTS.md §7.1`
- [x] 复现忠实度已登记 `RELATED_WORK_REPRO_AUDIT.md`
- [x] 未刷新 `§7.5` 正式基线快照
