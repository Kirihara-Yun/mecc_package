"""Beginner-readable, editable MECC talk built from the existing deck and figures.

All ideal numeric panels remain design targets in dac2027/ideal_assumptions.json.
"""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
from pptx.oxml.xmlchemy import OxmlElement
import build_hpca_clean_talk as old
import build_insight_pairs as pairs
import build_method_figures as method_figures
from media_hdd import display_text

P=old.PAPER
A=old.ASSETS
OUT=old.HERE/'current'/'MECC_HPCA_current.pptx'
NAVY='#173D68'; BLUE='#2768A8'; MID='#7EA7CF'; GREY='#8995A1'
PALE='#EAF2F9'; LIGHT='#F3F6F9'; RULE='#C4CFD8'; DARK='#172B3B'; WHITE='#FFFFFF'
FLAT_SLIDES=set()

def box(s,x,y,w,h,c):
 sh=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h))
 sh.fill.solid();sh.fill.fore_color.rgb=RGBColor.from_string(c[1:]);sh.line.fill.background()
 if id(s) in FLAT_SLIDES:
  style=sh._element.find(qn('p:style'))
  if style is not None:sh._element.remove(style)  # first-page figure only
 return sh
def t(s,x,y,w,h,v,size=17,bold=False,c=DARK,align=PP_ALIGN.LEFT):
 return old.text(s,x,y,w,h,v,size,bold,c,align)
def rule(s,x,y,w):box(s,x,y,w,.013,RULE)
def label(s,x,y,w,v):t(s,x,y,w,.35,v,16,True,NAVY)
def tile(s,x,y,w,h,title,body=None,fill=LIGHT):
 box(s,x,y,w,h,fill);t(s,x+.13,y+.09,w-.26,.34,title,17,True,NAVY)
 if body:t(s,x+.13,y+.46,w-.26,h-.5,body,14,False,DARK)
def base(s,n,title,lead):
 old.clear(s)
 t(s,.6,.1,12.1,.58,title,29,True,'#111111',PP_ALIGN.CENTER)
 box(s,.76,1.10,.12,.12,BLUE)
 t(s,1.01,1.04,11.55,1.08,lead,18,True,DARK)
 t(s,12.43,7.05,.31,.2,str(n),15,False,'#DD2A29',PP_ALIGN.RIGHT)
def foot(s,v):
 rule(s,.85,6.56,11.62)
 t(s,.96,6.69,11.43,.4,v,16,True,NAVY,PP_ALIGN.CENTER)
def panel(s,x,y,w,v):
 t(s,x,y,w,.35,v,17,True,NAVY,PP_ALIGN.CENTER);rule(s,x,y+.40,w)
def exp(s,x,y,e,c=LIGHT,w=.45):
 box(s,x,y,w,.37,c);t(s,x,y+.02,w,.27,e,12,True,WHITE if c==BLUE else NAVY,PP_ALIGN.CENTER)
def pic(s,name,x,y,w):s.shapes.add_picture(str(A/(name+'.png')),Inches(x),Inches(y),width=Inches(w))

