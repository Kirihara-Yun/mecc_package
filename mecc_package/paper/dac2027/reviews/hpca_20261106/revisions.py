"""Explicit review revisions. Numerical arrays and figure data stay frozen."""
from pathlib import Path
import re
from iterate import BASE,SOURCE,create

def block(s,label):
    for m in re.finditer(r'\\begin\{figure\}\[H\].*?\\end\{figure\}',s,re.S):
        if r'\label{'+label+'}' in m.group(0):return m.group(0)
    raise ValueError(label)

def section(s,name,end):
    return s[s.index(r'\section{'+name+'}'):s.index(r'\section{'+end+'}')]

def replace_section(s,name,end,new):
    a=s.index(r'\section{'+name+'}');b=s.index(r'\section{'+end+'}')
    return s[:a]+new+s[b:]

def r01(s):
    compile_fig=block(s,'fig:compile')
    retain_fig=block(s,'fig:retention')
    delivery_fig=block(s,'fig:delivery').replace('Delivery of resident','Prefill delivery of resident')
    method=r'''\section{Method}
\label{sec:method}
\subsection{Compiling Capacities and Initial Identities}
'''+compile_fig+r'''

Consider $L$ MoE layers with $N_\ell$ experts per layer. The evaluated models use equal-size experts and equal top-$k$ across layers. Let $s$ be expert size and let $B_{\mathrm H},B_{\mathrm C}$ be logical expert allowances. They supply $S_{\mathrm H}=\lfloor B_{\mathrm H}/s\rfloor$ HBM slots and $S_{\mathrm C}=\lfloor B_{\mathrm C}/s\rfloor$ CPU slots. Dense weights, activations, mirrors, and staging are separate allocations.

The compiler takes an expert order and a skew parameter $\alpha_\ell$ for each layer. Profile counts determine expert order; a discrete Zipf model supplies the marginal slot score:
\begin{equation}
q_{\ell,r}=\frac{r^{-\alpha_\ell}}{\sum_{j=1}^{N_\ell}j^{-\alpha_\ell}},
\qquad p_{\ell,r}=q_{\ell,r}/L.
\end{equation}
Here $r$ is a rank within one layer, not an expert ID shared across layers. Equal top-$k$ gives equal layer selection mass. Sorting counts preserves the mapping from each rank to its original expert ID.

Figure~\ref{fig:compile} shows the resulting cuts. A valid plan obeys $\sum_\ell K_{\mathrm H,\ell}\le S_{\mathrm H}$, $\sum_\ell K_{\mathrm C,\ell}\le S_{\mathrm C}$, and $K_{\mathrm H,\ell}+K_{\mathrm C,\ell}\le N_\ell$. The adaptive scan starts with one slot per layer in each fast tier. We consider allowances that support these minima and leave CPU ranks after the HBM cut.

The scan first assigns HBM slots. At each step, it chooses the layer with the largest next-rank score:
\begin{equation}
\Delta_\ell=q_{\ell,K_{\mathrm H,\ell}+1}.
\end{equation}
CPU allocation then compares ranks after each HBM cut. Allocating a slot exposes the next rank in that layer. Layer ID breaks score ties; expert ID breaks count ties. A direct scan costs $O(L(S_{\mathrm H}+S_{\mathrm C}))$ after sorting. It maximizes marginal coverage at each step; it does not solve a joint latency objective.

The plan emits per-layer capacities and ordered IDs. Initialization places the first HBM ranks on the GPU and the next CPU ranks on the host. Missing count data selects natural ID order. Capacities stay fixed during a run. Router requests can replace initial residents, including experts absent from the profile.

\subsection{Retaining Victims across the Tier Boundary}
Each layer keeps two ordered resident sets. Most-recently used (MRU) entries precede least-recently used (LRU) entries. HBM holds the first part of the logical order; CPU holds the next part. An HBM hit moves its expert to HBM MRU. A CPU hit removes its host entry and promotes it to HBM MRU. If HBM is full, its LRU victim becomes CPU MRU. CPU pressure removes the CPU LRU. HDD retains every backing expert.

'''+retain_fig+r'''
Figure~\ref{fig:retention} starts each row from HBM $[a_1,a_2]$ and CPU $[a_3,a_4]$. Requesting $a_2$ changes only HBM recency. Requesting $a_3$ gives HBM $[a_3,a_1]$ and CPU $[a_2,a_4]$. Requesting cold $a_5$ gives HBM $[a_5,a_1]$ and CPU $[a_2,a_3]$; $a_4$ leaves the fast tiers. Promotion preserves the more recent GPU victim in the position vacated on the host.

These completed serial transitions implement exclusive LRU across the combined logical capacity. Batch preparation can promote several experts before their consumers run. The serial stack describes replacement, while the batch path also needs temporary copies and a consumption order. Neither this stack rule nor an initial profile guarantees lower latency on every request stream.

The implementation retains a host mirror with each GPU resident. Demotion can reuse that mirror without D2H. Mirrors add physical host bytes; they do not add logical CPU slots. Logical eviction can release a cache entry before CUDA finishes using its storage. Tensor lifetime must therefore be tracked separately from membership.

\subsection{Ordering Delivery before Expert Consumption}
Prefill identifies the experts selected across its token rows. The runtime submits cold reads for those experts and resolves each read at consumption. Figure~\ref{fig:delivery} shows a prefill schedule in which a resident expert executes while another read progresses. Decode uses demand delivery rather than this prefill read batch. Both paths consume the original gate output and preserve expert aggregation order.

'''+delivery_fig+r'''
An SSD future must complete before its host weights can be copied. The implementation then waits on the copy stream before yielding CUDA weights to a consumer. Recording the consuming stream prevents allocator reuse while kernels still reference the tensors. These operations enforce read, copy, and use dependencies. The current synchronization covers the copy stream; it is not a per-expert readiness-event scheduler.

The schedule can reduce exposed delivery time without changing which requests miss. Its overlap depends on available resident work and on the submitted read batch. Cache coverage and delivery overlap therefore require separate comparisons.

\subsection{Sharing Execution and Accounting}
Policies share the FP16 loader and router. Accounting distinguishes unique primary residents, host mirrors, and staging storage. Initialization, warmup, prefill, decode, and PPL use separate windows. Logical slot counts describe the replacement experiment; physical allocations describe the host and GPU resources it consumes.

'''
    s=replace_section(s,'Method','Evaluation',method)
    s=s.replace('The delivery path determines when each selected expert becomes executable.',
                'The delivery path orders reads and copies before each selected expert executes.')
    return s

