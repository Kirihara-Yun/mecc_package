# R2 — Method, correctness, and reproducibility

This is an independent simulated review, not a review by an actual DAC committee member. The explicit simulated scale is **1 reject, 2 weak reject, 3 borderline, 4 accept, 5 strong accept**; it is not an official DAC rubric.

**Current-submission score: 1/5 (reject). Conditional technical score: 3/5 (borderline).** Confidence: high on the specification and source discrepancies; moderate on achievable hardware performance, which I did not measure.

The current file identifies all outcomes as hypothetical and explicitly says it is not for submission. That disclosure is appropriate, but a systems paper without measured execution, memory, or correctness evidence cannot support acceptance. For the conditional score, I assume only the displayed scenario values become valid measurements, including the displayed quality checks and memory point. I do not assume that planned factorial controls, undisplayed traffic counters, external-system reproductions, synchronization stress tests, or additional sensitivity cases succeed. Such measurements would make this a plausible systems paper, but would leave substantial specification, attribution, and reproducibility gaps. The desired score of 4 does not change this assessment.

## Scope and positive findings

I read the frozen `manuscript.tex`, extracted the rendered `manuscript.pdf` text and figures' labels, and read `assumptions.json`. I consulted the repository's required `AGENTS.md`, `docs/APPLICABILITY.md`, and `docs/THEORY.md`, followed by its provenance and writing guidance. The manuscript-only findings below are separate from a subsequent targeted audit of the current repository source. The source is not frozen alongside the manuscript and is not established to be the implementation that would produce the hypothetical results. I ran no GPU experiments. The repository claim verifier completed with no failures but retained warnings; it does not verify these hypothetical values or resolve execution correctness.

The paper gets several boundaries right. Proposition 1 is explicitly restricted to equal-size static objects and independent capacities. The multilayer planner is called a heuristic rather than an optimizer with a global guarantee. The runtime is not claimed to dominate static placement on every trace. The text distinguishes logical residency from physical mirrors, demand-source counters from transfer traffic, and unchanged weights from correct execution. The global-LRU reference is particularly useful: it makes the combined-capacity explanation testable and avoids presenting basic exclusive LRU as a universally superior new replacement principle. These distinctions should survive revision.

## Findings established by the manuscript

### M1. The layer-allocation objective and the executable heuristic are not fully connected

Section III-A calls `p_e` a request probability, but Equation (1) normalizes separately within each layer. Summing these probabilities over all experts gives one unit per layer, rather than a global request distribution. For homogeneous layers visited once per token with the same top-k, this common scaling does not change placement. With the general `k_l` and heterogeneous-layer model introduced in Section II, layer weights matter. Define whether the objective represents cost per expert request or cost per generated token. One suitable convention is an expected request count `q_(l,r) = k_l p_(l,r)` per token, with probabilities conditional on an expert selection in that layer. Prefill/batched serving instead needs an explicitly defined object-fetch frequency because many selected tokens can share one loaded expert.

Equation (3) is marginal probability coverage, not marginal latency reduction. The paragraph motivating allocation explicitly mentions differing miss costs, while the heuristic never multiplies by those costs or divides by bytes. This is defensible as a restricted heuristic if all candidate slots have common size, layer weight, and relevant cost difference. State those restrictions. With CPU placement fixed, moving the next SSD object to CPU saves its request weight times `T_S - T_C`; an HBM extension can change both the HBM/CPU boundary and the CPU/SSD boundary. Its gain must therefore be defined against an explicit current placement. The displayed `Delta_l` alone does not specify that calculation.

Proposition 1's exchange argument is sound under its stated static assumptions. It does not validate the sequential two-tier heuristic, minimum per-layer reservations, or nonconstant mirror requirements. The paper acknowledges part of this gap, but still lacks planner pseudocode specifying initial minima, infeasible-budget handling, tie breaking, rank-to-ID mapping, and termination. An implementer cannot reproduce the exact allocation from this prose.

**Text/specification repair:** define the probability convention and objective units; give a short deterministic planner algorithm; identify common-size/common-cost restrictions; state whether empirical probabilities actually drive allocation or only initial ordering. If the allocation intentionally ignores measured delivery costs, say so directly. **Required validation:** report allocations and predicted-versus-observed traffic on held-out real routes; compare uniform allocation and this planner under the same physical caps. A theorem for the general heuristic is unnecessary if the claims remain empirical.

### M2. Budget notation is reasonable, but the physical feasibility rule is incomplete

`B_H` is an expert-residency allowance; `B_C` is a total host allowance; Equation (2) uses reduced residency budgets `bar B_t`. There is no explicit equation relating these quantities to live physical allocations. In particular, mirror memory depends on which HBM experts are mirrored. A constant reservation cannot silently support arbitrary mirror policies. A mirrored implementation requires a constraint of the form