def intro(s):
 FLAT_SLIDES.add(id(s))
 base(s,1,'Research Problem: 单卡 MoE 推理的存储需求',
      'MoE 每次仅激活少数专家，但不同输入可能激活不同专家。单个推理任务可用的显存和 CPU 内存\n有限，无法容纳全部专家；当所选专家位于 SSD 时，必须读取并传输权重后才能计算。')
 # One continuous paper-style panel: route, tier residency, and upward delivery.
 box(s,.83,2.27,7.14,3.99,'#F7F9FB')
 t(s,1.04,2.39,6.72,.35,'单卡仍需支持模型中的全部专家',18,True,NAVY,PP_ALIGN.CENTER)
 rule(s,1.04,2.82,6.72)
 t(s,1.07,3.00,1.09,.31,'本次路由',15,True,NAVY)
 for j in range(8):
  x=2.25+j*.60;box(s,x,2.96,.48,.39,BLUE if j==7 else '#DCE6EF')
  t(s,x,3.04,.48,.23,f'E{j+1}',14,True,WHITE if j==7 else NAVY,PP_ALIGN.CENTER)
 t(s,1.07,3.48,6.68,.25,'蓝色 E8 为本次激活的专家；其存储位置决定读取开销。',14,False,DARK)
 tiers=[('GPU 显存',['E1','E2'],BLUE),('CPU 内存',['E3','E4','E5'],MID),('SSD',['E6','E7','E8'],GREY)]
 for i,(name,items,col) in enumerate(tiers):
  y=3.88+i*.58
  box(s,1.04,y,6.65,.47,WHITE)
  box(s,1.04,y,.085,.47,col)
  t(s,1.25,y+.08,1.56,.29,name,15,True,NAVY)
  for j,e in enumerate(items):
   x=3.01+j*.61;box(s,x,y+.07,.50,.32,BLUE if e=='E8' else '#D9E3EC')
   t(s,x,y+.12,.50,.22,e,13,True,WHITE if e=='E8' else NAVY,PP_ALIGN.CENTER)
  t(s,5.55,y+.09,1.82,.27,['直接计算','传输至显存','从 SSD 读取并传输'][i],13,False,NAVY,PP_ALIGN.RIGHT)
 box(s,1.06,5.75,6.61,.35,PALE)
 t(s,1.20,5.80,6.34,.25,'E8：从 SSD 读取 → 经 CPU 内存传输 → 在 GPU 上计算',15,True,NAVY,PP_ALIGN.CENTER)
 box(s,8.17,2.27,4.33,3.99,WHITE)
 t(s,8.27,2.39,4.12,.35,'应用场景与研究任务',18,True,NAVY,PP_ALIGN.CENTER)
 rule(s,8.27,2.82,4.12)
 for i,(a,b) in enumerate([('共享 GPU 服务器','任务仅分配一张 GPU 和部分内存'),
                           ('离线生成','问答、代码生成允许更长响应时间'),
                           ('单卡工作站','权重规模超过任务可用内存')]):
  y=2.96+i*.84
  box(s,8.31,y,4.05,.72,PALE if i==0 else LIGHT)
  box(s,8.31,y,.055,.72,BLUE)
  t(s,8.52,y+.07,3.62,.29,a,16,True,NAVY)
  t(s,8.52,y+.39,3.62,.27,b,14,False,DARK)
 t(s,8.31,5.43,4.04,.27,'MECC：MoE 专家缓存编译器',15,True,NAVY)
 t(s,8.31,5.69,4.04,.25,'MoE Expert Cache Compiler',14,False,DARK)
 t(s,8.31,5.94,4.04,.27,'初始放置 · 联合缓存 · 动态调整',14,False,DARK)
 foot(s,'研究目标：在单卡上运行完整 MoE 模型，降低专家权重读取造成的延迟。')

