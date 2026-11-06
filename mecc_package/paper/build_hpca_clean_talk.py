"""Polish the existing HPCA review deck for internal ideal-results reading."""
from pathlib import Path
from copy import deepcopy
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from media_hdd import figure_text
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

HERE=Path(__file__).resolve().parent
PAPER=HERE/'dac2027'
SOURCE=HERE/'MECC_HPCA_review_revision.pptx'
TABLE_SOURCE=HERE/'MECC_conference_talk.pptx'
OUT=HERE/'MECC_HPCA_clean_ideal.pptx'
ASSETS=HERE/'hpca_clean_ideal_assets';ASSETS.mkdir(exist_ok=True)
D=json.loads((PAPER/'ideal_assumptions.json').read_text(encoding='utf-8'))
BLUE='#4279A8';DARK='#20344A';MID='#84AFBD';GREY='#A8ADB3';LIGHT='#D5DCE3'
ORANGE='#D59A60';GREEN='#76A68B';INK='#29333B'
plt.rcParams.update({'font.family':['Times New Roman','SimSun'],
 'font.size':13,'axes.titlesize':15,'axes.labelsize':13,'xtick.labelsize':12,
 'ytick.labelsize':12,'axes.spines.top':False,'axes.spines.right':False,
 'axes.unicode_minus':False,'savefig.facecolor':'white','figure.facecolor':'white',
 'hatch.linewidth':.8,'pdf.fonttype':42})

def style(ax,ylabel=None):
 ax.grid(axis='y',color='#DEE2E5',lw=.55);ax.set_axisbelow(True)
 if ylabel:ax.set_ylabel(ylabel)
 ax.tick_params(length=3,color=INK)
 ax.spines['bottom'].set_color(INK);ax.spines['left'].set_color(INK)

def patterned_bars(ax,x,values,colors,hatches,width=.59,**kwargs):
 bars=ax.bar(x,values,color=colors,edgecolor=INK,linewidth=.75,width=width,**kwargs)
 for patch,h in zip(bars,hatches):patch.set_hatch(h)
 return bars

def save(fig,name):
 figure_text(fig)
 fig.savefig(ASSETS/(name+'.png'),dpi=240,bbox_inches='tight',pad_inches=.08)
 fig.savefig(ASSETS/(name+'.pdf'),bbox_inches='tight',pad_inches=.08)
 plt.close(fig)

