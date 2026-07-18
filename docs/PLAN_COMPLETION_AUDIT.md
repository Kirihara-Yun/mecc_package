# MECC 路线图完成度审计

> 审计日期：2026-07-18
> 权威计划：`docs/PROJECT_TAKEOVER_PLAN.md`
> 原则：只有直接证据通过才记完成；L0、D1 或推断不替代 L2。

## 1. 阶段结论

| 阶段 | 状态 | 直接证据 | 未完成门禁 |
|------|------|----------|------------|
| P0 基线冻结 | 本地工作完成，待快照提交 | `CONSISTENCY_AUDIT.md`；`verify_claims.py` 30 OK/0 FAIL；config fingerprint | 需提交当前受控改动；X1/X6 只能保持 unverified |
| P1 可复现实验 | 完成 | launcher、显式 configs、store manifest、阶段状态、Schema A 原子写、共同 trace、`run_cpu_checks.py` | 尚未在新的正式 L2 作业上演练故障恢复；不影响 CPU 逻辑验收 |
| P2 核心 claim | 部分完成 | baseline 命名拆分与共同 trace；TH-004 proven；TH-005/006 refuted | 五项核心消融缺正式 L2 JSON/log；更强 baseline 未完成外部版本核验 |
| P3 性能优化 | parked | `async_ssd_read` futures/屏障测试与 L0 | 无正式 L2 单变量消融，不能 adopted；后续候选未启动 |
| P4 论文收敛 | 部分完成 | 原稿删除 X1；DeepSeek=L1；自动 Mixtral 主表；claim scanner 通过 | 外部引用 TODO；无 TeX 引擎渲染；无新 L2/消融证据；不能打投稿 tag |

## 2. 第一批执行清单

`PROJECT_TAKEOVER_PLAN.md §13` 的 1--10 项均已产生对应代码、测试或诚实状态：

1. 口径审计：`CONSISTENCY_AUDIT.md`；
2. README/PROVENANCE 叙事修复：高风险扫描通过；
3. 文本 claim 检查：`verify_claims.py:_text_claim_violations`；
4. 持久 launcher：`experiment_launcher.py`；
5. store manifest：`e2e/store_manifest.py`；
6. schema/原子结果：`e2e/result_schema.py`；
7. 双实现共同 trace：`e2e/test_cache_consistency.py`；
8. baseline 拆名：`swapmoe_fp16` 与 inactive `swapmoe_quantized`；
9. TH-006 反例：`search_th006_counterexample.py`；
10. `async_ssd_read`：已实现、无 L2，按规范标 `parked`。

## 3. 当前可复现验证

```bash
python3 mecc_package/scripts/run_cpu_checks.py
```

该入口覆盖 26 项 CPU 测试、三条受保护 import 链、论文自动表、claim 一致性与 L0。
L0 输出中的 tok/s 只证明逻辑，不作为优化或论文性能证据。

## 4. 不可伪完成的外部依赖

1. 用户已取消正式 L2 复现，因此不能生成核心消融或 `async_ssd_read` 的 adopted 证据；
2. 当前外部检索网络失败，论文中未核实条目保留 `[TODO: verify cite]`；
3. 当前环境没有 TeX 引擎，无法证明投稿 PDF 可构建；
4. X1/X6 缺原始命令/revision，除非取得外部记录或重建独立 baseline，否则保持 unverified。

这些项目只在相应外部状态改变后继续，不用历史舍入值、L0 或模拟器替代。
