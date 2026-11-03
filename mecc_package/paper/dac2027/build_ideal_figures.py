"""Hypothetical DAC manuscript figures; NEVER experiment data.

All numeric arrays below are authored design targets, including spread across
the illustrative repeats. They are not estimates from executing any system.
"""
from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt
import build_figures as style

HERE=Path(__file__).resolve().parent
OUT=HERE/'ideal_figures'
OUT.mkdir(exist_ok=True)
B,T,O,G,I=style.BLUE,style.TEAL,style.ORANGE,style.GREY,style.INK
A={
 'status':'HYPOTHETICAL DESIGN TARGETS; NOT MEASURED; NOT FOR SUBMISSION',
 'groups':['8x7B / QA','8x7B / Code','8x22B / QA','8x22B / Code'],
 'tpot_seconds':{
  'Unoptimized streaming':[24,31,49,62],
  'Three-tier LRU':[14,18,28,36],
  'RF adapter':[11,14,23,29],
  'SSD-native adapter':[10,13,21,27],
  'MECC':[8,9.5,16,19],
  'Resident 8-GPU reference':[1,1.2,1.8,2.1]},
 'ttft_seconds':{'Unoptimized streaming':[130,155,230,280],'MECC':[60,68,96,112],
                 'Resident 8-GPU reference':[5,5.5,8,9]},
 'motivation':{'cpu_slots_uniform':[4,4,4,4],'cpu_slots_planned':[2,3,5,6],
  'ssd_misses_uniform':[18,21,36,44],'ssd_misses_planned':[21,23,20,22],
  'retention_ssd_percent':[32,23,12],
  'fixed_windows':[18,17,18,17,18,17,18,17,43,44,43,44,43,44,43,44],
  'online_windows':[30,22,16,12,12,12,12,12,32,22,16,13,12,12,12,12],
  'mecc_windows':[14,13,12,12,12,12,12,12,32,22,16,13,12,12,12,12]},
 'ablation_tpot_seconds':[24,18,11,8],
 'ablation_ssd_percent':[46,33,20,20],
 'cpu_budget_gb':[16,24,32,40,48],
 'budget_tpot_seconds':{'Three-tier LRU':[27,21,17,14,12],'MECC':[16,12,9.5,8,7]},
 'gpus':[1,2,4,8],
 'resident_gpu_tpot_seconds':[None,2.8,1.65,1.0],
 'mecc_gpu_tpot_seconds':[8,3.9,2.1,1.25],
 'startup_cost_seconds':{'reference':12,'MECC':30},
 'startup_decode_tpot_seconds':{'reference':10,'MECC':8},
 'memory_gb':{'gpu_cap':80,'gpu_parts':[42,22,4,2],
              'cpu_cap':40,'cpu_parts':[28,6,4,2]},
 'quality':{'weight_hash_equal':True,'selected_experts_equal':True,
            'max_logit_error_sync':0,'ppl_delta':0},
 'illustrative_repeat_factors':[.97,1.,1.03],
 'repeat_note':'Authored +/-3% spread, not observed runs or confidence intervals',
 'comparison_note':'RF/SSD-native are hypothetical local matched adapters, not published system performance',
 'gpu_reference_note':'Eight-GPU full-model-resident execution is a scenario reference, not FlashMoE',
 'withdrawn_or_unused_targets':{
  'memory_gb':'WITHDRAWN as a feasible configuration: 42 GB HBM experts cannot have only 6 GB mirrors under full CPU mirroring. Arithmetic only; do not execute as a validated plan.',
  'mecc_gpu_tpot_seconds':'Only index 0 is used. Indices 1-3 are withdrawn from active figures: no multi-GPU MECC design is specified.',
  'illustrative_repeat_factors':'Archived authored factors; unused in figures and not statistical evidence.'},
}


def save(fig,name):
    fig.text(.995,1.12,'HYPOTHETICAL · NOT MEASURED',ha='right',va='top',fontsize=6,color='#704000',
             bbox={'boxstyle':'square,pad=0.18','facecolor':'#FFF299','edgecolor':'none'})
    for ext in ['pdf','svg','png']:
        fig.savefig(OUT/f'{name}.{ext}',dpi=240,bbox_inches='tight',pad_inches=.035)
    plt.close(fig)