def r02(s):
    intro_fig=block(s,'fig:intro')
    intro=r'''\section{Introduction}
Mixture-of-experts (MoE) models expand parameter capacity while selecting a subset of experts for each token~\cite{shazeer,switch,mixtral,deepseekmoe}. Sparse execution reduces arithmetic. It leaves the full expert pool available for later selections. A single GPU may lack the HBM needed to retain that pool. A serving task may also receive less host memory than the server contains. This setting arises when jobs share a host or reserve resources for separate model instances. Expert demand can then reach HDD after missing both fast tiers. Every such miss adds weight delivery to the layer's execution path. A token crosses many MoE layers, so these delays can recur throughout decoding. Retaining weights across tokens can avoid repeated reads without changing the router or precision. We study how to allocate that retention capacity and update its contents during inference. The resource constraint belongs to the serving task: physical server capacity alone does not determine which weights the task can retain.

Expert parallelism distributes the expert pool over several GPUs~\cite{deepspeedmoe,tutel,flashmoedist}. Offloading systems instead manage transfers, host execution, and expert residency~\cite{offloading,moeinfinity,fiddler,lightning,promoe}. MoE-CORE combines layer-wise allocation, profile initialization, and online replacement~\cite{core}. SSD-LLaMA combines bounded RAM/VRAM caches with storage delivery~\cite{ssdllama}. Edge FlashMoE studies replacement under device-memory constraints~\cite{flashmoe}. These systems establish the importance of deciding which experts remain accessible after execution. MECC examines a specific coupling: an offline layer allocation supplies the initial state of a joint HBM/CPU retention rule. Initial coverage determines the first demand reads. Promotion and victim retention determine whether later selections require another cold read. Figure~\ref{fig:intro} isolates the latter decision in local A100 controls. Independent caches take 32.94~s per decode token, versus 7.38~s for joint retention at the same nominal slots and initialization. Their all-phase HDD-demand shares are 47.9\% and 12.5\%. These controls motivate studying cross-tier reuse; they do not rank the full implementations of the cited systems.

'''+intro_fig+r'''

We present \mecc{}, the MoE Expert Cache Compiler, for this allocation and retention problem. The compiler takes model metadata, task allowances, and layer profiles. It compares the next uncovered rank in each layer and emits HBM/CPU capacities with ordered expert IDs. Initialization loads those IDs into the fast tiers. During inference, the original router supplies demand. An HBM hit changes recency. A CPU hit promotes its expert and preserves the displaced HBM expert on the host. A cold admission follows the same promotion/demotion rule and can remove a host victim. Capacities remain fixed while resident identities follow the stream. Delivery resolves the selected experts' read and copy dependencies before their GPU consumers execute. The implementation batches cold reads during prefill and uses demand delivery during decode. This separates three responsibilities: selecting an initial state, retaining experts after tier crossings, and making selected weights available for computation. The compiler's output becomes the runtime's starting state; observed requests determine its later membership.

This paper makes three contributions.
\begin{list}{}{\setlength{\leftmargin}{16pt}\setlength{\labelwidth}{14pt}\setlength{\labelsep}{2pt}\setlength{\itemsep}{3pt}\setlength{\topsep}{3pt}}
\item[(1)] \textbf{Compiling initial residency:} we specify a layer-wise plan with capacities and expert IDs. A marginal-coverage scan allocates slots under fixed expert allowances.
\item[(2)] \textbf{Preserving cross-tier reuse:} we connect that plan to a joint promotion/demotion rule. We separate logical membership from the host mirrors and temporary copies used by delivery.
\item[(3)] \textbf{Characterizing the decisions:} we compare placement, retention, transfer exposure, and workload sensitivity under a shared inference interface. On one A100, uniform-initialized MECC takes 7.38~s/token, versus 13.04 for streaming and 21.75 for fixed CPU retention. These are local policy controls. The evaluation separates initial coverage from later replacement and examines the latency paid for using one accelerator.
\end{list}
'''
    a=s.index(r'\section{Introduction}');b=s.index(r'\twocolumn[{',a)
    s=s[:a]+intro+s[b:]
    abstract=r'''\begin{abstract}
Single-GPU MoE inference reads expert weights from HDD when a task's HBM and host allocation cannot retain the model. Initial placement and later GPU evictions determine how often these reads recur. We present MECC, the MoE Expert Cache Compiler, to connect layer-wise initial allocation with joint HBM/CPU retention. The compiler emits capacities and ranked expert IDs. The runtime promotes selected experts and retains GPU victims on the host. Delivery orders reads and copies before consumption. In single-run FP16 Mixtral-8x7B measurements on one A100, MECC with uniform initialization takes 7.38~s per decode token. This gives 1.77$\times$ the streaming rate and 2.95$\times$ the fixed-CPU rate, with matching sample perplexity.
\end{abstract}'''
    s=re.sub(r'\\begin\{abstract\}.*?\\end\{abstract\}',lambda _:abstract,s,count=1,flags=re.S)
    # Give Overview a lifecycle rather than another list of contributions.
    a=s.index('Figure~\\ref{fig:overview} organizes');b=s.index(r'\section{Method}',a)
    overview=r'''Figure~\ref{fig:overview} follows one model from preparation to inference. Offline profiling supplies layer/expert counts and skew parameters. The compiler combines those inputs with model metadata and task allowances. Its plan records per-layer capacities, ordered IDs, and initial tiers. Initialization reads the specified experts from HDD and populates HBM and CPU. The backing store retains the complete pool.

At each MoE layer, the gate produces selected IDs and weights. Residency lookup chooses HBM, CPU, or HDD as the source. Promotion makes the requested expert available on the GPU. Demotion preserves an HBM victim on the host when the retention rule admits it. Read and copy dependencies then order execution before output aggregation. Each generated token repeats this layer sequence; later tokens reuse the resulting resident state.

The interfaces separate what stays fixed from what changes. The plan fixes per-layer capacities. Accesses change membership and recency. Delivery controls when weights can be consumed. Placement comparisons therefore hold the runtime rule fixed. Retention comparisons hold initial capacities and IDs fixed. Scheduling comparisons use the same demand and resident state. This decomposition links the framework to the comparisons in Section~\ref{sec:evaluation} without treating any one component as a substitute for the others.

'''
    s=s[:a]+overview+s[b:]
    # Replace generic literature grouping with the two closest designs first.
    related=r'''\section{Related Work}
\textbf{Layer planning and online residency.} MoE-CORE combines nonuniform device capacity, domain-informed initialization, routing-history-aware replacement, and cross-layer prefetching~\cite{core}. Its main path executes the router-selected experts; substitution is optional. MECC also separates initialization from online membership. Its focus is the connection between per-layer allocation and joint HBM/CPU retention when a selected expert can miss both tiers. The overlap in these mechanisms makes whole-system feature counts an insufficient comparison.

\textbf{Storage-backed expert delivery.} SSD-LLaMA manages bounded RAM and VRAM caches, retains GPU victims on the host when possible, and pipelines expert reads and transfers~\cite{ssdllama}. It also studies lossless transport compression and CPU/GPU execution partitioning. Edge FlashMoE studies device-cache replacement with on-demand storage access~\cite{flashmoe}. MECC keeps FP16 representation and GPU expert execution fixed in its retention controls. These choices isolate residency decisions from transport format and execution placement; they do not imply that those other decisions are absent from prior work.

\textbf{Offloading, prediction, and execution.} Early expert offloading and SwapMoE expose placement and paging choices~\cite{offloading,swapmoe}. Fiddler and DAOP choose CPU/GPU work; MoE-Lightning pipelines heterogeneous execution; MoE-Infinity uses activation traces~\cite{fiddler,daop,lightning,moeinfinity}. ProMoE, Pre-gated MoE, Fate, and ExpertFlow use proactive caching, lookahead, or token scheduling~\cite{promoe,pregated,fate,expertflow}. HOBBIT and Specter vary loading precision; MoEpic uses segments; SliceMoE uses precision slices; Mira combines staging and quantization~\cite{hobbit,specter,moepic,slicemoe,mira}. ZipMoE uses compression and affinity scheduling~\cite{zipmoe}. These mechanisms change demand prediction, bytes per request, or where computation runs. A comparison of whole-expert retention keeps those choices fixed.

Klotski and Bevy expose work across batches or requests~\cite{klotski,bevy}. OD-MoE distributes on-demand loading across edge nodes; HeteGen studies heterogeneous dense inference~\cite{odmoe,hetegen}. Their scheduling scopes differ from delivery within the current MoE gate. Ready work from another request can hide a wait even when the ongoing request has no resident expert to execute. This distinction separates throughput from the response time of one request.

'''
    s=replace_section(s,'Related Work','Conclusion',related)
    return s

