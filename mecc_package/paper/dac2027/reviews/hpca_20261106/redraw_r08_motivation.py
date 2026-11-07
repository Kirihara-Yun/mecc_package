"""One vector canvas for Figure 2; retain frozen arrays and measured sources."""
from pathlib import Path
import hashlib
import json
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent.parent
OUT = HERE/'r08_layout'
sys.path.insert(0, str(PAPER))
from build_measured_a100 import load
from build_manuscript_visuals import axis, txt, rect, ribbon

BLUE='#326C9B'; TEAL='#6D9FAD'; GRAY='#ABB5BD'; ORANGE='#C78D51'
INK='#203244'; PALE='#EAF0F4'; YELLOW='#FFF19A'
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],
    'mathtext.fontset':'stix','font.size':7.5,'axes.titlesize':8,
    'axes.titleweight':'normal','axes.labelsize':7.5,'xtick.labelsize':6.8,
    'ytick.labelsize':7,'legend.fontsize':6.2,'pdf.fonttype':42,
    'axes.linewidth':.5,'hatch.linewidth':.6})


def title(ax, text, highlight=False):
    t=ax.set_title(text,loc='left',pad=7,fontsize=8,fontweight='normal',color='black')
    if highlight:
        t.set_bbox({'facecolor':YELLOW,'edgecolor':'none','pad':1.2})


def style(ax, ylabel):
    ax.spines[['top','right']].set_visible(False)
    ax.grid(axis='y',color='#E1E6EA',lw=.4)
    ax.set_axisbelow(True)
    ax.tick_params(length=2,pad=2,width=.5)
    ax.set_ylabel(ylabel,labelpad=2)


