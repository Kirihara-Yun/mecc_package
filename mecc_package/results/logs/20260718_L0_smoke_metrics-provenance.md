# 实验记录：评测精度与溯源元数据回归冒烟

- **日期 / 执行者**：2026-07-18 · Codex
- **级别**：L0 冒烟
- **目的**：验证吞吐精度、派生 speedup、平台和带时区运行时间字段的改动未破坏端到端逻辑链路。
- **关联改动**：`mecc_package/e2e/run_e2e.py`、`mecc_package/e2e/test_run_e2e_metrics.py`
- **本次引入的新维度**：N/A

---

## 1. 环境（平台引用 §7.3，不写死型号）

| 项 | 值 |
|----|----|
| 平台 id（§7.3） | `cpu-local` |
| 加速器 / 显存 | CPU / N/A |
| torch / CUDA | torch 2.5.1+cu121 / CUDA 当前会话不可用 |
| store_root | `/tmp/mecc_store_continue`（L0 临时 store；根文件系统运行时约 6.9GB 可用） |

## 2. 配置（与命令一致）

| 参数 | 值 |
|------|----|
| 模型 repo / model_type（§7.4） | `smoke-tiny-moe` |
| 默认 tier 判定（装得下=L1 / 落SSD=L2） | N/A（L0 人工小预算强制触发三级路径） |
| hbm_budget / cpu_budget (GB) | smoke 内置预算 |
| alpha | 1.0 |
| 编译产出 K_H / K_C | 2 / 3 |
| prompt_len / max_new_tokens / n_prompts | 8 / 6 / 4 |
| 数据集 / benchmark（§7.2 中本次采集的） | 随机 gate 的 L0 链路指标 |
| cold_ssd | true |
| 参与对比的策略（§7.1） | `ours,swapmoe,fiddler,naive` |

## 3. 命令（可复制复现）

```bash
cd mecc_package/e2e
python3 run_e2e.py --smoke --n_prompts 4 \
  --store_root /tmp/mecc_store_continue \
  --out /tmp/mecc_smoke_continue.json
```

产出文件：`/tmp/mecc_smoke_continue.json`（临时验证产物，不作为论文证据）

## 4. 结果（行=策略，列=指标，二者都按本次实际用到的来；不固定四策略/单指标）

| 策略\指标 | ttft_ms | tpot_ms | tok/s | ppl | HBM/CPU/SSD% |
|-----------|---------|---------|-------|-----|--------------|
| ours | 1031.33 | 1137.63 | 1.008734 | exact(lossless) | 0.6 / 1.9 / 97.4 |
| swapmoe | 733.66 | 624.17 | 1.580521 | exact(lossless) | 0.6 / 37.2 / 62.1 |
| fiddler | 639.63 | 646.12 | 1.558711 | exact(lossless) | 24.5 / 0.0 / 74.6 |
| naive | 596.05 | 534.35 | 1.867771 | exact(lossless) | 25.4 / 0.0 / 74.6 |

- **OURS speedup_vs**：N/A；L0 派生值仅用于字段回归检查，禁止作为性能结果引用。
- **关键观察**：四个策略均走到 SSD 路径，三级命中率因一位小数舍入约等于 100%，所有策略均为 exact(lossless)。输出包含 `platform=CPU` 与带时区 `run_time`，吞吐保留 6 位小数。

## 5. 成功判据核对（对照 EXPERIMENTS.md 对应级别，语义级）

- [x] 退出码 0，无 traceback
- [x] 覆盖 §7.1 全部 active 策略、§7.2 本级别必采指标完整
- [x] PPL/质量符合预期：所有策略 lossless 一致
- [x] 三级命中合理：各策略 SSD 命中大于 0，三级合计约 100%
- [ ] （L2）speedup 与 §7.5 同模型快照同量级（N/A）
- **判定**：PASS

## 6. 结论（严守口径）

L0 端到端逻辑链路通过；吞吐精度和溯源元数据改动按预期落盘。本次随机微型 CPU smoke 不提供任何性能或加速证据。

## 7. 异常与后续（失败排查记录）

| 现象 | 排查 | 处理 / 待办 |
|------|------|-------------|
| pytest 启动时第三方 `langsmith` 插件与本机 pydantic 冲突 | 冲突发生在项目测试收集前 | 设置 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` 后，项目 7 项测试全部通过 |
| 当前执行会话不可访问 CUDA，磁盘仅约 6.9GB 可用 | `check_env.py` 与 `df -h /tmp` | 不启动 L2；待 GPU 透传且 NVMe 空间满足后复现 |

## 8. 注册表维护确认（如本次有新维度）

- [x] 本次无新 baseline
- [x] 本次无新 benchmark/指标
- [x] 本次无新平台
- [x] 本次无新模型
- [x] 本次未刷新参考数字