`host residents + distinct host mirrors + staging + other live host storage <= B_C`,

and a separate GPU constraint covering experts, dense weights, KV/activations, in-flight loads, workspaces, and allocator effects. Count shared storage once, but count simultaneously live distinct copies even when they represent the same logical expert. Define whether the cap covers allocator-reserved memory, process RSS, and file-cache pages attributable to the task. Give the enforcement mechanism and memory sampling boundary.

The stated host breakdown sums to its cap; this is an authored accounting point, not a runtime proof. The GPU component array in `assumptions.json` has no semantic labels and cannot identify which bytes are expert weights, workspaces, or spare capacity. The nominal expert allowance, actual expert occupancy, and total peak need a labeled reconciliation for each model.

The combined-capacity condition in Section II is physically relevant: expert bytes exceeding host memory alone do not imply SSD demand if enough unique bytes also reside in HBM. State a sufficient capacity condition using the actual unique HBM-plus-host coverage after mirrors and buffers. Cold reads verify that the chosen execution accesses SSD; they do not independently prove SSD is unavoidable under every feasible placement.

**Text/specification repair:** add the two physical constraints and label the memory components, scope, units, and measurement mechanism. **Required experiments:** cap-enforced, time-aligned host/GPU peaks during initialization, prefill, decode, and quality evaluation; byte counters for each policy; a cold-I/O protocol with page-cache behavior and actual device-read evidence. The same slot counts are insufficient evidence of equal physical budgets.

### M3. The runtime is an understandable serial state machine, but its concurrent algorithm is missing

Section III-B should define `K_H` and `K_C` explicitly and attach a layer subscript. A per-layer policy is equivalent to a capacity-`K_H,l + K_C,l` LRU within that layer under the corresponding initial stack and demand-only, unit-object transitions. It is not one global cache across all layers. State the stack ordering, admission rule, and absence of speculative insertion assumed by the equivalence. A short induction or a clearly labeled controlled-model observation is enough; do not infer cross-policy dominance from it.

For execution, specify what happens when several experts are selected at once, when a requested expert is also a prospective victim, when a transfer is in flight, and when zero slots remain after budget reservation. Immutable weights simplify copying but do not eliminate ownership and lifetime requirements. The paper should state whether an outstanding consumer pins its expert against eviction and how transient references are charged. Without these details the runtime is a design contract, not a reproducible algorithm.

**Text/specification repair:** include access/promotion/demotion pseudocode and explicit in-flight states. **Required validation:** CPU transition tests against the per-layer reference, including small capacities and batched requests, followed by GPU execution tests. These test correctness rather than performance optimality.

### M4. Dependency-aware overlap is asserted, but no schedule or actual overlap evidence is provided

Section III-C gives good readiness and lifetime requirements, yet no launch sequence shows the work available to overlap with a transfer. For an ordinary autoregressive layer, next-layer routed expert IDs are generally unavailable until the current layer produces its activations and the next router runs. The paper should identify the available independent work: computation of other already selected experts, dense/shared work, or something else. It must identify the readiness horizon without assuming future routes are known.

A per-expert sequence should show SSD completion, pinned-source ownership, H2D launch, ready event, compute-stream wait, expert kernel, consumer completion, and eventual source/device reuse. Reordering experts to create overlap can also conflict with the stated preservation of aggregation order; specify how the implementation satisfies both conditions.

Holding SSD demand-miss share fixed in Figure 5 is useful, but does not prove that the time saved is hidden I/O. Physical bytes, admissions, ordering, synchronization overhead, and timing boundaries can differ while the miss share remains constant. The conditional measurements would establish an observed step improvement, not its detailed mechanism.

**Text/specification repair:** add schedule pseudocode or a stream timeline and the exact work overlapped. **Required experiments:** a synchronous reference and matched asynchronous execution, aligned SSD/H2D/D2H bytes, a hardware timeline separating exposed stalls from transfer duration, and correctness checks under eviction pressure. Valid quality checks at a displayed deterministic point do not establish every lifetime interleaving.

### M5. The reproducibility record remains a plan

Section V-A explicitly leaves model, dataset, and input revisions unfrozen. There are no complete run commands, exact adapter rules, profile token count and fitting settings, transfer calibration values, store layout/read method, cap enforcement, timer endpoints, or artifact revision. The single-/multi-GPU comparison also lacks an executable partition and scheduling specification. An independent implementation could satisfy this prose while producing a materially different system.

