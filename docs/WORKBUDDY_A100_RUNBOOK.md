# WorkBuddy：A100 实验执行清单

> 目的：本地 Codex 负责设计与分析，远端 WorkBuddy 只在 A100 服务器执行经过冻结的实验，
> 双方通过 Git 分支和结构化报告交接。任何性能数字都必须能定位到 commit、配置、机器和日志。

## 0. 权限与边界

WorkBuddy 可以：安装当前仓库声明的 Python 依赖、运行检查与实验、在自己的
`gpu/a100-*` 分支提交 `mecc_package/results/reports/` 下的紧凑报告和一份执行记录。

WorkBuddy 不可以：修改论文结论、删除历史结果、改实验配置来“跑通”、把 warm cache 当 cold SSD、
把 L0/预检数字写成性能结论，或提交模型、store、token、`.env`、完整巨型日志。

遇到以下任一情况应停止并回传报告：

- 不是 A100 80GB，或 GPU 正被其他作业占用；
- 模型目录不可读、revision 不明或 safetensors 不完整；
- `STORE_ROOT` 不是本地块设备/NVMe，位于 tmpfs/NFS，或空闲不足 120 GB；
- 可用 CPU 内存不足以安全提供 40 GB expert budget 加运行余量；
- CPU checks、L0 或前一阶段失败；
- 需要改变 fp16、cold SSD、预算、策略或 prompt 才能继续；
- `systemd --user` 不可用且当前 launcher 无法持久运行。

## 1. 拉取与建立独立分支

```bash
git clone https://github.com/Kirihara-Yun/mecc_package.git
cd mecc_package
git switch main
git pull --ff-only origin main
git switch -c "gpu/a100-$(date +%Y%m%d)"
git rev-parse HEAD
git status --short
```

开始时工作区必须为空。记下 HEAD；所有报告的 `git_commit` 必须等于这个实验 commit。

约定两个机器相关路径，按服务器实际情况替换：

```bash
export MECC_STATE_PATH=/data/models/Mixtral-8x7B-Instruct-v0.1
export MECC_STORE_ROOT=/data/mecc_store_mixtral
```

不要把上述路径改进受控 JSON；通过 launcher 的 CLI 参数覆盖。

## 2. Gate A：只读主机审计并回传

```bash
HOST_RUN="a100-host-$(date +%Y%m%d-%H%M)"
mkdir -p "mecc_package/results/reports/$HOST_RUN"
python3 mecc_package/scripts/collect_host_report.py \
  --state-path "$MECC_STATE_PATH" \
  --store-root "$MECC_STORE_ROOT" \
  --out "mecc_package/results/reports/$HOST_RUN/host_report.json"
```

人工检查 JSON：GPU 型号/显存、驱动、CPU available、目标盘文件系统与空闲空间、模型目录、
`systemd --user`、Python 包。然后新增：

`mecc_package/results/reports/$HOST_RUN/WORKBUDDY_NOTES.md`

最少写明：结论 PASS/BLOCKED、实际模型路径、实际 store 所在块设备/文件系统、GPU 是否空闲、
预计下一步，以及所有异常。不得写 token 或其他凭据。

提交并推送第一道门禁：

```bash
git add "mecc_package/results/reports/$HOST_RUN"
git commit -m "results: add A100 host audit $HOST_RUN"
git push -u origin HEAD
```

若 Gate A 为 BLOCKED，到这里停止。

## 3. Gate B：CPU 回归与 L0

在独立虚拟环境安装 `mecc_package/e2e/requirements_e2e.txt`。不要擅自升级仓库未要求的
系统 CUDA 驱动。随后：

```bash
python3 mecc_package/scripts/run_cpu_checks.py

L0_RUN="a100-l0-$(date +%Y%m%d-%H%M)"
python3 mecc_package/scripts/experiment_launcher.py run "$L0_RUN" \
  --config mecc_package/e2e/configs/l0_smoke.json --gpu 0 --dry-run
python3 mecc_package/scripts/experiment_launcher.py run "$L0_RUN" \
  --config mecc_package/e2e/configs/l0_smoke.json --gpu 0
python3 mecc_package/scripts/experiment_launcher.py status "$L0_RUN"
python3 mecc_package/scripts/experiment_launcher.py report "$L0_RUN"
```

