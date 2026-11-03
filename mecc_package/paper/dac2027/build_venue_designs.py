"""Three reference-led design systems; no change to manuscript or target data.

HPCA: architecture plate, slot arrays, numbered datapath, hatched comparison.
ASPLOS: compiler/runtime regions, plan artifacts, aligned execution lanes.
OSDI: request-centric service composition, state tables, direct annotations.
These are authored interpretations of named papers, not venue templates.
"""
from pathlib import Path
import json, hashlib, base64, html, zipfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, FancyArrowPatch, Circle, Ellipse
import pymupdf

P=Path(__file__).resolve().parent
OUT=P/'venue_designs'
SOURCE=P/'ideal_assumptions.json'
D=json.loads(SOURCE.read_text(encoding='utf-8'))
HASH=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
INK='#222222'
STYLES=['HPCA','ASPLOS','OSDI']
SPEC=[('01_challenges','三项实验动机'),('02_framework','系统框架'),
 ('03_retention','跨层联合留存'),('04_delivery','传输与执行依赖'),
 ('05_performance','主性能比较'),('06_ablation','累积消融'),
 ('07_resources','资源与初始化开销'),('08_allocation','GPU 资源权衡')]
CFG={
 'HPCA':dict(main='#526b8c',alt='#a1a9b3',pale='#edf0f4',accent='#d5b967',round=False),
 'ASPLOS':dict(main='#526eaa',alt='#6f9d93',pale='#f0f3fa',accent='#d4a95d',round=True),
 'OSDI':dict(main='#246652',alt='#929292',pale='#f4f5f4',accent='#383838',round=False)}
NOTES={
 'HPCA':'硬件架构板：容量边界、专家槽位与编号数据通路；实验图用紧凑分组、纹理和面板编号。',
 'ASPLOS':'软硬件协同视图：编译期产物贯穿运行时，语义区域与执行轨道对应；实验图采用对齐分面。',
 'OSDI':'请求驱动的系统视图：请求路径、缓存服务与后备存储分离；实验图用直接标注和简洁开放坐标。'}
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],
 'mathtext.fontset':'stix','font.size':9,'axes.labelsize':9,'axes.titlesize':10,
 'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,
 'pdf.fonttype':42,'ps.fonttype':42,'axes.linewidth':.65})
ENTRIES=[]

def text(a,x,y,s,size=9,**kw):
 return a.text(x,y,s,fontsize=size,ha=kw.pop('ha','center'),va=kw.pop('va','center'),color=kw.pop('color',INK),**kw)

def box(a,x,y,w,h,label='',fc='white',ec=INK,style='HPCA',size=9,lw=.8):
 if CFG[style]['round']:
  patch=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.1,rounding_size=0.7',fc=fc,ec=ec,lw=lw)
 else:patch=Rectangle((x,y),w,h,fc=fc,ec=ec,lw=lw)
 a.add_patch(patch)
 if label:text(a,x+w/2,y+h/2,label,size)
 return patch

def arrow(a,p,q,s='HPCA',dash=False,lw=1,rad=0,color=None):
 a.add_patch(FancyArrowPatch(p,q,arrowstyle='-|>',mutation_scale=9,
  lw=lw,color=color or INK,linestyle='--' if dash else '-',connectionstyle=f'arc3,rad={rad}'))

def number(a,x,y,n,s):
 a.add_patch(Circle((x,y),1.15,fc=CFG[s]['main'] if s!='OSDI' else INK,ec='none'))
 text(a,x,y,str(n),7.5,color='white',weight='bold')

def cells(a,x,y,ids,s,w=3.8,h=3,gap=.65,highlight=None):
 for j,e in enumerate(ids):
  color=CFG[s]['main'] if e!=highlight else CFG[s]['accent']
  box(a,x+j*(w+gap),y,w,h,f'$e_{e}$',color,'white',s,8,lw=.5)
  a.texts[-1].set_color('white' if e!=highlight or s=='OSDI' else INK)

def canvas(h=3.9):
 f,a=plt.subplots(figsize=(8.5,h));f.subplots_adjust(left=.01,right=.99,bottom=.04,top=.95)
 a.set(xlim=(0,100),ylim=(0,48));a.axis('off');return f,a

def emit(f,key,s,hypo=False):
 dest=OUT/key;dest.mkdir(parents=True,exist_ok=True)
 if hypo:f.text(.99,.995,'HYPOTHETICAL · NOT MEASURED',ha='right',va='top',fontsize=7,color='#734c00',bbox=dict(fc='#fff1b0',ec='none',pad=2))
 elif key=='04_delivery':f.text(.99,.995,'SCHEMATIC · NOT TO SCALE',ha='right',va='top',fontsize=7,color='#555555')
 for ext in ['pdf','svg','png']:f.savefig(dest/f'{s}.{ext}',dpi=220,bbox_inches='tight',pad_inches=.07)
 plt.close(f)
 ENTRIES.append(dict(figure=key,design=s,hypothetical=hypo))

