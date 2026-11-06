"""Section order and prose for the evidence-backed DAC reading copy."""

from __future__ import annotations


FRONT = r"""\section{Introduction}
Mixture-of-experts (MoE) models increase parameter capacity while activating only a few experts per token~\cite{shazeer,switch,mixtral,deepseekmoe}. Deployment must still keep every expert addressable because a later token may select a different subset. This paper studies single-GPU inference when the expert set exceeds HBM and cannot be retained entirely in the host memory assigned to a task. The remaining weights reside on HDD. A selected expert must then be read into host memory and copied to the GPU before execution. Routing is resolved layer by layer, so the current gate does not reveal the next layer's expert demand. At batch one, a demand read can delay the next decoding step. Dense layers, KV cache, and staging buffers also compete with experts for HBM. The problem is to reduce these deliveries under fixed fast-tier allowances while preserving the model's original routing and weights. This setting matters for local inference and shared servers, where one task may receive only part of the machine's physical memory.

Existing systems address several parts of this problem. Multi-GPU expert parallelism distributes resident weights across accelerators~\cite{deepspeedmoe,tutel,flashmoedist}. Single-GPU offloading systems exploit activation traces, CPU execution, prefetching, or transfer pipelines~\cite{offloading,moeinfinity,fiddler,lightning,promoe}; SSD-LLaMA and edge FlashMoE further optimize disk delivery and replacement~\cite{ssdllama,flashmoe}. These mechanisms make initial placement, admission, and retention consequential choices. A fixed host pool can lose an HBM victim that was not retained on the host. Independently updated caches can also spend slots on copies of the same expert. Preserving reuse across this boundary is a distinct decision from predicting the next expert or reducing the bytes transferred per miss. A remaining question is how a profile-derived initial state and online replacement should coordinate HBM and host residency when some experts must stay outside both tiers. Figure~\ref{fig:intro} isolates the runtime aspect with local controls on one A100. Separate HBM/CPU caches take 32.94~s per decode token, versus 7.38~s with joint retention under the same nominal slots and initialization. Their reported HDD-demand shares are 47.9\% and 12.5\%, respectively. These observations motivate preserving reuse across the tier boundary; they do not constitute a reproduction of the cited systems.

\begin{figure}[H]
\centering\includegraphics[width=\columnwidth]{measured_figures/intro_evidence.pdf}
\caption{Local retention controls on one A100 with Mixtral-8x7B. Separate denotes independently managed HBM/CPU caches. All policies use the same nominal slots and eight-prompt input. HDD-demand share includes all instrumented phases. One run per policy.}
\label{fig:intro}
\end{figure}

We present \mecc{}, the MoE Expert Cache Compiler, to connect initial placement with runtime retention. An independent route profile supplies an expert-demand prior. The compiler ranks experts within each layer and allocates HBM and CPU slots under the task's allowances. Each plan retains the profiled layer/expert IDs, since equal indices in different layers refer to different weights. At runtime, the unchanged router provides actual demand. A CPU hit promotes the selected expert and retains the displaced HBM expert in CPU memory, preserving it for later tokens. Online recency changes the resident identities as the workload changes, while the compiled capacities remain fixed. Weight delivery orders reads, copies, and GPU consumers through readiness dependencies. These decisions address different parts of the same lifecycle: the profile selects an initial state, joint retention preserves reuse, and the delivery contract makes requested weights available before execution. The current A100 evaluation uses uniform initialization to examine runtime behavior independently of a profile-placement gain.

This paper makes three contributions. \textbf{(1) Placement compilation:} we define a per-layer interface that maps route profiles and task allowances to ranked expert IDs and initial tier capacities, together with a marginal-coverage allocation heuristic. \textbf{(2) Joint retention and delivery:} we specify promotion, victim demotion, and readiness dependencies across HBM, CPU pinned memory, and HDD while retaining the router and FP16 weights. \textbf{(3) Single-GPU evaluation:} we implement an end-to-end harness and compare the runtime with streaming, fixed-CPU retention, independent caches, and local alternative policies on Mixtral-8x7B. With uniform initialization, MECC takes 7.38~s per output token, compared with 13.04~s for streaming and 21.75~s for fixed-CPU retention; the latter two controls report the same sample perplexity as MECC. The evaluation also examines source-tier demand and host-slot sensitivity.

\clearpage
\section{Background}
\label{sec:background}
\subsection{Sparse Execution and Deployment Choices}
For layer $\ell$, a router selects $k_\ell$ of $N_\ell$ experts for each token. Only those experts execute, but any of the $N_\ell$ may be selected by a later token. Switch Transformer and GShard establish the sparse-routing model~\cite{switch,gshard}; Mixtral, DeepSeekMoE, and DeepSeek-V2/V3 show large language-model instances~\cite{mixtral,deepseekmoe,deepseekv2,deepseekv3}. The active parameter count does not by itself specify the required storage capacity.

With enough aggregate GPU memory, expert parallelism places weights on several GPUs and routes token activations to them. DeepSpeed-MoE, Tutel, and MegaBlocks develop execution and scheduling mechanisms for distributed MoE workloads~\cite{deepspeedmoe,tutel,megablocks}. Distributed FlashMoE fuses dispatch, compute, and combine into a persistent kernel~\cite{flashmoedist}; HarMoEny balances token work across GPUs~\cite{harmoeny}. These are relevant deployment alternatives, but their published multi-GPU operator numbers are not single-A100 baselines. Mixtral 8x22B provides a second example of how expert capacity can grow beyond a single card~\cite{mixtral22}.

For one GPU, HBM must also hold dense layers, activations, and KV cache. PagedAttention and SGLang address other parts of the serving-memory and execution problem~\cite{pagedattention,sglang}. CPU memory can retain additional experts; a backing store retains the rest. A miss moves weights from the selected source before the expert kernel executes. FlexGen, DeepSpeed Inference, ZeRO-Infinity, and LLM in a Flash establish related heterogeneous-memory techniques~\cite{flexgen,dsinference,zeroinfinity,llmflash}. PowerInfer exploits activation skew for CPU/GPU inference~\cite{powerinfer}. Their placement and scheduling goals motivate explicit accounting of both resident and temporary copies.

\subsection{Related Expert-Serving Systems}
SwapMoE exposes a tunable memory budget; Fiddler compares CPU expert execution with weight movement; MoE-Lightning pipelines CPU, GPU, and I/O work; and MoE-Infinity uses request-level activation traces~\cite{swapmoe,fiddler,lightning,moeinfinity}. Klotski pipelines expert-aware batches~\cite{klotski}. ExpertFlow predicts routes and schedules tokens, while ProMoE, Pre-gated MoE, and Fate prefetch experts from intermediate signals~\cite{expertflow,promoe,pregated,fate}. DAOP combines data-aware CPU/GPU execution with predictive pre-calculation~\cite{daop}. Those predictors change the information available before a gate. Our demand-only retention rule uses the unchanged gate output.

HOBBIT uses mixed-precision expert loading, and Specter pairs quantization with speculative offloading~\cite{hobbit,specter}. SSD-LLaMA coordinates disk I/O, tiered residency, and execution placement~\cite{ssdllama}. The edge-device FlashMoE learns a recency/frequency replacement rule~\cite{flashmoe}; MoE-CORE combines domain initialization, layer-specific capacities, and prefetch~\cite{core}. ZipMoE adds lossless compression and cache-affinity scheduling~\cite{zipmoe}. These systems overlap individual MECC design axes. Our local RF adapter is not a reproduction of the published FlashMoE system.

MoEpic splits experts into segments and chooses cache allocations; SliceMoE caches precision slices~\cite{moepic,slicemoe}. Mira couples predictive staging with quantized transfers~\cite{mira}. OD-MoE uses on-demand loading across edge nodes; Bevy interleaves concurrent requests during expert fetches~\cite{odmoe,bevy}. HeteGen studies heterogeneous CPU/GPU inference for dense LLMs~\cite{hetegen}. These systems change granularity, prediction, precision, or request scheduling; MECC's measured comparison is limited to the local policies defined in Section~\ref{sec:evaluation}.

\section{Motivation and Insights}
\label{sec:challenges}
\subsection{Initial Coverage across Layers}
The expert set is larger than the fast-tier slots assigned to a task. Equal slots per layer can waste capacity when layers receive different fractions of demand. The compiler can rank experts from an independent profile and allocate the next slot where it covers the most expected selections. This is an initial-state decision; it does not change router outputs. Routing locality differs across models and workloads~\cite{routingconsistency}. The current A100 main runs use uniform slots and natural expert order, so their speedup does not measure this insight's profile-guided contribution.

\subsection{Preserving Reuse after Eviction}
An HBM victim need not become cold immediately. A later token may select the same expert. Separate HBM and CPU replacement rules can leave a duplicate resident or evict a useful host copy. In a matched local control, independent caches report 47.9\% cold-tier demand and 32.94~s/token; fixed CPU retention reports 31.5\% and 21.75~s/token; joint retention reports 12.5\% and 7.38~s/token. The insight is to treat HBM and host residency as one logical reuse stack: promotion makes room for the HBM victim in host memory. The comparison motivates the runtime rule under the tested quotas; physical bytes and phase-specific I/O remain separate accounting questions.

\subsection{Correcting a Stale Initial State}
A profile describes a prior workload, not every later request. When the selected expert distribution changes, static residency can keep experts that the new workload rarely uses. The compiler therefore fixes initial capacities and ranked IDs, while online recency changes the resident identities. This division gives the runtime a way to correct a stale prior without modifying the router. A task switch requires two distinct input sets and a measured before/after trace. The present single-A100 main run does not test a switch.

"""


