"""Conference talk: native mechanism figures, matplotlib plots, explicit mock data.

Run from any cwd. All illustrative experiment values stay outside results/.
"""
from pathlib import Path
import argparse
import json
from collections import OrderedDict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

import build_mecc_paper_talk as old
from build_mecc_first3 import BLUE_DARK, BLUE_MID, BLUE_LIGHT, GRAY_MID, GRAY_LIGHT, BLACK, WHITE, rect

HERE = Path(__file__).resolve().parent
INK, BLUE, GREY, ORANGE = '#172C46', '#2768A8', '#8C949E', '#A95315'
MOCK = '示例数据 · 待实测替换'


def configure():
    plt.rcParams.update({
        'font.family': 'sans-serif', 'font.sans-serif': ['Microsoft YaHei', 'DejaVu Sans'],
        'font.size': 14, 'axes.labelsize': 15, 'axes.titlesize': 16,
        'axes.edgecolor': '#626C79', 'axes.linewidth': .8,
        'xtick.labelsize': 13, 'ytick.labelsize': 13,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.unicode_minus': False, 'legend.frameon': False,
        'savefig.facecolor': 'white', 'figure.facecolor': 'white',
        'pdf.fonttype': 42, 'ps.fonttype': 42,
    })


def style(ax, ylabel):
    ax.set_ylabel(ylabel)
    ax.set_axisbelow(True)
    ax.grid(axis='y', color='#DFE4EA', linewidth=.7)
    ax.tick_params(length=3, color='#626C79')


def export(fig, folder, name, mock=False):
    if mock:
        fig.text(.985, .985, MOCK, ha='right', va='top', color=ORANGE,
                 fontsize=12, weight='bold',
                 bbox=dict(facecolor='#FFF5E9', edgecolor='none', pad=3))
    fig.savefig(folder / f'{name}.png', dpi=240)
    fig.savefig(folder / f'{name}.pdf')
    plt.close(fig)