def bridge(s):
 FLAT_SLIDES.add(id(s))
 base(s,3,'Our Approach: MECC 的三项设计',
      '部署前统计专家的使用频率，据此确定显存和 CPU 内存中的初始专家。推理过程中根据实际路由\n更新缓存。下图依次展示三项设计如何减少 SSD 读取。')
 stages=[
  ('部署前：统计专家频率','E1–E3 使用频率较高', ['E1','E2'],['E3','E4','E5'],['E6','E7','E8'],
   'Insight I  按频率确定初始位置'),
  ('推理时：再次访问 E3','E3 从 CPU 内存进入显存',['E1','E3'],['E2','E4','E5'],['E6','E7','E8'],
   'Insight II  联合更新两级缓存'),
  ('任务变化后：更新缓存','E6–E8 使用频率上升',['E6','E7'],['E8','E3','E4'],['E1','E2','E5'],
   'Insight III  根据实际访问调整')]
 for i,(head,note,gpu,cpu,ssd,ins) in enumerate(stages):
  x=.91+i*3.92
  box(s,x,2.44,3.58,3.80,'#F7F9FB')
  box(s,x,2.44,3.58,.055,BLUE)
  t(s,x+.13,2.64,3.32,.33,head,17,True,NAVY)
  t(s,x+.14,3.03,3.30,.28,note,14,False,DARK)
  t(s,x+.14,3.35,3.30,.25,'专家当前所在的存储层级',13,False,NAVY)
  for j,(tier,items,color) in enumerate([('显存',gpu,BLUE),('CPU',cpu,MID),('SSD',ssd,GREY)]):
   y=3.75+j*.57
   box(s,x+.12,y,3.34,.46,WHITE)
   box(s,x+.12,y,.065,.46,color)
   t(s,x+.27,y+.09,.69,.26,tier,14,True,NAVY)
   for k,e in enumerate(items):
    px=x+1.10+k*.60
    focus=(i==0 and e in ['E1','E2','E3']) or (i==1 and e=='E3') or (i==2 and e in ['E6','E7','E8'])
    box(s,px,y+.065,.49,.33,BLUE if focus else '#DDE7EF')
    t(s,px,y+.11,.49,.23,e,13,True,WHITE if focus else NAVY,PP_ALIGN.CENTER)
  box(s,x+.12,5.55,3.34,.51,PALE)
  t(s,x+.20,5.68,3.18,.28,ins,14,True,NAVY,PP_ALIGN.CENTER)
  if i<2:t(s,x+3.60,4.32,.28,.38,'→',20,True,BLUE,PP_ALIGN.CENTER)
 t(s,.98,6.29,11.35,.24,'深蓝表示当前高频访问或被选中的专家；其他方块表示专家所在的存储层级。',13,False,NAVY,PP_ALIGN.CENTER)
 foot(s,'SSD 保存完整专家权重；显存与 CPU 内存缓存当前更可能访问的专家。')

def related_work(s):
 old.reference_table(s)
 headers={
  '三级存储\v支撑':'显存/内存/SSD\n三级存储',
  '完整专家\v计算':'完整专家\n计算',
  '按预算生成\v驻留方案':'按内存预算\n安排专家',
  '历史热点\v预热':'提前加载\n常用专家',
  '冷读压力\v预估':'预测 SSD\n读取需求',
  '在线适应\v热点变化':'任务变化时\n更新缓存',
 }
 for shape in list(s.shapes):
  if shape.has_text_frame and not shape.text.strip() and abs(shape.top/Inches(1)-1.06)<.01 and abs(shape.left/Inches(1)-.93)<.01:
   shape._element.getparent().remove(shape._element)
  elif shape.has_text_frame and shape.text.strip().startswith('Related Work:'):
   shape._element.getparent().remove(shape._element)
  elif shape.has_text_frame and shape.text.strip().startswith('现有系统已能'):
   shape._element.getparent().remove(shape._element)
  elif shape.has_text_frame and shape.text in headers:
   shape.text=headers[shape.text]
   for paragraph in shape.text_frame.paragraphs:
    paragraph.alignment=PP_ALIGN.CENTER
    for run in paragraph.runs:
     run.font.size=old.Pt(14);run.font.bold=True
 box(s,.76,1.10,.12,.12,BLUE)
 t(s,1.01,1.04,11.55,1.08,
   '现有方法支持跨显存、CPU 内存和 SSD 读取专家，并缓存常用专家。在共享服务器中，还需要\n根据任务的内存预算确定初始放置、提前加载常用专家，并适应任务变化。',18,True,DARK)
 t(s,.6,.1,12.1,.58,'Related Work: 现有方法与 MECC 的对比',29,True,'#111111',PP_ALIGN.CENTER)
 t(s,.81,6.52,11.85,.43,
   '表内主要比较单卡卸载方法；MoE-Lightning 也测试多卡。8 卡 FlashMoE 是分布式算子参照，不是同机单卡基线。',
   14,False,NAVY,PP_ALIGN.CENTER)

