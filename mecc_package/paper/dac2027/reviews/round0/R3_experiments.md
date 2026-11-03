# R3 — Experimental design and evidential strength

This is an independent simulated DAC review, not a review by an actual DAC reviewer. I cold-read the frozen manuscript source, its six-page PDF, and `assumptions.json`. I also read the repository entry instructions, applicability boundary, and provenance ledger. Numerical values discussed below are the draft's hypothetical scenarios, not independently established measurements. I did not run experiments or change the manuscript.

**Scale:** 1 reject; 2 weak reject; 3 borderline; 4 accept; 5 strong accept.

**Current submission: 1/5 (reject).** All experimental outcomes, repeat variation, quality checks, and memory peaks are explicitly authored. This is an honest experimental-design document, but it does not establish an implemented system's correctness, benefit, or reproducibility. The hypothetical labels are appropriate; they do not substitute for evidence.

**Conditional score: 2/5 (weak reject), assuming the displayed numerical points were measured correctly.** This counterfactual does not grant successful unreported controls, external-system comparisons, memory audits, quality validation beyond the displayed targets, or sensitivity experiments. Even correct plotted values leave serious baseline and causal-identification gaps. Merely replacing the hypothetical labels with measurement language would not bring this submission to 4/5.

## Summary and strengths

The paper addresses a coherent deployment constraint: exact expert execution with SSD demand under bounded GPU and host memory. The design separates profile-guided initialization, online retention, and transfer overlap. The manuscript correctly distinguishes a local RF heuristic from FlashMoE and an SSD-inspired adapter from a reproduction of SSD-LLaMA. It also makes the GPU-allocation/latency tradeoff explicit instead of claiming that one GPU is faster than eight. Charging mirrors and staging to physical host capacity, recording demand tier before service, separating timing windows, and checking asynchronous correctness are sound experimental intentions.

The central experimental problem is that these intentions are mostly specifications. The displayed experiments neither establish competitiveness against strong implementations nor isolate the compiler's contribution from caching and delivery engineering.

## Major concerns and required changes

### 1. The headline baseline may leave the assigned budget unused

**Anchors:** Abstract; Section V-A, “Unoptimized single-GPU baseline”; Section V-B; Figure 4(a); Figure 5.

The sentence “It uses demand-driven staging with profile placement, dynamic CPU retention, and overlap disabled” is syntactically ambiguous: are all three mechanisms disabled, or only overlap? Figure 5 implies that placement and retention are added later. State an explicit configuration for every baseline.

More fundamentally, identical memory caps mean identical upper limits; they do not establish comparable use of those limits. If streaming stages only the demanded expert and discards it while MECC retains tens of GB, the headline 3.0–3.3× comparison largely establishes the value of using available memory. That remains a valid pedagogical floor, but it is weak evidence for the proposed compiler or coordinated runtime. Conversely, if streaming already retains experts, its policy and differences from “Three-tier LRU” need specification.

**Writing/design fix:** Provide a configuration table stating initial allocation, runtime admission/eviction, actual usable resident capacity, mirrors, staging, overlap, and prefetch for every policy. Lead the main claim with a competitive cache comparison; retain streaming as a floor.

**Evidence blocker:** Measure actual allocated and peak physical bytes for every policy, including whether the baseline consumes the available residency budget. Run a baseline that exploits the same usable capacity, loader, kernels, pinning, and transfer machinery. A common cap alone cannot close this issue.

### 2. Local mechanism adapters do not establish state-of-the-art competitiveness

**Anchors:** Section V-A, “Cache baselines”; Section V-B; Section VI; Figure 4(a).

The authors appropriately disclaim reproducing the cited systems, but RF and SSD-native adapters remain unspecified algorithms. The reported 1.25–1.42× advantage could arise from omitted prediction, admission, packing, transport, batching, tuning, or scheduling. The paper itself describes mechanisms absent from its adapters. MoE-CORE is particularly close to the profile/allocation/online-residency combination and is deferred to future experiments.

**Writing/design fix:** Publish adapter pseudocode and tuning rules, and limit claims to those implementations. Explain which external mechanisms are preserved, omitted, or inapplicable.

**Evidence blocker:** Evaluate credible strong baselines, preferably versioned actual systems where feasible. At minimum, include carefully validated exact-execution paths for the closest coordinated-residency and SSD systems, with equally tuned configurations and documented incompatibilities. Equalize model semantics and physical resources without arbitrarily stripping useful lossless mechanisms from competitors. Native deployment comparisons can supplement controlled mechanism comparisons. The present adapters cannot stand in for this work.

### 3. The cumulative ablation does not isolate the three claimed contributions

**Anchors:** Sections II-B–D, III-A–C and V-D; Figures 2 and 5.