def revise(s: str) -> str:
    first = s.index(r"\section{Introduction}")
    overview = s.index(r"\section{Overview}", first)
    s = s[:first] + FRONT + s[overview:]
    related = s.index(r"\section{Related Work}")
    conclusion = s.index(r"\section{Conclusion}", related)
    s = s[:related] + s[conclusion:]
    s = s.replace(r"\section{Implementation}",
                  r"\subsection{Implementation and Measurement Contract}")
    s = s.replace(r"\IEEEtriggeratref{15}", r"\IEEEtriggeratref{22}")
    s = s.replace(
        "Each main policy has one completed end-to-end run",
        "The evaluation asks three questions: how much does joint retention change end-to-end latency; "
        "where are selected experts found; and how does the host-slot allowance affect both? "
        "The counters include warmup and perplexity as well as generation. We therefore report "
        "cold-tier demand share as a cache observation, not as a decode-only explanatory variable. "
        "TPOT measures the decode interval, whereas TTFT includes the first response."
        "\n\nEach main policy has one completed end-to-end run",
    )
    s = s.replace(
        "These counts span several phases, so they describe cache behavior rather than a phase-matched explanation of TPOT alone.",
        "These counts span several phases, so they describe cache behavior rather than a "
        "phase-matched explanation of TPOT alone. The RF adapter is a useful counterexample to "
        "a universal MECC speedup claim: it has lower TTFT, lower cold-tier share, and slightly "
        "lower TPOT on this workload. Its recency/frequency rule differs from the published "
        "predictor of the same name.",
    )
    s = s.replace(
        "This comparison supports the joint-retention mechanism under these local policies.",
        "The ordering is consistent in both latency and demand sources. Independent caching "
        "reaches HBM for 51.9\\% of selected experts, fixed CPU reaches HBM for 62.6\\%, "
        "and MECC reaches HBM for 77.5\\%. The CPU shares are 0.3\\%, 5.8\\%, and "
        "10.0\\%, respectively. This comparison supports the joint-retention mechanism "
        "under these local policies.",
    )
    s = s.replace(
        "Figure~\\ref{fig:budget} shows all five local policies at these two settings.",
        "Figure~\\ref{fig:budget} shows all five local policies at these two settings. "
        "The sharp 60~GB drop is a capacity transition: the nominal HBM and host slots together "
        "cover all eight experts per layer, so the cold tier is no longer exercised by demand. "
        "It should not be interpreted as an HDD optimization gain at that budget.",
    )
    s = s.replace(
        r"\subsection{Scope of the Measurements}",
        r"""\subsection{Interpreting the Local Controls}
The three controls answer different questions. Streaming tests repeated delivery without a persistent expert cache. Fixed CPU retention tests the effect of host residency without the same joint promotion and victim demotion rule. Independent caching tests two separately managed resident sets at the same nominal slot count. Only the last control directly tests the coordination mechanism. The relative ordering across these controls should therefore be read as a sequence of local design comparisons, not as three implementations of the same external system. The main bars also include two alternative paths: CPU compute avoids some GPU weight movement but pays for host execution, while the RF adapter changes admission and replacement. Its slightly lower TPOT shows that a tuned replacement rule can matter even after the two fast tiers are coordinated.

The access-source bars provide a second observation for the latency comparison. Relative to fixed CPU retention, MECC serves a larger fraction of selected experts from both HBM and CPU, with fewer requests reaching the cold tier. This direction agrees with the intended reuse mechanism. It does not establish how many physical HDD bytes each policy read during decode. A demand counter increments when a selected expert is absent from the fast tiers; page-cache hits, coalesced reads, and reads issued in another phase can change the relation between that counter and device traffic. For the same reason, the demand shares in Fig.~\ref{fig:retention_result}(b) should not be multiplied by a single per-expert disk time to predict Fig.~\ref{fig:retention_result}(a). A byte and phase audit is needed for that calculation.

\subsection{Capacity and Quality Readout}
The host-slot comparison exposes the threshold between partly cold and fully resident expert sets. At four HBM plus two CPU slots per layer, at least two of the eight experts in a layer are outside the fast tiers at any instant. A routed request for one of these experts must use the cold path unless another mechanism has staged it. At four plus four slots, every expert in the layer can be retained in HBM or host memory. The zero cold-tier demand at the 60~GB setting is therefore consistent with the slot geometry. It does not imply that all experts fit into HBM, nor that the same speed would hold with a smaller host allowance. This threshold also explains why a large physical server memory does not remove the research problem when an individual serving task receives a smaller allocation.

The 30/60~GB runs use four prompts and 16 output tokens, versus eight prompts and 64 tokens in the main comparison. Their absolute TPOT values should not be merged into one curve. Within each budget, all plotted policies share input and quota. The RF adapter remains competitive: at 60~GB, it takes 0.74~s/token versus MECC's 0.76~s/token.

The perplexity check gives a limited quality readout. MECC, streaming, fixed CPU, RF, and MECC I/O report 3.427 on the same 1024-token WikiText-2 sample. Their common FP16 weights and unchanged router are intended to preserve computation. Equal perplexity on one sample is weaker than matching logits and tokens against an independent full-resident implementation. The CPU-compute adapter reports 3.432, so each path needs its own validation.

\subsection{Scope of the Measurements}""",
    )
    return s
