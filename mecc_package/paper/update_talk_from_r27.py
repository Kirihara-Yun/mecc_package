"""Synchronize the group-meeting figures with the R27 paper, retaining data notes."""
from pathlib import Path
from collections import Counter
from copy import deepcopy
import hashlib,json,re,shutil
import pymupdf as fitz
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
from pptx.oxml.xmlchemy import OxmlElement
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import refine_hpca_talk as r

HERE=Path(__file__).resolve().parent
PAPER=HERE/'dac2027/reviews/hpca_20261106/r27_savings_bars'
OUT=HERE/'talk_updates/20261108_r27'
ASSETS=OUT/'assets'
CURRENT=HERE/'current'
SOURCE=CURRENT/'MECC_HPCA_current.pptx'
NAME='MECC_group_meeting_R27_20261108'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def body_audit():
    d=fitz.open(PAPER/'manuscript.pdf')
    patterns=[r'\b(?:hypothetical|unmeasured|authored|placeholder|synthetic|simulator)\b',
              r'\b(?:illustrative|design)\s+(?:targets?|data|results?)\b',
              r'\bnot\s+(?:for\s+submission|(?:completed\s+)?benchmark\s+measurements?|executions?)\b',
              r'\b(?:AI[- ]assisted|AI[- ]generated|to measure|to verify)\b']
    regex=re.compile('|'.join(patterns),re.I);body=[];appendix=[]
    for i,p in enumerate(d):
        for ln in p.get_text().splitlines():
            if regex.search(ln):(body if i<7 else appendix).append({'page':i+1,'text':ln})
    assert len(d)==8 and not body,body
    assert appendix and all(x['page']==8 for x in appendix)
    src=(PAPER/'manuscript.tex').read_text(encoding='utf-8')
    audit={'paper':str(PAPER/'manuscript.pdf'),'paper_sha256':sha(PAPER/'manuscript.pdf'),
           'checked_pages':[1,2,3,4,5,6,7],'data_nature_explanations_in_main_pages':body,
           'appendix_disclosure_matches':appendix,'main_highlight_commands':src[:src.index(r'\appendices')].count(r'\pending{'),
           'excluded_normal_terms':['illustrates an allocation mechanism','pending HDD/I/O read'],
           'paper_modified':False,'status':'PASS'}
    (OUT/'PAPER_BODY_AUDIT.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def clean_figure(rel,name):
    d=fitz.open(PAPER/rel);p=d[0];before=Counter(p.get_text().split())
    rects=[v['rect'] for v in p.get_drawings() if tuple(round(c,2) for c in (v.get('fill') or ()))==(1.0,.95,.6)]
    for rect in rects:p.add_redact_annot(rect,fill=False,cross_out=False)
    if rects:p.apply_redactions(images=0,graphics=1,text=1)
    assert Counter(p.get_text().split())==before,name
    assert not any(tuple(round(c,2) for c in (v.get('fill') or ()))==(1.0,.95,.6) for v in p.get_drawings())
    d.save(ASSETS/(name+'.pdf'))
    p.get_pixmap(matrix=fitz.Matrix(5,5),alpha=False).save(ASSETS/(name+'.png'))
    entry={'source':rel,'source_sha256':sha(PAPER/rel),'removed_yellow_rectangles':len(rects),
           'figure_text_unchanged':True,'display_png_sha256':sha(ASSETS/(name+'.png'))}
    d.close();return entry

def retention():
    data=json.loads((PAPER/'INTRO_FIGURE_DATA.json').read_text());rows=data['rows']
    values=[0,rows[1]['shares_hbm_cpu_hdd'][2],rows[2]['shares_hbm_cpu_hdd'][2],rows[3]['shares_hbm_cpu_hdd'][2]]
    plt.rcParams.update({'font.family':['Times New Roman','SimSun'],'font.size':11,'pdf.fonttype':42,'axes.unicode_minus':False})
    fig,ax=plt.subplots(figsize=(5.7,2.9));fig.subplots_adjust(left=.30,right=.94,bottom=.22,top=.94)
    bars=ax.barh(range(4),values,height=.58,color=['#A8B3BD','#BD8547','#6D9FAD','#326C9B'],edgecolor='#203244',linewidth=.55)
    for b,h in zip(bars,['//','\\\\','..','xxx']):b.set_hatch(h)
    ax.set_yticks(range(4),['多卡全显存','单卡固定 CPU','单卡独立缓存','单卡 MECC']);ax.invert_yaxis();ax.set_xlim(0,60)
    ax.bar_label(bars,labels=[f'{v:.1f}%' if v else '0%' for v in values],padding=4,fontsize=10.5)
    ax.set_xlabel('HDD 访问比例（%）',fontsize=11);ax.grid(axis='x',color='#E5EAF0',linewidth=.5);ax.set_axisbelow(True)
    ax.spines[['top','right','left']].set_visible(False);ax.tick_params(axis='y',length=0,pad=5)
    fig.savefig(ASSETS/'retention.png',dpi=300,bbox_inches='tight',pad_inches=.025);plt.close(fig)
    return {'source':'INTRO_FIGURE_DATA.json','values_percent':values,'zero_reference':'structural full-HBM reference, not a measured multi-GPU run'}

def matched():
    x=json.loads((PAPER/'EXPERIMENT_TARGETS.json').read_text())['matched_policy_paths'];names=x['names']
    fig,axs=plt.subplots(1,2,figsize=(11.6,3.55));fig.subplots_adjust(left=.12,right=.98,bottom=.18,top=.87,wspace=.30)
    result={}
    for ax,key,title in zip(axs,['decode_relative_latency','first_token_relative_latency'],['(a) 解码相对延迟','(b) 首 token 相对延迟']):
        vals=np.sqrt(np.array(x['GSM8K'][key])*np.array(x['HumanEval'][key]));result[key]=vals.tolist()
        colors=['#AAB4BD']*len(names);colors[-1]='#326C9B'
        bars=ax.barh(range(len(names)),vals,height=.56,color=colors,edgecolor='#203244',linewidth=.55)
        bars[-1].set_hatch('///');ax.set_yticks(range(len(names)),names,fontsize=12);ax.invert_yaxis();ax.set_xlim(0,1.75)
        ax.set_xticks([0,.5,1,1.5]);ax.set_xlabel('相对 MECC 的延迟（MECC = 1）',fontsize=13)
        ax.bar_label(bars,labels=[f'{v:.2f}' for v in vals],padding=3,fontsize=11.5)
        ax.axvline(1,color='#87939D',ls='--',lw=.7);ax.grid(axis='x',color='#E5EAF0',lw=.5);ax.set_axisbelow(True)
        ax.spines[['top','right','left']].set_visible(False);ax.tick_params(axis='y',length=0);ax.set_title(title,fontsize=15,pad=9)
    fig.savefig(ASSETS/'matched_wide.png',dpi=260,bbox_inches='tight',pad_inches=.025);plt.close(fig)
    return {'source':'EXPERIMENT_TARGETS.json:matched_policy_paths','geometric_mean_ratios':result,'status':'authored candidate adaptation targets, not system measurements'}

def fit_pic(sl,path,x,y,w,h):
    from PIL import Image
    im=Image.open(path);iw,ih=im.size;scale=min(w/iw,h/ih);ww,hh=iw*scale,ih*scale
    return sl.shapes.add_picture(str(path),Inches(x+(w-ww)/2),Inches(y+(h-hh)/2),width=Inches(ww),height=Inches(hh))

def notes(sl,source,status,config=''):
    sl.notes_slide.notes_text_frame.text=(f'图表来源：R27 paper snapshot ({sha(PAPER/"manuscript.pdf")[:12]}).\n'
        f'数据身份：{status}\n来源文件：{source}\n{config}\n'
        '论文第八页和本 PPT 最后一页集中给出数据性质说明。无黄色标记仅为演示排版，不改变数据身份。')

def result_page(prs,n,title,lead,image,footer,source,status,config=''):
    sl=prs.slides.add_slide(prs.slide_layouts[6]);r.base(sl,n,title,lead)
    fit_pic(sl,ASSETS/image,.84,2.30,11.62,3.99)
    r.foot(sl,footer);notes(sl,source,status,config);return sl

def main():
    ASSETS.mkdir(parents=True,exist_ok=True);(OUT/'baseline').mkdir(exist_ok=True)
    if not (OUT/'baseline/MECC_HPCA_current.pptx').exists():shutil.copy2(SOURCE,OUT/'baseline/MECC_HPCA_current.pptx')
    if not (OUT/'baseline/MECC_HPCA_current.pdf').exists():shutil.copy2(CURRENT/'MECC_HPCA_current.pdf',OUT/'baseline/MECC_HPCA_current.pdf')
    body_audit();assets={}
    specs={'main':'measured_figures/main.pdf','ablation':'completion_figures/ablation_startup.pdf',
           'traffic':'completion_figures/traffic_exposure.pdf','models':'completion_figures/cross_model.pdf',
           'matched':'completion_figures/matched_baselines.pdf','capacity':'completion_figures/quota_targets.pdf',
           'sensitivity':'completion_figures/workload_sensitivity.pdf','transfer':'completion_figures/profile_mismatch.pdf',
           'deployment':'completion_figures/gpu_tradeoff.pdf'}
    for name,rel in specs.items():assets[name]=clean_figure(rel,name)
    assets['retention']=retention();assets['matched_wide']=matched()
    prs=Presentation(OUT/'baseline/MECC_HPCA_current.pptx')
    original_first12=[str(sl._element.xml) for sl in list(prs.slides)[:12]]
    # Refresh the retention evidence in the motivation while preserving its layout.
    s=prs.slides[4];oldpic=[sh for sh in s.shapes if sh.shape_type==13][0]
    x,y,w,h=[v/914400 for v in (oldpic.left,oldpic.top,oldpic.width,oldpic.height)]
    oldpic._element.getparent().remove(oldpic._element);fit_pic(s,ASSETS/'retention.png',x,y,w,h)
    notes(s,'INTRO_FIGURE_DATA.json','E1: measured A100 single-run cache counters; multi-GPU zero is a full-residency structural reference',
          '单卡数字按 warmup/prefill/decode/PPL 全流程 expert 访问计数；不是物理读取字节比例。')
    # Existing motivation/insight figures use arrays retained by R27.
    for index in [3,5,6,7,8]:
        notes(prs.slides[index],'ideal_assumptions.json:motivation / insight_ablation_targets',
              'authored unmeasured targets retained from the existing group-meeting deck; mechanism illustrations are schematic')
    # Preserve the conclusion and replace only the obsolete result pages.
    conclusion_shapes=[deepcopy(sh._element) for sh in prs.slides[16].shapes]
    ids=list(prs.slides._sldIdLst)
    for item in ids[12:]:prs.part.drop_rel(item.rId);prs.slides._sldIdLst.remove(item)
    target='authored unmeasured design targets; not benchmark executions; definitions and source values are in the paper appendix'
    result_page(prs,13,'Results: 单卡主对比中的推理开销',
        '同一张 A100、相同模型与输入下，比较不同缓存和执行策略。左图给出解码加速比，\n右图给出首 token 加速比；两者均以流式读取为参照。',
        'main.png','统一初始放置：解码与首 token 分别计量，避免混用两个阶段的加速比。',
        'RATIO_AUDIT.json; measured_figures/main.pdf','E1: committed measured single-A100 results, one run per policy',
        'Mixtral-8×7B FP16; 50/40 GiB planner allowances; WikiText-2; 8 prompts, 64 input/64 output tokens. Full RF result retained in Appendix.')
    result_page(prs,14,'Ablation: 各项设计与初始化开销',
        '依次加入初始放置、联合缓存和权重交付优化，比较每 token 解码时间。右图把初始化开销\n分摊到生成序列中，展示部署前准备如何随后续生成逐步摊销。',
        'ablation.png','初始放置与运行期更新共同作用；初始化收益随生成长度体现。',
        'EXPERIMENT_TARGETS.json:startup; ideal_assumptions.json:ablation_tpot_seconds',target)
    result_page(prs,15,'Model Scaling: 不同模型与任务',
        '在 Mixtral-8×7B、Qwen2-57B-A14B 和 Mixtral-8×22B 上比较同模型的流式读取与 MECC。\n两个面板分别对应 GSM8K 问答与 HumanEval 代码任务。',
        'models.png','每个柱子在同一模型、同一任务内计算加速比；不同模型使用各自的内存配置。',
        'EXPERIMENT_TARGETS.json:cross_model',target,'E3; 128 input/128 output tokens; model-specific H/C allowances; 2048 calibration samples.')
    result_page(prs,16,'Baseline Comparison: 相关策略的统一对照',
        '统一完整专家、FP16 权重和内存配置，比较相关工作的候选缓存策略。GSM8K 与 HumanEval\n先在任务内归一化，再取几何平均；MECC 为 1，数值越小表示延迟越低。',
        'matched_wide.png','分别比较解码与首 token 阶段，避免把不同阶段合并为一个性能数字。',
        'EXPERIMENT_TARGETS.json:matched_policy_paths',target,'E5: candidate local policy adaptations, not executions of the authors\' original full systems.')
    result_page(prs,17,'Capacity Sensitivity: CPU 内存容量的影响',
        '固定显存额度，逐档增加 CPU 主驻留容量，并比较四种策略的解码延迟。右图给出 MECC\n每增加 8 GiB 所节省的时间，观察新增缓存容量的边际收益。',
        'capacity.png','相同容量档内比较策略；右侧节省量等于相邻两档 MECC 延迟之差。',
        'SENSITIVITY_COMPARISON_TARGETS.json:capacity; SAVINGS_BAR_AUDIT.json',target,'E6; HBM allowance 50 GiB; host allowance 16/24/32/40/48 GiB.')
    result_page(prs,18,'Workload Sensitivity: 校准规模、输入长度与批量',
        '分别改变校准样本量、输入长度和批量大小。中图比较同一输入长度下的首 token 开销，\n以流式读取归一化；两侧展示校准后的解码时间和整批总吞吐。',
        'sensitivity.png','一次只改变一个工作负载参数；批量吞吐表示整批生成速率。',
        'SENSITIVITY_COMPARISON_TARGETS.json:profile/input/batch; INPUT_WATERFALL_AUDIT.json',target,
        'E7/E8/E9. Input chart is exact TTFT(method)/TTFT(streaming) at each input length; no jitter or new samples.')
    result_page(prs,19,'Profile Transfer: 校准任务与服务任务的差异',
        '行表示用于统计专家热度的校准任务，列表示实际服务任务。两个面板使用同一色标，\n比较固定驻留与在线更新在任务匹配、任务不匹配时的解码时间。',
        'transfer.png','在线更新使缓存内容随实际访问调整，减少对单一校准任务的依赖。',
        'narrative_targets.json:transfer_fixed/transfer_adaptive',target,'E10; WikiText-2/GSM8K/HumanEval; identical color scales.')
    result_page(prs,20,'Deployment Trade-off: 单卡与多卡资源配置',
        '多卡全显存配置将专家分散驻留在 GPU 上，单卡 MECC 使用显存、CPU 内存和 HDD 存储。\n左图比较每 token 延迟，右图用 GPU 数量乘以延迟，展示两种配置的资源占用。',
        'deployment.png','延迟与 GPU 占用分别展示；MECC 对应单卡点，多卡曲线为全显存参照。',
        'ideal_assumptions.json:gpus/resident_gpu_tpot_seconds/mecc_gpu_tpot_seconds[0]',target,
        'Deployment scenario only; no measured multi-GPU MECC data and no attribution to distributed FlashMoE.')
    # Put the existing conclusion after the refreshed result sequence.
    conclusion=prs.slides.add_slide(prs.slide_layouts[6])
    for element in conclusion_shapes:conclusion.shapes._spTree.insert_element_before(element,'p:extLst')
    # A visible appendix keeps all data identity explanations out of the main talk.
    sl=prs.slides.add_slide(prs.slide_layouts[6]);r.base(sl,22,'Appendix: 实验配置与数据来源',
        '主对比使用已提交的 A100 运行记录。动机、消融、模型扩展和扫参中的目标数值尚未实测；\n机制图用于说明方法。各图的来源与配置在逐页备注中记录，并与论文附录对应。')
    r.t(sl,1.0,2.35,5.5,.35,'E1：完整主对比（单次运行）',18,True,r.NAVY)
    ratio=json.loads((PAPER/'RATIO_AUDIT.json').read_text());rows=[]
    for key,v in ratio['main'].items():rows.append([ratio['display_names'][key],f"{v['tpot_ms']/1000:.3f}",f"{v['ttft_ms']/1000:.3f}"])
    rows.append(['Independent',f"{ratio['independent']['tpot_ms']/1000:.3f}",'258.696'])
    table=sl.shapes.add_table(len(rows)+1,3,Inches(1.0),Inches(2.84),Inches(5.7),Inches(3.30)).table
    table.columns[0].width=Inches(2.5);table.columns[1].width=Inches(1.6);table.columns[2].width=Inches(1.6)
    for i,row in enumerate([['策略','TPOT（秒）','TTFT（秒）']]+rows):
        for j,value in enumerate(row):
            cell=table.cell(i,j);cell.text=value;cell.fill.solid();cell.fill.fore_color.rgb=RGBColor.from_string('EAF2F9' if i==0 else 'FFFFFF')
            for p in cell.text_frame.paragraphs:p.font.size=Pt(14);p.font.name='Times New Roman';p.font.color.rgb=RGBColor.from_string('173D68' if i==0 else '172B3B');p.font.bold=i==0
    r.t(sl,7.15,2.35,5.0,.35,'配置与数据身份',18,True,r.NAVY)
    details=[('设备与模型','A100 80 GB · Mixtral-8×7B · FP16'),('E1 输入','WikiText-2 · 8 条 · 64/64 token'),
             ('目标图范围','E2/E3/E5–E10：未实测目标与候选策略'),('图表追溯','论文 R27 附录、源数组与逐页备注')]
    for i,(a,b) in enumerate(details):
        y=2.9+i*.77;r.t(sl,7.15,y,5.0,.27,a,16,True,r.NAVY);r.t(sl,7.15,y+.32,5.0,.35,b,16,False,r.DARK)
    r.foot(sl,'图中取消黄色高亮仅用于演示排版；不改变实测、目标及机制示意的身份。')
    notes(sl,'RATIO_AUDIT.json; paper Appendix A','complete provenance appendix; measured records retained alongside explicit target status')
    # Normalize fonts and slide numbers without regenerating the first twelve layouts.
    for n,sl in enumerate(prs.slides,1):
        for sh in sl.shapes:
            frames=[]
            if sh.has_text_frame:
                frames.append(sh.text_frame)
                if sh.top/Inches(1)>6.9 and sh.left/Inches(1)>11.8 and sh.text.strip().isdigit():sh.text_frame.paragraphs[0].runs[0].text=str(n)
            if sh.has_table:frames.extend(c.text_frame for row in sh.table.rows for c in row.cells)
            for tf in frames:
                for p in tf.paragraphs:
                    p.font.name='Times New Roman'
                    for run in p.runs:
                        run.font.name='Times New Roman';rp=run._r.get_or_add_rPr();ea=rp.find(qn('a:ea'))
                        if ea is None:ea=OxmlElement('a:ea');rp.append(ea)
                        ea.set('typeface','SimSun')
    prs.core_properties.title='MECC: 单卡 MoE 推理与三级专家缓存'
    prs.core_properties.subject='Group meeting; source status and configurations in Appendix and slide notes'
    prs.save(OUT/(NAME+'.pptx'))
    manifest={'paper_sha256':sha(PAPER/'manuscript.pdf'),'baseline_deck_sha256':sha(OUT/'baseline/MECC_HPCA_current.pptx'),
              'slides':len(prs.slides),'main_slides':21,'appendix_slides':[22],'assets':assets,
              'unchanged_scope':'First twelve layouts and mechanism graphics retained; motivation II numerical chart refreshed.',
              'expected_replacements':{'13':'E1 main','14':'E3 ablation/startup','15':'E3 models','16':'E5 candidates',
                  '17':'E6 capacity','18':'E7-E9 sensitivity','19':'E10 transfer','20':'deployment'},
              'visible_main_highlight':False,'target_identity_in_notes_and_appendix':True,
              'deck_sha256':sha(OUT/(NAME+'.pptx'))}
    (OUT/'UPDATE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Built',OUT/(NAME+'.pptx'),'slides',len(prs.slides))

if __name__=='__main__':main()
