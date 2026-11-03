"""Explicitly hypothetical ideal-result storyboard. Never writes to results/."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.dml.color import RGBColor

import build_mecc_conference_talk as base
import build_mecc_hpca_revision as revision
from build_mecc_first3 import BLACK, BLUE_DARK, BLUE_MID, BLUE_LIGHT, GRAY_MID, GRAY_LIGHT, WHITE, rect

HERE=Path(__file__).resolve().parent
BLUE,GREY,ORANGE=base.BLUE,base.GREY,base.ORANGE
DISCLAIMER='理想情景预演 · 所有实验结果均为假设'


def save(fig,assets,name):
    fig.text(.985,.985,'假设结果 · 非实测',ha='right',va='top',fontsize=11,
             color=ORANGE,bbox=dict(facecolor='#FFF4E7',edgecolor='none',pad=3))
    fig.savefig(assets/f'{name}.png',dpi=240)
    fig.savefig(assets/f'{name}.pdf'); plt.close(fig)


def ax1():
    fig,ax=plt.subplots(figsize=(6.2,3.6))
    fig.subplots_adjust(left=.15,bottom=.22,right=.97,top=.82)
    return fig,ax


def plots(assets):
    assets.mkdir(parents=True,exist_ok=True); base.configure()
    data={
        'status':'HYPOTHETICAL_IDEAL_SCENARIO_NOT_MEASURED',
        'notice':'Every numeric experimental outcome, including baselines, is an invented scenario assumption, not an empirical result or forecast.',
        'layer_io':{'uniform':[.4,.5,2.3,3.0],'planned':[.6,.7,1.1,1.3],
                    'uniform_cpu_slots':[4,4,4,4],'planned_cpu_slots':[2,3,5,6]},
        'retention':{'ssd_pct':[28,18,9],'policies':['固定CPU','独立LRU','联合保留']},
        'reuse_cdf_pct':[8,18,36,52,68,79,86,91,94,96,97,98,99,99,100,100],
        'drift':{'fixed':[12,12,11,12,11,12,12,12,34,37,36,35,36,35,36,35],
                 'lru':[25,21,18,16,15,14,14,14,31,26,22,19,17,16,15,14],
                 'mecc':[7,7,6,6,6,6,6,6,20,13,9,7,7,7,7,7]},
        'main':{'workloads':['问答','代码','长上下文','阶段切换'],
                'tpot_s':{'三级LRU':[8.7,10.5,11.4,13.0],
                          'RF替换':[7.2,8.6,9.3,11.2],
                          'CORE式协同':[6.4,7.6,8.2,9.9],
                          'MECC':[3.8,4.3,4.6,5.2]}},
        'ablation':{'names':['均匀+固定','仅预算计划','仅联合保留','完整MECC'],
                    'relative':[1.,1.25,1.56,2.12],'ssd_pct':[29,22,16,8]},
        'net_cost':{'output_tokens':[0,1,2,4,8,16,32,64],
                    'baseline_s':[12,20,28,44,76,140,268,524],
                    'mecc_including_setup_s':[30,34.5,39,48,66,102,174,318]},
        'resources':{'hbm_gb':{'专家':42,'主干':10,'KV/激活':14,'缓冲':4},
                     'cpu_gb':{'专家驻留':28,'镜像':6,'staging':4,'其他':2}},
        'assumed_validation':{'same_checkpoint':True,'same_precision':'fp16',
                               'actual_host_cap_gb':40,'actual_hbm_cap_gb':80,
                               'quality_equivalence':'assumed passed',
                               'strong_baselines':'assumed matched-mode comparisons passed',
                               'prefetch_fairness':'assumed equal settings',
                               'disjoint_profiling_and_evaluation':'assumed',
                               'statistical_repetitions':'assumed, not performed'},
    }
    main=data['main']['tpot_s']; best=np.array(main['CORE式协同']); ours=np.array(main['MECC'])
    gain=float(np.exp(np.log(best/ours).mean()))
    data['derived']={'geomean_speedup_vs_best_assumed_baseline':gain,
                     'layer_io_reduction_pct':100*(1-sum(data['layer_io']['planned'])/sum(data['layer_io']['uniform'])),
                     'ssd_reduction_pct':100*(1-8/29),'net_break_even_output_tokens':18/(8-4.5),
                     'hbm_peak_gb':sum(data['resources']['hbm_gb'].values()),
                     'cpu_peak_gb':sum(data['resources']['cpu_gb'].values())}
    (assets/'assumptions.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    fig,ax=ax1(); xs=np.arange(4)
    for name,off,color in [('uniform',-.18,GREY),('planned',.18,BLUE)]:
        bars=ax.bar(xs+off,data['layer_io'][name],.31,color=color,label='均匀分配' if name=='uniform' else '预算计划')
        ax.bar_label(bars,padding=4,fontsize=11)
    base.style(ax,'SSD 读取量（GB / token）↓'); ax.set_xticks(xs,['层组1','层组2','层组3','层组4'])
    ax.set_ylim(0,4.2); ax.legend(ncol=2,loc='upper left',fontsize=12)
    save(fig,assets,'mot_layer')
    fig,ax=ax1(); bars=ax.bar(range(3),data['retention']['ssd_pct'],.55,color=[GREY,'#91B2D0',BLUE])
    ax.bar_label(bars,labels=['28%','18%','9%'],padding=6,fontsize=14)
    base.style(ax,'SSD 访问比例（%）↓'); ax.set_xticks(range(3),data['retention']['policies']); ax.set_ylim(0,38)
    save(fig,assets,'mot_retain')
    fig,ax=ax1(); ax.axvspan(1.5,5.5,color='#E5F0FB')
    ax.plot(range(16),data['reuse_cdf_pct'],color=BLUE,marker='o',markevery=2,lw=2.4)
    ax.axvline(5.5,color=BLUE,ls=':',lw=1.3); ax.text(3.5,20,'CPU 可承接\n的再访区间',ha='center',fontsize=12,color=BLUE)
    base.style(ax,'再访累计比例（%）'); ax.set(xlabel='再访前出现的不同专家数',ylim=(0,105),xlim=(0,15))
    ax.set_xticks([0,2,4,6,8,12,15]); save(fig,assets,'mot_reuse')
    fig,ax=ax1(); ax.axvspan(8.5,16.4,color='#F1F5FA')
    for key,lab,color,marker in [('fixed','画像固定',GREY,'s'),('lru','仅在线LRU','#83A4C5','d'),('mecc','先验+在线',BLUE,'o')]:
        ax.plot(range(1,17),data['drift'][key],lw=2.2,marker=marker,markevery=2,color=color,label=lab)
    ax.axvline(8.5,color=ORANGE,ls='--',lw=1); ax.text(8.9,44,'阶段切换',color=ORANGE,fontsize=12)
    base.style(ax,'SSD 访问比例（%）↓'); ax.set(xlabel='连续请求时间窗',ylim=(0,55),xlim=(.7,16.3))
    ax.set_xticks([1,4,8,12,16]); ax.legend(ncol=3,loc='upper left',fontsize=10.5,columnspacing=.8)
    save(fig,assets,'mot_drift')
    fig,ax=plt.subplots(figsize=(12,3.65)); fig.subplots_adjust(left=.08,bottom=.22,right=.98,top=.81)
    xx=np.arange(4)
    for j,(name,color) in enumerate(zip(main,[GREY,'#BACBDD','#82A8CD',BLUE])):
        vals=best/np.array(main[name]); bars=ax.bar(xx+(j-1.5)*.18,vals,.17,color=color,label=name)
        if name=='MECC': ax.bar_label(bars,labels=[f'{v:.2f}×' for v in vals],fontsize=13,padding=5,weight='bold')
    base.style(ax,'相对最佳对照的解码性能 ↑'); ax.set_xticks(xx,data['main']['workloads']); ax.set_ylim(0,2.55)
    ax.axhline(1,color='#66717D',ls=':',lw=1); ax.legend(ncol=4,fontsize=12,loc='upper left')
    save(fig,assets,'main')
    fig,axs=plt.subplots(1,2,figsize=(12,3.65)); fig.subplots_adjust(left=.07,bottom=.23,right=.98,top=.80,wspace=.32)
    a=data['ablation']; colors=[GREY,'#BBCFE1','#7FA6CB',BLUE]
    for ax,vals,ylabel,title in [(axs[0],a['relative'],'相对综合性能 ↑','(a) 组件对性能的贡献'),(axs[1],a['ssd_pct'],'SSD 访问比例（%）↓','(b) 冷读压力随组件组合下降')]:
        bars=ax.bar(range(4),vals,.55,color=colors)
        ax.bar_label(bars,labels=[f'{v:.2f}×' for v in vals] if ax is axs[0] else [f'{v}%' for v in vals],padding=5,fontsize=12)
        base.style(ax,ylabel); ax.set_xticks(range(4),['均匀+固定','仅计划','仅联合','完整方案']); ax.set_title(title,pad=12)
    axs[0].set_ylim(0,2.6); axs[1].set_ylim(0,39); save(fig,assets,'ablation')
    fig,axs=plt.subplots(1,2,figsize=(12,3.65)); fig.subplots_adjust(left=.08,bottom=.23,right=.98,top=.80,wspace=.32)
    d=data['net_cost']; ax=axs[0]
    for key,lab,color,marker in [('baseline_s','最佳对照',GREY,'s'),('mecc_including_setup_s','MECC（含初始化）',BLUE,'o')]:
        ax.plot(d['output_tokens'],d[key],label=lab,color=color,marker=marker,ms=5,lw=2.2)
    base.style(ax,'含初始化的累计时间（s）↓'); ax.set(xlabel='生成 token 数',ylim=(0,570),xlim=(-1,65)); ax.legend(fontsize=11,loc='upper left')
    ax.set_title('(a) 画像与预热成本计入净收益',pad=12)
    ax=axs[1]; ax.axhline(80,color=GREY,ls=':',lw=1); ax.axhline(40,color=GREY,ls=':',lw=1)
    bottoms=[0,0]
    for j,(name,color) in enumerate(zip(['专家与副本','主干与KV','临时缓冲','其他'],[BLUE,'#89A9C9','#BDCFDF','#E0E7EF'])):
        vals=[[42,24,4,0][j],[34,0,4,2][j]]
        ax.bar([0,1],vals,.50,bottom=bottoms,color=color,label=name)
        bottoms=[a+b for a,b in zip(bottoms,vals)]
    ax.text(0,73,'70 / 80 GB',ha='center',fontsize=12,weight='bold'); ax.text(1,43,'40 / 40 GB',ha='center',fontsize=12,weight='bold')
    base.style(ax,'实际峰值驻留（GB）'); ax.set_xticks([0,1],['HBM','CPU']); ax.set_ylim(0,115)
    ax.set_title('(b) 副本与临时缓冲计入物理预算',pad=12); ax.legend(ncol=2,fontsize=10,loc='upper left')
    save(fig,assets,'net')
    fig=plt.figure(figsize=(6.4,.55))
    fig.text(.5,.5,r'$\mathbb{E}[T]=p_H T_H+p_C T_C+p_S T_S$',ha='center',va='center',fontsize=24,color=base.INK)
    fig.savefig(assets/'cost_equation.png',dpi=240); fig.savefig(assets/'cost_equation.pdf'); plt.close(fig)
    return data


def panel(s,assets,title,body,left,right,lefttitle,righttitle,takeaway):
    base.head(s,title,body); base.panel(s,.89,lefttitle); base.panel(s,6.89,righttitle)
    base.pic(s,assets,left,.77,3.12,5.77)
    if right: base.pic(s,assets,right,6.77,3.12,5.77)
    base.footer(s,takeaway)


def title(s,text):
    s.shapes.title.text=text


def body(s,text): revision.replace_body(s,text)


def bottom(s,text):
    for shape in list(s.shapes):
        if shape.has_text_frame and 6.45<shape.top/Inches(1)<6.8:
            shape._element.getparent().remove(shape._element)
    base.footer(s,text)


def build(template,out):
    assets=out.parent/'ideal_scenario_assets'; d=plots(assets)
    base.old.build(template,out); prs=Presentation(out)
    prs.slides.add_slide(prs.slide_layouts[5])
    revision.related(prs.slides[1]); title(prs.slides[1],'Related Work: Budgeted Expert Serving')
    body(prs.slides[1],'已有系统分别优化专家执行、缓存替换、压缩与调度。\nMECC 将预算计划与在线保留协同起来，面向工作集超过快层容量的完整专家推理。')
    bottom(prs.slides[1],'本文目标：在同实际内存预算下，联合降低初始冷读与持续推理代价。')
    revision.overview_contribution(prs.slides[2]); title(prs.slides[2],'MECC: Planned Placement + Online Retention')
    body(prs.slides[2],'MECC 用预算计划减少启动阶段的昂贵读取，用显存与 CPU 联合保留延续专家复用。\n两种时间尺度协同，在相同实际资源与完整 fp16 专家执行下取得稳定的端到端收益。')
    bottom(prs.slides[2],f'预算计划 × 联合保留：相对最强对照获得 {d["derived"]["geomean_speedup_vs_best_assumed_baseline"]:.2f}× 几何平均解码性能。')
    reduction=d['derived']['layer_io_reduction_pct']
    panel(prs.slides[3],assets,'Motivation I: Layer-Wise Capacity Mismatch',
          f'相同总容量下，均匀分配让高压力层持续访问 SSD；按层间需求重分配后，总读取量下降 {reduction:.0f}%。\n'
          '增加一个缓存槽位在不同层能避免的冷读不同，容量应该流向边际收益更高的位置。',
          'mot_layer',None,'(a) 同总容量下的逐层冷读','(b) 相同槽位数，不同层间分配',
          '动机 ①：容量应按可避免的冷读代价分配，而不是按层平均切分。')
    s=prs.slides[3]
    for row,(lab,slots) in enumerate([('均匀分配',[4,4,4,4]),('预算计划',[2,3,5,6])]):
        y=3.57+row*1.23; base.old.t(s,6.98,y,1.15,.37,lab,14,BLUE_DARK)
        for group,count in enumerate(slots):
            x=8.36+group*.94
            for k in range(count): rect(s,x,y+.64-k*.075,.63,.055,fill=BLUE_MID if row else GRAY_MID,line=WHITE)
            base.old.t(s,x-.03,y+.76,.71,.27,f'L{group+1}: {count}',11,BLUE_DARK)
    base.old.t(s,7.55,6.10,4.24,.28,'两种方案均为 16 槽；仅改变分配位置',12,BLACK,False)
    panel(prs.slides[4],assets,'Motivation II: Reuse Beyond HBM Eviction',
          '显存淘汰后的专家仍可能在短距离内再访；固定 CPU 集合和独立缓存未能完整承接这些请求。\n'
          '联合保留把 SSD 访问从 28% 降至 9%，再访距离分析表明大部分机会位于 CPU 可覆盖区间。',
          'mot_retain','mot_reuse','(a) 同容量、同初态的保留规则比较','(b) 显存淘汰后的再访机会',
          '动机 ②：一次显存淘汰不应终止复用，CPU 应继续保留近期工作集。')
    panel(prs.slides[5],assets,'Motivation III: Complementary Time Scales',
          '画像固定方案启动快，却在阶段切换后失配；纯在线 LRU 可以适应，但启动段承担更多冷读。\n'
          '先验与在线结合后同时降低启动和恢复代价，表明两者解决的是不同时间尺度的问题。',
          'mot_drift',None,'(a) 启动与阶段切换下的冷读压力','(b) 初始覆盖与在线纠偏',
          '动机 ③：用先验缩短启动，用反馈跟随变化。')
    s=prs.slides[5]
    for col in range(8): base.old.t(s,8.16+col*.48,3.52,.41,.29,f'E{col+1}',10,BLUE_DARK)
    for row,(lab,hot) in enumerate([('先验覆盖',[0,1,2]),('新阶段热点',[3,4,5]),('在线保留',[3,4,5])]):
        y=4.03+row*.62; base.old.t(s,6.96,y,1.13,.35,lab,13,BLUE_DARK)
        for col in range(8): rect(s,8.16+col*.48,y,.39,.32,fill=BLUE_MID if col in hot else GRAY_LIGHT,line=WHITE)
    base.old.t(s,7.44,6.12,4.66,.28,'初态来自画像，后续位置由真实请求更新',12,BLUE_DARK,False)
    title(prs.slides[6],'Insight I: Spend Capacity Where It Saves I/O')
    body(prs.slides[6],'将访问概率、层级取数代价与实际缓存预算放在同一目标中，优先保护高代价请求。\n编译器按层间边际收益安排容量，并输出专家初始驻留与预期冷读压力。')
    bottom(prs.slides[6],'洞察 ①：把“可避免的冷读代价”作为容量分配的共同尺度。')
    title(prs.slides[7],'Insight II: Retain Reuse Across Tiers')
    body(prs.slides[7],'显存与 CPU 组成联合工作集：显存淘汰降级到 CPU，再访命中后提升到显存。\n以实际物理字节约束全部权重、副本与缓冲，扩大有效覆盖并控制迁移成本。')
    bottom(prs.slides[7],'洞察 ②：跨层保留延续专家复用，统一记账确保收益来自策略。')
    base.insight3(prs.slides[8],assets); title(prs.slides[8],'Insight III: Optimize Two Time Scales')
    body(prs.slides[8],'编译期利用跨请求可复用的先验，运行期根据实际访问纠正画像偏差。\n在有限服务时域内共同优化初始化、传输与执行，使先验收益持续转化为推理收益。')
    bottom(prs.slides[8],'洞察 ③：先验决定起点，反馈保留真实热点。')
    base.overview(prs.slides[9],assets)
    title(prs.slides[10],'Method I: Budget-Aware Expert Placement')
    body(prs.slides[10],'独立路由画像给出专家访问概率，硬件标定给出取数代价，规划器据此安排三级驻留。\n在实际 HBM/CPU 预算内，输出逐层容量、初始位置、预热顺序与冷读压力估计。')
    for shape in list(prs.slides[10].shapes):
        if shape.has_text_frame and shape.text.startswith('优化目标'):
            shape._element.getparent().remove(shape._element)
    base.old.t(prs.slides[10],1.00,6.48,4.96,.40,'优化目标：最小化预期取数代价',16,BLUE_DARK)
    base.pic(prs.slides[10],assets,'cost_equation',6.20,6.44,5.64)
    base.dynamic_method(prs.slides[11],assets); title(prs.slides[11],'Method II: Budget-Bounded Joint Retention')
    base.head(prs.slides[12],'Evaluation I: End-to-End Performance',
              f'同模型权重、同 fp16、同实际内存上限下，MECC 在四类负载中均取得更低解码延迟。\n'
              f'相对每个负载的最强对照，几何平均解码性能为 {d["derived"]["geomean_speedup_vs_best_assumed_baseline"]:.2f}×，最高为 {max(np.array(d["main"]["tpot_s"]["CORE式协同"])/np.array(d["main"]["tpot_s"]["MECC"])):.2f}×。')
    base.pic(prs.slides[12],assets,'main',.89,2.65,11.52)
    base.footer(prs.slides[12],'同资源预算的端到端提升，覆盖不同请求结构与阶段变化。')
    base.head(prs.slides[13],'Evaluation II: Where the Gains Come From',
              '单变量消融显示：预算计划改善初始位置，联合保留改善后续复用，两者组合获得最大净收益。\n'
              '综合性能与 SSD 读取同步改善，连接了设计决策、缓存行为和端到端结果。')
    base.pic(prs.slides[13],assets,'ablation',.89,2.65,11.52)
    base.footer(prs.slides[13],'画像计划与在线保留各有独立贡献，组合后减少更多高代价冷读。')
    base.head(prs.slides[14],'Evaluation III: Net Benefit Within Budget',
              '计入画像、编译与预热后，MECC 从第 6 个输出 token 起获得净收益。\n'
              'HBM 峰值 70/80 GB、CPU 峰值 40/40 GB；副本与缓冲全部计费，fp16 输出等价检查通过。')
    base.pic(prs.slides[14],assets,'net',.89,2.65,11.52)
    base.footer(prs.slides[14],'MECC：在真实预算内，用编译期先验与运行期反馈降低完整推理代价。')
    for owner in list(prs.slide_layouts)+list(prs.slide_masters):
        for shape in list(owner.shapes):
            if shape.is_placeholder and shape.placeholder_format.type==PP_PLACEHOLDER.SLIDE_NUMBER:
                shape._element.getparent().remove(shape._element)
    for index,s in enumerate(prs.slides,1):
        for shape in s.shapes:
            if shape.has_text_frame and shape.text in ('K_H','K_H+K_C'):
                label=shape.text; p=shape.text_frame.paragraphs[0]; p.clear()
                tokens=[('K',False),('H',True)]
                if '+' in label: tokens += [('+K',False),('C',True)]
                for text,sub in tokens:
                    r=p.add_run(); r.text=text; r.font.name='Cambria Math'
                    r.font.size=Pt(12 if sub else 15); r.font.color.rgb=BLUE_DARK
                    if sub: r._r.get_or_add_rPr().set('baseline','-25000')
        for p in s.shapes.title.text_frame.paragraphs:
            p.alignment=PP_ALIGN.CENTER
            for r in p.runs: r.font.name='Microsoft YaHei'; r.font.size=Pt(29); r.font.bold=True
        for shape in list(s.shapes):
            is_number=(shape.is_placeholder and shape.placeholder_format.type==PP_PLACEHOLDER.SLIDE_NUMBER)
            if is_number or (shape.has_text_frame and shape.top/Inches(1)>6.60 and shape.text.strip().isdigit()):
                shape._element.getparent().remove(shape._element)
        base.old.t(s,.98,7.04,9.90,.24,DISCLAIMER,10.5,RGBColor.from_string(ORANGE[1:]),False,PP_ALIGN.LEFT)
        base.old.t(s,12.23,7.02,.48,.30,str(index),17,base.old.RED,False)
        s.notes_slide.notes_text_frame.text=(
            f'理想情景预演，第{index}页。所有实验数值、比较结果、质量检查、预算检查与成本回收均是假设，'
            '没有对应真机实验，不可当作论文结果引用。\n该版用于预演“如果实验全部达到理想状态”时的完整叙事。'
            '\n数据清单：ideal_scenario_assets/assumptions.json；不得放入 results/ 或 PROVENANCE 的 verified 表。'
            '\n实际研究状态请看 MECC_HPCA_review_revision.pptx 与 docs/HPCA_REVIEW_AND_REVISION.md。'
            '\n外部系统名称与机制事实参见审稿修订版文献表；本版 RF/CORE式对照的所有性能数字为虚构情景。')
    prs.core_properties.title='MECC — Ideal Scenario Storyboard (Hypothetical Results)'
    prs.core_properties.subject='All experimental outcomes are hypothetical; not research evidence'
    prs.core_properties.author=''; prs.core_properties.last_modified_by=''
    prs.core_properties.keywords='HYPOTHETICAL, NOT MEASURED, storyboard, MECC'
    revision.prune_unused_images(prs); prs.save(out)


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--template',type=Path,default=Path('C:/Users/zhaoy/Desktop/1013.pptx'))
    p.add_argument('--out',type=Path,default=HERE/'MECC_ideal_scenario.pptx'); a=p.parse_args(); build(a.template,a.out)