def mot_common(s,n,title,lead,l,r,img,readout,question):
 base(s,n,title,lead)
 panel(s,.83,2.28,5.62,l);panel(s,6.77,2.28,5.72,r)
 pic(s,img,.84,2.75,5.55)
 box(s,.98,5.72,5.32,.55,PALE);t(s,1.14,5.84,5.0,.30,readout,14,True,NAVY)
 foot(s,question)

def mot1(s):
 mot_common(s,4,'Motivation I: 首次访问带来的读取延迟',
     '当多卡总显存足以容纳模型时，专家可分散驻留在各卡显存，路由后传输 token 并执行。单卡的\n显存和任务内存预算有限，首次请求可能激活 HDD 上的专家。左图比较四组任务的首 token 延迟。',
     '(a) 四组任务的首 token 延迟','(b) 两种部署的专家读取路径','mot_cold_start',
     '首次访问 SSD 上的专家增加首 token 延迟。',
     '问题①：推理开始前，哪些专家应优先进入显存和 CPU 内存？')
 t(s,6.94,2.88,5.2,.30,'多卡全显存：专家分散驻留在 GPU',15,True,NAVY)
 for j in range(8):exp(s,6.96+j*.63,3.28,f'E{j+1}',BLUE if j==7 else '#DCE4EC',.51)
 t(s,7.04,3.77,4.92,.26,'选中 E8 → 跨卡传 token → 所在 GPU 执行',14,False,DARK,PP_ALIGN.CENTER)
 rule(s,6.96,4.18,5.27)
 t(s,6.94,4.32,5.2,.30,'单卡：E8 仍在 SSD',15,True,NAVY)
 for j,(name,col) in enumerate([('SSD\nE8',GREY),('CPU\n缓冲',MID),('GPU\n执行',BLUE)]):
  x=7.0+j*1.83;box(s,x,4.79,1.35,.67,col);t(s,x,4.91,1.35,.45,name,13,True,WHITE,PP_ALIGN.CENTER)
  if j<2:t(s,x+1.41,4.96,.34,.35,'→',20,True,BLUE,PP_ALIGN.CENTER)
 t(s,7.0,5.67,5.13,.55,'SSD 读取与权重传输均发生在专家计算之前。',14,True,DARK)

def mot2(s):
 FLAT_SLIDES.add(id(s))
 mot_common(s,5,'Motivation II: 重复访问导致多次 SSD 读取',
     '在多卡全显存配置中，再次访问同一专家无需读取 HDD。单卡的显存与 CPU 内存容量有限：\nE6 从 HDD 载入后可能被替换，再次访问仍需读取。左图比较不同缓存更新方式的读取比例。',
     '(a) HDD 冷层读取比例','(b) 重复访问 E6 的读取路径','mot_retention',
     '专家被缓存替换后，重复访问仍需读取 SSD。',
     '问题②：如何利用显存与 CPU 内存减少重复读取？')
 t(s,6.94,2.90,5.19,.30,'多卡全显存：专家分散驻留',15,True,NAVY)
 for j in range(8):exp(s,7.02+j*.60,3.32,f'E{j+1}',BLUE if j==5 else '#9FBBD7',.50)
 t(s,7.00,3.83,5.12,.29,'E6 → 其他专家 → E6：两次均命中显存',14,False,DARK,PP_ALIGN.CENTER)
 rule(s,6.98,4.20,5.22)
 t(s,6.94,4.35,5.19,.30,'单卡：显存与 CPU 内存容量有限',15,True,NAVY)
 t(s,7.01,4.86,.52,.25,'显存',12,True,NAVY)
 for j,e in enumerate(['E7','E8']):exp(s,7.58+j*.53,4.82,e,BLUE,.45)
 t(s,8.73,4.86,.55,.25,'CPU',12,True,NAVY)
 for j,e in enumerate(['E3','E4','E5']):exp(s,9.28+j*.53,4.82,e,MID,.45)
 t(s,10.99,4.86,.54,.25,'SSD',12,True,NAVY)
 exp(s,11.54,4.82,'E6',GREY,.45)
 t(s,7.00,5.37,5.16,.28,'读取 E6 → E6 被替换 → 再次读取 E6',14,False,DARK,PP_ALIGN.CENTER)
 t(s,7.00,5.78,5.16,.28,'固定的 CPU 缓存无法保留被替换的 E6。',13,False,DARK,PP_ALIGN.CENTER)

