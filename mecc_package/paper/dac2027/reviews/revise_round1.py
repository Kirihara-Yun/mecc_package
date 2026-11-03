"""Deterministic editorial repairs; preserves all authored numeric targets."""
from pathlib import Path
P=Path(__file__).resolve().parents[1]
p=P/'mecc_dac2027.tex'
s=p.read_text(encoding='utf-8')
changes={
'Error bars show authored $\\pm3\\%$ spread.':'Targets have no error bars. Nominal allowances are 50~GB for experts and 40~GB for host memory; physical feasibility remains unverified.',
'It uses demand-driven staging with profile placement, dynamic CPU retention, and overlap disabled.':'It uses demand-driven staging. Profile placement, dynamic CPU retention, and transfer/computation overlap are all disabled. Default residency and achieved occupancy must be documented before this comparison is interpretable.',
'RF uses a recency/frequency heuristic;':'The recency/frequency (RF) adapter uses a heuristic whose precise rule remains to be frozen;',
'Error bars represent three authored values at $0.97$, $1.00$, and $1.03$ times each mean. They show hypothetical spread, not measured uncertainty.':'We omit authored repeat variation from the plots. Execution must report independent repeats, request-level distributions, and the statistic used for uncertainty. No uncertainty estimate is available in this draft.',
'All results, repeat variation, quality checks, and memory peaks below are authored targets. They are not measurements.':'All results and quality checks below are authored targets. They are not measurements. Budget feasibility and implementation correctness are prerequisites, not established outcomes.',
'Table~\\ref{tab:gpu} isolates the first deployment point. \\mecc{} uses one GPU at 8~s/token; the resident reference uses eight GPUs at 1~s/token. Both use 8 GPU-s/token. This point exchanges GPU allocation for latency at equal nominal GPU-time. Energy and monetary cost also depend on host work, SSD activity, utilization, interconnect, and billing.':'Table~\\ref{tab:gpu} includes every specified resident allocation. The two-GPU resident target is faster and uses fewer nominal GPU-seconds than single-GPU \\mecc{}. The one-GPU configuration instead tests feasibility when only one GPU can be allocated. A suitable use case is offline generation with a declared latency allowance; 127 decode intervals at 8~s take about 17 minutes. This does not establish GPU-time, energy, or monetary savings.',
'Metric & Single-GPU \\mecc{} & Resident reference\\\\\\midrule\nAllocated A100 GPUs & 1 & 8\\\\\nDecode time / token (s) & 8 & 1\\\\\nGPU-seconds / token & 8 & 8\\\\\\bottomrule':'Configuration & TPOT (s) & GPU-s/token\\\\\\midrule\n\\mecc{}, 1 GPU & 8.0 & 8.0\\\\\nResident, 2 GPUs & 2.8 & 5.6\\\\\nResident, 4 GPUs & 1.65 & 6.6\\\\\nResident, 8 GPUs & 1.0 & 8.0\\\\\\bottomrule',
'Placement and retention reduce cold demand.':'Placement and retention reduce the illustrated SSD demand share.',
'The placement comparison varies only initialization and charges initial transfers.':'Separate controls must vary layer allocation and initial expert identities while holding the other fixed, and charge initial transfers.',
'The retention comparison records duplicate bytes under each policy.':'The retention comparison must record duplicate bytes under each policy.',
'(b) GPU scaling on 8x7B question answering; one-GPU residency does not fit. (c) Initialization plus decode. An 18~s initial overhead and a 2~s/token saving yield equal total time at nine tokens.':'(b) Allocation comparison on 8x7B question answering; the full-model-resident reference exceeds one GPU. Only the single-GPU MECC design is specified. (c) Initialization plus decode intervals. An 18~s initial overhead and a 2~s/interval saving yield equality at nine intervals.',
'Physical use includes the mirrors and buffers defined in Section~IV.':'Each point requires independent physical accounting, including mirrors and buffers. These target curves do not establish feasibility under the stated cap.',
'\\mecc{} targets 8.0, 3.9, 2.1, and 1.25~s/token on one through eight GPUs. The comparison includes the smallest feasible resident configuration and exposes the latency--resource frontier.':'Only the single-GPU \\mecc{} target is shown. Earlier multi-GPU \\mecc{} targets are withdrawn from the figure because this draft does not specify that extension. The smallest feasible resident reference must remain in the comparison.',
'The totals are equal at nine output tokens; \\mecc{} is lower from ten tokens onward. This illustration covers initialization plus decode. A full request-cost analysis additionally includes model loading, profile generation, and prefill where they are not already charged.':'The plotted terms are equal at nine decode intervals after the first token. This is not a full-request crossover. For $n$ output tokens, full cost is $J(n)=I+\\mathrm{TTFT}+(n-1)\\mathrm{TPOT}$, with amortized profiling/loading included in $I$ and no double counting. The adapter TTFT and profile costs are unspecified, so no numerical full-request break-even follows.',
}
for old,new in changes.items():
    assert old in s,old
    s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
p=P/'build_ideal_figures.py'; s=p.read_text(encoding='utf-8')
changes={
"v,.145,yerr=v*.03,capsize=1.2,":"v,.145,",
"ax.plot(x,A['tpot_seconds'][name],c=c,marker=marker,ms=3,label=name)":"ax.scatter(x+(j-.5)*.16,A['tpot_seconds'][name],c=c,marker=marker,s=14,label=name,zorder=3)",
"['7B-Q','7B-C','22B-Q','22B-C']":"['8x7B / QA','8x7B / Code','8x22B / QA','8x22B / Code'],fontsize=6",
"Task CPU budget (GB)":"Task host-memory cap (GB)",
"('MECC',A['mecc_gpu_tpot_seconds'],B,'o')":"('MECC (one GPU)',[A['mecc_gpu_tpot_seconds'][0],None,None,None],B,'o')",
"ax.set_xlabel('Generated tokens')":"ax.set_xlabel('Decode intervals after first token',fontsize=6.5)",
"(c) Include the cost of the prior":"(c) Initialization + decode illustration",
"ax.axvline(8.5,c=I,lw=.6,ls=':');":"ax.axvline(8.5,c=I,lw=.6,ls=':'); ax.text(8.7,49,'Shift',fontsize=6);",
}
for old,new in changes.items():
    assert old in s,old
    s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
p=P/'verify_draft.py';s=p.read_text(encoding='utf-8').replace("'memory_target_within_caps':","'archived_memory_parts_arithmetic_only':")
s=s.replace("'All scenario outcomes require real experiments'","'All scenario outcomes require real experiments','Archived mirror breakdown is not physically feasible for full mirroring','Planner guards, async readiness, and phase counters need implementation validation'")
p.write_text(s,encoding='utf-8')
print('Round-one editorial repairs applied; numeric targets unchanged.')