def mini_profile(a,x,y,s):
 for r in range(3):
  for c,v in enumerate([.9,.7,.4,.2,.1,.04]):
   box(a,x+c*1.7,y-r*1.7,1.5,1.4,fc=plt.cm.Greys(.1+v*.65) if s=='HPCA' else plt.cm.Blues(.1+v*.65),ec='white',style=s,lw=.2)

def framework(s):
 f,a=canvas(4.1);c=CFG[s]
 if s=='HPCA':
  # Architecture plate: control on top, concrete residency arrays below.
  box(a,1,3,98,41,ec=c['main'],lw=1.1)
  text(a,3,46,'MECC: control and memory datapath',11,ha='left',weight='bold')
  text(a,82,46,'Unchanged router',9,weight='bold');arrow(a,(82,44),(82,41),dash=True)
  box(a,3,31,27,11,fc=c['pale'],ec=c['main']);text(a,16.5,39,'Placement compiler',10,weight='bold')
  text(a,16.5,34.5,'Profile · model · caps · costs',8)
  box(a,36,32,24,9,'Residency plan\nLayer quotas + ranked IDs',style=s,size=9)
  arrow(a,(30,36),(36,36),dash=True);arrow(a,(60,36),(67,36),dash=True)
  box(a,67,32,29,9,'Residency lookup\nJoint dynamic LRU',fc=c['pale'],ec=c['main'])
  number(a,64,39,1,s)
  a.plot([3,97],[28,28],c=c['main'],lw=.65)
  for y,label,ids in [(20,'HBM',[0,1,3]),(12,'CPU pinned memory',[2,4,5]),(4,'SSD backing store',list(range(8)))]:
   box(a,5,y,44,6,ec=c['main']);text(a,7,y+3,'SSD' if len(ids)>3 else label,8,ha='left')
   cells(a,27 if len(ids)<8 else 18,y+1.3,ids,s,w=2.9,h=3.2,gap=.65)
  arrow(a,(51,7),(57,7));arrow(a,(57,7),(57,14));arrow(a,(49,15),(57,15))
  box(a,61,11,15,8,'Weight\ndelivery',fc=c['pale'],ec=c['main'])
  arrow(a,(57,15),(61,15));number(a,58,19,2,s)
  arrow(a,(76,15),(82,15));box(a,82,11,13,8,'GPU\nexecution',ec=c['main'])
  arrow(a,(49,23),(88,23));arrow(a,(88,23),(88,19));text(a,72,25,'Ready HBM weights',8)
  arrow(a,(68,19),(68,23));arrow(a,(68,23),(49,23));text(a,60,25,'H2D',7.5)
  arrow(a,(81,32),(81,29),dash=True);arrow(a,(81,29),(73,29),dash=True);arrow(a,(73,29),(73,19),dash=True);text(a,89,29,'Selected IDs',8)
  text(a,51,1,'Dashed: metadata / readiness   •   Solid: weights   •   Router selections unchanged',8)
 elif s=='ASPLOS':
  # Compiler-to-runtime composition; a plan artifact bridges domains.
  box(a,1,9,28,35,fc=c['pale'],ec='#b9c7df',style=s)
  text(a,15,41,'OFFLINE COMPILATION',10,weight='bold',color=c['main'])
  mini_profile(a,4,35,s);text(a,20,33,'Model + task caps\nDelivery costs',8)
  arrow(a,(15,29),(15,26),dash=True)
  box(a,4,19,22,7,'Placement compiler',ec=c['main'],style=s,size=10)
  arrow(a,(15,19),(15,16),dash=True)
  box(a,4,10,22,6,'Plan: quotas + IDs',fc='#fff4d7',ec=c['accent'],style=s)
  box(a,35,9,64,35,fc='#f8faf9',ec='#b8cfc7',style=s)
  text(a,67,41,'ONLINE EXECUTION',10,weight='bold',color=c['alt'])
  box(a,39,29,16,7,'Unchanged\nrouter',ec=c['alt'],style=s)
  box(a,61,29,31,7,'Residency lookup + joint LRU',ec=c['alt'],style=s)
  arrow(a,(55,32.5),(61,32.5));arrow(a,(26,13),(37,13),dash=True);arrow(a,(37,13),(37,26),dash=True);arrow(a,(37,26),(68,26),dash=True);arrow(a,(68,26),(68,29),dash=True)
  text(a,31,17,'Initialize',7.5,rotation=90)
  for x,label,ids in [(40,'HBM',[0,1,3]),(59,'CPU pinned',[2,4,5]),(78,'SSD backing',list(range(8)))]:
   box(a,x,12,17,10,fc='white',ec=c['alt'],style=s);text(a,x+8.5,24,label,8.5)
   if len(ids)<8:cells(a,x+1.5,15,ids,s,w=4,h=3,gap=.6)
   else:
    cells(a,x+1,17,ids[:4],s,w=3,h=2.5,gap=.6);cells(a,x+1,13,ids[4:],s,w=3,h=2.5,gap=.6)
  arrow(a,(76.5,29),(76.5,24),dash=True)
  box(a,35,0,64,6,fc='#f0f2f7',ec='#b9c7df',style=s)
  text(a,38,3,'Delivery:',8,ha='left');text(a,57,3,'read → H2D → ready',8.5)
  arrow(a,(72,3),(78,3));text(a,88,3,'GPU execution',9,weight='bold')
  arrow(a,(86.5,12),(86.5,6));arrow(a,(67.5,12),(67.5,6));arrow(a,(48.5,12),(48.5,6))
  text(a,9,37.8,'Route profile',8)
  text(a,15,4,'HBM hit bypasses read / H2D',8)
 else:
  # Request path in foreground; persistent service and backing store below.
  text(a,1,46,'Request path',11,ha='left',weight='bold')
  for x,w,label,n in [(2,18,'Unchanged router',1),(29,26,'Residency lookup',2),(66,31,'GPU execution',4)]:
   box(a,x,33,w,8,label,ec=c['main'],style=s,size=10);number(a,x+2,43,n,s)
  arrow(a,(20,37),(29,37));arrow(a,(55,37),(66,37));text(a,60.5,40,'Ready',8)
  box(a,29,10,33,17,ec=c['main']);text(a,45.5,24,'Cache service',10,weight='bold')
  text(a,45.5,20,'Joint LRU · weight delivery',8.5)
  box(a,31,12,12,5,'HBM',fc=c['pale'],ec=c['main']);box(a,46,12,14,5,'CPU pinned',fc=c['pale'],ec=c['main'],size=8)
  arrow(a,(42,33),(42,27));text(a,35,30,'Miss',8);number(a,26,24,3,s)
  arrow(a,(55,27),(60,37),dash=True);text(a,56,30,'Ready event',7.5,ha='right')
  arrow(a,(62,24),(66,28));arrow(a,(66,28),(82,28));arrow(a,(82,28),(82,33));text(a,75,30,'HBM weights',8)
  box(a,75,12,22,12,'SSD backing store\nAll expert weights',ec=INK,size=9)
  arrow(a,(75,17),(62,17));text(a,68,20,'Read',8)
  box(a,2,10,20,17,fc=c['pale'],ec='#999999');text(a,12,24,'Offline compiler',9,weight='bold')
  text(a,12,19,'Profile + metadata\nCaps + costs',8)
  text(a,12,13,'Plan: quotas + IDs',8)
  arrow(a,(22,15),(29,15),dash=True)
  text(a,50,3,'Solid: weight / request path     Dashed: initialization / readiness',8)
 emit(f,'02_framework',s)

