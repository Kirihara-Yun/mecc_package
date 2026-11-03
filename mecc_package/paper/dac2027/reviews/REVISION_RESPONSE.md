# Independent cold review and revision, 2026-10-29

These are simulated reviewer perspectives, not DAC committee decisions. Scores use a local 1–5 rubric, not a verified DAC rating form. Reviewers were not told to produce accept scores.

| Round 0 perspective | Current draft | Conditional on correct displayed measurements |
|---|---:|---:|
| R1 novelty and positioning | 1 | 2 |
| R2 method and implementation | 1 | 3 |
| R3 evaluation and fairness | 1 | 2 |
| R4 English and presentation | 1 | 2 |

R4 separately rated prose/layout approximately 4/5. That is not an overall acceptance score. Conditional scores do not assume that absent experiments succeed.

## Repairs in the revised manuscript

1. Distinguish global expert-selection probabilities from layer-conditional ranks; include layer selection weights. Restrict marginal-coverage reasoning to common sizes/costs. Describe deterministic next-slot selection, ties, minima, termination, complexity, and unimplemented guards.
2. Scope combined-LRU equivalence to one layer with matching stack, serial transitions, and no prefetch. No global or dominance claim.
3. Replace asserted asynchronous correctness with required lifetimes and an explicit batch-one overlap opportunity. Identify outstanding readiness validation and protect in-flight weights.
4. Withdraw the infeasible 42 GB expert / 6 GB mirror accounting example under full CPU mirroring. Numerical arrays stay archived unchanged; their sum is not a physical feasibility certificate.
5. Separate desired instrumentation from current phase-mixed counters; define demand-miss denominator. Document synthetic alpha and optional co-occurrence discrepancies.
6. Remove authored error bars and categorical connecting lines. Mark the synthetic shift and show illustrative slot counts. Missing global-LRU and factorial cells remain explicitly missing, without invented outcomes.
7. Include 2/4/8-GPU resident targets in the resource table. State that the two-GPU target has lower latency and nominal GPU-time. Remove unsupported multi-GPU MECC targets from the active chart.
8. Interpret the nine-interval intersection only as initialization-plus-decode arithmetic. Give the full request-cost equation; no full-request crossover without adapter TTFT/profile costs.
9. Center a falsifiable compiler-prior question instead of treating familiar modules as a novelty proof. Keep strongest-local-baseline targets in the abstract and identify their status.

## Required work before measured claims

| Priority | Test or implementation gate | Decision enabled |
|---|---|---|
| P0 | Storage-identity allocation audit, process/cgroup host cap, GPU live/reserved peaks, mirrored bytes at every phase | Is each configuration physically feasible? |
| P0 | Enforced copy events and lifetime tests; synchronous/asynchronous route/logit/token comparisons | Does delivery preserve computation? |
| P0 | Real profile exponents or empirical probabilities; explicit M3/co-occurrence setting; planner validation and exact per-layer byte totals | Does the artifact implement the stated method? |
| P0 | Arrival-tier and physical-I/O counters with reset boundaries before/after warmup, prefill, decode, and quality | Are explanatory metrics aligned with timings? |
| P1 | Faithful closest exact-execution competitors; exclusive per-layer LRU; same physical caps and occupied bytes | Is benefit beyond basic caching and existing methods? |
| P1 | Allocation × initialization controls; profile/random × static/adaptive; leave-one-out and overlap-only controls | Which mechanism causes the gain? |
| P1 | Independent profiles, frozen prompts/revisions, no-shift and mismatch tests, profile cost and full request latency | Does the prior help on held-out service horizons? |
| P1 | Paired requests and independent runs, cache-state/device-I/O audit, latency distributions and uncertainty | Is the effect reproducible? |
| P2 | Smallest resident allocation, fixed-latency minimum host cap, workload/batch/length sweeps | What deployment tradeoff is supported? |

No favorable outcomes are prescribed. If compiler benefit vanishes against the matched reference, revise the contribution instead of changing the evaluation until it passes. All scenario outcomes remain hypothetical. No amount of language editing can guarantee four accept recommendations.

## Round-one review and final editorial reconciliation

Independent round-one reports are stored beside their frozen manuscript in `round1/`. Scores remained R1 1/2, R2 1/3, R3 1/2, and R4 1/2 (current/conditional); R4 separately rated prose 4/5. These overall scores did not improve through rewording because the missing evidence was not supplied. No report represents an actual DAC reviewer or an acceptance guarantee.

After freezing round one, the working copy received layout changes, a corrected overview showing all SSD backing weights, and these editorial repairs: archived infeasible memory and unsupported multi-GPU arrays now carry explicit withdrawal metadata; authored repeat factors are marked unused; the score is explicitly coverage rather than a latency marginal; prefill selections are distinguished from fetches; arrival-source counts are separated from physical SSD bytes and in-flight prefetch; validation protocol statements no longer imply completed tests. These are not new experimental results or a separately scored review round. `final_artifact_hashes.json` identifies the delivered working files, and `revision_diff.html` compares them with round zero.
