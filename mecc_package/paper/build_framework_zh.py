"""Draw the paper's framework with Chinese labels and make a deck variant.

The English manuscript figure remains untouched. This is a schematic figure;
no performance values are generated here.
"""
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches

sys.path.insert(0, str(Path(__file__).resolve().parent / 'dac2027'))
from build_paper_figures import (BLUE, GRAY, INK, PALE, RULE, TEAL,
                                 arrow, box, text)

OUT = Path(__file__).resolve().parent / 'current'
OUT.mkdir(exist_ok=True)


def draw():
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS'],
        'mathtext.fontset': 'stix',
        'pdf.fonttype': 42,
        'svg.fonttype': 'none',
        'text.color': INK,
    })
    fig, ax = plt.subplots(figsize=(7.05, 2.48))
    fig.subplots_adjust(left=.005, right=.995, bottom=.015, top=.99)
    ax.set(xlim=(0, 100), ylim=(-1.5, 33))
    ax.axis('off')

    box(ax, .5, 1, 30.5, 29.5, PALE, RULE, .65)
    box(ax, 35, 1, 64, 29.5, 'white', RULE, .65)
    text(ax, 15.8, 32, '部署前：编译放置', 9, weight='bold')
    text(ax, 67, 32, '服务时：查找与执行', 9, weight='bold')

    for r in range(3):
        for j, v in enumerate([.92, .7, .45, .25, .13, .06]):
            box(ax, 3.2+j*1.75, 25-r*1.6, 1.48, 1.25,
                plt.cm.Blues(.12+.8*v), 'white', .3)
    text(ax, 8.4, 28.4, '专家访问画像', 7.6)
    text(ax, 23, 27, '模型信息', 7.5)
    text(ax, 23, 24.7, '任务内存额度', 7.5)
    text(ax, 23, 22.4, '权重搬运代价', 7.5)
    arrow(ax, (8.4, 21.4), (8.4, 19.5), GRAY, '--')
    arrow(ax, (23, 21.4), (23, 19.5), GRAY, '--')
    box(ax, 3.0, 13, 25.5, 6.0, 'white', BLUE, .9)
    text(ax, 15.8, 17.0, '放置编译器', 8.5, weight='bold')
    text(ax, 15.8, 14.7, '排序专家 · 分配驻留槽位', 7.4)
    arrow(ax, (15.8, 12.8), (15.8, 10.6), GRAY, '--')
    box(ax, 3.0, 3, 25.5, 7, 'white', BLUE, .9)
    text(ax, 15.8, 8.3, '初始驻留计划', 8.5, weight='bold')
    text(ax, 15.8, 6.2, r'$K_{\mathrm{H},\ell}$, $K_{\mathrm{C},\ell}$', 8)
    text(ax, 15.8, 4.3, '按热度排序的专家编号', 7.5)

    ax.plot([28.6, 33, 33], [6.4, 6.4, 17.1], c=GRAY, lw=.8, ls='--')
    arrow(ax, (33, 17.1), (37.7, 17.1), GRAY, '--')
    arrow(ax, (33, 10.6), (37.7, 10.6), GRAY, '--')
    text(ax, 45.8, 28.4, '路由器（保持不变）', 8)
    for xx, e in [(40.6, 2), (46.7, 6)]:
        box(ax, xx, 24.3, 4.4, 2.5, '#E6EFF6', BLUE, .7)
        text(ax, xx+2.2, 25.55, rf'$e_{e}$', 8)
    arrow(ax, (51.5, 25.5), (55.3, 25.5), GRAY, '--')
    box(ax, 55.6, 23.3, 17, 4.4, PALE, INK, .75)
    text(ax, 64.1, 25.5, '查找专家驻留位置', 8)
    arrow(ax, (72.8, 25.5), (79.4, 25.5), GRAY, '--')
    box(ax, 79.7, 22.3, 17.3, 6.4, '#E6EFF6', BLUE, .9)
    text(ax, 88.4, 26.6, 'GPU 专家计算', 8.3, weight='bold')
    text(ax, 88.4, 24.2, '执行被选中的专家', 7.4)

    tiers = [('显存（HBM）', 15.2, BLUE, [0, 1, 3]),
             ('CPU 锁页\n内存', 8.7, TEAL, [2, 4, 5]),
             ('SSD 完整\n权重', 2.2, GRAY, list(range(8)))]
    for label, y, color, ids in tiers:
        box(ax, 38, y, 32, 4.0, 'white', color, .85)
        text(ax, 44.7, y+2, label, 7.3)
        step, width = (2.13, 1.92) if len(ids) > 4 else (5.65, 4.9)
        for j, e in enumerate(ids):
            xx = 52+j*step
            box(ax, xx, y+.8, width, 2.4, color, 'white', .35)
            text(ax, xx+width/2, y+2, rf'$e_{e}$', 7, color='white')

    arrow(ax, (48.4, 15.0), (48.4, 13.0), BLUE)
    text(ax, 43.1, 13.9, '降入 CPU', 6.8)
    arrow(ax, (62.8, 13.0), (62.8, 15.0), TEAL)
    text(ax, 66.7, 13.9, '提升至显存', 6.8)
    box(ax, 79.7, 8.7, 17.3, 6.0, PALE, TEAL, .85)
    text(ax, 88.4, 12.9, '权重搬运', 8, weight='bold')
    text(ax, 88.4, 10.5, '读取 · 暂存 · 传至显存', 7.2)
    arrow(ax, (70.2, 10.8), (79.4, 10.8), TEAL)
    ax.plot([70.2, 75.4, 75.4], [4.2, 4.2, 9.0], c=GRAY, lw=.8)
    arrow(ax, (75.4, 9.0), (79.4, 9.0), GRAY)
    ax.plot([70.2, 75.4, 75.4], [17.2, 17.2, 23], c=BLUE, lw=.8)
    arrow(ax, (75.4, 23), (79.4, 23), BLUE)
    arrow(ax, (83, 14.9), (83, 22), TEAL)
    arrow(ax, (92.0, 14.9), (92.0, 22), GRAY, '--')
    text(ax, 96.0, 18.5, '就绪事件', 7.0)
    text(ax, 83, 4.8, '完整专家权重\n始终保存在 SSD', 7.4, color=GRAY)
    text(ax, 50, -.55, '虚线：控制与计划信息     实线：权重搬运', 7.3)

    for ext in ('png', 'svg', 'pdf'):
        fig.savefig(OUT / f'framework_zh.{ext}', dpi=320,
                    bbox_inches='tight', pad_inches=.025, facecolor='white')
    plt.close(fig)


def deck_variant():
    source = OUT / 'MECC_HPCA_current.pptx'
    prs = Presentation(source)
    slide = prs.slides[9]
    pictures = [shape for shape in slide.shapes if shape.shape_type == 13]
    assert len(pictures) == 1, 'expected one framework picture on slide 10'
    old = pictures[0]
    left, top, width = old.left, old.top, old.width
    old._element.getparent().remove(old._element)
    slide.shapes.add_picture(str(OUT / 'framework_zh.png'), left, top,
                             width=width)
    dest = OUT / 'MECC_HPCA_framework_zh.pptx'
    prs.save(dest)
    return dest


if __name__ == '__main__':
    draw()
    print(deck_variant())
