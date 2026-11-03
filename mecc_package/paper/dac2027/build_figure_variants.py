"""Three genuinely different visual encodings for each of eight paper figures.

All numerical inputs are frozen hypothetical targets. Schematics are not timing
measurements. Outputs are isolated from the active paper and beginner guide.
"""
from pathlib import Path
from contextlib import contextmanager
import base64
import hashlib
import html
import json
import re
import zipfile
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mc
from matplotlib.patches import Rectangle, FancyArrowPatch
import pymupdf
import build_paper_figures as base

P=Path(__file__).resolve().parent
OUT=P/'figure_variants'
DATA=P/'ideal_assumptions.json'
D=json.loads(DATA.read_text(encoding='utf-8'))
HASH=hashlib.sha256(DATA.read_bytes()).hexdigest()
INK='#20242b'; BLUE='#245b8a'; TEAL='#39867f'; ORANGE='#be733d'
GRAY='#899199'; LIGHT='#d3d8dd'; PALE='#f2f5f8'; RULE='#dce1e5'
TPOT='TPOT (s/token)'; MISS='SSD demand-miss share (%)'
SPEC=[
 ('01_challenges','图 1 · 三项动机','Deployment challenges',base.motivation),
 ('02_framework','图 2 · 系统框架','MECC framework',base.framework),
 ('03_retention','图 3 · 缓存升降级','Cross-tier retention',base.retention),
 ('04_delivery','图 4 · 传输与计算依赖','Delivery dependencies',base.delivery),
 ('05_performance','图 5 · 主性能比较','Single-GPU performance',base.main_performance),
 ('06_ablation','图 6 · 累积消融','Cumulative ablation',base.ablation),
 ('07_resources','图 7 · 资源与开销','Resources and initialization',base.budget_and_cost),
 ('08_allocation','附图 · GPU 资源权衡','GPU allocation tradeoff',base.hardware_cost),
]
NOTES={
 '01_challenges':[
  '黑白分组柱与折线，保留目前论文的三个并列面板。',
  '配对点、水平排序与折线，强调同一对象在两种策略下的变化。',
  '分配矩阵与窗口热图，直接看槽位、未命中及热点变化。'],
 '02_framework':[
  '黑白架构板，离线与在线分区，适合保守的论文排版。',
  '分层框架：上方计划、中间执行、下方存储，按职责阅读。',
  '以三级存储为中心，左右分别放编译与执行，强调数据去向。'],
 '03_retention':[
  '三个横向快照，按先后顺序对照专家位置。',
  '状态表式布局，按行阅读请求与两个缓存的内容。',
  '合并 LRU 栈视图，固定容量边界，突出专家移动。'],
 '04_delivery':[
  '黑白分轨时序，强调读盘、复制与计算的先后依赖。',
  '串行与可重叠调度并列，保持专家计算顺序，仅示意独立工作。',
  '依赖图，明确分叉、复制完成和两条依赖的汇合，不表达时间长度。'],
 '05_performance':[
  '保守分组柱状图与加速比矩阵，方便直接放入正文。',
  '四个小面板分别展开模型/任务，所有 TPOT 使用同一横轴范围。',
  '水平点图把五种策略放在同一行，突出 MECC 与接近基线的距离。'],
 '06_ablation':[
  '黑白双柱状图，分别展示 TPOT 和 SSD 需求比例。',
  '同一阶段对齐两列点图，方便关联时间与未命中变化。',
  '累积瀑布图，保留起点、每步变化和终点；不作独立收益归因。'],
 '07_resources':[
  '三个保守折线面板，依次查看主存、GPU 数量和受限开销。',
  '四面板分析：保留三项原比较，另列名义 GPU 时间以避免挑参照。',
  '主存热图、资源表和成本差值曲线，强调数值与交点。'],
 '08_allocation':[
  '黑白三组柱状图，完整列出单卡与 2/4/8 卡参考。',
  '指标矩阵，按行比较 GPU 数、TPOT 与名义 GPU 时间；颜色仅在行内比较。',
  '延迟—GPU 数散点配 GPU 时间条形图，直观看资源取舍。'],
}
MANIFEST=[]

def txt(ax,x,y,s,fs=8,**kw):
    ax.text(x,y,s,fontsize=fs,ha=kw.pop('ha','center'),va=kw.pop('va','center'),
            color=kw.pop('color',INK),**kw)

def rect(ax,x,y,w,h,fc='white',ec=RULE,lw=.7):
    ax.add_patch(Rectangle((x,y),w,h,facecolor=fc,edgecolor=ec,lw=lw))

def arr(ax,a,b,c=INK,ls='-',rad=0):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=7,lw=.85,
      color=c,linestyle=ls,connectionstyle=f'arc3,rad={rad}'))

def clean(ax,y=None):
    base.clean(ax,y)

