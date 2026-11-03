# R1 — Simulated review: originality, significance, and DAC fit

This is an independent simulated research review, not an actual DAC review. The scoring scale used here is **1 reject; 2 weak reject; 3 borderline; 4 accept; 5 strong accept**. It is not asserted to be an official DAC scale.

## Judgments

**Current submission score: 1/5 (reject).** The manuscript explicitly labels all experimental outcomes, repeat variation, memory peaks, and correctness checks as hypothetical. This transparency is appropriate, but the document is a design and evaluation proposal rather than a validated systems research contribution. Its elementary static-placement proposition cannot substitute for experimental support. No claim of fabrication or concealment is intended.

**Conditional technical-merit score: 2/5 (weak reject), assuming the plotted numbers were measured faithfully.** This assumption upgrades only the displayed experiments; it does not turn local adapters into reproductions, supply planned comparisons, validate undisplayed controls, or establish novelty. The assumed gains would demonstrate useful engineering under a bounded host-memory deployment. They would not yet distinguish MECC from the combination of mechanisms already described by MoE-CORE and SSD-LLaMA. The strongest reported gain is against intentionally unoptimized streaming; the closer SSD-native comparator is explicitly a local mechanism adapter. My confidence is high about the contribution-overlap concern and moderate about eventual practical impact, which depends on the unavailable implementation evidence.

## Summary and strengths

MECC proposes profile-guided initial allocation of expert weights across HBM, host memory, and SSD; exclusive promotion/demotion at runtime; and dependency-aware transfers. The deployment problem is meaningful when the effective fast-tier working set cannot retain the expert pool and requests actually reach SSD. Single-device inference under a task host-memory cap is a credible systems setting. It is also a narrower claim than general superiority of three-tier caching on any offloaded MoE.

Several aspects are unusually careful: the paper distinguishes physical traffic from demand-tier counters; charges mirrors and staging against memory caps; acknowledges that exact expert selection is available in prior work; labels adapters honestly; limits Proposition 1 to its static assumptions; and separates GPU allocation from latency and nominal GPU-time. These choices strengthen credibility. They should survive revision.

## Major concerns

### 1. The claimed insight closely overlaps prior coordinated residency

**Anchors:** Section I, paragraph beginning “Our insight”; Section I contribution list; Sections III-A–III-C; Section VI, “Coordinated residency.”

The stated insight—initialize residency from a route profile and correct it using online requests—is not sufficiently differentiated. In the supplied **MoE-CORE PDF, Sections 3 and 3.1, pp. 5–6**, decode combines nonuniform layer allocation, domain-profile initialization, history-aware replacement, and asynchronous cross-layer prefetch. Its exact execution path preserves router-selected experts; optional substitution is separate. Thus, preserving expert selection does not distinguish MECC from that exact path. MECC's inclusion of SSD is an important scope difference, but it does not by itself establish a new allocation or adaptation principle.

The supplied **SSD-LLaMA PDF, Sections 3.2–3.3, pp. 5–7, and Section 4.1, p. 7**, already describes an SSD/RAM/VRAM hierarchy, dynamically retained experts, bounded pinned buffers, asynchronous expert delivery, and per-expert readiness publication. Lossless storage and unchanged router selection are also explicit there. A GPU-executed, uncompressed configuration is a legitimate experimental scope, but restricting an existing design space is not automatically an original contribution.

**Concrete paper edit:** Replace the broad contribution inventory with a precise delta statement and a compact comparison table: what each closest system already does; what MECC changes in its planner, runtime, and objective; and which experiment isolates each change. If no new algorithm or coupling exists, describe the work as a disciplined integration and deployment study and justify that study's new findings. Do not add “first” claims or recast MoE-CORE as intrinsically approximate.

**Evidence needed:** Run faithful closest-system configurations where feasible, or explicitly validated ports of their relevant mechanisms. Compare MoE-CORE-style allocation/initialization/adaptation in the same three-tier delivery environment, SSD-LLaMA-style residency/delivery, and their straightforward combination against MECC. The decisive question is whether the proposed design contributes beyond assembling those components.

### 2. “Compiler-guided” currently names a planning phase more than a research advance

**Anchors:** Title; Section III-A, Equations (1)–(3), Proposition 1, and paragraph beginning “The multilayer implementation.”

The compiler emits ranked expert IDs and initial capacities. Proposition 1 establishes the familiar exchange argument for equal-size objects with fixed probabilities and tier costs. The text correctly concedes that the implemented sequential multilayer planner is a heuristic. However, it does not show what compilation adds beyond sorting a profile and assigning slots. Nor does it demonstrate that Zipf fitting improves decisions over empirical counts.

The formulation is also disconnected from the implemented marginal score: Equation (2) uses delivery costs, while Equation (3) uses probability coverage. The paper should define how layer invocation rates and top-k selections enter the probability normalization, and when a probability-only score is equivalent to saved delivery time. With differing expert sizes or tier cost gaps, that equivalence needs additional assumptions. This is a specification gap, not a claim that Proposition 1 itself is false.

**Concrete paper edit:** Define the planner algorithm in compact pseudocode, including tie-breaking, reserved space, minima, and infeasible plans. State its complexity and identify exactly which calibrated quantities affect decisions. Explain whether a compiled plan fixes per-layer capacities throughout serving while only identities adapt. Either motivate “compiler” through a meaningful model/hardware contract and validated optimization, or adopt the more modest term “profile-guided residency planner.”

**Evidence needed:** Compare empirical-frequency placement, Zipf placement, uniform allocation, and a small-instance exact optimum or exhaustive reference for the stated static objective. Report planning/profile cost and realized held-out latency, not only modeled coverage. Show where the planner's extra structure matters.

### 3. The runtime's cleanest property also limits its novelty claim

