# MECC Ablation — 优化消融实验

针对 Mixtral-8x7B（A100，真实端到端）逐项叠加优化的消融实验归档。
每个 `opt*` 对应一项独立优化，配套 运行脚本 / 输出配置 / 运行日志。

> 注：`scripts/` 内的 `.sh` 使用远程服务器绝对路径（`/data/...`、`/home/qinzy/...`），
> 为远程运行的归档副本，本地仅作记录。

## 目录结构

```
mecc_ablation/
├── README.md
├── scripts/                # 运行脚本 + 补丁
│   ├── run_baseline.sh
│   ├── run_opt1.sh ~ run_opt5.sh   # 含 run_opt3b.sh
│   └── opt1_zero_copy.patch
├── configs/                # 各 opt 的输出配置 (--out 产物)
│   ├── 00_baseline.json
│   ├── 01_zero_copy.json
│   ├── 02_no_pin.json
│   ├── 03_prefetch.json
│   ├── 03b_batch_h2d.json
│   └── 04_per_layer_adaptive.json
└── logs/                   # 运行日志
    ├── 00_baseline.log / baseline*.log
    ├── opt1.log ~ opt5.log (含 opt3b.log)
    └── ablation_full.log   # 全量汇总日志
```

## 优化项对照

| 编号 | 优化 | 脚本 | 配置 | 日志 |
|------|------|------|------|------|
| 00 | baseline | `run_baseline.sh` | `00_baseline.json` | `00_baseline.log` |
| 01 | zero-copy（含 patch） | `run_opt1.sh` | `01_zero_copy.json` | `opt1.log` |
| 02 | no-pin | `run_opt2.sh` | `02_no_pin.json` | `opt2.log` |
| 03 | prefetch | `run_opt3.sh` | `03_prefetch.json` | `opt3.log` |
| 03b | batch H2D | `run_opt3b.sh` | `03b_batch_h2d.json` | `opt3b.log` |
| 04 | per-layer adaptive | `run_opt4.sh` | `04_per_layer_adaptive.json` | `opt4.log` |
| 05 | （见脚本/日志） | `run_opt5.sh` | — | `opt5.log` |
