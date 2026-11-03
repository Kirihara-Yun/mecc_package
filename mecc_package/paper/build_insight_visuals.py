"""Conference-talk concept figures for the three MECC insights.

These figures are schematics. The probabilities and access windows illustrate
state transitions; they are not measurements or exported experiment results.
"""

from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, PathPatch
from matplotlib.path import Path as MplPath
import numpy as np

OUT = Path(__file__).resolve().parent / 'current' / 'insight_figures'
OUT.mkdir(parents=True, exist_ok=True)

NAVY = '#152B3C'
BLUE = '#2768A8'
MID = '#7EA7CF'
INK = '#273743'
MUTED = '#6C7C89'
LIGHT = '#E9EEF2'
GREY = '#A7B2BB'
AMBER = '#D98632'
WHITE = '#FFFFFF'

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Microsoft YaHei', 'Arial'],
    'font.size': 14,
    'svg.fonttype': 'none',
    'pdf.fonttype': 42,
})


def canvas():
    fig = plt.figure(figsize=(12, 4), dpi=240, facecolor='white')
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4)
    ax.axis('off')
    return fig, ax


def mini_canvas():
    fig = plt.figure(figsize=(4.4, 1.65), dpi=240, facecolor='white')
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 4.4)
    ax.set_ylim(0, 1.65)
    ax.axis('off')
    return fig, ax


def save(fig, stem):
    for ext in ('png', 'svg', 'pdf'):
        fig.savefig(OUT / f'{stem}.{ext}', dpi=240, facecolor='white',
                    bbox_inches='tight', pad_inches=.03)
    plt.close(fig)


def label(ax, x, y, txt, *, size=14, color=INK, weight='normal', ha='left', va='center'):
    ax.text(x, y, txt, fontsize=size, color=color, fontweight=weight,
            ha=ha, va=va, zorder=10)


def placement():
    fig, ax = canvas()
    xs = np.linspace(1.05, 10.95, 8)
    p = np.array([.23, .19, .16, .13, .105, .08, .061, .044])
    h = p / p.max() * 2.36
    base = .91
    label(ax, .39, 3.58, '专家访问概率', size=16, color=NAVY, weight='bold')
    label(ax, 11.55, 3.58, '热度排序 →', size=11, color=MUTED, ha='right')
    ax.plot(xs, base + h, color=NAVY, linewidth=2.3, zorder=3)
    for i, (x, hh) in enumerate(zip(xs, h)):
        col = BLUE if i < 2 else MID if i < 5 else GREY
        ax.vlines(x, base, base + hh, color=col, linewidth=5.2, zorder=2)
        ax.scatter([x], [base + hh], s=100, color=col,
                   edgecolor=WHITE, linewidth=1.5, zorder=4)
        label(ax, x, .64, f'E{i+1}', size=12, color=NAVY, weight='bold', ha='center')
    ax.hlines(base, .55, 11.47, color=LIGHT, linewidth=1.6)
    cuts = [(xs[1]+xs[2])/2, (xs[4]+xs[5])/2]
    for x in cuts:
        ax.vlines(x, .72, 3.48, color=AMBER, linewidth=1.8, linestyles='dashed')
    label(ax, cuts[0], 3.68, '显存预算', size=13, color=AMBER, weight='bold', ha='center')
    label(ax, cuts[1], 3.68, 'CPU 预算', size=13, color=AMBER, weight='bold', ha='center')
    spans = [(0.55, cuts[0], '显存', BLUE),
             (cuts[0], cuts[1], 'CPU', MID),
             (cuts[1], 11.47, 'SSD', GREY)]
    for lo, hi, name, color in spans:
        ax.hlines(.28, lo, hi, color=color, linewidth=5.3)
        label(ax, (lo+hi)/2, .075, name, size=14, color=NAVY,
              weight='bold', ha='center')
    save(fig, 'insight1_rank_cut')


