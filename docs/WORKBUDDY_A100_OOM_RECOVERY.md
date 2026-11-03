# WorkBuddy A100 下一轮：补证与显存溢出定位（2026-11-03）

这是 **`9285838` 结果之后的新任务**。先读根目录 `AGENTS.md`、`WORKBUDDY.md`、`docs/WORKBUDDY_A100_RUNBOOK.md`、`docs/EXPERIMENTS.md` 和 `docs/PROVENANCE.md`。本任务只收集诊断证据；**不产出论文/PPT 性能柱高**。不要再原样重跑已两次 OOM 的 50/40 GB 完整复现实验。

## 已确认的起点

- 2026-11-03 的 50/40 GB 最小预检（1 prompt、2 token、跳过 PPL）完成；这个结果不是正式速度或质量证据。
- 50/40 GB、4 prompt、16 token 的运行在第一个 `ours` 策略的 decode 前向中、`tiered_engine.py:batch_prefetch()` 搬运专家时 OOM。它尚未运行到 PPL；不能把 PPL 称为已定位的原因。错误报告 PyTorch 已分配 78.47 GiB。这仍不足以判断是 KV、预取暂存、缓存/镜像、请求间遗留，还是它们叠加。
- 新 L0 的远端 `status.json` 显示完成，但已推送的报告缺 `result.json`，`run_tail.log` 为 0 字节。需要重新导出完成证据，不必重跑 L0。
- `/data` 显示为 `/dev/sdb`、RAID 控制器 `MR9364-8i`、`rota=true`。当前不能证明盘内物理介质是 NVMe SSD；`cold_ssd=true` 仅表示代码走冷读路径。
- 上轮结果分支从旧提交 `b46f0a4` 建立，不包含本地设计分支的交接说明 `1aa0140`。不要合并结果分支回设计分支：它与设计分支有无关的文档/数据删除差异。

## 工作包 A：无 GPU，先完成

1. **补齐旧 L0 报告。** 在原运行目录所在的旧 checkout 执行：

   ```bash
   python3 mecc_package/scripts/experiment_launcher.py report a100-l0-20261103-0846 --tail-lines 10000
   ```

   确认 `mecc_package/results/reports/a100-l0-20261103-0846/` 里同时有 `status.json`、`result.json`、非空 `run_tail.log`，且 manifest 中哈希与文件匹配。若原始 `run.log` 仍为空，按事实记录为 `log unavailable`，不要伪造。仅把这个目录的补充文件提交到原 `gpu/a100-20261103` 分支并推送；不要纳入未跟踪的 `p1a-*` 目录。

2. **建立干净的新执行 checkout。** 保留旧工作区和全部历史报告。另建一个目录，从设计分支最新提交创建新结果分支：

   ```bash
   git clone --branch design/hpca-review-20261028 https://github.com/Kirihara-Yun/mecc_package.git /home/qinzy/mecc_a100_recovery
   cd /home/qinzy/mecc_a100_recovery
   git merge-base --is-ancestor 1aa0140 HEAD
   git status --porcelain
   git switch -c gpu/a100-oom-recovery-20261103
   ```

   第二行检查失败、工作区不干净、或 GitHub 不可达时，报告 `BLOCKED` 并停止；不要继续用旧提交运行。每次实验的 `run.json.git_commit` 必须可定位到此新分支的运行前提交。

3. **只读核实存储介质。** 记录 `findmnt -T /data`、`lsblk -o NAME,PATH,MODEL,ROTA,TYPE,SIZE,MOUNTPOINTS`、控制器可用的只读介质信息。若有 `storcli`/`perccli`，使用只读 `show` 查询物理盘型号和介质；没有权限或工具则写 `unknown`，不安装驱动、不改变 RAID 配置。把命令、输出和判断保存到 `mecc_package/results/reports/a100-storage-audit-20261103/STORAGE_AUDIT.md`。存储未确认之前，后续运行仅用于**显存诊断**，不写“NVMe SSD 性能”。

4. **检查 `p1a-*` 未跟踪报告。** 只列目录名称、已有 `run.json`/`result.json`/日志和 commit/预算，不把它们混入本轮结果；若它们是完整实验，另写清单等待本地审计。不得删除或补写虚构结果。

## 工作包 B：最多三次 A100 诊断运行

只有 GPU 空闲、单卡独占、模型路径和 store manifest 可读时才做。使用仓库中三个**冻结配置**，均为 50 GB expert HBM、40 GB expert CPU、`ours`、内置固定输入、`skip_ppl=true`、`uniform=true`、同一模型与 store。`skip_ppl=true` 时结果中的 `ppl="exact(lossless)"` 是当前代码的占位字符串，**实际 PPL 未测**。

| 运行顺序 | 配置 | 目的 |
|---|---|---|
| B1 | `diag_a100_50g_p1_t16.json` | 1 个输入、16 token：单请求增长是否足以 OOM？ |
| B2 | `diag_a100_50g_p4_t2.json` | 4 个输入、2 token：多请求循环是否足以 OOM？ |
| B3 | `diag_a100_50g_p4_t16.json` | 只有 B1/B2 都完成才执行；检查两者组合，且排除 PPL 路径 |

每项均先 `--dry-run`，检查命令后再启动；将下列模板中的 `<ID>`、`<CONFIG>`、模型快照路径替换为该项固定值：

```bash
python3 mecc_package/scripts/experiment_launcher.py run <ID> \
  --config mecc_package/e2e/configs/<CONFIG> \
  --state-path /data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61 \
  --store-root /data/mecc_store_mixtral --gpu 0 --dry-run
python3 mecc_package/scripts/experiment_launcher.py run <ID> \
  --config mecc_package/e2e/configs/<CONFIG> \
  --state-path /data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61 \
  --store-root /data/mecc_store_mixtral --gpu 0
```

等待每项状态成为 `complete` 或 `failed` 后，再执行 `report <ID> --tail-lines 10000`。检查报告的最终状态、原始日志、模型 revision、配置指纹和 GPU 进程。**B1 或 B2 OOM 时仍可执行另一项，以区分长度与请求数；B3 只在前两项均完成时执行。** B1/B2 是事先冻结的两个独立诊断臂；仅在此处覆盖旧 runbook 的“一个 gate 失败就停止”规则。这不是“失败后调参重跑”。若 GPU 中途被他人占用，立即停止后续项并报告。不得改成 30/40 GB、减少生成长度或换 prompt 后沿用同一实验 ID。

不比较这些诊断项的速度或命中率，不称它们为正式 L2 结论。内置 prompt 的实际 tokenized 长度可能不同；在总结中如实写出这一混杂因素。当前 harness 不记录逐 token 显存峰值，因此 B1/B2/B3 最多定位触发条件，**不能直接证明根因**。

## 工作包 C：回传与停止点

在新分支提交各诊断项的紧凑报告和 `mecc_package/results/reports/a100-oom-recovery-20261103/RECOVERY_SUMMARY.md`。总结至少有：B1/B2/B3 的 `complete/failed/not run`、是否 OOM、失败堆栈、存储介质结论或 `unknown`、旧 L0 是否补齐、`p1a-*` 清单、下一步需要本地开发补的计量代码。推送新结果分支，回复 `branch / commit / run_id / PASS|BLOCKED / 一句话原因`。

**到此停止。** 暂不运行 30/40 GB 正式主表、三项 Insight 消融或第二模型。下一轮由本地先补逐 token 显存/暂存、实际字节 cap、正确性与分相位计量，再给 WorkBuddy 单独的正式实验配置。所有失败和不利结果照实回传。