def mot3(s):
 FLAT_SLIDES.add(id(s))
 mot_common(s,6,'Motivation III: 任务变化引起专家访问变化',
     '多卡全显存配置在任务变化后仍可直接访问各卡专家。单卡依据先前任务安排缓存；若新任务\n频繁访问另一组专家，而缓存未及时更新，HDD 读取比例会持续升高。左图显示切换前后变化。',
     '(a) 任务切换前后的 HDD 读取比例','(b) 新任务常用专家的存储位置','mot_drift',
     '任务切换后，固定缓存仍保留旧任务的常用专家。',
     '问题③：任务变化后，如何更新显存与 CPU 内存中的专家？')
 t(s,6.94,2.90,5.22,.31,'多卡全显存：新任务专家仍在显存',15,True,NAVY)
 for j in range(8):exp(s,7.02+j*.60,3.33,f'E{j+1}',BLUE if j>=5 else '#9FBBD7',.50)
 t(s,7.02,3.82,5.07,.28,'任务 A → 任务 B：路由到 E6–E8 所在 GPU',14,False,DARK,PP_ALIGN.CENTER)
 rule(s,6.98,4.20,5.22)
 t(s,6.94,4.35,5.22,.31,'单卡：缓存仍保留旧任务的常用专家',15,True,NAVY)
 t(s,7.02,4.86,.52,.25,'显存',12,True,NAVY)
 for j,e in enumerate(['E1','E2']):exp(s,7.58+j*.53,4.82,e,BLUE,.45)
 t(s,8.73,4.86,.55,.25,'CPU',12,True,NAVY)
 for j,e in enumerate(['E3','E4','E5']):exp(s,9.28+j*.53,4.82,e,MID,.45)
 t(s,10.99,4.86,.54,.25,'SSD',12,True,NAVY)
 for j,e in enumerate(['E6','E7','E8']):exp(s,11.54+j*.29,4.82,e,GREY,.27)
 t(s,7.02,5.38,5.07,.29,'任务 B 频繁访问 E6–E8，却仍需从 SSD 读取。',14,False,DARK,PP_ALIGN.CENTER)
 t(s,7.02,5.79,5.07,.27,'常用专家已改变，但缓存内容没有更新。',13,False,DARK,PP_ALIGN.CENTER)

def insight(s,n,title,lead,left_title,right_title):
 FLAT_SLIDES.add(id(s))
 old.clear(s)
 t(s,.6,.1,12.1,.58,title,29,True,'#111111',PP_ALIGN.CENTER)
 box(s,.81,1.14,.11,.11,BLUE)
 t(s,1.06,1.07,11.45,1.02,lead,18,False,DARK)
 t(s,.79,2.19,5.72,.35,left_title,16,True,NAVY)
 t(s,6.82,2.19,5.72,.35,right_title,16,True,NAVY)
 s.shapes.add_picture(str(pairs.OUT/(f'pair{n}_mechanism.png')),
                      Inches(.74),Inches(2.56),width=Inches(5.85))
 s.shapes.add_picture(str(pairs.OUT/(f'pair{n}_ablation.png')),
                      Inches(6.74),Inches(2.56),width=Inches(5.85))
 t(s,12.43,7.05,.31,.20,str(n),15,False,'#DD2A29',PP_ALIGN.RIGHT)