def canvas(w=7.05,h=2.65):
    f,a=plt.subplots(figsize=(w,h)); f.subplots_adjust(left=.015,right=.985,bottom=.03,top=.95)
    a.set(xlim=(0,100),ylim=(0,35)); a.axis('off')
    return f,a

def chips(ax,x,y,ids,c=BLUE,step=4.4,w=3.8,h=2.8,highlight=None):
    for j,e in enumerate(ids):
        xx=x+j*step; rect(ax,xx,y,w,h,c,'white',.45)
        txt(ax,xx+w/2,y+h/2,f'$e_{e}$',7.6,color='white')
        if e==highlight: rect(ax,xx-.12,y-.12,w+.24,h+.24,'none',ORANGE,1.1)

def emit(fig,key,variant,hypo=False):
    dest=OUT/key; dest.mkdir(parents=True,exist_ok=True)
    if hypo:
        fig.text(.992,.992,'HYPOTHETICAL · NOT MEASURED',fontsize=6,
          ha='right',va='top',color='#704000',
          bbox={'facecolor':'#fff299','edgecolor':'none','pad':1.2})
    for ext in ['pdf','svg','png']:
        fig.savefig(dest/f'{variant}.{ext}',dpi=230,bbox_inches='tight',pad_inches=.035)
    plt.close(fig)
    MANIFEST.append({'figure':key,'variant':variant,'hypothetical':hypo,
       'pdf':f'{key}/{variant}.pdf','svg':f'{key}/{variant}.svg','png':f'{key}/{variant}.png'})

@contextmanager
def monochrome(key):
    names=['INK','BLUE','TEAL','ORANGE','GRAY','LIGHT','RULE','PALE','save','box','text','arrow']
    old={n:getattr(base,n) for n in names}
    def gray(c):
        if c=='none': return c
        r,g,b,a=mc.to_rgba(c); v=.2126*r+.7152*g+.0722*b
        return (v,v,v,a)
    def mb(ax,x,y,w,h,fc='white',ec=RULE,lw=.7): old['box'](ax,x,y,w,h,gray(fc),gray(ec),lw)
    def mt(ax,x,y,s,size=8,**kw):
        if 'color' in kw:
            rgba=gray(kw['color'])
            if rgba!='none' and rgba[0]<.99:
                rgba=(min(rgba[0],.38),)*3+(rgba[3],)
            kw['color']=rgba
        old['text'](ax,x,y,s,size,**kw)
    def ma(ax,a,b,color=INK,style='-',lw=.8,rad=0):
        old['arrow'](ax,a,b,color=gray(color),style=style,lw=lw,rad=rad)
    def ms(fig,folder,name,hypothetical=False): emit(fig,key,'A',hypothetical)
    try:
        base.INK='#202020';base.BLUE='#252525';base.TEAL='#686868';base.ORANGE='#999999'
        base.GRAY='#b2b2b2';base.LIGHT='#dedede';base.RULE='#dddddd';base.PALE='#f5f5f5'
        base.box=mb;base.text=mt;base.arrow=ma;base.save=ms
        yield
    finally:
        for n,v in old.items(): setattr(base,n,v)

def challenge_b():
    f,aa=plt.subplots(1,3,figsize=(7.05,2.6));f.subplots_adjust(left=.06,right=.99,bottom=.27,top=.80,wspace=.54)
    m=D['motivation'];a=aa[0];ys=np.arange(4)
    for y,u,v in zip(ys,m['ssd_misses_uniform'],m['ssd_misses_planned']):
        a.plot([u,v],[y,y],c=RULE,lw=3,zorder=1)
    a.scatter(m['ssd_misses_uniform'],ys,c=GRAY,s=22,label='Uniform allocation',zorder=3)
    a.scatter(m['ssd_misses_planned'],ys,c=BLUE,s=25,marker='D',label='Profile-guided allocation',zorder=3)
    a.set_yticks(ys,[r'$\ell_1$: 4→2',r'$\ell_2$: 4→3',r'$\ell_3$: 4→5',r'$\ell_4$: 4→6'])
    a.invert_yaxis();a.set_xlim(0,55);a.set_xlabel(MISS,fontsize=7);clean(a)
    a.legend(frameon=False,fontsize=6.5,loc='lower left');a.set_ylim(4.7,-.6);a.set_title('(a) Allocation at equal total slots')
    a=aa[1];v=m['retention_ssd_percent'];a.barh(range(3),v,color=[GRAY,LIGHT,BLUE],height=.5)
    a.set_yticks(range(3),['Fixed CPU\npool','Independent\nLRU','MECC\nretention']);a.invert_yaxis()
    a.set_xlim(0,40);a.set_xlabel(MISS,fontsize=7);clean(a);a.set_title('(b) Retention rule')
    for i,x in enumerate(v): a.text(x+1,i,f'{x}%',va='center',fontsize=8)
    a=aa[2]
    for k,c,ls,lab in [('fixed_windows',GRAY,'--','Profile + static'),('online_windows',ORANGE,':','Random + adaptive'),('mecc_windows',BLUE,'-','MECC')]:
        a.plot(range(1,17),m[k],c=c,ls=ls,marker='o' if k=='mecc_windows' else None,ms=2.6,label=lab)
    a.axvspan(8.5,16.5,color=PALE,zorder=0);a.axvline(8.5,c=INK,lw=.6,ls=':')
    a.set_ylim(0,60);a.set_xticks([1,8,16]);a.set_xlabel('Window index');clean(a,MISS)
    a.legend(frameon=False,fontsize=6.3,loc='upper left');a.set_title('(c) Startup and shift')
    emit(f,'01_challenges','B',True)

