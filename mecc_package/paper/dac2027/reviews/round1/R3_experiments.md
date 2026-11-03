# R3 — Independent simulated experimental review, round 1

This is a simulated DAC review, not an actual reviewer report. I independently read the frozen round1 TeX, seven-page PDF, and assumptions file, without consulting other reviews. All discussed outcomes remain explicitly hypothetical.

**Scale:** 1 reject; 2 weak reject; 3 borderline; 4 accept; 5 strong accept.

**Current score: 1/5 (reject).** This is a substantially more candid design draft, but no performance, physical feasibility, uncertainty, or execution-correctness evidence has been established.

**Conditional score: 2/5 (weak reject)** if the displayed numerical outcomes were measured correctly. This assumption grants neither unreported controls nor missing implementations and comparisons. Correct plotted outcomes alone would still not isolate the proposed compiler or establish competitiveness.

## Substantive improvements

The revision corrects several consequential interpretations. Section II-A now defines combined unique fast-tier capacity and distinguishes sustained SSD demand from startup reads. Section V-A unambiguously disables all three streaming optimizations. Section IV withdraws the physically incompatible full-mirror budget rather than presenting it as feasible. Figure 4 removes invented uncertainty bars. Sections II-C–D and V-D acknowledge missing exclusive-LRU and factorial controls. Section III-C explains what batch-one routing actually reveals and no longer treats a copy stream as proof of overlap.

Table I and the abstract now prominently include the two-GPU resident point: its hypothetical 5.6 GPU-s/token beats single-GPU MECC's 8, while also reducing latency. The unsupported multi-GPU MECC curve is removed. Section V-E correctly defines request cost using TTFT and n−1 decode intervals and restricts the nine-interval intersection to its plotted terms. These are meaningful fixes to framing and experimental specification; they do not constitute new evidence.

## Remaining acceptance blockers

1. **Budget use and competitiveness (V-A–B; Figure 4).** Streaming occupancy remains unspecified. Equal caps do not show that the weak baseline uses its assigned memory. RF's rule is not frozen, SSD-native remains a local adapter, and the closest coordinated-residency comparison is deferred. Measure a fully utilized, equally engineered cache baseline and credible external exact-execution paths, especially the closest allocation/profile/residency system. Publish configurations and tuning rules. The narrowed introduction makes superiority over the same retention/delivery stack the central question, but no such clean comparison is displayed.

2. **Causality (II-B–D; V-D; Figures 2 and 5).** Cumulative 24→18→11→8 targets remain order-dependent. Separately vary layer allocation and initial identities; complete the initialization×adaptation crossing; compare exclusive per-layer LRU with matching initial stacks; quantify duplicates, migration, and exposed transfer time. Repeat essential controls on held-out real routes. Four model/domain means and an authored drift trace cannot establish the proposed finite-horizon advantage or its robustness.

3. **Physical feasibility and correctness (III-C; IV; V-E).** The acknowledged mirror contradiction leaves no validated replacement configuration. Enforce caps and audit transient allocations, mirrors, staging, and page cache for every policy and budget. Show sustained decode SSD bytes alongside demand shares. Validate synchronous/asynchronous equivalence under misses, eviction, and buffer reuse. Test the host-fit boundary and HBM sensitivity; do not extrapolate the current capacity curves to an SSD-free regime.

4. **Statistics and request semantics (V-A; V-E).** Freeze datasets, model/input revisions, profile splits, adapter policies, repeat design, and machine configuration. Supply paired prompt-level distributions and measured uncertainty. Measure competitive-baseline TTFT, profile/loading amortization, full-request crossover, prefill behavior, input/output lengths, and batch/concurrency effects. The stated complete sensitivity matrix remains planned.

## Reporting fixes still possible without new experiments

Change “Section V-D separates those effects” in V-B to acknowledge cumulative targets. Replace completed-action wording such as “We compare” in III-C where tests remain unperformed. Mark withdrawn memory and multi-GPU entries in `assumptions.json` as archived; they remain machine-readable without the manuscript's qualification. Report promised throughput and physical traffic only when available. The displayed arithmetic is consistent, and the corrected GPU comparison no longer supports an efficiency claim. Achieving 4/5 requires the missing causal, competitive, resource, and correctness evidence, not additional disclaimers.
