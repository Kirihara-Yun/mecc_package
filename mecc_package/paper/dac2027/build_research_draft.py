"""Research-completion copy: measured results plus explicitly yellow targets.

This copy never changes measured run data or registers a target as verified.
"""
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent

BACKGROUND=r'''\section{Background}
\label{sec:background}
An MoE layer routes each token to a small subset of its experts. Sparse execution reduces arithmetic, but every expert remains a possible future selection~\cite{shazeer,switch,gshard}. Mixtral and the DeepSeek family instantiate this separation between active computation and total weights~\cite{mixtral,deepseekmoe,deepseekv2,deepseekv3,mixtral22}. Experts with the same index in different layers are different weight objects. A route profile must therefore retain both layer and expert identity.

Expert parallelism partitions weights over resident GPU memories and dispatches token activations to their owners~\cite{deepspeedmoe,tutel,megablocks,flashmoedist,harmoeny}. On one GPU, the task also needs space for dense layers, activations, and the KV cache. KV management and request execution are complementary to expert residency~\cite{pagedattention,sglang}. A host-resident expert needs an H2D copy; an expert absent from both fast tiers additionally needs a backing-store read. Heterogeneous inference systems expose related placement and scheduling choices~\cite{flexgen,dsinference,zeroinfinity,llmflash,powerinfer}.

We use immutable FP16 experts and three logical tiers: HBM, CPU pinned memory, and HDD. The task's allowance may be smaller than the server's physical RAM. Unique resident weights, host mirrors, staging buffers, and other allocations must be distinguished. The original gate determines demand, and a delivered expert can remain resident for later tokens. MECC separates the initial residency decision from the online transitions that respond to those later selections.

\section{Motivation and Insights}
\label{sec:challenges}
\subsection{Spend Capacity Where It Covers Demand}
Equal slots per layer assume comparable cache pressure. A profile can reveal different ranked demand distributions even when each layer has the same expert count. Figure~\ref{fig:insights}(a,d) connects this question to a ranked capacity cut: the compiler allocates the next slot by its marginal covered demand. \pending{E05: replace panel (a)'s ideal numbers with a same-runtime, same-byte placement sweep.} The experiment must include empirical-profile and uniform controls; the current measured main runs use uniform initialization. Local routing consistency can also vary across models~\cite{routingconsistency}.

\subsection{An HBM Victim Can Still Be Useful}
Figure~\ref{fig:insights}(b,e) shows why two resident sets should preserve cross-tier reuse. With the same nominal slots and initialization, the measured independent-cache control reports 47.9\% HDD demand, fixed CPU 31.5\%, and MECC 12.5\%. These counters span all instrumented phases. The insight is to promote a host hit while retaining the displaced HBM expert in CPU, rather than treating the eviction as the end of its useful lifetime. The source-tier and physical-byte measurements answer different questions and must be reported separately.

\subsection{Use the Profile as an Initial State}
A profile represents past inputs. If the routed set changes, fixed residency can preserve experts that are no longer useful. Figure~\ref{fig:insights}(c,f) pairs an expected miss transient with the corresponding residency update. Compilation fixes capacities and ranked IDs; online recency changes identities within those capacities. \pending{E07/E08: measure initial misses and the WikiText-2/GSM8K switch transient using distinct, hashed input sets.} The experiment must retain the no-switch control and compare profile-plus-online with both fixed residency and online-only initialization.

'''

