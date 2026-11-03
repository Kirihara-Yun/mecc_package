"""Publication-size vector figures. Empirical inputs are frozen repository data.

Run from any directory. Does not execute inference or modify results/.
Schematic figures contain no fabricated measurements.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Circle

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'figures'
OUT.mkdir(exist_ok=True)
DATA = ROOT / 'results/raw/motivation_causal_replay_20261027_v2.json'
HIST = ROOT / 'results/raw/mixtral_real.json'
D = None
HD = None
BLUE, TEAL, ORANGE, GREY, INK = '#28649A', '#258779', '#C07832', '#8A929B', '#202A34'
COLORS = [GREY, '#BBC1C7', TEAL, BLUE, ORANGE, '#DFB383']
plt.rcParams.update({'font.family':'serif', 'font.serif':['Times New Roman', 'DejaVu Serif'],
    'font.size':8, 'axes.labelsize':8, 'axes.titlesize':8.5, 'legend.fontsize':7,
    'xtick.labelsize':7, 'ytick.labelsize':7, 'pdf.fonttype':42, 'ps.fonttype':42,
    'axes.linewidth':.6, 'lines.linewidth':1.1, 'savefig.facecolor':'white'})


def save(fig, name):
    for ext in ['pdf', 'svg', 'png']:
        fig.savefig(OUT / f'{name}.{ext}', dpi=240, bbox_inches='tight', pad_inches=.035)
    plt.close(fig)


def clean(ax, ylabel=None):
    ax.spines[['top','right']].set_visible(False)
    ax.grid(axis='y', color='#E3E6E9', lw=.45, zorder=0)
    ax.set_axisbelow(True)
    if ylabel:
        ax.set_ylabel(ylabel)


def txt(ax, x, y, s, size=8, **kw):
    ax.text(x,y,s,fontsize=size,va='center',ha='center',color=INK,**kw)


def arrow(ax, a, b, color=INK, **kw):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=8,
                                linewidth=.9,color=color,**kw))


def tile(ax,x,y,label,color=BLUE,w=.35,h=.24):
    ax.add_patch(Rectangle((x,y),w,h,facecolor=color,edgecolor='white',lw=.6))
    ax.text(
        x+w/2,y+h/2,label,fontsize=7,ha='center',va='center',color='white')


def overview():
    fig,ax=plt.subplots(figsize=(7.05,2.35)); ax.set(xlim=(0,10),ylim=(0,3)); ax.axis('off')
    for x,w,title in [(0,2.6,'(a) Sparse expert demand'),(3,2.6,'(b) Compile the initial state'),(6.05,3.9,'(c) Adapt residency online')]:
        txt(ax,x+w/2,2.84,title,9,weight='bold')
    txt(ax,.43,2.28,'Router',8)
    for i in range(8):
        xx=.2+(i%4)*.55; yy=1.2+(i//4)*.43
        tile(ax,xx,yy,f'$e_{i}$',BLUE if i in [1,6] else '#C8CDD2',w=.44,h=.31)
    arrow(ax,(.65,2.1),(.97,1.52),BLUE)
    arrow(ax,(.65,2.1),(1.52,1.96),BLUE)
    txt(ax,1.25,.79,'Only selected experts compute',7.5)
    txt(ax,1.25,.47,'All weights remain addressable',7.5)
    counts=[.86,.66,.54,.31,.24,.18,.12,.08]
    for i,v in enumerate(counts):
        ax.add_patch(Rectangle((3.18+i*.27,1.16),.19,v,fc=BLUE if i<2 else TEAL if i<6 else GREY))
    txt(ax,4.3,2.38,'Independent route profile',8)
    txt(ax,4.3,.86,'Ranked expert IDs + tier capacities',7.5)
    txt(ax,4.3,.46,'HBM / host budget supplied by user',7.5)
    arrow(ax,(5.59,1.56),(5.97,1.56))
    tiers=[('HBM',2.0,BLUE,[1,6]),('CPU pinned',1.28,TEAL,[0,3,4,2]),('SSD: all experts',.56,GREY,list(range(8)))]
    for name,y,color,ids in tiers:
        txt(ax,6.81,y+.12,name,8)
        ax.add_patch(Rectangle((7.48,y-.06),2.02,.38,fc='#F4F6F8',ec=color,lw=.7))
        for j,e in enumerate(ids):
            step,width=(.24,.21) if name.startswith('SSD') else (.45,.39)
            tile(ax,7.55+j*step,y,f'$e_{e}$',color,w=width,h=.24)
    arrow(ax,(9.68,1.4),(9.68,2.1),TEAL,connectionstyle='arc3,rad=.25')
    txt(ax,9.68,2.44,'Promote',7)
    arrow(ax,(7.29,2.03),(7.29,1.44),TEAL)
    txt(ax,6.69,1.77,'Retain',7)
    save(fig,'fig01_overview')


def records(work,arm):
    b=next(x for x in D['workloads'] if x['workload']==work)
    return [next(r for r in t['results'] if r['policy']==arm) for t in b['paired_trials']]


def motivation():
    fig,axs=plt.subplots(1,3,figsize=(7.05,2.0))
    fig.subplots_adjust(wspace=.48,bottom=.25,top=.82,left=.065,right=.99)
    ax=axs[0]; h=[16,32,64,128,256]
    for arm,c,m,label in [('random_joint',GREY,'s','Random initial state'),('profile_joint',BLUE,'o','Profile initial state')]:
        v=np.array([[r['startup_misses'][str(n)] for n in h] for r in records('stationary',arm)])
        ax.errorbar(h,v.mean(0),yerr=v.std(0,ddof=1),c=c,marker=m,ms=3,capsize=2,label=label)
    clean(ax,'Cumulative SSD demand misses')
    ax.set_xscale('log',base=2); ax.set_xticks(h,[str(x) for x in h]); ax.set_ylim(bottom=0)
    ax.set_xlabel('Requests since initialization'); ax.legend(loc='upper left',fontsize=6)
    ax.set_title('(a) Initial placement: same online rule')
    ax=axs[1]
    for j,(arm,c,hatch,label) in enumerate([('profile_static',GREY,'','Fixed CPU'),('profile_independent',ORANGE,'//','Independent LRU'),('profile_joint',BLUE,'','Exclusive joint LRU')]):
        v=[r['ssd_per_1000'] for r in records('drift',arm)]
        ax.bar(j,np.mean(v),yerr=np.std(v,ddof=1),capsize=2,width=.64,color=c,hatch=hatch,edgecolor='white',lw=.5)
        ax.text(j,np.mean(v)+np.std(v,ddof=1)+15,f'{np.mean(v):.1f}',ha='center',fontsize=7)
    clean(ax,'SSD misses / 1,000 requests')
    ax.set_xticks([0,1,2],['Fixed\nCPU','Independent\nLRU','Exclusive\njoint LRU']); ax.set_ylim(0,490)
    ax.set_title('(b) Retention: same profile and trace')
    ax=axs[2]; x=np.arange(16)*64+32
    for arm,c,ls,label in [('profile_static',GREY,'--','Fixed CPU'),('profile_independent',ORANGE,':','Independent LRU'),('profile_joint',BLUE,'-','Exclusive joint LRU')]:
        v=np.array([r['ssd_by_window'] for r in records('drift',arm)])
        ax.plot(x,v.mean(0),c=c,ls=ls,label=label)
    ax.axvline(512,c=INK,ls=':',lw=.7); ax.text(535,590,'Shift',fontsize=7)
    clean(ax,'SSD misses / 1,000 requests'); ax.set_ylim(0,650); ax.set_xticks([0,512,1024])
    ax.set_xlabel('Request index'); ax.legend(fontsize=6,loc='upper left')
    ax.set_title('(c) Drift: local windows expose adaptation')
    save(fig,'fig02_motivation')


def retention():
    fig,ax=plt.subplots(figsize=(3.42,2.0)); ax.set(xlim=(0,6.6),ylim=(0,3.8)); ax.axis('off')
    states=[([0,1],[2,3,4]),([1,2],[3,4,0]),([2,0],[3,4,1])]
    for i,(h,c) in enumerate(states):
        x=.13+i*2.19
        txt(ax,x+.8,3.48,['Initial state','Request $e_2$','Request $e_0$'][i],8,weight='bold')
        for j,e in enumerate(h): tile(ax,x+.18+j*.57,2.55,f'$e_{e}$',BLUE,w=.52,h=.39)
        for j,e in enumerate(c): tile(ax,x+j*.57,1.49,f'$e_{e}$',TEAL,w=.52,h=.39)
        txt(ax,x+.75,2.21,'HBM: LRU → MRU',6.5)
        txt(ax,x+.75,1.14,'CPU: LRU → MRU',6.5)
        if i<2: arrow(ax,(x+1.77,2.07),(x+2.08,2.07))
    txt(ax,3.26,.59,'CPU hit promotes the requested expert;',7.5)
    txt(ax,3.26,.25,'HBM victim remains available in CPU.',7.5)
    save(fig,'fig03_retention')


def controls():
    fig,ax=plt.subplots(figsize=(7.05,2.25)); fig.subplots_adjust(left=.075,right=.99,bottom=.2,top=.79)
    works=['stationary','drift','phase_shuffled','uniform']; xs=np.arange(4)
    arms=['random_static','profile_static','random_joint','profile_joint','random_independent','profile_independent']
    names=['Random + fixed CPU','Profile + fixed CPU','Random + joint LRU','Profile + joint LRU','Random + independent LRU','Profile + independent LRU']
    for j,(arm,c,label) in enumerate(zip(arms,COLORS,names)):
        means=[D['summaries'][w][arm]['ssd_per_1000_mean'] for w in works]
        sd=[D['summaries'][w][arm]['ssd_per_1000_sd'] for w in works]
        ax.bar(xs+(j-2.5)*.125,means,.117,yerr=sd,capsize=1.5,color=c,
               hatch='//' if 'independent' in arm else '',edgecolor='white',lw=.4,label=label)
    clean(ax,'SSD demand misses / 1,000 requests')
    ax.set_xticks(xs,['Stationary locality','Hotspot shift','Within-phase shuffle','Uniform IID'])
    ax.set_ylim(0,850); ax.legend(ncol=3,loc='lower center',bbox_to_anchor=(.5,1.01),frameon=False,columnspacing=1.2)
    save(fig,'fig04_factorial')


def order_and_cost():
    fig,axs=plt.subplots(1,2,figsize=(7.05,2.0)); fig.subplots_adjust(left=.07,right=.99,bottom=.24,top=.82,wspace=.45)
    ax=axs[0]
    for work,c,ls,label in [('drift',BLUE,'-','Original order'),('phase_shuffled',ORANGE,'--','Within-phase shuffle')]:
        values=[]
        for t in next(b for b in D['workloads'] if b['workload']==work)['paired_trials']:
            last={}; distances=[]
            for i,e in enumerate(t['trace']):
                if e in last: distances.append(len(set(t['trace'][last[e]+1:i])))
                last[e]=i
            values.append([np.mean(np.array(distances)<k) for k in range(1,17)])
        arr=np.array(values)
        ax.plot(range(1,17),arr.mean(0),c=c,ls=ls,label=label)
    ax.axvline(6,c=GREY,ls=':',lw=.8)
    clean(ax,'Reuses with distance below capacity')
    ax.set_xlabel('Distinct-object reuse distance threshold'); ax.set_ylim(0,1.03); ax.set_xticks([1,6,10,16])
    ax.legend(loc='lower right',frameon=False); ax.set_title('(a) Same phase histograms, different locality')
    ax=axs[1]
    for arm,c,m,label in [('profile_static',GREY,'s','Fixed CPU'),('profile_independent',ORANGE,'^','Independent LRU'),('profile_joint',BLUE,'o','Exclusive joint LRU')]:
        for w in ['drift','uniform']:
            rr=records(w,arm); x=np.mean([r['d2h_objects']*1000/1024 for r in rr]); y=np.mean([r['ssd_per_1000'] for r in rr])
            ax.scatter(x,y,edgecolors=c,marker=m,s=30,facecolors=c if w=='drift' else 'white',linewidths=1,label=label if w=='drift' else None,zorder=4)
    clean(ax,'SSD misses / 1,000 requests'); ax.set_xlabel('D2H object transfers / 1,000 requests')
    ax.set_xlim(-60,970); ax.set_ylim(0,850); ax.legend(loc='upper center',frameon=False,fontsize=6.8)
    ax.set_title('(b) Retention trades SSD reads for migration')
    ax.text(440,370,'Filled: hotspot shift\nOpen: uniform IID',fontsize=7,ha='center')
    save(fig,'fig05_order_migration')


def historical():
    fig,ax=plt.subplots(figsize=(3.42,1.78)); fig.subplots_adjust(left=.17,right=.98,bottom=.22,top=.95)
    r=HD['results']; x=np.arange(2); bottom=np.zeros(2)
    for key,c,name in [('hbm',BLUE,'HBM'),('cpu',TEAL,'CPU'),('ssd',GREY,'SSD')]:
        v=np.array([r[p]['hit_pct'][key] for p in ['swapmoe','ours']])
        ax.bar(x,v,.52,bottom=bottom,color=c,label=name,edgecolor='white',lw=.7)
        for i in range(2): ax.text(x[i],bottom[i]+v[i]/2,f'{v[i]:.1f}',ha='center',va='center',fontsize=8,color='white')
        bottom+=v
    clean(ax,'Recorded tier-access share (%)'); ax.set_ylim(0,102)
    ax.set_xticks(x,['Local fixed-CPU adapter','MECC']); ax.legend(ncol=3,loc='lower center',bbox_to_anchor=(.5,1.01),frameon=False)
    save(fig,'fig06_historical')


def comparison_design():
    fig,ax=plt.subplots(figsize=(3.42,1.72)); ax.set(xlim=(0,6.4),ylim=(0,3.4)); ax.axis('off')
    groups=[(.0,'1 GPU','Unoptimized'),(2.2,'1 GPU','MECC'),(4.4,'n GPUs','Resident reference')]
    for x,n,label in groups:
        txt(ax,x+.9,3.1,label,7.5,weight='bold')
        for i in range(1 if x<4 else 3):
            xx=x+.25+i*.29; yy=1.73+i*.15
            ax.add_patch(Rectangle((xx,yy),.92,.73,fc='#E9EFF5',ec=BLUE,lw=.9))
            for dx in [.14,.43,.72]:
                for dy in [.16,.44]: ax.add_patch(Rectangle((xx+dx,yy+dy),.14,.14,fc=BLUE,lw=0))
        txt(ax,x+.9,1.24,n,8)
        txt(ax,x+.9,.72,'TPOT / TTFT / throughput',6.5)
    txt(ax,3.1,.18,'Matched model, precision, input, and decoding settings',7)
    save(fig,'fig07_comparison_design')


def main():
    global D, HD
    D = json.loads(DATA.read_text(encoding='utf-8'))
    HD = json.loads(HIST.read_text(encoding='utf-8'))
    assert D['evidence_level']=='D1'
    overview(); motivation(); retention(); controls(); order_and_cost(); historical(); comparison_design()
    sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [DATA,HIST]}
    manifest={'sources':sources,'figure_types':{'fig01':'schematic','fig02':'D1 measured replay',
        'fig03':'schematic','fig04':'D1 measured replay','fig05':'D1 derived from frozen traces',
        'fig06':'D2 historical observation; not causal','fig07':'measurement design, no measured speeds'},
        'hypothetical_results_used':False,'seed_count':8,'error_bars':'sample standard deviation, ddof=1'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('7 figures saved as PDF/SVG/PNG:',OUT)


if __name__=='__main__': main()