L0 只验证逻辑，不解释 tok/s。失败则提交报告并停止。

## 4. Gate C：Mixtral 最小 L2 预检

首次运行会物化并校验约 90 GB 的 fp16 expert store；即使预检 token 很少，这一步也可能很久。
必须先 dry-run：

```bash
PRE_RUN="a100-mixtral-preflight-$(date +%Y%m%d-%H%M)"
python3 mecc_package/scripts/experiment_launcher.py run "$PRE_RUN" \
  --config mecc_package/e2e/configs/l2_mixtral_preflight.json \
  --state-path "$MECC_STATE_PATH" --store-root "$MECC_STORE_ROOT" \
  --gpu 0 --dry-run
python3 mecc_package/scripts/experiment_launcher.py run "$PRE_RUN" \
  --config mecc_package/e2e/configs/l2_mixtral_preflight.json \
  --state-path "$MECC_STATE_PATH" --store-root "$MECC_STORE_ROOT" \
  --gpu 0
```

观察状态，不要通过重复启动制造同 GPU 并发任务：

```bash
python3 mecc_package/scripts/experiment_launcher.py status "$PRE_RUN"
tail -n 200 "mecc_package/results/runs/$PRE_RUN/run.log"
```

完成或失败后都导出并提交：

```bash
python3 mecc_package/scripts/experiment_launcher.py report "$PRE_RUN" --tail-lines 10000
git add "mecc_package/results/reports/$PRE_RUN"
git commit -m "results: add Mixtral A100 preflight $PRE_RUN"
git push
```

通过标准：`mode=real`；只有 `ours,swapmoe`；两者均有完整 TTFT/TPOT/tok/s/hit_pct；
store manifest 校验成功；`cold_ssd=true`；无 OOM、NaN 或 traceback。预检数据不进入论文。

## 5. Gate D：复现历史 Mixtral 主结果

只有 Gate C 通过才执行。该配置冻结为历史口径：A100 80GB、HBM expert budget 50 GB、
CPU expert budget 40 GB、64-token prompt、4 prompts、16 generated tokens、cold SSD、
`ours,swapmoe`、统一逐层预算。

```bash
REPRO_RUN="a100-mixtral-repro-$(date +%Y%m%d-%H%M)"
python3 mecc_package/scripts/experiment_launcher.py run "$REPRO_RUN" \
  --config mecc_package/e2e/configs/l2_mixtral_repro.json \
  --state-path "$MECC_STATE_PATH" --store-root "$MECC_STORE_ROOT" \
  --gpu 0 --dry-run
python3 mecc_package/scripts/experiment_launcher.py run "$REPRO_RUN" \
  --config mecc_package/e2e/configs/l2_mixtral_repro.json \
  --state-path "$MECC_STATE_PATH" --store-root "$MECC_STORE_ROOT" \
  --gpu 0
```

结束后：

```bash
python3 mecc_package/scripts/experiment_launcher.py report "$REPRO_RUN" --tail-lines 10000
git add "mecc_package/results/reports/$REPRO_RUN"
git commit -m "results: reproduce Mixtral A100 baseline $REPRO_RUN"
git push
```

不要因为结果不接近历史 1.33× 就重跑到“满意”为止。先如实回传；本地端将检查平台、store、
命中率、舍入、PPL、页面缓存和运行方差，再决定是否做重复实验。

## 6. WorkBuddy 最终回复格式

向用户只需返回：

```text
branch: gpu/a100-YYYYMMDD
commit: <latest pushed commit>
gate: A/B/C/D complete | blocked
run_id: <run id>
result: PASS | FAILED | BLOCKED
one-line reason: <一句话>
```

详细信息必须在 Git 报告中，不依赖聊天上下文。

## 7. 本轮刻意不做的事

- 不直接跑 FlashMoE/Edge0/MoE-CORE；它们需要独立的版本锁定和公平性设计。
- 不把 `flashmoe_rf_adaptation` 当 FlashMoE 官方实现。
- 不做 async SSD adopted claim；必须先有稳定复现基线，再设计单变量开关。
- 不自动更新论文数字。新结果先进入报告，经 PROVENANCE 审核后才能成为 claim。

