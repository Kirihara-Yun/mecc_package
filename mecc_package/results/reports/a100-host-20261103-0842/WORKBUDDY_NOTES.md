# WorkBuddy Gate A — Host Audit Notes

- **结论**: PASS（资源齐备，可进入 Gate B；Gate C/D 存在已知 OOM 风险，见下）
- **执行时间**: 2026-11-03T08:42:15+08:00
- **host_report**: `a100-host-20261103-0842/host_report.json` (schema mecc-host-report-v1)

## 实际机器相关路径（与 WORKBUDDY 默认约定不同，已按“按服务器实际情况替换”处理）

- **模型实际路径 (state-path)**:
  `/data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61`
  - 默认约定 `/data/models/Mixtral-8x7B-Instruct-v0.1` **不存在**；模型以 HuggingFace `models--` 缓存布局落盘，snapshot 子目录含完整 19 个 `model-000xx-of-00019.safetensors` + `config.json` + tokenizer，可加载。
  - 该 snapshot 目录直接含 `*.safetensors`，满足 `materialize_experts_to_ssd` / `build_tiered_model` 的 `glob(state_path, "*.safetensors")` 要求；`store_manifest.source_identity` 可从 `snapshots/<hash>` 正确提取 revision。
- **store 实际路径 (store-root)**: `/data/mecc_store_mixtral`（已存在）
- **store 所在块设备/文件系统**: `/dev/sdb`（MR9364-8i RAID 呈现，lsblk `rota=true`，可能为 HDD 阵列而非纯 NVMe），ext4，挂载 `/data`。**本地块设备，非 tmpfs/NFS**，空闲 360 GB（≥120 GB 要求）。

## GPU

- 型号 `NVIDIA A100 80GB PCIe`，驱动 560.35.03，compute capability 8.0。
- `nvidia-smi` 显示 **memory.free=81153 MiB，utilization.gpu=0，无 compute-apps 占用** → GPU 空闲，独占可用。
- `CUDA_VISIBLE_DEVICES` 未设置（默认 device 0）。

## CPU 内存

- total ~1.08 TB，free 441 GB，**available ~1.05 TB** → 安全满足 40 GB expert budget + 运行余量。

## 依赖

- torch 2.5.1+cu121（cuda_available=True，cudnn 90100）、transformers 4.53.0、safetensors 0.4.5、numpy 1.26.4、accelerate 1.12.0 → 满足 L2 Mixtral 运行要求。

## user-systemd

- `systemctl --user is-system-running` → `running` → experiment_launcher 持久化可用。

## 异常 / 偏差（如实登记，不静默处理）

1. **工作区非空**：git `dirty=true`，存在历史未跟踪目录 `mecc_package/results/reports/p1a-cpu{20,40,60}g-run{1,2}/` 与 `p1a_driver.log`。WORKBUDDY 第 1 节要求“开始时工作区必须为空”，实际不符；这些为历史 p1a 实验产物，**按 AGENTS.md 硬约束不删除**，也不纳入本次 commit 范围。
2. **当前分支非 main**：本地在 `design/motivation-evidence-20261011`（HEAD `b46f0a4`）。历史已存在 `gpu/a100-20261010` 分支（本地+远程）。本次按当前 HEAD 建 `gpu/a100-20261103`，未执行 `git pull --ff-only origin main`（沙盒网络/远程同步存疑，且避免引入非受控变更）；报告 `git_commit` 以实际分支 HEAD 为准。
3. **HF cache 未设置**：`HF_HOME/HF_HUB_CACHE` 为空。模型以 `/data/qinzy/models/models--mistralai--...` 布局存在，运行 Gate C/D 时需设 `HF_HUB_CACHE=/data/qinzy/models`（或等价）以便 `AutoConfig.from_pretrained("mistralai/Mixtral-8x7B-Instruct-v0.1")` 离线解析；否则会尝试联网下载而失败。
4. **已知 OOM 风险（重要）**：git 历史显示 `gpu/a100-20261010` 分支的 `a100-mixtral-repro-50g-1-20261011-2148` 实验 **FAILED：OOM（PyTorch 78.47 GiB > A100-80g 80 GB 限制）**。WORKBUDDY Gate C（`l2_mixtral_preflight.json`）与 Gate D（`l2_mixtral_repro.json`）均冻结 **HBM 50 GB + CPU 40 GB** 预算，与历史 OOM 配置一致 → Gate C/D 有较高重现 OOM 概率。按文档纪律：**不静默调小预算/改精度/改策略**，若 OOM 将如实回传 FAILED。