def retention(s):
 f,a=canvas(3.25);c=CFG[s]
 states=[([0,1],[2,3,4]),([1,2],[3,4,0]),([2,0],[3,4,1])]
 if s=='HPCA':
  for i,(h,cp) in enumerate(states):
   x=2+i*34;text(a,x+14,43,['Initial state','Access $e_2$','Access $e_0$'][i],11,weight='bold')
   box(a,x,9,28,29,ec=c['main']);text(a,x+2,34,'HBM',9,ha='left');cells(a,x+5,26,h,s,w=7,h=5,gap=2)
   a.plot([x,x+28],[23,23],color=c['main'],lw=1);text(a,x+2,20,'CPU pinned',9,ha='left');cells(a,x+2,12,cp,s,w=6,h=5,gap=2)
   text(a,x+14,5,'LRU → MRU',8)
   if i<2:arrow(a,(x+29,24),(x+33,24),lw=1.3)
  text(a,50,0,'Promote requested expert; demote HBM victim into the joint retention set',9)
 elif s=='ASPLOS':
  for i,(h,cp) in enumerate(states):
   y=34-i*14;box(a,1,y-2,98,11,fc=c['pale'] if i%2==0 else '#fafafa',ec='#d7deeb',style=s)
   text(a,11,y+3,['Initial state','Request $e_2$','Request $e_0$'][i],10,weight='bold')
   cells(a,26,y,h,s,w=8,h=6,gap=2);cells(a,59,y,cp,s,w=8,h=6,gap=2)
   if i:
    arrow(a,(30,y+12),(83,y+8),color=c['accent'])
    text(a,55,y+12,'Demote $e_'+str(i-1)+'$',8)
  text(a,35,46,'HBM residency',10,weight='bold',color=c['main']);text(a,73,46,'CPU residency',10,weight='bold',color=c['alt'])
  text(a,50,0,'Each row is a complete snapshot; each tier is ordered LRU → MRU',8.5)
 else:
  # Unified ranked state; the capacity seam has operational meaning.
  text(a,1,46,'A single recency order across two resident tiers',11,ha='left',weight='bold')
  for i,stack in enumerate([[1,0,4,3,2],[2,1,0,4,3],[0,2,1,4,3]]):
   y=32-i*11;text(a,13,y+2.6,['Initial','After $e_2$','After $e_0$'][i],10)
   cells(a,28,y,stack,s,w=10,h=5.5,gap=2)
  a.plot([50.5,50.5],[7,40],color=INK,ls='--',lw=1)
  text(a,39,41,'HBM',9,weight='bold');text(a,69,41,'CPU pinned memory',9,weight='bold')
  text(a,28,3,'MRU',9,ha='left');text(a,87,3,'LRU',9,ha='right')
  text(a,50,0,'Exclusive logical residency; serial example without prefetch or mirrors',8)
 emit(f,'03_retention',s)

