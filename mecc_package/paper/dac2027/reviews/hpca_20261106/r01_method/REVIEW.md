# R01: reviewing the method revision

Conditional recommendation: **2/5**. Method exposition: **3/5**. Writing: **3/5**. The recommendation still grants the displayed target values and does not penalize their absence of measurement.

## Resolved

R00-M1 now has definitions for layers, slots, minima, rank IDs, and the supported equal-size/equal-top-k regime. The marginal rule is a coverage heuristic, not a latency optimum. R00-M2 now distinguishes prefill disk-future batching from decode demand delivery. Stream synchronization replaces the unsupported per-expert event claim. R00-M3 now distinguishes serial replacement, batch preparation, logical eviction, and tensor lifetime. MRU/LRU are defined.

## Remaining

**N1 remains decisive.** The changes describe the implementation more precisely. They do not yet establish a technical distinction from the nearest prior systems. The Introduction and Related Work still imply a broad gap before acknowledging systems that cover much of it.

**S1 remains.** Overview repeats the component list instead of explaining the lifecycle. Motivation repeats the profile/recency distinction after stating it. Some Evaluation text narrates the review protocol rather than interpreting a curve. The next revision should make each section answer a different question.

**Implementation finding I1.** The e2e CLI uses generated per-layer alpha values when `--uniform` is absent (`run_e2e.py`, lines 437–448). Supplying an offline alpha profile to the compiler library is a supported input; the CLI is not an automatic calibrated-profile pipeline. The measured main configuration remains uniform. This finding is not resolved by granting ideal bars.

**Implementation finding I2.** The inspected `OursIOPolicy` uses a weight-object GPU entry, whereas the common engine's mirror/demotion path expects a `(gpu, host)` pair. This is a code-contract issue to resolve separately. The revision does not claim that this adapter proves a decode-overlap contribution.

## Next revision

Rewrite the Introduction with the same four roles. Explain that preserving a GPU victim is a choice under bounded host retention, rather than claiming that three-tier caching is new. Describe MoE-CORE and SSD-LLaMA directly. Keep the implementation and data fixed. Remove repeated explanations before splitting individual sentences.

The PDF remains six body pages plus one reference page. All 15 figures share a page with their first explanation. No undefined references or overfull boxes are reported.