EVALUATION=r'''\section{Evaluation}
\label{sec:evaluation}
\subsection{Testbed and Evidence Map}
Measured runs use FP16 Mixtral-8x7B-Instruct-v0.1 on one A100 80~GB PCIe. The cold store is on a RAID logical device reporting rotational media; physical drives remain uninventoried. Main runs use four HBM and three host slots per layer, uniform initialization, eight WikiText-2 prompts, 64 input and 64 output tokens, and one run per policy. Perplexity uses 1024 WikiText-2 tokens. The 50/40~GB allowances are planner parameters; mirrors and buffers still need a physical-byte audit.

Yellow plots and text are experiment-completion targets, not measurements. Their arrays come from the existing design-target record. \pending{Freeze model revisions, input hashes, precision, total charged bytes, and timing windows before replacing each target.} The experiments address full-system benefit, individual mechanisms, workload change, resource tradeoffs, and numerical equivalence.

\subsection{Measured Runtime and Quality}
\begin{figure}[H]
\centering\includegraphics[width=\columnwidth]{measured_figures/main.pdf}
\caption{Measured single-A100 runtime: one run per local policy, eight WikiText-2 prompts, 64 output tokens. RF and CPU-compute adapters are local mechanisms.}
\label{fig:performance}
\end{figure}
Figure~\ref{fig:performance} reports MECC at 7.38~s/token, streaming at 13.04, and fixed CPU at 21.75: TPOT ratios of 1.77$\times$ and 2.95$\times$. The RF adapter takes 7.19~s, MECC I/O 7.78, and CPU compute 8.26. RF is faster than MECC in this run. MECC's TTFT is 139.1~s, versus 156.9 for streaming and 174.2 for fixed CPU. MECC, streaming, fixed CPU, RF, and MECC I/O report PPL 3.427; CPU compute reports 3.432. A short-window route/logit/token diagnostic supports local correctness but does not replace an independent resident reference.

\subsection{Mechanism Attribution}
\label{sec:mechanisms}
\begin{figure*}[!t]
\centering\includegraphics[width=\textwidth]{completion_figures/mechanism_sweeps.pdf}
\caption{\pending{TO MEASURE: ideal component targets on three models.} (a) Placement with runtime fixed. (b) Retention with initialization fixed. (c) Adaptation after a task switch. Separate protocols must be frozen for the three controls; these bars are not A100 outcomes.}
\label{fig:target_mechanisms}
\end{figure*}
The matched local independent-cache control takes 32.94~s/token. Figure~\ref{fig:target_mechanisms} separates three mechanisms in the target component harness. For Mixtral-8x7B, the placement target moves from \pending{18.6 to 14.2 s/token}, joint retention from \pending{18.3 to 14.2}, and post-switch adaptation from \pending{25.1 to 16.0} relative to fixed residency. The three controls hold runtime, initial plan, and switch protocol fixed, respectively. This separates better initial coverage from preservation of later reuse. \pending{E04--E08: replace targets and add leave-one-out controls.}

\begin{figure}[H]
\centering\includegraphics[width=\columnwidth]{completion_figures/ablation_startup.pdf}
\caption{\pending{TO MEASURE: ideal ablation and startup targets.} The right panel evaluates startup/output-token plus decode cost from authored inputs; it is not a measured latency trace.}
\label{fig:target_ablation}
\end{figure}
Figure~\ref{fig:target_ablation} tests component addition and startup amortization. The authored TPOT sequence is \pending{24, 18, 11, and 8 s/token}. The last I/O step retains a \pending{20-percent target HDD-demand share}, separating delivery scheduling from miss reduction. With the plotted startup/decode costs, the target amortization curves cross at \pending{9 output tokens}. This check exposes the service horizon over which an initial investment pays back. \pending{E04/E13: replace targets with phase timings and addition/removal runs.}

\subsection{Model and Deployment Coverage}
\begin{figure}[H]
\centering\includegraphics[width=\columnwidth]{completion_figures/cross_model.pdf}
\caption{\pending{TO MEASURE: ideal model/workload targets.} Mixtral-8x7B and 8x22B with QA/code inputs. Values specify planned comparisons, not measured benchmarks. The RF policy is a local adapter.}
\label{fig:target_models}
\end{figure}
Figure~\ref{fig:target_models} expands the present one-model workload. The MECC target ranges from \pending{8 to 19 s/token}, versus \pending{24 to 62} for streaming and \pending{11 to 29} for the RF adapter. QA and code exercise different expert-demand patterns; increasing model size also changes the expert pool and transfer size. The comparison therefore pairs every policy within each model/workload point. \pending{E01/E02: replace targets under frozen inputs, precision, and byte allowances.}

\begin{figure}[H]
\centering\includegraphics[width=\columnwidth]{completion_figures/gpu_tradeoff.pdf}
\caption{\pending{TO MEASURE: ideal one-GPU/resident-reference tradeoff.} MECC has only a one-GPU point. Resident points use 2/4/8 GPUs; occupancy is GPU count times TPOT. These values are not published FlashMoE results.}
\label{fig:target_gpu}
\end{figure}
Figure~\ref{fig:target_gpu} separates GPU provisioning from response latency. The endpoint target is \pending{one GPU at 8 s/token versus eight GPUs at 1 s/token}; both correspond to \pending{8 GPU-s/token}. The \pending{two-GPU resident target is 5.6 GPU-s/token}, which makes the smallest feasible resident configuration a necessary comparison. Occupancy is reported alongside latency, rather than substituted for energy. \pending{E03/E14: replace all resident-reference targets.}

\balance
\subsection{Capacity and Implementation Checks}
\begin{figure}[H]
\centering\includegraphics[width=\columnwidth]{measured_figures/budget.pdf}
\caption{Measured 30/60~GB nominal host-allowance comparison. Four WikiText-2 prompts and 16 output tokens, one run per point. Demand share covers all instrumented phases.}
\label{fig:budget}
\end{figure}
Figure~\ref{fig:budget} reports MECC at 14.46 and 0.76~s/token, with 32.2\% and zero HDD demand. Four HBM plus four host slots at 60~GB cover all eight experts per layer; zero cold demand is a capacity transition. RF takes 13.06 and 0.74~s/token. These points use a shorter protocol than the main run.

\begin{figure}[H]
\centering\includegraphics[width=\columnwidth]{completion_figures/quota_targets.pdf}
\caption{\pending{TO MEASURE: ideal dense-quota sweep.} The target experiment uses a separately frozen protocol; it is not joined to the measured 30/60~GB curve.}
\label{fig:target_quota}
\end{figure}
Figure~\ref{fig:target_quota} resolves intermediate capacity points. Its authored MECC target changes from \pending{16 to 7 s/token} over \pending{16--48 GB}, compared with \pending{27 to 12} for three-tier LRU. The purpose is to separate pressure within the cold-tier regime from the full-coverage threshold. \pending{E10: replace with one matched, physically charged quota sweep.}

\pending{E14/E15: fill peak physical HBM/host bytes, mirrors, pinned staging, phase-specific traffic, and independent-reference route/logit/token checks.} The current sample PPL equality supports only that sample. \pending{E09/E11/E12: add profile-size sensitivity, no-switch/shift controls, and batch/input/output-length sensitivity if the corresponding claims remain in the paper.}

\begin{table}[H]
\centering\small\renewcommand{\arraystretch}{0.9}
\caption{Numerical and resource checks. Sample PPL values are measured; highlighted entries require independent validation or measurement.}
\label{tab:checks}
\begin{tabular}{@{}p{0.46\linewidth}p{0.49\linewidth}@{}}
\toprule
Check & Current value / target\\
\midrule
MECC / fixed-CPU sample PPL & 3.427 / 3.427\\
CPU-compute sample PPL & 3.432\\
Resident-reference route match & \pending{Target: exact}\\
Resident-reference logit error & \pending{Target: zero}\\
Physical HBM / host peak bytes & \pending{TO MEASURE}\\
Phase-specific HDD/H2D bytes & \pending{TO MEASURE}\\
\bottomrule
\end{tabular}
\end{table}
Table~\ref{tab:checks} closes the evaluation contract: performance comparisons preserve the routed computation and precision, and charge the actual resident and temporary allocations. A nominal slot budget alone cannot establish physical-memory equivalence.

'''

