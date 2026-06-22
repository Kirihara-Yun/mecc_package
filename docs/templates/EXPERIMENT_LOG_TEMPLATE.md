<!--
  实验记录模板 —— 每次跑实验后复制本文件填写，存到 mecc_package/results/logs/
  命名规范：YYYYMMDD_<level>_<model>_<简述>.md
  例如：20260622_L0_smoke_verify-zero-copy-evict.md
        20260622_L2_mixtral_repro-main-table.md
  填写规范见 ../EXPERIMENTS.md §5（SOP）与 §7（注册表）。
  本模板按"不写死"设计：策略行 / 指标列 / 平台 / 数据集都按本次实际用到的来填，
  数量不固定——以 EXPERIMENTS.md §7 注册表为准追加，不要被下面的示例行限制。
  保留所有标题；不适用的项写 N/A，不要删。
-->

# 实验记录：<一句话标题>

- **日期 / 执行者**：YYYY-MM-DD ·（人 / agent 名）
- **级别**：L0 冒烟 / L1 对照 / L2 主实验 / 消融（**只能选一个**；语义见 EXPERIMENTS.md §0）
- **目的**：<为什么跑这次>
- **关联改动**：<commit / PR / 改了哪些文件；无则 N/A>
- **本次引入的新维度**：<若新增了 baseline/benchmark/平台/模型，列出并确认已在 EXPERIMENTS.md §7 登记；无则 N/A>

---

## 1. 环境（平台引用 §7.3，不写死型号）

| 项 | 值 |
|----|----|
| 平台 id（§7.3） | <如 a100-80g / rtx5090 / cpu-local / 新平台> |
| 加速器 / 显存 | <实际> |
| torch / CUDA | <版本> |
| store_root | <路径>（真实 NVMe? tmpfs? `df -h` 余量?） |

## 2. 配置（与命令一致）

| 参数 | 值 |
|------|----|
| 模型 repo / model_type（§7.4） | |
| 默认 tier 判定（装得下=L1 / 落SSD=L2） | |
| hbm_budget / cpu_budget (GB) | |
| alpha | |
| 编译产出 K_H / K_C | |
| prompt_len / max_new_tokens / n_prompts | |
| 数据集 / benchmark（§7.2 中本次采集的） | <如 wikitext-PPL / MMLU / 自定义吞吐集> |
| cold_ssd | true / false |
| 参与对比的策略（§7.1） | <本次实际跑的 baseline id 列表> |

## 3. 命令（可复制复现）

```bash
<把实际执行的完整命令粘这里，含所有占位的真实取值>
```

产出文件：`<out json 路径>`

## 4. 结果（行=策略，列=指标，二者都按本次实际用到的来；不固定四策略/单指标）

> 列头从 EXPERIMENTS.md §7.2 中本级别"必采 + 本次额外采集"的指标实例化；
> 行从 §7.1 中本次参与的策略实例化。新增的 baseline/benchmark 直接加行/加列。

| 策略\指标 | ttft_ms | tpot_ms | tok/s | ppl | HBM/CPU/SSD% | <新增指标…> |
|-----------|---------|---------|-------|-----|--------------|-------------|
| ours | | | | | | |
| <baseline-2> | | | | | | |
| <baseline-3> | | | | | | |
| … | | | | | | |

- **OURS speedup_vs**：<逐个 baseline 列：vs <id> __×；条数随参与的 baseline 增减>
- **关键观察**：<如 SSD 命中 ours vs 换页类 baseline；无损 vs 有损质量差>

## 5. 成功判据核对（对照 EXPERIMENTS.md 对应级别，语义级）

- [ ] 退出码 0，无 traceback
- [ ] **覆盖 §7.1 全部 active 策略**（不是固定四个）、§7.2 本级别必采指标完整
- [ ] PPL/质量符合预期（L0/L1：lossless 一致；L2：ours 无损、有损 baseline 明显更差，阈值见 §7.5 同模型快照）
- [ ] 三级命中合理（L0：ssd>0 且三级≈100%；L2：ours SSD 命中显著低于换页类 baseline）
- [ ] （L2）speedup 与 §7.5 同模型快照同量级
- **判定**：PASS / FAIL

## 6. 结论（严守口径）

> - **L0** 只写：链路 PASS/FAIL，**不写性能结论**。
> - **L1** 只写：算法结构性上界，**非主战场证据**。
> - **L2** 才可写：有效性 / 加速 / 无损优势（数字以 results/raw 为准）。

<结论正文>

## 7. 异常与后续（失败排查记录）

| 现象 | 排查 | 处理 / 待办 |
|------|------|-------------|
| | | |

## 8. 注册表维护确认（如本次有新维度）

- [ ] 新 baseline 已加入 EXPERIMENTS.md §7.1 并标 status
- [ ] 新 benchmark/指标已加入 §7.2 并标各级别是否必采
- [ ] 新平台已加入 §7.3
- [ ] 新模型已加入 §7.4 并标 tier
- [ ] 若刷新了参考数字，已更新 §7.5 基线快照并附 results/raw 来源
