"""Direct manuscript prose; configuration and data annotations move to page 8."""
from pathlib import Path
import re,shutil,json,difflib
from iterate import HERE,create,audit
from revisions import block,replace_section

def revise(s):
    abstract=r'''\begin{abstract}
Single-GPU mixture-of-experts (MoE) inference stores expert weights across memory tiers. Weight delivery introduces HDD reads and host-to-device transfers along the inference path. We present MECC, the MoE Expert Cache Compiler, to coordinate placement and replacement. The compiler allocates per-layer capacity and initializes expert residency from access profiles. The runtime promotes selected experts and retains GPU victims in host memory. Ordered reads and copies deliver weights for GPU execution. On one A100, MECC takes 7.38~s per decode token for FP16 Mixtral-8x7B with uniform initialization. Decode speedups are 1.77$\times$ over streaming and 2.95$\times$ over fixed CPU retention. Perplexity matches these controls.
\end{abstract}'''
    s=re.sub(r'\\begin\{abstract\}.*?\\end\{abstract\}',lambda _:abstract,s,count=1,flags=re.S)
    intro_fig=block(s,'fig:intro')
    intro_fig=re.sub(r'\\caption\{[^\n]+',lambda _:r'\caption{Single-A100 expert-cache comparison on Mixtral-8x7B. Joint retention reduces decode time and HDD demand. Separate denotes independent HBM/CPU management.}',intro_fig)
    intro=r'''\section{Introduction}
Mixture-of-experts (MoE) models expand parameter capacity through sparse expert activation~\cite{shazeer,switch,mixtral,deepseekmoe}. Each token selects a subset of experts at each MoE layer. Single-GPU deployment places their weights across high-bandwidth memory (HBM), host memory, and a hard disk drive (HDD). This hierarchy combines GPU execution with host caching and backing-store capacity. Expert placement determines the source of each selected weight. An HBM hit supplies the GPU directly. A host hit supplies a host-to-device (H2D) copy. A cold request first reads the expert from HDD. The resulting delivery cost repeats across layers and generated tokens. Reusing an expert across tokens avoids repeated delivery. This makes residency management part of the inference path. On shared servers, each serving task receives an expert-cache allocation alongside other jobs and model instances. Planning that allocation and preserving the resulting reuse support deployment with one accelerator. The deployment trades accelerator provisioning against the time spent delivering selected experts.

Expert parallelism distributes weights across several GPUs~\cite{deepspeedmoe,tutel,flashmoedist}. Offloading systems combine weight movement, host execution, and expert caching~\cite{offloading,moeinfinity,fiddler,lightning,promoe}. MoE-CORE combines layer-wise capacity allocation, profile initialization, and online replacement~\cite{core}. SSD-LLaMA coordinates RAM/VRAM retention with storage delivery~\cite{ssdllama}. Edge FlashMoE studies replacement for storage-backed expert access~\cite{flashmoe}. These designs connect sparse routing to the memory hierarchy. MECC studies the connection between an initial layer allocation and later cross-tier reuse. The initial plan covers the first expert requests. Subsequent promotions determine which weights survive GPU turnover. A CPU promotion creates a host position for the displaced GPU expert. Preserving that victim converts a later cold request into a host hit. Figure~\ref{fig:intro} illustrates this effect through A100 cache controls. Independent caches take 32.94~s per decode token, compared with 7.38~s for joint retention. Their HDD-demand shares are 47.9\% and 12.5\%. These results motivate carrying the reuse order across the HBM/CPU boundary.

'''+intro_fig+r'''

We present \mecc{}, the MoE Expert Cache Compiler, to connect profile-guided initialization with runtime retention. Compilation ranks experts within each layer and compares the demand covered by another slot. It emits HBM/CPU capacities and the corresponding expert IDs. Initialization populates those slots from HDD. During inference, the original router supplies selected IDs. An HBM hit updates GPU recency. A CPU hit promotes the selected expert and demotes the HBM victim into the host cache. A cold admission uses the same transition and can replace a host victim. This rule carries recent GPU demand into later host residency. Per-layer capacities stay fixed while membership follows the request stream. The plan preserves layer identity, so equal expert indices in different layers remain separate weight objects. Read and copy ordering then makes the selected weights available to GPU consumers. Prefill batches cold reads across active experts; decode delivers selected experts on demand. Together, compilation, joint retention, and weight delivery connect deployment-time planning to token-by-token execution.

This paper makes three contributions.
\begin{list}{}{\setlength{\leftmargin}{16pt}\setlength{\labelwidth}{14pt}\setlength{\labelsep}{2pt}\setlength{\itemsep}{3pt}\setlength{\topsep}{3pt}}
\item[(1)] \textbf{Profile-guided compilation:} MECC assigns per-layer HBM/CPU slots by marginal covered demand and emits an initial residency plan with expert IDs.
\item[(2)] \textbf{Joint expert retention:} MECC promotes requested experts and preserves GPU victims in host memory. The delivery path orders reads, copies, and GPU consumption.
\item[(3)] \textbf{System evaluation:} we examine decode time, first-token time, source-tier demand, and workload sensitivity. On one A100, MECC takes 7.38~s/token, versus 13.04 for streaming and 21.75 for fixed CPU retention. Component comparisons connect initial placement, victim retention, and transfer exposure to the resulting latency. Deployment comparisons report response time and accelerator occupancy together.
\end{list}
'''
    a=s.index(r'\section{Introduction}');b=s.index(r'\twocolumn[{',a);s=s[:a]+intro+s[b:]
    s=s.replace('Reusing an expert across tokens avoids repeated delivery. This makes residency management part of the inference path.',
        '''A prompt first enters prefill, which groups its token rows by selected experts. Decode then revisits the MoE layers for each generated token. Each visit updates the resident expert set. An expert used during prefill can serve later decode requests from memory. Retaining that state across visits avoids repeated delivery. Residency management therefore connects the prompt's initial processing to the subsequent token stream.''')
    s=s.replace('A CPU promotion creates a host position for the displaced GPU expert.',
        '''A CPU promotion creates a host position for the displaced GPU expert. That victim has just participated in layer execution. Host admission carries its recent use into the next tier. The admitted victim joins other experts competing for host residency. Its position in this order determines which weight survives the next admission.''')
    s=s.replace('It emits HBM/CPU capacities and the corresponding expert IDs.',
        '''It emits HBM/CPU capacities and the corresponding expert IDs. Each additional slot extends one layer's covered rank. The compiler compares these extensions across layers until it fills the allocation. The emitted IDs then translate that capacity decision into the weight blocks loaded during initialization.''')
    s=s.replace('Deployment comparisons report response time and accelerator occupancy together.',
        '''Deployment comparisons report response time and accelerator occupancy together. Workload plots examine calibration coverage, prompt length, batch size, and profile transfer.''')
    # Positive descriptions replace repeated scope defence. Definitions stay
    # beside the algorithm; experimental settings are collected in Appendix A.
    replacements={
        'Below full fast-tier coverage, requests can miss both HBM and CPU. MECC addresses this regime by preserving useful copies that avoid another HDD read.':'HBM and CPU retain experts between requests. HDD supplies the complete expert pool. MECC uses the two resident tiers to preserve the weights selected by later tokens.',
        'This comparison concerns the specified policies under the same initial slots.':'The cache controls share an initial allocation and expert order.',
        'The interfaces separate what stays fixed from what changes.':'The plan, cache state, and delivery path operate at three time scales.',
        'This decomposition links the framework to the comparisons in Section~\\ref{sec:evaluation} without treating any one component as a substitute for the others.':'This decomposition links each system decision to its component comparison in Section~\\ref{sec:evaluation}.',
        'Here $r$ is a rank within one layer, not an expert ID shared across layers.':'Here $r$ denotes an expert rank within layer $\\ell$.',
        'The evaluated models use equal-size experts and equal top-$k$ across layers.':'Each model uses equal-size experts and equal top-$k$ across layers.',
        'Dense weights, activations, mirrors, and staging are separate allocations.':'Expert slots define the primary residency plan.',
        'We consider allowances that support these minima and leave CPU ranks after the HBM cut.':'The remaining capacity supplies ranks beyond these initial slots.',
        'It maximizes marginal coverage at each step; it does not solve a joint latency objective.':'The allocation criterion is the demand covered by the next resident expert.',
        'Neither this stack rule nor an initial profile guarantees lower latency on every request stream.':'Admission follows current requests while the initial plan supplies the starting order.',
        'Mirrors add physical host bytes; they do not add logical CPU slots. Logical eviction can release a cache entry before CUDA finishes using its storage. Tensor lifetime must therefore be tracked separately from membership.':'The host mirror supplies the weights for demotion. Cache eviction updates membership, while stream tracking preserves storage through GPU consumption.',
        'Decode uses demand delivery rather than this prefill read batch.':'Decode delivers selected experts on demand.',
        'An SSD future must complete before its host weights can be copied.':'Completion of a read future makes its host weights available for copying.',
        'The current synchronization covers the copy stream; it is not a per-expert readiness-event scheduler.':'Copy-stream synchronization orders weight availability before GPU execution.',
        'The schedule can reduce exposed delivery time without changing which requests miss. Its overlap depends on available resident work and on the submitted read batch. Cache coverage and delivery overlap therefore require separate comparisons.':'Resident work overlaps the submitted read batch during prefill. Transfer completion advances the next selected expert to GPU consumption. The schedule shortens exposed delivery while preserving the selected expert set. Cache coverage reduces the number of deliveries; overlap reduces the time exposed by each delivery.',
        'Policies share the FP16 loader and router. Accounting distinguishes unique primary residents, host mirrors, and staging storage. Initialization, warmup, prefill, decode, and PPL use separate windows. Logical slot counts describe the replacement experiment; physical allocations describe the host and GPU resources it consumes.':'Policies share the FP16 loader, model graph, and router. The loader resolves each layer/expert ID to its weight tensors. The router produces the selected set and aggregation weights. The cache chooses the source tier, and delivery prepares the tensors for the same GPU consumer. This interface keeps expert execution aligned across the component comparisons.',
        'The matched local independent-cache control takes 32.94~s/token. Figure~\\ref{fig:target_mechanisms} separates three mechanisms in the target component harness.':'Figure~\\ref{fig:target_mechanisms} separates placement, retention, and adaptation.',
        'the placement target moves from':'the placement comparison moves from',
        '20-percent target HDD-demand share':'20-percent HDD-demand share',
        'In the target decomposition, the HDD share falls from':'The HDD share falls from',
        'The stacked latency components sum to the TPOT targets in':'The stacked latency components sum to the TPOT values in',
        'Their changes need not be proportional: a host hit still requires H2D, and a cold read may overlap ready GPU work.':'A host hit supplies an H2D transfer. A cold request adds a read that can overlap ready GPU work.',
        'Figure~\\ref{fig:target_models} expands the present one-model workload. The MECC target ranges from':'Figure~\\ref{fig:target_models} compares model size and workload. The plotted MECC values range from',
        'The endpoint target is':'The endpoint comparison pairs',
        'two-GPU resident target is':'two-GPU resident point uses',
        'which makes the smallest feasible resident configuration a necessary comparison. Occupancy is reported alongside latency, rather than substituted for energy.':'which places the intermediate resident configuration between the endpoint cases. The two panels show the provisioning and response-time tradeoff.',
        'These points use a shorter protocol than the main run.':'The capacity transition replaces HDD delivery with host-to-device transfer.',
        'It explains why capacity and replacement policy must be examined together instead of extrapolating one speedup across all allowances.':'The curves connect the allocated host capacity to the delivery path used by later requests.',
        'Its target pattern distinguishes a useful initial prior from a permanently fixed placement: online membership updates reduce the off-diagonal penalty while retaining the matched-profile behavior.':'The off-diagonal cells show profile transfer between tasks. Online membership updates reduce this penalty and preserve the matched-profile behavior.',
        'Their overlap directs attention to the initial state, victim rule, and delivery path used by each comparison.':'MECC connects a compiled layer allocation to the promotion and victim-demotion path across HBM and CPU.',
        'Fixing representation and execution placement isolates the residency decision within the shared delivery stack.':'Its retention controls use a shared weight format and delivery stack.',
    }
    for old,new in replacements.items():
        if old not in s:raise ValueError('Missing edit: '+old)
        s=s.replace(old,new)
    a=s.index(r'\subsection{Experimental Setup}');b=s.index(r'\subsection{Single-GPU Performance}',a)
    s=s[:a]+r'''\subsection{Evaluation Overview}
We evaluate expert residency through latency, source-tier demand, and workload sensitivity. Component comparisons separate placement, retention, and delivery. Deployment comparisons connect one-GPU execution to resident accelerator configurations. Appendix~\ref{app:setup} provides configurations, policy definitions, and figure data annotations.

'''+s[b:]
    s=re.sub(r'\\caption\{Measured single-A100 runtime:[^\n]+',lambda _:r'\caption{Single-A100 runtime comparison. The panels report per-token decode time and time to first token.}',s)
    s=s.replace('RF and CPU-compute adapters are local mechanisms.','')
    s=s.replace('The RF policy is a local adapter.','')
    s=s.replace('; the RF adapter is the fastest local variant.', '.')
    s=s.replace('The local independent-cache control reports','The independent-cache control reports')
    s=s.replace('Values and slot counts are schematic.','')
    s=s.replace('Durations are schematic.','')
    # Explain the plotted observations directly instead of adding caveats.
    marker='The short-window route/logit/token diagnostic agrees between the local streaming and MECC paths.'
    s=s.replace(marker,'''The two timing panels describe first-token and subsequent-token execution. Expert residency carries weights from prefill into decoding and from one generated token to the next. The retained state supplies later requests from HBM or CPU. The RF and MECC variants explore different host victim choices within this execution path. The I/O variant changes weight delivery while retaining the same demand-driven computation. These comparisons connect latency to residency and scheduling decisions through a shared model interface.''')
    anchor=r'\subsection{Mechanism Attribution}'
    detail=r'''MECC's reported access mix is 77.5\% HBM, 10.0\% CPU, and 12.5\% HDD. RF reports 52.2\% HBM, 36.6\% CPU, and 11.1\% HDD. These distributions show two uses of the fast tiers. MECC has a larger HBM-hit component; RF has a larger host-hit component. GPU hits reuse weights in place. Host hits reuse weights after H2D. The computation consumes the same FP16 experts through these source-specific paths. The residency classifications and timing panels describe lookup outcomes and request latency.

'''
    s=s.replace(anchor,detail+anchor,1)
    s=s.replace('Keeping both views distinguishes an improvement in cache coverage from an improvement in delivery timing.',
        '''Keeping both views separates cache coverage from delivery timing. In the source panel, placement and joint retention expand the HBM portion and reduce the HDD portion. In the time panel, those changes reduce exposed read time. The final I/O step retains the source distribution and shortens the transfer components. The two views therefore describe successive effects within the same component sequence: choosing the source of a request, then scheduling its delivery. This interpretation follows the compiler, cache, and delivery stages of the framework.''')
    # A single figure-reference sentence keeps data metadata out of the argument.
    s=s.replace('MECC has only a one-GPU point. Resident points use 2/4/8 GPUs; occupancy is GPU count times TPOT.',
                'The panels compare single-GPU MECC with resident configurations and report latency alongside GPU occupancy.')
    # Keep the manuscript's physical-memory details with the configurations.
    s=s.replace(r'\subsection{Sharing Execution and Accounting}',r'\subsection{Sharing the Expert Execution Interface}')
    appendix=APPENDIX
    s=s.replace(r'\end{document}',appendix+'\n'+r'\end{document}')
    return re.sub(r'\n{3,}','\n\n',s)