The 24→18→11→8 s stack provides order-dependent incremental gains. It cannot establish the independent contribution of placement, retention, or overlap, and it covers only the first workload. Placement also conflates cross-layer capacity allocation with initial expert ranking. Figure 2(a) reallocates CPU slots, whereas V-D says the placement comparison varies “only initialization.” Those are distinct interventions and should not share an undifferentiated label.

Figure 2(b) compares policies with different duplicate coverage, but supplies no displayed duplicate-byte, unique-coverage, migration, or global-LRU result. Since the controlled exclusive policy matches global LRU, that reference is essential to explain whether the gain is ordinary effective capacity, migration behavior, or a distinctive MECC decision. Figure 2(c) shows three curves, not the complete profile/random × static/adaptive crossing asserted in II-D. Missing random-static, mismatch, uniform, and no-shift results cannot be inferred from the illustration.

**Writing/design fix:** Separate allocation, initialization, retention, and scheduling in terminology and configuration tables. Identify each trace, request count, denominator, and configuration. Replace statements implying completed full controls with their actual status.

**Evidence blocker:** Run matched allocation/initialization controls, leave-one-out or factorial combinations, and an exclusive global-LRU reference. Report physical duplicates and migration costs. Repeat the essential controls across models and workloads. Use real held-out routes for mechanism relevance; synthetic shifts and histogram-preserving shuffles test mechanisms but do not establish natural drift or end-to-end gains. The separate 12% and 20% miss targets are disclosed and are not an arithmetic contradiction, but their different workloads preclude connecting them causally without additional data.

### 4. The SSD regime and resource feasibility require quantitative proof

**Anchors:** Sections II-A, IV, V-A and V-E; Figure 6(a); `assumptions.json` memory entries.

Document exact expert bytes, dense bytes, and effective unique HBM+host capacity for each model. CPU insufficiency alone does not quantify whether combined usable fast-tier storage forces sustained SSD demand. Cold reads at initialization also do not demonstrate steady-state capacity pressure: every cold-start cache reads backing storage at least once. Show ongoing timed decode reads and a capacity calculation. A host-fit two-tier control is mentioned but not displayed.

The nominal 50 GB expert allowance in V-A and the 70 GB total target in IV lack a fully labeled GPU breakdown; `gpu_parts=[42,22,4,2]` is not self-describing. The 40 GB host target exactly exhausts its cap, leaving the treatment of allocator overhead, transient peaks, and charged page cache important. A single target breakdown cannot validate both model sizes, all policies, and all host caps.

**Writing/design fix:** Specify GB/GiB, component identities, budget enforcement, allowed OS page cache, direct/buffered I/O, cold-cache procedure, host limits, and failure rules. State an exact capacity threshold rather than relying on model names.

**Evidence blocker:** Audit peak bytes per configuration, including transient copies and page cache, with enforced caps. Extend budget sweeps through the SSD-to-host-fit boundary and include HBM sensitivity. Report demand-source shares alongside actual timed SSD/H2D/D2H bytes; prefetch can reduce demand misses while increasing physical I/O.

### 5. Timing semantics and the nine-token crossover are incomplete

**Anchors:** Sections IV, V-A, V-B and V-E; Figure 6(c).

The arithmetic 30+8n = 12+10n gives n=9 for the displayed initialization-plus-decode model. It is not a full request break-even point. Profiling, model loading, prefill, and first-token production are excluded, and the figure title “Include the cost of the prior” overstates what is included if profile generation is excluded. No SSD-native TTFT is displayed, so a complete crossover against that adapter cannot be reconstructed. Define whether n counts generated tokens or post-first-token intervals; with TTFT separated, N outputs normally contribute N−1 later intervals.

**Writing/design fix:** Define TPOT's denominator, EOS/output truncation, warmup state, TTFT start/end, initialization boundaries, and a complete request-time equation. Label the plotted intersection as a restricted illustration. Explain whether profiling is amortized across requests and over what service lifetime.

**Evidence blocker:** Measure full cold-start and warm-service request costs, profile generation and plan loading, and output-length sweeps. The only displayed batch is one; prefill executes many routed token-expert pairs and cannot inherit decode cache semantics without specification. Add input-length and batch/concurrency tests, define request-vs-token throughput, and report latency distributions. Pinning, batched H2D within a request, and serving batch size are separate dimensions.

### 6. Statistical evidence and reproducibility are absent

**Anchors:** Section V-A, “Models and workloads” and “Metrics”; Figure 4; `illustrative_repeat_factors`.

Three authored ±3% factors are neither independent repetitions nor confidence intervals. Even conditional on correct displayed means, no sample counts, prompt distribution, run-order controls, variance sources, or uncertainty in paired speedups are established. Four model/domain means do not quantify workload robustness. “QA” and “Code” are not reproducible datasets; the draft explicitly leaves model, dataset, and input revisions unfrozen.