def motivation():
    m=A['motivation']; fig,axs=plt.subplots(1,3,figsize=(7.05,2.07))
    fig.subplots_adjust(left=.06,right=.99,bottom=.25,top=.79,wspace=.48)
    ax=axs[0]; x=np.arange(4)
    for off,key,c,label in [(-.18,'ssd_misses_uniform',G,'Uniform slots'),(.18,'ssd_misses_planned',B,'Planned slots')]:
        ax.bar(x+off,m[key],.33,color=c,label=label,zorder=3)
    style.clean(ax,'SSD demand-miss share (%)'); ax.set_xticks(x,['1–8','9–16','17–24','25–32'])
    ax.set_xlabel('Layer group; slots: uniform 4/4/4/4; planned 2/3/5/6',fontsize=5.7); ax.set_ylim(0,52); ax.legend(frameon=False,fontsize=6.5)
    ax.set_title('(a) Equal total capacity, unequal pressure')
    ax=axs[1]; bars=ax.bar([0,1,2],m['retention_ssd_percent'],color=[G,O,B],width=.6,zorder=3)
    ax.bar_label(bars,labels=['32%','23%','12%'],padding=3,fontsize=7)
    style.clean(ax,'SSD demand-miss share (%)'); ax.set_ylim(0,40)
    ax.set_xticks([0,1,2],['Fixed\nCPU','Independent\nLRU','Joint\nretention'])
    ax.set_title('(b) Cross-tier retention preserves reuse')
    ax=axs[2]
    for key,c,ls,label in [('fixed_windows',G,'--','Fixed profile'),('online_windows',O,':','Online only'),('mecc_windows',B,'-','MECC')]:
        ax.plot(np.arange(16)+1,m[key],c=c,ls=ls,label=label)
    ax.axvline(8.5,c=I,lw=.6,ls=':'); ax.text(8.7,49,'Shift',fontsize=6); style.clean(ax,'SSD demand-miss share (%)')
    ax.set_xlabel('Request window'); ax.set_ylim(0,56); ax.set_xticks([1,8,16]); ax.legend(frameon=False,fontsize=6.5,ncol=1)
    ax.set_title('(c) Prior + online updates across a shift')
    save(fig,'fig02_challenges')


def main_performance():
    fig,axs=plt.subplots(1,2,figsize=(7.05,2.15),gridspec_kw={'width_ratios':[1.65,1]})
    fig.subplots_adjust(left=.065,right=.99,bottom=.23,top=.77,wspace=.34)
    ax=axs[0]; x=np.arange(4)
    for j,(name,c,ha) in enumerate(zip(list(A['tpot_seconds'])[:5],[G,'#B5BEC7',O,T,B],['','//','','',''])):
        v=np.array(A['tpot_seconds'][name]); ax.bar(x+(j-2)*.16,v,.145,
            color=c,hatch=ha,edgecolor='white',lw=.4,label=name,zorder=3)
    style.clean(ax,'Decode time / token (s) ↓'); ax.set_ylim(0,70)
    ax.set_xticks(x,A['groups']); ax.tick_params(axis='x',labelsize=6.5)
    ax.legend(ncol=3,loc='lower center',bbox_to_anchor=(.5,1.01),frameon=False,fontsize=6,columnspacing=.8)
    ax.set_title('(a) Same single-GPU hardware',y=1.29)
    ax=axs[1]
    for j,(name,c,marker) in enumerate([('MECC',B,'o'),('Resident 8-GPU reference',G,'s')]):
        ax.scatter(x+(j-.5)*.16,A['tpot_seconds'][name],c=c,marker=marker,s=14,label=name,zorder=3)
    style.clean(ax,'Decode time / token (s) ↓'); ax.set_ylim(0,23); ax.set_xticks(x,['8x7B / QA','8x7B / Code','8x22B / QA','8x22B / Code'],fontsize=6)
    ax.legend(frameon=False,fontsize=6,loc='upper left'); ax.set_title('(b) Single GPU vs. resident reference',y=1.29)
    save(fig,'fig04_performance')


