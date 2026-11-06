"""Paper-size English adaptations of the talk concepts, plus method diagrams.

The rank cut, stack ribbons, and route/residency matrix follow
../build_insight_visuals.py. All states and durations are schematic.
"""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, PathPatch
from matplotlib.path import Path as MPath
import numpy as np

OUT=Path(__file__).resolve().parent/'measured_figures'
OUT.mkdir(exist_ok=True)
INK='#203244'; BLUE='#326C9B'; TEAL='#6D9FAD'; GRAY='#ABB5BD'
PALE='#EAF0F4'; ORANGE='#C78D51'; RULE='#D9E0E5'
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],
 'mathtext.fontset':'stix','font.size':8,'pdf.fonttype':42,'svg.fonttype':'none'})

def txt(ax,x,y,s,size=8,ha='center',color=INK,**kw):
    ax.text(x,y,s,fontsize=size,ha=ha,va='center',color=color,**kw)
def rect(ax,x,y,w,h,fc=PALE,ec=RULE,lw=.6):
    ax.add_patch(Rectangle((x,y),w,h,fc=fc,ec=ec,lw=lw,zorder=3))
def arr(ax,a,b,color=INK,rad=0,lw=.8):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=6,
        lw=lw,color=color,connectionstyle=f'arc3,rad={rad}',zorder=5))
def axis(ax):
    ax.set(xlim=(0,1),ylim=(0,1)); ax.axis('off')
def save(fig,name):
    for ext in ('pdf','svg','png'):
        path=OUT/f'{name}.{ext}'
        fig.savefig(path,dpi=280,bbox_inches='tight',pad_inches=.025)
        if ext=='svg':
            path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
    plt.close(fig)

def introduction():
    fig,ax=plt.subplots(figsize=(3.45,1.13));fig.subplots_adjust(0,0,1,1);axis(ax)
    txt(ax,.5,.94,'One MoE layer: two selected experts',8.5,weight='bold')
    xs=np.linspace(.04,.88,8)
    for j,x in enumerate(xs):
        active=j in (1,5)
        rect(ax,x,.28,.085,.29,BLUE if active else PALE,BLUE if active else GRAY)
        txt(ax,x+.0425,.425,f'$e_{j+1}$',8,color='white' if active else INK)
    for lo,hi,label in [(0,2,'HBM'),(2,5,'CPU'),(5,8,'HDD')]:
        x=xs[lo]; end=xs[hi-1]+.085
        ax.plot([x,end],[.20,.20],color=GRAY,lw=1)
        txt(ax,(x+end)/2,.10,label,8)
    arr(ax,(xs[5]+.04,.60),(xs[0]+.04,.60),ORANGE,rad=.32)
    txt(ax,.38,.75,'HDD read + host-to-device copy',7.6,color=ORANGE)
    save(fig,'intro_compact')

def ribbon(ax,x0,x1,y0,y1,color,width=.020,alpha=.7):
    m=(y0+y1)/2; h=width/2
    v=[(x0-h,y0),(x0-h,m),(x1-h,m),(x1-h,y1),
       (x1+h,y1),(x1+h,m),(x0+h,m),(x0+h,y0),(x0-h,y0)]
    c=[MPath.MOVETO,MPath.CURVE4,MPath.CURVE4,MPath.CURVE4,
       MPath.LINETO,MPath.CURVE4,MPath.CURVE4,MPath.CURVE4,MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(v,c),fc=color,ec='none',alpha=alpha,zorder=2))

def insights(stem='insights_en', letters='abc'):
    fig,axs=plt.subplots(1,3,figsize=(7.1,1.65))
    fig.subplots_adjust(left=.01,right=.99,bottom=.04,top=.94,wspace=.22)
    for ax in axs: axis(ax)
    a,b,c=axs
    txt(a,0,1.04,f'({letters[0]}) Rank, then divide capacity',8.3,ha='left',weight='bold')
    xs=np.linspace(.07,.94,8); ps=np.array([.77,.64,.53,.44,.35,.28,.22,.17])
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
    txt(b,0,1.04,f'({letters[1]}) Promote and retain the victim',8.3,ha='left',weight='bold')
    xs=np.linspace(.08,.93,5); before=[1,2,3,4,5]; after=[3,1,2,4,5]
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
    txt(c,0,1.04,f'({letters[2]}) Correct the initial profile online',8.3,ha='left',weight='bold')
    for block,ybase,label in [(0,.53,'Route'),(1,.08,'Cache')]:
        txt(c,0,ybase+.15,label,7.2,ha='left')
        for r,e in enumerate([1,2,6,7]):
            yy=ybase+.27-r*.085
            txt(c,.20,yy+.026,str(e),6.2)
            for j in range(6):
                on=(r<2 if j<2 else r>=2)
                if block: on=(r<2 if j<3 else r in (1,2) if j==3 else r>=2)
                rect(c,.25+j*.12,yy,.096,.056,BLUE if on else PALE,'none',0)
    c.vlines(.475,.04,.90,color=ORANGE,lw=.7,ls='--')
    txt(c,.475,.94,'Task switch',7,color=ORANGE)
    txt(c,.60,-.07,r'Time $\longrightarrow$',7)
    save(fig,stem)

