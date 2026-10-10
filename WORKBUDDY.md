# WorkBuddy A100 execution entry

This repository is developed locally and executed on the remote A100 host.  The
remote agent is an **experiment operator**, not an independent paper editor.

Before doing anything, read these files in order:

1. `AGENTS.md`
2. `docs/WORKBUDDY_A100_RUNBOOK.md`
3. `docs/EXPERIMENTS.md`
4. `docs/GPU_HANDOFF.md`

The current mission is deliberately staged:

1. collect and return the host report;
2. pass CPU/L0 checks;
3. pass the minimal Mixtral L2 preflight;
4. only then reproduce the historical Mixtral `ours,swapmoe` result.

Do not start later stages when an earlier gate fails.  Do not invent fixes or
silently change budgets, precision, policies, prompts, cold/warm SSD semantics,
or model revision.  Record the failure, export a report, commit it on a
`gpu/a100-*` branch, push the branch, and stop for review.

Never commit model weights, Hugging Face tokens, `.env` files, the expert store,
or full multi-gigabyte logs.  Use `experiment_launcher.py report` to produce the
compact report intended for Git.