def main():
    assumptions=json.loads((OUT/'ideal_assumptions.json').read_text(encoding='utf-8'))
    d=assumptions['motivation']; real=load()
    fig=plt.figure(figsize=(7.1,3.25))
    grid=fig.add_gridspec(2,3,left=.065,right=.985,bottom=.085,top=.94,
                         hspace=.50,wspace=.37,height_ratios=[1,1.08])
    top=[fig.add_subplot(grid[0,i]) for i in range(3)]
    bottom=[fig.add_subplot(grid[1,i]) for i in range(3)]
    ax=top[0];x=np.arange(4)
    for off,key,col,label in [(-.18,'ssd_misses_uniform',GRAY,'Uniform'),(.18,'ssd_misses_planned',BLUE,'Profile')]:
        ax.bar(x+off,d[key],.33,color=col,ec=INK,lw=.35,label=label,zorder=3)
    ax.set_xticks(x,['1–8','9–16','17–24','25–32']);ax.set_ylim(0,50)
    ax.set_xlabel('Layer group',labelpad=2);style(ax,'HDD-demand share (%)')
    ax.legend(ncol=2,frameon=False,loc='upper left',handlelength=1,columnspacing=.6)
    title(ax,'(a) Unequal layer pressure',True)
    rows=[real['independent'],real['main']['swapmoe'],real['main']['ours']]
    values=[r['metrics']['hit_pct']['ssd'] for r in rows]
    ax=top[1]
    bars=ax.bar(range(3),values,width=.55,color=[GRAY,ORANGE,BLUE],ec=INK,lw=.35,zorder=3)
    for bar,hatch in zip(bars,['...','///','xxx']):bar.set_hatch(hatch)
    ax.bar_label(bars,labels=[f'{v:.1f}' for v in values],padding=2,fontsize=6.6)
    ax.set_xticks(range(3),['Separate','Fixed CPU','MECC']);ax.set_ylim(0,60)
    style(ax,'HDD-demand share (%)');title(ax,'(b) Reuse after eviction')
    ax=top[2]
    for key,col,ls,label in [('fixed_windows',GRAY,'--','Fixed'),('online_windows',ORANGE,':','Online'),('mecc_windows',BLUE,'-','MECC')]:
        ax.plot(range(1,17),d[key],c=col,ls=ls,lw=.9,label=label)
    ax.axvline(8.5,c=INK,lw=.5,ls='--');ax.set_xticks([1,8,16]);ax.set_ylim(0,55)
    ax.set_xlabel('Request window (shift at 9)',labelpad=2);style(ax,'HDD-demand share (%)')
    ax.legend(ncol=3,frameon=False,loc='upper left',handlelength=1,columnspacing=.5)
    title(ax,'(c) Workload shift',True)
    for ax in bottom:axis(ax)
    a,b,c=bottom
    title(a,'(d) Rank, then divide capacity')
    xs=np.linspace(.07,.94,8);ps=np.array([.77,.64,.53,.44,.35,.28,.22,.17])
    a.plot(xs,.18+ps*.68,color=INK,lw=.85)
    for j,(x,p) in enumerate(zip(xs,ps)):
        color=BLUE if j<2 else TEAL if j<5 else GRAY
        a.vlines(x,.18,.18+p*.68,color=color,lw=2.5)
        a.scatter([x],[.18+p*.68],s=16,fc=color,ec='white',lw=.5,zorder=4)
        txt(a,x,.10,str(j+1),6.7)
    for cut in [(xs[1]+xs[2])/2,(xs[4]+xs[5])/2]:
        a.vlines(cut,.03,.86,color=ORANGE,lw=.7,ls='--')
    txt(a,.05,.91,'Selection probability',7,ha='left')
    for lo,hi,label,col in [(.03,.255,'HBM',BLUE),(.255,.63,'CPU',TEAL),(.63,.98,'HDD',GRAY)]:
        a.plot([lo,hi],[0,0],color=col,lw=3);txt(a,(lo+hi)/2,-.08,label,7)
    title(b,'(e) Promote and retain the victim')
    xs=np.linspace(.08,.93,5);before=[1,2,3,4,5];after=[3,1,2,4,5]
    for i,e in enumerate(before):
        ribbon(b,xs[i],xs[after.index(e)],.66,.30,
               ORANGE if e==3 else BLUE if e==2 else GRAY,
               .036 if e in (2,3) else .012,.8 if e in (2,3) else .3)
    for yy,state in [(.70,before),(.16,after)]:
        for i,e in enumerate(state):
            rect(b,xs[i]-.07,yy,.14,.13,'#FFF1DF' if e==3 else PALE,
                 ORANGE if e==3 else BLUE if i<2 else GRAY)
            txt(b,xs[i],yy+.065,f'$e_{e}$',7.5)
    b.vlines(.40,.12,.90,color=ORANGE,lw=.65,ls='--')
    txt(b,.17,.93,'HBM',7.2,color=BLUE);txt(b,.70,.93,'CPU',7.2)
    txt(b,.02,.58,'MRU',6.3,ha='left');txt(b,.97,.58,'LRU',6.3,ha='right')
    txt(b,.50,-.07,'Request $e_3$: host hit; $e_2$ stays warm',7)
    title(c,'(f) Correct the initial profile online')
    for block,ybase,label in [(0,.53,'Route'),(1,.08,'Cache')]:
        txt(c,0,ybase+.15,label,7.2,ha='left')
        for r,e in enumerate([1,2,6,7]):
            yy=ybase+.27-r*.085;txt(c,.20,yy+.026,str(e),6.2)
            for j in range(6):
                on=(r<2 if j<2 else r>=2)
                if block:on=(r<2 if j<3 else r in (1,2) if j==3 else r>=2)
                rect(c,.25+j*.12,yy,.096,.056,BLUE if on else PALE,'none',0)
    c.vlines(.475,.04,.90,color=ORANGE,lw=.7,ls='--')
    txt(c,.475,.94,'Task switch',7,color=ORANGE)
    txt(c,.60,-.07,r'Time $\longrightarrow$',7)
    dest=OUT/'figures'/'fig02_motivation_insights'
    for ext in ['pdf','png']:
        fig.savefig(dest.with_suffix('.'+ext),dpi=260,bbox_inches='tight',pad_inches=.025)
    plt.close(fig)
    record={'assumptions_sha256':hashlib.sha256((OUT/'ideal_assumptions.json').read_bytes()).hexdigest(),
            'measured':[{k:r[k] for k in ['run_id','sha256']} for r in rows],
            'measured_values':values,'style':{'panel_title_pt':8,'panel_title_weight':'normal'},
            'targets_preserved':['motivation.ssd_misses_uniform','motivation.ssd_misses_planned',
                                 'motivation.fixed_windows','motivation.online_windows','motivation.mecc_windows']}
    (OUT/'FIGURE2_SOURCES.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