def delivery(s):
 f,a=canvas(3.5);c=CFG[s]
 if s=='HPCA':
  text(a,1,46,'Readiness gates execution; independent compute can overlap transfer',10.5,ha='left',weight='bold')
  lanes=[('SSD read',33),('H2D copy',23),('GPU compute',9)]
  for label,y in lanes:text(a,1,y+3,label,9,ha='left');a.plot([22,98],[y-1,y-1],color='#bbbbbb',lw=.6)
  box(a,24,33,30,6,'Read $e_2$',fc=c['pale'],ec=c['main']);box(a,54,23,18,6,'Copy $e_2$',fc=c['pale'],ec=c['main'])
  box(a,24,9,26,6,'Execute $e_0$',fc=c['main'],ec=c['main']);a.texts[-1].set_color('white')
  box(a,73,9,23,6,'Execute $e_2$',fc=c['main'],ec=c['main']);a.texts[-1].set_color('white')
  arrow(a,(54,36),(54,29));arrow(a,(72,26),(73,15));number(a,74,21,2,s)
  text(a,59,12,'Wait for $e_2$',8);number(a,23,43,1,s);text(a,39,43,'Router selects $e_0$, $e_2$',9)
  arrow(a,(23,2),(97,2));text(a,60,0,'Schematic time →',8)
 elif s=='ASPLOS':
  # Program order above, asynchronous delivery below, shared semantic colors.
  text(a,1,46,'Program order',10,ha='left',weight='bold')
  for x,label in [(8,'Select $e_0$, $e_2$'),(38,'Execute $e_0$'),(76,'Execute $e_2$')]:
   box(a,x,32,21,8,label,fc=c['pale'],ec=c['main'],style=s)
  arrow(a,(29,36),(38,36));arrow(a,(59,36),(76,36))
  box(a,1,5,98,20,fc='#f3f7f5',ec='#bfcec8',style=s);text(a,4,21,'Asynchronous delivery',9,ha='left',weight='bold',color=c['alt'])
  box(a,8,9,24,7,'SSD read $e_2$',fc='white',ec=c['alt'],style=s)
  box(a,40,9,22,7,'H2D copy $e_2$',fc='white',ec=c['alt'],style=s)
  box(a,75,9,20,7,'Ready event',fc='#fff4d7',ec=c['accent'],style=s)
  arrow(a,(32,12.5),(40,12.5));arrow(a,(62,12.5),(75,12.5));arrow(a,(85,16),(85,32),dash=True)
  arrow(a,(18,32),(18,25),dash=True);arrow(a,(18,25),(18,16),dash=True)
  text(a,48,28,'$e_0$ is already HBM-resident',8.5)
  text(a,50,0,'Execution order is preserved; delivery of $e_2$ can overlap execution of $e_0$',9)
 else:
  text(a,1,46,'Two dependencies must complete before $e_2$ executes',11,ha='left',weight='bold')
  box(a,1,25,21,10,'Select $e_0$, $e_2$',ec=c['main'],size=10)
  box(a,32,31,24,8,'Execute $e_0$',fc=c['pale'],ec=c['main'],size=10)
  box(a,31,9,17,8,'Read $e_2$',ec=c['main']);box(a,56,9,17,8,'H2D $e_2$',ec=c['main'])
  a.add_patch(Circle((80,35),1.1,fc=INK));box(a,86,30,13,10,'Execute\n$e_2$',ec=c['main'],size=10)
  arrow(a,(22,30),(32,35));arrow(a,(22,28),(31,13));arrow(a,(48,13),(56,13));arrow(a,(73,13),(80,34),dash=True)
  arrow(a,(56,35),(79,35));arrow(a,(81,35),(86,35))
  text(a,67,39,'Kernel order',8.5);text(a,84,20,'Weights ready',8.5)
  number(a,28,39,1,s);number(a,54,20,2,s);number(a,83,43,3,s)
  text(a,50,1,'Branching denotes independent work; arrow length does not encode duration',9)
 emit(f,'04_delivery',s)

def axes(s,n=2,h=3.1):
 f,aa=plt.subplots(1,n,figsize=(8.5,h),squeeze=False)
 f.subplots_adjust(left=.075,right=.985,bottom=.26,top=.77,wspace=.43)
 return f,list(aa[0])

def polish(a,s,title,ylabel=None):
 c=CFG[s];a.set_title(title,loc='left' if s!='HPCA' else 'center',fontweight='bold',pad=9)
 if ylabel:a.set_ylabel(ylabel)
 a.set_axisbelow(True);a.tick_params(length=3,pad=3)
 if s=='HPCA':
  for sp in a.spines.values():sp.set_visible(True);sp.set_linewidth(.65)
  a.grid(axis='y',lw=.4,color='#cccccc',ls=':')
 elif s=='ASPLOS':
  a.spines[['top','right']].set_visible(False);a.set_facecolor('#f8f9fc');a.grid(axis='y',color='white',lw=1)
 else:
  a.spines[['top','right','left']].set_visible(False);a.tick_params(axis='y',length=0)
  a.grid(axis='y',lw=.45,color='#e4e4e4')

