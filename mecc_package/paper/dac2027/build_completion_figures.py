"""Experiment-completion figures. Every unmeasured panel is yellow-tagged.

Targets are read from ideal_assumptions.json. No target is exported as a run.
Withdrawn memory examples, fake repeats, and multi-GPU MECC targets are unused.
"""
from pathlib import Path
import json
import hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from build_measured_a100 import load
from build_manuscript_visuals import insights

HERE=Path(__file__).resolve().parent
OUT=HERE/'completion_figures';OUT.mkdir(exist_ok=True)
A=json.loads((HERE/'ideal_assumptions.json').read_text(encoding='utf-8'))
BLUE='#326C9B';TEAL='#6D9FAD';GRAY='#ABB5BD';ORANGE='#C78D51';INK='#203244';YELLOW='#FFF19A'
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],'font.size':7.5,
 'axes.titlesize':8,'axes.labelsize':7.5,'xtick.labelsize':6.8,'ytick.labelsize':7,
 'legend.fontsize':6.2,'pdf.fonttype':42,'svg.fonttype':'none','axes.linewidth':.5})

def style(ax,ylabel):
    ax.spines[['top','right']].set_visible(False)
    ax.grid(axis='y',color='#E1E6EA',lw=.4);ax.set_axisbelow(True)
    ax.tick_params(length=2,pad=2,width=.5);ax.set_ylabel(ylabel,labelpad=2)
def target(ax,text='IDEAL TARGET — pending measurement'):
    ax.text(.5,1.22,text,transform=ax.transAxes,ha='center',va='bottom',fontsize=6.3,
            bbox={'facecolor':YELLOW,'edgecolor':'none','pad':1.5},clip_on=False)
def save(fig,name,source):
    for ext in ('pdf','png'):
        fig.savefig(OUT/f'{name}.{ext}',dpi=280,bbox_inches='tight',pad_inches=.025)
    plt.close(fig);MANIFEST[name]=source

MANIFEST={}
def motivation():
    d=A['motivation'];real=load()
    fig,axs=plt.subplots(1,3,figsize=(7.1,1.43))
    fig.subplots_adjust(.065,.26,.985,.78,wspace=.37)
    ax=axs[0];x=np.arange(4)
    for off,key,col,label in [(-.18,'ssd_misses_uniform',GRAY,'Uniform'),(.18,'ssd_misses_planned',BLUE,'Profile')]:
        ax.bar(x+off,d[key],.33,color=col,ec=INK,lw=.35,label=label,zorder=3)
    ax.set_xticks(x,['1–8','9–16','17–24','25–32']);ax.set_ylim(0,50)
    ax.set_xlabel('Layer group',labelpad=2);style(ax,'HDD-demand share (%)')
    ax.legend(ncol=2,frameon=False,loc='upper left',handlelength=1,columnspacing=.6)
    ax.set_title('(a) Unequal layer pressure',loc='left',pad=4);target(ax)
    ax=axs[1]
    rows=[real['independent'],real['main']['swapmoe'],real['main']['ours']]
    vals=[r['metrics']['hit_pct']['ssd'] for r in rows]
    b=ax.bar(range(3),vals,width=.55,color=[GRAY,ORANGE,BLUE],ec=INK,lw=.35,zorder=3)
    for bar,h in zip(b,['...','///','xxx']):bar.set_hatch(h)
    ax.bar_label(b,labels=[f'{v:.1f}' for v in vals],padding=2,fontsize=6.6)
    ax.set_xticks(range(3),['Separate','Fixed CPU','MECC']);ax.set_ylim(0,60)
    style(ax,'HDD-demand share (%)');ax.set_title('(b) Reuse after eviction',loc='left',pad=4)
    ax.text(.5,1.22,'MEASURED · Mixtral-8x7B / A100',transform=ax.transAxes,ha='center',fontsize=6.3,color=BLUE)
    ax=axs[2]
    for key,col,ls,label in [('fixed_windows',GRAY,'--','Fixed'),('online_windows',ORANGE,':','Online'),('mecc_windows',BLUE,'-','MECC')]:
        ax.plot(range(1,17),d[key],c=col,ls=ls,lw=.9,label=label)
    ax.axvline(8.5,c=INK,lw=.5,ls='--');ax.set_xticks([1,8,16]);ax.set_ylim(0,55)
    ax.set_xlabel('Request window (shift at 9)',labelpad=2);style(ax,'HDD-demand share (%)')
    ax.legend(ncol=3,frameon=False,loc='upper left',handlelength=1,columnspacing=.5)
    ax.set_title('(c) Workload shift',loc='left',pad=4);target(ax)
    save(fig,'motivation_evidence',{'target_fields':['motivation.ssd_misses_*','motivation.*_windows'],
         'measured':'DATA_AUDIT.json: independent, main.swapmoe, main.ours; all-phase hit_pct.ssd'})