def charts():
 mdata=D['motivation']
 fig,ax=plt.subplots(figsize=(5.7,2.75));fig.subplots_adjust(left=.13,right=.97,bottom=.23,top=.90)
 values=[D['ttft_seconds']['Resident 8-GPU reference'][0],D['ttft_seconds']['Unoptimized streaming'][0],D['ttft_seconds']['MECC'][0]]
 bars=patterned_bars(ax,range(3),values,[GREY,ORANGE,BLUE],['///','\\\\','xxx'])
 ax.bar_label(bars,fmt='%g',padding=4,fontsize=13)
 ax.set_xticks(range(3),['8 卡显存部署','未优化单卡','单卡 MECC'])
 ax.set_ylim(0,150);style(ax,'首 token 延迟（秒）')
 save(fig,'mot_cold_start')

 fig,ax=plt.subplots(figsize=(5.7,2.75));fig.subplots_adjust(left=.13,right=.97,bottom=.23,top=.90)
 values=[0,mdata['retention_ssd_percent'][0]]
 bars=patterned_bars(ax,range(2),values,[GREY,BLUE],['///','xxx'],width=.56)
 ax.bar_label(bars,fmt='%g%%',padding=4,fontsize=13)
 ax.set_xticks(range(2),['8 卡显存部署','单卡固定 CPU 缓存'])
 ax.set_ylim(0,40);style(ax,'需从 SSD 读取（%）')
 save(fig,'mot_retention')

 fig,ax=plt.subplots(figsize=(5.7,2.75));fig.subplots_adjust(left=.14,right=.97,bottom=.23,top=.87)
 xx=np.arange(1,17)
 ax.plot(xx,np.zeros_like(xx),label='8 卡显存部署',color=GREY,marker='o',ms=2.7,lw=1.5)
 for key,label,color,marker in [('fixed_windows','单卡固定缓存',BLUE,'s')]:
  ax.plot(xx,mdata[key],label=label,color=color,marker=marker,ms=3.4,lw=1.45)
 ax.axvline(8.5,color='#AEB8C1',lw=.85,ls=':')
 ax.set_xlim(1,16);ax.set_ylim(-3,58);ax.set_xticks([1,4,8,9,12,16])
 ax.set_xlabel('请求窗口');ax.legend(loc='upper left',ncol=1,fontsize=10,frameon=False)
 style(ax,'需从 SSD 读取（%）');save(fig,'mot_drift')

 fig,aa=plt.subplots(1,2,figsize=(11.7,3.35),gridspec_kw={'width_ratios':[1.7,1]})
 fig.subplots_adjust(left=.065,right=.98,bottom=.23,top=.73,wspace=.36)
 x=np.arange(4);labs=['8×7B\n问答','8×7B\n代码','8×22B\n问答','8×22B\n代码']
 for j,(name,c,h) in enumerate([('Unoptimized streaming',GREY,'///'),('SSD-native adapter',ORANGE,'\\\\'),('MECC',BLUE,'xxx')]):
  aa[0].bar(x+(j-1)*.23,D['tpot_seconds'][name],.215,color=c,edgecolor=INK,linewidth=.65,hatch=h,label={'Unoptimized streaming':'未优化单卡','SSD-native adapter':'SSD 缓存基线','MECC':'MECC'}[name])
 aa[0].set_xticks(x,labs);aa[0].set_ylim(0,72)
 handles,labels=aa[0].get_legend_handles_labels()
 fig.legend(handles,labels,ncol=3,fontsize=10,loc='upper left',bbox_to_anchor=(.06,.99),frameon=False)
 aa[0].set_title('(a) 单卡解码延迟');style(aa[0],'TPOT（秒/token）')
 ratio=np.array(D['tpot_seconds']['SSD-native adapter'])/np.array(D['tpot_seconds']['MECC'])
 labels=['8×7B 问答','8×7B 代码','8×22B 问答','8×22B 代码']
 b=aa[1].barh(np.arange(4),ratio,color=BLUE,edgecolor=INK,linewidth=.7,hatch='///',height=.54)
 aa[1].set_yticks(np.arange(4),labels);aa[1].invert_yaxis();aa[1].set_xlim(0,1.8)
 aa[1].bar_label(b,labels=[f'{v:.2f}×' for v in ratio],padding=4,fontsize=11)
 style(aa[1],'加速比')
 aa[1].set_title('(b) 相对 SSD 缓存基线的加速比')
 save(fig,'main')

 fig,aa=plt.subplots(1,2,figsize=(11.7,3.35));fig.subplots_adjust(left=.075,right=.98,bottom=.25,top=.83,wspace=.37)
 names=['未优化\n单卡','+ 初始\n放置','+ 两级\n缓存','+ 传输\n重叠']
 for a,vals,ylabel,lim,title in zip(aa,[D['ablation_tpot_seconds'],D['ablation_ssd_percent']],
      ['TPOT（秒/token）','SSD 读取比例（%）'],[31,55],['(a) 解码延迟','(b) SSD 读取比例']):
  b=patterned_bars(a,range(4),vals,[GREY,ORANGE,GREEN,BLUE],['///','\\\\','---','xxx'],width=.64)
  a.bar_label(b,fmt='%g',padding=4,fontsize=12);a.set_xticks(range(4),names)
  a.set_ylim(0,lim);a.set_title(title);style(a,ylabel)
 save(fig,'ablation')

 fig,aa=plt.subplots(1,2,figsize=(11.7,3.35));fig.subplots_adjust(left=.08,right=.98,bottom=.22,top=.85,wspace=.39)
 x=D['cpu_budget_gb'];aa[0].plot(x,D['budget_tpot_seconds']['Three-tier LRU'],'s--',color=GREY,label='三级 LRU')
 aa[0].plot(x,D['budget_tpot_seconds']['MECC'],'o-',color=BLUE,label='MECC')
 aa[0].set_xticks(x);aa[0].set_ylim(0,31);aa[0].set_xlabel('任务可用 CPU 内存（GB）')
 aa[0].legend(frameon=False,fontsize=11);aa[0].set_title('(a) CPU 内存与解码延迟');style(aa[0],'TPOT（秒/token）')
 m=np.arange(21);aa[1].plot(m,12+10*m,'s--',color=GREY,label='SSD 缓存基线')
 aa[1].plot(m,30+8*m,'o-',color=BLUE,label='MECC')
 aa[1].scatter([9],[102],color=BLUE,s=46,zorder=4);aa[1].annotate('9 个生成区间',(9,102),xytext=(11,66),fontsize=11,arrowprops=dict(arrowstyle='->',lw=.8))
 aa[1].set_xlim(0,21);aa[1].set_xlabel('首 token 后的生成区间数')
 aa[1].set_title('(b) 初始化 + 解码开销');aa[1].legend(frameon=False,fontsize=11);style(aa[1],'累计秒数')
 save(fig,'resources')

 fig,aa=plt.subplots(1,2,figsize=(11.7,3.35));fig.subplots_adjust(left=.075,right=.98,bottom=.23,top=.85,wspace=.34)
 labs=['MECC\n1 卡','显存部署\n2 卡','显存部署\n4 卡','显存部署\n8 卡']
 g=np.array([1,2,4,8]);lat=np.array([8,2.8,1.65,1]);cost=g*lat
 for a,v,label,title in [(aa[0],lat,'TPOT（秒/token）','(a) 延迟'),(aa[1],cost,'GPU 秒/token','(b) 名义 GPU 时间')]:
  b=patterned_bars(a,range(4),v,[BLUE]+[GREY]*3,['xxx']+['///']*3,width=.62);a.bar_label(b,fmt='%g',padding=3,fontsize=12)
  a.set_xticks(range(4),labs);a.set_ylim(0,10.2);a.set_title(title);style(a,label)
 save(fig,'allocation')