def matrix(ax,data,rows,cols,cmap='Blues',fmt='g',vmin=None,vmax=None,fs=8):
    d=np.asarray(data,float);lo=np.min(d) if vmin is None else vmin;hi=np.max(d) if vmax is None else vmax
    norm=mc.Normalize(lo,hi if hi>lo else lo+1)
    for (r,c),v in np.ndenumerate(d):
        color=plt.get_cmap(cmap)(.12+.80*norm(v))
        rect(ax,c-.5,r-.5,1,1,color,'white',1)
        luminance=.2126*color[0]+.7152*color[1]+.0722*color[2]
        ax.text(c,r,format(v,fmt),ha='center',va='center',fontsize=fs,color='white' if luminance<.51 else INK)
    ax.set(xlim=(-.5,d.shape[1]-.5),ylim=(d.shape[0]-.5,-.5))
    ax.set_xticks(range(len(cols)),cols);ax.set_yticks(range(len(rows)),rows)
    ax.tick_params(length=0,pad=4)
    for sp in ax.spines.values():sp.set_visible(False)

def challenge_c():
    f,aa=plt.subplots(1,3,figsize=(7.05,2.45),gridspec_kw={'width_ratios':[1,1,1.15]})
    f.subplots_adjust(left=.095,right=.99,bottom=.27,top=.78,wspace=.58)
    m=D['motivation'];a=aa[0]
    matrix(a,[m['ssd_misses_uniform'],m['ssd_misses_planned']],['Uniform','Planned'],[r'$\ell_1$',r'$\ell_2$',r'$\ell_3$',r'$\ell_4$'],vmin=0,vmax=50,fs=8)
    a.set_xlabel('Equal total CPU slots: 16',fontsize=7.3);a.set_title('(a) SSD demand-miss share (%)')
    a=aa[1];v=m['retention_ssd_percent'];a.hlines(range(3),0,v,color=[GRAY,GRAY,BLUE],lw=2)
    a.scatter(v,range(3),s=45,c=[GRAY,GRAY,BLUE],zorder=3)
    a.set_yticks(range(3),['Fixed CPU\npool','Independent\nLRU','MECC\nretention']);a.invert_yaxis();a.set_xlim(0,40)
    for i,x in enumerate(v):a.text(x+2,i,str(x),va='center',fontsize=8)
    a.set_xlabel(MISS,fontsize=7);clean(a);a.set_title('(b) Cross-tier retention')
    a=aa[2];data=[m[k] for k in ['fixed_windows','online_windows','mecc_windows']]
    matrix(a,data,['Profile\n+ static','Random\n+ adaptive','MECC'],['']*16,vmin=0,vmax=60,fs=0)
    # A small-multiple heat strip uses all original windows, not new traces.
    for t in list(a.texts):t.remove()
    a.set_xticks([0,7,15],['1','8','16']);a.axvline(7.5,c=INK,ls=':',lw=.9)
    a.set_xlabel('Window index; shift after 8',fontsize=7);a.set_title('(c) SSD demand (dark = more)')
    cmap=mc.LinearSegmentedColormap.from_list('miss_scale',plt.cm.Blues(np.linspace(.12,.92,256)))
    cax=a.inset_axes([1.04,0,.045,1])
    bar=f.colorbar(plt.cm.ScalarMappable(norm=mc.Normalize(0,60),cmap=cmap),cax=cax,ticks=[0,30,60])
    bar.solids.set_rasterized(False)
    bar.ax.tick_params(labelsize=6.5,length=2);bar.set_label('%',fontsize=7,labelpad=1)
    emit(f,'01_challenges','C',True)

