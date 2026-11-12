# WorkBuddy handoff — current manuscript and A100 plan

Date: 2026-11-12 (Asia/Shanghai). Branch: `handoff/workbuddy-current-progress-20261112`.

## Current state

- This branch starts from the frozen A100 completion branch at `543202a`; the experiment code, input set, and queue in [`WORKBUDDY_A100_COMPLETION_20261109.md`](WORKBUDDY_A100_COMPLETION_20261109.md) are unchanged.
- The current manuscript is [`mecc_package/paper/workbuddy_current_20261112/paper.pdf`](../mecc_package/paper/workbuddy_current_20261112/paper.pdf), with compilable source at [`mecc_package/paper/workbuddy_current_20261112/source/main.tex`](../mecc_package/paper/workbuddy_current_20261112/source/main.tex). It is the seven-page version read back from the author's [online LaTeX project](https://latex.sysu.edu.cn/project/6af2656ec3f5028c95223ebe) on 2026-11-12.
- Evaluation occupies pages 5–6. Figure 7 places the A100 Mixtral-8×7B and Qwen2-57B-A14B comparisons side by side. The author withdrew the previous H100 Mixtral-8×22B values; the current manuscript has no H100 performance figure or claim. Wait for corrected per-workload measurements before restoring that comparison.
- The manuscript explains HBM/CPU/HDD request paths, host-mirror retention, exposed delivery time, and task-transfer behavior using the displayed figures. The separate unfigured 64/64-token performance paragraph is absent.
- The manuscript and A100 completion queue serve different purposes. Do not infer new server-run results from the manuscript or use its figures as substitutes for `result.json` and run logs. Do not reuse the withdrawn H100 numbers from older commits.

## WorkBuddy scope

This commit shares context only. Do not start GPU jobs, alter experiment settings, edit the manuscript, or sync Overleaf because of this handoff. When the author starts the A100 queue, follow the frozen protocol in [`WORKBUDDY_A100_COMPLETION_20261109.md`](WORKBUDDY_A100_COMPLETION_20261109.md) and the repository entry documents. Report completed and blocked run IDs, the exact commit and configuration, compact result paths, and the next pending step. Preserve model weights, stores, tokens, and full logs outside Git.

For a clean checkout on the A100 host:

```bash
git fetch origin
git worktree add -b gpu/a100-from-handoff-20261112 ../mecc_a100_from_handoff origin/handoff/workbuddy-current-progress-20261112
cd ../mecc_a100_from_handoff
git status --short
git rev-parse HEAD
```
