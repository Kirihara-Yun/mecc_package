# R4 — Independent simulated presentation re-review

Scope: frozen round1 manuscript.tex, manuscript.pdf, and assumptions.json only; no other reviews consulted. I inspected rendered PDF pages. This is a simulated review, not an actual committee review. The simulated scale is 1 reject, 2 weak reject, 3 borderline, 4 accept, 5 strong accept; it is not a verified official DAC scale.

**Current submission: 1/5 (reject). Conditional technical merit: 2/5 (weak reject). Prose alone: 4/5.** The conditional score assumes only that displayed numerical outcomes were measured correctly. It does not assume successful missing controls, feasible matched deployments, validated asynchronous execution, or competitive external baselines. These are acceptance scores, separate from English quality.

## Improvements that resolve presentation objections

The revision is substantially more precise. The abstract now leads with the relevant local-adapter comparison, calls outcomes illustrative targets, and includes the smallest specified resident reference. The introduction identifies a falsifiable question: whether the profile prior improves finite-horizon service over the same retention and transfer machinery. It explicitly avoids claiming novelty from combining established components.

The deployment condition now uses capacity accounting rather than startup SSD reads. Per-layer probabilities have a defined global normalization. The placement heuristic's assumptions, tie rules, complexity, and prototype limitations are stated. Global-LRU equivalence has a clear serial, per-layer scope. The overlap discussion explains when routes become available and what can overlap at batch one.

The ambiguous streaming-baseline sentence is fixed. Authored error bars are removed, categorical performance comparisons use points, and the unsupported multi-GPU MECC extension is withdrawn. The two-GPU reference exposes the GPU-time disadvantage; the offline use case makes the latency compromise concrete. Full-request cost is separated correctly from the nine-interval illustration. These changes improve scientific meaning, not merely style.

## Remaining acceptance blockers

1. **Evidence:** All results remain hypothetical. Even under the conditional assumption, unspecified adapter rules and missing external comparisons prevent a claim of competitive advantage.
2. **Feasibility and correctness:** Section IV withdraws the mirror breakdown and states that asynchronous readiness and phase counters are unvalidated. Correct numerical latency values alone would not certify matched physical budgets or unchanged computation. The paper now reports these limitations honestly, but disclosure does not establish the proposed system.
3. **Novelty:** A clearer question is a useful research plan, not an answered contribution. The closest coordinated-residency distinction and the decisive comparison remain absent.
4. **Attribution:** Exclusive-LRU, the fourth initialization/adaptation condition, duplicate/migration measurements, and factorial or leave-one-out controls remain missing. The cumulative ablation cannot settle component interactions.

## Remaining presentation fixes

- **Frozen Figure 1:** SSD appears to contain only two experts, conflicting with backing-store semantics. The communicated later working-copy repair is outside this scored artifact. Also distinguish offline profiling from the online router path visually.
- **Figure 2:** Show slot allocations, demand-weighted aggregates, trace/window definitions, and shift annotation. Its three curves and three retention bars should not visually imply the missing controls exist.
- **Frozen PDF layout:** Figures 5–6 float to page 6 after the conclusion, leaving large blank regions. Restore proximity to their analysis and improve page balance. This is a layout issue, not an acceptance blocker by itself.
- **Sections III-C and V:** “We compare” and “We report” still suggest completed operations despite explicit warnings. Use “The validation protocol compares” and “The planned measurements include” where appropriate.
- **Section V-B:** “Separates those effects” overstates what the cumulative ablation establishes. Prefer “illustrates incremental changes in one component order.”

To reach **4/5 overall**, establish a feasible, synchronized implementation; execute the stated mechanism controls; compare against concrete relevant baselines; and demonstrate a technical advantage beyond the established components. More polished English cannot substitute for these outcomes. The revision improves credibility and reviewability considerably, while leaving the underlying acceptance judgment unchanged.