def clear(slide):
 for sh in list(slide.shapes):sh._element.getparent().remove(sh._element)

def reference_table(slide):
 """Copy the native, editable checkmark matrix from the approved reference."""
 source=Presentation(TABLE_SOURCE).slides[1]
 if any(sh.shape_type==13 for sh in source.shapes):
  raise ValueError('Reference table contains pictures; relationship copy required')
 clear(slide)
 for sh in list(source.shapes)[1:]:
  slide.shapes._spTree.insert_element_before(deepcopy(sh._element),'p:extLst')
 text(slide,12.2,7.02,.5,.28,'2',17,False,'#E32222',PP_ALIGN.RIGHT)

def box(sl,x,y,w,h,c):
 sh=sl.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h));sh.fill.solid();sh.fill.fore_color.rgb=RGBColor.from_string(c[1:]);sh.line.fill.background()

def text(sl,x,y,w,h,s,size=18,bold=False,color='#111111',align=PP_ALIGN.LEFT):
 sh=sl.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=sh.text_frame;tf.clear();tf.word_wrap=True
 tf.margin_left=Pt(0);tf.margin_right=Pt(0);tf.margin_top=Pt(0);tf.margin_bottom=Pt(0)
 p=tf.paragraphs[0];p.text=s;p.alignment=align;p.font.name='SimSun' if any('\u4e00' <= ch <= '\u9fff' for ch in s) else 'Times New Roman';p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=RGBColor.from_string(color[1:]);return sh

def frame(sl,n,title,body):
 clear(sl)
 text(sl,.68,.09,12,.66,title,30,True,align=PP_ALIGN.CENTER)
 box(sl,0,.81,13.333,.035,BLUE)
 box(sl,.81,1.165,.15,.15,BLUE)
 text(sl,1.13,1.09,11.45,.94,body,19,True)
 text(sl,12.2,7.02,.5,.28,str(n),17,False,'#E32222',PP_ALIGN.RIGHT)

def footer(sl,content):
 box(sl,1.02,6.40,11.25,.012,'#B4BEC8')
 text(sl,1.04,6.53,11.2,.48,content,17,True,DARK,PP_ALIGN.CENTER)

def panel_title(sl,x,s):
 text(sl,x,2.56,5.53,.39,s,17,True,DARK,PP_ALIGN.CENTER)
 box(sl,x,3.02,5.53,.012,'#B4BEC8')

def expert(sl,x,y,label,w=.47,fill='#E7ECF1',color=DARK):
 box(sl,x,y,w,.36,fill)
 text(sl,x,y,w,.36,label,12,True,color,PP_ALIGN.CENTER)