RELATED=r'''\section{Related Work}
Expert offloading starts from the distinction between sparse execution and full weight capacity~\cite{offloading,swapmoe}. Fiddler and DAOP choose CPU/GPU execution or movement; MoE-Lightning pipelines heterogeneous work; MoE-Infinity uses activation traces~\cite{fiddler,daop,lightning,moeinfinity}. ProMoE, Pre-gated MoE, Fate, and ExpertFlow provide lookahead, proactive caching, or token scheduling~\cite{promoe,pregated,fate,expertflow}. MECC's demand path instead consumes the original gate output and coordinates initial placement with online residency.

HOBBIT and Specter use precision in expert loading; MoEpic divides experts into segments; SliceMoE caches precision slices; Mira combines staging with quantization~\cite{hobbit,specter,moepic,slicemoe,mira}. ZipMoE uses compression and affinity scheduling~\cite{zipmoe}. SSD-LLaMA, edge FlashMoE, and MoE-CORE address storage delivery, replacement, or coordinated residency~\cite{ssdllama,flashmoe,core}. MECC studies the interaction between an independent placement prior and online whole-expert retention across the two fast tiers under HDD-backed demand.

Granularity changes the meaning of a cache hit. A segment cache can avoid part of an expert transfer while still fetching the remaining weights. A precision-slice cache can change both resident bytes and numerical execution. A whole-expert cache instead changes the source of unchanged weights. These comparisons therefore report representation and quality alongside latency. Physical traffic per miss and the number of misses are separate quantities: compression or splitting can reduce the former, while retention changes the latter.

\begin{table}[H]
\centering\small\renewcommand{\arraystretch}{0.9}
\caption{Representative control granularity and primary decision.}
\label{tab:related_units}
\begin{tabular}{@{}p{0.20\linewidth}p{0.22\linewidth}p{0.47\linewidth}@{}}
\toprule
System & Unit & Primary decision\\
\midrule
Fiddler~\cite{fiddler} & Expert & CPU/GPU execution\\
ProMoE~\cite{promoe} & Expert & Proactive caching\\
MoEpic~\cite{moepic} & Segment & Split ratio and allocation\\
HOBBIT~\cite{hobbit} & Expert precision & Precision-aware loading\\
Bevy~\cite{bevy} & Request & Runahead and batching\\
MECC & FP16 expert & Initial placement and joint retention\\
\bottomrule
\end{tabular}
\end{table}

Klotski and Bevy expose independent work across batches or requests~\cite{klotski,bevy}. OD-MoE distributes on-demand loading over edge nodes, while HeteGen studies heterogeneous dense-model inference~\cite{odmoe,hetegen}. Their execution units differ from batch-one per-gate expert delivery. The full-system, mechanism, and resource experiments above distinguish these comparisons.

Cross-request scheduling also changes the available overlap. A ready request can advance while another waits, providing work beyond the current gate's selected experts. In a single-request stream, MECC's delivery dependencies only expose already-ready expert computation. This distinction explains why cache replacement, route lookahead, and request scheduling require separate controls even when all three improve an end-to-end latency metric.

\section{Conclusion}
MECC connects a profile-derived initial state with online cross-tier retention and weight delivery. Current single-A100 measurements support the local runtime comparison. The yellow experiment panels define the remaining evidence for placement, adaptation, model coverage, startup, and resident multi-GPU tradeoffs. They must be replaced before those outcomes enter a final performance claim.

'''

