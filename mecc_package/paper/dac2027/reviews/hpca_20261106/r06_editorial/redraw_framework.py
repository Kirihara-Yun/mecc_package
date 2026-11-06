from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, FancyBboxPatch
P=Path(__file__).resolve().parent
INK='#20242B'; BLUE='#245B8A'; TEAL='#39867F'; ORANGE='#BA7941'
GRAY='#899199'; LIGHT='#D3D8DD'; RULE='#DCE1E5'; PALE='#F4F6F8'
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],
 'mathtext.fontset':'stix','font.size':8,'text.color':INK,'pdf.fonttype':42,'svg.fonttype':'none'})
def text(ax,x,y,s,size=8,**kw):
    s=s.replace('SSD','HDD')
    ax.text(x,y,s,fontsize=size,ha=kw.pop('ha','center'),
            va=kw.pop('va','center'),color=kw.pop('color',INK),**kw)

def arrow(ax,a,b,color=INK,style='-',lw=.8,rad=0):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=7,
      lw=lw,color=color,linestyle=style,connectionstyle=f'arc3,rad={rad}'))

def box(ax,x,y,w,h,fc='white',ec=RULE,lw=.7):
    ax.add_patch(Rectangle((x,y),w,h,facecolor=fc,edgecolor=ec,lw=lw))

def save(fig,folder,name):
    dest=P/folder;dest.mkdir(exist_ok=True)
    for ext in ('pdf','png'):
        fig.savefig(dest/f'{name}.{ext}',dpi=260,bbox_inches='tight',pad_inches=.025)
    plt.close(fig)


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
    text(ax,23,22.4,'Layer skew',7.5)
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
      ('CPU resident\nmemory',8.7,TEAL,[2,4,5]),
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
    text(ax,96.3,18.5,'Copy/use\nordering',7.0)
    text(ax,83,4.8,'All backing weights\nremain on SSD',7.4,color=GRAY)
    text(ax,50,-.55,'Dashed: control / plan metadata     Solid: weight movement',7.3,color=INK)
    save(fig,'figures','fig01_overview')

if __name__=='__main__':framework()