def intro(sl):
 frame(sl,1,'Research Problem: Single-GPU MoE Deployment',
       '在单卡与有限任务内存额度下部署 MoE：模型仍须按需访问全部专家，冷权重可能从 SSD 进入计算路径。')
 text(sl,.93,2.15,6.25,.43,'单卡的专家驻留',20,True,DARK,PP_ALIGN.CENTER)
 box(sl,.93,2.65,6.25,.015,'#B4BEC8')
 for label,y,ids,colors in [
     ('GPU 显存',2.88,['E1','E2'],[BLUE,BLUE]),
     ('CPU 内存',3.38,['E3','E4','E5'],[MID,MID,MID]),
     ('SSD 后备',3.88,['E1','E2','E3','E4','E5','E6','E7','E8'],[LIGHT]*7+[BLUE])]:
  text(sl,1.05,y,.99,.35,label,15,True,DARK)
  start=2.33;step=.61
  for j,e in enumerate(ids):expert(sl,start+j*step,y,e,.51,colors[j],'#FFFFFF' if colors[j]==BLUE else DARK)
 text(sl,1.13,4.37,5.98,.42,'E8 被选中：需从 SSD 交付到 GPU',16,True,DARK,PP_ALIGN.CENTER)
 text(sl,7.65,2.15,4.75,.43,'应用场景',20,True,DARK,PP_ALIGN.CENTER)
 box(sl,7.65,2.65,4.75,.015,'#B4BEC8')
 for j,label in enumerate(['共享服务器：每个任务只获一张 GPU',
                          '离线问答与代码生成',
                          '容量受限的单卡工作站']):
  y=2.92+j*.56;box(sl,7.81,y,4.46,.45,'#EDF3F8')
  text(sl,7.94,y,4.2,.45,label,15,True,DARK)
 text(sl,.93,4.95,11.55,.42,'MECC 的三项工作',20,True,DARK,PP_ALIGN.CENTER)
 box(sl,.93,5.41,11.55,.015,'#B4BEC8')
 for i,(a,b) in enumerate([('编译期放置','画像决定初始驻留'),('跨层联合留存','保留被替换的专家'),('依赖感知交付','交叠读取与计算')]):
  x=1.0+i*3.96;box(sl,x,5.61,3.61,.56,'#EDF3F8')
  text(sl,x,5.62,3.61,.28,a,16,True,DARK,PP_ALIGN.CENTER)
  text(sl,x,5.90,3.61,.22,b,12,False,DARK,PP_ALIGN.CENTER)
 footer(sl,'研究目标：在单卡上执行超出快层容量的 MoE，并减少冷专家读取等待。')