def framework_b():
    f,a=canvas(h=3.05)
    rect(a,.7,23,98,10,PALE,RULE);txt(a,5,31,'OFFLINE',7.8,ha='left',weight='bold')
    txt(a,15,27.2,'Independent profile\nModel · memory caps · costs',8)
    arr(a,(29,27),(35,27),GRAY,'--');rect(a,35.5,24.4,25,5.4,'white',BLUE)
    txt(a,48,27.1,'Placement compiler',8.7,weight='bold')
    arr(a,(61,27),(67,27),GRAY,'--');rect(a,67.5,24.4,28,5.4,'white',BLUE)
    txt(a,81.5,27.1,'Residency plan\nLayer quotas + ranked IDs',8)
    txt(a,5,21,'ONLINE',7.8,ha='left',weight='bold')
    rect(a,3,14.6,20,4.5,'#e6eff6',BLUE);txt(a,13,17.7,'GPU execution',8.2)
    txt(a,13,15.7,'Wait on readiness event',6.8)
    rect(a,30.5,14.6,27,4.5,PALE,INK)
    txt(a,44,16.8,'Residency lookup\nWeight delivery: read · H2D',7.8)
    arr(a,(30.1,18),(23.4,18),GRAY,'--');arr(a,(30.1,15.6),(23.4,15.6),TEAL)
    arr(a,(65.1,16.8),(58,16.8),GRAY,'--');rect(a,65.5,14.6,30,4.5,'white',INK)
    txt(a,80.5,16.8,'Router (unchanged)',8.2)
    a.plot([81.5,81.5,44],[24.2,21,21],c=GRAY,ls='--',lw=.8);arr(a,(44,21),(44,19.3),GRAY,'--')
    for x,name,ids,c in [(3,'HBM',[0,1,3],BLUE),(37,'CPU pinned memory',[2,4,5],TEAL),(71,'SSD backing store',list(range(8)),GRAY)]:
        rect(a,x,3.1,25,7.2,'white',c);txt(a,x+12.5,8.7,name,8,weight='bold')
        chips(a,x+1.3,4.2,ids,c,step=2.9 if len(ids)>4 else 6.4,w=2.5 if len(ids)>4 else 5.7,h=2.5)
    arr(a,(16,10.5),(16,14.3),BLUE);arr(a,(49.5,10.5),(49.5,14.3),TEAL)
    a.plot([83.5,83.5,54],[10.5,12.1,12.1],c=GRAY,lw=.8)
    arr(a,(54,12.1),(54,14.3),GRAY)
    arr(a,(36.5,6),(28.5,6),TEAL);txt(a,32.5,7.4,'Promote',6.8)
    arr(a,(28.5,3.8),(36.5,3.8),BLUE);txt(a,32.5,2.3,'Demote',6.8)
    txt(a,50,.55,'Dashed: control / plan     Solid: weight movement     SSD retains all backing weights',7.4)
    emit(f,'02_framework','B')

def framework_c():
    f,a=canvas(h=2.95)
    txt(a,17,33,'Compile a prior',9,weight='bold');txt(a,50,33,'Retain the working set',9,weight='bold');txt(a,84,33,'Deliver selected weights',9,weight='bold')
    rect(a,1,7,30,22.5,PALE,RULE);txt(a,16,27.2,'Independent route profile',8)
    for r in range(3):
        for j,v in enumerate([.95,.7,.45,.28,.14,.05]):rect(a,5+j*3.8,21-r*1.7,3.15,1.3,plt.cm.Blues(v),'white',.3)
    txt(a,16,16.3,'Model + task caps + costs',7.5);arr(a,(16,14.7),(16,12.7),GRAY,'--')
    rect(a,4,8.8,24,3.6,'white',BLUE);txt(a,16,10.6,'Placement compiler',8.3,weight='bold')
    for y,label,ids,c in [(24.2,'HBM',[0,1,3],BLUE),(15.2,'CPU pinned memory',[2,4,5],TEAL),(6.2,'SSD backing store',list(range(8)),GRAY)]:
        rect(a,36,y,28,6,'white',c);txt(a,50,y+4.6,label,8,weight='bold')
        chips(a,37.4,y+1,ids,c,step=3.15 if len(ids)>4 else 7.1,w=2.8 if len(ids)>4 else 6.4,h=2.5)
    arr(a,(42,21.5),(42,24),TEAL);arr(a,(58,24),(58,21.5),BLUE)
    txt(a,37.9,22.7,'↑',8);txt(a,61,22.7,'↓',8)
    rect(a,71,24.2,27,6,'#e6eff6',BLUE);txt(a,84.5,28.5,'GPU execution',8.6,weight='bold');txt(a,84.5,26,'Selected experts',7.5)
    rect(a,71,14.2,27,6,PALE,TEAL);txt(a,84.5,18.4,'Weight delivery',8.5,weight='bold');txt(a,84.5,16,'Read · stage · H2D',7.5)
    arr(a,(64.4,27),(70.5,27),BLUE);arr(a,(64.4,17),(70.5,17),TEAL)
    a.plot([64.4,67.8,67.8],[9.2,9.2,15.2],c=GRAY,lw=.8);arr(a,(67.8,15.2),(70.5,15.2),GRAY)
    arr(a,(80,20.4),(80,23.9),TEAL);arr(a,(90,20.4),(90,23.9),GRAY,'--');txt(a,96,22.3,'Ready\nevent',6.8)
    txt(a,84.5,10.1,'Router (unchanged)',8);txt(a,84.5,7.5,'Selected expert IDs',7.5)
    a.plot([98.2,99.2,99.2],[9,9,25],c=GRAY,ls='--',lw=.75);arr(a,(99.2,25),(98.2,25),GRAY,'--')
    a.plot([28.4,33,33],[10.6,10.6,27],c=GRAY,ls='--',lw=.75);arr(a,(33,27),(35.5,27),GRAY,'--');arr(a,(33,18),(35.5,18),GRAY,'--')
    txt(a,50,2.1,'Plan: layer quotas + ranked IDs; capacities fixed during a run',7.6)
    txt(a,50,.2,'Solid: weight movement     Dashed: control / plan     SSD stores all experts',7.1)
    emit(f,'02_framework','C')

