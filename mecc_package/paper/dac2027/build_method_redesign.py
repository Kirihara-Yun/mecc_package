"""Native vector method diagrams: ranked cuts, residency states, delivery lanes."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import numpy as np

HERE=Path(__file__).resolve().parent
OUT=HERE/'method_redesign';OUT.mkdir(exist_ok=True)
INK='#203244';BLUE='#326C9B';TEAL='#6D9FAD';PALE='#E9EDF0';ORANGE='#C78D51'
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],
 'font.size':7.5,'pdf.fonttype':42,'svg.fonttype':'none','axes.linewidth':.5})

def save(fig,name):
    for ext in ('pdf','png'):
        fig.savefig(OUT/f'{name}.{ext}',dpi=300,bbox_inches='tight',pad_inches=.025)
    plt.close(fig)

def canvas(h):
    fig,ax=plt.subplots(figsize=(3.45,h))
    fig.subplots_adjust(0,0,1,1);ax.set(xlim=(0,10),ylim=(0,5));ax.axis('off')
    return fig,ax

def box(ax,x,y,w,h,color,label='',size=7.5):
    ax.add_patch(Rectangle((x,y),w,h,fc=color,ec='white',lw=.8))
    if label:ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=size,
                    color='white' if color in (BLUE,TEAL) else INK)

def compile_frontiers():
    fig,ax=canvas(1.62)
    ax.text(.2,4.65,'Ranked profile',weight='bold',color=INK)
    ax.text(5.25,4.65,'Emitted placement',weight='bold',color=INK)
    vals=[[.37,.24,.16,.11,.07,.05],[.51,.21,.12,.08,.05,.03],[.23,.20,.18,.16,.13,.10]]
    ids=[[2,4,5,1,3,6],[3,1,5,2,4,6],[6,4,2,5,1,3]]
    kh=[2,3,1]
    for row,(v,order,k) in enumerate(zip(vals,ids,kh)):
        y=3.35-row*1.02;letter='ABC'[row]
        ax.text(.15,y+.26,letter,va='center',weight='bold')
        for j,value in enumerate(v):
            col=plt.cm.Blues(.18+value*1.3)
            box(ax,.52+j*.59,y,.56,.58,col)
            ax.text(.8+j*.59,y+.29,str(order[j]),ha='center',va='center',fontsize=7,color=INK)
        ax.add_patch(Circle((.8+k*.59,y+.29),.27,fill=False,ec=ORANGE,lw=1.3))
        ax.text(5.02,y+.29,letter,va='center',weight='bold')
        for j,num in enumerate(order):
            box(ax,5.4+j*.67,y,.63,.58,BLUE if j<k else TEAL if j<4 else PALE,str(num))
        ax.plot([5.38+k*.67]*2,[y-.07,y+.68],c=BLUE,lw=.9)
    ax.annotate('',xy=(4.98,2.62),xytext=(4.15,2.62),arrowprops={'arrowstyle':'->','color':INK,'lw':.8})
    ax.text(2.2,.47,'Next rank: largest marginal demand',ha='center',fontsize=6.7,color=INK)
    for x,col,label in [(5.1,BLUE,'HBM'),(6.6,TEAL,'CPU'),(8.1,PALE,'HDD')]:
        box(ax,x,.3,.25,.25,col);ax.text(x+.33,.425,label,va='center',fontsize=6.8)
    save(fig,'compile_frontiers')

def residency_cases():
    fig,ax=canvas(1.56)
    ax.text(.15,4.65,'Initial: HBM [a₁, a₂]   CPU [a₃, a₄]',color=INK,weight='bold')
    ax.text(3.36,4.05,'HBM',ha='center',color=BLUE,weight='bold')
    ax.text(6.5,4.05,'CPU',ha='center',color=TEAL,weight='bold')
    for y,req,h,c,out in [(2.95,'a₂',['a₂','a₁'],['a₃','a₄'],''),
                           (1.85,'a₃',['a₃','a₁'],['a₂','a₄'],''),
                           (.75,'a₅',['a₅','a₁'],['a₂','a₃'],'a₄')]:
        ax.text(.2,y+.31,'Request '+req,va='center',fontsize=7.5)
        ax.annotate('',xy=(2.3,y+.31),xytext=(1.95,y+.31),arrowprops={'arrowstyle':'->','lw':.8,'color':INK})
        for j,e in enumerate(h):box(ax,2.45+j*.94,y,.9,.63,BLUE,e,8.5)
        for j,e in enumerate(c):box(ax,5.6+j*.94,y,.9,.63,TEAL,e,8.5)
        if out:
            box(ax,8.35,y,.83,.63,PALE,out,8.5)
            ax.text(8.76,y-.25,'Evict',ha='center',fontsize=6.4)
    ax.plot([4.9,4.9],[.5,3.85],c='#B9C4CC',lw=.7,ls='--')
    ax.text(3.35,.1,'MRU → LRU',ha='center',fontsize=6.5,color=INK)
    ax.text(6.5,.1,'MRU → LRU',ha='center',fontsize=6.5,color=INK)
    save(fig,'residency_cases')

def delivery_overlap():
    fig,ax=canvas(1.73)
    ax.text(.15,4.67,'Gate selects resident a₁ and cold a₅',weight='bold',color=INK)
    start=1.85;scale=7.7
    ax.text(.15,3.8,'Serial',weight='bold',color=INK)
    ax.text(.15,2.65,'Overlap',weight='bold',color=INK)
    for y in (3.35,1.7):
        ax.plot([start,9.5],[y,y],c='#D4DDE2',lw=.6,zorder=0)
    segments=[(3.25,.0,.36,TEAL,'Read a₅'),(3.25,.36,.15,ORANGE,'H2D'),
              (3.25,.51,.14,BLUE,'a₁'),(3.25,.65,.14,BLUE,'a₅'),
              (1.95,.0,.36,TEAL,'Read a₅'),(1.95,.36,.15,ORANGE,'H2D'),
              (.97,.0,.14,BLUE,'a₁'),(.97,.51,.14,BLUE,'a₅')]
    for y,x,w,col,label in segments:box(ax,start+x*scale,y,w*scale,.49,col,label,6.7)
    ready=start+.51*scale
    ax.plot([ready,ready],[.8,2.65],c=INK,lw=.65,ls='--')
    ax.text(ready+.08,2.57,'Ready',va='bottom',fontsize=6.5,color=INK)
    ax.text(1.6,2.18,'I/O',ha='right',va='center',fontsize=6.5)
    ax.text(1.6,1.21,'GPU',ha='right',va='center',fontsize=6.5)
    ax.annotate('',xy=(start+.79*scale,.35),xytext=(start+.65*scale,.35),
                arrowprops={'arrowstyle':'<->','lw':.7,'color':INK})
    ax.text(start+.72*scale,.02,'Saved wait',ha='center',fontsize=6.5,color=INK)
    ax.annotate('',xy=(9.6,3.0),xytext=(start,3.0),arrowprops={'arrowstyle':'->','lw':.6,'color':INK})
    ax.text(9.65,3.0,'t',va='center',fontsize=7)
    save(fig,'delivery_overlap')

if __name__=='__main__':
    compile_frontiers();residency_cases();delivery_overlap()
    print('Three vector method diagrams written.')
