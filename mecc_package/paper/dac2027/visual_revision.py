"""Apply compact visual placement and the expanded related-work comparison."""
import re

def figure(s,label,body):
    pattern=r'\\begin\{figure\*?\}[^\n]*\n(?:(?!\\begin\{figure).)*?\\label\{'+re.escape(label)+r'\}.*?\\end\{figure\*?\}'
    s,n=re.subn(pattern,lambda _:body,s,count=1,flags=re.S)
    assert n==1,label
    return s

def apply(s):
    s=s.replace(r'\maketitle',r'\maketitle\raggedbottom')
    s=s.replace(r'\usepackage{balance}',r'''\usepackage{balance}
\usepackage{capt-of}
\usepackage{float}
\usepackage{needspace}
\setcounter{dbltopnumber}{3}
\renewcommand{\dbltopfraction}{0.85}
\renewcommand{\textfraction}{0.10}''')
    s=s.replace(r'\section{Background}',r'\section{Background and Related Work}')
    s=s.replace(r'\subsection{Related Expert-Serving Systems}',
                r'\subsection{Related Expert-Serving Systems}')
    anchor=r'\section{Motivation and Insights}'
    extra=r'''The comparison spans three decisions. \emph{Execution location} determines whether to move weights to the GPU or execute an expert on the CPU. Fiddler and DAOP explore this choice~\cite{fiddler,daop}, whereas the measured MECC path executes selected experts on the GPU. \emph{Lookahead} determines when an expert becomes known. ProMoE, Pre-gated MoE, Fate, and Mira expose or predict later demand~\cite{promoe,pregated,fate,mira}; MECC's demand path begins with the original gate output. \emph{Residency} determines which delivered weights survive for reuse. MoE-Infinity, FlashMoE, MoE-CORE, and ZipMoE address this decision with different trace, replacement, initialization, or scheduling mechanisms~\cite{moeinfinity,flashmoe,core,zipmoe}. These axes can coexist in one system, so the experimental controls must identify the particular rule being changed.

The storage regime also affects the comparison. A host-resident expert set mainly exposes PCIe movement or CPU execution. A set larger than the task's fast-tier allowance additionally exposes backing-store reads. SSD-LLaMA and edge FlashMoE explicitly address storage delivery~\cite{ssdllama,flashmoe}. MECC studies HDD-backed demand while combining a placement prior with online HBM/CPU retention.

'''
    s=s.replace(anchor,extra+anchor)
    s=s.replace(r'\label{sec:challenges}',r'''\label{sec:challenges}
\begin{figure*}[!b]
\centering\includegraphics[width=\textwidth]{measured_figures/insights_en.pdf}
\caption{Three design insights, adapted from the MECC talk diagrams. (a) Rank experts within a layer and divide fast-tier capacity at the ranked boundaries. (b) Treat HBM and CPU as one reuse stack: requesting $e_3$ promotes it while retaining the HBM victim $e_2$ in CPU. (c) Update resident identities when the routed expert set changes. All probabilities, states, and time windows are schematic.}
\label{fig:insights}
\end{figure*}''')
    s=s.replace('The expert set is larger than the fast-tier slots assigned to a task.',
                'Figure~\\ref{fig:insights}(a) illustrates initial coverage. The expert set is larger than the fast-tier slots assigned to a task.')
    s=s.replace('An HBM victim need not become cold immediately.',
                'Figure~\\ref{fig:insights}(b) illustrates reuse across the tier boundary. An HBM victim need not become cold immediately.')
    s=s.replace('A profile describes a prior workload, not every later request.',
                'Figure~\\ref{fig:insights}(c) shows the timing of adaptation. A profile describes a prior workload, not every later request.')
    s=s.replace(' A task switch requires two distinct input sets and a measured before/after trace. The present single-A100 main run does not test a switch.',
                '')
    s=figure(s,'fig:overview',r'''\begin{figure*}[!t]
\centering\includegraphics[width=\textwidth]{figures/fig01_overview.pdf}
\caption{MECC framework, shared with the project presentation. The placement compiler emits per-layer capacities and ranked IDs. Online execution resolves unchanged router selections against HBM, CPU pinned memory, and HDD, then delivers weights before their GPU consumers. Dashed arrows carry control or plan metadata; solid arrows move weights.}
\label{fig:overview}
\end{figure*}''')
    s=s.replace(r'\subsection{Compiler: Profile-Guided Placement}',r'''\subsection{Compiler: Profile-Guided Placement}
\begin{figure}[!t]
\centering\includegraphics[width=\columnwidth]{measured_figures/method_compile.pdf}
\caption{Compiling layer-specific placement. A, B, and C denote different layers. The compiler keeps each layer's expert identities, ranks its profile counts, and allocates HBM and CPU slots from shared task allowances. Colors identify initial tiers; counts and capacities are schematic.}
\label{fig:compile}
\end{figure}
Figure~\ref{fig:compile} shows the compiler's input and emitted state.''')
    s=figure(s,'fig:retention',r'''\begin{figure}[!t]
\centering\includegraphics[width=\columnwidth]{measured_figures/method_runtime.pdf}
\caption{One CPU-hit transition. Lists run from MRU to LRU. Requesting $e_3$ promotes it, demotes the HBM victim $e_2$, and preserves both experts in the combined fast-tier set. The dashed line is the capacity boundary.}
\label{fig:retention}
\end{figure}''')
    s=s.replace('Figure~\\ref{fig:retention} starts with HBM $[e_0,e_1]$ and CPU $[e_2,e_3,e_4]$. Requesting $e_2$ promotes it and demotes $e_0$. The next request for $e_0$ hits CPU.',
                'Figure~\\ref{fig:retention} starts with HBM $[e_1,e_2]$ and CPU $[e_3,e_4]$, each ordered from MRU to LRU. Requesting $e_3$ promotes it and demotes $e_2$. A later request for $e_2$ hits CPU.')
    s=figure(s,'fig:delivery',r'''\begin{figure}[!t]
\centering\includegraphics[width=\columnwidth]{measured_figures/method_delivery.pdf}
\caption{Delivery dependencies within one gate's selected set. The GPU can execute resident $e_1$ while $e_3$ is read and copied. A readiness event orders the copied weight before its GPU consumer. Durations are schematic.}
\label{fig:delivery}
\end{figure}''')
    s=s.replace('Figure~\\ref{fig:delivery} pairs one HBM-resident expert with one HDD-backed expert from the same gate.',
                'Figure~\\ref{fig:delivery} pairs HBM-resident $e_1$ with HDD-backed $e_3$ from the same gate.')
    s=s.replace('The resident $e_0$ can execute while $e_2$ is read and copied.',
                'The resident $e_1$ can execute while $e_3$ is read and copied.')
    s=s.replace(r'\IEEEtriggeratref{22}',r'\IEEEtriggeratref{24}')
    s=s.replace('Three design insights, adapted from the MECC talk diagrams.',
                'Profile-guided placement and online correction.')
    s=s.replace('MECC framework, shared with the project presentation.','MECC framework.')
    # Declare the wide Motivation graphic before the first column is emitted.
    pattern=r'\\begin\{figure\*\}[^\n]*\n(?:(?!\\begin\{figure).)*?\\label\{fig:insights\}.*?\\end\{figure\*\}'
    m=re.search(pattern,s,re.S);assert m,'motivation figure'
    insight=m.group(0);s=s[:m.start()]+s[m.end():]
    s=s.replace(r'\label{sec:background}',r'\label{sec:background}'+'\n'+insight,1)
    # Keep only the framework in the Overview page header.
    pattern=r'\\begin\{figure\*\}[^\n]*\n(?:(?!\\begin\{figure).)*?\\label\{fig:overview\}.*?\\end\{figure\*\}'
    m=re.search(pattern,s,re.S);assert m,'overview figure'
    block=re.sub(r'\\begin\{figure\*\}[^\n]*\n','',m.group(0))
    block=block.replace(r'\end{figure*}','').replace(r'\caption{',r'\captionof{figure}{')
    s=s[:m.start()]+s[m.end():]
    header=r'''\twocolumn[{
\begin{minipage}{\textwidth}
\section{Overview}
\label{sec:overview}
'''+block+r'''
\vspace{8pt}
\end{minipage}
}]
'''
    s=s.replace(r'\section{Overview}',header,1)
    s=s.replace('}]\n\n\\label{sec:overview}','}]\n',1)
    for label in ['fig:compile','fig:retention','fig:delivery']:
        pattern=r'\\begin\{figure\}\[!t\]\n(?:(?!\\begin\{figure).)*?\\label\{'+re.escape(label)+r'\}.*?\\end\{figure\}'
        m=re.search(pattern,s,re.S);assert m,label
        block=m.group(0).replace(r'\begin{figure}[!t]',r'\begin{figure}[H]')
        s=s[:m.start()]+block+s[m.end():]
    # Use native column-sized plots at their explanatory subsections. Avoid
    # a wide result-float queue that postpones the controls to a later page.
    for label,heading,reserve in [
        ('fig:performance',r'\subsection{Single-GPU Latency}','2.7in'),
        ('fig:retention_result',r'\subsection{Retention Control}','2.6in'),
        ('fig:budget',r'\subsection{Host-Slot Sensitivity}','1.7in')]:
        pattern=r'\\begin\{figure\*?\}[^\n]*\n(?:(?!\\begin\{figure).)*?\\label\{'+re.escape(label)+r'\}.*?\\end\{figure\*?\}'
        m=re.search(pattern,s,re.S);assert m,label
        block=m.group(0)
        block=re.sub(r'\\begin\{figure\*?\}[^\n]*',lambda _:r'\begin{figure}[H]',block)
        block=block.replace(r'\end{figure*}',r'\end{figure}').replace(r'width=\textwidth',r'width=\columnwidth')
        if label=='fig:performance':
            block=block.replace('(c) Reported cold-tier demand share across all instrumented phases, including warmup and perplexity; it is not a decode-only share. ','')
        s=s[:m.start()]+s[m.end():]
        anchor=heading
        if label=='fig:retention_result':anchor+='\n'+r'\label{sec:mechanisms}'
        assert anchor in s
        preface=''
        if label=='fig:budget':
            preface=r'''
The 30 and 60~GB host allowances use the same four-prompt, 16-output-token input, with four HBM slots per layer. The matched plans differ in CPU slots. Cold slots denote experts outside both fast tiers; the following counts are per layer.
\begin{center}\small
\begin{tabular}{rrrr}
\toprule
CPU (GB) & HBM slots & CPU slots & Cold slots\\
\midrule
30 & 4 & 2 & 2\\
60 & 4 & 4 & 0\\
\bottomrule
\end{tabular}
\end{center}
These plans straddle the complete-coverage threshold. Four HBM and two CPU slots retain at most six distinct experts per layer, leaving two outside the fast tiers. Four slots in each fast tier can retain all eight experts. This is a transition in logical coverage; it does not imply that all weights fit in HBM. Both runs use a shorter output window than the main comparison, so their absolute latencies are compared only within the matched budget protocol.

'''
        s=s.replace(anchor,r'\Needspace{'+reserve+'}\n'+anchor+'\n'+preface+block,1)
    s=s.replace('The 30 and 60~GB nominal CPU settings use the same four-prompt, 16-token WikiText-2 protocol within each setting. They are a distinct experiment from the eight-prompt main comparison. ',
                'These settings use a shorter protocol than the eight-prompt main comparison. ')
    s=s.replace("The RF adapter is a useful counterexample to a universal MECC speedup claim: it has lower TTFT, lower cold-tier share, and slightly lower TPOT on this workload. Its recency/frequency rule differs from the published predictor of the same name.",
                "The RF adapter has the lowest TTFT and TPOT in this local comparison.")
    s=s.replace('Model adapters map layer/expert IDs to weight objects, and policies share an end-to-end loader. The harness maps each layer/expert ID to an immutable FP16 weight object. Policies share the same loader and router interface.',
                'Model adapters map layer/expert IDs to immutable FP16 weights. Policies share the loader and router interface.')
    s=s.replace('These counts span several phases, so they describe cache behavior rather than a phase-matched explanation of TPOT alone.',
                'These multi-phase counts describe cache behavior, rather than decode-only I/O.')
    # These explanations duplicate the main result and quality paragraphs.
    a=s.index(r'\subsection{Interpreting the Local Controls}')
    b=s.index(r'\subsection{Scope of the Measurements}',a)
    s=s[:a]+r'''\balance
'''+s[b:]
    # Keep the two immediately relevant offloading paragraphs in Background.
    # Move the broader comparison to the final body page, which also leaves
    # room for the Motivation text and graphic to share a page.
    a=s.index(r'\subsection{Related Expert-Serving Systems}')
    b=s.index(r'\section{Motivation and Insights}',a)
    paragraphs=[p for p in re.split(r'\n\s*\n',s[a:b]) if p.strip()]
    front='\n\n'.join(paragraphs[:2])+'\n\n'
    related=r'\section{Related Work}'+'\n'+'\n\n'.join(paragraphs[2:])+r'''

The granularity of the cached object determines which decisions can be compared directly. MoEpic retains expert segments, while SliceMoE retains precision slices~\cite{moepic,slicemoe}. HOBBIT and Specter use precision as part of the offloading decision~\cite{hobbit,specter}. MECC's current object is a complete FP16 expert, and its primary decision is the resident tier. Comparing these approaches therefore requires reporting both the stored representation and the quality protocol. A smaller transferred representation changes the traffic per miss, whereas a different retention rule changes which requests miss.

Request scheduling provides another source of overlap. Klotski constructs an expert-aware pipeline across batches; Bevy lets ready requests advance while other requests wait for expert fetches~\cite{klotski,bevy}. These systems create independent work across requests. MECC's delivery contract instead defines dependencies within the expert set revealed by the current gate. The amount of overlap available in a batch-one stream depends on ready computation and must be measured separately from the reduction in cold-tier demand.

'''
    comparison=r'''\begin{table}[H]
\centering\small
\caption{Control granularity and primary decisions in representative MoE-serving systems.}
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

'''
    related=related.replace('The granularity of the cached object',comparison+'The granularity of the cached object',1)
    s=s[:a]+front+s[b:]
    s=s.replace(r'\section{Background and Related Work}',r'\section{Background}')
    s=s.replace(r'\section{Conclusion}',related+r'\section{Conclusion}',1)
    return s