def r03(s):
    s=s.replace('It leaves the full expert pool available for later selections.',
                'Every expert can still be selected by a later token.')
    s=s.replace('This gives 1.77$\\times$ the streaming rate and 2.95$\\times$ the fixed-CPU rate, with matching sample perplexity.',
                'Decode speedups are 1.77$\\times$ over streaming and 2.95$\\times$ over fixed CPU retention. Sample perplexity matches these controls.')
    s=s.replace('Every such miss adds weight delivery to the layer\'s execution path.',
        '''Every such miss adds weight delivery to the layer's execution path. The fast tiers avoid different parts of that path. An HBM hit avoids both the cold read and H2D. A host hit avoids the cold read but still needs H2D. A placement decision therefore changes where a later request begins its delivery.''')
    s=s.replace('Initial coverage determines the first demand reads.',
        '''Initial coverage determines the first demand reads. The plan and the eviction rule affect different request segments. Loading a frequently selected expert can reduce early reads. Its first GPU eviction creates a later choice: retain it on the host or fetch it again. The host admission can also displace another expert. A plan's initial hit rate does not describe this sequence of choices.''')
    s=s.replace('Capacities remain fixed while resident identities follow the stream.',
        '''Capacities remain fixed while resident identities follow the stream. The plan retains layer IDs, so equal expert indices in different layers remain separate objects. An expert can enter HBM even when calibration never selected it.''')
    s=s.replace('These controls motivate studying cross-tier reuse; they do not rank the full implementations of the cited systems.',
                'The shared loader and initial state connect this difference to the local retention rules.')
    s=s.replace('The overlap in these mechanisms makes whole-system feature counts an insufficient comparison.',
                'Their overlap directs attention to the initial state, victim rule, and delivery path used by each comparison.')
    s=s.replace('These choices isolate residency decisions from transport format and execution placement; they do not imply that those other decisions are absent from prior work.',
                'Fixing representation and execution placement isolates the residency decision within the shared delivery stack.')
    s=s.replace('CPU pinned memory','CPU resident memory')
    motivation=r'''\section{Motivation and Insights}
\label{sec:challenges}
\subsection{Allocating Slots by Marginal Demand}
A slot can cover different request mass in different layers. Uniform allocation gives each layer the same capacity, even after its hottest experts fit. Figure~\ref{fig:insights}(a,d) connects the resulting pressure to a per-layer capacity cut. The next uncovered expert determines the gain from another slot. Comparing that gain across layers allocates capacity where it covers more demand. Ranking within each layer then determines the initial IDs. Capacity and identity are separate outputs: one sets the room available to a layer, and the other fills it. Routing locality across models has also been studied independently~\cite{routingconsistency}.

\subsection{Preserving Reuse after GPU Eviction}
A GPU eviction changes an expert's location before it determines the expert's next use. If the host retains the weights, another selection avoids HDD. Figure~\ref{fig:insights}(b,e) shows the promotion/demotion decision. Promotion vacates one CPU position as the HBM victim loses its GPU position. Joint retention reuses that host position for the victim. The local independent-cache control reports 47.9\% HDD demand, versus 12.5\% for joint retention across all instrumented phases. This comparison concerns the specified policies under the same initial slots. It motivates preserving the victim's place in the combined reuse order, rather than discarding its history at the HBM boundary.

\subsection{Updating Residency beyond Calibration}
A profile summarizes calibration inputs. The next prompt can select a different expert set before a fixed initial placement changes. Figure~\ref{fig:insights}(c,f) pairs the demand shift with an update of resident IDs. The compiler supplies capacities and a starting membership. Recency then changes membership within those capacities. Initial coverage controls early reads; online admission controls the response to later selections. These are separate time intervals in one cache lifecycle. A task switch can expose the distinction even when both methods start with the same profile. Updating IDs from actual requests lets the runtime respond without compiling a new plan or predicting a later gate.

'''
    # The wide Overview header precedes its section; keep that header intact.
    a=s.index(r'\section{Motivation and Insights}');b=s.index(r'\twocolumn[{',a)
    s=s[:a]+motivation+s[b:]
    s=s.replace('A CPU hit needs an H2D copy, while an HDD miss first reads the expert into host memory.',
        'A CPU hit needs a host-to-device (H2D) copy. An HDD miss first reads the expert into host memory.')
    s=s.replace('The profile describes an initialization prior, while the online policy operates on the actual request order.',
                'The profile initializes membership. Runtime requests determine its later order.')
    return s

