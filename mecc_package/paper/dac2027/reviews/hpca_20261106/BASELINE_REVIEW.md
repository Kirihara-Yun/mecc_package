# R00: HPCA-style cold read

Conditional recommendation: **2/5, weak reject**. Writing: **3/5**. This is a simulated assessment under the protocol in this directory. The numerical targets are held fixed and granted as conditional inputs; their unmeasured status is not the reason for this recommendation.

## Summary

MECC combines per-layer initialization, HBM/CPU victim retention, and delivery of router-selected experts. The target setting has bounded host allocation and cold expert demand. The figures now explain this setting, and the paper has enough material to support a focused systems argument. The present argument still relies on the existence of three components rather than showing a technical distinction in how they interact.

## Major issues

**R00-N1 — The nearest prior work changes the novelty question.** MoE-CORE already combines nonuniform capacity, domain initialization, and online replacement (supplied PDF, pp. 2 and 5–7). SSD-LLaMA already manages RAM/VRAM retention, can keep a VRAM victim in RAM, and coordinates I/O readiness (supplied PDF, §§4.1–4.2, pp. 7–8). Listing those capabilities cannot establish a difference. The paper must identify the exact decisions it studies and describe the related systems before claiming an unmet need. A slower backing device is a deployment condition, not an algorithmic contribution.

**R00-M1 — The compiler's input and guarantees exceed the implementation.** The text allows arbitrary layer weights and empirical allocation. The inspected `compile_plan` uses an equal-weight, fitted-Zipf marginal scan. It reserves one slot per layer in each tier. It does not reject every budget that violates those minima. The paper needs a concrete supported regime, slot definitions, and admissibility constraints. It must not imply a cost-aware optimizer or a globally optimal joint allocation.

**R00-M2 — Delivery describes an event pipeline that the caller does not implement.** `TieredSparseMoe.forward` submits disk futures for prefill. `LayerExpertCache.load_experts` waits on the copy stream before yielding CUDA weights. Decode does not issue the same disk-future batch. The figure can illustrate a prefill schedule; the text cannot claim that schedule as the measured decode mechanism. Stream ordering, storage lifetime, and policy membership are different responsibilities.

**R00-M3 — The logical reuse rule needs an execution scope.** Concatenating HBM and CPU orders describes exclusive serial LRU. Batched host promotions, temporary device copies, and retained host mirrors need separate treatment. The first use of MRU/LRU is undefined. The current text also says an in-flight entry cannot be evicted; recording a CUDA stream protects tensor storage, which is a different statement.

**R00-S1 — Repetition consumes space without advancing the argument.** The Introduction explains bounded storage several times. Overview repeats the same three decisions. Related Work gives generic distinctions after grouping the closest systems in one sentence. Some Evaluation sentences describe why a comparison is needed rather than what the plotted comparison means.

**R00-L1 — Short sentences alone are insufficient.** The baseline sentence audit already has a mean of 13.76 words. Most of the writing problem is repeated content, vague objects ("this decision", "useful", "the same execution interface"), and long noun chains. Splitting sentences without clarifying their subjects would not solve it.

## Changes required for the next review

Define the actual compiler inputs, capacities, minima, and output. Distinguish the serial replacement rule from batched execution and physical copies. Describe the implemented prefill/copy synchronization path. Then restructure the argument around initial coverage, surviving a tier crossing, and correcting profile mismatch. Give SSD-LLaMA and MoE-CORE specific descriptions. Preserve the four-part Introduction and all data.

## What would justify 5/5

A precise and consequential technical distinction from the closest systems, supported by the comparisons that distinguish that decision. The existing data plots, even granted as valid, do not automatically establish this distinction. A perfect English score would not supply it.