def motivation(sl,n,title,body,plot,left,right,footer_text):
 frame(sl,n,title,body)
 panel_title(sl,.85,left);panel_title(sl,6.90,right)
 sl.shapes.add_picture(str(ASSETS/(plot+'.png')),Inches(.77),Inches(3.16),width=Inches(5.74))
 if n==4:
  text(sl,7.05,3.29,5.2,.29,'多卡完整驻留：选中专家已在 GPU',15,True,DARK)
  for j in range(8):expert(sl,7.05+j*.65,3.73,f'E{j+1}',.53,BLUE if j in [1,7] else '#DCE8F4','#FFFFFF' if j in [1,7] else DARK)
  text(sl,7.05,4.25,5.18,.36,'路由 → 显存命中 → 执行',16,True,DARK,PP_ALIGN.CENTER)
  box(sl,7.05,4.77,5.2,.014,'#B4BEC8')
  text(sl,7.05,4.87,5.2,.31,'单卡分层驻留：选中 E8 落在 SSD',15,True,DARK)
  for j,(lab,col) in enumerate([('GPU: E1 E2',BLUE),('CPU: E3 E4 E5',MID),('SSD: E6 E7 E8',GREY)]):
   x=7.05+j*1.78;box(sl,x,5.28,1.55,.43,col);text(sl,x,5.28,1.55,.43,lab,12,True,'#FFFFFF',PP_ALIGN.CENTER)
  text(sl,7.04,5.76,5.2,.25,'SSD 读取 → CPU 缓冲 → H2D → 执行',13,True,DARK,PP_ALIGN.CENTER)
 elif n==5:
  text(sl,7.01,3.34,5.2,.30,'同样的 5 个快层槽位',16,True,DARK,PP_ALIGN.CENTER)
  text(sl,7.02,3.83,1.24,.30,'独立维护',14,True,DARK)
  text(sl,8.12,3.84,.64,.29,'HBM',12,False,DARK)
  expert(sl,8.82,3.81,'E1',.59,BLUE,'#FFFFFF');expert(sl,9.52,3.81,'E2',.59,BLUE,'#FFFFFF')
  text(sl,10.20,3.84,.63,.29,'CPU',12,False,DARK)
  for j,e in enumerate(['E1','E3','E4']):expert(sl,10.75+j*.51,3.81,e,.45,MID)
  text(sl,7.02,4.32,5.2,.28,'E1 重复占位；E5 留在 SSD',13,False,DARK,PP_ALIGN.CENTER)
  box(sl,7.05,4.72,5.2,.014,'#B4BEC8')
  text(sl,7.02,4.96,1.24,.30,'联合留存',14,True,DARK)
  text(sl,8.12,4.97,.64,.29,'HBM',12,False,DARK)
  expert(sl,8.82,4.94,'E1',.59,BLUE,'#FFFFFF');expert(sl,9.52,4.94,'E2',.59,BLUE,'#FFFFFF')
  text(sl,10.20,4.97,.63,.29,'CPU',12,False,DARK)
  for j,e in enumerate(['E3','E4','E5']):expert(sl,10.75+j*.51,4.94,e,.45,MID)
  text(sl,7.02,5.45,5.2,.33,'唯一覆盖增加，被淘汰专家仍可在 CPU 复用',13,True,DARK,PP_ALIGN.CENTER)
 elif n==6:
  for phase,y,hot,fixed,online in [
      ('阶段 A',3.40,{1,2,3},{1,2,3},{1,2,3}),
      ('阶段 B',4.76,{5,6,7},{1,2,3},{5,6,7})]:
   text(sl,6.98,y-.06,1.15,.31,phase,15,True,DARK)
   for j in range(8):expert(sl,8.08+j*.51,y,f'E{j+1}',.42,BLUE if j in hot else '#E5E9ED','#FFFFFF' if j in hot else DARK)
   text(sl,7.0,y+.51,1.2,.25,'固定驻留',12,False,DARK)
   for j in range(8):box(sl,8.08+j*.51,y+.52,.42,.18,GREY if j in fixed else '#F2F4F6')
   text(sl,7.0,y+.78,1.2,.25,'在线更新',12,False,DARK)
   for j in range(8):box(sl,8.08+j*.51,y+.79,.42,.18,BLUE if j in online else '#F2F4F6')
  text(sl,8.14,6.00,4.0,.23,'热点改变后，固定初态与请求错位',12,True,DARK,PP_ALIGN.CENTER)
 footer(sl,footer_text)

def page(sl,n,title,body,img,footer):
 clear(sl)
 text(sl,.76,.10,11.8,.63,title,30,True,align=PP_ALIGN.CENTER)
 box(sl,0,.81,13.333,.035,BLUE)
 box(sl,.81,.985,.15,.15,BLUE)
 text(sl,1.13,.9,11.35,1.04,body,19,True)
 sl.shapes.add_picture(str(ASSETS/(img+'.png')),Inches(.83),Inches(2.42),width=Inches(11.67))
 box(sl,1.02,6.40,11.25,.012,'#B4BEC8')
 text(sl,1.04,6.52,11.2,.5,footer,17,True,DARK,PP_ALIGN.CENTER)
 text(sl,12.2,7.02,.5,.28,str(n),17,False,'#E32222',PP_ALIGN.RIGHT)

def close_page(sl,n):
 clear(sl);text(sl,.76,.1,11.8,.65,'Conclusion: Single-GPU SSD-Active MoE',30,True,align=PP_ALIGN.CENTER)
 box(sl,0,.81,13.333,.035,BLUE)
 text(sl,1.13,.96,11.25,1.02,'MECC 用部署前画像确定初态，用运行中访问修正驻留，并在权重就绪后执行专家。',19,True)
 for i,(label,a,b) in enumerate([
   ('放置','按层分配快层容量','画像确定初始专家'),
   ('留存','HBM/CPU 联合维护复用','SSD 保存完整后备'),
   ('交付','读取与独立计算交叠','就绪事件保护数值计算')]):
  x=.94+i*4.13;box(sl,x,2.43,3.7,.045,BLUE)
  text(sl,x,2.7,3.7,.48,label,24,True,DARK,PP_ALIGN.CENTER)
  text(sl,x,3.45,3.7,.55,a,19,False,align=PP_ALIGN.CENTER)
  text(sl,x,4.14,3.7,.55,b,19,False,align=PP_ALIGN.CENTER)
 box(sl,1.02,6.4,11.25,.012,'#B4BEC8')
 text(sl,1.04,6.53,11.2,.48,'目标部署：专家权重超出单任务 CPU 内存，且可接受单卡服务延迟。',17,True,DARK,PP_ALIGN.CENTER)
 text(sl,12.2,7.02,.5,.28,str(n),17,False,'#E32222',PP_ALIGN.RIGHT)