def main():
    base=(HERE/'mecc_dac2027_measured.tex').read_text(encoding='utf-8')
    intro_start=base.index(r'\section{Introduction}')
    intro_end=base.index(r'\clearpage',intro_start)
    prefix=base[:intro_start]
    # hyperref must see float/caption packages after they have been loaded.
    hyper_setup=re.search(r'\\hypersetup[^\n]*',prefix).group(0)
    prefix=prefix.replace(r'\usepackage[hidelinks]{hyperref}'+'\n','')
    prefix=prefix.replace(hyper_setup+'\n','')
    prefix=prefix.replace(r'\begin{document}',r'\usepackage[hidelinks]{hyperref}'+'\n'+hyper_setup+'\n'+r'\begin{document}')
    prefix=prefix.replace(r'\usepackage{xcolor}',r'''\usepackage{xcolor}
\usepackage{soul}
\DeclareRobustCommand{\pending}[1]{{\sethlcolor{yellow}\hl{#1}}}
\setlength{\abovecaptionskip}{3pt}
\setlength{\belowcaptionskip}{2pt}
\setlength{\intextsep}{6pt plus 1pt minus 1pt}
\setlength{\textfloatsep}{7pt plus 1pt minus 1pt}
\setlength{\floatsep}{6pt plus 1pt minus 1pt}''')
    intro=base[intro_start:intro_end]
    p=intro.index('This paper makes three contributions.')
    contribution=intro[p:]
    parts=re.split(r'\\textbf\{\((\d)\) ([^}]+)\}',contribution)
    assert len(parts)==10
    listing='This paper makes three contributions.\n'+r'''\begin{list}{}{\setlength{\leftmargin}{16pt}\setlength{\labelwidth}{14pt}\setlength{\labelsep}{2pt}\setlength{\itemsep}{3pt}\setlength{\topsep}{3pt}}
'''
    for j in (1,4,7):
        listing+=r'\item[('+parts[j]+r')] \textbf{'+parts[j+1]+'} '+parts[j+2].strip()+'\n'
    listing+=r'\end{list}'+'\n'
    intro=intro[:p]+listing
    mot_header=r'''\twocolumn[{
\begin{minipage}{\textwidth}
\centering
\includegraphics[width=\textwidth]{completion_figures/motivation_evidence.pdf}\par
\vspace{2pt}
\includegraphics[width=\textwidth]{measured_figures/insights_lower.pdf}
\captionof{figure}{Motivation evidence and matching insights. \pending{Panels (a,c) are ideal targets to replace}; (b) is measured A100 demand across all phases. (d--f) are schematic mechanisms, adapted from the talk. Profiles guide initial coverage, joint retention preserves victims, and online updates follow changed routing.}
\label{fig:insights}
\vspace{5pt}
\end{minipage}
}]
'''
    a=base.index(r'\twocolumn[{');b=base.index(r'\section{Method}',a)
    overview=base[a:b]
    method=base[b:base.index(r'\section{Evaluation}',b)]
    # Preserve the stated model and exchange argument, remove its standalone
    # theorem styling: it is supporting context, not a claimed novel theorem.
    method=re.sub(r'\\begin\{proposition\}(.*?)\\end\{proposition\}\s*\\noindent\\emph\{Proof sketch\.\}(.*?)(?=\n\n)',
        lambda m:'For equal-size experts with fixed probabilities, exchanging a more probable expert in a slower tier with a less probable expert in a faster tier cannot increase static expected cost. This establishes ranked placement under independent capacities and ordered tier costs. The implementation below uses marginal coverage, rather than claiming to solve the general latency objective.',method,flags=re.S)
    a=method.index(r'\subsection{Implementation and Measurement Contract}')
    method=method[:a]+r'''\subsection{Implementation and Accounting}
Policies share the FP16 loader and unchanged router. Logical tier occupancy is not physical memory. Host mirrors, staging, and temporary copies are charged separately from unique residents. Full CPU mirroring requires host bytes at least as large as the mirrored HBM experts. \pending{E14: replace nominal slot equivalence with measured physical-byte accounting.}

The harness records initialization, warmup, prefill, decode, and PPL separately. TPOT and TTFT use their own timing windows. Demand-source counts and physical HDD/H2D/D2H bytes must share phase boundaries. \pending{E15: complete independent-resident reference checks before a general lossless claim.}

'''
    ending=r'''\clearpage
\nobalance
\IEEEtriggeratref{24}
\bibliographystyle{IEEEtran}
\bibliography{references}
\end{document}
'''
    paper=prefix+intro+mot_header+BACKGROUND+overview+method+EVALUATION+RELATED+ending
    # Number the top-of-page mechanism float before the measured column plot.
    a=paper.index(r'\begin{figure*}[!t]',paper.index(r'\section{Evaluation}'))
    b=paper.index(r'\end{figure*}',a)+len(r'\end{figure*}')
    component=paper[a:b];paper=paper[:a]+paper[b:]
    paper=paper.replace(r'\subsection{Measured Runtime and Quality}',component+'\n\n'+r'\subsection{Measured Runtime and Quality}',1)
    # End the graphics paragraph explicitly and suppress interline glue before
    # its caption. This closes the large visual gap without negative margins.
    paper=re.sub(r'(\\includegraphics[^\n]*)(\n)(\\caption(?:of\{figure\})?\{)',
                 lambda m:m.group(1)+'\n'+r'\par\nointerlineskip'+'\n'+m.group(3),paper)
    paper='\n'.join(line.rstrip() for line in paper.splitlines())+'\n'
    (HERE/'MECC_DAC_research_draft.tex').write_text(paper,encoding='utf-8')
    print('Research draft written; targets explicitly yellow-highlighted; measured copy preserved.')

if __name__=='__main__':main()