def r04(s):
    # Account for split-box depth when packing the final balanced columns.
    # This changes box height, not font metrics or the diagnostic threshold.
    s=s.replace(r'\usepackage{balance}',r'''\usepackage{balance}
\makeatletter
\patchcmd{\@BAlancecol}
 {\setbox\@leftcolumn=\vbox to \@tempdima}
 {\@tempdimb=\ht1\advance\@tempdimb by\dp1
  \ifdim\@tempdimb>\@tempdima\@tempdima=\@tempdimb\fi
  \@tempdimb=\ht3\advance\@tempdimb by\dp3
  \ifdim\@tempdimb>\@tempdima\@tempdima=\@tempdimb\fi
  \setbox\@leftcolumn=\vbox to \@tempdima}
 {\typeout{MECC: balance packing includes split-box depth.}}
 {\errmessage{Failed to patch balanced-column packing}}
\makeatother''')
    s=s.replace('Single-GPU MoE inference reads expert weights',
                'Single-GPU mixture-of-experts (MoE) inference reads expert weights',1)
    s=s.replace("The readiness event orders $a_5$'s consumer;", "The copy/use boundary orders $a_5$'s consumer;")
    s=s.replace('A single GPU may lack the HBM needed to retain that pool.',
                'A single GPU may lack the high-bandwidth memory (HBM) needed to retain that pool.')
    s=s.replace('Expert demand can then reach HDD after missing both fast tiers.',
                'Expert demand can then reach a hard disk drive (HDD) after missing both fast tiers.')
    s=s.replace('physical server capacity alone does not determine which weights the task can retain.',
        '''physical server capacity alone does not determine which weights the task can retain. A deployment can trade resident multi-GPU latency for a smaller accelerator allocation.''')
    s=s.replace('and examines the latency paid for using one accelerator.',
        '''and examines the latency paid for using one accelerator. Comparisons report both response time and accelerator occupancy.''')
    s=s.replace('It motivates preserving the victim\'s place in the combined reuse order, rather than discarding its history at the HBM boundary.',
                'The victim keeps its place in the combined reuse order as it crosses the HBM boundary.')
    # State the MoE operation before discussing placement. It is a model
    # definition, not a new theorem or a numerical-equivalence claim.
    anchor='A generated token passes through successive layers, so expert demand is revealed incrementally during the forward pass.'
    operation=r'''For input $x$, let $G(x)$ be the selected set and $g_e(x)$ its normalized gate weights. The layer computes
\begin{equation}
y(x)=\sum_{e\in G(x)}g_e(x)E_e(x).
\end{equation}
'''
    s=s.replace(anchor,operation+anchor)
    anchor='Below full fast-tier coverage, requests can miss both HBM and CPU.'
    s=s.replace(anchor,'''Prefill groups prompt rows by their selected experts. One fetched expert can serve several rows. Decode advances one token per sequence. These phases expose different amounts of work for hiding delivery.

'''+anchor)
    s=s.replace('Perplexity uses 1024 WikiText-2 tokens.',
        '''Perplexity uses 1024 WikiText-2 tokens. TTFT is time to first token. TPOT is time per output token during decode.''')
    s=s.replace('RF and CPU-compute are local adapters within the shared harness.',
        '''RF is a local recency/frequency adapter derived from FlashMoE's public features. It uses HBM LRU and a CPU replacement score. CPU-compute is a separate local adapter.''')
    s=s.replace('These controls compare residency and execution decisions under one loader, rather than importing latency numbers from different machines.',
                'The shared loader keeps model loading and routing fixed across these residency and execution controls.')
    s=s.replace('Figure~\\ref{fig:target_ablation} tests component addition and startup amortization. The authored TPOT sequence is',
                'Figure~\\ref{fig:target_ablation}(a) compares component addition. Its TPOT sequence is')
    s=s.replace('With the plotted startup/decode costs, the target amortization curves cross at \\pending{9 output tokens}. This check exposes the service horizon over which an initial investment pays back.',
        r'''Panel (b) uses $T_{\mathrm{avg}}(n)=T_{\mathrm{init}}/n+T_{\mathrm{decode}}$ for $n$ output tokens. The curves cross at \pending{9 output tokens}. Before that point, MECC's initial cost dominates. Later outputs amortize initialization and expose the difference in decode time.''')
    s=s.replace('Its authored MECC target changes from','The MECC curve changes from')
    s=s.replace('The purpose is to separate pressure within the cold-tier regime from the full-coverage threshold.',
                'The sweep separates pressure within the cold-tier regime from the full-coverage threshold.')
    a=s.index(r'\section{Conclusion}');b=s.index(r'\clearpage',a)
    conclusion=r'''\section{Conclusion}
\looseness=1
MECC uses an offline plan to initialize a per-layer HBM/CPU expert cache. Online promotion preserves GPU victims on the host as routing changes. The implementation separates replacement from storage lifetime and orders reads and copies before execution. The A100 study reports decode latency, source-tier demand, and sample perplexity under a shared FP16 harness. Placement, retention, and delivery controls expose the decisions behind those outcomes.

'''
    s=s[:a]+conclusion+s[b:]
    return s

