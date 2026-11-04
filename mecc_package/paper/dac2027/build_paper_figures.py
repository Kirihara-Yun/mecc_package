"""Camera-size vector redraws. Numeric inputs remain authored design targets.

One terminology and typography scheme for every active manuscript figure.
No GPU work, inferred measurements, or new numerical outcomes.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from media_hdd import figure_text
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, FancyBboxPatch
from build_ideal_figures import A

P=Path(__file__).resolve().parent
INK='#20242B'; BLUE='#245B8A'; TEAL='#39867F'; ORANGE='#BA7941'
GRAY='#899199'; LIGHT='#D3D8DD'; RULE='#DCE1E5'; PALE='#F4F6F8'
LABELS={'tpot':'TPOT (s/token)', 'miss':'SSD demand-miss share (%)',
        'host':'Task host-memory cap (GB)', 'hbm':'HBM',
        'cpu':'CPU pinned memory', 'ssd':'SSD backing store'}
plt.rcParams.update({
 'font.family':'serif','font.serif':['Times New Roman'],
 'mathtext.fontset':'stix','font.size':8,'axes.titlesize':8.5,
 'axes.labelsize':8,'xtick.labelsize':7.5,'ytick.labelsize':7.5,
 'legend.fontsize':7,'axes.linewidth':.6,'lines.linewidth':1.25,
 'text.color':INK,'axes.labelcolor':INK,'xtick.color':INK,'ytick.color':INK,
 'pdf.fonttype':42,'ps.fonttype':42,'savefig.facecolor':'white',
})

def text(ax,x,y,s,size=8,**kw):
    ax.text(x,y,s,fontsize=size,ha=kw.pop('ha','center'),
            va=kw.pop('va','center'),color=kw.pop('color',INK),**kw)

def arrow(ax,a,b,color=INK,style='-',lw=.8,rad=0):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=7,
      lw=lw,color=color,linestyle=style,connectionstyle=f'arc3,rad={rad}'))

def box(ax,x,y,w,h,fc='white',ec=RULE,lw=.7):
    ax.add_patch(Rectangle((x,y),w,h,facecolor=fc,edgecolor=ec,lw=lw))

def clean(ax,y=None):
    ax.spines[['top','right']].set_visible(False)
    ax.grid(axis='y',color=RULE,lw=.45,zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=2.5,width=.55,pad=2)
    if y: ax.set_ylabel(y,labelpad=4)

def save(fig,folder,name,hypothetical=False):
    figure_text(fig)
    dest=P/folder; dest.mkdir(exist_ok=True)
    if hypothetical:
        fig.text(.992,.992,'HYPOTHETICAL · NOT MEASURED',fontsize=6,
          color='#704000',ha='right',va='top',
          bbox={'facecolor':'#FFF299','edgecolor':'none','pad':1.3})
    for ext in ['pdf','svg','png']:
        fig.savefig(dest/f'{name}.{ext}',dpi=260,bbox_inches='tight',pad_inches=.025)
    plt.close(fig)

def overview():
    fig,ax=plt.subplots(figsize=(7.05,2.25))
    fig.subplots_adjust(left=.005,right=.995,bottom=.02,top=.98)
    ax.set(xlim=(0,100),ylim=(0,31)); ax.axis('off')
    # Phases are spatially separated; the runtime never feeds its route back
    # into the independent offline profile shown on the left.
    box(ax,.5,3.2,60.2,25.4,PALE,ec=RULE)
    text(ax,30.5,30,'OFFLINE COMPILATION',8,color=GRAY,weight='bold')
    text(ax,80.5,30,'ONLINE EXECUTION',8,color=GRAY,weight='bold')
    text(ax,15.7,26.6,'(a) Independent route profile',8.5,weight='bold')
    text(ax,46.5,26.6,'(b) Residency plan',8.5,weight='bold')
    text(ax,80.6,26.6,'(c) Retention and delivery',8.5,weight='bold')
    heat=np.array([[.95,.7,.3,.15,.10,.06,.03,.02],
      [.92,.6,.45,.3,.14,.08,.05,.03],[.8,.7,.6,.5,.3,.2,.1,.06],
      [.7,.65,.6,.55,.5,.35,.2,.1]])
    for r in range(4):
        yy=20.5-r*3.4
        text(ax,3.8,yy+1,r'$\ell_'+str(r+1)+'$',8)
        for j in range(8):
            c=plt.cm.Blues(.09+.83*heat[r,j])
            box(ax,6.2+j*2.65,yy,2.27,2.05,c,'white',.6)
    text(ax,16.6,23.9,'Expert ID',7.5)
    for j in [0,3,7]: text(ax,7.3+j*2.65,6.8,str(j),7)
    text(ax,16.7,4.9,'Darker = more selections',7.2,color=GRAY)
    arrow(ax,(29,16),(34,16),BLUE)
    # Colored slots show the emitted capacities; these are schematic counts.
    text(ax,39.5,23.6,r'$K_{\mathrm{H},\ell}$',8)
    text(ax,52,23.6,r'$K_{\mathrm{C},\ell}$',8)
    for r,(nh,nc) in enumerate([(2,3),(1,4),(3,2),(2,3)]):
        yy=20.6-r*3.4
        for j in range(nh): box(ax,35.4+j*2.7,yy,2.2,1.85,BLUE,'white',.6)
        for j in range(nc): box(ax,47+j*2.7,yy,2.2,1.85,TEAL,'white',.6)
    text(ax,46.6,7.1,'Ranked expert IDs',7.5)
    text(ax,46.6,4.9,'Task memory caps',7.5)
    # Plan affects capacities and initial IDs, not the router's selections.
    arrow(ax,(61.2,24),(67.2,24),GRAY,'--')
    text(ax,64.1,25.25,'Initialize',7,color=GRAY)
    tiers=[('HBM',19.1,BLUE,[0,1,3]),
           ('CPU pinned memory',12.7,TEAL,[2,4,5]),
           ('SSD backing store',6.3,GRAY,list(range(8)))]
    for label,yy,c,ids in tiers:
        text(ax,80.3,yy+3.8,label,8,weight='bold')
        box(ax,68.4,yy,23.7,2.6,'white',c,.8)
        w,step=(2.42,2.8) if len(ids)>4 else (4.4,5.1)
        for j,e in enumerate(ids):
            xx=69.1+j*step
            box(ax,xx,yy+.35,w,1.85,c,'white',.6)
            text(ax,xx+w/2,yy+1.27,r'$e_'+str(e)+'$',7,color='white')
    arrow(ax,(67,15.6),(67,18.8),TEAL)
    text(ax,65.2,17.1,'H2D',6.8,rotation=90)
    arrow(ax,(94.0,18.8),(94.0,15.6),BLUE)
    text(ax,96.5,17.1,'Demote',6.8,rotation=90)
    arrow(ax,(67,9.2),(67,12.4),GRAY)
    text(ax,65.2,10.9,'Read',6.8,rotation=90)
    text(ax,80.2,4.0,'Backing weights: all experts',7.3,color=GRAY)
    text(ax,30.5,.7,'Dashed: plan metadata     Solid: weight movement',7.3,color=GRAY)
    text(ax,80.2,.7,'Copy → readiness event → expert execution',7.0,color=INK)
    save(fig,'figures','fig01_overview')

def framework():
    """Architecture plate: software/control above a concrete memory datapath."""
    fig,ax=plt.subplots(figsize=(7.05,2.48))
    fig.subplots_adjust(left=.005,right=.995,bottom=.015,top=.99)
    ax.set(xlim=(0,100),ylim=(-1.5,33)); ax.axis('off')
    box(ax,.5,1,30.5,29.5,PALE,RULE,.65)
    box(ax,35,1,64,29.5,'white',RULE,.65)
    text(ax,15.8,32,'Offline compilation',9,weight='bold')
    text(ax,67,32,'Online execution',9,weight='bold')
    # Profile is an actual layer/expert array, not a generic input rectangle.
    for r in range(3):
        for j,v in enumerate([.92,.7,.45,.25,.13,.06]):
            box(ax,3.2+j*1.75,25-r*1.6,1.48,1.25,plt.cm.Blues(.12+.8*v),'white',.3)
    text(ax,8.4,28.4,'Route profile',7.6)
    text(ax,23,27,'Model metadata',7.5)
    text(ax,23,24.7,'Task memory caps',7.5)
    text(ax,23,22.4,'Delivery costs',7.5)
    arrow(ax,(8.4,21.4),(8.4,19.5),GRAY,'--')
    arrow(ax,(23,21.4),(23,19.5),GRAY,'--')
    box(ax,3.0,13,25.5,6.0,'white',BLUE,.9)
    text(ax,15.8,17.0,'Placement compiler',8.5,weight='bold')
    text(ax,15.8,14.7,'Rank experts · allocate slots',7.4)
    arrow(ax,(15.8,12.8),(15.8,10.6),GRAY,'--')
    box(ax,3.0,3,25.5,7,'white',BLUE,.9)
    text(ax,15.8,8.3,'Residency plan',8.5,weight='bold')
    text(ax,15.8,6.2,r'$K_{\mathrm{H},\ell}$, $K_{\mathrm{C},\ell}$',8)
    text(ax,15.8,4.3,'Ranked expert IDs',7.5)
    # Dashed initialization bus goes to fast-tier residency, never to the router.
    ax.plot([28.6,33,33],[6.4,6.4,17.1],c=GRAY,lw=.8,ls='--')
    arrow(ax,(33,17.1),(37.7,17.1),GRAY,'--')
    arrow(ax,(33,10.6),(37.7,10.6),GRAY,'--')
    # Request path is separate from the placement bus.
    text(ax,45.8,28.4,'Router (unchanged)',8)
    for xx,e in [(40.6,2),(46.7,6)]:
        box(ax,xx,24.3,4.4,2.5,'#E6EFF6',BLUE,.7)
        text(ax,xx+2.2,25.55,r'$e_'+str(e)+'$',8)
    arrow(ax,(51.5,25.5),(55.3,25.5),GRAY,'--')
    box(ax,55.6,23.3,17,4.4,PALE,INK,.75)
    text(ax,64.1,25.5,'Residency lookup',8)
    arrow(ax,(72.8,25.5),(79.4,25.5),GRAY,'--')
    box(ax,79.7,22.3,17.3,6.4,'#E6EFF6',BLUE,.9)
    text(ax,88.4,26.6,'GPU execution',8.3,weight='bold')
    text(ax,88.4,24.2,'Selected experts',7.4)
    # Physical weight objects and the explicit backing copy.
    tiers=[('HBM',15.2,BLUE,[0,1,3]),
      ('CPU pinned\nmemory',8.7,TEAL,[2,4,5]),
      ('SSD backing\nstore',2.2,GRAY,list(range(8)))]
    for label,y,c,ids in tiers:
        box(ax,38,y,32,4.0,'white',c,.85)
        text(ax,44.7,y+2,label,7.6)
        step,w=(2.13,1.92) if len(ids)>4 else (5.65,4.9)
        for j,e in enumerate(ids):
            xx=52+j*step; box(ax,xx,y+.8,w,2.4,c,'white',.35)
            text(ax,xx+w/2,y+2,r'$e_'+str(e)+'$',7,color='white')
    arrow(ax,(48.4,15.0),(48.4,13.0),BLUE)
    text(ax,43.1,13.9,'Demote',6.8)
    arrow(ax,(62.8,13.0),(62.8,15.0),TEAL)
    text(ax,66.7,13.9,'Promote',6.8)
    box(ax,79.7,8.7,17.3,6.0,PALE,TEAL,.85)
    text(ax,88.4,12.9,'Weight delivery',8,weight='bold')
    text(ax,88.4,10.5,'Read · stage · H2D',7.2)
    arrow(ax,(70.2,10.8),(79.4,10.8),TEAL)
    ax.plot([70.2,75.4,75.4],[4.2,4.2,9.0],c=GRAY,lw=.8)
    arrow(ax,(75.4,9.0),(79.4,9.0),GRAY)
    ax.plot([70.2,75.4,75.4],[17.2,17.2,23],c=BLUE,lw=.8)
    arrow(ax,(75.4,23),(79.4,23),BLUE)
    arrow(ax,(83,14.9),(83,22),TEAL)
    arrow(ax,(92.0,14.9),(92.0,22),GRAY,'--')
    text(ax,96.3,18.5,'Readiness\nevent',7.0)
    text(ax,83,4.8,'All backing weights\nremain on SSD',7.4,color=GRAY)
    text(ax,50,-.55,'Dashed: control / plan metadata     Solid: weight movement',7.3,color=INK)
    save(fig,'figures','fig01_overview')

def retention():
    fig,ax=plt.subplots(figsize=(3.42,1.88))
    fig.subplots_adjust(left=.015,right=.99,bottom=.035,top=.98)
    ax.set(xlim=(0,10),ylim=(0,5.6)); ax.axis('off')
    states=[([0,1],[2,3,4]),([1,2],[3,4,0]),([2,0],[3,4,1])]
    for i,(h,c) in enumerate(states):
        x=.8+i*3.18
        text(ax,x+1.18,5.1,['(a) Initial','(b) Access $e_2$','(c) Access $e_0$'][i],8,weight='bold')
        box(ax,x-.17,1.25,2.8,3.25,PALE,RULE,.5)
        for yy,ids,col in [(3.45,h,BLUE),(1.8,c,TEAL)]:
            for j,e in enumerate(ids):
                xx=x+j*.86; box(ax,xx,yy,.76,.72,col,'white',.65)
                text(ax,xx+.38,yy+.36,r'$e_'+str(e)+'$',8,color='white')
                if (i==1 and e==2) or (i==2 and e==0):
                    box(ax,xx-.035,yy-.035,.83,.79,'none',ORANGE,1.2)
        text(ax,x+1.15,2.99,'HBM',7.5)
        text(ax,x+1.15,1.42,'CPU pinned memory',7.2)
        if i<2: arrow(ax,(x+2.67,2.8),(x+3.0,2.8),GRAY)
    text(ax,5,.76,'Lists: LRU → MRU',7.5,color=GRAY)
    text(ax,5,.22,'CPU hit promotes; HBM victim is demoted',8)
    save(fig,'figures','fig03_retention')

def motivation():
    m=A['motivation']
    fig,axs=plt.subplots(1,3,figsize=(7.05,2.52))
    fig.subplots_adjust(left=.064,right=.992,bottom=.30,top=.80,wspace=.50)
    ax=axs[0]; x=np.arange(4)
    for off,key,c,label in [(-.18,'ssd_misses_uniform',GRAY,'Uniform allocation'),
                            (.18,'ssd_misses_planned',BLUE,'Profile-guided allocation')]:
        bars=ax.bar(x+off,m[key],.32,color=c,edgecolor='white',lw=.35,label=label,zorder=3)
        ax.bar_label(bars,padding=2,fontsize=6.8)
    clean(ax,LABELS['miss']); ax.set_ylim(0,55); ax.set_yticks([0,20,40])
    ax.set_xticks(x,[r'$\ell_1$'+'\n4→2',r'$\ell_2$'+'\n4→3',r'$\ell_3$'+'\n4→5',r'$\ell_4$'+'\n4→6'])
    ax.set_xlabel('Layer; CPU slots: uniform → planned',fontsize=7)
    ax.legend(frameon=False,fontsize=6.8,loc='upper left',borderaxespad=.2)
    ax.set_title('(a) Layer allocation',pad=8)
    ax=axs[1]
    bars=ax.bar(range(3),m['retention_ssd_percent'],color=[GRAY,LIGHT,BLUE],width=.59,zorder=3)
    ax.bar_label(bars,labels=['32%','23%','12%'],padding=3,fontsize=8)
    clean(ax,LABELS['miss']); ax.set_ylim(0,42); ax.set_yticks([0,20,40])
    ax.set_xticks(range(3),['Fixed CPU\npool','Independent\nLRU','MECC\nretention'])
    ax.set_title('(b) Cross-tier retention',pad=8)
    ax=axs[2]
    for key,c,ls,label in [('fixed_windows',GRAY,'--','Profile + static'),
                          ('online_windows',ORANGE,':','Random + adaptive'),
                          ('mecc_windows',BLUE,'-','MECC')]:
        ax.plot(np.arange(16)+1,m[key],c=c,ls=ls,label=label,lw=1.3)
    ax.axvline(8.5,c=INK,lw=.6,ls=':'); text(ax,10.0,38,'Shift',7,ha='left')
    clean(ax,LABELS['miss']); ax.set_ylim(0,60); ax.set_yticks([0,20,40,60])
    ax.set_xlabel('Window index'); ax.set_xticks([1,8,16])
    ax.legend(frameon=False,fontsize=6.8,loc='upper left',borderaxespad=.1,labelspacing=.2)
    ax.set_title('(c) Initialization and adaptation',pad=8)
    save(fig,'ideal_figures','fig02_challenges',True)

def main_performance():
    fig,(ax,h)=plt.subplots(1,2,figsize=(7.05,2.62),gridspec_kw={'width_ratios':[2.45,1]})
    fig.subplots_adjust(left=.063,right=.989,bottom=.23,top=.76,wspace=.53)
    keys=list(A['tpot_seconds'])[:5]
    colors=[GRAY,LIGHT,ORANGE,TEAL,BLUE]; x=np.arange(4)
    for j,(name,c) in enumerate(zip(keys,colors)):
        ax.bar(x+(j-2)*.156,A['tpot_seconds'][name],.145,color=c,
          edgecolor='white',lw=.35,label=name,zorder=3)
    clean(ax,LABELS['tpot']); ax.set_ylim(0,70); ax.set_yticks([0,20,40,60])
    ax.set_xticks(x,['Mixtral-8x7B\nQA','Mixtral-8x7B\nCode','Mixtral-8x22B\nQA','Mixtral-8x22B\nCode'],fontsize=7)
    ax.legend(ncol=3,loc='lower center',bbox_to_anchor=(.5,1.015),frameon=False,
       fontsize=7,columnspacing=.9,handlelength=1.2,handletextpad=.35)
    ax.set_title('(a) Single-GPU latency',y=1.37)
    gains=np.array(A['tpot_seconds']['SSD-native adapter'])/np.array(A['tpot_seconds']['MECC'])
    vals=gains.reshape(2,2)
    h.set_xlim(-.5,1.5); h.set_ylim(1.5,-.5); h.set_aspect('equal')
    for (r,c),v in np.ndenumerate(vals):
        box(h,c-.5,r-.5,1,1,plt.cm.Blues((v-1)/.5),'white',1)
        h.text(c,r,f'{v:.2f}×',ha='center',va='center',fontsize=11,
               color='white' if v>1.34 else INK)
    h.set_xticks([0,1],['QA','Code']); h.set_yticks([0,1],['Mixtral-8x7B','Mixtral-8x22B'],fontsize=7)
    h.tick_params(length=0,pad=4)
    for sp in h.spines.values(): sp.set_visible(False)
    h.set_xticks(np.arange(-.5,2,1),minor=True); h.set_yticks(np.arange(-.5,2,1),minor=True)
    h.grid(which='minor',color='white',lw=2); h.tick_params(which='minor',length=0)
    h.set_title('(b) Speedup over\nSSD-native adapter',pad=10)
    save(fig,'ideal_figures','fig04_performance',True)

def ablation():
    fig,axs=plt.subplots(1,2,figsize=(7.05,1.88))
    fig.subplots_adjust(left=.065,right=.992,bottom=.28,top=.79,wspace=.32)
    names=['Unoptimized\nstreaming','+ Profile-guided\nplacement','+ Cross-tier\nretention','+ Transfer\noverlap']
    for ax,vals,y,title in [(axs[0],A['ablation_tpot_seconds'],LABELS['tpot'],'(a) Cumulative latency'),
                           (axs[1],A['ablation_ssd_percent'],LABELS['miss'],'(b) Cumulative SSD demand')]:
        bars=ax.bar(range(4),vals,color=[GRAY,ORANGE,TEAL,BLUE],width=.57,zorder=3)
        ax.bar_label(bars,padding=3,fontsize=8); clean(ax,y)
        ax.set_ylim(0,max(vals)*1.25); ax.set_xticks(range(4),names,fontsize=7.1)
        ax.set_title(title,pad=8)
    save(fig,'ideal_figures','fig05_ablation',True)

def budget_and_cost():
    fig,axs=plt.subplots(1,3,figsize=(7.05,2.18))
    fig.subplots_adjust(left=.063,right=.99,bottom=.29,top=.81,wspace=.46)
    ax=axs[0]
    for name,c,m in [('Three-tier LRU',GRAY,'s'),('MECC',BLUE,'o')]:
        ax.plot(A['cpu_budget_gb'],A['budget_tpot_seconds'][name],c=c,marker=m,ms=3,label=name)
    clean(ax,LABELS['tpot']); ax.set_ylim(0,32); ax.set_xticks([16,32,48])
    ax.set_xlabel('Task host-memory cap (GB)',fontsize=7.5)
    ax.legend(frameon=False,loc='upper right',fontsize=7)
    ax.set_title('(a) Host-memory sensitivity',pad=8)
    ax=axs[1]
    ax.plot(A['gpus'][1:],A['resident_gpu_tpot_seconds'][1:],c=GRAY,marker='s',ms=3,label='Resident reference')
    ax.scatter([1],[A['mecc_gpu_tpot_seconds'][0]],c=BLUE,s=24,zorder=4,label='MECC (1 GPU)')
    clean(ax,LABELS['tpot']); ax.set_ylim(0,10); ax.set_xticks([1,2,4,8]); ax.set_xlabel('GPU count')
    text(ax,1.25,1.0,'Resident:\nnot feasible',6.8,color=GRAY,ha='left')
    ax.legend(frameon=False,fontsize=7,loc='upper right')
    ax.set_title('(b) GPU allocation',pad=8)
    ax=axs[2]; n=np.arange(65)
    for name,c,ls,label in [('reference',GRAY,'--','SSD-native adapter'),('MECC',BLUE,'-','MECC')]:
        ax.plot(n,A['startup_cost_seconds'][name]+n*A['startup_decode_tpot_seconds'][name],c=c,ls=ls,label=label)
    clean(ax,'Initialization + decode (s)'); ax.set_ylim(0,720); ax.set_xticks([0,32,64])
    ax.set_xlabel('Decode intervals after first token',fontsize=7)
    ax.axvline(9,c=ORANGE,lw=.7,ls=':'); ax.plot(9,102,'o',ms=3,c=ORANGE)
    ax.annotate('9 intervals',xy=(9,102),xytext=(20,210),fontsize=7,
                arrowprops={'arrowstyle':'-','lw':.6,'color':ORANGE},color=ORANGE)
    ax.legend(frameon=False,fontsize=7,loc='upper left')
    ax.set_title('(c) Initialization + decode',pad=8)
    save(fig,'ideal_figures','fig06_budget_cost',True)

def delivery():
    fig,ax=plt.subplots(figsize=(3.42,2.12))
    fig.subplots_adjust(left=.02,right=.99,bottom=.02,top=.97)
    ax.set(xlim=(-1.9,6.6),ylim=(-.7,5.3)); ax.axis('off')
    lanes=[('Router',4.3),('SSD read',3.2),('H2D copy',2.1),('GPU compute',1.0)]
    for name,y in lanes:
        text(ax,-.15,y+.18,name,7.6,ha='right')
        ax.plot([0,6.2],[y,y],c=RULE,lw=.6,zorder=0)
    def task(x,y,w,label,c):
        box(ax,x,y,w,.57,c,'white',.4); text(ax,x+w/2,y+.285,label,7.5,color='white')
    task(0,4.3,.72,'Gate',GRAY)
    task(.88,3.2,1.35,r'$e_2$',GRAY)
    task(2.23,2.1,1.35,r'$e_2$',TEAL)
    task(.88,1.0,2.9,r'$e_0$ (ready in HBM)',BLUE)
    task(3.94,1.0,2.0,r'$e_2$',BLUE)
    arrow(ax,(.72,4.50),(.87,3.60),GRAY)
    arrow(ax,(2.23,3.2),(2.23,2.75),GRAY)
    ax.plot([3.58,3.58],[2.1,.84],c=ORANGE,lw=.8,ls=':')
    arrow(ax,(3.58,.82),(3.93,1.02),ORANGE)
    text(ax,4.65,2.62,'Readiness event',7.5,color=ORANGE)
    text(ax,3.33,4.55,r'Selected IDs: $e_0$, $e_2$',8)
    text(ax,3.1,.10,'Copy may overlap ready-expert computation',7.5)
    text(ax,3.1,-.43,'Dependency order; durations are schematic',7,color=GRAY)
    save(fig,'figures','fig08_delivery')

def hardware_cost():
    fig,axs=plt.subplots(1,3,figsize=(7.05,2.1))
    fig.subplots_adjust(left=.065,right=.99,bottom=.24,top=.8,wspace=.39)
    counts=[1,2,4,8]; lat=[8,2.8,1.65,1]
    for ax,ys,y,title in zip(axs,[counts,lat,list(np.array(counts)*lat)],
        ['GPU count',LABELS['tpot'],'GPU-s/token'],
        ['(a) GPU allocation','(b) TPOT','(c) Nominal GPU-time']):
        bars=ax.bar(range(4),ys,color=[BLUE,GRAY,GRAY,GRAY],width=.58,zorder=3)
        ax.bar_label(bars,fmt='%g',padding=3,fontsize=8); clean(ax,y)
        ax.set_xticks(range(4),['MECC\n1 GPU','Resident\n2 GPUs','Resident\n4 GPUs','Resident\n8 GPUs'],fontsize=7)
        ax.set_ylim(0,max(ys)*1.25); ax.set_title(title,pad=8)
    save(fig,'ideal_figures','fig07_gpu_tradeoff',True)

def main():
    framework(); retention(); delivery(); motivation(); main_performance()
    ablation(); budget_and_cost(); hardware_cost()
    (P/'figure_terms.json').write_text(json.dumps(LABELS,indent=2),encoding='utf-8')
    print('Redrawn: overview, retention, delivery, and five scenario figures.')

if __name__=='__main__': main()