def mechanisms():
    d=A['insight_ablation_targets']
    fig,axs=plt.subplots(1,3,figsize=(7.1,1.70))
    fig.subplots_adjust(.055,.27,.985,.76,wspace=.31)
    for ax,key,title in zip(axs,['placement_same_runtime','retention_same_initial_plan','adaptation_same_initial_plan'],
                            ['(a) Placement; runtime fixed','(b) Retention; plan fixed','(c) Adaptation after shift']):
        x=np.arange(3)
        for j,((name,vals),col,hatch) in enumerate(zip(d[key].items(),[GRAY,ORANGE,BLUE],['...','///','xxx'])):
            ax.bar(x+(j-1)*.23,vals,.21,color=col,ec=INK,lw=.35,hatch=hatch,label=name,zorder=3)
        ax.set_xticks(x,['Mixtral 7B','Qwen2 57B','Mixtral 22B']);ax.set_ylim(0,85)
        style(ax,'TPOT (s/token)');ax.set_title(title,loc='left',pad=4);target(ax)
        ax.legend(loc='upper left',frameon=False,fontsize=5.8,handlelength=1,labelspacing=.15)
    save(fig,'mechanism_sweeps',{'target_fields':['insight_ablation_targets.'+k for k in ['placement_same_runtime','retention_same_initial_plan','adaptation_same_initial_plan']]})

def cross_model():
    fig,ax=plt.subplots(figsize=(3.45,1.75));fig.subplots_adjust(.14,.25,.98,.75)
    x=np.arange(4)
    for j,(name,col,h) in enumerate([('Unoptimized streaming',GRAY,'...'),('RF adapter',ORANGE,'///'),('MECC',BLUE,'xxx')]):
        ax.bar(x+(j-1)*.23,A['tpot_seconds'][name],.21,color=col,ec=INK,lw=.35,hatch=h,label={'Unoptimized streaming':'Streaming'}.get(name,name),zorder=3)
    ax.set_xticks(x,['7B / QA','7B / Code','22B / QA','22B / Code']);ax.set_ylim(0,72)
    style(ax,'TPOT (s/token)');ax.legend(frameon=False,ncol=3,loc='upper left',handlelength=1,columnspacing=.7)
    target(ax);save(fig,'cross_model',{'target_fields':['groups','tpot_seconds.Unoptimized streaming','tpot_seconds.RF adapter','tpot_seconds.MECC']})

