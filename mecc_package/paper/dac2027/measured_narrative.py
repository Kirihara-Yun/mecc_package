"""Section order and prose for the evidence-backed DAC reading copy."""

from __future__ import annotations


FRONT = r"""\section{Introduction}
Mixture-of-experts (MoE) models activate only a few experts for each token, yet deployment must keep every expert addressable~\cite{shazeer,switch,mixtral,deepseekmoe}. On a single accelerator, the selected expert can be absent from HBM. A server may also assign a task less host memory than the machine physically contains. If the expert set exceeds both allocations, some requests must reach a backing store.

\begin{figure*}[!b]
\centering\includegraphics[width=\textwidth]{measured_figures/intro.pdf}
\caption{Single-GPU motivation. (a) An expert selected by the unchanged router may require HDD-to-host-to-GPU delivery. Boxes are schematic. (b) Measured Mixtral-8x7B decode latency for three local policies on one A100, with the common eight-prompt input and one run per policy. The plot does not measure the compiler's profile gain.}
\label{fig:intro}
\end{figure*}

Figure~\ref{fig:intro} connects the weight path to a local runtime comparison. Streaming takes 13.04~s per output token and fixed-CPU retention takes 21.75~s. Joint retention takes 7.38~s under the same nominal slots. These figures motivate cache coordination; they do not isolate placement or transfer overlap. The readout is slow in absolute terms because HDD-backed demand remains in the critical path.

The operational unit is a selected expert at a particular layer, not a whole model moved for each token. A token passes through successive MoE layers; each layer's gate selects a small set of its own expert IDs. The selected weights must be ready before the expert kernels run. If they are already in HBM, no weight transfer is needed. A host hit needs a host-to-device copy; a cold-tier miss also needs a storage read. The same expert may be selected again by later tokens, making retention useful even when the next layer selects different experts. Figure~\ref{fig:intro}(a) depicts this demand path. It also shows why the host tier matters when it cannot hold the entire expert set assigned to the task.

Multi-GPU expert parallelism can partition experts across resident HBM and move token activations between GPUs~\cite{deepspeedmoe,tutel,flashmoedist}. That is a different capacity point. Single-GPU systems instead choose which weights remain in HBM or host memory and what happens on a miss. Prior work addresses CPU execution, prefetching, cache replacement, and disk delivery~\cite{fiddler,moeinfinity,lightning,ssdllama,flashmoe,offloading}. The design question here is how an independent route profile and the observed route should share those decisions under a task-specific capacity.

This paper makes three contributions. First, it states a compiler interface for ranked per-layer placement under explicit HBM and host allowances. Second, it specifies joint promotion and demotion across the two fast tiers while retaining the original router and FP16 experts. Third, it measures the current single-A100 runtime against matched local controls and separates observed retention gains from placement and adaptation questions that require separate runs.

The system divides decisions by time scale. A route profile gives the compiler a prior over expert demand and determines an initial placement plan. At inference time, the unchanged gate identifies actual demand, and recency updates the identities retained in each tier. The plan fixes capacities within the run; it does not force the runtime to keep an expert that is no longer requested. This separation allows a profile to shorten the initial cold phase while a shared fast-tier cache preserves reuse as inputs change. The evaluation below directly tests the runtime component with uniform initialization. That makes the strongest supported conclusion narrower than the complete design: the measured advantage is from the local joint-retention implementation under the tested slots.

The paper proceeds from the execution and deployment choices in Section~\ref{sec:background} to three capacity and reuse challenges, then presents the system architecture, method, and single-GPU measurements. This order separates the general design from the current implementation evidence.

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
