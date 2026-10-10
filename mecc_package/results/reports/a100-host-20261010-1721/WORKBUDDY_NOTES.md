# WorkBuddy Host Audit Notes — a100-host-20261010-1721

**branch**: gpu/a100-20261010
**commit**: 613a517ead87eabb1d9bfc17e6aa4a8203747af8
**collected_at**: see host_report.json

## 结论：BLOCKED（仅因模型目录缺失；其余 Gate 0 检查全部 PASS）

| Gate 0 检查项 | 结果 |
|--------------|------|
| 是 A100 80GB | ✅ `NVIDIA A100 80GB PCIe`，driver 560.35.03，CUDA 12.6 |
| GPU 空闲（无其他作业） | ✅ 81153 / 81920 MiB free，无 compute 进程，util 0% |
| `systemd --user` 可用 | ✅ `running` |
| CPU 内存足以提供 40GB expert budget | ✅ 1007.5 GiB total / 980 GiB avail |
| STORE_ROOT 本地块设备、非 tmpfs/NFS、空闲≥120GB | ✅ `/data/mecc_store_mixtral` → 块设备 `/dev/sdb`，ext4，本地盘；空闲 330.7 GiB |
| **模型目录可读 / revision 明确 / safetensors 完整** | ❌ **BLOCKED** |

## 实际路径

- **模型路径（缺失）**：`/data/models/Mixtral-8x7B-Instruct-v0.1` 不存在；`/data/models/` 整个目录缺失。
  `collect_host_report.py` 的 `path_snapshot` 回退 probe 到 `/data`（`state_path.exists = false`）。
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

唯一异常：Mixtral-8x7B-Instruct-v0.1 权重目录不存在。这是 Gate C/D（真实 Mixtral 推理）的前置，
当前阻塞 GPU 主实验。Gate B（CPU 回归 + L0 逻辑冒烟）不加载模型权重，可独立于本项先行。

## 预计下一步

1. 解决模型权重：将 Mixtral-8x7B-Instruct-v0.1 放置/下载到 `/data/models/Mixtral-8x7B-Instruct-v0.1`
   （需确认本机是否有 HF/外网访问；权重约 90GB+）。
2. 权重就位后复核 `state_path.exists = true`、safetensors 完整、revision 明确，再继续 Gate B → C → D。
3. Gate B（CPU/L0）不依赖模型，可在权重就绪前先跑，以尽早暴露 CPU/逻辑回归问题。

> 本文件不含任何 token、凭据或 `.env` 内容。
