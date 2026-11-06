"""Create the measured A100 reading copy from the existing IEEE manuscript.

The prior ideal-results copy remains available for layout history. This copy
contains only numerical outcomes backed by committed A100 result.json files.
"""
from pathlib import Path
import re
from measured_narrative import revise
from visual_revision import apply as revise_visuals

HERE = Path(__file__).resolve().parent
SRC = HERE / "mecc_dac2027_clean.tex"
OUT = HERE / "mecc_dac2027_measured.tex"


def replace_between(s: str, start: str, end: str, body: str) -> str:
    a, b = s.index(start), s.index(end, s.index(start) + len(start))
    return s[:a] + body.rstrip() + "\n\n" + s[b:]


def main():
    s = SRC.read_text(encoding="utf-8")
    abstract = r"""\begin{abstract}
Single-GPU mixture-of-experts inference can require weight reads from a cold tier when expert residency is limited. MECC combines a placement interface with joint HBM/host retention and weight delivery. We evaluate its current runtime on one A100 with Mixtral-8x7B and a RAID block device reported as rotational. With uniform initial placement and eight WikiText-2 prompts, MECC takes 7.38~s per decode token, versus 13.04~s for unoptimized streaming and 21.75~s for a fixed-CPU cache. A local recency/frequency adapter takes 7.19~s. A matched independent-cache control takes 32.94~s. These single-run measurements support the retention comparison; profile-guided placement and cross-task adaptation remain separate experiments.
\end{abstract}"""
    s = replace_between(s, r"\begin{abstract}", r"\begin{IEEEkeywords}", abstract)
    s = s.replace("We evaluate the contribution of profile placement, retention, and transfer scheduling separately. We also compare one-GPU latency with the smallest feasible resident GPU allocation.",
                  "We measure the current runtime under uniform initialization and compare its cache behavior with single-GPU local controls. The profile compiler and multi-GPU resident alternative are not timed in this evaluation.")
    challenges = r"""\section{Deployment Model and Challenges}
\label{sec:challenges}
\subsection{Single-GPU Execution with Bounded Host Memory}
Consider $L$ MoE layers. Layer $\ell$ contains $N_\ell$ experts and selects $k_\ell$ per token. Expert $e=(\ell,j)$ is an immutable weight object of size $s_e$. Dense weights, activations, KV cache, and temporary buffers also consume HBM. The task is assigned nominal expert slots in HBM and host memory; mirrors and staging consume additional physical memory.

When selected weights are absent from HBM and host memory, a request reads the backing store before host-to-device transfer. Cold reads can enter both prefill and decode. We distinguish demand-tier counts from physical block-device bytes and record the phase of each request.

\subsection{Initial Coverage and Retention}
Uniform per-layer slots may spend capacity on rarely selected experts. A route profile can rank experts within each layer and guide initial placement, but its benefit must be measured against the same online replacement rule. The current main comparison uses uniform quotas and natural expert order; it does not establish a profile-placement gain.

An HBM victim can still be useful to later tokens. Independent HBM and host caches may duplicate experts or fail to preserve a victim in the host working set. Joint promotion and demotion can improve coverage under the same nominal slot counts. The matched independent-cache result in Section~\ref{sec:mechanisms} tests this mechanism on one workload.

\subsection{Workload Change}
The requested experts can change with the input stream. A compiler profile provides an initial prior, while runtime recency reflects later requests. A separate experiment must use distinct task inputs and report both sides of the switch. No task-switch performance claim is made from the current main runs."""
    s = replace_between(s, r"\section{Deployment Model and Challenges}", r"\section{Overview}", challenges)
    s = s.replace("The plan records per-layer capacities, ranked expert IDs, initial tiers, and modeled hit fractions. Input model/profile hashes, object sizes, and the ranking mode identify its provenance. A missing profile selects the natural-order fallback; the plan records the ranking mode. Initialization traffic and planning time are charged before comparing finite service horizons.",
                  "The plan records per-layer capacities, ranked expert IDs, initial tiers, and modeled hit fractions. A missing profile selects natural expert order. The measured runs below use this uniform/natural-order path, so they test the runtime retention and delivery stack rather than the profile compiler. Profile initialization cost and gains require separate matched runs.")
    evaluation = r"""\section{Evaluation}
\label{sec:evaluation}
\subsection{Testbed and Comparison}
The model is Mixtral-8x7B-Instruct-v0.1 with FP16 expert weights on one A100 80~GB PCIe GPU. The backing store resides on a RAID logical block device reported as rotational (\texttt{ROTA=1}); the physical drives behind the controller have not been inventoried. We call the cold tier HDD as a deployment shorthand. No SSD/NVMe comparison is measured.

Each main policy has one completed end-to-end run on the same model revision with nominal expert allowances of 50~GB HBM and 40~GB host memory, four HBM and three host slots per layer, uniform initialization, and cold reads enabled. The input source is WikiText-2 test: eight prompts truncated to 64 input tokens, with 64 generated tokens each. Perplexity uses a 1024-token WikiText-2 sample. Values are single-run point estimates. The nominal host allowance is a planner parameter; mirrors, staging, and page cache are not demonstrated to fit within a physical 40~GB process cap.

The compared policies are unoptimized streaming (\texttt{naive}), fixed-CPU retention (\texttt{swapmoe}), MECC, a local recency/frequency adapter, a CPU-compute adapter, and MECC with an alternative I/O path (\texttt{ours\_io}). The RF and I/O adapters are local implementations, not reproductions of published FlashMoE or SSD-LLaMA. These six runs use one A100 each. There is no measured multi-GPU reference.

\begin{figure*}[tb]
\centering\includegraphics[width=\textwidth]{measured_figures/main.pdf}
\caption{Single-A100 Mixtral-8x7B comparison (eight WikiText-2 prompts, 64 output tokens, one run per policy). (a) Decode time per output token. (b) First-token latency. (c) Reported cold-tier demand share across all instrumented phases, including warmup and perplexity; it is not a decode-only share. All six local policies are shown.}
\label{fig:performance}
\end{figure*}

\subsection{Single-GPU Latency}
Figure~\ref{fig:performance} reports TPOT of 7.38~s for MECC, 13.04~s for streaming, and 21.75~s for fixed-CPU retention. The corresponding TPOT ratios are 1.77$\times$ and 2.95$\times$. The local RF adapter is slightly faster at 7.19~s; MECC I/O takes 7.78~s and the CPU-compute adapter takes 8.26~s. The cold-tier demand shares are 12.5\% for MECC, 20.1\% for streaming, 31.5\% for fixed CPU, and 11.1\% for RF. These counts span several phases, so they describe cache behavior rather than a phase-matched explanation of TPOT alone.

The first-token times are 139.1~s for MECC, 156.9~s for streaming, 174.2~s for fixed CPU, 101.8~s for RF, and 398.4~s for CPU compute. MECC, streaming, fixed CPU, RF, and MECC I/O report perplexity 3.427 on the same 1024-token sample; CPU compute reports 3.432. This quality comparison is specific to that sample. A separate short-window route/logit/token comparison supports the implementation check but is not an independent full-resident reference.

\subsection{Retention Control}
\label{sec:mechanisms}
The independent-cache run matches the main runs' model, nominal slots, input scale, and uniform initialization. Figure~\ref{fig:retention_result} compares independent caching, fixed CPU, and joint MECC retention. Independent caching takes 32.94~s/token and reports 47.9\% cold-tier demand; the fixed-CPU policy takes 21.75~s and reports 31.5\%; MECC takes 7.38~s and reports 12.5\%. This comparison supports the joint-retention mechanism under these local policies. Physical host footprints and exposed I/O time still need matched accounting before the entire latency gap can be assigned to replacement alone.

\begin{figure*}[tb]
\centering\includegraphics[width=\textwidth]{measured_figures/retention.pdf}
\caption{Matched single-A100 cache-policy control at 50/40~GB nominal allowances, eight WikiText-2 prompts, and 64 output tokens. (a) Decode latency. (b) Selected-expert demand resolved from HBM, CPU, or HDD across all instrumented phases. Independent and fixed-CPU policies are local mechanisms. One run per policy.}
\label{fig:retention_result}
\end{figure*}

\subsection{Host-Slot Sensitivity}
The 30 and 60~GB nominal CPU settings use the same four-prompt, 16-token WikiText-2 protocol within each setting. They are a distinct experiment from the eight-prompt main comparison. At 30~GB, MECC takes 14.46~s/token and reports 32.2\% cold-tier demand; at 60~GB, it takes 0.76~s/token and reports no cold-tier demand. The 60~GB plan has four HBM and four host slots per layer, enough for all eight experts. The RF adapter takes 13.06~s/token at 30~GB and 0.74~s/token at 60~GB, faster than MECC in both settings. Figure~\ref{fig:budget} shows all five local policies at these two settings.

\begin{figure*}[tb]
\centering\includegraphics[width=\textwidth]{measured_figures/budget.pdf}
\caption{Nominal CPU-slot sensitivity on one A100. Four WikiText-2 prompts and 16 output tokens per run; 30 and 60~GB are the only two settings shown with the same input source. The earlier 20~GB runs used a different prompt source and are excluded from this comparison. Cold-tier share covers all instrumented phases. One run per point.}
\label{fig:budget}
\end{figure*}

\subsection{Scope of the Measurements}
These results are single-run observations on a RAID logical device reporting rotational media. The main comparison uses uniform initialization and does not measure the compiler's profile-guided gain. A true WikiText-2 to GSM8K task-switch sequence has now been implemented, but no completed task-switch result appears in the committed result set. The 20~GB budget runs mix prompt sources and cannot be joined to the 30/60~GB curve. Physical drive identity, physical host-cap equivalence, and multi-GPU resident performance remain separate measurements."""
    s = replace_between(s, r"\section{Evaluation}", r"\section{Related Work}", evaluation)
    # The ideal-results source places its old performance float just before
    # Evaluation. Remove it so only the measured float owns this label.
    s, removed = re.subn(
        r"\\begin\{figure\*\}\[tb\]\s*\\centering\\includegraphics\[width=\\textwidth\]"
        r"\{clean_review/figures/fig04_performance\.pdf\}.*?\\end\{figure\*\}\s*",
        "", s, count=1, flags=re.S)
    assert removed == 1
    s = replace_between(s, r"\section{Conclusion}", r"\clearpage", r"""\section{Conclusion}
On one A100 with uniform initial placement, MECC's joint-retention runtime reduces decode latency relative to local streaming, fixed-CPU, and independent-cache controls. The local RF adapter is slightly faster on the main workload. Profile-guided placement, task changes, physical budget equivalence, and multi-GPU tradeoffs require separate evidence before they enter the performance claim.""")
    # The clean review copy contains no in-body disclosure; keep the reading copy
    # marked by its filename and data-audit artifact, without inventing measurements.
    assert "3.00--3.26" not in s and "Mixtral-8x22B" not in s
    assert "ideal_figures/" not in s and "Hypothetical" not in s
    s = revise(s)
    s = revise_visuals(s)
    OUT.write_text(s, encoding="utf-8")
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