STATES=[([0,1],[2,3,4]),([1,2],[3,4,0]),([2,0],[3,4,1])]

def retention_b():
    f,a=canvas(w=5.0,h=2.62)
    txt(a,12,32,'Request',8,weight='bold');txt(a,40,32,'HBM',8.5,weight='bold');txt(a,77,32,'CPU pinned memory',8.5,weight='bold')
    for i,(h,c) in enumerate(STATES):
        y=24-i*8;rect(a,1,y-1,98,6,PALE if i%2==0 else 'white','none')
        txt(a,12,y+2,['Initial','Access $e_2$','Access $e_0$'][i],8)
        chips(a,28,y+.3,h,BLUE,step=9,w=8,h=3.5,highlight=None if i==0 else [2,0][i-1])
        chips(a,61,y+.3,c,TEAL,step=10,w=8.6,h=3.5)
    txt(a,50,2.8,'LRU → MRU within each tier',8)
    txt(a,50,.5,'CPU hit promotes; HBM victim is demoted',7.8)
    emit(f,'03_retention','B')

def retention_c():
    f,a=canvas(w=4.85,h=2.85)
    for j,(h,c) in enumerate(STATES):
        x=15+j*31;seq=list(reversed(h))+list(reversed(c))
        txt(a,x+7,32,['Initial','Access $e_2$','Access $e_0$'][j],8.2,weight='bold')
        for i,e in enumerate(seq):
            y=25-i*4.5;col=BLUE if i<2 else TEAL
            rect(a,x,y,14,3.6,col,'white',.6);txt(a,x+7,y+1.8,f'$e_{e}$',8.5,color='white')
            if (j==1 and e==2) or (j==2 and e==0):rect(a,x-.2,y-.2,14.4,4,'none',ORANGE,1.2)
        a.plot([x-2,x+16],[20.1,20.1],c=INK,ls='--',lw=.7)
    txt(a,5,30.3,'MRU',7);txt(a,5,5.5,'LRU',7)
    txt(a,5,22,'HBM',7,rotation=90);txt(a,5,14.3,'CPU pinned memory',7,rotation=90)
    txt(a,50,3,'Combined stack; boundary fixed at 2 HBM + 3 CPU slots',7.8)
    txt(a,50,.6,'Serial example, no prefetch or physical mirrors',7.4,color=GRAY)
    emit(f,'03_retention','C')

def delivery_b():
    f,a=canvas(h=2.65)
    def task(x,y,w,s,c):rect(a,x,y,w,3.0,c,'white',.4);txt(a,x+w/2,y+1.5,s,8,color='white')
    txt(a,50,33,'Same gate selects $e_0$ and $e_2$; expert execution order is unchanged',8.3)
    for top,label in [(25,'Serial schedule'),(10,'Overlap opportunity')]:
        txt(a,2,top+3,label,8.3,ha='left',weight='bold')
        txt(a,12,top-1,'I/O',7.5);txt(a,12,top-6,'GPU',7.5)
        a.plot([19,97],[top-2,top-2],c=RULE,lw=.6);a.plot([19,97],[top-7,top-7],c=RULE,lw=.6)
    task(20,17.9,25,'$e_0$',BLUE);task(46,22.9,15,'SSD $e_2$',GRAY);task(61,22.9,15,'H2D $e_2$',TEAL);task(77,17.9,19,'$e_2$',BLUE)
    task(20,7.9,15,'SSD $e_2$',GRAY);task(35,7.9,15,'H2D $e_2$',TEAL)
    task(20,2.9,32,'$e_0$ (HBM ready)',BLUE);task(54,2.9,19,'$e_2$',BLUE)
    a.plot([50,50],[7.9,2.3],c=ORANGE,ls=':',lw=.8);txt(a,62,11.2,'Readiness event',7.5,color=ORANGE)
    txt(a,50,.5,'Schematic order only; bar lengths are not measured times',7.5,color=GRAY)
    emit(f,'04_delivery','B')