## 预计下一步

- Gate B：CPU 回归（`run_cpu_checks.py`）+ L0 smoke（launcher dry-run→run→status→report）。
- Gate C：Mixtral L2 preflight（先 dry-run 校验命令/预算，再实跑；设 `HF_HUB_CACHE`；预计物化 ~90 GB store 耗时较长，可能 OOM）。
- Gate D：仅当 Gate C PASS 才执行；冻结 50/40 口径复现历史 Mixtral `ours,swapmoe`。

## 执行结果（Gate B / C / D，2026-11-03）

### Gate B — PASS
- `run_cpu_checks.py` 全 PASS（单元测试 + import 链 + 内部 L0 smoke：5 策略均 `exact(lossless)`，三级命中占比和≈100% 且 ssd>0）。
- launcher L0（`a100-l0-20261103-0846`）：`status=complete`，覆盖全部 5 个 active 策略，PPL 均无损；result `device=cuda`（smoke 模式在 GPU 可用时默认走 cuda，L0 仅验证逻辑故无碍）；`ours speedup 0.58×` 为随机模型无局部性正常现象，不写入结论。
- L0 报告已 commit + push（`4a38637`）。

### Gate C — PASS（preflight）
- run `a100-mixtral-preflight-20261103`：`phase=complete`，`ExecMainStatus=0`，无 OOM/NaN。
- `mode=real`、`platform=a100-80g`、`config.cold_ssd=true`；仅 `ours,swapmoe`；两者 PPL 均 `exact(lossless)`；store manifest 校验成功（**skip materialization**，store 已由历史实验物化于 `/data/mecc_store_mixtral`）。
- 指标：ours TTFT=84382.7ms TPOT=13322.83ms 0.02047 tok/s，hit HBM/CPU/SSD=27.3/56.2/16.5；swapmoe TTFT=121214.9ms TPOT=54473.06ms 0.011384 tok/s，hit=40.9/20.6/38.5。**OURS SSD 命中 16.5% < swapmoe 38.5%**（主战场压冷读证据，与历史 17.6% vs 34.5% 一致）。
- 注：preflight 仅 2 token，1.798× 不应入论文（文档明确"预检数据不进入论文"）。报告已 commit + push（`c204495`）。

### Gate D — FAILED（repro，OOM 78.47 GiB）
- run `a100-mixtral-repro-20261103`：`phase=failed`，`error_type=OutOfMemoryError`。
- 错误：`CUDA out of memory ... 78.47 GiB is allocated by PyTorch`（GPU 0 总 79.25 GiB）。**该数字与历史 `a100-mixtral-repro-50g-1-20261011-2148` 的 OOM（78.47 GiB）完全一致** → 历史失败被如实复现。
- 关键洞察：Gate C preflight（max_new_tokens=2, n_prompts=1, skip_ppl=true）在 50/40 下**不 OOM**，而 Gate D repro（max_new_tokens=16, n_prompts=4, skip_ppl=false）**OOM**。区别在生成长度/激活峰值与 PPL 测量，而非单纯 expert 预算 → 50/40 冻结口径在 A100-80g 上对"16-token 生成"不成立。
- 按 WORKBUDDY 纪律：**未静默改预算/精度/策略/prompt**，如实回传 FAILED，不重跑。报告（含 status.json failed + run.log OOM）已导出、commit，待 push。

## 偏差与新增风险（更新）
1. **wikitext 不可达**：Gate D `skip_ppl=false` 尝试下载 WikiText-2 失败（`Connection reset by peer`），回退 `builtin prompts` 测 PPL。因此 D 的 PPL 口径与历史 wikitext PPL（24.57 fp16）不一致；若后续复现 PPL，需以 PROVENANCE 规范谨慎引用，或预先离线备好 wikitext。C 因 `skip_ppl=true` 不受影响。
2. **HF_HUB_CACHE 注入**：launcher 经 `systemd-run --user` 启动的 unit 不继承 shell env；已用 `systemctl --user set-environment HF_HUB_CACHE=/data/qinzy/models` 使模型离线可解析（已验证 `AutoConfig.from_pretrained(..., local_files_only=True)` 成功，layers=32, experts=8）。
3. 其余 Gate A 已登记的偏差（默认 state-path 不存在、工作区非空、未从 main pull、store 已物化于 HDD/RAID `rota=true`）仍然成立。
