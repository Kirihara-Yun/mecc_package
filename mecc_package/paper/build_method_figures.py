"""Vector diagrams for the two Method slides. Values shown are illustrative."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from media_hdd import figure_text
from matplotlib.patches import Rectangle, FancyArrowPatch

OUT = Path(__file__).resolve().parent / 'current' / 'method_figures'
OUT.mkdir(parents=True, exist_ok=True)
NAVY='#173D68'; INK='#172B3B'; BLUE='#2768A8'; CPU='#8FB5D4'
SSD='#C9D1D8'; AMBER='#CF7828'; RULE='#CBD5DE'; PALE='#EAF2F8'; WHITE='#FFFFFF'
plt.rcParams.update({'font.family':'sans-serif',
    'font.sans-serif':['Microsoft YaHei','SimHei','Arial'],
    'font.size':12,'pdf.fonttype':42,'svg.fonttype':'none'})

def canvas():
    fig=plt.figure(figsize=(12,3.72),dpi=240,facecolor=WHITE)
    ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,12),ylim=(0,3.72));ax.axis('off')
    return fig,ax
def txt(ax,x,y,value,size=12,color=INK,weight='normal',ha='left'):
    ax.text(x,y,value,fontsize=size,color=color,fontweight=weight,
            ha=ha,va='center',zorder=10)
def ln(ax,x0,y0,x1,y1,color=RULE,lw=.85,ls='-'):
    ax.plot([x0,x1],[y0,y1],color=color,lw=lw,ls=ls,zorder=2)
def rect(ax,x,y,w,h,fill,edge='none',lw=0):
    ax.add_patch(Rectangle((x,y),w,h,facecolor=fill,edgecolor=edge,
                           linewidth=lw,zorder=3))
def arr(ax,a,b,color=BLUE,lw=1.35,scale=11,connection=None):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=scale,
                 linewidth=lw,color=color,connectionstyle=connection,zorder=5))
def section(ax,x0,x1,title,subtitle):
    ln(ax,x0,3.38,x1,3.38,NAVY,1.2)
    txt(ax,x0,3.52,title,15,NAVY,'bold')
    txt(ax,x0,3.15,subtitle,10.5,'#536B7E')
def save(fig,name):
    figure_text(fig)
    for ext in ('png','svg','pdf'):
        fig.savefig(OUT/f'{name}.{ext}',dpi=240,facecolor=WHITE,
                    bbox_inches='tight',pad_inches=.035)
    plt.close(fig)

def placement():
    fig,ax=canvas()
    section(ax,.16,4.24,'(a) 统计各层专家访问次数','同一层中，不同专家的访问次数存在差异')
    section(ax,4.58,5.56,'排序','逐层')
    section(ax,5.89,11.84,'(b) 根据容量确定初始位置',
            '各层分别排序，显存和 CPU 内存共享任务预算')
    rows=[
      ('第 1 层','A',[4,9,6,3,8,2,5,1],['A2','A5','A3','A7','A1','A4','A6','A8'],2,5),
      ('第 2 层','B',[8,3,6,4,2,9,5,1],['B6','B1','B3','B7','B4','B2','B5','B8'],3,5),
      ('第 3 层','C',[2,5,9,3,7,4,1,6],['C3','C5','C8','C2','C6','C4','C1','C7'],1,5)]
    for (layer,prefix,counts,ranked,kh,kc),y in zip(rows,[2.55,1.72,.89]):
        txt(ax,.18,y+.11,layer,11.6,NAVY,'bold')
        for j,value in enumerate(counts):
            x=1.13+j*.375
            rect(ax,x,y-.17,.265,.56,'#EFF3F6')
            rect(ax,x,y-.17,.265,.56*value/10,BLUE if value>=8 else CPU)
            txt(ax,x+.133,y-.31,f'{prefix}{j+1}',8.9,INK,ha='center')
        ln(ax,.14,y-.47,4.21,y-.47,RULE,.65)
        arr(ax,(4.32,y+.04),(5.64,y+.04),BLUE,1.2,10)
        txt(ax,5.93,y+.10,layer,11.6,NAVY,'bold')
        for j,expert in enumerate(ranked):
            x=6.87+j*.555;fill=BLUE if j<kh else CPU if j<kc else SSD
            rect(ax,x,y-.17,.48,.48,fill)
            txt(ax,x+.24,y+.07,expert,10.2,WHITE if j<kh else INK,'bold','center')
        for a,b,c in [(0,kh,BLUE),(kh,kc,CPU),(kc,8,SSD)]:
            if b>a:ln(ax,6.87+a*.555,y-.27,6.87+(b-1)*.555+.48,y-.27,c,2.8)
        ln(ax,5.86,y-.47,11.84,y-.47,RULE,.65)
    ln(ax,4.39,.34,4.39,3.29,RULE,.8)
    ln(ax,5.72,.34,5.72,3.29,RULE,.8)
    txt(ax,.18,.22,'示意：柱高表示访问次数，专家编号按层区分。',10.6,'#536B7E')
    for x,c,label in [(7.00,BLUE,'GPU 显存'),(8.57,CPU,'CPU 内存'),(10.17,SSD,'SSD')]:
        rect(ax,x,.14,.20,.16,c);txt(ax,x+.29,.22,label,10.7,NAVY)
    save(fig,'method1_placement')

def delivery():
    fig,ax=canvas()
    section(ax,.16,5.54,'(a) 一次 CPU 内存访问如何更新缓存',
            '访问 E3 后，E3 进入显存；被替换的 E2 保留在 CPU 内存')
    section(ax,6.10,11.84,'(b) 所选专家何时可以计算',
            '已在显存的 E1 先计算；E6 的权重到达后再执行')
    tiers=[('GPU 显存',1.25,BLUE),('CPU 内存',2.94,CPU),('SSD',4.42,SSD)]
    for name,x,color in tiers:
        ln(ax,x,2.65,x+1.36,2.65,color,2.8)
        txt(ax,x+.68,2.80,name,11.7,NAVY,'bold','center')
    states=[
        ('访问前',2.02,[('E1','E2'),('E3','E4'),('E5','E6')]),
        ('访问后',.91,[('E1','E3'),('E2','E4'),('E5','E6')])]
    for phase,y,groups in states:
        txt(ax,.18,y+.21,phase,11.7,NAVY,'bold')
        for j,(_,x,_) in enumerate(tiers):
            for k,name in enumerate(groups[j]):
                px=x+.12+k*.58;active=name in ('E2','E3')
                rect(ax,px,y,.48,.42,'#FFF5EA' if active else PALE,
                     AMBER if active else '#B7C8D5',1.05 if active else .6)
                txt(ax,px+.24,y+.21,name,10.8,NAVY,'bold','center')
        ln(ax,.16,y-.18,5.77,y-.18,RULE,.65)
    arr(ax,(3.34,1.91),(2.11,1.39),AMBER,1.9,13,'arc3,rad=.12')
    arr(ax,(2.15,1.91),(3.34,1.39),BLUE,1.9,13,'arc3,rad=-.12')
    txt(ax,.22,.34,'E2 保留在 CPU 内存，后续访问无需再次读取 SSD。',10.6,'#536B7E')
    ln(ax,5.92,.27,5.92,3.38,RULE,.85)
    left,right=7.39,11.60
    for name,y in [('SSD 读取',2.58),('传至显存',1.91),('GPU 计算',1.24)]:
        txt(ax,6.12,y+.16,name,11.6,NAVY,'bold')
        ln(ax,left,y,right,y,'#DCE4EA',.9)
    for x,v in [(left,'t0'),(9.01,'t1'),(10.13,'t2'),(right,'时间')]:
        txt(ax,x,.49,v,10.3,'#536B7E',ha='center')
    ln(ax,left,.74,right,.74,RULE,.9)
    rect(ax,7.56,2.57,1.45,.34,SSD);txt(ax,8.28,2.74,'读取 E6',10.8,INK,'bold','center')
    rect(ax,9.01,1.90,1.12,.34,CPU);txt(ax,9.57,2.07,'传输 E6',10.8,INK,'bold','center')
    rect(ax,7.56,1.23,2.20,.34,BLUE);txt(ax,8.66,1.40,'计算 E1',10.8,WHITE,'bold','center')
    rect(ax,10.13,1.23,1.28,.34,BLUE);txt(ax,10.77,1.40,'计算 E6',10.8,WHITE,'bold','center')
    ln(ax,10.13,.76,10.13,2.36,AMBER,1.35,'--')
    txt(ax,10.19,2.43,'权重就绪',10.5,AMBER,'bold')
    arr(ax,(9.01,2.57),(9.01,2.26),'#849BAE',.8,8)
    arr(ax,(10.13,1.90),(10.13,1.59),'#849BAE',.8,8)
    txt(ax,6.13,.22,'同一请求中，权重读取与已有专家的计算可以重叠。',10.6,'#536B7E')
    save(fig,'method2_delivery')

if __name__=='__main__':
    placement();delivery();print(OUT)