def delivery_c():
    f,a=canvas(h=2.35)
    nodes=[(2,14,13,6,'Gate',GRAY),(26,24,21,6,'Compute $e_0$',BLUE),
      (23,4,18,6,'SSD read $e_2$',GRAY),(48,4,18,6,'H2D $e_2$',TEAL),
      (73,4,22,6,'Ready event',ORANGE),(73,24,22,6,'Compute $e_2$',BLUE)]
    for x,y,w,h,s,c in nodes:rect(a,x,y,w,h,c,'white',.5);txt(a,x+w/2,y+h/2,s,8,color='white')
    arr(a,(15,19),(25.5,26),GRAY);arr(a,(15,15),(22.5,8),GRAY)
    arr(a,(41.5,7),(47.5,7),GRAY);arr(a,(66.5,7),(72.5,7),GRAY)
    arr(a,(47.5,27),(72.5,27),BLUE);txt(a,59,30.4,'Preserve kernel order',7.3)
    arr(a,(84,10.4),(84,23.6),ORANGE);txt(a,72,17.4,'Weight readiness',7.5,ha='right',color=ORANGE)
    txt(a,50,33,'Two dependencies must hold before computing $e_2$',8.4,weight='bold')
    txt(a,50,.7,'Dependency graph, not a timeline; selected IDs and weights are unchanged',7.5,color=GRAY)
    emit(f,'04_delivery','C')

POLICIES=list(D['tpot_seconds'])[:5]
COLORS=[GRAY,LIGHT,ORANGE,TEAL,BLUE]
GROUPS=['Mixtral-8x7B / QA','Mixtral-8x7B / Code','Mixtral-8x22B / QA','Mixtral-8x22B / Code']

def performance_b():
    f,aa=plt.subplots(2,2,figsize=(7.05,3.9),sharex=True)
    f.subplots_adjust(left=.21,right=.985,bottom=.12,top=.88,wspace=.60,hspace=.48)
    for i,a in enumerate(aa.flat):
        v=[D['tpot_seconds'][k][i] for k in POLICIES]
        bars=a.barh(range(5),v,color=COLORS,height=.59,zorder=3)
        a.set_yticks(range(5),POLICIES,fontsize=7);a.invert_yaxis();a.set_xlim(0,72)
        for j,x in enumerate(v):a.text(x+1,j,f'{x:g}',fontsize=7,va='center')
        clean(a);a.set_title(GROUPS[i],fontsize=8.2,pad=6)
        if i>=2:a.set_xlabel(TPOT)
    emit(f,'05_performance','B',True)

def performance_c():
    f,a=plt.subplots(figsize=(7.05,2.82));f.subplots_adjust(left=.22,right=.80,bottom=.23,top=.79)
    markers=['s','D','^','v','o'];ys=np.arange(4)
    for k,c,m in zip(POLICIES,COLORS,markers):
        a.scatter(D['tpot_seconds'][k],ys,c=c,marker=m,s=26 if k=='MECC' else 21,label=k,zorder=4 if k=='MECC' else 3)
    a.set_yticks(ys,GROUPS,fontsize=7.5);a.set_ylim(3.65,-.45);a.set_xlim(0,70);a.set_xlabel(TPOT);clean(a)
    a.legend(ncol=3,frameon=False,loc='lower center',bbox_to_anchor=(.44,1.06),fontsize=7,handletextpad=.3,columnspacing=.9)
    for i,v in enumerate(D['tpot_seconds']['MECC']):
        a.text(v,i+.14,f'{v:g}',color=BLUE,fontsize=7.5,ha='center',va='top')
        g=D['tpot_seconds']['SSD-native adapter'][i]/v
        a.text(1.04,i,f'{g:.2f}×',transform=a.get_yaxis_transform(),ha='left',va='center',fontsize=9,color=BLUE)
    a.text(1.04,1.02,'Speedup vs.\nSSD-native adapter',transform=a.transAxes,fontsize=7,ha='left',va='bottom')
    emit(f,'05_performance','C',True)

STAGES=['Unoptimized streaming','+ Profile-guided placement','+ Cross-tier retention','+ Transfer overlap']

def ablation_b():
    f,aa=plt.subplots(1,2,figsize=(7.05,2.45),sharey=True)
    f.subplots_adjust(left=.25,right=.98,bottom=.24,top=.80,wspace=.34)
    for a,v,label in zip(aa,[D['ablation_tpot_seconds'],D['ablation_ssd_percent']],[TPOT,MISS]):
        for i,x in enumerate(v):a.hlines(i,0,x,color=RULE,lw=2)
        a.scatter(v,range(4),c=[GRAY,ORANGE,TEAL,BLUE],s=35,zorder=3)
        for i,x in enumerate(v):a.text(x+max(v)*.035,i,f'{x:g}',va='center',fontsize=8)
        a.set_xlim(0,max(v)*1.22);a.set_xlabel(label);a.set_yticks(range(4),STAGES,fontsize=7.5);clean(a)
    aa[0].invert_yaxis();aa[0].set_title('(a) Cumulative latency');aa[1].set_title('(b) Cumulative SSD demand')
    emit(f,'06_ablation','B',True)

