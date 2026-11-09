# WorkBuddy A100 execution entry

This repository is developed locally and executed on the remote A100 host.  The
remote agent is an **experiment operator**, not an independent paper editor.

For the current experiment request, read
`docs/WORKBUDDY_A100_COMPLETION_20261109.md` after the four entry documents below.
It supersedes COPY_READINESS, the old insight driver, and the 2026-11-03 roadmap
for this round. This branch includes the execution code and frozen inputs.
Do not treat ideal PPT values as measurements.

Before doing anything, read these files in order:

1. `AGENTS.md`
2. `docs/WORKBUDDY_A100_RUNBOOK.md`
3. `docs/EXPERIMENTS.md`
4. `docs/GPU_HANDOFF.md`

The current mission is deliberately staged:

1. confirm the A100 is idle and the checkout is clean;
2. pass `test_completion_protocol.py`, L0, and short policy correctness gates;
3. execute the frozen C11 serial queue with an 80 GiB unit memory.max and zero swap;
4. return complete and failed runs with per-request, per-phase and physical-memory evidence.

The default queue contains 23 runs, with one independent measurement per point.
Six input-length runs are optional and require genuinely long enough inputs.
Single-run data gets no invented variance. The 24-hour option is a queue deadline,
not a claim that all figures will finish in that time.

Do not start later stages when an earlier gate fails. Do not invent fixes or
silently change budgets, precision, policies, prompts, cold/warm SSD semantics,
or model revision. Record the failure, export a report, commit it on a
`gpu/a100-*` branch, push the branch, and stop for review.

Never commit model weights, Hugging Face tokens, `.env` files, the expert store,
or full multi-gigabyte logs.  Use `experiment_launcher.py report` to produce the
compact report intended for Git.