def bars(a,s,x,ys,labels,width=.32,labels_on=False):
 c=CFG[s];colors=[c['alt'],c['main'],c['accent'],'#d1d4d6','#7f8b9b','#222222']
 n=len(ys)
 for j,(values,label) in enumerate(zip(ys,labels)):
  b=a.bar(np.array(x)+(j-(n-1)/2)*width,values,width*.92,label=label,
   color=colors[j],ec=INK if s=='HPCA' else 'white',lw=.5,
   hatch=['','///','..','xx','--','++'][j] if s=='HPCA' else None,zorder=3)
  if labels_on:a.bar_label(b,fmt='%g',padding=3,fontsize=8)

def legend(a,s,n=2):
 a.legend(loc='upper left',bbox_to_anchor=(-.04,1.34),ncol=n,frameon=s=='HPCA',
  edgecolor='#bbbbbb',handlelength=1.5,columnspacing=1,borderpad=.4)

def line(a,s,x,y,label,j=0):
 c=CFG[s];col=[c['alt'],c['main'],c['accent']][j]
 a.plot(x,y,label=label,c=col,marker=['s','o','^'][j],markersize=3.5,lw=1.3,
  ls=['--','-','-.'][j] if s=='HPCA' else '-')
 if s=='OSDI':a.annotate(label,(x[-1],y[-1]),xytext=(4,0),textcoords='offset points',fontsize=8,color=col,va='center')

def challenge(s):
 f,aa=axes(s,3,3.65);f.subplots_adjust(bottom=.34,wspace=.5)
 m=D['motivation'];x=np.arange(4)
 bars(aa[0],s,x,[m['ssd_misses_uniform'],m['ssd_misses_planned']],['Uniform','Planned'])
 aa[0].set_xticks(x,['L1','L2','L3','L4']);aa[0].set_xlabel('Layer group');aa[0].set_ylim(0,55)
 polish(aa[0],s,'(a) Placement imbalance','SSD demand misses');legend(aa[0],s)
 bars(aa[1],s,np.arange(3),[m['retention_ssd_percent']],['Retention'],width=.6,labels_on=True)
 aa[1].set_xticks([0,1,2],['Separate','Mirrored','Joint']);aa[1].set_ylim(0,40)
 polish(aa[1],s,'(b) Redundant residency','SSD demand-miss share (%)')
 for j,(key,label) in enumerate([('fixed_windows','Fixed'),('online_windows','Online LRU'),('mecc_windows','MECC')]):
  line(aa[2],s,list(range(1,17)),m[key],label,j)
  if s=='OSDI':
   aa[2].texts[-1].remove()
   aa[2].annotate(label,(16,m[key][-1]),xytext=(19,[45,23,5][j]),
    fontsize=7.5,va='center',color=[CFG[s]['alt'],CFG[s]['main'],CFG[s]['accent']][j],
    arrowprops=dict(arrowstyle='-',lw=.5,color='#999999'))
 aa[2].axvline(8.5,c='#aaaaaa',ls=':',lw=.8);aa[2].set_ylim(0,58);aa[2].set_xticks([1,8,16]);aa[2].set_xlabel('Request window')
 polish(aa[2],s,'(c) Cold start and drift','SSD demand-miss share (%)')
 if s!='OSDI':legend(aa[2],s,3)
 else:aa[2].set_xlim(0,30)
 # Three small explanatory drawings connect evidence to the mechanism.
 for i in range(3):
  a=f.add_axes([.08+i*.31,.025,.25,.16]);a.set(xlim=(0,30),ylim=(0,10));a.axis('off')
  if i==0:
   for j,n in enumerate([2,3,5,6]):
    for k in range(n):box(a,1+j*4,3+k*.6,3,.48,fc=CFG[s]['main'],ec='white',style=s,lw=.2)
   text(a,21,5,'Layer-specific\nslot quotas',8)
  elif i==1:
   cells(a,1,4,[0,1],s,w=3,h=3);cells(a,12,4,[2,3,4],s,w=3,h=3)
   text(a,15,0,'Distinct experts across resident tiers',7.5)
  else:
   for j in range(5):
    a.add_patch(Circle((3+j*4,5),.8,fc=CFG[s]['main'] if j<2 else '#c8c8c8'))
   arrow(a,(6,8),(18,8));text(a,15,0,'Adapt to a changing hot set',7.5)
 emit(f,'01_challenges',s,True)