def ablation_startup():
    fig,axs=plt.subplots(1,2,figsize=(3.45,1.65));fig.subplots_adjust(.13,.30,.98,.72,wspace=.34)
    ax=axs[0];vals=A['ablation_tpot_seconds']
    ax.bar(range(4),vals,color=[GRAY,TEAL,ORANGE,BLUE],ec=INK,lw=.35,zorder=3)
    ax.set_xticks(range(4),['Base','+Plan','+Joint','+I/O'],rotation=25);style(ax,'TPOT (s/token)')
    ax.set_ylim(0,30);ax.set_title('(a) Component addition',loc='left',pad=3);target(ax,'IDEAL TARGET')
    ax=axs[1];n=np.array([1,4,16,64,256])
    for name,col in [('reference',GRAY),('MECC',BLUE)]:
        v=A['startup_cost_seconds'][name]/n+A['startup_decode_tpot_seconds'][name]
        ax.plot(n,v,c=col,marker='o',ms=2.5,lw=.8,label='Base' if name=='reference' else name)
    ax.set_xscale('log',base=4);ax.set_xticks([1,16,256],['1','16','256']);ax.set_xlabel('Output tokens',labelpad=2)
    style(ax,'Amortized s/token');ax.legend(frameon=False,fontsize=6);ax.set_title('(b) Initial cost',loc='left',pad=3);target(ax,'IDEAL TARGET')
    save(fig,'ablation_startup',{'target_fields':['ablation_tpot_seconds','ablation_ssd_percent','startup_cost_seconds','startup_decode_tpot_seconds'],
       'derived':'amortized = startup_cost / output_tokens + decode_tpot; fixed illustrative costs'})

def gpu_tradeoff():
    fig,axs=plt.subplots(1,2,figsize=(3.45,1.65));fig.subplots_adjust(.13,.26,.98,.74,wspace=.35)
    g=np.array([2,4,8]);v=np.array(A['resident_gpu_tpot_seconds'][1:])
    for ax,factor,title,ylabel in zip(axs,[np.ones(3),g],['(a) Response latency','(b) Accelerator occupancy'],['TPOT (s/token)','GPU-s/token']):
        ax.plot(g,v*factor,c=GRAY,marker='s',ms=3,lw=.9,label='Resident')
        ax.scatter([1],[A['mecc_gpu_tpot_seconds'][0]],c=BLUE,s=20,label='MECC (1 GPU)',zorder=4)
        ax.set_xticks([1,2,4,8]);ax.set_ylim(bottom=0);ax.set_xlabel('GPU count',labelpad=2)
        style(ax,ylabel);ax.set_title(title,loc='left',pad=3);target(ax,'IDEAL TARGET')
    axs[0].legend(frameon=False,fontsize=5.7,loc='upper right',handlelength=1)
    save(fig,'gpu_tradeoff',{'target_fields':['gpus','resident_gpu_tpot_seconds','mecc_gpu_tpot_seconds[0]'],
        'excluded':'No multi-GPU MECC values. No attribution to published FlashMoE.'})

def quota_targets():
    fig,ax=plt.subplots(figsize=(3.45,1.55));fig.subplots_adjust(.14,.28,.98,.75)
    for name,col,marker in [('Three-tier LRU',GRAY,'s'),('MECC',BLUE,'o')]:
        ax.plot(A['cpu_budget_gb'],A['budget_tpot_seconds'][name],c=col,marker=marker,ms=3,lw=.9,label=name)
    ax.set_xticks(A['cpu_budget_gb']);ax.set_ylim(0,32)
    ax.set_xlabel('Task host allowance (GB)',labelpad=2);style(ax,'TPOT (s/token)')
    ax.legend(frameon=False,fontsize=6.3);target(ax)
    save(fig,'quota_targets',{'target_fields':['cpu_budget_gb','budget_tpot_seconds'],
        'scope':'Authored dense-quota sweep; not merged with the measured four-prompt protocol.'})

def main():
    motivation();mechanisms();cross_model();ablation_startup();gpu_tradeoff();quota_targets()
    insights('insights_lower','def')
    MANIFEST['_source_sha256']=hashlib.sha256((HERE/'ideal_assumptions.json').read_bytes()).hexdigest()
    MANIFEST['_status']='Yellow-tagged targets are authored placeholders, not experiment results.'
    (OUT/'SOURCE_MANIFEST.json').write_text(json.dumps(MANIFEST,indent=2)+'\n',encoding='utf-8')
    print('Completion figures saved; all unmeasured panels carry yellow target labels.')

if __name__=='__main__':main()
