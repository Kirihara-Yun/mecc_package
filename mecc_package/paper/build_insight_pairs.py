"""Equal-weight mechanism and ablation figures for Insight slides 7–9.

The ablation values are authored design targets in dac2027/ideal_assumptions.json.
They are not measurements. The mechanism diagrams are schematics.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from media_hdd import figure_text
from matplotlib.patches import Rectangle, PathPatch
from matplotlib.path import Path as MplPath
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'current' / 'insight_figures'
OUT.mkdir(parents=True, exist_ok=True)
DATA = json.loads((HERE / 'dac2027' / 'ideal_assumptions.json').read_text(encoding='utf-8'))['insight_ablation_targets']

NAVY = '#172B3B'
BLUE = '#4279A8'
MID = '#84AFBD'
GREY = '#A8ADB3'
LIGHT = '#E7EDF2'
AMBER = '#D59A60'
WHITE = '#FFFFFF'

plt.rcParams.update({
    'font.family': ['Times New Roman', 'SimSun'],
    'svg.fonttype': 'none',
    'pdf.fonttype': 42,
    'hatch.linewidth': 1.0,
})


def save(fig, name):
    figure_text(fig)
    for ext in ('png', 'svg', 'pdf'):
        fig.savefig(OUT / f'{name}.{ext}', dpi=240, facecolor=WHITE,
                    bbox_inches='tight', pad_inches=.025)
    plt.close(fig)


def mechanism_canvas():
    fig = plt.figure(figsize=(6, 4.2), dpi=240, facecolor=WHITE)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 4.2)
    ax.axis('off')
    return fig, ax


def txt(ax, x, y, value, *, size=12, color=NAVY, weight='normal', ha='left'):
    ax.text(x, y, value, fontsize=size, color=color, fontweight=weight,
            ha=ha, va='center', zorder=10)


def placement_mechanism():
    fig, ax = mechanism_canvas()
    txt(ax, .35, 3.84, '一次前向依次经过这些层', size=14, weight='bold')
    txt(ax, 5.62, 3.84, '热 → 冷', size=11, color='#687A88', ha='right')
    rows = [
        ('第1层', ['A2','A5','A4','A1','A8','A3','A6','A7'], 2, 5),
        ('第2层', ['B7','B1','B3','B8','B2','B6','B4','B5'], 3, 5),
        ('第3层', ['C6','C3','C8','C2','C1','C4','C5','C7'], 1, 5),
    ]
    x0, dx, cw = 1.12, .57, .48
    for row, (layer, experts, kh, kc) in enumerate(rows):
        y = 3.03 - row*1.04
        txt(ax, .10, y+.24, layer, size=11.5, weight='bold')
        for i, expert in enumerate(experts):
            color = BLUE if i < kh else MID if i < kc else GREY
            ax.add_patch(Rectangle((x0+i*dx, y), cw, .48,
                                   facecolor=color, edgecolor='none'))
            txt(ax, x0+i*dx+cw/2, y+.24, expert, size=11,
                color=WHITE if i < kh else NAVY, weight='bold', ha='center')
        ax.hlines(y-.13, x0, x0+kh*dx-.10, color=BLUE, linewidth=3)
        ax.hlines(y-.13, x0+kh*dx-.10, x0+kc*dx-.10, color=MID, linewidth=3)
        ax.hlines(y-.13, x0+kc*dx-.10, x0+8*dx-.10, color=GREY, linewidth=3)
    for x, color, label in [(1.04, BLUE, '显存'), (2.75, MID, 'CPU'), (4.39, GREY, 'SSD')]:
        ax.add_patch(Rectangle((x, .18), .17, .12, facecolor=color, edgecolor='none'))
        txt(ax, x+.25, .24, label, size=11)
    save(fig, 'pair7_mechanism')


def ribbon(ax, x0, x1, y0, y1, color, width, alpha=1):
    half = width / 2
    mid = (y0 + y1) / 2
    verts = [(x0-half,y0), (x0-half,mid), (x1-half,mid), (x1-half,y1),
             (x1+half,y1), (x1+half,mid), (x0+half,mid), (x0+half,y0),
             (x0-half,y0)]
    codes = [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
             MplPath.LINETO, MplPath.CURVE4, MplPath.CURVE4,
             MplPath.CURVE4, MplPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MplPath(verts, codes), facecolor=color,
                           edgecolor='none', alpha=alpha, zorder=2))


def retention_mechanism():
    fig, ax = mechanism_canvas()
    xs = np.array([.88, 1.91, 2.94, 3.97, 5.00])
    before = ['E1','E2','E3','E4','E5']
    after = ['E3','E1','E2','E4','E5']
    top, bottom = 3.13, .93
    cut = (xs[1]+xs[2])/2
    txt(ax, .20, 3.83, '一次 CPU 内存访问，同时更新两级缓存', size=14, weight='bold')
    for y, names, phase in [(top, before, '访问前'), (bottom, after, '访问后')]:
        txt(ax, .12, y+.52, phase, size=11, weight='bold')
        ax.hlines(y+.37, .53, cut, color=BLUE, linewidth=3)
        ax.hlines(y+.37, cut, 5.57, color=MID, linewidth=3)
        for i, name in enumerate(names):
            col = AMBER if name=='E3' else BLUE if i<2 else GREY
            fill = '#FFF0DE' if name=='E3' else '#E5EFF7' if i<2 else '#EFF2F4'
            ax.add_patch(Rectangle((xs[i]-.35,y-.23), .70,.46,
                                   facecolor=fill, edgecolor=col, linewidth=1.4,
                                   zorder=4))
            txt(ax, xs[i], y, name, size=13, weight='bold', ha='center')
    for name in before:
        i, j = before.index(name), after.index(name)
        col = AMBER if name=='E3' else BLUE if name=='E2' else GREY
        ribbon(ax, xs[i], xs[j], top-.24, bottom+.24, col,
               .17 if name in ('E2','E3') else .07,
               .86 if name in ('E2','E3') else .23)
    txt(ax, 1.46, .30, '显存', size=11, color=BLUE, weight='bold', ha='center')
    txt(ax, 4.02, .30, 'CPU', size=11, color='#6A7C89', weight='bold', ha='center')
    save(fig, 'pair8_mechanism')


def adaptation_mechanism():
    fig, ax = mechanism_canvas()
    txt(ax, .20, 3.83, '专家访问变化后，缓存随之更新', size=14, weight='bold')
    experts = ['E1','E2','E6','E7']
    x0, dx, cw = 1.38, .55, .43
    for j in range(8):
        txt(ax, x0+j*dx+cw/2, 3.43, f't{j+1}', size=9.5,
            color='#70818E', ha='center')
    for row, (title, ybase) in enumerate([('路由选择', 2.89), ('显存与内存缓存', 1.31)]):
        txt(ax, .08, ybase+.04, title, size=12, weight='bold')
        for i, expert in enumerate(experts):
            y = ybase-i*.28
            txt(ax, 1.04, y+.08, expert, size=9.5, color='#70818E', ha='center')
            for j in range(8):
                route_hot = i < 2 if j < 3 else i >= 2
                resident = (i < 2 if j <= 3 else
                            expert in ('E2','E6') if j==4 else i>=2)
                on = route_hot if row==0 else resident
                ax.add_patch(Rectangle((x0+j*dx,y),cw,.17,
                                       facecolor=BLUE if on else LIGHT,
                                       edgecolor='none'))
    switch_x = x0+3*dx-.07
    ax.vlines(switch_x, .32, 3.10, color=AMBER, linewidth=1.6,
              linestyles='dashed')
    txt(ax, switch_x, 3.20, '任务切换', size=10.5, color=AMBER,
        weight='bold', ha='center')
    save(fig, 'pair9_mechanism')


def ablation_chart(name, series, models):
    fig = plt.figure(figsize=(6, 4.2), dpi=240, facecolor=WHITE)
    ax = fig.add_axes([.13, .23, .84, .62])
    names = list(series)
    values = np.array([series[n] for n in names], dtype=float)
    assert values.shape == (3, len(models)), f'{name}: require three baselines and one value per model'
    centers = np.arange(len(models))
    width = .22
    patterns = ['///', '\\\\', 'xxx']
    fills = ['#9CC1DC', '#E7BD91', '#88B8A3']
    display = {
        'Equal layer budgets': '平均分配',
        'Global hotness': '全局排序',
        'Per-layer profile': '逐层统计',
        'Fixed CPU': 'CPU 固定',
        'Independent LRU': '独立更新',
        'Joint LRU': '联合更新',
        'Fixed residency': '固定缓存',
    }
    for i, (policy, vals) in enumerate(zip(names, values)):
        ax.bar(centers+(i-1)*width, vals, width=.19,
               color=fills[i], edgecolor=NAVY, linewidth=.85,
               hatch=patterns[i], label=display[policy], zorder=3)
    ax.set_xlim(-.55, len(models)-.45)
    ax.set_ylim(0, np.ceil(values.max()/10)*10+5)
    ax.set_ylabel('每 token 时间（秒）', fontsize=11, color=NAVY)
    labels = [s.replace(' 8×', '\n8×').replace(' 57B', '\n57B') for s in models]
    ax.set_xticks(centers, labels, fontsize=10.5)
    ax.tick_params(axis='y', labelsize=9.5, colors='#5E7180', length=0)
    ax.tick_params(axis='x', length=0, pad=8)
    ax.grid(axis='y', color=LIGHT, linewidth=.8, zorder=0)
    for spine in ('top','right','left'):
        ax.spines[spine].set_visible(False)
    ax.spines['bottom'].set_color('#B8C4CE')
    ax.legend(loc='upper center', bbox_to_anchor=(.5,1.22), ncol=3,
              fontsize=9.2, frameon=False, handlelength=1.1,
              columnspacing=.9, handletextpad=.35)
    save(fig, name)


def build():
    placement_mechanism()
    retention_mechanism()
    adaptation_mechanism()
    ablation_chart('pair7_ablation', DATA['placement_same_runtime'],
                   DATA['stationary_workloads'])
    ablation_chart('pair8_ablation', DATA['retention_same_initial_plan'],
                   DATA['stationary_workloads'])
    ablation_chart('pair9_ablation', DATA['adaptation_same_initial_plan'],
                   DATA['shift_workloads'])


if __name__ == '__main__':
    build()
    print(OUT)