def ins1(s):
 insight(s,7,'Insight I: 按专家访问频率确定初始位置',
     '用代表性输入运行模型，统计每一层各专家被激活的次数。部署时分别对每层专家排序，\n在显存和 CPU 内存预算内优先缓存高频专家，其余权重保存在 SSD。',
     '设计示意：分别统计每层专家','消融实验：比较不同初始放置方法')

def ins2(s):
 insight(s,8,'Insight II: 显存与 CPU 内存联合更新缓存',
     '从 CPU 内存访问专家时，将其传输至显存；被替换的显存专家则保留在 CPU 内存中。\n这样可以同时更新两级缓存，降低再次访问该专家时读取 SSD 的概率。',
     '设计示意：一次访问更新两级缓存','消融实验：比较不同缓存更新方法')

def ins3(s):
 insight(s,9,'Insight III: 根据实际访问调整专家缓存',
     '部署前的统计结果用于确定初始位置；推理时根据实际访问更新显存和 CPU 内存的缓存顺序。\n任务变化后，新任务频繁访问的专家逐步进入缓存，从而减少后续 SSD 读取。',
     '设计示意：根据实际访问更新缓存','消融实验：比较任务变化后的表现')
def overview(s):
 base(s,10,'System Overview: MECC 系统总览',
     'MECC 在部署前确定专家的初始位置，在推理时根据实际路由访问并更新缓存。SSD 保存完整的\n专家权重；显存和 CPU 内存只缓存部分专家。所选专家的权重到达显存后执行计算。')
 # Use the exact overview figure referenced by the paper's Overview section.
 figure=P/'figures'/'fig01_overview.png'
 s.shapes.add_picture(str(figure),Inches(.72),Inches(2.35),width=Inches(11.9))
 foot(s,'部署前确定初始位置；推理时根据路由访问和更新缓存。')

def method1(s):
 base(s,11,'Method I: 确定专家的初始存储位置',
     '部署前使用代表性输入统计每层专家的访问频率，并记录权重大小及任务的内存预算。\n编译器按层排序，在显存和 CPU 内存预算内确定初始位置；SSD 保存完整权重。')
 s.shapes.add_picture(str(method_figures.OUT/'method1_placement.png'),
                      Inches(.72),Inches(2.39),width=Inches(11.9))
 foot(s,'编译结果记录各层的缓存容量和专家编号；推理时继续根据实际请求更新缓存。')

def method2(s):
 base(s,12,'Method II: 更新缓存并执行专家计算',
     '推理时先根据路由查找所选专家。CPU 内存命中时将专家传输到显存，并把被替换的专家\n保留在 CPU 内存；访问 SSD 时，等待权重到达显存后再执行计算。')
 s.shapes.add_picture(str(method_figures.OUT/'method2_delivery.png'),
                      Inches(.72),Inches(2.39),width=Inches(11.9))
 foot(s,'两级缓存更新减少重复读取；已在显存的专家可先计算，其他专家在权重到达后计算。')

def result(s,n,title,lead,img,caption):
 base(s,n,title,lead)
 pic(s,img,.84,2.35,11.62)
 box(s,.96,6.05,11.38,.41,PALE);t(s,1.10,6.12,11.05,.27,caption,14,True,NAVY,PP_ALIGN.CENTER)

def conclusion(s):
 base(s,17,'Conclusion: 单卡运行完整 MoE 模型',
     '当任务可用的 CPU 内存无法容纳全部专家时，部分权重需要保存在 SSD。MECC 依据访问频率\n确定初始位置，联合更新显存和 CPU 内存缓存，并根据实际请求调整，以减少 SSD 读取。')
 for i,(a,b,c) in enumerate([('初始放置','优先缓存高频专家','减少首次读取'),('缓存更新','联合使用显存与 CPU 内存','减少重复读取'),('动态调整','根据实际访问更新缓存','适应任务变化')]):
  x=.98+i*4.12;box(s,x,2.62,3.74,.06,BLUE);t(s,x,2.94,3.74,.45,a,22,True,NAVY,PP_ALIGN.CENTER)
  t(s,x,3.69,3.74,.45,b,17,False,DARK,PP_ALIGN.CENTER)
  box(s,x+.29,4.51,3.16,.61,PALE);t(s,x+.35,4.66,3.04,.31,c,16,True,NAVY,PP_ALIGN.CENTER)
 foot(s,'面向单卡、有限任务内存预算下的完整 MoE 推理。')