def ribbon(ax, x0, x1, y0, y1, *, width, color, alpha=1, zorder=2):
    """A continuous expert trajectory between two cache states."""
    half = width / 2
    mid = (y0 + y1) / 2
    verts = [
        (x0-half, y0), (x0-half, mid), (x1-half, mid), (x1-half, y1),
        (x1+half, y1), (x1+half, mid), (x0+half, mid), (x0+half, y0),
        (x0-half, y0),
    ]
    codes = [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
             MplPath.LINETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
             MplPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MplPath(verts, codes), facecolor=color,
                           edgecolor='none', alpha=alpha, zorder=zorder))


def retention():
    fig, ax = canvas()
    x = np.array([2.00, 3.95, 5.90, 7.85, 9.80])
    cut = (x[1] + x[2]) / 2
    top, bottom = 3.00, .90
    slot_width, slot_height = 1.35, .48

    # A single ranked stack is split by one capacity boundary. The ribbons
    # make the two coupled cache moves visible without a process-flow diagram.
    label(ax, .35, 3.50, '访问前', size=15, color=NAVY, weight='bold')
    label(ax, .35, .38, '访问后', size=15, color=NAVY, weight='bold')
    label(ax, 3.02, 3.50, '显存', size=13, color=BLUE, weight='bold', ha='center')
    label(ax, 7.86, 3.50, 'CPU', size=13, color=MUTED, weight='bold', ha='center')
    ax.hlines(3.28, 1.18, cut, color=BLUE, linewidth=3.5)
    ax.hlines(3.28, cut, 10.62, color=MID, linewidth=3.5)
    ax.hlines(.62, 1.18, cut, color=BLUE, linewidth=3.5)
    ax.hlines(.62, cut, 10.62, color=MID, linewidth=3.5)
    label(ax, cut, 3.72, '显存容量', size=12, color=AMBER,
          weight='bold', ha='center')
    ax.vlines(cut, 3.20, 3.57, color=AMBER, linewidth=2)
    ax.vlines(cut, .53, .73, color=AMBER, linewidth=2)

    before = ['E1', 'E2', 'E3', 'E4', 'E5']
    after = ['E3', 'E1', 'E2', 'E4', 'E5']
    destinations = {name: after.index(name) for name in before}
    for i, name in enumerate(before):
        j = destinations[name]
        col = AMBER if name == 'E3' else BLUE if name == 'E2' else GREY
        strength = .80 if name == 'E3' else .64 if name == 'E2' else .23
        ribbon(ax, x[i], x[j], top-.26, bottom+.26,
               width=.24 if name in ('E2', 'E3') else .11,
               color=col, alpha=strength, zorder=2 if name not in ('E2','E3') else 3)

    for y, names in [(top, before), (bottom, after)]:
        for i, name in enumerate(names):
            fill = '#FFF1DF' if name == 'E3' else '#E9F0F7' if i < 2 else '#EEF1F3'
            edge = AMBER if name == 'E3' else BLUE if i < 2 else GREY
            ax.add_patch(Rectangle((x[i]-slot_width/2, y-slot_height/2),
                                   slot_width, slot_height,
                                   facecolor=fill, edgecolor=edge,
                                   linewidth=1.4, zorder=5))
            label(ax, x[i], y, name, size=14, color=NAVY,
                  weight='bold', ha='center')

    save(fig, 'insight2_joint_stack')


def adaptation():
    fig, ax = canvas()
    experts = ['E1', 'E2', 'E3', 'E6', 'E7', 'E8']
    x0, dx, cw = 2.06, .91, .70
    top_y, lower_y = 3.39, 1.45
    label(ax, .28, 3.47, '真实路由', size=16, color=NAVY, weight='bold')
    label(ax, .28, 1.53, '快层驻留', size=16, color=NAVY, weight='bold')
    for j in range(10):
        label(ax, x0+j*dx+cw/2, 3.96, f't{j+1}', size=11,
              color=MUTED, ha='center')
    for row, e in enumerate(experts):
        yt = top_y-row*.25
        yb = lower_y-row*.25
        label(ax, 1.70, yt+.09, e, size=11, color=MUTED, ha='center')
        label(ax, 1.70, yb+.09, e, size=11, color=MUTED, ha='center')
        for j in range(10):
            active = row < 3 if j < 4 else row >= 3
            resident = (row < 3 if j <= 4 else
                        e in ('E2', 'E6', 'E7') if j == 5 else row >= 3)
            for yy, on in [(yt, active), (yb, resident)]:
                ax.add_patch(Rectangle((x0+j*dx, yy), cw, .18,
                                       facecolor=BLUE if on else LIGHT,
                                       edgecolor='none'))
    switch_x = x0+4*dx-.10
    ax.vlines(switch_x, .15, 3.58, color=AMBER, linewidth=1.8,
              linestyles='dashed')
    label(ax, switch_x, 3.67, '任务切换', size=13, color=AMBER,
          weight='bold', ha='center')
    label(ax, 11.25, 2.70, '访问先变', size=12, color=INK, weight='bold')
    label(ax, 11.25, .74, '驻留跟进', size=12, color=INK, weight='bold')
    save(fig, 'insight3_route_feedback')


