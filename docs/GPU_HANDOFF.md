# GPU 实验交接流程

这套流程用于“本地开发 → GitHub → GPU 机器运行 → 结果回传”。GPU 机器上的完整工作目录保留在
`mecc_package/results/runs/<run-id>/`；回传目录位于
`mecc_package/results/reports/<run-id>/`。前者默认不进 Git，后者是紧凑、可追踪的诊断材料。

由 WorkBuddy 执行 A100 任务时，以 [`WORKBUDDY_A100_RUNBOOK.md`](./WORKBUDDY_A100_RUNBOOK.md)
为逐项门禁；根目录 `WORKBUDDY.md` 是其入口。本文件保留通用 launcher/reference 用法。

## 1. GPU 机器拉取与检查

```bash
git clone https://github.com/Kirihara-Yun/mecc_package.git
cd mecc_package
git rev-parse HEAD
python3 mecc_package/scripts/check_env.py
```

安装依赖前建议创建独立虚拟环境。L2 Mixtral 依赖见
`mecc_package/e2e/requirements_e2e.txt`，模型与 NVMe 空间要求见
`mecc_package/e2e/README_E2E.md`。

## 2. 先核对命令，再启动持久实验

下面以 A100 80GB 的 L2 主实验为例。`RUN_ID` 只使用小写字母、数字、点、下划线和连字符。

```bash
RUN_ID=l2-mixtral-$(date +%Y%m%d-%H%M)

python3 mecc_package/scripts/experiment_launcher.py run "$RUN_ID" \
  --config mecc_package/e2e/configs/l2_mixtral_main.json \
  --state-path /data/models/Mixtral-8x7B-Instruct-v0.1 \
  --store-root /data/mecc_store_mixtral \
  --gpu 0 --dry-run

python3 mecc_package/scripts/experiment_launcher.py run "$RUN_ID" \
  --config mecc_package/e2e/configs/l2_mixtral_main.json \
  --state-path /data/models/Mixtral-8x7B-Instruct-v0.1 \
  --store-root /data/mecc_store_mixtral \
  --gpu 0
```

启动器使用 user-systemd，即使 SSH 断开，实验也会继续。若服务器未启用 user-systemd，启动会失败并在
run 目录留下 `launch_error.txt`；不要改用临时前台命令掩盖失败，先把该文件回传以便适配平台。

## 3. 查看状态和日志

```bash
python3 mecc_package/scripts/experiment_launcher.py status "$RUN_ID"
tail -n 200 -f "mecc_package/results/runs/$RUN_ID/run.log"
```

关键文件：

- `run.json`：Git commit、配置指纹、完整命令和环境快照。
- `status.json`：当前阶段或失败原因。
- `partial_result.json`：已完成策略的原子检查点。
- `result.json`：全部完成后才出现的正式结果。
- `run.log`：完整 stdout/stderr，仅留在 GPU 机器，避免 Git 仓库膨胀。

停止与复用已验证 expert store：

```bash
python3 mecc_package/scripts/experiment_launcher.py stop "$RUN_ID"
python3 mecc_package/scripts/experiment_launcher.py resume-from-store \
  "$RUN_ID" "${RUN_ID}-retry" --gpu 0
```

## 4. 导出并回传给开发端

实验完成或失败后都执行：

```bash
python3 mecc_package/scripts/experiment_launcher.py report "$RUN_ID"
git add "mecc_package/results/reports/$RUN_ID"
git commit -m "results: add GPU report $RUN_ID"
git push
```

`report` 会复制完整的 metadata/status/result/partial JSON，并截取日志最后 2000 行；
`report_manifest.json` 记录源日志大小和 SHA-256，足够判断报告是否对应同一次运行。需要更多上下文时可用
`--tail-lines 10000` 重新导出到新的 run id，或单独传递 GPU 机器上的完整 `run.log`。

回传后，在开发端执行 `git pull` 即可读取报告并继续诊断。不要提交模型权重、expert store、Hugging Face
token 或 `.env`。
