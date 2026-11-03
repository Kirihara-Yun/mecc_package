# A100 显存溢出（OOM）恢复诊断汇总（2026-11-03）

本报告只收集**诊断证据**，不产出论文/PPT 性能结论，不用于任何加速/命中率主张。
本轮不重跑已失败的正式 50/40 GB 完整复现实验。

## 0. 执行环境与分支

- 干净 checkout：`/home/qinzy/mecc_a100_recovery`
  （`git clone --branch design/hpca-review-20261028`，`git merge-base --is-ancestor 1aa0140 HEAD` 通过，工作区纯净）
- 新结果分支：`gpu/a100-oom-recovery-20261103`，基线提交 `d1a7811`（含 `1aa0140`）
- 两次诊断运行 `run.json.git_commit` 均为 `d1a7811`（可定位）
- 存储：`/data` = `/dev/sdb`（ext4，`rw,relatime,stripe=64`，3.5T/可用 336G），详见 `a100-storage-audit-20261103/STORAGE_AUDIT.md`
- 模型：`/data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61`（19 分片）
- Store：`/data/mecc_store_mixtral`（manifest 可读，revision 匹配，256 expert `.bin`；运行时 `skip materialization`）
- GPU：A100 80GB PCIe，运行前空闲（1 MiB / 0 %，无计算进程）

## 1. 工作包 A 结果

### A1. 旧 L0 报告补齐（不重跑 L0）

- 旧 checkout（`/home/qinzy/mecc_package`，分支 `gpu/a100-20261103`）重新导出 `a100-l0-20261103-0846`：
  现含 `status.json`、`result.json`、`partial_result.json`、`run_tail.log`（2818 B，非空）、`report_manifest.json`。
- manifest 哈希与文件逐一匹配（`ALL_MATCH=True`），`included_tail_lines=10000`。
- 已仅提交该目录并推送：`c3d3627`（未纳入未跟踪的 `p1a-*`）。

### A3. 存储介质只读审计 → **unknown**

- `findmnt -T /data` → `/dev/sdb ext4 rw,relatime,stripe=64`
- `lsblk`：`sdb` MODEL=`MR9364-8i`，`ROTA=1`，TYPE=disk，3.5T，挂载 `/data`
- `/sys/block/sdb/queue/rotational = 1`；`vendor=AVAGO`，`model=MR9364-8i`
- 无 `/dev/nvme*`；`/proc/mdstat` 无 md RAID
- `storcli64`（`/opt/MegaRAID/storcli/storcli64`）只读 `show` → `Number of Controllers = 0`；`sudo -n` 需密码
- **结论：物理介质无法证明为 NVMe SSD，记 `unknown`。** `cold_ssd=true` 仅表示代码走冷读路径。
  未安装驱动、未改变 RAID 配置。

### A4. `p1a-*` 未跟踪报告清单（仅盘点，未合并/未改动）

| 目录 | result.json | run.json(git_commit) | 预算 (HBM/CPU) | k_h/k_c | 输入×token | 状态 |
|---|---|---|---|---|---|---|
| p1a-cpu20g-run1 | 有 | 无 | 30 / 20 GB | 2 / 1 | 4 × 16 | 完成（ours 1.276×，仅记录不引用）|
| p1a-cpu20g-run2 | 无 | 无 | 30 / 20 GB | 2 / 1 | 4 × 16 | 仅 run.log |
| p1a-cpu40g-run1 | 无 | 无 | 30 / 40 GB | 2 / 3 | 4 × 16 | 仅 run.log |
| p1a-cpu40g-run2 | 有 | 无 | 30 / 40 GB | 2 / 3 | 4 × 16 | 完成（ours 2.011×，仅记录不引用）|
| p1a-cpu60g-run1 | 无 | 无 | 30 / 60 GB | 2 / 5 | 4 × 16 | **OOM ~78 GiB** |
| p1a-cpu60g-run2 | 无 | 无 | 30 / 60 GB | 2 / 5 | 4 × 16 | **OOM ~78 GiB** |

说明：均无 `run.json`，因此无 `git_commit` 记录；`compiled_plan.hardware` 为历史串 `rtx5090`。
这些目录不属于本轮结果，等待本地审计。

## 2. 工作包 B 结果（三次冻结配置，仅 ours、skip_ppl、uniform、50/40 GB）