def ablation():
    fig,axs=plt.subplots(1,2,figsize=(7.05,1.93)); fig.subplots_adjust(left=.065,right=.99,bottom=.29,top=.78,wspace=.42)
    names=['Streaming','+ Placement','+ Retention','+ Overlap']
    for ax,v,y,title in [(axs[0],A['ablation_tpot_seconds'],'Decode time / token (s) ↓','(a) Incremental execution stack'),
                         (axs[1],A['ablation_ssd_percent'],'SSD demand-miss share (%) ↓','(b) Demand-source accounting')]:
        bars=ax.bar(range(4),v,color=[G,O,T,B],width=.61,zorder=3)
        ax.bar_label(bars,padding=3,fontsize=7); style.clean(ax,y)
        ax.set_ylim(0,max(v)*1.22); ax.set_xticks(range(4),names,fontsize=7); ax.set_title(title)
    save(fig,'fig05_ablation')


def budget_and_cost():
    fig,axs=plt.subplots(1,3,figsize=(7.05,2.03)); fig.subplots_adjust(left=.065,right=.99,bottom=.25,top=.8,wspace=.5)
    ax=axs[0]
    for name,c,m in [('Three-tier LRU',G,'s'),('MECC',B,'o')]:
        ax.plot(A['cpu_budget_gb'],A['budget_tpot_seconds'][name],c=c,marker=m,ms=3,label=name)
    style.clean(ax,'Decode time / token (s) ↓'); ax.set_xlabel('Task host-memory cap (GB)'); ax.set_ylim(0,32)
    ax.legend(frameon=False,fontsize=6.5); ax.set_title('(a) Fixed GPU, varying host budget')
    ax=axs[1]
    for name,ys,c,m in [('Resident reference',A['resident_gpu_tpot_seconds'],G,'s'),('MECC (one GPU)',[A['mecc_gpu_tpot_seconds'][0],None,None,None],B,'o')]:
        ax.plot(A['gpus'],ys,c=c,marker=m,ms=3,label=name)
    style.clean(ax,'Decode time / token (s) ↓'); ax.set_xlabel('GPU count'); ax.set_ylim(0,9); ax.set_xticks([1,2,4,8])
    ax.text(1,1,'OOM',fontsize=7,color=G); ax.legend(frameon=False,fontsize=6.5); ax.set_title('(b) A latency–hardware frontier')
    ax=axs[2]; n=np.arange(0,65)
    for name,c,ls,label in [('reference',G,'--','SSD-native adapter'),('MECC',B,'-','MECC')]:
        cost=A['startup_cost_seconds'][name]+n*A['startup_decode_tpot_seconds'][name]
        ax.plot(n,cost,c=c,ls=ls,label=label)
    style.clean(ax,'Initialization + decode time (s) ↓'); ax.set_xlabel('Decode intervals after first token',fontsize=6.5); ax.set_ylim(0,720); ax.set_xticks([0,32,64])
    ax.axvline(9,c=O,lw=.7,ls=':'); ax.legend(frameon=False,fontsize=6.5)
    ax.set_title('(c) Initialization + decode illustration')
    save(fig,'fig06_budget_cost')


def hardware_cost():
    fig,axs=plt.subplots(1,3,figsize=(7.05,1.8)); fig.subplots_adjust(left=.06,right=.99,bottom=.25,top=.76,wspace=.47)
    for ax,ys,y,title in zip(axs,[[1,8],[8,1],[8,8]],['GPU count ↓','Decode time / token (s) ↓','GPU-seconds / token ↓'],
                            ['(a) Hardware footprint','(b) Token latency','(c) GPU-time proxy']):
        bars=ax.bar([0,1],ys,color=[B,G],width=.54,zorder=3); ax.bar_label(bars,padding=3,fontsize=8)
        style.clean(ax,y); ax.set_xticks([0,1],['MECC','Resident reference']); ax.set_ylim(0,10); ax.set_title(title)
    save(fig,'fig07_gpu_tradeoff')


def main():
    # The active paper uses the unified architecture/plot redraw, not the
    # retained early design functions above.
    from build_paper_figures import main as redraw
    redraw()
    assert sum(A['motivation']['cpu_slots_uniform'])==sum(A['motivation']['cpu_slots_planned'])
    assert sum(A['memory_gb']['gpu_parts'])<=80 and sum(A['memory_gb']['cpu_parts'])<=40
    (HERE/'ideal_assumptions.json').write_text(json.dumps(A,indent=2),encoding='utf-8')
    print('Hypothetical vector figures:',OUT)


if __name__=='__main__': main()