def placement_across_layers():
    """Schematic compiler output: the same capacity rule, different hot experts."""
    fig, ax = mini_canvas()
    label(ax, .10, 1.43, '逐层生成驻留表', size=13, color=NAVY, weight='bold')
    rows = [
        ['H', 'H', 'C', 'C', 'C', 'S', 'S', 'S'],
        ['C', 'S', 'C', 'H', 'H', 'C', 'S', 'S'],
        ['H', 'C', 'S', 'C', 'S', 'H', 'S', 'C'],
    ]
    colors = {'H': BLUE, 'C': MID, 'S': '#C5CFD7'}
    for row, tiers in enumerate(rows):
        y = 1.09 - row*.31
        label(ax, .11, y+.07, f'L{row+1}', size=10, color=MUTED, weight='bold')
        for col, tier in enumerate(tiers):
            ax.add_patch(Rectangle((.49+col*.39, y), .31, .16,
                                   facecolor=colors[tier], edgecolor='none'))
    for x, name, col in [(1.03, '显存', BLUE), (2.12, 'CPU', MID), (3.17, 'SSD', '#C5CFD7')]:
        ax.add_patch(Rectangle((x, .10), .14, .11, facecolor=col, edgecolor='none'))
        label(ax, x+.19, .155, name, size=9.5, color=MUTED)
    save(fig, 'insight1_layer_plan')


def retained_revisit():
    """A revisit example that distinguishes fixed and jointly updated CPU sets."""
    fig, ax = mini_canvas()
    label(ax, .10, 1.43, 'E2 再次被路由选中', size=13, color=NAVY, weight='bold')
    for y, policy, tier, col in [(.96, '固定 CPU 集合', 'SSD', GREY),
                                 (.48, '联合更新', 'CPU', MID)]:
        label(ax, .10, y, policy, size=10.5, color=INK)
        ax.hlines(y, 2.02, 3.22, color=LIGHT, linewidth=2)
        ax.scatter([2.05], [y], s=95, color=AMBER, zorder=3)
        label(ax, 2.05, y-.21, 'E2', size=9, color=MUTED, ha='center')
        ax.add_patch(Rectangle((3.35, y-.17), .72, .34,
                               facecolor=col, edgecolor='none'))
        label(ax, 3.71, y, tier, size=10.5, color=WHITE if tier=='SSD' else NAVY,
              weight='bold', ha='center')
    save(fig, 'insight2_revisit')


def rank_inversion():
    """Compact hot-set swap behind the route/residency time matrix."""
    fig, ax = mini_canvas()
    label(ax, .10, 1.43, '任务切换改变高频专家', size=13, color=NAVY, weight='bold')
    for y, task, selected in [(1.00, '任务 A', {0,1,2}),
                              (.48, '任务 B', {5,6,7})]:
        label(ax, .10, y, task, size=10.5, color=INK, weight='bold')
        for i in range(8):
            x = 1.10 + i*.38
            ax.add_patch(Rectangle((x, y-.11), .31, .22,
                                   facecolor=BLUE if i in selected else LIGHT,
                                   edgecolor='none'))
            label(ax, x+.155, y, str(i+1), size=8.5,
                  color=WHITE if i in selected else MUTED, ha='center')
    save(fig, 'insight3_rank_shift')


if __name__ == '__main__':
    placement()
    retention()
    adaptation()
    placement_across_layers()
    retained_revisit()
    rank_inversion()
    print(OUT)
