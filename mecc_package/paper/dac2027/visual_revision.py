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
    # Two result figures now occupy one column each. Their native fonts are
    # set for this size by build_compact_results.py.
    for label in ['fig:retention_result','fig:budget']:
        stem='retention' if label=='fig:retention_result' else 'budget'
        pattern=r'\\begin\{figure\*\}\[tb\]\s*\\centering\\includegraphics\[width=\\textwidth\]\{measured_figures/'+stem+r'\.pdf\}.*?\\label\{'+re.escape(label)+r'\}.*?\\end\{figure\*\}'
        match=re.search(pattern,s,re.S);assert match,label
        block=match.group(0).replace(r'\begin{figure*}[tb]',r'\begin{figure}[!t]').replace(r'\end{figure*}',r'\end{figure}').replace(r'width=\textwidth',r'width=\columnwidth')
        s=s[:match.start()]+block+s[match.end():]
    s=s.replace(r'\IEEEtriggeratref{22}',r'\IEEEtriggeratref{24}')
    s=s.replace('Three design insights, adapted from the MECC talk diagrams.',
                'Profile-guided placement and online correction.')
    s=s.replace('MECC framework, shared with the project presentation.',
                'MECC framework.')
    # Reserve one top-of-page block for the insight strip and framework.
    # This keeps each caption attached and gives Overview its actual diagram.
    blocks={}
    for label in ['fig:insights','fig:overview']:
        pattern=r'\\begin\{figure\*\}[^\n]*\n(?:(?!\\begin\{figure).)*?\\label\{'+re.escape(label)+r'\}.*?\\end\{figure\*\}'
        m=re.search(pattern,s,re.S);assert m,label
        block=m.group(0)
        block=re.sub(r'\\begin\{figure\*\}[^\n]*\n','',block)
        blocks[label]=block.replace(r'\end{figure*}','').replace(r'\caption{',r'\captionof{figure}{')
        s=s[:m.start()]+s[m.end():]
    s=s.replace(r'\section{Overview}',r'''\twocolumn[{
\begin{minipage}{\textwidth}
'''+blocks['fig:insights']+r'''
\section{Overview}
\label{sec:overview}
'''+blocks['fig:overview']+r'''
\vspace{8pt}
\end{minipage}
}]
''',1)
    # Remove the inherited label after the page block.
    s=s.replace('}]\n\n\\label{sec:overview}', '}]\n',1)
    for label in ['fig:compile','fig:retention','fig:delivery']:
        pattern=r'\\begin\{figure\}\[!t\]\n(?:(?!\\begin\{figure).)*?\\label\{'+re.escape(label)+r'\}.*?\\end\{figure\}'
        m=re.search(pattern,s,re.S);assert m,label
        block=m.group(0).replace(r'\begin{figure}[!t]',r'\begin{figure}[H]')
        s=s[:m.start()]+block+s[m.end():]
    pattern=r'\\begin\{figure\*\}\[tb\]\n(?:(?!\\begin\{figure).)*?\\label\{fig:performance\}.*?\\end\{figure\*\}'
    m=re.search(pattern,s,re.S);assert m,'performance placement'
    main=m.group(0).replace(r'\begin{figure*}[tb]',r'\begin{figure*}[!t]')
    s=s[:m.start()]+s[m.end():]
    s=s.replace(r'\section{Evaluation}',main+'\n\n'+r'\section{Evaluation}',1)
    panels={}
    for label in ['fig:retention_result','fig:budget']:
        pattern=r'\\begin\{figure\}\[!t\]\n(?:(?!\\begin\{figure).)*?\\label\{'+re.escape(label)+r'\}.*?\\end\{figure\}'
        m=re.search(pattern,s,re.S);assert m,label
        inner=m.group(0).replace(r'\begin{figure}[!t]','').replace(r'\end{figure}','')
        panels[label]=inner.replace(r'width=\columnwidth',r'width=\linewidth')
        s=s[:m.start()]+('RESULT_PAIR' if label=='fig:retention_result' else '')+s[m.end():]
    paired=r'''\begin{figure*}[!t]
\begin{minipage}[t]{0.48\textwidth}
'''+panels['fig:retention_result']+r'''
\end{minipage}\hfill
\begin{minipage}[t]{0.48\textwidth}
'''+panels['fig:budget']+r'''
\end{minipage}
\end{figure*}'''
    s=s.replace('RESULT_PAIR',paired)
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
\subsection{Reading the Capacity Transition}
The 60~GB plan has four HBM and four CPU slots per layer, covering all eight experts. MECC's zero cold-tier demand is consistent with this slot geometry. It does not mean that the model fits in HBM. At the smaller quota, the cache must decide which experts remain outside the fast tiers, and the replacement rule changes the observed reuse. The main and budget protocols use different prompt/output lengths, so only points within the matched budget protocol belong on the same curve.

'''+s[b:]
    return s
