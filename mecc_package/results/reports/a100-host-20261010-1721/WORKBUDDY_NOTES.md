# WorkBuddy Host Audit Notes — a100-host-20261010-1721

**branch**: gpu/a100-20261010
**commit**: 613a517ead87eabb1d9bfc17e6aa4a8203747af8
**collected_at**: see host_report.json

## 结论：PASS（全部 Gate 0 检查通过，可进入 Gate B → C → D）

| Gate 0 检查项 | 结果 |
|--------------|------|
| 是 A100 80GB | ✅ `NVIDIA A100 80GB PCIe`，driver 560.35.03，CUDA 12.6 |
| GPU 空闲（无其他作业） | ✅ 81153 / 81920 MiB free，无 compute 进程，util 0% |
| `systemd --user` 可用 | ✅ `running` |
| CPU 内存足以提供 40GB expert budget | ✅ 1007.5 GiB total / 980 GiB avail |
| STORE_ROOT 本地块设备、非 tmpfs/NFS、空闲≥120GB | ✅ `/data/mecc_store_mixtral` → 块设备 `/dev/sdb`，ext4，本地盘；空闲 330.7 GiB |
| **模型目录可读 / revision 明确 / safetensors 完整** | ✅ PASS（`/data/qinzy/models/.../snapshots/eba92302...`，19 shards，87.0 GiB） |

## 实际路径

- **模型路径（已找到且完整）**：实际位于 HF 缓存目录，而非默认 `/data/models/`
  `/data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61`
  - revision: `eba92302a2861cdc0098cc54bc9f17cb2c47eb61`（`mecc_package_old/download_mixtral.log` 确认
    `mistralai/Mixtral-8x7B-Instruct-v0.1` 完整下载，耗时 126.8 min，36 文件）
  - 完整性：19 个 safetensors shard 全部存在，真实权重（blobs）合计 **87.0 GiB**；`config.json` 正确
    （`num_local_experts=8, num_hidden_layers=32, num_experts_per_tok=2`）；含 `model.safetensors.index.json` + tokenizer。
  - 后续 Gate C/D 通过 launcher CLI `--state-path` 指向该 snapshot 路径（**不改进受控 JSON**）。
- **store 路径（存在）**：`/data/mecc_store_mixtral`，块设备 `/dev/sdb`，文件系统 ext4，挂载于 `/data`，
  非 tmpfs/NFS，空闲 330.7 GiB，满足 ≥120 GB 要求。

## GPU 是否空闲

是。A100 80GB PCIe，当前 81153 / 81920 MiB 空闲，无任何 compute 进程，GPU-Util 0%。

## 依赖快照

- torch `2.5.1+cu121`、transformers `4.53.0`、safetensors `0.4.5`、numpy `1.26.4`
- `torch.cuda.is_available() = True`，设备 `NVIDIA A100 80GB PCIe`
- ⚠️ **注意**：torch 版本恰为 `docs/PITFALLS.md` §1.1 记录的 K_H=4 OOM 版本。后续 Gate C/D 实验
  必须沿用 `HBM=30 (K_H=2)` 口径，而非冻结配置里的 50GB，否则推理阶段 OOM。

## 异常

无阻断性异常。仅提示：默认约定路径 `/data/models/` 不存在，权重实际位于 `/data/qinzy/models/...`
（HF 缓存格式）；已通过实际路径验证完整性，不影响流程。

## 预计下一步

1. Gate 0 全部 PASS，按序进入 **Gate B（CPU 回归 + L0 冒烟）→ Gate C（Mixtral L2 预检，首次物化 ~90GB store）→ Gate D（复现 1.33×）**。
2. 所有需要模型的步骤通过 launcher `--state-path /data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302a2861cdc0098cc54bc9f17cb2c47eb61` 覆盖，不改进受控 JSON。
3. 注意 torch `2.5.1+cu121` 为已知 K_H=4 OOM 版本，Gate C/D 须用 `HBM=30 (K_H=2)` 口径。

> 本文件不含任何 token、凭据或 `.env` 内容。
