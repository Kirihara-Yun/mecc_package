"""Build a 14-slide paper-style MECC group talk from the 1013 template."""

from __future__ import annotations

import argparse
from math import log10
from pathlib import Path

from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN

from build_mecc_first3 import (
    BLACK, BLUE, BLUE_DARK, BLUE_LIGHT, BLUE_MID, GRAY, GRAY_LIGHT,
    GRAY_MID, WHITE, arrow, caption, circle, clean_slide, panel_title,
    RED, rect, retain_slides, text_box,
)


def t(slide, x, y, w, h, s, size=14, color=BLACK, bold=True, align=PP_ALIGN.CENTER):
    return text_box(slide, x, y, w, h, s, size=size, color=color, bold=bold, align=align)


def box(slide, x, y, w, h, s="", fill=WHITE, line=BLUE_DARK, size=15):
    return rect(slide, x, y, w, h, s, fill=fill, line=line, size=size, color=BLUE_DARK)


def note(slide, s):
    # Research caveats and provenance live in the accompanying speaker notes,
    # not on the group-meeting slides.
    return None


def heading(slide, title, explanation, *, explanation_size=16,
            explanation_y=0.96, explanation_height=0.94):
    clean_slide(slide, title)
    rect(slide, 0.93, 1.06, 0.16, 0.16, fill=WHITE, line=BLUE, size=10)
    shape = text_box(slide, 1.25, explanation_y, 11.0, explanation_height, explanation,
                     size=explanation_size, color=BLACK, bold=True,
                     align=PP_ALIGN.LEFT, valign=MSO_ANCHOR.TOP)
    shape.text_frame.word_wrap = True


def row(slide, y, label, cells, widths, *, highlight=False):
    x = 0.83
    fill = BLUE_LIGHT if highlight else WHITE
    box(slide, x, y, widths[0], 0.54, label, fill, BLUE_DARK if highlight else GRAY_MID, 13)
    x += widths[0]
    for value, width in zip(cells, widths[1:]):
        box(slide, x, y, width, 0.54, value, fill, BLUE_DARK if highlight else GRAY_MID, 12)
        x += width


def draw_layers(slide, x=1.0, y=2.15, w=3.1, *, label_size=15):
    for i, (label, fill) in enumerate((('GPU 显存\n专家就地计算', BLUE_LIGHT), ('CPU 内存\n传输后在 GPU 计算', GRAY_LIGHT), ('SSD\n保存完整专家集合', WHITE))):
        box(slide, x, y + i * 1.15, w, 0.86, label, fill, BLUE_DARK, label_size)
        if i < 2:
            arrow(slide, x + w / 2 - .09, y + .89 + i * 1.15, .18, .23, direction='down', color=BLUE)