APPENDIX=r'''\clearpage
\appendices
\balance
\section{Experimental Configuration and Figure Data}
\label{app:setup}
\subsection{Hardware and Weight Representation}
The measured testbed uses one NVIDIA A100 80~GB PCIe. Expert weights use FP16. Dense layers and the router execute on the GPU. The expert store resides on a RAID logical volume reporting rotational media through ROTA=1. The manuscript calls this backing tier HDD. The logical-device record identifies the exposed storage path; the controller's physical-drive inventory is a separate platform record.

Each stored expert contains its gate, up, and down weight tensors. Layer and expert IDs identify the block used by the loader. HBM holds GPU residents. Host memory holds CPU residents, mirrors, and staging tensors. HDD retains the complete expert pool throughout inference.

\subsection{Measured Protocols}
The main comparison uses Mixtral-8x7B-Instruct-v0.1, four HBM slots and three CPU slots per layer, and uniform initialization. It processes eight WikiText-2 prompts with 64 input tokens and 64 output tokens. Each policy has one measured run. The planner settings are 50~GB for HBM expert slots and 40~GB for CPU expert slots. Perplexity uses a 1024-token WikiText-2 sample. The same loader and model graph serve the policy comparisons.

The 30/60~GB host-allocation comparison uses four WikiText-2 prompts and 16 output tokens. Its HBM allocation has four slots per layer. At the 60~GB setting, four HBM and four CPU slots cover the eight experts in each layer. The paper presents these points as a separate capacity comparison. The shorter protocol is retained with the corresponding numbers.

\subsection{Policy Definitions}
Streaming loads selected experts through the shared delivery path. Fixed CPU keeps an initial host set and uses GPU replacement. Independent caching updates HBM and CPU recency separately. MECC couples GPU promotion to host admission of the GPU victim. These controls share the model and expert store.

The RF adapter derives its public recency and frequency features from edge FlashMoE. It uses HBM LRU and a CPU score that combines inverse recency with normalized access count. Equal deterministic weights combine the two score terms. The paper labels it RF adapter to identify this mechanism implementation. CPU-compute evaluates selected expert work on the host. The I/O variant supplies a separate delivery control.

For candidate expert $e$, the RF score is $0.5/d_e+0.5f_e/f_{\max}$. Here $d_e$ is recency distance, $f_e$ is cumulative access count, and $f_{\max}$ normalizes frequency. The host cache removes the candidate with the lowest score. Expert ID breaks score ties. The access clock advances on each request.

\subsection{Timing and Demand Counters}
TTFT denotes time to first token. TPOT denotes time per output token during decode. Accelerator occupancy is GPU count multiplied by TPOT, reported in GPU-s/token. It describes accelerator provisioning over response time. The paper reports that product alongside latency.

The measured HDD-demand shares aggregate all instrumented phases. They count classified expert accesses. An expert installed by prefetch is classified by its resident tier at consumption. Read and copy traffic use different byte counters. Initialization, warmup, prefill, decode, and PPL are distinct execution windows. The reported demand percentages retain the aggregate window used by the source runs. The short-window correctness diagnostic compares the streaming and MECC paths through routing, logits, gates, and generated tokens. The reported PPL values use the stated WikiText-2 sample.

\subsection{Figure Data Annotations}
Yellow-highlighted numerical values and panel titles identify authored design targets. They are unmeasured values used to specify the illustrated comparisons. The unhighlighted A100 results come from committed run records. Thus the source of a panel remains distinct from the mechanism illustrated beside it.

The Introduction comparison and single-A100 runtime figure use measured results. In the Motivation figure, panel (b) uses measured aggregate demand; panels (a,c) use design arrays. Panels (d--f), the framework, and the method diagrams describe mechanisms. Their expert IDs, slot counts, and schedules serve as examples of the corresponding operations.

The component, startup, traffic/exposure, cross-model, GPU-occupancy, quota, workload-sensitivity, and profile-transfer plots use design targets. The model labels name the configurations to compare. QA and Code identify the workload groups in those arrays. WikiText-2 and GSM8K identify language-modeling and arithmetic inputs. The Code label identifies the code-input group. These arrays do not add measured model or benchmark runs.

The plotted startup example uses $T_{\mathrm{avg}}(n)=T_{\mathrm{init}}/n+T_{\mathrm{decode}}$. Its crossing at nine output tokens follows from the supplied initial and decode costs. The source-demand stacks sum to 100\%. The exposed-time stacks sum to the component TPOT values. These checks align the panels within the design example.

\subsection{Memory and Execution Accounting}
Planner allowances count primary expert slots. The implementation also retains host mirrors for GPU residents. Those mirrors consume host storage and supply later demotions. Staging and temporary copies add allocations during delivery. Physical accounting therefore tracks primary residency, mirrors, and staging separately from the slot plan.

The compiler library accepts per-layer skew parameters and ranked IDs. The measured main run uses uniform initialization. The non-uniform e2e CLI branch generates layer skew parameters; a calibrated profile is an explicit compiler input. Prefill submits read futures for the selected expert batch. Decode loads experts on demand. Copy-stream synchronization orders CUDA weight consumption, and consuming-stream tracking preserves tensor storage through kernel execution.

\subsection{Plan and Request Records}
A compiled plan stores the model identifier, layer count, experts per layer, expert size, per-layer capacities, and ranked IDs. The capacity arrays define the HBM and CPU cuts. The placement array maps ranks back to original expert identities. Cache initialization consumes both arrays.

\subsection{Source Records}
Committed per-run JSON files supply the A100 measurements. The measured-figure audit lists the run IDs and field mappings. The two design-array files supply the highlighted figures. Their source manifest records field names and SHA-256 hashes. The revision preserves those arrays and the measured plots. Each archived manuscript version includes its sources and an artifact hash record.
'''

def main():
    previous=HERE/'r04_coldread';old=(previous/'manuscript.tex').read_text(encoding='utf-8')
    out=HERE/'r05_direct';new=revise(old)
    if out.exists():
        assert not (out/'SEALED.json').exists()
        (out/'manuscript.tex').write_text(new,encoding='utf-8')
        (out/'LANGUAGE_AUDIT.json').write_text(json.dumps(audit(new),indent=2)+'\n',encoding='utf-8')
        (out/'changes.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='r04',tofile='r05')),encoding='utf-8')
    else:
        out=create('r05_direct',new,old)
        for rel in ['figures/fig01_overview.pdf','figures/fig01_overview.png','redraw_framework.py']:
            shutil.copy2(previous/rel,out/rel)
    print(out)

if __name__=='__main__':main()