def performance(s):
 c=CFG[s]
 if s=='ASPLOS':
  f,aa=plt.subplots(2,2,figsize=(8.5,4.5));f.subplots_adjust(left=.08,right=.98,bottom=.15,top=.82,hspace=.8,wspace=.25)
  for k,a in enumerate(aa.flat):
   vals=[v[k] for name,v in D['tpot_seconds'].items() if name!='Resident 8-GPU reference']
   cols=[c['alt']]*4+[c['main']];b=a.bar(range(5),vals,color=cols,ec='white',lw=.5)
   a.bar_label(b,fmt='%g',padding=2,fontsize=8);a.set_xticks(range(5),['Stream','LRU','RF','SSD','MECC']);a.set_ylim(0,75)
   polish(a,s,f'({chr(97+k)}) '+D['groups'][k],'TPOT (s/token)')
  f.text(.5,.94,'Matched single-GPU policies',ha='center',weight='bold',fontsize=11)
 elif s=='OSDI':
  f,aa=axes(s,2,3.6)
  for i,a in enumerate(aa):
   for j,(name,values) in enumerate(D['tpot_seconds'].items()):
    if name=='Resident 8-GPU reference':continue
    x=np.arange(2);v=values[2*i:2*i+2]
    a.plot(x,v,c=c['main'] if name=='MECC' else ['#999999','#777777','#555555','#aaaaaa'][j],lw=1.8 if name=='MECC' else .8,marker='o',ms=4)
    # Spread direct labels independently of values; thin leaders preserve mapping.
    label_y=([34,24,18,12,5] if i==0 else [62,42,34,27,19])[j]
    a.annotate(['Streaming','Three-tier LRU','RF adapter','SSD-native','MECC'][j],
      (1,v[-1]),xytext=(1.25,label_y),textcoords='data',fontsize=8,va='center',
      color=c['main'] if name=='MECC' else '#555555',
      arrowprops=dict(arrowstyle='-',color=c['main'] if name=='MECC' else '#aaaaaa',lw=.55))
   a.set_xlim(-.15,2.05);a.set_ylim(0,70);a.set_xticks([0,1],['QA','Code']);polish(a,s,['(a) Mixtral-8x7B','(b) Mixtral-8x22B'][i],'TPOT (s/token)')
 else:
  f,aa=axes(s,2,3.6)
  for i,a in enumerate(aa):
   ys=[v[2*i:2*i+2] for name,v in D['tpot_seconds'].items() if name!='Resident 8-GPU reference']
   bars(a,s,np.arange(2),ys,['Stream','LRU','RF','SSD','MECC'],width=.15)
   a.set_xticks([0,1],['QA','Code']);a.set_ylim(0,70);polish(a,s,['(a) Mixtral-8x7B','(b) Mixtral-8x22B'][i],'TPOT (s/token)')
  handles,labels=aa[0].get_legend_handles_labels();f.legend(handles,labels,loc='upper center',bbox_to_anchor=(.5,.94),ncol=5,frameon=True)
 f.text(.5,.015,'RF / SSD: hypothetical matched adapters; resident multi-GPU reference is shown separately.',ha='center',fontsize=8)
 emit(f,'05_performance',s,True)

def ablation(s):
 f,aa=axes(s,2,3.3);names=['Streaming','+ Placement','+ Joint LRU','+ Delivery']
 for i,(a,ys,label) in enumerate(zip(aa,[D['ablation_tpot_seconds'],D['ablation_ssd_percent']],['TPOT (s/token)','SSD demand-miss share (%)'])):
  if s=='OSDI':
   a.plot(range(4),ys,c=CFG[s]['main'],marker='o',ms=5)
   for x,y in enumerate(ys):a.annotate(f'{y:g}',(x,y),xytext=(0,7),textcoords='offset points',ha='center',fontsize=9)
  else:
   b=a.bar(range(4),ys,color=[CFG[s]['alt']]*3+[CFG[s]['main']],ec=INK if s=='HPCA' else 'white',lw=.6)
   if s=='HPCA':
    for j,p in enumerate(b):p.set_hatch(['','//','..','xx'][j])
   a.bar_label(b,fmt='%g',padding=3,fontsize=9)
  a.set_xticks(range(4),['Stream','+Place','+Retain','+Deliver']);a.set_ylim(0,max(ys)*1.3);polish(a,s,['(a) Decode latency','(b) SSD demand'][i],label)
 f.text(.5,.045,'Cumulative configurations: placement → joint retention → delivery. Not independent effect sizes.',ha='center',fontsize=8.5)
 emit(f,'06_ablation',s,True)

def resources(s):
 f,aa=axes(s,2,3.5)
 for j,(name,v) in enumerate(D['budget_tpot_seconds'].items()):line(aa[0],s,D['cpu_budget_gb'],v,name,j)
 aa[0].set_xlabel('Task host-memory cap (GB)');aa[0].set_ylim(0,34);aa[0].set_xticks(D['cpu_budget_gb']);polish(aa[0],s,'(a) Host-memory sensitivity','TPOT (s/token)')
 if s=='OSDI':aa[0].set_xlim(14,71)
 else:legend(aa[0],s)
 m=np.arange(25)
 for j,(name,y) in enumerate([('SSD-native adapter',12+10*m),('MECC',30+8*m)]):line(aa[1],s,m,y,name,j)
 aa[1].scatter([9],[102],c=CFG[s]['accent'],s=24,zorder=5);aa[1].annotate('$m=9$',(9,102),xytext=(-10,24),textcoords='offset points',arrowprops=dict(arrowstyle='-',lw=.7),fontsize=9)
 aa[1].set_xlabel('Decode intervals after first token, $m$');polish(aa[1],s,'(b) Initialization + decode','Restricted cost (s)')
 if s=='OSDI':aa[1].set_xlim(0,43)
 else:legend(aa[1],s)
 f.text(.5,.035,'Restricted accounting: 12 + 10m versus 30 + 8m. Excludes TTFT and profiling.',ha='center',fontsize=8.5)
 emit(f,'07_resources',s,True)

