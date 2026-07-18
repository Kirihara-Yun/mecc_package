# MECC 路线图完成度审计

> 审计日期：2026-07-18
> 权威计划：`docs/PROJECT_TAKEOVER_PLAN.md`
> 原则：只有直接证据通过才记完成；L0、D1 或推断不替代 L2。

## 1. 阶段结论

| 阶段 | 状态 | 直接证据 | 未完成门禁 |
|------|------|----------|------------|
| P0 基线冻结 | 完成 | `CONSISTENCY_AUDIT.md`；`verify_claims.py` 30 OK/0 FAIL；config fingerprint；事实快照 `bffe489` | X1/X6 只能保持 unverified，不影响已核事实冻结 |
| P1 可复现实验 | 完成 | launcher、显式 configs、store manifest、阶段状态、Schema A 原子写、共同 trace、`run_cpu_checks.py` | 尚未在新的正式 L2 作业上演练故障恢复；不影响 CPU 逻辑验收 |
| P2 核心 claim | 部分完成 | baseline 命名拆分与共同 trace；TH-004 proven；TH-005/006 refuted | 五项核心消融缺正式 L2 JSON/log；更强 baseline 未完成外部版本核验 |
| P3 性能优化 | parked | `async_ssd_read` futures/屏障测试与 L0 | 无正式 L2 单变量消融，不能 adopted；后续候选未启动 |
| P4 论文收敛 | 部分完成 | 原稿删除 X1；DeepSeek=L1；自动 Mixtral 主表；claim scanner 通过；引用主来源见 `CITATION_AUDIT.md`；XeLaTeX 容器两遍构建通过 | 无新 L2/消融证据；不能打投稿 tag |

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

该入口覆盖 37 项 CPU 测试、三条受保护 import 链、论文自动表、TeX 静态结构、claim 一致性与 L0。
L0 输出中的 tok/s 只证明逻辑，不作为优化或论文性能证据。

## 4. 不可伪完成的外部依赖

1. 用户已取消正式 L2 复现，因此不能生成核心消融或 `async_ssd_read` 的 adopted 证据；
2. 当前正文引用已由主来源核验；若新增文献，仍须先更新 `CITATION_AUDIT.md`；
3. X1/X6 缺原始命令/revision，除非取得外部记录或重建独立 baseline，否则保持 unverified。

这些项目只在相应外部状态改变后继续，不用历史舍入值、L0 或模拟器替代。

## 5. 论文构建证据

2026-07-18 使用 `ubuntu:24.04` 临时容器安装 TeX Live 2023 的
`texlive-xetex texlive-lang-chinese texlive-science`，在只读挂载的 `paper/` 源码上连续运行
两遍 `xelatex -interaction=nonstopmode -halt-on-error mecc_paper.tex`。第二遍退出码为 0，产出
10 页 PDF；引用与交叉引用均已解析。构建同时促成以下源文件修复：Markdown 反引号导致的
下划线数学模式错误、损坏字符“名��”、裸 `μ` 字形缺失与错误的 `\~1000` 写法。

日志仍含 Fandol 字体 Script 元数据、含数学符号的 PDF bookmark、两个 overfull box 与 float
位置调整警告；这些不阻止 PDF 生成，但投稿模板排版阶段仍应清理。验证产物只保存在
`/tmp/mecc_paper_verified.pdf`，不把派生 PDF 或辅助文件混入证据提交。

## 6. 未跟踪用户文件分类（只登记，不删除）

| 文件 | 分类 | 当前裁决 |
|------|------|----------|
| `e2e/bench_moe_infinity.py` | 外部 baseline 草稿 | 缺版本锁定、公平预算、PPL、平台/时间与 Schema A；已在 EXPERIMENTS 注册为 inactive，不运行、不引用 |
| `results/l2_preflight_20260718.json` | 单策略最小 L2 预检 | 仅 `ours`、1 prompt/2 tokens、`exact(lossless)` 路径标记；不等同于后续四策略 `/data` 预检，不作论文或优化证据 |
| `paper/MIDTERM_REPORT.md`、`paper/build_ppt.py`、两份 PPTX | 用户汇报材料 | 保留原样；其中可能含旧 X1/X6/理论口吻，未纳入投稿事实快照 |

上述文件仍保持未跟踪，避免在没有用户明确选择的情况下把历史草稿混入受控证据提交。
