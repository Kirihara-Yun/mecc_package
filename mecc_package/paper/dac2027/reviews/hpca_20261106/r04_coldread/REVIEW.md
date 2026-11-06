# R04: final cold read of this editing cycle

**Conditional recommendation: 3/5, borderline.** Writing: **4/5**. Confidence: **4/5**. This uses the local five-point rubric. It is not an actual HPCA committee decision. The assessment grants the displayed target outcomes; it does not penalize their unmeasured status.

## What is now clear

The Introduction has the requested four roles. It defines the task allocation, identifies the nearest systems, presents the lifecycle, and states three contributions. The two fast tiers avoid different portions of delivery. Background defines the MoE operation, layer/expert identity, and the prefill/decode distinction. Method specifies the marginal allocation, serial replacement rule, host mirrors, read/copy dependencies, and consumption ordering. The framework's labels match that account.

The timing acronyms and recency/frequency adapter are defined. Startup is interpreted through initialization divided by output length plus decode time. The one-GPU comparison keeps response time separate from GPU occupancy. The original data, yellow panel titles, and four-part Introduction are preserved. The exact wording "ILLUSTRATIVE TARGET" does not appear in any new manuscript PDF.

The wording uses short sentences and removes promotional emphasis. The lexical audit has no listed tone terms and no detected prose sentence above 25 English words. I have no remaining major English or section-order objection. The audit is a screening tool; it does not certify native authorship or technical acceptance.

## Why this is still not 5/5

**1. The stated contribution remains a composition of established decisions.** SSD-LLaMA already coordinates disk delivery and two bounded resident tiers, including host retention of GPU victims. MoE-CORE already combines nonuniform allocation, profile initialization, and online replacement. MECC now describes a narrower composition accurately. The displayed results, even granted, do not establish a distinct architectural result over equivalently initialized exclusive retention with the same delivery path. This is the same substantive concern found in R02 and R03.

**2. The prototype does not yet support the full compiler-to-runtime claim.** The library accepts per-layer skew parameters, but the e2e CLI generates them outside uniform mode instead of using calibrated layer estimates. The inspected I/O adapter also has a weight-entry representation mismatch with the common engine. Writing can expose these facts; it cannot repair the execution contract.

**3. Logical and physical budgets remain different objects.** Retaining a host mirror for each GPU expert changes how much host memory the plan consumes. The paper now states this distinction. It does not yet turn it into a physical-memory-constrained placement decision. The scope is therefore a logical-slot study, not a demonstrated byte-feasible compiler under an enforced host cap. Granting every plotted latency does not supply that missing resource constraint.

## Decision after four revisions

Further adjective removal or more favorable hypothetical bars would not resolve these three points. I would not assign 5/5 to the present technical contribution. I retain **3/5** rather than changing the scale or silently granting undisplayed mechanisms. The next useful iteration needs a research/implementation change. A concrete route is described in `../TECHNICAL_NEXT_STEPS.md`.

The baseline and each of the four revision PDFs remain separately available. No frozen PDF was overwritten.
