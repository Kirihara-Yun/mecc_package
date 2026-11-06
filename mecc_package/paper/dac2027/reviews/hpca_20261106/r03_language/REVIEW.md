# R03: reviewing language, mechanism labels, and interpretation

Conditional recommendation: **3/5**. Writing: **4/5**. Narrative: **4/5**. The current numerical targets are again granted; none were changed.

## Resolved

The causal wording in the opening now separates sparse arithmetic from expert availability. The abstract reports decode speedup rather than an ambiguous whole-request rate. Motivation explains marginal coverage, victim retention, and membership updates as distinct decisions. The framework preserves its geometry while replacing three inaccurate labels: CPU resident memory, layer skew, and copy/use ordering. Its labels now agree with the method text.

The lexical audit finds no listed tone or promotional terms. The mean is 11.8 English words per sentence; all detected prose sentences are at most 25 words. These statistics support the requested short-sentence style but are not a quality score by themselves.

## Final cold-read repairs

1. Expand MoE in the abstract. Define HBM/HDD at first use in the Introduction. Define TTFT and TPOT where timing is introduced.
2. Explain RF as the recency/frequency adapter. Its CPU replacement score is not the trained FlashMoE model. This is a naming issue, not a request to invent a stronger result.
3. Add a short MoE equation and phase distinction in Background. This lets a reader understand prefill read batching before reaching Method.
4. Interpret the startup panel with its actual amortization expression. Replace phrases such as "this check exposes" with a direct reading of the curves.
5. Complete first-page and second-page use with these explanations. Do not enlarge fonts or repeat the contribution list.
6. Remove the remaining defensive comparison wording. State what is fixed and what is compared.

## Recommendation constraint

R00-N1 remains after the narrative repair. The paper now acknowledges the overlapping mechanisms but does not supply a technical result that distinguishes their composition from equivalent exclusive retention and initialization. R01-I1/I2 are implementation-contract issues, independent of granting ideal outcomes. The next revision can finish the writing repairs. It cannot turn those open issues into a strong-accept result merely by changing adjectives or the displayed targets.