def main():
 old.charts();pairs.build();method_figures.placement();method_figures.delivery()
 prs=Presentation(old.SOURCE)
 intro(prs.slides[0]);related_work(prs.slides[1]);bridge(prs.slides[2])
 mot1(prs.slides[3]);mot2(prs.slides[4]);mot3(prs.slides[5])
 ins1(prs.slides[6]);ins2(prs.slides[7]);ins3(prs.slides[8])
 overview(prs.slides[9]);method1(prs.slides[10]);method2(prs.slides[11])
 result(prs.slides[12],13,'Results: 单卡解码延迟',
   '左图比较四组模型与任务中，未优化单卡方案、SSD 缓存方案和 MECC 的每 token 解码延迟。\n右图给出 MECC 相对 SSD 缓存方案的加速比。',
   'main','同一任务内存额度下，MECC 与 SSD 缓存基线相差 1.25–1.42×。')
 result(prs.slides[13],14,'Ablation: 各项设计的效果',
   '从基础方案开始，依次加入初始放置、两级缓存更新和计算与传输重叠。左图比较解码延迟，\n右图比较 SSD 读取比例，以区分各项设计对读取次数和等待时间的影响。',
   'ablation','首组任务：24 → 18 → 11 → 8 秒/token；SSD 请求比例：46% → 33% → 20%。')
 result(prs.slides.add_slide(prs.slide_layouts[6]),15,'Resource Sensitivity: CPU 内存与生成长度',
   '任务可用的 CPU 内存越大，可缓存的专家越多。生成的 token 越多，初始加载开销对平均延迟的\n影响越小。两张图分别改变 CPU 内存预算和生成长度。',
   'resources','单卡推理性能受到 CPU 内存预算和生成长度共同影响。')
 result(prs.slides.add_slide(prs.slide_layouts[6]),16,'Deployment Trade-off: 单卡与多卡部署',
   '在总显存足以容纳模型的多卡配置中，专家分散驻留于 GPU，因此单 token 延迟更低；MECC 使用\n一张 GPU 运行完整模型。右图以 GPU 数量乘以延迟，比较两种部署的 GPU 资源开销。',
   'allocation','单卡方案适用于 GPU 数量受限、可以接受较长推理延迟的任务。')
 conclusion(prs.slides.add_slide(prs.slide_layouts[6]))
 for slide in prs.slides:
  slide.notes_slide.notes_text_frame.text=''
  for shape in slide.shapes:
   frames=[]
   if shape.has_text_frame:frames.append(shape.text_frame)
   if shape.has_table:frames.extend(cell.text_frame for row in shape.table.rows for cell in row.cells)
   for frame in frames:
    for paragraph in frame.paragraphs:
     for run in paragraph.runs:
      run.text=display_text(run.text)
      run.font.name='Times New Roman'
      rpr=run._r.get_or_add_rPr()
      ea=rpr.find(qn('a:ea'))
      if ea is None:
       ea=OxmlElement('a:ea');rpr.append(ea)
      ea.set('typeface','SimSun')
 prs.core_properties.title='MECC: Single-GPU MoE Inference';prs.core_properties.subject='Internal ideal-results research talk'
 prs.core_properties.author='';prs.core_properties.last_modified_by=''
 OUT.parent.mkdir(exist_ok=True)
 prs.save(OUT);print('Saved',OUT,'slides',len(prs.slides))

if __name__=='__main__':main()