**Writing/design fix:** Freeze revisions, prompt selection, profile/evaluation separation, routing extraction, decoding, repetitions, hardware topology, SSD/CPU/software configuration, and baseline tuning before execution. State aggregation and interval construction.

**Evidence blocker:** Collect independent repeated runs and diverse paired prompts with randomized or counterbalanced execution order, controlled cache state, and thermal/I/O conditions. Report request-level latency distributions and paired uncertainty, separating prompt variability from rerun variability. Publish raw timing and traffic records. A narrow repeated synthetic spread cannot establish significance.

### 7. The multi-GPU comparison is an allocation illustration, not an efficiency result

**Anchors:** Section V-C; Section V-E; Table I; Figures 4(b) and 6(b).

Table I correctly computes 1×8 = 8×1 GPU-s/token. This equality does not demonstrate lower energy, lower monetary cost, or improved throughput. Importantly, Figure 6(b)'s two-GPU resident point is 2.8 s/token, or 5.6 allocated GPU-s/token, and is both faster and lower in nominal GPU-time than the one-GPU 8 s/token target. The eight-GPU reference should therefore not anchor a broad resource-efficiency claim. Single-GPU feasibility can still matter when only one GPU is available.

The multi-GPU MECC targets require an implementation beyond the specified single-GPU runtime. Define expert/model/tensor parallelism, per-device and aggregate host/HBM budgets, interconnect, overlap, and routing communication. Explain why an eight-GPU MECC configuration remains slower than a resident configuration at the same GPU count, and whether both could select residency when the full model fits. Otherwise the frontier may compare artificially fixed policies rather than each method's best feasible configuration.

**Writing/design fix:** Retain the allocation distinction, state the intended latency SLO and deployment constraint, and report the smallest feasible resident configuration prominently. Avoid cost/energy language unsupported by measurements.

**Evidence blocker:** Validate partitioning and memory feasibility, tune resident and MECC configurations at each GPU count, and compare equivalent service loads. For economic claims, include measured host/SSD/communication costs and utilization. For resource savings, measure minimum resources at an explicit latency or throughput target; the reverse comparison is currently only planned.

### 8. Exactness must be established at execution level

**Anchors:** Section III-C; Section V-E; `quality` assumptions.

The proposed hashes, expert-selection checks, synchronous reference, logits, tokens, and perplexity are appropriate. Hash equality alone cannot establish correct buffer lifetimes or readiness. Even a measured zero-error target needs a defined corpus, token count, eviction pressure, synchronization regime, and tolerance. The provenance ledger records historical fairness, synchronization, and timing-window concerns; their existence is not proof of a defect in this draft's proposed implementation, but historical measurements cannot automatically discharge these obligations.

**Evidence blocker:** Execute and document paired synchronous/asynchronous checks across cache hits, SSD misses, evictions, staging reuse, and relevant workloads. Freeze deterministic settings and numerical tolerances. Keep quality evaluation outside performance counters. A correctly measured tiny displayed example would still not establish broad runtime correctness.

## Figure/table and metric consistency

The plotted TPOT targets, Figure 5 cumulative sequence, Figure 6 budget/scaling targets, and Table I arithmetic agree with the supplied assumptions at the level inspected. The PDF consistently marks outcomes as hypothetical. The strong-baseline gain range and streaming speedup range are arithmetically consistent. There is no need to invent a numerical contradiction where the draft already distinguishes different controlled traces or different metrics.

Remaining presentation weaknesses matter experimentally: Figure 2(a) shows miss shares but not the actual per-layer slot allocation or weighted aggregate denominator; Figure 2(c) omits one cell of the claimed 2×2 design; physical traffic and unique coverage are promised rather than displayed; throughput is listed as a metric without reported throughput results; TTFT lacks competitive cache baselines; and the GPU-memory assumptions lack labeled components. Figure 6(c)'s restricted break-even convention should not be silently interpreted as complete request latency. Compact tables or an artifact can resolve reporting space, but unmeasured entries must remain unmeasured.

## What would support 4/5

A credible accept case needs measured, reproducible SSD-bound end-to-end results against strong exact-execution baselines under audited physical caps; a competitive baseline that actually uses its assigned memory; independent evidence for allocation, initialization, retention, and overlap; correct execution under asynchronous pressure; and honest uncertainty and full-request costs. The resident reference should characterize a deployment tradeoff under a stated service requirement. Not every possible workload must be exhausted, but the closest competitor, the capacity threshold, the compiler's causal contribution, and the actual physical-resource advantage cannot remain assumptions. Text revisions can make the scope precise; they cannot supply those missing results.