def main():
 charts();prs=Presentation(SOURCE)
 intro(prs.slides[0])
 reference_table(prs.slides[1])
 motivation(prs.slides[3],4,'Motivation I: Cold Start under One-GPU Capacity',
   '完整驻留的多卡无需为所选专家读取 SSD；单卡容量受限时，首 token 的冷专家必须先读取并复制。',
   'mot_cold_start','(a) 首 token 延迟：8×7B 问答','(b) 多卡驻留与单卡交付路径',
   '问题①：首 token 前，如何让单卡快层覆盖最可能请求的专家？')
 motivation(prs.slides[4],5,'Motivation II: Limited Slots, Repeated Cold Reads',
   '单卡的 HBM 与 CPU 槽位有限。独立管理会造成重复占位或淘汰后的再次冷读，快层覆盖因此受限。',
   'mot_retention','(a) 相同容量下的 SSD 需求未命中','(b) 相同槽位的唯一专家覆盖',
   '问题②：有限容量下，怎样保留更多不同的可复用专家？')
 motivation(prs.slides[5],6,'Motivation III: Hot-Set Drift during Service',
   '路由热点改变后，单卡的固定驻留仍覆盖旧热点；真实请求驱动的在线更新逐步恢复快层覆盖。',
   'mot_drift','(a) 热点切换前后的 SSD 需求未命中','(b) 旧初态与新热点逐渐错位',
   '问题③：画像失配后，怎样根据实际路由修正驻留？')
 page(prs.slides[12],13,'Results: Single-GPU Decode Latency',
      '四组模型与任务中，MECC 的单卡解码延迟低于未优化流式执行与本地 SSD 缓存基线。',
      'main','同一任务内存额度下，较接近的 SSD 缓存基线与 MECC 相差 1.25–1.42×。')
 page(prs.slides[13],14,'Ablation: Placement, Retention, Delivery',
      '放置与联合留存减少 SSD 需求未命中；交叠调度进一步减少暴露的传输等待。',
      'ablation','第一组工作负载：24 → 18 → 11 → 8 秒/token。')
 page(prs.slides.add_slide(prs.slide_layouts[6]),15,'Resource Sensitivity: Host Cap and Horizon',
      '更高的 CPU 任务额度扩大快层覆盖；更长的服务时域摊薄初始化开销。',
      'resources','资源额度和服务长度共同决定部署点。')
 page(prs.slides.add_slide(prs.slide_layouts[6]),16,'One GPU versus Resident Multi-GPU',
      '单卡 MECC 达到 8.0 秒/token；2/4/8 卡完整驻留参考进一步降低延迟。',
      'allocation','单卡方案服务于 GPU 配额受限、允许较长生成时间的场景。')
 close_page(prs.slides.add_slide(prs.slide_layouts[6]),17)
 for idx,title in [(2,'MECC: Prior and Online Policy')]:
  heading=prs.slides[idx].shapes.title
  heading.text=title
  for p in heading.text_frame.paragraphs:
   p.alignment=PP_ALIGN.CENTER
   for r in p.runs:
    r.font.name='Microsoft YaHei';r.font.size=Pt(30);r.font.bold=True;r.font.color.rgb=RGBColor(0,0,0)
 for slide in prs.slides:
  # The source deck includes process notes; this edition is a reading copy.
  slide.notes_slide.notes_text_frame.text=''
 prs.core_properties.title='MECC: Single-GPU MoE Inference'
 prs.core_properties.subject='Research presentation'
 prs.core_properties.author='';prs.core_properties.last_modified_by='';prs.core_properties.keywords='MECC, MoE, expert caching'
 prs.save(OUT)
 print('Saved',OUT,'with',len(prs.slides),'slides')

if __name__=='__main__':main()
