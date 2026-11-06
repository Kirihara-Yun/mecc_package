"""Compact paper figures; values come from build_measured_a100.load()."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUT=Path(__file__).resolve().parent/'measured_figures'
INK='#203244'; BLUE='#326C9B'; TEAL='#6D9FAD'; GRAY='#ADB6BE'; ORANGE='#C78D51'
ORDER=['swapmoe','naive','fiddler','ours_io','ours','flashmoe_rf_adaptation']
LABELS=['Fixed CPU','Streaming','CPU compute','MECC I/O','MECC','RF adapter']
COLORS=[ORANGE,GRAY,GRAY,TEAL,BLUE,'#77A18B']
HATCH=['\\\\','///','...','---','xxx','+++']

def setup():
    plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],
     'font.size':7.5,'axes.titlesize':8,'axes.labelsize':7.5,
     'xtick.labelsize':7,'ytick.labelsize':7,'legend.fontsize':6.8,
     'pdf.fonttype':42,'svg.fonttype':'none','axes.linewidth':.5})
def style(ax,axis='x'):
    ax.spines[['top','right']].set_visible(False)
    ax.grid(axis=axis,color='#E0E6EB',lw=.4,zorder=0);ax.set_axisbelow(True)
    ax.tick_params(length=2,pad=2,width=.5)
def save(fig,stem):
    for ext in ('pdf','png'):
        fig.savefig(OUT/f'{stem}.{ext}',dpi=280,bbox_inches='tight',pad_inches=.025)
    plt.close(fig)

def render_results(data):
    setup();main=data['main']
    controls=[main['naive'],main['swapmoe'],data['independent'],main['ours']]
    fig,axs=plt.subplots(1,2,figsize=(3.45,1.48))
    fig.subplots_adjust(left=.19,right=.96,bottom=.25,top=.81,wspace=.31)
    for a,key,title,xlabel,limit in zip(axs,['tpot_ms','ssd'],
        ['(a) Decode latency','(b) HDD demand'],['TPOT (s/token)','Demand share (%)'],[43,63]):
        vals=[r['metrics']['hit_pct']['ssd'] if key=='ssd' else r['metrics'][key]/1000 for r in controls]
        bars=a.barh(range(4),vals,height=.58,color=[GRAY,ORANGE,GRAY,BLUE],ec=INK,lw=.4,zorder=3)
        for b,h in zip(bars,['///','\\\\','...','xxx']):b.set_hatch(h)
        a.bar_label(bars,labels=[f'{v:.1f}' for v in vals],padding=2,fontsize=6.5)
        a.set_yticks(range(4),['Streaming','Fixed CPU','Separate','MECC'] if a is axs[0] else ['']*4)
        a.invert_yaxis();a.set_xlim(0,limit);a.set_xticks([0,20,40] if key=='tpot_ms' else [0,25,50])
        a.set_xlabel(xlabel,labelpad=2);a.set_title(title,loc='left',fontweight='bold',pad=4);style(a)
    save(fig,'intro_evidence')
    fig,axs=plt.subplots(1,2,figsize=(3.45,1.82))
    fig.subplots_adjust(left=.21,right=.96,bottom=.24,top=.86,wspace=.28)
    for i,(a,key,title,xlabel,limit) in enumerate(zip(axs,
        ['tpot_ms','ttft_ms'],['(a) Decode latency','(b) First token'],
        ['TPOT (s/token)','TTFT (s)'],[25,450])):
        vals=[main[p]['metrics']['hit_pct']['ssd'] if key=='ssd' else main[p]['metrics'][key]/1000 for p in ORDER]
        bars=a.barh(range(6),vals,height=.62,color=COLORS,ec=INK,lw=.4,zorder=3)
        for b,h in zip(bars,HATCH):b.set_hatch(h)
        a.bar_label(bars,labels=[f'{v:.1f}' for v in vals],padding=2,fontsize=6.5)
        a.set_yticks(range(6),LABELS if i==0 else ['']*6);a.invert_yaxis()
        a.set_xlim(0,limit);a.set_xlabel(xlabel,labelpad=2)
        a.set_title(title,loc='left',fontweight='bold',pad=4);style(a)
    save(fig,'main')

    groups=[data['independent'],main['swapmoe'],main['ours']]
    fig,axs=plt.subplots(1,2,figsize=(3.45,1.63),gridspec_kw={'width_ratios':[.9,1.1]})
    fig.subplots_adjust(left=.19,right=.98,bottom=.24,top=.79,wspace=.26)
    vals=[r['metrics']['tpot_ms']/1000 for r in groups]
    bars=axs[0].barh(range(3),vals,height=.59,color=[GRAY,ORANGE,BLUE],ec=INK,lw=.4,zorder=3)
    for b,h in zip(bars,['///','\\\\','xxx']):b.set_hatch(h)
    axs[0].bar_label(bars,labels=[f'{v:.1f}' for v in vals],padding=2,fontsize=6.5)
    axs[0].set_yticks(range(3),['Independent','Fixed CPU','MECC']);axs[0].set_xlim(0,43)
    axs[0].set_xticks([0,20,40]);axs[0].set_xlabel('TPOT (s/token)',labelpad=2)
    axs[0].set_title('(a) Decode',loc='left',pad=4,fontweight='bold')
    left=np.zeros(3)
    for tier,col,hatch,name in [('hbm',BLUE,'xxx','HBM'),('cpu',TEAL,'///','CPU'),('ssd',ORANGE,'\\\\','HDD')]:
        vals=np.array([r['metrics']['hit_pct'][tier] for r in groups])
        axs[1].barh(range(3),vals,left=left,height=.59,color=col,ec=INK,lw=.35,hatch=hatch,label=name,zorder=3)
        left+=vals
    axs[1].set_xlim(0,100);axs[1].set_xticks([0,50,100]);axs[1].set_yticks(range(3),['']*3)
    axs[1].set_xlabel('Demand share (%)',labelpad=2)
    axs[1].set_title('(b) Source tier',loc='left',pad=4,fontweight='bold')
    fig.legend(*axs[1].get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.65,1.04),ncol=3,
               frameon=False,columnspacing=.8,handlelength=1,handletextpad=.3,fontsize=6.5)
    for a in axs:a.invert_yaxis();style(a)
    save(fig,'retention')

    fig,axs=plt.subplots(1,2,figsize=(3.45,2.0))
    fig.subplots_adjust(left=.13,right=.98,bottom=.34,top=.85,wspace=.37)
    keys=['naive','swapmoe','ours','flashmoe_rf_adaptation','fiddler']
    cols=[GRAY,ORANGE,BLUE,'#77A18B','#846A96'];markers=['s','^','o','D','v']
    names=['Streaming','Fixed CPU','MECC','RF adapter','CPU compute']
    for ax,key,title,ylabel in zip(axs,['tpot_ms','ssd'],['(a) Decode','(b) Cold-tier demand'],['TPOT (s/token)','Demand share (%)']):
        for p,col,marker,name in zip(keys,cols,markers,names):
            vals=[data['budget'][c][p]['metrics']['hit_pct']['ssd'] if key=='ssd' else
                  data['budget'][c][p]['metrics'][key]/1000 for c in (30,60)]
            ax.plot([30,60],vals,c=col,marker=marker,ms=3,lw=.9,label=name)
        ax.set_xticks([30,60]);ax.set_xlim(27,63);ax.set_ylim(bottom=-1)
        ax.set_xlabel('CPU allowance (GB)',labelpad=2);ax.set_ylabel(ylabel,labelpad=2)
        ax.set_title(title,loc='left',fontweight='bold',pad=4);style(ax,'y')
    fig.legend(*axs[0].get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.52,-.015),ncol=3,
               frameon=False,columnspacing=.8,handlelength=1.3,handletextpad=.35,fontsize=6.5)
    save(fig,'budget')