| 顺序 | 配置 | 输入×token | 状态 | 关键事实 |
|---|---|---|---|---|
| B1 | `diag_a100_50g_p1_t16.json` | 1 × 16 | **FAILED (OOM)** | PyTorch 已分配 **78.47 GiB**，剩余 4.75 MiB |
| B2 | `diag_a100_50g_p4_t2.json` | 4 × 2 | **COMPLETE** | TTFT 80991.85 ms，TPOT 17686.47 ms，0.020305 tok/s |
| B3 | `diag_a100_50g_p4_t16.json` | 4 × 16 | **NOT RUN** | 计划规定 B3 仅在 B1、B2 均完成时执行；B1 失败故不执行 |

### B1 失败堆栈（原始日志摘录）

```
File ".../mecc_package/e2e/mixtral_tiered.py", line 75, in forward
    for (_lid, expert_idx), expert_layer in self.experts.load_experts(
File ".../mecc_package/e2e/tiered_engine.py", line 351, in load_experts
    self.batch_prefetch(cpu_uids)
File ".../mecc_package/e2e/tiered_engine.py", line 326, in batch_prefetch
    gpu_ws = ws.to(self.device, non_blocking=True)
File ".../mecc_package/e2e/tiered_engine.py", line 62, in to
    self.w1.to(device, non_blocking=non_blocking),
torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 112.00 MiB.
GPU 0 has a total capacity of 79.25 GiB of which 4.75 MiB is free.
Including non-PyTorch memory, this process has 79.12 GiB memory in use.
Of the allocated memory 78.47 GiB is allocated by PyTorch ...
```

B2 未 OOM，正常完成（`phase=complete`，`ExecMainStatus=0`），可见 hit HBM/CPU/SSD = 32.9 / 47.2 / 19.9 %。

### 触发条件定位（仅触发条件，非根因）

- **1 输入 × 16 token → OOM**；**4 输入 × 2 token → 不 OOM**；此前 preflight **1 输入 × 2 token → 不 OOM**。
- 因此在本 harness 下，**OOM 由"解码步数/生成长度"驱动，而非并发请求数**。
  4 个请求各只有 2 个 decode 步时不触发；单请求 16 个 decode 步即触发。
- 失败位置始终在 `batch_prefetch` 的 GPU staging 拷贝（`ws.to(device)`），说明随 decode 步推进，
  HBM 中常驻/staging 占用持续增长，最终触及 79.25 GiB 物理上限。

### 混杂因素与证据不足（必须如实记录）

1. `skip_ppl=true` 时结果里的 `ppl="exact(lossless)"` 只是**当前代码的占位字符串，实际 PPL 未测**；
   不得当作质量/PPL 证据。
2. 内置 prompt 的**实际 tokenized 长度可能与 `prompt_len=64` 不同**，B1/B2 间存在该混杂因素。
3. 当前 harness **不记录逐 token 显存峰值 / staging 字节数**，故本报告只能定位"什么条件触发"，
   **不能证明根因**（无法区分 KV cache、预取暂存、缓存/镜像、请求间遗留，或其叠加）。
4. 本轮所有数字均为**诊断用**，不得进入论文/PPT，不作为正式 L2 结论。

## 3. 下一步需要本地开发补的计量（供本地参考）

- 逐 token / 逐 decode 步的 HBM 分配峰值与 `reserved/allocated` 曲线；
- `batch_prefetch` staging workspace 的实际字节数与生命周期（是否在步间释放）；
- KV cache 与 expert 缓存/镜像的显存占用分解；
- 实际字节 cap（而非仅参数预算）；
- 分相位（prefill / decode / PPL）计量与正确性校验。

## 4. 本轮结论

- 工作包 A：L0 报告已补齐并推送；干净 checkout 已建立；存储介质判定 `unknown`；`p1a-*` 已盘点未合并。
- 工作包 B：B1 FAILED(OOM 78.47 GiB)、B2 COMPLETE、B3 按门禁未运行。
- 诊断（触发条件）：**解码长度 16 步足以 OOM，4 请求 × 2 步不 OOM**；根因待本地补计量后确认。
- 到此停止：不运行 30/40 GB 正式主表、不跑 Insight 消融、不跑第二模型。