def compiler():
    fig,ax=plt.subplots(figsize=(3.45,1.65));fig.subplots_adjust(.01,.02,.99,.98);axis(ax)
    txt(ax,.23,.96,'Profile counts',8.3,weight='bold')
    txt(ax,.73,.96,'Ranked initial placement',8.3,weight='bold')
    specs=[('A',[3,8,2,6,4,1],[2,4,5,1,3,6],2,4),
           ('B',[7,3,8,2,5,1],[3,1,5,2,4,6],3,4),
           ('C',[2,4,1,7,3,8],[6,4,2,5,1,3],1,4)]
    for (prefix,counts,order,kh,cut),yy in zip(specs,[.68,.42,.16]):
        txt(ax,.02,yy+.07,prefix,8,ha='left',weight='bold')
        for j,h in enumerate(counts):
            rect(ax,.075+j*.052,yy,.033,.17*h/8,TEAL,'none',0)
        arr(ax,(.405,yy+.08),(.47,yy+.08),BLUE)
        for j,e in enumerate(order):
            fill=BLUE if j<kh else TEAL if j<cut else GRAY
            rect(ax,.49+j*.077,yy-.01,.065,.17,fill,'white',.4)
            txt(ax,.522+j*.077,yy+.075,f'{prefix}{e}',6.6,color='white' if j<kh else INK)
    for x,label,col in [(.17,'HBM',BLUE),(.44,'CPU',TEAL),(.71,'HDD',GRAY)]:
        rect(ax,x,-.01,.033,.04,col,'none',0);txt(ax,x+.047,.01,label,7,ha='left')
    save(fig,'method_compile')

def runtime():
    fig,ax=plt.subplots(figsize=(3.45,1.16));fig.subplots_adjust(.01,.02,.99,.98);axis(ax)
    txt(ax,.03,.91,'Request $e_3$',8.5,ha='left',weight='bold')
    for y,label,ids in [(.55,'Before',[1,2,3,4]),(.14,'After',[3,1,2,4])]:
        txt(ax,.03,y+.09,label,7.5,ha='left')
        for j,e in enumerate(ids):
            col=BLUE if j<2 else TEAL
            rect(ax,.25+j*.17,y,.14,.19,'#FFF1DF' if e==3 else PALE,
                 ORANGE if e==3 else col,.8)
            txt(ax,.32+j*.17,y+.095,f'$e_{e}$',8)
    ax.vlines(.565,.08,.84,color=GRAY,lw=.7,ls='--')
    txt(ax,.40,.83,'HBM',7.2,color=BLUE);txt(ax,.74,.83,'CPU',7.2,color=TEAL)
    arr(ax,(.66,.54),(.32,.35),ORANGE,rad=.1)
    arr(ax,(.49,.54),(.66,.35),BLUE,rad=-.1)
    txt(ax,.43,-.01,r'MRU $\longrightarrow$ LRU',7)
    save(fig,'method_runtime')

def delivery():
    fig,ax=plt.subplots(figsize=(3.45,1.45));fig.subplots_adjust(.01,.04,.99,.98);axis(ax)
    for yy,label in [(.70,'HDD'),(.44,'H2D'),(.18,'GPU')]:
        txt(ax,.02,yy+.07,label,7.8,ha='left')
        ax.hlines(yy,.18,.98,color=RULE,lw=.55)
    rect(ax,.22,.70,.31,.13,GRAY,GRAY);txt(ax,.375,.765,'Read $e_3$',7)
    rect(ax,.54,.44,.20,.13,TEAL,TEAL);txt(ax,.64,.505,'Copy $e_3$',7)
    rect(ax,.22,.18,.30,.13,BLUE,BLUE);txt(ax,.37,.245,'Resident $e_1$',7,color='white')
    rect(ax,.76,.18,.20,.13,BLUE,BLUE);txt(ax,.86,.245,'Run $e_3$',7,color='white')
    arr(ax,(.53,.70),(.54,.59),GRAY)
    ax.vlines(.745,.15,.61,color=ORANGE,lw=.85,ls='--')
    txt(ax,.745,.65,'Ready',7,color=ORANGE)
    arr(ax,(.745,.43),(.76,.33),ORANGE)
    arr(ax,(.18,.065),(.98,.065),INK);txt(ax,.58,-.015,'Time (schematic)',7)
    save(fig,'method_delivery')

if __name__=='__main__':
    introduction();insights();compiler();runtime();delivery()
