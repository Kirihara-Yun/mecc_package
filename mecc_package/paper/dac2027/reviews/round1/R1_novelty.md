# R1 — Round 1 simulated novelty review

Independent simulated review, not an actual DAC review. Scale: **1 reject, 2 weak reject, 3 borderline, 4 accept, 5 strong accept**; this is not a verified official DAC scale. I read the frozen round1 TeX, PDF, and assumptions, without consulting other reviewers' reports. Prior-art assessment refers to the supplied primary MoE-CORE and SSD-LLaMA PDFs examined in my first review.

**Current submission: 1/5 (reject).** All experimental outcomes remain hypothetical, and Section IV now explicitly identifies unvalidated implementation contracts and infeasible archived memory accounting. This is a more credible research proposal, but still lacks validated research results.

**Conditional technical merit: 2/5 (weak reject)** if the displayed outcomes become faithful measurements. This condition does not supply missing comparisons, prove cap feasibility, or resolve undisplayed synchronization checks. Even granting feasible measurements of every displayed latency, originality remains unestablished.

## Substantive repairs

The revision substantially improves claim precision. Section I explicitly acknowledges that popularity placement, LRU, and event-based overlap are established mechanisms, and asks a narrower finite-horizon question. It clarifies that layer capacities remain fixed while expert identities adapt. Section III-A defines layer selection weights, limits the probability-only score to appropriate cost assumptions, specifies tie-breaking and complexity, and distinguishes the intended contract from the prototype. Section III-B correctly restricts LRU equivalence to serial per-layer demands with matching initialization.

Section II-A now states combined unique-residency pressure and distinguishes sustained SSD demand from startup reads. Sections II-C–II-D acknowledge missing exclusive-LRU and factorial controls. Section IV withdraws the incompatible mirror breakdown. The abstract centers the local comparator and smallest feasible resident alternative; Table I exposes the two-GPU reference's lower nominal GPU-time. Authored uncertainty and unsupported multi-GPU MECC points are removed from figures. These are meaningful repairs to interpretation, not evidence of additional performance.

## Remaining acceptance blockers

**1. A better question has not yet become a new contribution.** Section I's finite-horizon prior-plus-online question is worthwhile, but MoE-CORE already combines layer allocation, domain initialization, and adaptive residency; SSD-LLaMA already manages three-tier retention and asynchronous delivery. Their relevant exact paths preserve selected experts. Section VI describes this overlap honestly but provides no precise technical delta. A new deployment budget alone does not establish algorithmic novelty. Add a compact mechanism comparison and identify what MECC changes beyond a straightforward composition. Alternatively, develop a measurement-driven characterization contribution with findings unavailable from the existing mechanisms.

**2. The decisive baselines are still absent.** Sections V-A–V-B compare hypothetical local adapters whose rules are not fully frozen. A measured gain over such adapters would establish only that implementation-specific comparison. Require faithful closest-system configurations or validated mechanism ports, including MoE-CORE-style allocation/initialization within the same three-tier delivery stack. Compare against exclusive LRU with identical quotas, initial stacks, mirroring, and overlap. Isolate layer allocation from initial identities and report finite-horizon total cost including profiling and TTFT. Do not assume the planned controls succeed.

**3. “Compiler-guided” remains stronger than its demonstrated content.** Section III-A now specifies a reasonable ranking heuristic, but calibrated delivery costs affect the reference objective more visibly than the actual decisions. Show an input-to-decision example and measured advantage over empirical-frequency sorting and uniform allocation. The elementary proposition is useful exposition, not sufficient novelty. DAC relevance is plausible through hardware-aware memory planning, but requires validated decisions and resource tradeoffs rather than the label alone.

**4. Implementation feasibility remains a prerequisite.** Sections III-C and IV disclose unresolved readiness, mirroring, and counter issues. These disclosures improve honesty but leave the hypothetical gains unsupported. Replace them with a validated concrete memory policy, synchronization results, phase-specific traffic, and enforced physical caps before claiming a functioning system.

For **4/5**, I need reproducible SSD-active measurements, a defensible technical or characterization delta, faithful closest-baseline evidence, and mechanism controls that explain its benefit. The writing repairs remove several overclaims; they do not remove the central novelty and evidence blockers.