def ablation_c():
    f,aa=plt.subplots(1,2,figsize=(7.05,2.38));f.subplots_adjust(left=.07,right=.99,bottom=.28,top=.80,wspace=.32)
    for a,v,y,title in zip(aa,[D['ablation_tpot_seconds'],D['ablation_ssd_percent']],
        [TPOT,MISS],['(a) Cumulative TPOT changes','(b) Cumulative miss-share changes']):
        a.bar(0,v[0],.55,color=GRAY,zorder=3)
        for i in range(1,4):
            a.plot([i-1+.28,i-.28],[v[i-1],v[i-1]],c=GRAY,lw=.7)
            delta=v[i]-v[i-1]
            a.bar(i,abs(delta),.55,bottom=min(v[i],v[i-1]),color=[ORANGE,TEAL,BLUE][i-1],zorder=3)
            if delta==0:a.plot([i-.28,i+.28],[v[i],v[i]],c=BLUE,lw=2)
            a.text(i,max(v[i],v[i-1])+max(v)*.045,f'{delta:+g}',ha='center',fontsize=8)
        a.bar(4,v[-1],.55,color=BLUE,zorder=3)
        a.text(0,v[0]+max(v)*.045,str(v[0]),ha='center',fontsize=8)
        a.text(4,v[-1]+max(v)*.045,str(v[-1]),ha='center',fontsize=8)
        a.set_xticks(range(5),['Streaming','Placement','Retention','Overlap','MECC'],fontsize=7)
        a.set_ylim(0,max(v)*1.27);clean(a,y);a.set_title(title)
    emit(f,'06_ablation','C',True)

def resources_b():
    f,aa=plt.subplots(2,2,figsize=(7.05,3.45));f.subplots_adjust(left=.08,right=.98,bottom=.13,top=.89,wspace=.31,hspace=.55)
    a=aa[0,0]
    for k,c,m in [('Three-tier LRU',GRAY,'s'),('MECC',BLUE,'o')]:a.plot(D['cpu_budget_gb'],D['budget_tpot_seconds'][k],c=c,marker=m,ms=3,label=k)
    clean(a,TPOT);a.set_ylim(0,32);a.set_xlabel('Task host-memory cap (GB)');a.legend(frameon=False,fontsize=7);a.set_title('(a) Host-memory sensitivity')
    a=aa[0,1];a.plot([2,4,8],D['resident_gpu_tpot_seconds'][1:],c=GRAY,marker='s',ms=4,label='Resident reference')
    a.scatter([1],[8],c=BLUE,s=30,label='MECC (1 GPU)');clean(a,TPOT);a.set_xticks([1,2,4,8]);a.set_ylim(0,10);a.set_xlabel('GPU count');a.legend(frameon=False,fontsize=7);a.set_title('(b) Allocation and latency')
    a=aa[1,0];n=np.arange(65)
    for k,c,ls,lab in [('reference',GRAY,'--','SSD-native adapter'),('MECC',BLUE,'-','MECC')]:a.plot(n,D['startup_cost_seconds'][k]+n*D['startup_decode_tpot_seconds'][k],c=c,ls=ls,label=lab)
    clean(a,'Initialization + decode (s)');a.set_xlabel('Decode intervals after first token',fontsize=7);a.axvline(9,c=ORANGE,ls=':',lw=.7);a.legend(frameon=False,fontsize=7);a.set_title('(c) Restricted cost illustration')
    a=aa[1,1];v=np.array([1,2,4,8])*np.array([8,2.8,1.65,1])
    bars=a.bar(range(4),v,color=[BLUE,GRAY,GRAY,GRAY],width=.54);a.bar_label(bars,fmt='%g',padding=2,fontsize=8)
    clean(a,'GPU-s/token');a.set_ylim(0,10);a.set_xticks(range(4),['MECC\n1 GPU','Resident\n2 GPUs','Resident\n4 GPUs','Resident\n8 GPUs'],fontsize=7);a.set_title('(d) Nominal GPU-time')
    emit(f,'07_resources','B',True)

def resources_c():
    f,aa=plt.subplots(1,3,figsize=(7.05,2.65),gridspec_kw={'width_ratios':[1.15,1.05,1]})
    f.subplots_adjust(left=.08,right=.99,bottom=.26,top=.78,wspace=.58)
    a=aa[0];matrix(a,[D['budget_tpot_seconds'][k] for k in ['Three-tier LRU','MECC']],['Three-tier\nLRU','MECC'],[str(x) for x in D['cpu_budget_gb']],vmin=0,vmax=32,fs=7.5)
    a.set_xlabel('Task host-memory cap (GB)',fontsize=7);a.set_title('(a) TPOT (s/token)')
    a=aa[1];matrix(a,[[1,2,4,8],[8,2.8,1.65,1]],['GPU count','TPOT (s/token)'],['MECC','R2','R4','R8'],cmap='Greys',vmin=0,vmax=8,fs=8)
    a.set_xlabel('R = resident reference',fontsize=7);a.set_title('(b) Allocation / latency')
    a=aa[2];n=np.arange(65)
    diff=(D['startup_cost_seconds']['MECC']-D['startup_cost_seconds']['reference'])+n*(D['startup_decode_tpot_seconds']['MECC']-D['startup_decode_tpot_seconds']['reference'])
    a.plot(n,diff,c=BLUE);a.axhline(0,c=GRAY,lw=.8);a.axvline(9,c=ORANGE,lw=.8,ls=':');a.scatter([9],[0],c=ORANGE,s=20,zorder=4)
    a.fill_between(n,0,diff,where=diff<=0,color=BLUE,alpha=.10)
    a.set_xlabel('Decode intervals',fontsize=7);clean(a,'Δ initialization + decode (s)');a.set_title('(c) MECC − SSD-native adapter',fontsize=7.8)
    a.text(.98,.94,'30 + 8m − (12 + 10m)',transform=a.transAxes,fontsize=6.7,ha='right',va='top')
    emit(f,'07_resources','C',True)