**Anchors:** Section III-B, final paragraph; Figure 3; Sections II-C and V-D.

The paper states that exclusive retention reproduces the SSD miss sequence of a global LRU with combined capacity in its controlled object model. This is useful for understanding correctness and coverage, but it makes the runtime difficult to present as a distinct replacement-policy advance. Gains over a fixed CPU pool or independent caches may be ordinary consequences of recovering unique capacity. CPU mirrors then trade some of that capacity back for reduced D2H traffic.

**Concrete paper edit:** State directly that the policy instantiates an exclusive hierarchy, and locate any claimed innovation in a measurable choice beyond that abstraction. Clarify that the global-LRU equivalence is per layer under matching quotas and initial stacks, rather than an unrestricted global allocator across every layer. Describe mirror admission, eviction, invalidation, and its physical budget; “an implementation can keep a CPU mirror” is insufficient for a paper whose results depend on the choice.

**Evidence needed:** A matched exclusive-LRU baseline with identical quotas, initialization, transfer machinery, and physical memory allowance is essential. Report unique retained bytes and D2H/H2D/SSD traffic. Show whether MECC wins after duplicate-capacity effects and asynchronous-copy implementation differences have been controlled.

### 4. The headline evidence does not establish the relevant comparison

**Anchors:** Abstract; Section V-A “Cache baselines”; Figure 4(a); Section V-B; Section V-D; Section V-E's planned sensitivity paragraph.

The hypothetical streaming speedup measures the whole stack against a baseline with placement, dynamic retention, and overlap disabled. Even if measured, it would support the value of implementing caching and delivery competently, rather than the originality of MECC. The RF adapter omits FlashMoE's learned predictor, and the SSD-native adapter is not SSD-LLaMA. The manuscript discloses both facts correctly; this prevents misrepresentation, but does not solve comparator weakness. Similarly, a sequential ablation cannot tell whether the final system exceeds a straightforward composition of known techniques.

**Concrete paper edit:** Center the eventual abstract and evaluation around the strongest faithful matched-budget comparator. Retain streaming as a diagnostic lower baseline. Mark each undisplayed control as planned wherever it is mentioned: Sections II-B–II-D and V-D sometimes describe full comparisons in present tense, despite Section V-E explicitly saying key cases remain planned. Replace authored spread with measured repeated-run uncertainty only when such runs exist.

**Evidence needed:** Closest-system comparisons; factorial or leave-one-out controls for planner/retention/overlap; natural held-out routes; profile mismatch and uniform-access controls; and complete request-cost accounting. Hypothetical figures becoming measurements would not automatically provide these missing cases.

### 5. Significance and DAC relevance need a sharper deployment argument

**Anchors:** Section II-A; Section IV memory breakdown; Sections V-C and V-E; Figures 4(b) and 6.

The host-cap setting is plausible, but the paper should establish that the cap corresponds to an actual deployment constraint and not an arbitrary restriction selected to create SSD pressure. An A100 with a host allowance smaller than its device memory can occur under shared tenancy; that arrangement deserves a concrete workload and enforcement description. Report effective unique HBM-plus-host residency after non-expert state, mirrors, and buffers. Merely failing to fit the model in CPU memory alone does not prove unavoidable SSD demand if disjoint GPU residency supplies the remaining capacity; the paper appropriately invokes combined working-set pressure and should quantify it.

The assumed single-GPU latency remains many seconds per output token. Reduced allocated GPU count could still matter for offline or low-duty-cycle workloads, but the paper needs to identify those workloads and evaluate their useful operating points. An eight-GPU reference is contextual; the smaller feasible resident reference and a minimum-resource comparison at a latency target are more informative. Equal GPU-seconds do not imply equal energy or monetary cost, a distinction the paper already makes well.

DAC fit is plausible through memory-hierarchy optimization and hardware-aware mapping. It is weaker if “hardware/software co-design” means only using standard CUDA streams with an offline popularity sort. A concrete decision that changes with measured SSD/PCIe characteristics, and a validated capacity/latency tradeoff, would make the design-automation relevance substantive. I am assessing technical fit here, not asserting a verified DAC track requirement.

## What would make a 4/5 defensible?

A credible accept case requires all of the following, rather than cosmetic reframing:

1. Measured, reproducible SSD-active end-to-end evaluation, with frozen inputs and model revisions, enforced physical budgets, traffic counters, and completed correctness checks.
2. A precise technical delta from MoE-CORE's coordinated allocation/initialization/adaptation and SSD-LLaMA's three-tier delivery, supported by faithful matched-budget comparisons. If an existing component combination matches MECC, the novelty claim must change.
3. Evidence that the proposed delta explains the gains after equalizing exclusive coverage, mirroring, buffering, overlap, and initialization. Include representative failure cases and mismatch sensitivity.
4. A reproducible planner specification tying its objective to actual decisions, plus measured profile/planning amortization and a useful deployment operating point.

The most fatal current issue is the complete absence of measured validation. Under the requested conditional assumption, the most serious remaining blocker is unestablished originality relative to the closest supplied work. The problem definition, algorithm specification, contribution wording, baseline labels, planned-versus-completed descriptions, and deployment framing are fixable within the paper. Establishing a material technical advantage requires new evidence and may require a stronger method; wording alone cannot guarantee an accept.

## Reading scope

Cold-read materials: frozen round0 `manuscript.tex`, rendered `manuscript.pdf`, and `assumptions.json`; repository `AGENTS.md` and `docs/APPLICABILITY.md` for the stated research boundary; and the supplied local MoE-CORE and SSD-LLaMA primary PDFs, especially the sections identified above. No implementation inspection, experiments, manuscript edits, or external search were performed. Numerical performance statements in this review concern the manuscript's hypothetical scenario only; they are not promoted to verified repository results.