def allocation(s):
 f,aa=axes(s,2,3.5);gpu=np.array([1,2,4,8]);lat=np.array([8,2.8,1.65,1])
 for a,y,label,title in [(aa[0],lat,'TPOT (s/token)','(a) Latency'),(aa[1],gpu*lat,'Nominal GPU-s/token','(b) Allocated GPU-time')]:
  b=a.bar(range(4),y,color=[CFG[s]['main']]+[CFG[s]['alt']]*3,ec=INK if s=='HPCA' else 'white',lw=.6,width=.6)
  if s=='HPCA':
   for p in list(b)[1:]:p.set_hatch('//')
  a.bar_label(b,fmt='%g',padding=4,fontsize=9);a.set_ylim(0,10.5)
  a.set_xticks(range(4),['MECC\n1 GPU','Resident\n2 GPUs','Resident\n4 GPUs','Resident\n8 GPUs']);polish(a,s,title,label)
 f.text(.5,.04,'Resident configurations are scenario references. GPU-time = GPU count × TPOT; no energy claim.',ha='center',fontsize=8)
 emit(f,'08_allocation',s,True)

def cn(page,rect,t,size=11):
 page.insert_font(fontname='CN',fontfile='C:/Windows/Fonts/msyh.ttc')
 z=page.insert_textbox(pymupdf.Rect(rect),t,fontname='CN',fontsize=size,color=(.12,.12,.12))
 if z<0:raise ValueError(t)