def allocation_b():
    f,a=plt.subplots(figsize=(7.05,2.5));f.subplots_adjust(left=.24,right=.98,bottom=.22,top=.83)
    data=np.array([[1,2,4,8],[8,2.8,1.65,1],[8,5.6,6.6,8]])
    for r,row in enumerate(data):
        norm=mc.Normalize(row.min(),row.max())
        for c,v in enumerate(row):
            col=plt.cm.Blues(.14+.69*norm(v));rect(a,c-.5,r-.5,1,1,col,'white',1)
            txt(a,c,r,f'{v:g}',11,color='white' if norm(v)>.65 else INK)
    a.set(xlim=(-.5,3.5),ylim=(2.5,-.5));a.set_xticks(range(4),['MECC\n1 GPU','Resident\n2 GPUs','Resident\n4 GPUs','Resident\n8 GPUs'])
    a.set_yticks(range(3),['GPU count','TPOT (s/token)','GPU-s/token']);a.tick_params(length=0,pad=7)
    for sp in a.spines.values():sp.set_visible(False)
    f.text(.6,.045,'Shading is normalized within each row; quantities have different units.',fontsize=7,ha='center',color=GRAY)
    emit(f,'08_allocation','B',True)

def allocation_c():
    f,(a,b)=plt.subplots(1,2,figsize=(7.05,2.7),gridspec_kw={'width_ratios':[1.35,1]})
    f.subplots_adjust(left=.08,right=.98,bottom=.22,top=.79,wspace=.42)
    count=np.array([1,2,4,8]);lat=np.array([8,2.8,1.65,1]);cost=count*lat
    a.plot(count[1:],lat[1:],c=GRAY,lw=.8,ls='--')
    a.scatter(count,lat,c=[BLUE,GRAY,GRAY,GRAY],s=cost*17,edgecolor='white',lw=.5,zorder=3)
    for i,(x,y) in enumerate(zip(count,lat)):a.annotate(['MECC','Resident 2','Resident 4','Resident 8'][i],(x,y),xytext=(6,7),textcoords='offset points',fontsize=7.5)
    clean(a,TPOT);a.set_xlabel('GPU count');a.set_xticks([1,2,4,8]);a.set_xlim(0,10);a.set_ylim(0,10)
    a.set_title('(a) Latency–allocation tradeoff')
    bars=b.barh(range(4),cost,color=[BLUE,GRAY,GRAY,GRAY],height=.56);b.invert_yaxis()
    b.set_yticks(range(4),['MECC 1','Resident 2','Resident 4','Resident 8']);b.set_xlim(0,10);b.bar_label(bars,fmt='%g',padding=3,fontsize=8)
    b.set_xlabel('GPU-s/token');clean(b);b.set_title('(b) Nominal GPU-time')
    f.text(.31,.035,'Point area scales with nominal GPU-s/token; no energy or price claim.',fontsize=7,ha='center',color=GRAY)
    emit(f,'08_allocation','C',True)

def main():
    OUT.mkdir(exist_ok=True)
    for key,cn,en,fn in SPEC:
        with monochrome(key):fn()
    for fn in [challenge_b,challenge_c,framework_b,framework_c,retention_b,retention_c,
               delivery_b,delivery_c,performance_b,performance_c,ablation_b,ablation_c,
               resources_b,resources_c,allocation_b,allocation_c]:fn()
    assert len(MANIFEST)==24
    assert hashlib.sha256(DATA.read_bytes()).hexdigest()==HASH
    m={'status':'STYLE ALTERNATIVES; ALL NUMERICAL OUTCOMES REMAIN HYPOTHETICAL',
       'source_file':'ideal_assumptions.json','source_sha256':HASH,
       'does_not_replace_active_manuscript':True,'figure_count':8,'variants_per_figure':3,
       'entries':MANIFEST,'notes':NOTES}
    (OUT/'manifest.json').write_text(json.dumps(m,indent=2,ensure_ascii=False),encoding='utf-8')
    print('Generated 24 isolated figure variants as PDF, SVG and PNG.')

if __name__=='__main__':main()