The displayed adaptation plot has three curves, although the text announces a crossed initialization-by-update experiment. The fourth cell and the no-shift, mismatch, and uniform controls are not displayed. The component plot is cumulative, and the text correctly says leave-one-out and factorial studies remain planned. Those missing results cannot be credited in the conditional score. In particular, long-run improvement may come from allocated capacity and ordinary LRU after the initial profile has washed out; startup and steady-state attribution must be separated.

**Text/specification repair:** supply an artifact manifest and exact protocol. **Required experiments:** the missing initialization/update cell, real-route order controls, and at least targeted leave-one-out comparisons addressing compiler initialization, tier coverage, and delivery. Broader sensitivity sweeps can remain future work if the claims are narrowed.

## Separate source audit: concrete discrepancies requiring resolution

These observations concern the current `mecc_package/e2e` code. They are not evidence that any particular hypothetical result was generated incorrectly. A different implementation could satisfy the manuscript, but it must be identified and frozen.

1. **Profile-driven layer capacities are not implemented as described in the normal runner.** `run_e2e.py:369–381` synthesizes per-layer exponents with a seeded Gaussian and passes them to `compile_plan`; `--profile` is supplied separately. Unless uniform mode is selected, real per-layer capacities therefore depend on synthetic exponents rather than fitted exponents from the independent route profile. `compile_config.py:265–312` allocates by Zipf coverage. Resolve this before claiming that measured allocation gains arise from the real profile.

2. **Promised feasibility checks are absent in the audited planner.** `compile_config.py:269–306` initializes one HBM and one CPU slot per layer without rejecting budgets below those minima. It also initializes a CPU slot even when a layer already has all experts in HBM. The returned plan can exceed its supplied slot budget or the unique-expert limit. `hbm_gb_used` and `cpu_gb_used` at lines 362–363 use rounded average capacities rather than summing actual per-layer capacities. Budget checks in Section III-A must become executable rejection/adjustment rules, and accounting must use actual placements.

3. **The source contains a placement mechanism absent from the method.** `compile_config.py:332–347` enables co-occurrence-boosted joint ranking by default when the profile has suitable traces. That is different from the manuscript's marginal popularity ranking. Disable it for the claimed method or document and ablate it. The current `CompiledPlan` also lacks the claimed explicit model/profile revision identifiers needed for provenance.

4. **Every HBM entry retains a host mirror on the OURS path.** `tiered_engine.py:229–237` initializes each GPU entry as `(gpu_weights, cpu_weights)`; `policy_plugin.py:76–101` retains that host tensor on subsequent admissions. Host mirror bytes thus track the actual HBM expert footprint, rather than an independently chosen small allowance. The displayed 6 GB mirror component needs an implementation policy that supports it; it cannot simply accompany a much larger fully mirrored GPU expert pool. The audited `--cpu_budget` is documented as expert-system-memory budget and is passed to slot allocation without the manuscript's total-task reservation contract.

5. **A required use-before-compute barrier is not visible on the Mixtral path.** `tiered_engine.py:252–265` launches H2D on a separate stream; the pending state is a boolean, not a recorded per-transfer readiness event. `load_experts` yields weights before its final `sync_copy` at line 364. `mixtral_tiered.py:75–94` consumes the yielded GPU weights on the compute path without an explicit wait on the copy stream. This is a concrete synchronization risk relative to Section III-C, not proof of an observed numerical failure. Add the dependency and source/device lifetime handling, then validate on GPU. A CPU smoke test cannot validate it.

6. **Prefetch, counters, and measurement windows do not match the stated controls.** `mixtral_tiered.py:56–61` invokes near-miss prefetch without a manuscript-style experiment switch. OURS can consume this buffer; matched baseline behavior is not established. `tiered_engine.py:349–362` installs prefetched CPU objects into GPU residency before the policy's access call, so that call counts them as HBM hits. `run_e2e.py:210–243` aggregates cache hits after warmup, timed generation, and optional PPL without resetting separate windows. These paths contradict the intended arrival-source and timing-window semantics. Implement the controls and counters before using demand percentages to explain timed speedups.

## Changes that would support an accept-level technical case

The strongest route to 4/5 is a complete, narrowly scoped executable method: deterministic planner pseudocode with valid physical reservations; per-layer exclusive retention with fully specified concurrent ownership; a real use-before-compute schedule; and a frozen artifact matching those descriptions. The evaluation then needs measured fair-budget gains over the matched caching references, distinct evidence for layer allocation versus initial placement, and transfer/quality traces that close the synchronization and attribution questions.

Many wording repairs are inexpensive and do not require a new theorem. Physical-cap compliance, asynchronous correctness, and causal performance attribution require implementation work and experiments. Replacing scenario labels with measured numbers alone would leave the conditional paper borderline.