def galleries():
 doc=pymupdf.open();compare=OUT/'comparisons';compare.mkdir(exist_ok=True)
 sections=[]
 # Framework first so the three design languages can be assessed immediately.
 for key,title in sorted(SPEC,key=lambda x:0 if x[0]=='02_framework' else 1):
  page=doc.new_page(width=842,height=1191)
  cn(page,(30,17,810,49),title+'：三种设计语言',19)
  cn(page,(30,50,810,75),'参考具体论文的信息组织方式；不是会场统一模板。实验数字均为假设目标。',10)
  cards=[]
  for i,s in enumerate(STYLES):
   y=85+i*352
   cn(page,(32,y,810,y+25),s+' 参考设计',14)
   cn(page,(32,y+28,810,y+62),NOTES[s],10)
   with pymupdf.open(OUT/key/f'{s}.pdf') as src:page.show_pdf_page(pymupdf.Rect(32,y+64,810,y+336),src,0)
   uri=base64.b64encode((OUT/key/f'{s}.png').read_bytes()).decode()
   cards.append(f'<article><h3>{s}</h3><p>{NOTES[s]}</p><button class="image" onclick="zoom(this)"><img src="data:image/png;base64,{uri}" alt="{title} {s}"></button><button onclick="choose(\'{key}\',\'{s}\')">选择 {s}</button></article>')
  page.get_pixmap(matrix=pymupdf.Matrix(1,1)).save(str(compare/f'{key}.png'))
  sections.append(f'<section id="{key}"><h2>{title}</h2><div class="cards">'+''.join(cards)+'</div></section>')
 doc.subset_fonts();doc.save(OUT/'MECC_venue_design_comparison.pdf',garbage=4,deflate=True)
 index=json.dumps(SPEC,ensure_ascii=False)
 content='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>MECC · HPCA / ASPLOS / OSDI 参考设计</title><style>
 *{box-sizing:border-box}body{font:15px/1.7 "Microsoft YaHei",sans-serif;color:#222;background:#f4f5f6;margin:0;padding:28px}main{max-width:1650px;margin:auto}h1{font-size:27px}h2{margin-top:42px}h3{margin:0;font-size:20px}.lead{max-width:1100px}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}article{background:white;padding:18px;border:1px solid #d4d8dc}article p{font-size:13px;min-height:70px;color:#555}.image{height:280px;border:0;background:white;width:100%;padding:0;cursor:zoom-in}.image img{width:100%;height:100%;object-fit:contain}button{font:inherit;font-size:13px;padding:6px 13px;cursor:pointer}textarea{width:100%;height:240px;font:15px/1.8 monospace;margin:12px 0}dialog{width:96vw;max-width:1500px;border:1px solid #999}dialog img{width:100%;max-height:85vh;object-fit:contain}dialog::backdrop{background:#0009}.notice{background:#fff1b0;padding:12px 18px}.selected{outline:3px solid #246652}a{color:#245b8a}@media(max-width:1100px){.cards{grid-template-columns:1fr}.image{height:auto}.image img{max-height:450px}article p{min-height:0}}
 </style><main><h1>同一篇 MECC，三套不同的图形设计</h1><p class="lead">HPCA 参考：硬件与存储层次；ASPLOS 参考：编译器与运行时协同；OSDI 参考：请求路径与系统服务。三套方案分别调整布局、对象画法、阅读顺序与注释体系。先看系统框架，再看各套规则如何延续到其余图中。</p>
 <p>具体参考：<a href="https://seonghoonseo.github.io/files/pdf/research/2025-hpca-facil.pdf">FACIL · HPCA 2025</a>、<a href="https://yuyue.github.io/res/paper/Klotski-ASPLOS2025.pdf">Klotski · ASPLOS 2025</a>、<a href="https://www.usenix.org/system/files/osdi24-lee.pdf">InfiniGen · OSDI 2024</a>。这是对具体图例的设计借鉴，不代表该会议只有一种风格。</p><p class="notice">所有实验结果保留 HYPOTHETICAL 标记；时序示意不代表实测时间。未替换论文中的正式配图。</p>'''+''.join(sections)+'''<h2>选择清单</h2><p>可逐张选择，点击图片可放大查看。</p><textarea id="choices" readonly></textarea></main><dialog id="large"><button onclick="this.parentElement.close()">关闭</button><img id="big"></dialog><script>
 const items='''+index+''';let selected={};try{selected=JSON.parse(localStorage.getItem('mecc-venue-design-v1')||'{}')}catch(e){}function update(){document.getElementById('choices').value=items.map(([k,t])=>t+'：'+(selected[k]||'未选择')).join('\\n');document.querySelectorAll('article').forEach(a=>a.classList.remove('selected'));for(const [k,s] of Object.entries(selected)){const sec=document.getElementById(k);if(sec)for(const a of sec.querySelectorAll('article'))if(a.querySelector('h3').textContent===s)a.classList.add('selected')}try{localStorage.setItem('mecc-venue-design-v1',JSON.stringify(selected))}catch(e){}}function choose(k,s){selected[k]=s;update()}function zoom(b){document.getElementById('big').src=b.querySelector('img').src;document.getElementById('large').showModal()}update();</script></html>'''
 (OUT/'MECC_venue_design_chooser.html').write_text(content,encoding='utf-8')

def audit():
 checks=[]
 for e in ENTRIES:
  p=OUT/e['figure']/f"{e['design']}.pdf";d=pymupdf.open(p);page=d[0]
  outside=[sp['text'] for b in page.get_text('dict')['blocks'] for ln in b.get('lines',[]) for sp in ln['spans'] if not page.rect.contains(pymupdf.Rect(sp['bbox']))]
  checks.append(dict(**e,vector_only=not page.get_images(),outside_text=outside,
   target_badge=(not e['hypothetical'] or 'NOT MEASURED' in page.get_text())))
 assert all(c['vector_only'] and not c['outside_text'] and c['target_badge'] for c in checks),checks
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==HASH
 (OUT/'validation.json').write_text(json.dumps({'source_sha256':HASH,'checks':checks},indent=2),encoding='utf-8')

def main():
 OUT.mkdir(exist_ok=True)
 for s in STYLES:
  for fn in [framework,retention,delivery,challenge,performance,ablation,resources,allocation]:fn(s)
 galleries();audit()
 (OUT/'README.md').write_text('''# MECC：三套参考设计

这次区别是设计语言，不是 A/B/C 配色换肤。框架图首先分别按硬件数据通路、编译/运行协同、请求服务路径重构；其余图延续各自的对象、分区和注释方式。

参考来源（均非 PRICE）：
- HPCA：FACIL (2025), Fig. 7–8 的模块分栏、编号操作及内存布局表达。
- ASPLOS：Klotski (2025), Fig. 6 的离线/在线划分与执行轨道表达。
- OSDI：InfiniGen (2024) 的缓存管理系统视图、操作编号及简洁实验图组织。

会议内部有多种设计风格，这三套是结合具体参考作出的设计解释，不是会议官方模板，也未复制其算法结构。

先打开 MECC_venue_design_chooser.html，或 MECC_venue_design_comparison.pdf。框架图排在最前。共 8 类图 × 3 套；每张包含 PDF / SVG / PNG。Times New Roman 与 STIX 沿用论文。数值来源是原有 ideal_assumptions.json，不包含新增实测、置信区间或多卡 MECC 假设；所有数字仍是 HYPOTHETICAL。示意图不代表时间测量。主论文尚未替换。

重建：python build_venue_designs.py。validation.json 记录输入哈希、矢量性、文字边界与假设标记检查。
''',encoding='utf-8')
 with zipfile.ZipFile(P.parent/'MECC_venue_designs.zip','w',zipfile.ZIP_DEFLATED) as z:
  for f in OUT.rglob('*'):
   if f.is_file():z.write(f,f.relative_to(P))
  z.write(Path(__file__),'build_venue_designs.py')
 print('24 figure designs generated; vector, bounds, badges and frozen-input checks passed.')

if __name__=='__main__':main()
