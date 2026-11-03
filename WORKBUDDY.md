# WorkBuddy A100 execution entry

This repository is developed locally and executed on the remote A100 host.  The
remote agent is an **experiment operator**, not an independent paper editor.

For the current experiment request, read
`docs/WORKBUDDY_A100_NEARMISS_ABLATION.md` after the four entry documents below.
It supersedes the previous A100 task for the next diagnostic run. The broader
missing-experiment matrix remains in `docs/WORKBUDDY_A100_NEXT_EXPERIMENTS.md`.
Do not treat ideal PPT values as measurements.

Before doing anything, read these files in order:

1. `AGENTS.md`
2. `docs/WORKBUDDY_A100_RUNBOOK.md`
3. `docs/EXPERIMENTS.md`
4. `docs/GPU_HANDOFF.md`

The current mission is deliberately staged:

1. confirm the A100 is idle and the checkout is clean;
2. pass CPU/L0 checks after the near-miss call was disabled;
3. repeat the frozen long-sequence diagnosis with per-token memory tracing;
4. return raw logs and a compact comparison without treating it as a performance result.

Do not start later stages when an earlier gate fails. Do not invent fixes or
silently change budgets, precision, policies, prompts, cold/warm SSD semantics,
or model revision.  Record the failure, export a report, commit it on a
`gpu/a100-*` branch, push the branch, and stop for review.

Never commit model weights, Hugging Face tokens, `.env` files, the expert store,
or full multi-gigabyte logs.  Use `experiment_launcher.py report` to produce the
compact report intended for Git.

