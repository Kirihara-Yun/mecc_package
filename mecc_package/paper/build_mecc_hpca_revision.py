"""Build a review-driven talk using measured D1 causal replay, never mock curves."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.oxml.ns import qn
from pptx.opc.constants import RELATIONSHIP_TYPE as RT

import build_mecc_conference_talk as base
from build_mecc_first3 import BLACK, BLUE_DARK, BLUE_MID, BLUE_LIGHT, GRAY_LIGHT, GRAY_MID, WHITE, rect

HERE=Path(__file__).resolve().parent
DATA=HERE.parent/'results/raw/motivation_causal_replay_20261027_v2.json'
BLUE, GREY, ORANGE=base.BLUE, base.GREY, base.ORANGE
ARMS=['random_static','profile_static','random_joint','profile_joint']
LABELS={'random_static':'随机初态＋固定CPU', 'profile_static':'画像初态＋固定CPU',
        'random_joint':'随机初态＋联合LRU', 'profile_joint':'画像初态＋联合LRU',
        'profile_independent':'两层独立LRU'}


def records(d, name, arm):
    block=next(b for b in d['workloads'] if b['workload']==name)
    return [next(r for r in t['results'] if r['policy']==arm) for t in block['paired_trials']]


def save(fig, folder, name, label='D1 受控回放 · 合成序列 · 8 个配对种子'):
    fig.text(.985,.985,label,ha='right',va='top',fontsize=10.5,color=base.INK)
    fig.savefig(folder/f'{name}.png',dpi=240)
    fig.savefig(folder/f'{name}.pdf')
    plt.close(fig)


def two_axes():
    fig,ax=plt.subplots(figsize=(6.2,3.6))
    fig.subplots_adjust(left=.14,bottom=.22,right=.97,top=.82)
    return fig,ax


def mechanism_plots(folder):
    base.configure(); folder.mkdir(exist_ok=True,parents=True)
    d=json.loads(DATA.read_text(encoding='utf-8'))
    assert d['evidence_level']=='D1' and 'mode' not in d
    fig,ax=two_axes(); horizons=[16,32,64,128,256]
    for arm,color,marker,label in [('random_joint',GREY,'s','随机初态'),
                                  ('profile_joint',BLUE,'o','独立训练画像')]:
        vals=np.array([[r['startup_misses'][str(k)] for k in horizons] for r in records(d,'stationary',arm)])
        mean,sd=vals.mean(0),vals.std(0,ddof=1)
        ax.errorbar(horizons,mean,yerr=sd,color=color,marker=marker,capsize=3,lw=2,label=label)
    base.style(ax,'累计 SSD 需求未命中（次）↓')
    ax.set_xscale('log',base=2); ax.set_xticks(horizons,[str(k) for k in horizons])
    ax.set_xlabel('自开始服务起的请求数'); ax.set_ylim(bottom=0)
    ax.legend(fontsize=11,ncol=2,loc='upper left')
    save(fig,folder,'m1_startup')

    block=d['workloads'][0]['paired_trials'][0]
    order=block['profile_ranking']
    # Test distribution from the frozen held-out requests, not a drawn heat region.
    counts=np.bincount(block['trace'][:64],minlength=16)
    fig,ax=two_axes()
    fig.subplots_adjust(left=.25)
    arr=np.array([[1. if e in order[:6] else 0. for e in order],
                  [counts[e]/max(counts.max(),1) for e in order]])
    ax.imshow(arr,aspect='auto',cmap='Blues',vmin=0,vmax=1,interpolation='nearest')
    ax.set_xticks(range(16),[str(e) for e in order],fontsize=9)
    ax.set_yticks([0,1],['初始快层覆盖','前64请求热度'],fontsize=13)
    ax.set_xlabel('按独立训练画像排序的对象 ID')
    ax.set_xticks(np.arange(-.5,16,1),minor=True); ax.set_yticks([-.5,.5,1.5],minor=True)
    ax.grid(which='minor',color='white',lw=2); ax.tick_params(which='minor',length=0)
    ax.set_title('画像的快层覆盖与启动请求',fontsize=14,pad=14)
    save(fig,folder,'m1_coverage','D1 受控回放 · 固定展示首个种子 3')

    fig,ax=two_axes(); xs=np.arange(2)
    for arm,off,color,label in [('profile_static',-.24,GREY,'固定CPU'),
                               ('profile_independent',0,'#83A4C5','两层独立LRU'),
                               ('profile_joint',.24,BLUE,'排他联合LRU')]:
        groups=[[r['ssd_per_1000'] for r in records(d,work,arm)] for work in ['drift','phase_shuffled']]
        means=[np.mean(g) for g in groups]; sds=[np.std(g,ddof=1) for g in groups]
        bars=ax.bar(xs+off,means,.22,color=color,yerr=sds,capsize=3,label=label)
        ax.bar_label(bars,labels=[f'{m:.0f}' for m in means],padding=5,fontsize=11)
    base.style(ax,'SSD 需求未命中 / 千请求 ↓')
    ax.set_xticks(xs,['原访问顺序','阶段内乱序']); ax.set_ylim(0,850)
    ax.legend(fontsize=10,ncol=3,loc='upper left',handlelength=1.2,columnspacing=.7)
    save(fig,folder,'m2_order')

    fig,ax=two_axes()
    for name,color,label in [('drift',BLUE,'原访问顺序'),('phase_shuffled',GREY,'阶段内乱序')]:
        # Unique intervening objects, not wall time or ordinary request distance.
        trace=next(b for b in d['workloads'] if b['workload']==name)['paired_trials'][0]['trace']
        last={}; distances=[]
        for t,e in enumerate(trace):
            if e in last: distances.append(len(set(trace[last[e]+1:t])))
            last[e]=t
        ax.plot(range(16),[np.mean(np.array(distances)<=k)*100 for k in range(16)],
                color=color,marker='o' if name=='drift' else 's',markevery=2,lw=2,label=label)
    ax.axvspan(1.5,5.5,color='#E5F0FB',zorder=0)
    ax.axvline(1.5,color='#9CA7B4',ls=':',lw=1)
    ax.axvline(5.5,color=BLUE,ls=':',lw=1)
    ax.text(3.5,35,'CPU 可承接\n的复用区间',ha='center',fontsize=11,color=BLUE)
    base.style(ax,'已发生再访的累计比例（%）')
    ax.set(xlabel='两次访问间的不同对象数',xlim=(0,15),ylim=(0,105))
    ax.set_xticks([0,2,4,6,8,12,15]); ax.legend(loc='lower right',fontsize=11)
    save(fig,folder,'m2_reuse','D1 受控回放 · 条件再访 CDF · 种子 3')

    fig,ax=two_axes()
    ax.axvspan(8.5,16.5,color='#F1F5FA',zorder=0)
    for arm,color,ls,marker in [('random_static','#9BA1A8','--','s'),('profile_static',ORANGE,'-','^'),
                              ('random_joint','#75A6CE','--','d'),('profile_joint',BLUE,'-','o')]:
        vals=np.array([r['ssd_by_window'] for r in records(d,'drift',arm)])
        ax.plot(range(1,17),vals.mean(0),color=color,ls=ls,marker=marker,markevery=2,lw=2,label=LABELS[arm])
    ax.axvline(8.5,color=ORANGE,ls=':',lw=1)
    base.style(ax,'SSD 需求未命中 / 千请求 ↓')
    ax.set(xlabel='64 请求 / 时间窗',ylim=(0,850),xlim=(.6,16.4))
    ax.set_xticks([1,4,8,12,16]); ax.legend(fontsize=9.5,ncol=2,loc='upper left',columnspacing=.8)
    save(fig,folder,'m3_factorial')

    trial=next(b for b in d['workloads'] if b['workload']=='drift')['paired_trials'][0]
    tr=trial['trace']; rank=trial['profile_ranking']
    arr=np.array([[1 if e in rank[:6] else 0 for e in range(16)],
                  [tr[:512].count(e)/512 for e in range(16)],
                  [tr[512:].count(e)/512 for e in range(16)]],float)
    arr[1:]/=max(arr[1:].max(),1e-9)
    fig,ax=two_axes()
    fig.subplots_adjust(left=.25)
    ax.imshow(arr,aspect='auto',cmap='Blues',vmin=0,vmax=1)
    ax.set_yticks([0,1,2],['初始快层覆盖','阶段 A 热度','阶段 B 热度'],fontsize=13)
    ax.set_xticks(range(16),range(16),fontsize=9); ax.set_xlabel('固定对象 ID（不按测试频次重排）')
    ax.set_xticks(np.arange(-.5,16,1),minor=True); ax.set_yticks(np.arange(-.5,3,1),minor=True)
    ax.grid(which='minor',color='white',lw=2); ax.tick_params(which='minor',length=0)
    save(fig,folder,'m3_coverage','D1 受控回放 · 人工阶段切换 · 种子 3')

    fig,axs=plt.subplots(1,2,figsize=(12,3.65))
    fig.subplots_adjust(left=.07,bottom=.24,right=.98,top=.81,wspace=.32)
    for ax,work,title in [(axs[0],'stationary','(a) 含局部工作集的请求'),(axs[1],'uniform','(b) 均匀独立请求')]:
        vals=[]; sds=[]
        for arm in ['profile_static','profile_independent','profile_joint']:
            g=[r['ssd_per_1000'] for r in records(d,work,arm)]
            vals.append(np.mean(g)); sds.append(np.std(g,ddof=1))
        bars=ax.bar(range(3),vals,.55,color=[GREY,'#83A4C5',BLUE],yerr=sds,capsize=4)
        ax.bar_label(bars,labels=[f'{v:.0f}' for v in vals],fontsize=12,padding=6)
        base.style(ax,'SSD 需求未命中 / 千请求 ↓')
        ax.set_xticks(range(3),['固定CPU','独立LRU','联合LRU'])
        ax.set_ylim(0,900); ax.set_title(title,pad=10)
    save(fig,folder,'controls')

    historical=json.loads((HERE.parent/'results/raw/mixtral_real.json').read_text(encoding='utf-8'))
    fig,ax=plt.subplots(figsize=(11.8,3.5)); fig.subplots_adjust(left=.11,bottom=.20,right=.96,top=.80)
    values=[1,historical['results']['ours']['speedup_vs']['swapmoe']]
    bars=ax.barh([1,0],values,.43,color=[GREY,BLUE])
    for bar,v in zip(bars,values): ax.text(v+.025,bar.get_y()+bar.get_height()/2,f'{v:.2f}×',va='center',fontsize=18,weight='bold')
    ax.set_yticks([1,0],['本地机制对照','MECC']); ax.set_xlim(0,1.6)
    ax.set_xlabel('相对综合性能（历史记录）'); ax.grid(axis='x',color='#DFE4EA'); ax.set_axisbelow(True)
    save(fig,folder,'historical','历史 D2 记录 · 配置槽位对齐；物理字节与计数窗口待复核')
    return d


def panel_slide(s,assets,title,body,left,right,lefttitle,righttitle,takeaway):
    base.head(s,title,body)
    base.panel(s,.89,lefttitle); base.panel(s,6.89,righttitle)
    base.pic(s,assets,left,.72,3.15,5.83)
    base.pic(s,assets,right,6.72,3.15,5.83)
    base.footer(s,takeaway)


def related(s):
    base.head(s,'Related Work: What Remains to Establish',
              '近期系统从画像引导、三级驻留、替换与调度等角度优化专家访问。\n'
              'MECC 研究有限请求时域内的初态与在线协同，目标是降低实际内存约束下的总代价。')
    cols=[1.82,4.00,2.56,3.18]; x0=.86
    rows=[['系统','核心控制机制','主要目标','核心决策对象'],
          ['Fiddler [1]','离线专家热度；CPU/GPU 执行选择','异构执行延迟','CPU/GPU 执行位置'],
          ['MoE-Lightning [2]','预算约束策略搜索；传输流水','批量推理吞吐','批量与驻留比例'],
          ['SSD-LLaMA [3]','原生三级驻留；动态保留','SSD 专家交付','I/O 路径与三级驻留'],
          ['FlashMoE [4]','近期性/频率驱动的学习式替换','减少 SSD I/O','专家缓存替换'],
          ['MoE-CORE [5]','离线领域画像；历史替换与预取','协同卸载与驻留','逐层容量、驻留与预取'],
          ['ZipMoE [6]','无损压缩；缓存亲和调度','容量与调度协同','权重表示与请求调度'],
          ['MECC','预算计划；联合保留','有限时域总代价','有限时域初态与迁移']]
    for i,row in enumerate(rows):
        y=2.32+i*.47; x=x0
        for j,(text,w) in enumerate(zip(row,cols)):
            rect(s,x,y,w,.44,fill=WHITE,line=BLACK)
            base.old.t(s,x+.025,y,w-.05,.44,text,13 if j else 13.5,BLACK,i in (0,7))
            x+=w
    base.old.t(s,1.03,6.10,11.28,.24,'文献机制比较；本地 fp16 机制对照不等同于上述系统的官方实现。',11.5,BLACK,False)
    base.footer(s,'研究重点：先验计划与在线保留，在同实际资源约束下分别贡献多少？')


def overview_contribution(s):
    base.head(s,'MECC: Separate the Prior from the Policy',
              'MECC 将部署前的预算计划与运行中的联合保留放在同一框架中。\n'
              '我们分别检验启动段的画像效应、访问次序的复用效应，以及初态与在线规则的交互。')
    for x,title in [(1.04,'① 初始计划'),(5.05,'② 在线保留'),(9.04,'③ 独立验证')]:
        base.old.t(s,x,2.62,3.22,.40,title,18,BLUE_DARK)
        rect(s,x,3.10,3.22,.012,fill=GRAY_MID,line=GRAY_MID)
    for i,h in enumerate([1.45,1.18,.91,.69,.46,.26]):
        rect(s,1.22+i*.48,5.38-h,.31,h,fill=BLUE_MID if i<2 else GRAY_MID,line=BLUE_DARK)
    base.old.t(s,1.12,5.73,3.08,.38,'独立画像 → 初始驻留',15,BLUE_DARK)
    for r,seq in enumerate(['HHCCSS','CHHCSS','CCHHSS']):
        for c,t in enumerate(seq):
            rect(s,5.21+c*.45,3.82+r*.53,.36,.36,fill={'H':BLUE_MID,'C':GRAY_MID,'S':GRAY_LIGHT}[t],line=WHITE)
    base.old.t(s,5.12,5.73,3.08,.38,'共同访问序列 → 驻留更新',15,BLUE_DARK)
    for r,name in enumerate(['无画像','有画像']):
        base.old.t(s,8.96,4.10+r*.67,.79,.38,name,12,BLUE_DARK)
        for c,lab in enumerate(['固定','在线']):
            if r==0: base.old.t(s,9.88+c*1.02,3.59,.91,.36,lab,13,BLUE_DARK)
            rect(s,9.88+c*1.02,4.10+r*.67,.91,.42,fill=BLUE_LIGHT if r+c else WHITE,line=BLUE_DARK)
    base.old.t(s,9.11,5.73,3.08,.38,'2×2 对照 → 识别增量',15,BLUE_DARK)
    base.footer(s,'一个框架，三个可证伪问题；机制回放与真机性能分别验证。')


def replace_body(slide, text):
    for shape in slide.shapes:
        if shape.has_text_frame and 0.9<shape.top/Inches(1)<1.01 and shape.left/Inches(1)>1.15:
            shape.text_frame.text=text
            for p in shape.text_frame.paragraphs:
                for run in p.runs:
                    run.font.name='Microsoft YaHei'; run.font.size=Pt(18); run.font.bold=True
                    run.font.color.rgb=BLACK
            return


def prune_unused_images(prs):
    """Remove replaced preview plots from the delivered package, not user files."""
    for slide in prs.slides:
        used={value for node in slide._element.iter()
              for value in (node.get(qn('r:embed')),node.get(qn('r:link'))) if value}
        for rel in list(slide.part.rels.values()):
            if rel.reltype==RT.IMAGE and rel.rId not in used:
                slide.part.drop_rel(rel.rId)


def build(template,out):
    assets=out.parent/'hpca_revision_assets'; data=mechanism_plots(assets)
    summaries=data['summaries']
    startup_random=summaries['stationary']['random_joint']['startup64_mean']
    startup_profile=summaries['stationary']['profile_joint']['startup64_mean']
    miss_original=summaries['drift']['profile_joint']['ssd_per_1000_mean']
    miss_shuffled=summaries['phase_shuffled']['profile_joint']['ssd_per_1000_mean']
    base.build(template,out); prs=Presentation(out)
    related(prs.slides[1]); overview_contribution(prs.slides[2])
    panel_slide(prs.slides[3],assets,'Motivation I: Isolate the Initial-State Effect',
                f'在相同联合 LRU 下，独立画像将前 64 次请求的平均冷读从 {startup_random:g} 次降至 {startup_profile:g} 次。\n'
                '累计差异主要在启动段形成；初始计划的价值因此与服务请求时域有关。',
                'm1_startup','m1_coverage','(a) 同一在线规则的启动段冷读','(b) 初始覆盖与独立测试请求',
                '动机 ①：启动段是离线先验发挥作用的重要窗口。')
    panel_slide(prs.slides[4],assets,'Motivation II: Frequency Is Not Enough',
                f'保持每阶段访问频次不变，阶段内乱序使联合 LRU 的冷读从 {miss_original:.0f} 增至 {miss_shuffled:.0f} 次/千请求。\n'
                '访问次序改变了再访距离与可复用机会；单独的热度直方图不足以刻画缓存压力。',
                'm2_order','m2_reuse','(a) 保持边际频次，只改变时序','(b) 再访距离与快层复用区间',
                '动机 ②：访问频次决定热度，访问次序决定复用机会。')
    panel_slide(prs.slides[5],assets,'Motivation III: Test the Prior–Policy Interaction',
                '人工阶段切换后，画像固定方案的冷读上升，而两种联合方案保持接近。\n'
                '初始先验与运行期保留作用于不同时间尺度；2×2 对照呈现了各自的作用。',
                'm3_factorial','m3_coverage','(a) 初始画像 × 在线保留的 2×2 对照','(b) 固定对象 ID 下的阶段热度',
                '动机 ③：按两个时间尺度组织初始先验与在线反馈。')
    replace_body(prs.slides[6], '画像把有限快层空间优先配置给高概率对象，在请求开始时减少冷读。\n以服务请求数量为时域，将画像、编译与预热开销纳入初始化和推理的总代价。')
    replace_body(prs.slides[7], '专家被显存淘汰后，若在短距离内再访，CPU 保留能够承接这次请求。\n跨层去重扩大唯一对象覆盖；访问次序与驻留状态共同决定哪些冷读可以避免。')
    replace_body(prs.slides[8], '画像初始化影响启动段，在线保留决定后续请求如何利用快层空间。\n通过两种时间尺度协同利用先验与真实访问，并将跨层迁移开销纳入总代价。')
    base.head(prs.slides[12],'Historical Observation: A Reference Point',
              '历史 A100 Mixtral 实验记录中，相对本地机制对照的综合性能为 1.33×。\n'
              '该记录对齐了配置槽位；实际内存字节、质量等价与统计窗口仍需独立复核。')
    base.pic(prs.slides[12],assets,'historical',.92,2.62,11.50)
    base.footer(prs.slides[12],'历史观测为硬件复核提供锚点；编译器的独立收益由新增对照检验。')
    base.head(prs.slides[13],'Controls: When Does the Mechanism Help?',
              '局部工作集与均匀独立请求采用相同对象数和物理槽位；误差棒为合成种子标准差。\n'
              '保留无优势与较小画像效应，检验唯一覆盖、迁移开销和真实请求分布对收益的影响。')
    base.pic(prs.slides[13],assets,'controls',.89,2.67,11.52)
    base.footer(prs.slides[13],'机制证据：可复现、可反驳；硬件结论还需真实访问序列与净端到端代价。')
    titles={6:'Insight I: Optimize the Finite Horizon',7:'Insight II: Measure Coverage and Reuse',
            8:'Insight III: Quantify the Incremental Gain'}
    for i,title in titles.items(): prs.slides[i].shapes.title.text=title
    # The source template also renders inherited automatic page numbers.
    for owner in list(prs.slide_layouts)+list(prs.slide_masters):
        for shape in list(owner.shapes):
            if shape.is_placeholder and shape.placeholder_format.type==PP_PLACEHOLDER.SLIDE_NUMBER:
                shape._element.getparent().remove(shape._element)
    for i,slide in enumerate(prs.slides,1):
        # Reapply approved title treatment to newly assigned text.
        for p in slide.shapes.title.text_frame.paragraphs:
            p.alignment=PP_ALIGN.CENTER
            for run in p.runs: run.font.name='Microsoft YaHei'; run.font.size=Pt(30); run.font.bold=True
        # New pages rebuild page-number shapes rather than inheriting old ones.
        for shape in list(slide.shapes):
            is_number_placeholder=(shape.is_placeholder and
                                   shape.placeholder_format.type==PP_PLACEHOLDER.SLIDE_NUMBER)
            if is_number_placeholder or (shape.has_text_frame and shape.top/Inches(1)>6.60 and shape.text.strip().isdigit()):
                shape._element.getparent().remove(shape._element)
        base.old.t(slide,12.23,7.02,.48,.30,str(i),17,base.old.RED,False)
        slide.notes_slide.notes_text_frame.text=(
            f'第{i}页。该版经过三名模拟 HPCA 审稿视角复审，不构成实际投稿接收结论。\n'
            '第4/5/6/14页为实际运行的D1抽象缓存回放：N16,H2,C4,8配对种子，无预算外镜像和预取；'
            '合成序列不是Mixtral路由，标准差不是GPU重复运行方差。\n'
            '第13页仅为历史D2参考。PROVENANCE X7物理预算、X8跨流屏障、X9统计窗口未关闭。\n'
            '同H+C容量全局LRU与联合排他模型逐请求miss相同，不声称新替换算法。\n'
            '资料：docs/HPCA_REVIEW_AND_REVISION.md；docs/HPCA_CAUSAL_REPLAY_PROTOCOL.md；'
            'results/raw/motivation_causal_replay_20261027_v2.json。\n'
            '相关工作：[1]Fiddler ICLR2025 §3.4；[2]MoE-Lightning ASPLOS2025 §4.2；'
            '[3]SSD-LLaMA arXiv2609.18110；[4]FlashMoE arXiv2601.17063v2；'
            '[5]MoE-CORE arXiv2610.01950v1；[6]ZipMoE ICML2026。')
    prs.core_properties.title='MECC — HPCA review revision'
    prs.core_properties.subject='Controlled characterization of prior-guided tiered expert caching'
    prs.core_properties.author=''
    prs.core_properties.last_modified_by=''
    prs.core_properties.keywords='MECC, MoE, tiered caching, controlled replay, research draft'
    prune_unused_images(prs)
    prs.save(out)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--template',type=Path,default=Path('C:/Users/zhaoy/Desktop/1013.pptx'))
    p.add_argument('--out',type=Path,default=HERE/'MECC_HPCA_review_revision.pptx')
    a=p.parse_args(); build(a.template,a.out)