def make_plots(folder):
    configure()
    folder.mkdir(parents=True, exist_ok=True)
    data = {
        'notice': 'mock entries are illustrative numbers, not measured results or forecasts',
        'budget': {'status': 'mock', 'cpu_budget_gb': [20, 30, 40, 50],
                   'fixed_tpot_s': [36, 29, 23, 18], 'joint_tpot_s': [28, 22, 17, 13]},
        'drift': {'status': 'mock', 'window': list(range(1, 17)),
                  'fixed_ssd_pct': [18, 17, 18, 16, 17, 18, 17, 18, 40, 43, 42, 41, 44, 42, 43, 42],
                  'online_ssd_pct': [18, 17, 17, 16, 16, 17, 16, 17, 39, 31, 26, 22, 19, 18, 17, 17]},
        'ablation': {'status': 'mock', 'variants': ['固定驻留', '仅画像', '仅在线', '完整方案'],
                     'relative_performance': [1., 1.12, 1.21, 1.36],
                     'ssd_pct': [35, 29, 23, 17]},
    }
    source = json.loads((HERE.parent / 'results/raw/mixtral_real.json').read_text(encoding='utf-8'))
    real = source['results']
    data['main'] = {'status': 'verified_D2', 'source': 'results/raw/mixtral_real.json',
                    'claim_ids': ['M1', 'M3', 'M4'],
                    'speedup': real['ours']['speedup_vs']['swapmoe'],
                    'cpu_pct': [real[p]['hit_pct']['cpu'] for p in ('swapmoe', 'ours')],
                    'ssd_pct': [real[p]['hit_pct']['ssd'] for p in ('swapmoe', 'ours')]}
    (folder / 'presentation_data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    fig.subplots_adjust(left=.14, bottom=.22, right=.96, top=.82)
    d = data['budget']
    for key, label, color, marker in [('fixed_tpot_s', '固定驻留', GREY, 's'),
                                       ('joint_tpot_s', '联合缓存', BLUE, 'o')]:
        ax.plot(d['cpu_budget_gb'], d[key], lw=2.4, marker=marker, ms=7, color=color, label=label)
    style(ax, '每个输出 token 延迟（s）↓')
    ax.set_xlabel('CPU 专家缓存预算（GB）')
    ax.set_xticks(d['cpu_budget_gb']); ax.set_ylim(0, 45)
    ax.legend(loc='upper right', ncol=2, fontsize=12)
    export(fig, folder, 'mot_budget', True)

    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    fig.subplots_adjust(left=.14, bottom=.22, right=.96, top=.84)
    xx = np.arange(2)
    vals0 = [data['main']['cpu_pct'][0], data['main']['ssd_pct'][0]]
    vals1 = [data['main']['cpu_pct'][1], data['main']['ssd_pct'][1]]
    for vals, off, color, label in [(vals0, -.18, GREY, '本地对照'), (vals1, .18, BLUE, 'MECC')]:
        bars = ax.bar(xx+off, vals, .31, color=color, label=label)
        ax.bar_label(bars, labels=[f'{v:.1f}%' for v in vals], padding=5, fontsize=13, color=INK)
    style(ax, '专家访问比例（%）')
    ax.set_xticks(xx, ['CPU 命中 ↑', 'SSD 访问 ↓']); ax.set_ylim(0, 52)
    ax.legend(ncol=2, loc='upper right', fontsize=12)
    export(fig, folder, 'mot_reuse')

    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    fig.subplots_adjust(left=.14, bottom=.22, right=.96, top=.82)
    d = data['drift']
    ax.axvspan(8.5, 16.3, color='#F0F5FA', zorder=0)
    for key, lab, color, marker in [('fixed_ssd_pct', '固定驻留', GREY, 's'),
                                    ('online_ssd_pct', '在线更新', BLUE, 'o')]:
        ax.plot(d['window'], d[key], label=lab, color=color, marker=marker, markevery=2, ms=5, lw=2.2)
    ax.axvline(8.5, color=ORANGE, ls='--', lw=1.2)
    ax.text(8.8, 47, '请求阶段切换', fontsize=12, color=ORANGE)
    style(ax, 'SSD 访问比例（%）↓')
    ax.set(xlabel='连续请求时间窗', ylim=(0, 60), xlim=(.7, 16.3))
    ax.set_xticks([1, 4, 8, 12, 16]); ax.legend(loc='upper left', fontsize=12, ncol=2)
    export(fig, folder, 'mot_drift', True)

    fig, axs = plt.subplots(1, 2, figsize=(12.0, 3.7))
    fig.subplots_adjust(left=.07, bottom=.24, right=.98, top=.87, wspace=.33)
    ax = axs[0]
    bars = ax.bar([0, 1], [1., data['main']['speedup']], .48, color=[GREY, BLUE])
    ax.bar_label(bars, labels=['1.00×', '1.33×'], padding=6, fontsize=16, weight='bold')
    style(ax, '相对综合性能 ↑')
    ax.set_xticks([0, 1], ['本地对照', 'MECC']); ax.set_ylim(0, 1.65)
    ax.set_title('(a) 相同预算的端到端比较', pad=12)
    ax = axs[1]
    for vals, off, color, label in [(vals0, -.18, GREY, '本地对照'), (vals1, .18, BLUE, 'MECC')]:
        bars = ax.bar(xx+off, vals, .31, color=color, label=label)
        ax.bar_label(bars, labels=[f'{v:.1f}%' for v in vals], padding=4, fontsize=13)
    style(ax, '专家访问比例（%）')
    ax.set_xticks(xx, ['CPU 命中 ↑', 'SSD 访问 ↓']); ax.set_ylim(0, 52)
    ax.set_title('(b) 缓存行为解释性能变化', pad=12)
    ax.legend(ncol=2, fontsize=11, loc='upper right')
    export(fig, folder, 'main_result')

    fig, axs = plt.subplots(1, 2, figsize=(12., 3.7))
    fig.subplots_adjust(left=.07, bottom=.24, right=.98, top=.80, wspace=.32)
    d = data['ablation']; xx = np.arange(4)
    for ax, values, ylabel, title in [
        (axs[0], d['relative_performance'], '相对综合性能 ↑', '(a) 组件对综合性能的贡献'),
        (axs[1], d['ssd_pct'], 'SSD 访问比例（%）↓', '(b) 组件对冷读压力的影响')]:
        bars = ax.bar(xx, values, .57, color=[GREY, '#A2BDD8', '#6C9AC5', BLUE])
        ax.bar_label(bars, padding=5, fontsize=13,
                     labels=[f'{v:.2f}×' for v in values] if ax is axs[0] else [f'{v}%' for v in values])
        style(ax, ylabel); ax.set_xticks(xx, d['variants']); ax.set_title(title, pad=12)
    axs[0].set_ylim(0, 1.7); axs[1].set_ylim(0, 46)
    export(fig, folder, 'ablation', True)
    fig = plt.figure(figsize=(6.4, .55))
    fig.text(.5, .5, r'$\mathbb{E}[T] = p_H T_H + p_C T_C + p_S T_S$',
             ha='center', va='center', fontsize=24, color=INK)
    export(fig, folder, 'cost_equation')
    return data


def pic(s, assets, name, x, y, w):
    s.shapes.add_picture(str(assets / f'{name}.png'), Inches(x), Inches(y), width=Inches(w))


def footer(s, message):
    rect(s, 1.02, 6.40, 11.25, .012, fill=GRAY_MID, line=GRAY_MID)
    old.t(s, 1.06, 6.55, 11.17, .41, message, 17, BLUE_DARK)


def badge(s, mock):
    if mock:
        old.t(s, 9.56, 2.16, 2.70, .30, MOCK, 12, RGBColor.from_string(ORANGE[1:]))


def head(s, title, body, mock=False):
    old.heading(s, title, body, explanation_size=18, explanation_height=1.08)
    # Each mock plot carries its own visible label, including standalone exports.


def panel(s, x, title):
    old.t(s, x, 2.57, 5.55, .40, title, 17, BLUE_DARK)
    rect(s, x, 3.03, 5.55, .012, fill=GRAY_MID, line=GRAY_MID)


def mot1(s, assets):
    head(s, 'Motivation I: Cold Reads Stall Decoding',
         '单任务缓存预算决定有多少专家访问需要进入 SSD；冷读越频繁，生成就越容易等待权重。\n'
         '预算扫描用于观察端到端延迟随 CPU 容量的变化，并检验联合缓存能否在同预算下减少等待。', True)
    panel(s, .89, '(a) 缓存预算与解码延迟')
    panel(s, 6.89, '(b) 稀疏路由与专家驻留位置')
    pic(s, assets, 'mot_budget', .77, 3.12, 5.77)
    for i in range(8):
        x = 8.01+i*.51
        old.t(s, x, 3.30, .43, .30, f'E{i+1}', 11, BLUE_DARK)
        selected = i in (1, 6)
        old.circle(s, x, 3.83, .42, fill=BLUE_MID if selected else GRAY_LIGHT,
                   line=BLUE_DARK if selected else GRAY_MID)
        for row, tier in enumerate(('显存', 'CPU', 'SSD')):
            active = row == (0 if i<2 else 1 if i<5 else 2)
            rect(s, x, 4.52+row*.43, .43, .29,
                 fill=([BLUE_MID, GRAY_MID, GRAY_LIGHT][row] if active else WHITE),
                 line=BLUE_DARK if active else WHITE)
    old.t(s, 6.95, 3.81, .95, .34, '本次路由', 12, BLUE_DARK)
    for row, label in enumerate(('显存', 'CPU', 'SSD')):
        old.t(s, 7.01, 4.49+row*.43, .82, .33, label, 13, BLUE_DARK)
    old.t(s, 8.21, 5.96, 3.91, .30, 'E7 被选中：必须读取 SSD', 14, BLUE_DARK)
    footer(s, '动机 ①：快层空间有限，需要把容量用在更可能被访问的专家上。')


def mot2(s, assets):
    head(s, 'Motivation II: Eviction Breaks Reuse',
         '历史 Mixtral A100 实测中，本地对照的 SSD 访问为 34.5%，MECC 为 17.6%。\n'
         'CPU 命中同时由 23.3% 增至 38.0%；这一结果提示，显存淘汰后的专家仍值得在 CPU 层保留。')
    panel(s, .89, '(a) 相同预算下的缓存访问分布')
    panel(s, 6.89, '(b) 专家淘汰后的跨层复用')
    pic(s, assets, 'mot_reuse', .77, 3.12, 5.77)
    stages = ['首次激活', '显存淘汰', '再次激活']
    for j, lab in enumerate(stages):
        old.t(s, 8.14+j*1.30, 3.52, 1.17, .35, lab, 13, BLUE_DARK)
    for row, (lab, colors, words) in enumerate([
        ('固定驻留', [BLUE_MID, GRAY_LIGHT, WHITE], ['显存', '未保留', 'SSD']),
        ('联合保留', [BLUE_MID, GRAY_MID, GRAY_MID], ['显存', 'CPU', 'CPU'])]):
        y = 4.23+row*.91
        old.t(s, 6.97, y+.04, 1.08, .40, lab, 14, BLUE_DARK)
        for j, (color, word) in enumerate(zip(colors, words)):
            x = 8.17+j*1.30
            rect(s, x, y, 1.04, .52, fill=color, line=BLUE_DARK)
            old.t(s, x, y, 1.04, .52, word, 14, WHITE if j==0 else BLACK)
    old.t(s, 7.25, 6.01, 4.80, .30, '机制示意：再访时由 CPU 承接', 13, BLUE_DARK)
    footer(s, '动机 ②：显存与 CPU 应共同保留工作集，让复用跨越显存淘汰事件。')


def mot3(s, assets):
    head(s, 'Motivation III: Profiles Become Stale',
         '请求阶段发生变化时，历史画像中的高频专家可能不再覆盖当前热点。\n'
         '按时间窗观察 SSD 访问，能够区分“固定驻留持续失配”与“在线缓存逐步适应”两种行为。', True)
    panel(s, .89, '(a) 请求阶段切换后的冷读压力')
    panel(s, 6.89, '(b) 新热点与初始驻留失配')
    pic(s, assets, 'mot_drift', .77, 3.12, 5.77)
    for i in range(8):
        old.t(s, 8.04+i*.51, 3.39, .43, .30, f'E{i+1}', 11, BLUE_DARK)
    for row, (lab, hot) in enumerate([('初始驻留', [0,1,2]), ('阶段 A', [0,1,2]), ('阶段 B', [3,4,5])]):
        y = 4.03+row*.66
        old.t(s, 6.98, y+.02, 1., .34, lab, 13, BLUE_DARK)
        for i in range(8):
            rect(s, 8.04+i*.51, y, .43, .37,
                 fill=BLUE_MID if i in hot else GRAY_LIGHT, line=WHITE)
    old.t(s, 7.33, 6.01, 4.78, .30, '机制示意：新热点仍在原快层之外', 13, BLUE_DARK)
    footer(s, '动机 ③：部署前画像给出起点，运行时反馈负责持续纠偏。')


def result(s, assets):
    head(s, 'Evaluation: Faster with Fewer Cold Reads',
         '历史 A100 Mixtral 主实验使用相同的 50 GB 显存与 40 GB CPU 预算。\n'
         'MECC 的综合性能达到本地 SwapMoE-style 对照的 1.33×，并将更多访问转移到 CPU 缓存。')
    pic(s, assets, 'main_result', .89, 2.67, 11.52)
    old.t(s, 1.10, 6.09, 10.92, .29,
          'D2 真机 · Mixtral-8x7B · 来源：mixtral_real.json（M1 / M3 / M4）', 12, BLACK, False)
    footer(s, '主结果：同预算下提高综合性能，同时减少进入 SSD 的专家访问。')


def overview(s, assets):
    head(s, 'System Overview: From Prior to Feedback',
         '编译期把访问画像与单任务预算转成逐层驻留方案；运行期根据真实路由更新显存与 CPU 缓存。\n'
         '两部分共享同一个三级存储视图：SSD 保存完整权重，快层位置随专家访问改变。')
    panel(s, .89, '编译期：专家 × 层级的初始驻留')
    panel(s, 6.89, '运行期：每次访问实际命中哪一层')
    colors = {'H': BLUE_MID, 'C': GRAY_MID, 'S': GRAY_LIGHT}
    for col in range(8):
        old.t(s, 1.72+col*.55, 3.42, .43, .30, f'E{col+1}', 11, BLUE_DARK)
    for row, seq in enumerate(['HHCCCCSS', 'HHHCCSSS', 'HHCCCSSS', 'HHHCCCSS']):
        y = 4.00+row*.46
        old.t(s, 1.04, y, .56, .32, f'L{row+1}', 13, BLUE_DARK)
        for col, tier in enumerate(seq):
            rect(s, 1.72+col*.55, y, .43, .32, fill=colors[tier], line=WHITE)
    for j, (name, color) in enumerate([('显存', BLUE_MID), ('CPU', GRAY_MID), ('SSD', GRAY_LIGHT)]):
        rect(s, 1.60+j*1.54, 6.00, .21, .21, fill=color, line=color)
        old.t(s, 1.86+j*1.54, 5.94, 1.00, .32, name, 12, BLACK, False, PP_ALIGN.LEFT)
    seq = ['H', 'C', 'H', 'S', 'C', 'H', 'C', 'H']
    ys = {'H': 3.98, 'C': 4.63, 'S': 5.28}
    for tier, name in [('H','显存'),('C','CPU'),('S','SSD')]:
        old.t(s, 6.99, ys[tier]-.02, .75, .34, name, 13, BLUE_DARK)
        rect(s, 7.91, ys[tier]+.14, 4.15, .009, fill=GRAY_LIGHT, line=GRAY_LIGHT)
    for i, tier in enumerate(seq):
        x = 7.94+i*.55
        old.circle(s, x, ys[tier], .29, fill=colors[tier], line=BLUE_DARK)
        old.t(s, x-.03, 5.83, .37, .29, str(i+1), 11, BLACK, False)
    old.t(s, 8.11, 6.16, 3.82, .28, '访问次序（机制示意）', 12, BLUE_DARK, False)
    footer(s, '编译期确定初始位置；运行期通过显存与 CPU 的联合保留持续纠偏。')


def insight3(s, assets):
    head(s, 'Insight III: Combine Prior and Feedback',
         '历史画像决定“从哪里开始”，真实路由决定“接下来保留谁”。\n'
         '编译期给出初始驻留；当热点改变，运行期用最近访问修正快层内容，使位置重新覆盖当前热点。')
    for panel_x, title, hot in [(.89, '阶段 A：画像与真实热点一致', (0,1,2)),
                                (6.89, '阶段 B：在线反馈重新覆盖热点', (3,4,5))]:
        panel(s, panel_x, title)
        for col in range(6):
            old.t(s, panel_x+1.54+col*.57, 3.40, .43, .30, f'E{col+1}', 11, BLUE_DARK)
        for row, (name, selected) in enumerate([
            ('当前热点', hot), ('初始驻留', (0,1,2)), ('在线驻留', hot)]):
            y=4.02+row*.64
            old.t(s, panel_x+.05, y, 1.27, .40, name, 14, BLUE_DARK)
            for col in range(6):
                rect(s, panel_x+1.54+col*.57, y, .44, .38,
                     fill=BLUE_MID if col in selected else GRAY_LIGHT, line=WHITE)
    old.t(s, 1.16, 6.02, 11.00, .30, '深色单元格表示当前热点或快层保留位置；专家身份与阶段均为机制示意。', 13, BLUE_DARK, False)
    footer(s, '洞察 ③：把离线先验和在线反馈放在两个时间尺度上协同使用。')


def dynamic_method(s, assets):
    head(s, 'Method II: Joint HBM–CPU Retention',
         '真实路由驱动专家访问：显存命中直接复用，CPU 命中提升到显存，两层未命中才读取 SSD。\n'
         '下图以显存 2 槽、CPU 2 槽演示联合保留；每列表示一次访问完成后各专家的最快驻留层级。')
    old.t(s, 1.13, 2.64, 11.06, .39, '同一访问序列下的驻留状态演化（机制示意）', 18, BLUE_DARK)
    events = [1, 2, 3, 1, 4, 3, 2]
    gpu, cpu, states = OrderedDict(), OrderedDict(), []
    for eid in events:
        if eid in gpu:
            gpu.move_to_end(eid)
        else:
            cpu.pop(eid, None)
            if len(gpu) == 2:
                evicted, _ = gpu.popitem(last=False)
                cpu[evicted] = None
                if len(cpu) > 2:
                    cpu.popitem(last=False)
            gpu[eid] = None
        states.append({e: 'H' if e in gpu else 'C' if e in cpu else 'S' for e in range(1,5)})
    colors={'H':BLUE_MID, 'C':GRAY_MID, 'S':GRAY_LIGHT}
    for col, event in enumerate(events):
        x=2.19+col*1.40
        old.t(s, x, 3.23, 1.04, .28, f't{col+1}', 12, BLACK, False)
        old.t(s, x, 3.58, 1.04, .36, f'E{event}', 15, BLUE_DARK)
    for row in range(4):
        y=4.14+row*.46
        old.t(s, 1.13, y, .65, .34, f'E{row+1}', 14, BLUE_DARK)
        for col, state in enumerate(states):
            rect(s, 2.19+col*1.40, y, 1.04, .34,
                 fill=colors[state[row+1]], line=BLUE_DARK if events[col]==row+1 else WHITE)
    for j, (lab, color) in enumerate([('显存',BLUE_MID),('CPU',GRAY_MID),('SSD',GRAY_LIGHT)]):
        rect(s, 2.53+j*2.92, 6.09, .22, .22, fill=color, line=BLUE_DARK)
        old.t(s, 2.81+j*2.92, 6.02, 1.22, .34, lab, 13, BLACK, False, PP_ALIGN.LEFT)
    footer(s, 'E1 与 E2 再访时由 CPU 承接；每次迁移均保持原专家权重与路由选择。')


def ablation(s, assets):
    head(s, 'Ablation: Placement Meets Online Retention',
         '组件消融分别保留画像引导、在线更新及两者组合，使用相同的模型、输入与缓存预算。\n'
         '同时比较综合性能与 SSD 访问，检验性能收益能否由缓存行为的变化解释。', True)
    pic(s, assets, 'ablation', .89, 2.67, 11.52)
    footer(s, 'MECC：用编译期先验安排起点，用运行期反馈保留真实工作集。')


def build(template, output):
    assets = output.parent / 'conference_assets'
    data = make_plots(assets)
    old.build(template, output)
    prs = Presentation(output)
    for index, fn in [(3, mot1), (4, mot2), (5, mot3), (8, insight3),
                       (9, overview), (11, dynamic_method), (12, result), (13, ablation)]:
        fn(prs.slides[index], assets)
    titles = {0:'Research Problem: Sparse Access, Large State',
              1:'Related Work: Deployment Gaps',
              2:'MECC: Compile Once, Adapt Online',
              6:'Insight I: Place by Expected Access Cost',
              7:'Insight II: Retain Experts Across Evictions',
              10:'Method I: Budget-Constrained Placement',
              11:'Method II: Joint HBM–CPU Retention'}
    # Title-only edit preserves all template-native components.
    for i, title in titles.items():
        shape = prs.slides[i].shapes.title
        if shape and shape.has_text_frame:
            for p in shape.text_frame.paragraphs:
                if p.runs:
                    p.runs[0].text = title
                    for run in p.runs[1:]: run.text = ''
                    break
    # Improve body line breaks on the retained insight page.
    for shape in prs.slides[7].shapes:
        if shape.has_text_frame and shape.text.startswith('洞察 ②'):
            shape.text_frame.text = ('显存淘汰的专家可在 CPU 层继续保留，CPU 命中后再提升到显存。\n'
                                     '这样，专家复用能够跨越显存淘汰；两层共同保存近期工作集，减少再次读取 SSD。')
            for p in shape.text_frame.paragraphs:
                for run in p.runs:
                    run.font.name='Microsoft YaHei'; run.font.size=Pt(18); run.font.bold=True
    for shape in list(prs.slides[10].shapes):
        if shape.has_text_frame and shape.text.startswith('优化目标'):
            shape._element.getparent().remove(shape._element)
    old.t(prs.slides[10], 1.00, 6.48, 4.96, .40, '优化目标：最小化预期取数代价', 16, BLUE_DARK)
    pic(prs.slides[10], assets, 'cost_equation', 6.20, 6.44, 5.64)
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text in ('K_H','K_H+K_C'):
                label=shape.text
                p=shape.text_frame.paragraphs[0]
                p.clear()
                tokens=[('K',False),('H',True)]
                if '+' in label: tokens += [('+K',False),('C',True)]
                for text, sub in tokens:
                    run=p.add_run(); run.text=text
                    run.font.name='Cambria Math'; run.font.size=Pt(12 if sub else 15)
                    run.font.color.rgb=BLUE_DARK
                    if sub: run._r.get_or_add_rPr().set('baseline','-25000')
    mock_pages = {4, 6, 14}
    for i, slide in enumerate(prs.slides, 1):
        # One visual vocabulary across the native graphics and scientific plots.
        for shape in slide.shapes:
            if shape.has_text_frame:
                for p in shape.text_frame.paragraphs:
                    for run in p.runs:
                        try:
                            if str(run.font.color.rgb) == '2F5496':
                                run.font.color.rgb = RGBColor.from_string('173E65')
                        except (AttributeError, TypeError):
                            pass
            try:
                if shape.fill.type == 1 and str(shape.fill.fore_color.rgb) == '5B9BD5':
                    shape.fill.fore_color.rgb = RGBColor.from_string('2768A8')
            except (AttributeError, TypeError):
                pass
        # Native templates may carry original page numbers; rewrite all red ones.
        for shape in slide.shapes:
            if shape.has_text_frame and shape.top/Inches(1)>6.96 and shape.text.strip().isdigit():
                shape.text_frame.paragraphs[0].runs[0].text = str(i)
        if i>=13:
            old.t(slide, 12.23, 7.02, .48, .30, str(i), 17, old.RED, False)
        slide.notes_slide.notes_text_frame.text = (
            f'MECC conference talk / slide {i}. '
            + ('MOCK EXPERIMENT: illustrative numbers only; replace before reporting results. '
               if i in mock_pages else 'Mechanism illustrations are schematic; measured values follow PROVENANCE. ')
            + 'Figures: conference_assets/presentation_data.json. '
            + 'References for plot design: Fiddler ICLR 2025 Fig.4–6; MoE-Lightning ASPLOS 2025 Fig.7.'
        )
    prs.save(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--template', type=Path, default=Path('C:/Users/zhaoy/Desktop/1013.pptx'))
    parser.add_argument('--out', type=Path, default=HERE/'MECC_conference_talk.pptx')
    args = parser.parse_args()
    build(args.template, args.out)