def redraw_framework(out):
    """Keep geometry, correcting three labels found during code review."""
    import ast
    root=BASE.parent.parent.parent
    original=(root/'build_paper_figures.py').read_text(encoding='utf-8')
    tree=ast.parse(original)
    defs={n.name:ast.get_source_segment(original,n) for n in tree.body if isinstance(n,ast.FunctionDef)}
    head='''from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, FancyBboxPatch
P=Path(__file__).resolve().parent
INK='#20242B'; BLUE='#245B8A'; TEAL='#39867F'; ORANGE='#BA7941'
GRAY='#899199'; LIGHT='#D3D8DD'; RULE='#DCE1E5'; PALE='#F4F6F8'
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],
 'mathtext.fontset':'stix','font.size':8,'text.color':INK,'pdf.fonttype':42,'svg.fonttype':'none'})
'''
    text=defs['text'].replace("    ax.text(","    s=s.replace('SSD','HDD')\n    ax.text(",1)
    save='''def save(fig,folder,name):
    dest=P/folder;dest.mkdir(exist_ok=True)
    for ext in ('pdf','png'):
        fig.savefig(dest/f'{name}.{ext}',dpi=260,bbox_inches='tight',pad_inches=.025)
    plt.close(fig)
'''
    fw=defs['framework'].replace('Delivery costs','Layer skew').replace(r'CPU pinned\nmemory',r'CPU resident\nmemory').replace(r'Readiness\nevent',r'Copy/use\nordering')
    code=head+'\n\n'.join([text,defs['arrow'],defs['box'],save,fw])+"\n\nif __name__=='__main__':framework()\n"
    (out/'redraw_framework.py').write_text(code,encoding='utf-8')
    import subprocess,sys
    subprocess.run([sys.executable,str(out/'redraw_framework.py')],check=True)

def main():
    import sys
    source=(BASE/SOURCE).read_text(encoding='utf-8')
    if len(sys.argv)>1 and sys.argv[1]=='r04':
        source=(BASE.parent/'r03_language/manuscript.tex').read_text(encoding='utf-8')
        out=create('r04_coldread',r04(source),source)
        import shutil
        for rel in ['figures/fig01_overview.pdf','figures/fig01_overview.png','redraw_framework.py']:
            shutil.copy2(BASE.parent/'r03_language'/rel,out/rel)
    elif len(sys.argv)>1 and sys.argv[1]=='r03':
        source=(BASE.parent/'r02_story/manuscript.tex').read_text(encoding='utf-8')
        out=create('r03_language',r03(source),source)
        redraw_framework(out)
    elif len(sys.argv)>1 and sys.argv[1]=='r02':
        source=(BASE.parent/'r01_method/manuscript.tex').read_text(encoding='utf-8')
        out=create('r02_story',r02(source),source)
    else:
        out=create('r01_method',r01(source),source)
    print(out)

if __name__=='__main__':main()