def slide1(s):
    heading(s, 'Research Problem',
            'MoE 每次只激活少数专家，但全部专家都要随时可访问。\n'
            '专家权重可能放在 GPU 显存、CPU 内存或 SSD。\n'
            '选中 SSD 上的专家会产生读取等待；MECC 要减少这种等待。',
            explanation_size=21, explanation_y=0.95, explanation_height=1.22)
    t(s, .94, 2.54, 5.44, .42, '本 token 的稀疏激活', 18, BLUE_DARK)
    t(s, 6.92, 2.54, 5.44, .42, '完整专家集合的三级驻留', 18, BLUE_DARK)
    rect(s, .93, 3.07, 5.40, .018, fill=GRAY_MID, line=GRAY_MID)
    rect(s, 6.91, 3.07, 5.40, .018, fill=GRAY_MID, line=GRAY_MID)
    for i in range(12):
        x = 1.16 + (i % 6) * .82
        y = 3.42 + (i // 6) * .83
        active = i in (1, 8)
        circle(s, x, y, .55, f'E{i+1}', fill=BLUE if active else GRAY_LIGHT,
               line=BLUE_DARK if active else GRAY,
               color=WHITE if active else BLACK, size=12)
    circle(s, 1.63, 5.36, .25, fill=BLUE, line=BLUE_DARK)
    t(s, 1.94, 5.25, 1.35, .47, '本次激活', 16, BLUE_DARK, align=PP_ALIGN.LEFT)
    circle(s, 3.68, 5.36, .25, fill=GRAY_LIGHT, line=GRAY)
    t(s, 3.98, 5.25, 1.35, .47, '未激活', 16, BLACK, align=PP_ALIGN.LEFT)
    for row, (lab, ids, fill) in enumerate((
        ('显存', ('E1', 'E2', 'E3'), BLUE_LIGHT),
        ('CPU', ('E4', 'E5', 'E6', 'E7'), GRAY_MID),
        ('SSD', ('E8', 'E9', 'E10', '…'), GRAY_LIGHT),
    )):
        y = 3.37 + row * .82
        t(s, 6.94, y, 1.03, .48, lab, 16, BLUE_DARK)
        for j, eid in enumerate(ids):
            x = 8.04 + j * .92
            selected = eid == 'E9'
            rect(s, x, y, .78, .48,
                 fill=BLUE_MID if selected else fill,
                 line=BLUE_DARK if selected else WHITE)
            t(s, x, y, .78, .48, eid, 13,
              WHITE if selected else BLACK)
    t(s, 7.25, 5.98, 4.74, .41, 'E9 被选中，却仍在 SSD', 16, BLUE_DARK)
    t(s, 1.52, 6.49, 10.21, .42,
      '关键代价：被路由选中的冷专家必须从 SSD 读取，生成因此等待。', 17, BLUE_DARK)


def slide2(s):
    heading(s, 'Related Work',
            '现有系统已能跨显存、内存和 SSD 按需执行专家，并在推理时保留常用专家。\n'
            '共享服务器还需要回答：给定单任务预算如何安排驻留、如何减少初始冷读、\n'
            '以及部署前如何估计 SSD 压力。MECC 将这三项能力纳入同一方案。',
            explanation_size=18, explanation_height=1.10)
    widths = [1.85, 1.73, 1.73, 1.73, 1.73, 1.73, 1.73]
    headers = ['方法', '三级存储\n支撑', '完整专家\n计算', '按预算生成\n驻留方案',
               '历史热点\n预热', '冷读压力\n预估', '在线适应\n热点变化']
    x = .57
    for label, width in zip(headers, widths):
        rect(s, x, 2.18, width, .72, fill=WHITE, line=BLACK)
        t(s, x, 2.19, width, .69, label, 14, BLACK)
        x += width
    entries = [
        ('SwapMoE¹',       (False, False, False, True,  False, True)),
        ('Fiddler²',       (False, True,  False, False, False, False)),
        ('MoE-Infinity³',  (False, True,  False, False, False, True)),
        ('MoE-Lightning⁴',(False, True,  False, False, False, False)),
        ('SSD-LLaMA⁵',     (True,  True,  False, False, False, True)),
        ('MECC',           (True,  True,  True,  True,  True,  True)),
    ]
    for i, (name, values) in enumerate(entries):
        y = 3.02 + i * .55
        fill = WHITE
        ink = BLACK
        x = .57
        rect(s, x, y, widths[0], .51, fill=fill, line=BLACK)
        t(s, x, y, widths[0], .51, name, 15, ink)
        x += widths[0]
        for value, width in zip(values, widths[1:]):
            rect(s, x, y, width, .51, fill=fill, line=BLACK)
            t(s, x, y-.03, width, .57, '✓' if value else '✗', 25,
              ink, True)
            x += width
    note(s, '表按论文公开报告的部署能力比较，✗ 表示未报告对应能力，不代表技术上无法实现。MECC 的预算规划、热点预热和 SSD 命中率预估均为编译期支持功能；预估值不是真机性能保证。SSD-LLaMA 已具备三级动态缓存和完整专家执行，不能误标为缺失。')


def slide3(s):
    heading(s, 'Our Work: MECC',
            'MECC 用两种时间尺度解决三级专家驻留问题：部署前按访问画像与预算确定初始位置，'
            '运行期随真实路由更新显存和 CPU 缓存。'
            '这种协同在 A100 Mixtral 的完整推理中得到验证。',
            explanation_size=18, explanation_height=1.14)
    xs = (1.02, 5.00, 8.98)
    titles = ('编译期：预算放置', '运行期：联合保留', '真机：端到端验证')
    for x, title in zip(xs, titles):
        t(s, x, 2.51, 3.31, .42, title, 17, BLUE_DARK)
        rect(s, x, 3.02, 3.31, .018, fill=GRAY_MID, line=GRAY_MID)
    t(s, 1.16, 3.34, 2.99, .37, '路由热度（示意）', 15, BLUE_DARK)
    for i, h in enumerate((1.39, 1.19, .95, .71, .49, .29)):
        x = 1.18 + i * .48
        rect(s, x, 5.36-h, .33, h,
             fill=BLUE_MID if i < 2 else GRAY_MID if i < 4 else GRAY_LIGHT,
             line=BLUE_DARK)
    t(s, 1.12, 5.58, 3.07, .39, '高频 → 快层；低频 → SSD', 14, BLUE_DARK)
    t(s, 5.18, 3.34, 3.02, .37, '驻留轨迹（示意）', 15, BLUE_DARK)
    for row, sequence in enumerate(('HHCCSS', 'HCHCSS', 'CHHCSS')):
        for i, tier in enumerate(sequence):
            color = BLUE_MID if tier == 'H' else GRAY_MID if tier == 'C' else GRAY_LIGHT
            rect(s, 5.25 + i * .45, 3.72 + row * .53, .38, .40,
                 fill=color, line=WHITE)
    t(s, 5.17, 5.58, 3.11, .39, '显存 / CPU 随访问联合更新', 14, BLUE_DARK)
    t(s, 9.29, 3.34, 2.74, .43, '相对综合性能', 15, BLUE_DARK)
    for i, (lab, val, color) in enumerate((('对照', 1.0, GRAY_MID), ('MECC', 1.333, BLUE_MID))):
        y = 4.09 + i * .79
        t(s, 9.06, y, .72, .39, lab, 13, BLUE_DARK)
        rect(s, 9.85, y, 1.53 * val / 1.333, .37, fill=color, line=BLUE_DARK)
        t(s, 11.45, y - .03, .68, .40, f'{val:.2f}×', 15, BLUE_DARK)
    t(s, 9.12, 5.58, 3.11, .39, 'A100 · Mixtral-8x7B', 14, BLUE_DARK)
    t(s, 1.31, 6.49, 10.72, .41,
      '核心贡献：用静态先验减少初始冷读，用在线反馈保留真实热点。', 17, BLUE_DARK)


def slide4(s):
    heading(s, 'Motivation I: Per-Task Budget', '服务器的物理内存要服务多个任务，并为系统与数据处理留空间；模型部署时真正可用的是单任务预算。\n在 Mixtral 主实验中，我们按显存 50 GB、CPU 内存 40 GB 规划专家驻留，剩余访问由 SSD 承担。')
    box(s, 1.0, 2.38, 4.55, 3.24, '', WHITE, BLUE_DARK)
    t(s, 1.25, 2.55, 4.0, .4, '服务器总内存', 18, BLUE_DARK)
    for i in range(5):
        box(s, 1.42 + i * .7, 3.38, .56, 1.27, '', BLUE_LIGHT if i == 0 else GRAY_LIGHT, BLUE_DARK)
    t(s, 1.24, 4.82, 4.12, .52, '本任务预算       其他任务 / 系统预留', 14)
    arrow(s, 5.78, 3.89, .7, .24, color=BLUE)
    box(s, 6.75, 2.42, 5.28, 3.2, '', WHITE, BLUE_DARK)
    t(s, 7.0, 2.64, 4.78, .42, 'Mixtral 主实验配置', 18, BLUE_DARK)
    box(s, 7.18, 3.31, 1.32, .8, '显存\n50 GB', BLUE_LIGHT, BLUE_DARK, 16)
    box(s, 8.78, 3.31, 1.32, .8, 'CPU\n40 GB', GRAY_LIGHT, BLUE_DARK, 16)
    box(s, 10.38, 3.31, 1.32, .8, 'SSD\n冷层', WHITE, BLUE_DARK, 16)
    t(s, 7.2, 4.56, 4.55, .55, '真实运行触发 SSD 访问', 17, BLUE_DARK)
    box(s, 1.79, 6.10, 9.73, .52, '部署决策看单任务预算：显存与 CPU 内存越紧，专家放置就越重要', BLUE_LIGHT, BLUE_DARK, 16)
    note(s, '预算来自原始 Mixtral 实验配置；不把 1 TB 物理内存等同于单任务可用内存。')


def slide5(s):
    heading(s, 'Motivation II: Workload Drift', '不同请求会反复激活不同专家：早期高频的专家，不一定在后续请求中仍然高频。\n如果缓存位置始终固定，新热点就会不断从较慢层级读取；系统需要随着真实路由改变驻留内容。')
    for k, y in enumerate((2.50, 4.18)):
        t(s, .94, y, 1.3, .45, '阶段 A' if k == 0 else '阶段 B', 16, BLUE_DARK)
        for i in range(8):
            hot = (i < 3) if k == 0 else (3 <= i < 6)
            circle(s, 2.62 + i * 1.15, y, .56, f'E{i+1}', fill=BLUE_MID if hot else GRAY_LIGHT, size=13)
        t(s, 2.5, y + .74, 9.8, .3, '蓝色代表当前高频访问专家', 13, GRAY, False)
    arrow(s, 6.38, 3.43, .22, .5, direction='down', color=BLUE)
    box(s, 1.48, 5.57, 4.65, .57, '固定缓存：仍保留阶段 A 的专家', GRAY_LIGHT, BLUE_DARK, 15)
    arrow(s, 6.25, 5.77, .56, .17, color=BLUE)
    box(s, 6.99, 5.57, 4.82, .57, '动态缓存：逐步转向阶段 B 的专家', BLUE_LIGHT, BLUE_DARK, 15)
    note(s, '示意图：说明工作负载漂移的机制，不代表该分布已在 Mixtral 真机测得。')


def slide6(s):
    heading(s, 'Insight I: Prior-Guided Placement', '运行之前可以用路由画像估计每个专家被访问的频率。把更可能被激活的专家优先放在显存，\n其次放在 CPU 内存，较少访问的专家保留在 SSD，可从第一批请求开始减少高代价读取。')
    for i, v in enumerate([.88, .74, .62, .45, .31, .22, .14, .08]):
        x = 1.22 + i * 1.32
        rect(s, x, 4.82 - v * 2.3, .72, v * 2.3, fill=BLUE_MID if i < 3 else GRAY_MID if i < 6 else GRAY_LIGHT, line=BLUE_DARK)
        t(s, x-.08, 5.04, .9, .35, f'E{i+1}', 13)
    box(s, 1.06, 5.55, 3.85, .56, '显存：最高访问概率', BLUE_LIGHT, BLUE_DARK, 15)
    box(s, 4.92, 5.55, 3.85, .56, 'CPU：次高访问概率', GRAY_LIGHT, BLUE_DARK, 15)
    box(s, 8.78, 5.55, 3.52, .56, 'SSD：其余专家', WHITE, BLUE_DARK, 15)
    t(s, 1.05, 2.16, 11.2, .4, '示例访问频率：按照被路由选中的可能性安排驻留顺序', 18, BLUE_DARK)
    note(s, '柱高为说明性访问概率；静态排序仅在等尺寸等假设下有最优性结论。')


def slide7(s):
    heading(s, 'Insight II: Online Adaptation', '初始画像提供一个良好起点，但每次真实路由都带来新信息。显存命中直接执行；CPU 命中时提升专家；\n只有两级都未命中才从 SSD 读取，再通过联合淘汰把近期活跃专家留在更快的位置。')
    box(s, .98, 2.35, 3.0, .67, '访问专家 E', BLUE_LIGHT, BLUE_DARK, 18)
    arrow(s, 4.15, 2.57, .56, .2, color=BLUE)
    box(s, 4.94, 2.28, 3.14, .8, '显存命中？', BLUE_LIGHT, BLUE_DARK, 18)
    arrow(s, 8.30, 2.58, .48, .2, color=BLUE)
    box(s, 9.0, 2.28, 3.15, .8, '直接执行', BLUE_LIGHT, BLUE_DARK, 18)
    arrow(s, 6.37, 3.19, .2, .46, direction='down', color=BLUE)
    box(s, 4.94, 3.87, 3.14, .76, 'CPU 命中？', GRAY_LIGHT, BLUE_DARK, 18)
    arrow(s, 8.30, 4.13, .48, .2, color=BLUE)
    box(s, 9.0, 3.87, 3.15, .76, '提升到显存', GRAY_LIGHT, BLUE_DARK, 18)
    arrow(s, 6.37, 4.77, .2, .45, direction='down', color=BLUE)
    box(s, 4.94, 5.43, 3.14, .68, 'SSD 冷读', WHITE, BLUE_DARK, 18)
    arrow(s, 8.30, 5.64, .48, .2, color=BLUE)
    box(s, 9.0, 5.43, 3.15, .68, '插入并联合淘汰', WHITE, BLUE_DARK, 17)
    note(s, '运行期联合 LRU 是在线启发式，不宣称对任意访问序列全局最优。')


def slide8(s):
    heading(s, 'System Overview',
            'MECC 将部署前的访问画像与运行中的实际路由放在同一三级驻留视图中。'
            '左侧是编译器根据预算生成的初始 expert→tier 分配；右侧是请求到来后'
            '显存与 CPU 命中不断变化的取数轨迹，SSD 始终保存完整权重。',
            explanation_size=18, explanation_height=1.14)
    evidence_panel(s, .79, '编译期：每层专家的初始驻留')
    evidence_panel(s, 6.79, '运行期：逐次访问的实际命中')
    plan = [
        ('L1', 'HHHCCCSS'), ('L2', 'HHCCCCSS'),
        ('L3', 'HHHCCCSS'), ('L4', 'HHCCCCSS'),
    ]
    colors = {'H': BLUE_MID, 'C': GRAY_MID, 'S': GRAY_LIGHT}
    for i in range(8):
        t(s, 1.53 + i * .53, 3.27, .46, .30, f'E{i+1}', 11, GRAY, False)
    for row, (layer, states) in enumerate(plan):
        y = 3.75 + row * .53
        t(s, .92, y, .52, .41, layer, 13, BLUE_DARK)
        for i, tier in enumerate(states):
            rect(s, 1.53 + i * .53, y, .46, .43,
                 fill=colors[tier], line=WHITE)
    for j, (lab, color) in enumerate((('显存', BLUE_MID), ('CPU', GRAY_MID), ('SSD', GRAY_LIGHT))):
        x = 1.25 + j * 1.64
        rect(s, x, 6.03, .24, .24, fill=color, line=BLUE_DARK)
        t(s, x + .32, 5.96, 1.06, .37, lab, 13, BLACK, False, PP_ALIGN.LEFT)
    hits = ['H', 'H', 'C', 'H', 'S', 'C', 'H', 'C']
    for i, tier in enumerate(hits):
        x = 7.17 + i * .61
        t(s, x, 3.30, .50, .31, str(i+1), 12, GRAY, False)
        h = 1.52 if tier == 'H' else 1.04 if tier == 'C' else .56
        rect(s, x, 5.29 - h, .50, h,
             fill=colors[tier], line=BLUE_DARK)
        t(s, x, 5.47, .50, .31, tier, 13, BLUE_DARK)
    t(s, 7.17, 5.91, 5.00, .35, 'H：显存  C：CPU  S：SSD（示意轨迹）', 13, GRAY, False)
    t(s, 1.21, 6.51, 10.95, .37, '同一 expert 在运行期可改变驻留层级；路由选择与权重数值保持不变。', 16, BLUE_DARK)


def slide9(s):
    heading(s, 'Method I: Static Placement',
            '编译器读取各层专家的访问画像、权重大小与单任务显存/CPU 预算。'
            '在给定独立容量上限下，按访问概率排序并确定两道容量边界，'
            '输出每层专家的初始三级驻留位置与预期冷读比例。',
            explanation_size=18, explanation_height=1.14)
    evidence_panel(s, .79, '访问画像：专家访问频率（示意）')
    evidence_panel(s, 6.79, '编译产物：预算约束下的三级分配')
    values = (1.64, 1.42, 1.22, .99, .77, .56, .37, .22)
    for i, h in enumerate(values):
        x = 1.09 + i * .66
        rect(s, x, 5.56-h, .40, h,
             fill=BLUE_MID if i < 3 else GRAY_MID if i < 6 else GRAY_LIGHT,
             line=BLUE_DARK)
        t(s, x-.05, 5.66, .49, .31, str(i+1), 11, BLACK)
    t(s, .98, 6.06, 5.52, .31, '专家按访问概率降序排列', 13, GRAY, False)
    for x, lab in ((8.30, 'K_H'), (10.23, 'K_H+K_C')):
        rect(s, x, 3.48, .018, 2.28, fill=BLUE_DARK, line=BLUE_DARK)
        t(s, x-.37, 3.17, .75, .32, lab, 13, BLUE_DARK)
    for i in range(8):
        x = 7.11 + i * .64
        tier = '显存' if i < 2 else 'CPU' if i < 5 else 'SSD'
        color = BLUE_MID if i < 2 else GRAY_MID if i < 5 else GRAY_LIGHT
        rect(s, x, 4.06, .48, .67, fill=color, line=BLUE_DARK)
        t(s, x-.03, 4.81, .54, .29, f'E{i+1}', 11, BLACK)
    t(s, 7.09, 5.45, 5.14, .40, '显存 2 槽  ·  CPU 3 槽  ·  其余在 SSD', 15, BLUE_DARK)
    t(s, .99, 6.51, 11.23, .38,
      '优化目标：E[T] = p_H T_H + p_C T_C + p_S T_S（各层命中概率 × 取数代价）。', 16, BLUE_DARK)


def slide10(s):
    heading(s, 'Method II: Joint Dynamic Cache',
            '运行期以真实路由为观测，按显存、CPU、SSD 的次序查找被选专家。'
            '显存与 CPU 命中直接复用已有权重；迁入显存时，被替换专家可在 CPU 层继续保留，'
            '使新的访问热点逐步改变快层驻留。',
            explanation_size=18, explanation_height=1.14)
    t(s, 1.02, 2.50, 11.29, .39, '访问序列与三级驻留状态（机制示意）', 18, BLUE_DARK)
    events = ('E1', 'E2', 'E3', 'E1', 'E4', 'E3', 'E2')
    for col, event in enumerate(events):
        x = 2.20 + col * 1.40
        t(s, x, 3.14, 1.07, .33, f't{col+1}', 12, GRAY, False)
        t(s, x, 3.49, 1.07, .37, event, 15, BLUE_DARK)
    states = {
        'E1': ('H', 'H', 'C', 'H', 'C', 'C', 'S'),
        'E2': ('S', 'H', 'H', 'C', 'C', 'S', 'H'),
        'E3': ('S', 'S', 'H', 'H', 'C', 'H', 'C'),
        'E4': ('S', 'S', 'S', 'S', 'H', 'C', 'C'),
    }
    palette = {'H': BLUE_MID, 'C': GRAY_MID, 'S': GRAY_LIGHT}
    for row, (expert, seq) in enumerate(states.items()):
        y = 4.06 + row * .48
        t(s, 1.12, y, .65, .35, expert, 13, BLUE_DARK)
        for col, tier in enumerate(seq):
            x = 2.20 + col * 1.40
            rect(s, x, y, 1.06, .38, fill=palette[tier], line=WHITE)
    for j, (lab, color) in enumerate((('显存 H', BLUE_MID), ('CPU C', GRAY_MID), ('SSD S', GRAY_LIGHT))):
        x = 2.16 + j * 2.75
        rect(s, x, 6.17, .24, .22, fill=color, line=BLUE_DARK)
        t(s, x + .31, 6.09, 1.69, .36, lab, 13, BLACK, False, PP_ALIGN.LEFT)
    t(s, 1.12, 6.54, 11.02, .36, '同一专家可随访问在三级之间迁移；搬运不改变被选专家集合和权重精度。', 16, BLUE_DARK)


def slide11(s):
    heading(s, 'Results I: End-to-End Speedup',
            'A100 上的 Mixtral-8x7B 主实验中，两种策略均使用 50 GB 显存、40 GB CPU 内存预算。\n'
            'MECC 相对本项目实现的 SwapMoE-style 对照取得 1.33× 综合性能。',
            explanation_size=18, explanation_height=1.14)
    t(s, 1.09, 2.31, 10.91, .37, '相对综合性能（SwapMoE-style = 1.00；越高越好）', 18, BLUE_DARK)
    x0, x1, y0 = 3.23, 10.77, 5.58
    for value in (0, .5, 1.0, 1.5):
        x = x0 + (x1-x0)*value/1.5
        rect(s, x, 3.05, .012, 2.54, fill=GRAY_LIGHT, line=GRAY_LIGHT)
        t(s, x-.28, 5.68, .56, .31, f'{value:.1f}', 12, GRAY, False)
    for label, value, fill, y in (('SwapMoE-style', 1.0, GRAY_MID, 3.43),
                                  ('MECC', 1.333, BLUE_MID, 4.48)):
        t(s, 1.08, y+.04, 1.94, .46, label, 16, BLUE_DARK)
        rect(s, x0, y, (x1-x0)*value/1.5, .55, fill=fill, line=BLUE_DARK)
        t(s, x0+(x1-x0)*value/1.5+.12, y+.02, .97, .49,
          f'{value:.2f}×', 18, BLUE_DARK)
    t(s, 1.15, 6.23, 10.87, .39,
      '相同资源预算下，联合驻留策略获得 33% 的综合性能提升。', 17, BLUE_DARK)
    t(s, 1.13, 6.70, 10.84, .28,
      'D2 真机 · 数据：results/raw/mixtral_real.json', 11, GRAY, False, PP_ALIGN.LEFT)
    note(s, '来源：results/raw/mixtral_real.json；对照是本项目实现的 SwapMoE-style 策略，不等同原论文系统。')


def slide12(s):
    heading(s, 'Results II: Cache Behavior',
            'A100 的 Mixtral 主实验中，CPU 命中率由 23.3% 升至 38.0%，SSD 访问比例由 34.5% 降至 17.6%。\n'
            '两项缓存行为变化与端到端性能提升一致；MECC 使用原始 fp16 权重，测得 PPL 24.57。',
            explanation_size=18, explanation_height=1.14)
    t(s, 1.03, 2.30, 10.84, .39, '专家访问的命中层级（每种策略合计 100%）', 18, BLUE_DARK)
    x0, width = 2.39, 8.98
    for value in (0, 25, 50, 75, 100):
        x = x0 + width * value/100
        rect(s, x, 3.00, .012, 2.45, fill=GRAY_LIGHT, line=GRAY_LIGHT)
        t(s, x-.32, 5.49, .64, .30, f'{value}%', 12, GRAY, False)
    rows = (('对照', 23.3, 34.5, 3.45), ('MECC', 38.0, 17.6, 4.52))
    for name, cpu, ssd, y in rows:
        gpu = 100-cpu-ssd
        t(s, 1.05, y+.05, 1.19, .46, name, 17, BLUE_DARK)
        start = x0
        for fraction, fill, label, color in ((gpu, BLUE_LIGHT, '显存', BLUE_DARK),
                                             (cpu, BLUE_MID, f'CPU {cpu:.1f}%', WHITE),
                                             (ssd, GRAY_MID, f'SSD {ssd:.1f}%', BLACK)):
            w = width*fraction/100
            rect(s, start, y, w, .61, fill=fill, line=WHITE)
            t(s, start+.03, y+.05, w-.06, .48, label, 14, color)
            start += w
    for x, lab, fill in ((3.25, '显存', BLUE_LIGHT), (5.54, 'CPU', BLUE_MID),
                         (7.48, 'SSD', GRAY_MID)):
        rect(s, x, 6.13, .24, .24, fill=fill, line=BLUE_DARK)
        t(s, x+.29, 6.06, 1.09, .36, lab, 14, BLACK, False, PP_ALIGN.LEFT)
    t(s, 9.42, 6.05, 2.73, .38, 'fp16 PPL 24.57', 16, BLUE_DARK)
    t(s, 1.12, 6.69, 10.84, .29,
      'D2 真机 · 数据：results/raw/mixtral_real.json', 11, GRAY, False, PP_ALIGN.LEFT)
    note(s, 'A100 真机 D2；PPL 仅报告 MECC 本身，不对未核实的对照 PPL 做质量结论。')


def evidence_panel(s, x, title):
    t(s, x + .06, 2.43, 5.71, .43, title, 17, BLUE_DARK)
    rect(s, x, 2.95, 5.83, .018, fill=GRAY_MID, line=GRAY_MID)


def motivation_1(s):
    heading(s, 'Motivation I: Slow-Tier Cost',
            '5090 单专家实测：SSD 冷读约 790 ms，显存命中仅 0.256 ms，相差三个数量级。\n'
            '单任务快层预算若覆盖不了全部专家，一次 SSD 未命中就可能拉长 token 生成时间。',
            explanation_size=18, explanation_height=1.14)
    evidence_panel(s, .78, '结果：SSD 冷读代价远高于快层命中')
    evidence_panel(s, 6.78, '原因：慢层读取暴露在关键路径（示意）')
    for j, tick in enumerate((.1, 1, 10, 100, 1000)):
        y = 5.74 - j * .58
        rect(s, 1.40, y, 4.88, .009, fill=GRAY_LIGHT, line=GRAY_LIGHT)
        t(s, .83, y - .15, .55, .31, str(tick), 11, GRAY, False)
    levels = [('显存', .256, BLUE_MID), ('CPU', 6.504, GRAY_MID),
              ('SSD', 789.739, BLUE_DARK)]
    for i, (lab, ms, fill) in enumerate(levels):
        x = 2.00 + i * 1.48
        h = (log10(ms) + 1) / 4 * 2.32
        rect(s, x, 5.74 - h, .67, h, fill=fill, line=BLUE_DARK)
        t(s, x - .12, 5.83, .91, .35, lab, 14)
        t(s, x - .27, 5.34 - h, 1.18, .35,
          '≈790 ms' if i == 2 else f'{ms:g} ms', 14, BLUE_DARK)
    t(s, 1.03, 6.10, 5.14, .30, '5090 真机 · 每次访问延迟 / ms', 12, GRAY, False)
    for y, lab in ((3.38, '显存命中'), (4.38, 'CPU 命中'), (5.38, 'SSD 冷读')):
        t(s, 6.87, y, 1.27, .40, lab, 14, BLACK)
    # Timeline lengths are schematic; the quantitative delays are in the left plot.
    rect(s, 8.29, 3.45, .44, .26, fill=BLUE_MID, line=BLUE_MID)
    rect(s, 8.29, 4.45, 1.47, .26, fill=GRAY_MID, line=GRAY_MID)
    rect(s, 9.76, 4.45, .44, .26, fill=BLUE_MID, line=BLUE_MID)
    rect(s, 8.29, 5.45, 2.81, .26, fill=BLUE_DARK, line=BLUE_DARK)
    rect(s, 11.10, 5.45, 1.02, .26, fill=GRAY_MID, line=GRAY_MID)
    t(s, 8.27, 3.05, 1.31, .32, '路由完成', 13, GRAY, False)
    t(s, 10.83, 5.87, 1.62, .32, '权重就绪', 13, GRAY, False)
    for x, color, lab in ((7.10, BLUE_DARK, 'SSD 读取'), (9.05, GRAY_MID, '传输'), (10.61, BLUE_MID, '计算')):
        rect(s, x, 6.09, .20, .20, fill=color, line=color)
        t(s, x + .23, 6.02, 1.22, .32, lab, 12, BLACK, False, PP_ALIGN.LEFT)
    t(s, .92, 6.49, 11.42, .39, '研究问题 ①  单任务预算有限时，如何优先保护代价最高的 SSD 访问？', 17, BLUE_DARK)


def motivation_2(s):
    heading(s, 'Motivation II: Missed Reuse',
            'Mixtral A100 实测中，固定 CPU 驻留对照仍有 34.5% 的专家访问落到 SSD；联合保留后降至 17.6%。\n'
            '同时 CPU 命中由 23.3% 升至 38.0%：问题并非只有显存容量不足，显存淘汰后的专家还需要在 CPU 层复用。',
            explanation_size=18, explanation_height=1.14)
    evidence_panel(s, .78, '结果：固定 CPU 驻留产生更多 SSD 访问')
    evidence_panel(s, 6.78, '原因：显存淘汰后未在 CPU 保留（示意）')
    # Two category panels share one 0–40% scale; direct labels avoid legend lookup.
    left, span = 2.18, 3.77
    for value in (0, 10, 20, 30, 40):
        x = left + span*value/40
        rect(s, x, 3.25, .010, 2.53, fill=GRAY_LIGHT, line=GRAY_LIGHT)
        t(s, x-.31, 5.80, .62, .28, str(value), 11, GRAY, False)
    t(s, .99, 3.18, 1.11, .32, 'CPU 命中', 14, BLUE_DARK)
    t(s, .99, 4.44, 1.11, .32, 'SSD 访问', 14, BLUE_DARK)
    for value, y, fill, name in ((23.3, 3.57, GRAY_MID, '对照'),
                                 (38.0, 3.97, BLUE_MID, 'MECC'),
                                 (34.5, 4.83, GRAY_MID, '对照'),
                                 (17.6, 5.23, BLUE_MID, 'MECC')):
        rect(s, left, y, span*value/40, .27, fill=fill, line=fill)
        t(s, left+span*value/40+.09, y-.04, .73, .34, f'{value:.1f}%', 12, BLUE_DARK)
    rect(s, 2.24, 6.17, .22, .21, fill=GRAY_MID, line=GRAY_MID)
    t(s, 2.53, 6.09, 1.05, .32, '对照', 12, BLACK, False, PP_ALIGN.LEFT)
    rect(s, 3.80, 6.17, .22, .21, fill=BLUE_MID, line=BLUE_MID)
    t(s, 4.08, 6.09, 1.11, .32, 'MECC', 12, BLACK, False, PP_ALIGN.LEFT)
    t(s, 7.05, 3.12, 5.17, .30, '同一专家 E1：首次访问 → 淘汰 → 再访', 14, GRAY, False)
    for j, lab in enumerate(('首次访问', '显存淘汰', '再次访问')):
        t(s, 8.27 + j * 1.30, 3.61, 1.14, .36, lab, 13, BLUE_DARK)
    for row, (name, values) in enumerate((
        ('固定 CPU', [('显存', BLUE_LIGHT), ('未保留', GRAY_LIGHT), ('SSD', WHITE)]),
        ('联合缓存', [('显存', BLUE_LIGHT), ('CPU 保留', GRAY_MID), ('CPU', GRAY_MID)]),
    )):
        y = 4.13 + row * .82
        t(s, 6.92, y, 1.26, .49, name, 14, BLUE_DARK)
        for j, (lab, fill) in enumerate(values):
            rect(s, 8.27 + j * 1.30, y, 1.15, .50, fill=fill, line=BLUE_DARK)
            t(s, 8.27 + j * 1.30, y, 1.15, .50, lab, 14, BLACK)
    t(s, 7.08, 5.94, 5.17, .31, '第三次访问：CPU 命中替代 SSD 冷读', 14, BLUE_DARK)
    t(s, .92, 6.49, 11.42, .39, '研究问题 ②  如何让显存与 CPU 共同保留真实工作集？', 17, BLUE_DARK)


def motivation_3(s):
    heading(s, 'Motivation III: Shifting Hotspots',
            '缓存模拟实验显示：热点漂移使静态驻留对照的 SSD 访问比例由 7.5% 升至 11.3%。\n'
            '这提示历史画像会与当前请求失配：新阶段的高频专家可能仍留在 SSD。',
            explanation_size=18, explanation_height=1.14)
    evidence_panel(s, .78, '结果：漂移使静态驻留的 SSD 访问增加')
    evidence_panel(s, 6.78, '原因：初始驻留与新热点错位（示意）')
    x0, span = 2.25, 3.59
    for value in (0, 4, 8, 12):
        x = x0 + span*value/12
        rect(s, x, 3.29, .010, 2.48, fill=GRAY_LIGHT, line=GRAY_LIGHT)
        t(s, x-.29, 5.79, .58, .30, f'{value}%', 12, GRAY, False)
    for i, (lab, val) in enumerate((('热点静止', 7.5), ('热点漂移', 11.3))):
        y = 3.73 + i * 1.13
        t(s, .94, y, 1.22, .46, lab, 15, BLUE_DARK)
        rect(s, x0, y+.06, span*val/12, .35,
             fill=GRAY_MID if i == 0 else BLUE_MID, line=BLUE_DARK)
        t(s, x0+span*val/12+.08, y-.02, .71, .48, f'{val:.1f}%', 15, BLUE_DARK)
    t(s, 1.13, 6.13, 5.29, .31, 'DeepSeek 合成规模 · D1 缓存模拟器', 12, GRAY, False)
    for i in range(8):
        t(s, 8.03 + i * .53, 3.37, .48, .31, f'E{i+1}', 11, GRAY, False)
    for k, y in enumerate((3.98, 4.77, 5.56)):
        t(s, 6.88, y, 1.06, .41, ('初始驻留', '阶段 A', '阶段 B')[k], 14, BLUE_DARK)
        for i in range(8):
            hot = i in ((0, 1, 2) if k in (0, 1) else (3, 4, 5))
            rect(s, 8.03 + i * .53, y, .46, .47,
                 fill=BLUE_MID if hot else GRAY_LIGHT, line=WHITE)
    t(s, 8.10, 6.17, 4.07, .30, '阶段 B：快层位置仍覆盖旧热点', 13, BLUE_DARK, False)
    t(s, .92, 6.49, 11.42, .39, '研究问题 ③  初始画像失配后，缓存如何持续跟随新热点？', 17, BLUE_DARK)


def insight_1(s):
    heading(s, 'Insight I: Cost-Aware Placement',
            '洞察 ①：不同层级的取数代价高度不对称，应按访问概率与单任务预算共同决定初始驻留。\n'
            '把高频专家放入显存、次高频专家放入 CPU，剩余留在 SSD；'
            '目标是降低预期取数代价，而不是平均分配空间。',
            explanation_size=18, explanation_height=1.14)
    for i, h in enumerate((1.60, 1.43, 1.22, .98, .78, .60, .44, .30)):
        x = 1.16 + i * 1.31
        rect(s, x, 4.97 - h, .72, h,
             fill=BLUE_MID if i < 3 else GRAY_MID if i < 6 else GRAY_LIGHT,
             line=BLUE_DARK)
        t(s, x - .02, 5.06, .76, .34, f'E{i+1}', 13)
    t(s, 1.11, 2.50, 10.8, .43, '按访问热度排序的专家与三级容量边界', 19, BLUE_DARK)
    t(s, 1.17, 3.00, 2.18, .32, '排序示意', 13, GRAY, False, PP_ALIGN.LEFT)
    for x, lab in ((4.78, 'K_H'), (8.69, 'K_H+K_C')):
        rect(s, x, 3.28, .016, 2.20, fill=BLUE_DARK, line=BLUE_DARK)
        t(s, x - .51, 3.07, 1.05, .31, lab, 13, BLUE_DARK)
    for x, w, lab, fill in ((1.04, 3.72, '显存：高频', BLUE_MID),
                            (4.84, 3.83, 'CPU：次高频', GRAY_MID),
                            (8.75, 3.57, 'SSD：其余', GRAY_LIGHT)):
        rect(s, x, 5.67, w, .10, fill=fill, line=fill)
        t(s, x, 5.82, w, .35, lab, 15, BLUE_DARK)
    t(s, 1.15, 6.51, 11.0, .35, '对应动机 ①：优先避免高概率请求承担昂贵的 SSD 冷读。', 16, BLUE_DARK)


def insight_2(s):
    heading(s, 'Insight II: Joint Retention',
            '洞察 ②：显存与 CPU 不应是相互独立的缓存。显存淘汰的专家可在 CPU 层继续保留，\n'
            'CPU 命中再提升到显存；只在两层均未命中时访问 SSD。'
            '因此 CPU 容量被用于保存正在形成的工作集，而非固定不变的专家集合。',
            explanation_size=18, explanation_height=1.14)
    t(s, 1.22, 2.73, 10.8, .42, '一次 E3 访问前后：各专家所在的最快层级', 18, BLUE_DARK)
    for i in range(6):
        t(s, 2.62 + i * 1.56, 3.27, 1.18, .37, f'E{i+1}', 15, BLUE_DARK)
    states = [
        ('访问前', ('显存', '显存', 'CPU', 'CPU', 'SSD', 'SSD')),
        ('访问后', ('显存', 'CPU', '显存', 'CPU', 'SSD', 'SSD')),
    ]
    palette = {'显存': BLUE_MID, 'CPU': GRAY_MID, 'SSD': WHITE}
    for row, (row_label, values) in enumerate(states):
        y = 3.83 + row * .91
        t(s, 1.13, y + .06, 1.22, .41, row_label, 16, BLUE_DARK)
        for i, tier in enumerate(values):
            x = 2.62 + i * 1.56
            rect(s, x, y, 1.18, .55, fill=palette[tier], line=BLUE_DARK)
            t(s, x, y, 1.18, .55, tier, 14,
              WHITE if tier == '显存' else BLACK)
    t(s, 2.66, 5.81, 8.96, .38,
      'E3 从 CPU 提升至显存；被替换的 E2 留在 CPU', 17, BLUE_DARK)
    t(s, 1.15, 6.51, 11.0, .35, '对应动机 ②：让专家复用跨越显存淘汰事件。', 16, BLUE_DARK)


def insight_3(s):
    heading(s, 'Insight III: Prior + Feedback',
            '洞察 ③：历史画像适合决定“从哪里开始”，真实路由适合决定“接下来保留谁”。\n'
            '编译期先给出预算约束下的初始计划，运行期用访问历史更新三级驻留；'
            '两种时间尺度协同，既利用已知热点，又能响应请求变化。',
            explanation_size=18, explanation_height=1.14)
    rect(s, .95, 2.69, 7.24, 3.40, fill=WHITE, line=BLUE_DARK)
    t(s, 1.15, 2.85, 6.82, .43, '访问热度：先验与真实观测', 18, BLUE_DARK)
    for k, y in enumerate((3.54, 4.94)):
        t(s, 1.14, y, 1.48, .43, '历史画像' if k == 0 else '真实路由', 16, BLUE_DARK)
        for i in range(6):
            hot = i < 2 if k == 0 else 2 <= i < 4
            circle(s, 2.99 + i * .76, y - .02, .46, f'E{i+1}',
                   fill=BLUE_MID if hot else GRAY_LIGHT,
                   line=BLUE_DARK, size=11,
                   color=WHITE if hot else BLACK)
    arrow(s, 5.05, 4.17, .18, .40, direction='down', color=BLUE)
    t(s, 8.61, 2.86, 3.62, .42, '驻留与热点的匹配', 18, BLUE_DARK)
    for j, lab in enumerate(('阶段 A', '阶段 B')):
        t(s, 9.30 + j * 1.39, 3.43, 1.18, .37, lab, 14, GRAY)
    for k, (row_label, values) in enumerate((
        ('固定放置', (True, False)),
        ('在线更新', (True, True)),
    )):
        y = 4.04 + k * .91
        t(s, 8.27, y + .06, 1.05, .40, row_label, 14, BLUE_DARK)
        for j, matched in enumerate(values):
            x = 9.40 + j * 1.39
            rect(s, x, y, 1.10, .53,
                 fill=BLUE_LIGHT if matched else GRAY_LIGHT, line=BLUE_DARK)
            t(s, x, y, 1.10, .53, '匹配' if matched else '失配', 14,
              BLUE_DARK if matched else GRAY)
    t(s, 1.15, 6.51, 11.0, .35, '对应动机 ③：不把一次历史画像当作永久不变的工作集。', 16, BLUE_DARK)


BUILDERS=[slide1,slide2,slide3,motivation_1,motivation_2,motivation_3,
          insight_1,insight_2,insight_3,slide8,slide9,slide10,slide11,slide12]


def build(template: Path, output: Path):
    prs=Presentation(template)
    for _ in range(2):
        prs.slides.add_slide(prs.slide_layouts[5])
    retain_slides(prs,set(range(1,15)))
    for i,(builder,slide) in enumerate(zip(BUILDERS,prs.slides)):
        builder(slide)
        if i >= 12:
            t(slide, 12.23, 7.02, .48, .30, str(i + 1), 17, RED, False)
    output.parent.mkdir(parents=True,exist_ok=True)
    prs.save(output)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--template',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    build(a.template,a.out)


if __name__=='__main__': main()
