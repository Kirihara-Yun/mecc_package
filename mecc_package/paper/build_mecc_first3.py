"""Build the first three visual MECC slides using the approved 1013 style."""

from __future__ import annotations

import argparse
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, PP_PLACEHOLDER
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt


BLACK = RGBColor(0, 0, 0)
BLUE = RGBColor(0, 112, 192)
BLUE_DARK = RGBColor(47, 84, 150)
BLUE_MID = RGBColor(91, 155, 213)
BLUE_LIGHT = RGBColor(221, 232, 247)
GRAY = RGBColor(127, 127, 127)
GRAY_LIGHT = RGBColor(242, 242, 242)
GRAY_MID = RGBColor(217, 217, 217)
RED = RGBColor(230, 40, 40)
WHITE = RGBColor(255, 255, 255)


def retain_slides(prs: Presentation, keep: set[int]) -> None:
    ids = prs.slides._sldIdLst
    for position in reversed(range(len(ids))):
        if position in keep:
            continue
        slide_id = ids[position]
        prs.part.drop_rel(slide_id.rId)
        ids.remove(slide_id)


def remove_theme_effects(shape) -> None:
    style = shape._element.find(qn("p:style"))
    if style is not None:
        shape._element.remove(style)


def style_runs(paragraph, size, bold=True, color=BLACK,
               font="Microsoft YaHei") -> None:
    for run in paragraph.runs:
        run.font.name = font
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color


def clean_slide(slide, title_text: str) -> None:
    for shape in list(slide.shapes):
        keep = False
        if shape.is_placeholder:
            keep = shape.placeholder_format.type in (
                PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.SLIDE_NUMBER)
        if not keep:
            element = shape._element
            element.getparent().remove(element)
    title = next(
        shape for shape in slide.shapes
        if shape.is_placeholder
        and shape.placeholder_format.type == PP_PLACEHOLDER.TITLE
    )
    # Newly appended pages use the template's title-only layout; normalize its
    # title geometry to the approved content slides before adding body text.
    title.left = Inches(0)
    title.top = Inches(-0.14166557305336833)
    title.width = Inches(13.333333333333334)
    title.height = Inches(1.09375)
    title.text = title_text
    for paragraph in title.text_frame.paragraphs:
        paragraph.alignment = PP_ALIGN.CENTER
        style_runs(paragraph, 32, True)


def text_box(slide, x, y, w, h, text, *, size=15, bold=True, color=BLACK,
             align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    remove_theme_effects(shape)
    frame = shape.text_frame
    frame.clear()
    frame.margin_left = Inches(0.04)
    frame.margin_right = Inches(0.04)
    frame.margin_top = Inches(0.02)
    frame.margin_bottom = Inches(0.02)
    frame.vertical_anchor = valign
    paragraph = frame.paragraphs[0]
    paragraph.text = text
    paragraph.alignment = align
    style_runs(paragraph, size, bold, color)
    return shape


def rect(slide, x, y, w, h, text="", *, fill=GRAY_LIGHT, line=BLACK,
         size=15, bold=True, rounded=False, color=BLACK, dash=False):
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    remove_theme_effects(shape)
    if fill is None:
        shape.fill.background()
    else:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line
    shape.line.width = Pt(1.1)
    if dash:
        shape.line.dash_style = 4
    if text:
        frame = shape.text_frame
        frame.clear()
        frame.margin_left = Inches(0.05)
        frame.margin_right = Inches(0.05)
        frame.margin_top = Inches(0.02)
        frame.margin_bottom = Inches(0.02)
        frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        paragraph = frame.paragraphs[0]
        paragraph.text = text
        paragraph.alignment = PP_ALIGN.CENTER
        style_runs(paragraph, size, bold, color)
    return shape


def circle(slide, x, y, d, text="", *, fill=BLUE_LIGHT, line=BLACK,
           size=13, color=BLACK):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    remove_theme_effects(shape)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line
    shape.line.width = Pt(1)
    if text:
        frame = shape.text_frame
        frame.clear()
        frame.margin_left = frame.margin_right = 0
        frame.margin_top = frame.margin_bottom = 0
        frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        paragraph = frame.paragraphs[0]
        paragraph.text = text
        paragraph.alignment = PP_ALIGN.CENTER
        style_runs(paragraph, size, True, color)
    return shape


def arrow(slide, x, y, w=0.45, h=0.13, *, direction="right", color=BLACK):
    kinds = {
        "right": MSO_SHAPE.RIGHT_ARROW,
        "down": MSO_SHAPE.DOWN_ARROW,
        "up": MSO_SHAPE.UP_ARROW,
        "both": MSO_SHAPE.LEFT_RIGHT_ARROW,
    }
    shape = slide.shapes.add_shape(
        kinds[direction], Inches(x), Inches(y), Inches(w), Inches(h))
    remove_theme_effects(shape)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape


def caption(slide, text: str) -> None:
    square = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(1.03), Inches(1.20), Inches(0.18), Inches(0.18))
    remove_theme_effects(square)
    square.fill.background()
    square.line.color.rgb = BLUE
    square.line.width = Pt(2.5)
    shape = text_box(slide, 1.34, 0.99, 10.85, 0.68, text, size=17,
                     bold=True, align=PP_ALIGN.LEFT)
    shape.text_frame.word_wrap = True


def panel_title(slide, x, y, w, text, color=BLACK):
    text_box(slide, x, y, w, 0.35, text, size=16, bold=True, color=color)


def build_introduction(slide) -> None:
    clean_slide(slide, "Introduction")
    caption(slide, "MoE 通过路由激活少量 Expert，将模型容量与单次计算解耦。")

    rect(slide, 0.88, 1.88, 3.48, 3.92, fill=None, dash=True)
    panel_title(slide, 1.55, 2.02, 2.14, "Dense Model")
    circle(slide, 1.27, 3.30, 0.56, "x", fill=WHITE, size=15)
    arrow(slide, 1.93, 3.51, 0.48, 0.12)
    for idx in range(4):
        rect(slide, 2.55 + idx * 0.36, 2.75, 0.27, 1.72, "",
             fill=GRAY_MID if idx < 3 else GRAY_LIGHT, line=WHITE)
    text_box(slide, 1.28, 4.92, 2.72, 0.38, "全部参数参与计算", size=15)
    text_box(slide, 1.48, 5.35, 2.34, 0.28, "Dense activation", size=12,
             color=GRAY)

    arrow(slide, 4.62, 3.58, 0.62, 0.18, color=BLUE)

    rect(slide, 5.50, 1.88, 6.92, 3.92, fill=None, dash=True)
    panel_title(slide, 7.64, 2.02, 2.64, "Mixture-of-Experts", BLUE_DARK)
    circle(slide, 5.92, 3.30, 0.56, "x", fill=WHITE, size=15)
    arrow(slide, 6.57, 3.51, 0.42, 0.12)
    router = slide.shapes.add_shape(
        MSO_SHAPE.DIAMOND, Inches(7.08), Inches(3.16), Inches(0.86), Inches(0.86))
    remove_theme_effects(router)
    router.fill.solid(); router.fill.fore_color.rgb = GRAY_LIGHT
    router.line.color.rgb = BLACK; router.line.width = Pt(1.1)
    router.text = "G"
    for paragraph in router.text_frame.paragraphs:
        paragraph.alignment = PP_ALIGN.CENTER
        style_runs(paragraph, 12, True)
    arrow(slide, 8.02, 3.51, 0.42, 0.12)

    expert_positions = []
    for row in range(2):
        for col in range(4):
            expert_positions.append((8.56 + col * 0.61, 2.72 + row * 0.94))
    active = {1, 6}
    for idx, (x, y) in enumerate(expert_positions):
        fill = BLUE_MID if idx in active else GRAY_LIGHT
        line = BLUE_DARK if idx in active else GRAY
        color = WHITE if idx in active else BLACK
        rect(slide, x, y, 0.48, 0.68, f"E{idx+1}", fill=fill, line=line,
             size=10, rounded=True, color=color)
    text_box(slide, 9.06, 4.56, 1.80, 0.34, "Top-k = 2", size=14,
             color=BLUE_DARK)
    text_box(slide, 7.16, 5.02, 4.76, 0.38, "每个 token 仅激活少量 Expert", size=15)
    text_box(slide, 7.86, 5.35, 3.36, 0.28, "Sparse activation", size=12,
             color=BLUE_DARK)

    rect(slide, 3.18, 6.02, 7.00, 0.48,
         "更大参数容量   ·   更少激活计算",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=18, color=BLUE_DARK)


def build_motivation_capacity(slide) -> None:
    clean_slide(slide, "Motivation I")
    caption(slide, "共享服务器中，单个推理任务通常只能使用部分 HBM 与 CPU 内存。")

    rect(slide, 0.78, 1.90, 4.18, 4.02, fill=None, dash=True)
    panel_title(slide, 1.70, 2.04, 2.30, "共享服务器", BLUE_DARK)
    # Server silhouette and co-located workloads.
    rect(slide, 1.18, 2.62, 3.36, 2.56, fill=GRAY_LIGHT, line=GRAY,
         rounded=True)
    text_box(slide, 1.48, 2.75, 2.76, 0.30, "GPU + CPU + SSD", size=14,
             color=GRAY)
    rect(slide, 1.48, 3.22, 2.76, 0.50, "推理任务", fill=BLUE_MID,
         line=WHITE, size=15, color=WHITE, rounded=True)
    rect(slide, 1.48, 3.84, 1.22, 0.48, "任务 A", fill=GRAY_MID,
         line=WHITE, size=13, rounded=True)
    rect(slide, 2.76, 3.84, 1.48, 0.48, "任务 B", fill=GRAY_MID,
         line=WHITE, size=13, rounded=True)
    rect(slide, 1.48, 4.44, 2.76, 0.48, "系统服务", fill=WHITE,
         line=GRAY, size=13, rounded=True)
    text_box(slide, 1.35, 5.34, 3.02, 0.34, "物理容量由多任务共享", size=15)

    arrow(slide, 5.12, 3.72, 0.58, 0.18, color=BLUE)

    rect(slide, 5.84, 1.90, 6.74, 4.02, fill=None, dash=True)
    panel_title(slide, 7.78, 2.04, 2.90, "单任务可用配额", BLUE_DARK)
    text_box(slide, 6.28, 2.64, 5.86, 0.30, "Expert 权重", size=14)
    for idx in range(10):
        fill = BLUE_MID if idx < 6 else GRAY_MID
        color = WHITE if idx < 6 else BLACK
        rect(slide, 6.34 + idx * 0.55, 3.02, 0.44, 0.48, f"E{idx+1}",
             fill=fill, line=WHITE, size=9, color=color)
    text_box(slide, 6.28, 3.66, 5.86, 0.28, "任务内存预算", size=13,
             color=GRAY)
    rect(slide, 6.34, 4.02, 1.12, 0.72, "HBM", fill=BLUE_DARK,
         line=WHITE, size=14, color=WHITE)
    rect(slide, 7.46, 4.02, 2.30, 0.72, "CPU 配额", fill=BLUE_LIGHT,
         line=WHITE, size=14)
    rect(slide, 9.76, 4.02, 2.04, 0.72, "SSD", fill=GRAY_MID,
         line=WHITE, size=14)
    arrow(slide, 10.62, 3.54, 0.18, 0.38, direction="down", color=RED)
    text_box(slide, 9.72, 4.90, 2.16, 0.34, "超出快层预算", size=14,
             color=RED)
    text_box(slide, 6.34, 5.34, 5.46, 0.34, "大模型将权重延伸到 SSD", size=15)

    rect(slide, 3.12, 6.08, 7.16, 0.46,
         "模型规模  >  任务内存预算   →   三级存储",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=18, color=BLUE_DARK)


def draw_hotness_bars(slide, x0, y0, heights, hot_indices):
    for idx, height in enumerate(heights):
        fill = BLUE_MID if idx in hot_indices else GRAY_MID
        rect(slide, x0 + idx * 0.43, y0 + 1.18 - height, 0.28, height,
             fill=fill, line=WHITE)
        text_box(slide, x0 + idx * 0.43 - 0.02, y0 + 1.23, 0.32, 0.24,
                 f"E{idx+1}", size=8, bold=False)


def build_motivation_hotness(slide) -> None:
    clean_slide(slide, "Motivation II")
    caption(slide, "Expert 访问呈现显著热点，但热点会随请求分布持续迁移。")

    rect(slide, 0.78, 1.90, 5.36, 4.05, fill=None, dash=True)
    panel_title(slide, 2.22, 2.02, 2.50, "热点可学习", BLUE_DARK)
    draw_hotness_bars(slide, 1.22, 2.75,
                      [1.15, 0.91, 0.72, 0.55, 0.42, 0.34, 0.26, 0.19], {0, 1})
    arrow(slide, 4.75, 3.28, 0.52, 0.13)
    rect(slide, 5.36, 2.68, 0.48, 0.60, "H", fill=BLUE_DARK,
         line=WHITE, size=13, color=WHITE)
    rect(slide, 5.36, 3.34, 0.48, 0.82, "C", fill=BLUE_LIGHT,
         line=WHITE, size=13)
    rect(slide, 5.36, 4.22, 0.48, 0.92, "S", fill=GRAY_MID,
         line=WHITE, size=13)
    text_box(slide, 1.32, 4.65, 3.60, 0.42, "高概率 Expert 优先进入快层", size=15)
    rect(slide, 1.55, 5.25, 3.75, 0.43, "Profile-guided placement",
         fill=GRAY_LIGHT, size=14)

    circle(slide, 6.27, 3.62, 0.50, "+", fill=WHITE, line=BLUE,
           size=20, color=BLUE)

    rect(slide, 6.90, 1.90, 5.70, 4.05, fill=None, dash=True)
    panel_title(slide, 8.48, 2.02, 2.55, "热点会迁移", BLUE_DARK)
    text_box(slide, 7.25, 2.66, 0.52, 0.28, "t₀", size=13)
    text_box(slide, 7.25, 3.63, 0.52, 0.28, "t₁", size=13)
    for row, hot in enumerate(({0, 1}, {4, 5})):
        for idx in range(8):
            fill = BLUE_MID if idx in hot else GRAY_LIGHT
            color = WHITE if idx in hot else BLACK
            circle(slide, 7.90 + idx * 0.48, 2.52 + row * 0.98, 0.34,
                   f"{idx+1}", fill=fill,
                   line=BLUE_DARK if idx in hot else GRAY,
                   size=9, color=color)
    arrow(slide, 9.60, 3.13, 0.18, 0.32, direction="down", color=BLUE)
    text_box(slide, 7.76, 4.35, 4.05, 0.42, "热点迁移 → 在线升降级", size=15)
    rect(slide, 8.05, 5.25, 3.72, 0.43, "Online joint migration",
         fill=GRAY_LIGHT, size=14)

    rect(slide, 3.46, 6.10, 6.44, 0.43,
             "可学习  +  会变化  →  需要静态先验与在线自适应",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=17, color=BLUE_DARK)


def build_overview(slide) -> None:
    clean_slide(slide, "MECC Overview")
    caption(slide, "MECC 将编译期概率放置与运行期联合迁移连接成一个无损执行闭环。")

    rect(slide, 0.66, 1.90, 4.20, 4.15, fill=None, dash=True)
    panel_title(slide, 1.66, 2.02, 2.20, "编译期", BLUE_DARK)
    # Profile icon: a cluster of access dots.
    rect(slide, 1.02, 2.62, 1.00, 0.70, "Profile", fill=GRAY_LIGHT,
         size=14, rounded=True)
    for idx, (dx, dy) in enumerate(((0.15, 0.15), (0.40, 0.13), (0.65, 0.20),
                                    (0.28, 0.42), (0.58, 0.45))):
        circle(slide, 2.25 + dx, 2.58 + dy, 0.13, fill=BLUE_MID,
               line=BLUE_MID)
    arrow(slide, 3.24, 2.91, 0.42, 0.12)
    rect(slide, 3.75, 2.62, 0.75, 0.70, "α", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=21, rounded=True, color=BLUE_DARK)

    arrow(slide, 2.57, 3.55, 0.18, 0.38, direction="down", color=BLUE)
    rect(slide, 1.22, 4.02, 3.10, 0.62, "Optimize  K_H / K_C",
         fill=GRAY_LIGHT, size=16, rounded=True)
    arrow(slide, 2.57, 4.80, 0.18, 0.38, direction="down", color=BLUE)
    rect(slide, 1.22, 5.24, 0.88, 0.48, "HBM", fill=BLUE_DARK,
         line=WHITE, size=12, color=WHITE)
    rect(slide, 2.10, 5.24, 1.08, 0.48, "CPU", fill=BLUE_LIGHT,
         line=WHITE, size=12)
    rect(slide, 3.18, 5.24, 1.14, 0.48, "SSD", fill=GRAY_MID,
         line=WHITE, size=12)
    text_box(slide, 1.38, 5.73, 2.80, 0.27, "Placement plan", size=12,
             color=GRAY)

    arrow(slide, 4.98, 3.77, 0.60, 0.18, color=BLUE)

    rect(slide, 5.68, 1.90, 6.92, 4.15, fill=None, dash=True)
    panel_title(slide, 7.90, 2.02, 2.35, "运行期", BLUE_DARK)
    # Router and dispatch.
    circle(slide, 6.06, 3.28, 0.60, "x", fill=WHITE, size=15)
    arrow(slide, 6.74, 3.51, 0.42, 0.12)
    router = slide.shapes.add_shape(
        MSO_SHAPE.DIAMOND, Inches(7.24), Inches(3.18), Inches(0.82), Inches(0.82))
    remove_theme_effects(router)
    router.fill.solid(); router.fill.fore_color.rgb = GRAY_LIGHT
    router.line.color.rgb = BLACK
    router.text = "Gate"
    for paragraph in router.text_frame.paragraphs:
        paragraph.alignment = PP_ALIGN.CENTER
        style_runs(paragraph, 13, True)
    arrow(slide, 8.14, 3.51, 0.42, 0.12)

    rect(slide, 8.64, 2.70, 2.90, 0.72, "HBM · 热 Expert",
         fill=BLUE_DARK, line=WHITE, size=15, color=WHITE, rounded=True)
    rect(slide, 8.64, 3.55, 2.90, 0.72, "CPU · 温 Expert",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=15, rounded=True)
    rect(slide, 8.64, 4.40, 2.90, 0.72, "SSD · 冷 Expert",
         fill=GRAY_MID, line=GRAY, size=15, rounded=True)
    arrow(slide, 10.00, 3.36, 0.18, 0.16, direction="down", color=BLUE)
    arrow(slide, 10.00, 4.21, 0.18, 0.16, direction="down", color=BLUE)
    text_box(slide, 6.11, 4.50, 2.18, 0.70,
             "联合 LRU\n在线迁移", size=15, color=BLUE_DARK)
    arrow(slide, 8.02, 4.66, 0.42, 0.12, direction="both", color=BLUE)
    text_box(slide, 7.14, 5.38, 4.10, 0.34,
             "实际路由持续修正初始放置", size=14)

    rect(slide, 1.10, 6.18, 3.25, 0.42, "FP16 恒等搬运",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=15, color=BLUE_DARK)
    rect(slide, 5.08, 6.18, 3.25, 0.42, "热点自适应",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=15, color=BLUE_DARK)
    rect(slide, 9.05, 6.18, 3.25, 0.42, "端到端可验证",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=15, color=BLUE_DARK)


def build_work_introduction(slide) -> None:
    clean_slide(slide, "引言")
    caption(slide, "MECC 面向 Expert 工作集超过单任务 HBM 与 CPU 内存预算的场景。\n它在编译期按热度生成初始放置，再在运行期根据真实路由持续纠偏。")

    # Problem strip: the full working set is larger than the fast-tier budget.
    text_box(slide, 0.58, 1.78, 1.42, 0.34, "Expert 工作集", size=13,
             color=BLUE_DARK)
    for idx in range(10):
        rect(slide, 2.08 + idx * 0.45, 1.73, 0.35, 0.44, f"E{idx+1}",
             fill=BLUE_MID if idx < 6 else GRAY_MID, line=WHITE,
             size=8, color=WHITE if idx < 6 else BLACK)
    text_box(slide, 6.62, 1.76, 1.22, 0.34, ">", size=22, color=RED)
    rect(slide, 7.64, 1.73, 0.90, 0.44, "HBM", fill=BLUE_DARK,
         line=WHITE, size=11, color=WHITE)
    rect(slide, 8.54, 1.73, 1.56, 0.44, "CPU 配额", fill=BLUE_LIGHT,
         line=WHITE, size=11)
    arrow(slide, 10.32, 1.88, 0.48, 0.12, color=RED)
    rect(slide, 10.92, 1.73, 1.12, 0.44, "SSD", fill=GRAY_MID,
         line=WHITE, size=12)
    text_box(slide, 7.60, 2.08, 2.54, 0.26, "单任务快层预算", size=12,
             color=GRAY)
    text_box(slide, 10.72, 2.08, 1.52, 0.26, "剩余权重", size=12,
             color=RED)

    rect(slide, 0.72, 2.38, 4.20, 3.10, fill=None, dash=True)
    panel_title(slide, 1.68, 2.49, 2.28, "编译期·先验放置", BLUE_DARK)
    rect(slide, 1.00, 3.08, 1.02, 0.58, "路由\n轨迹", fill=GRAY_LIGHT,
         size=11, rounded=True)
    for idx, height in enumerate((0.70, 0.56, 0.42, 0.31, 0.22, 0.15)):
        rect(slide, 2.18 + idx * 0.26, 3.68 - height, 0.17, height,
             fill=BLUE_MID if idx < 2 else GRAY_MID, line=WHITE)
    arrow(slide, 3.88, 3.30, 0.42, 0.12, color=BLUE)
    rect(slide, 4.38, 2.96, 0.34, 0.52, "H", fill=BLUE_DARK,
         line=WHITE, size=11, color=WHITE)
    rect(slide, 4.38, 3.50, 0.34, 0.66, "C", fill=BLUE_LIGHT,
         line=WHITE, size=11)
    rect(slide, 4.38, 4.18, 0.34, 0.76, "S", fill=GRAY_MID,
         line=WHITE, size=11)
    text_box(slide, 1.15, 4.27, 2.92, 0.34, "统计访问概率 pᵢ 并排序", size=13)
    text_box(slide, 0.92, 4.69, 3.52, 0.34, "热点→HBM、次热→CPU、冷门→SSD", size=12,
             color=GRAY)
    text_box(slide, 1.15, 5.02, 3.02, 0.28, "输出初始放置方案", size=13,
             color=BLUE_DARK)

    arrow(slide, 5.08, 3.72, 0.62, 0.18, color=BLUE)

    rect(slide, 5.86, 2.38, 6.72, 3.10, fill=None, dash=True)
    panel_title(slide, 8.05, 2.49, 2.34, "运行期·在线纠偏", BLUE_DARK)
    circle(slide, 6.18, 3.51, 0.52, "x", fill=WHITE, size=14)
    arrow(slide, 6.80, 3.70, 0.42, 0.12)
    diamond = slide.shapes.add_shape(
        MSO_SHAPE.DIAMOND, Inches(7.30), Inches(3.36), Inches(0.76), Inches(0.76))
    remove_theme_effects(diamond)
    diamond.fill.solid(); diamond.fill.fore_color.rgb = GRAY_LIGHT
    diamond.line.color.rgb = BLACK; diamond.text = "G"
    for paragraph in diamond.text_frame.paragraphs:
        paragraph.alignment = PP_ALIGN.CENTER
        style_runs(paragraph, 14, True)
    arrow(slide, 8.14, 3.70, 0.42, 0.12)
    rect(slide, 8.64, 2.90, 2.82, 0.54, "HBM · 热点 Expert", fill=BLUE_DARK,
         line=WHITE, size=13, color=WHITE, rounded=True)
    rect(slide, 8.64, 3.57, 2.82, 0.54, "CPU · 次热 Expert", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=13, rounded=True)
    rect(slide, 8.64, 4.24, 2.82, 0.54, "SSD · 冷门 Expert", fill=GRAY_MID,
         line=GRAY, size=13, rounded=True)
    arrow(slide, 11.72, 3.02, 0.18, 1.60, direction="both", color=BLUE)
    text_box(slide, 6.12, 4.25, 2.28, 0.62, "路由器产生\n实际 Expert 请求", size=12,
             color=GRAY)
    text_box(slide, 6.18, 4.88, 2.18, 0.40, "联合 LRU 纠偏", size=13,
             color=BLUE_DARK)
    text_box(slide, 11.66, 4.80, 0.78, 0.28, "迁移", size=12,
             color=BLUE_DARK)

    rect(slide, 0.94, 5.78, 3.55, 0.48, "热度引导的初始放置",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=14, color=BLUE_DARK)
    rect(slide, 4.89, 5.78, 3.55, 0.48, "运行期联合迁移",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=14, color=BLUE_DARK)
    rect(slide, 8.84, 5.78, 3.55, 0.48, "FP16 无损权重搬运",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=14, color=BLUE_DARK)
    text_box(slide, 2.52, 6.31, 8.34, 0.38,
             "编译期生成初始放置，运行期按真实路由纠偏，把热 Expert 留在快层。", size=17,
             color=RED)


def build_work_motivation(slide) -> None:
    clean_slide(slide, "研究动机")
    caption(slide, "共享服务器通常不会把全部 CPU 内存交给一个推理任务。\n当 Expert 工作集超过任务配额时，部分权重必须进入 SSD，频繁冷读会直接拖慢逐词生成。")

    # Shared-server quota, compact but explicit.
    rect(slide, 0.72, 1.88, 2.84, 3.96, fill=None, dash=True)
    panel_title(slide, 1.22, 2.01, 1.84, "共享资源", BLUE_DARK)
    rect(slide, 1.05, 2.58, 2.18, 2.18, fill=GRAY_LIGHT, line=GRAY,
         rounded=True)
    rect(slide, 1.28, 2.88, 1.72, 0.50, "推理任务", fill=BLUE_MID,
         line=WHITE, size=14, color=WHITE, rounded=True)
    rect(slide, 1.28, 3.51, 0.78, 0.46, "A", fill=GRAY_MID,
         line=WHITE, size=13, rounded=True)
    rect(slide, 2.13, 3.51, 0.87, 0.46, "B", fill=GRAY_MID,
         line=WHITE, size=13, rounded=True)
    rect(slide, 1.28, 4.10, 1.72, 0.42, "系统服务", fill=WHITE,
         line=GRAY, size=12, rounded=True)
    text_box(slide, 0.90, 4.92, 2.54, 0.70,
             "HBM / CPU 由多任务共享\n全机容量 ≠ 本任务配额", size=13)

    arrow(slide, 3.73, 3.72, 0.52, 0.16, color=BLUE)

    rect(slide, 4.42, 1.88, 3.82, 3.96, fill=None, dash=True)
    panel_title(slide, 5.17, 2.01, 2.32, "无热度感知的放置", BLACK)
    for idx in range(8):
        rect(slide, 4.82 + idx * 0.37, 2.60, 0.29, 0.42, f"E{idx+1}",
             fill=GRAY_LIGHT, line=GRAY, size=7)
    rect(slide, 4.82, 3.36, 0.86, 0.58, "HBM", fill=BLUE_DARK,
         line=WHITE, size=12, color=WHITE)
    rect(slide, 5.68, 3.36, 1.26, 0.58, "CPU", fill=BLUE_LIGHT,
         line=WHITE, size=12)
    rect(slide, 6.94, 3.36, 0.88, 0.58, "SSD", fill=GRAY_MID,
         line=WHITE, size=12)
    text_box(slide, 4.72, 3.98, 3.18, 0.28, "路由未命中时直接从慢层取数", size=12,
             color=GRAY)
    for x in (5.00, 5.58, 6.16, 6.74):
        arrow(slide, x, 4.32, 0.16, 0.48, direction="down", color=RED)
    rect(slide, 4.82, 4.91, 3.00, 0.46, "反复触发 SSD 冷读",
         fill=WHITE, line=RED, size=14, color=RED)
    text_box(slide, 5.10, 5.43, 2.44, 0.26, "SSD 访问暴露", size=13, color=RED)

    arrow(slide, 8.42, 3.72, 0.52, 0.16, color=BLUE)

    rect(slide, 9.10, 1.88, 3.50, 3.96, fill=None, dash=True)
    panel_title(slide, 10.08, 2.01, 1.54, "MECC", BLUE_DARK)
    # Hotness-aware expert ranking.
    for idx, height in enumerate((0.74, 0.60, 0.47, 0.36, 0.27, 0.20)):
        rect(slide, 9.49 + idx * 0.43, 3.34 - height, 0.25, height,
             fill=BLUE_MID if idx < 2 else GRAY_MID, line=WHITE)
    text_box(slide, 9.38, 3.37, 2.78, 0.28, "从离线画像获得 Expert 热度", size=12,
             color=GRAY)
    arrow(slide, 10.72, 3.68, 0.18, 0.24, direction="down", color=BLUE)
    rect(slide, 9.47, 3.98, 0.78, 0.56, "热点", fill=BLUE_DARK,
         line=WHITE, size=12, color=WHITE)
    rect(slide, 10.25, 3.98, 1.08, 0.56, "次热", fill=BLUE_LIGHT,
         line=WHITE, size=12)
    rect(slide, 11.33, 3.98, 0.78, 0.56, "冷门", fill=GRAY_MID,
         line=WHITE, size=12)
    rect(slide, 9.47, 4.91, 2.64, 0.46, "热点 Expert 优先留在快层",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=14, color=BLUE_DARK)
    text_box(slide, 9.52, 5.43, 2.54, 0.26, "减少慢层暴露", size=13,
             color=BLUE_DARK)

    rect(slide, 1.82, 6.06, 9.72, 0.48,
         "MECC 按访问热度分配快层容量，减少进入 SSD 关键路径的访问。",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=17, color=BLUE_DARK)


def build_work_insight(slide) -> None:
    clean_slide(slide, "核心洞察")
    caption(slide, "离线热度画像能从历史路由中学习稳定热点，但请求分布变化会让初始放置逐渐失效。\nMECC 把离线画像作为先验，再用真实路由驱动联合 LRU 持续升降级 Expert。")

    rect(slide, 0.68, 1.90, 3.28, 3.84, fill=None, dash=True)
    panel_title(slide, 1.12, 2.02, 2.40, "离线先验", BLUE_DARK)
    text_box(slide, 0.86, 2.49, 1.52, 0.30, "历史路由轨迹", size=12,
             color=GRAY)
    for idx, height in enumerate((0.82, 0.66, 0.49, 0.34, 0.25, 0.18)):
        rect(slide, 1.05 + idx * 0.39, 3.72 - height, 0.23, height,
             fill=BLUE_MID if idx < 2 else GRAY_MID, line=WHITE)
    arrow(slide, 2.07, 3.96, 0.18, 0.36, direction="down", color=BLUE)
    rect(slide, 1.02, 4.42, 0.74, 0.52, "H", fill=BLUE_DARK,
         line=WHITE, size=12, color=WHITE)
    rect(slide, 1.76, 4.42, 1.00, 0.52, "C", fill=BLUE_LIGHT,
         line=WHITE, size=12)
    rect(slide, 2.76, 4.42, 0.72, 0.52, "S", fill=GRAY_MID,
         line=WHITE, size=12)
    text_box(slide, 0.96, 5.08, 2.72, 0.42, "估计 pᵢ，生成初始放置", size=14)

    circle(slide, 4.16, 3.55, 0.50, "+", fill=WHITE, line=BLUE,
           size=20, color=BLUE)

    rect(slide, 4.86, 1.90, 3.62, 3.84, fill=None, dash=True)
    panel_title(slide, 5.30, 2.02, 2.74, "在线观测", BLUE_DARK)
    text_box(slide, 5.19, 2.65, 0.44, 0.26, "t₀", size=12)
    text_box(slide, 5.19, 3.55, 0.44, 0.26, "t₁", size=12)
    for row, hot in enumerate(({0, 1}, {4, 5})):
        for idx in range(7):
            circle(slide, 5.78 + idx * 0.34, 2.52 + row * 0.91, 0.26,
                   "", fill=BLUE_MID if idx in hot else GRAY_LIGHT,
                   line=BLUE_DARK if idx in hot else GRAY)
    arrow(slide, 6.82, 4.12, 0.18, 0.34, direction="down", color=BLUE)
    rect(slide, 5.44, 4.56, 1.12, 0.48, "升级", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=12, color=BLUE_DARK)
    rect(slide, 6.75, 4.56, 1.12, 0.48, "降级", fill=GRAY_LIGHT,
         line=GRAY, size=12)
    text_box(slide, 5.16, 5.08, 3.04, 0.42, "t₀→t₁ 热点迁移，触发升降级", size=13)

    arrow(slide, 8.68, 3.72, 0.56, 0.18, color=BLUE)

    rect(slide, 9.38, 1.90, 3.24, 3.84, fill=None, dash=True)
    panel_title(slide, 10.35, 2.02, 1.30, "MECC", BLUE_DARK)
    rect(slide, 9.80, 2.64, 2.40, 0.48, "初始放置方案", fill=GRAY_LIGHT,
         line=GRAY, size=13, rounded=True)
    arrow(slide, 10.90, 3.20, 0.18, 0.34, direction="down", color=BLUE)
    rect(slide, 9.80, 3.64, 2.40, 0.48, "联合 LRU 纠偏", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=13, color=BLUE_DARK, rounded=True)
    arrow(slide, 10.90, 4.20, 0.18, 0.34, direction="down", color=BLUE)
    rect(slide, 9.74, 4.64, 0.72, 0.50, "H", fill=BLUE_DARK,
         line=WHITE, size=12, color=WHITE)
    rect(slide, 10.46, 4.64, 0.92, 0.50, "C", fill=BLUE_LIGHT,
         line=WHITE, size=12)
    rect(slide, 11.38, 4.64, 0.72, 0.50, "S", fill=GRAY_MID,
         line=WHITE, size=12)
    text_box(slide, 9.58, 5.18, 2.68, 0.34, "初始方案是起点，LRU 持续纠偏", size=12,
             color=BLUE_DARK)

    # Verified D2 result as the empirical landing point.
    rect(slide, 0.82, 5.98, 4.18, 0.54, "A100 80GB · Mixtral-8×7B：",
         fill=GRAY_LIGHT, line=GRAY, size=15)
    rect(slide, 5.00, 5.98, 3.08, 0.54, "相较 SwapMoE\n综合加速 1.33×",
         fill=BLUE_DARK, line=BLUE_DARK, size=13, color=WHITE)
    rect(slide, 8.08, 5.98, 4.44, 0.54, "SSD 命中 34.5% → 17.6%。",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=16, color=BLUE_DARK)


def build_problem_model(slide) -> None:
    clean_slide(slide, "问题建模")
    caption(slide, "MECC 将每个 Expert 权重块视为只读对象，将路由选择视为访问请求。\n目标是在 HBM 与 CPU 容量约束下，最小化整个请求流的取数与迁移开销。")

    rect(slide, 0.70, 1.90, 3.28, 3.56, fill=None, dash=True)
    panel_title(slide, 1.35, 2.03, 1.98, "只读对象集", BLUE_DARK)
    for idx in range(8):
        rect(slide, 1.02 + (idx % 4) * 0.64, 2.72 + (idx // 4) * 0.76,
             0.50, 0.56, f"E{idx+1}", fill=BLUE_LIGHT if idx < 4 else GRAY_LIGHT,
             line=BLUE_DARK if idx < 4 else GRAY, size=10, rounded=True)
    text_box(slide, 1.03, 4.43, 2.64, 0.34, "大小 sᵢ  ·  访问概率 pᵢ", size=14)
    text_box(slide, 1.02, 4.90, 2.66, 0.30, "MoE 映射：Expert 权重块", size=12,
             color=GRAY)

    arrow(slide, 4.12, 3.55, 0.52, 0.16, color=BLUE)

    rect(slide, 4.78, 1.90, 3.30, 3.56, fill=None, dash=True)
    panel_title(slide, 5.52, 2.03, 1.82, "请求过程", BLUE_DARK)
    for idx in range(9):
        circle(slide, 5.10 + idx * 0.29, 2.72 + (idx % 2) * 0.52, 0.24,
               str((idx * 3) % 8 + 1), fill=BLUE_MID if idx in (0,1,5,6) else WHITE,
               line=BLUE_DARK if idx in (0,1,5,6) else GRAY,
               size=8, color=WHITE if idx in (0,1,5,6) else BLACK)
    arrow(slide, 5.72, 3.92, 1.42, 0.15, color=BLUE)
    text_box(slide, 5.16, 4.38, 2.54, 0.34, "X₁, X₂, …, Xᵀ", size=17,
             color=BLUE_DARK)
    text_box(slide, 5.10, 4.88, 2.66, 0.30, "MoE 映射：路由选中 Expert", size=12,
             color=GRAY)

    arrow(slide, 8.22, 3.55, 0.52, 0.16, color=BLUE)

    rect(slide, 8.88, 1.90, 3.74, 3.56, fill=None, dash=True)
    panel_title(slide, 9.75, 2.03, 2.00, "三级存储", BLUE_DARK)
    rect(slide, 9.30, 2.67, 2.90, 0.58, "HBM：容量小、延迟低",
         fill=BLUE_DARK, line=WHITE, size=14, color=WHITE, rounded=True)
    rect(slide, 9.30, 3.39, 2.90, 0.58, "CPU：容量中等",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=14, rounded=True)
    rect(slide, 9.30, 4.11, 2.90, 0.58, "SSD：容量大、冷读慢",
         fill=GRAY_MID, line=GRAY, size=14, rounded=True)
    text_box(slide, 9.30, 4.91, 2.90, 0.28, "Tₕ < Tᴄ ≪ Tₛ", size=15,
             color=RED)

    rect(slide, 1.05, 5.78, 11.20, 0.60,
         "最小化：Σ pᵢ · T(放置层级)  +  运行期迁移开销",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=19, color=BLUE_DARK)
    text_box(slide, 3.20, 6.47, 6.92, 0.28,
             "容量约束决定“放哪里”，访问概率决定“谁更值得留在快层”。",
             size=14, color=RED)


def build_compile_placement(slide) -> None:
    clean_slide(slide, "编译期放置")
    caption(slide, "编译器从代表性路由轨迹中估计 Expert 热度，并按访问概率从高到低排序。\n在等大小对象和独立容量上限下，依次填满 HBM、CPU，剩余 Expert 放入 SSD。")

    steps = [(0.62, "历史路由", GRAY_LIGHT), (3.06, "估计热度", BLUE_LIGHT),
             (5.50, "概率排序", BLUE_LIGHT), (7.94, "容量切分", BLUE_LIGHT),
             (10.38, "生成方案", GRAY_LIGHT)]
    for x, label, fill in steps:
        rect(slide, x, 2.05, 1.80, 0.48, label, fill=fill,
             line=BLUE_DARK if fill == BLUE_LIGHT else GRAY, size=14, rounded=True,
             color=BLUE_DARK if fill == BLUE_LIGHT else BLACK)
    for x in (2.51, 4.95, 7.39, 9.83):
        arrow(slide, x, 2.21, 0.42, 0.12, color=BLUE)

    rect(slide, 0.68, 2.82, 2.26, 2.62, fill=None, dash=True)
    for idx, hot in enumerate((1,2,1,5,2,1,6,1,2,7,1,5)):
        circle(slide, 0.93 + (idx % 6) * 0.29, 3.12 + (idx // 6) * 0.48,
               0.22, str(hot), fill=BLUE_MID if hot in (1,2) else WHITE,
               line=BLUE_DARK if hot in (1,2) else GRAY, size=7,
               color=WHITE if hot in (1,2) else BLACK)
    text_box(slide, 0.94, 4.35, 1.70, 0.32, "路由计数", size=13)
    text_box(slide, 0.91, 4.78, 1.76, 0.30, "c₁, c₂, …, cₙ", size=13, color=GRAY)

    rect(slide, 3.12, 2.82, 2.26, 2.62, fill=None, dash=True)
    text_box(slide, 3.56, 3.10, 1.36, 0.58, "α", size=31, color=BLUE_DARK)
    text_box(slide, 3.40, 3.82, 1.72, 0.34, "热度集中程度", size=13)
    text_box(slide, 3.38, 4.34, 1.76, 0.48, "α 越大\n热点越集中", size=13, color=GRAY)

    rect(slide, 5.56, 2.82, 2.26, 2.62, fill=None, dash=True)
    for idx, height in enumerate((1.20,0.94,0.72,0.54,0.39,0.28)):
        rect(slide, 5.85 + idx * 0.28, 4.36 - height, 0.18, height,
             fill=BLUE_MID if idx < 2 else GRAY_MID, line=WHITE)
    text_box(slide, 5.86, 4.60, 1.62, 0.30, "p₁ ≥ p₂ ≥ … ≥ pₙ", size=12)

    rect(slide, 8.00, 2.82, 2.26, 2.62, fill=None, dash=True)
    rect(slide, 8.28, 3.14, 1.70, 0.48, "Kₕ", fill=BLUE_DARK,
         line=WHITE, size=15, color=WHITE)
    rect(slide, 8.28, 3.74, 1.70, 0.48, "Kᴄ", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=15)
    rect(slide, 8.28, 4.34, 1.70, 0.48, "N−Kₕ−Kᴄ", fill=GRAY_MID,
         line=GRAY, size=13)

    rect(slide, 10.44, 2.82, 2.26, 2.62, fill=None, dash=True)
    rect(slide, 10.72, 3.12, 1.70, 0.52, "HBM：E1–E2", fill=BLUE_DARK,
         line=WHITE, size=12, color=WHITE)
    rect(slide, 10.72, 3.78, 1.70, 0.52, "CPU：E3–E5", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=12)
    rect(slide, 10.72, 4.44, 1.70, 0.52, "SSD：E6–EN", fill=GRAY_MID,
         line=GRAY, size=12)

    rect(slide, 2.18, 5.86, 9.00, 0.52,
         "静态放置原则：概率越高，存储层级越快；可用容量尽可能填满。",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=17, color=BLUE_DARK)


def build_runtime_migration(slide) -> None:
    clean_slide(slide, "运行期联合迁移")
    caption(slide, "真实请求到来后，MECC 先查找 HBM，再查找 CPU，最后才访问 SSD。\nCPU 命中的 Expert 升级到 HBM，HBM 淘汰项降级到 CPU，两层共享一条 LRU 更新链。")

    circle(slide, 0.80, 3.33, 0.62, "E", fill=WHITE, size=16)
    text_box(slide, 0.62, 4.06, 0.98, 0.30, "Expert 请求", size=12)
    arrow(slide, 1.52, 3.56, 0.52, 0.14, color=BLUE)

    rect(slide, 2.18, 2.04, 2.58, 0.76, "HBM 命中？", fill=BLUE_DARK,
         line=WHITE, size=17, color=WHITE, rounded=True)
    rect(slide, 2.18, 3.31, 2.58, 0.76, "CPU 命中？", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=17, rounded=True)
    rect(slide, 2.18, 4.58, 2.58, 0.76, "SSD 冷读", fill=GRAY_MID,
         line=GRAY, size=17, rounded=True)
    arrow(slide, 3.36, 2.90, 0.18, 0.31, direction="down", color=BLACK)
    arrow(slide, 3.36, 4.17, 0.18, 0.31, direction="down", color=BLACK)

    arrow(slide, 4.93, 2.33, 0.55, 0.14, color=BLUE)
    arrow(slide, 4.93, 3.60, 0.55, 0.14, color=BLUE)
    arrow(slide, 4.93, 4.87, 0.55, 0.14, color=BLUE)
    rect(slide, 5.62, 2.05, 2.18, 0.70, "直接计算", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=16, rounded=True)
    rect(slide, 5.62, 3.32, 2.18, 0.70, "升级到 HBM", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=16, rounded=True)
    rect(slide, 5.62, 4.59, 2.18, 0.70, "SSD→CPU→HBM", fill=GRAY_LIGHT,
         line=GRAY, size=14, rounded=True)

    arrow(slide, 8.04, 3.56, 0.55, 0.14, color=BLUE)
    rect(slide, 8.73, 2.10, 3.42, 0.66, "HBM · 当前热点", fill=BLUE_DARK,
         line=WHITE, size=16, color=WHITE, rounded=True)
    rect(slide, 8.73, 3.40, 3.42, 0.66, "CPU · 候选热点", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=16, rounded=True)
    rect(slide, 8.73, 4.70, 3.42, 0.66, "SSD · 冷门权重", fill=GRAY_MID,
         line=GRAY, size=16, rounded=True)
    arrow(slide, 10.24, 2.86, 0.20, 0.43, direction="down", color=BLUE)
    arrow(slide, 10.62, 4.20, 0.20, 0.40, direction="down", color=GRAY)
    text_box(slide, 10.55, 2.86, 1.32, 0.30, "淘汰后降级", size=12, color=BLUE_DARK)
    text_box(slide, 9.05, 4.21, 1.20, 0.30, "需要时升级", size=12, color=BLUE_DARK)

    rect(slide, 2.32, 5.92, 8.72, 0.54,
         "初始方案决定起点，联合 LRU 让 HBM 与 CPU 随真实工作集一起演化。",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=17, color=BLUE_DARK)


def build_system(slide) -> None:
    clean_slide(slide, "系统实现")
    caption(slide, "MECC 将编译器、三级缓存引擎、MoE 前向适配与端到端评测串成一条可执行链路。\n编译产物只描述初始放置；运行时引擎管理命中、搬运、替换与真实 SSD 冷读。")

    lanes = [(0.68, "编译器", "路由画像\nα 估计\nKₕ / Kᴄ 优化", BLUE_LIGHT),
             (3.34, "放置方案", "Expert → HBM\nExpert → CPU\nExpert → SSD", GRAY_LIGHT),
             (6.00, "三级引擎", "联合 LRU\n异步搬运\n冷存读取", BLUE_LIGHT),
             (8.66, "MoE 适配", "路由选择\nExpert 执行\n输出聚合", GRAY_LIGHT),
             (11.32, "评测", "TTFT\nTPOT\n命中率", BLUE_LIGHT)]
    widths = [2.02,2.02,2.02,2.02,1.32]
    for (x, title, body, fill), w in zip(lanes, widths):
        rect(slide, x, 2.18, w, 0.52, title, fill=BLUE_DARK,
             line=WHITE, size=15, color=WHITE, rounded=True)
        rect(slide, x, 2.84, w, 2.36, body, fill=fill,
             line=BLUE_DARK if fill == BLUE_LIGHT else GRAY, size=14, rounded=True)
    for x in (2.78,5.44,8.10,10.76):
        arrow(slide, x, 3.82, 0.42, 0.14, color=BLUE)

    text_box(slide, 0.72, 5.43, 2.00, 0.32, "输出：每层容量切分", size=12, color=GRAY)
    text_box(slide, 5.93, 5.43, 2.20, 0.32, "维护：三级驻留状态", size=12, color=GRAY)
    text_box(slide, 8.61, 5.43, 2.18, 0.32, "接入：真实 MoE 前向", size=12, color=GRAY)
    text_box(slide, 11.08, 5.43, 1.68, 0.32, "输出：端到端指标", size=12, color=GRAY)
    rect(slide, 2.22, 6.02, 8.92, 0.52,
         "从编译方案到真实生成，所有策略共用同一精度、容量预算和冷存。",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=17, color=BLUE_DARK)


def build_experiment_setup(slide) -> None:
    clean_slide(slide, "实验设计")
    caption(slide, "主实验在 A100 80GB 上运行 Mixtral-8×7B，Expert 权重集约 90GB，部分权重被迫落入冷 SSD。\n所有策略共用同一 fp16 权重存储、路由输入和容量预算，对比仅聚焦缓存管理机制。")

    rect(slide, 0.72, 1.96, 4.00, 3.70, fill=None, dash=True)
    panel_title(slide, 1.64, 2.08, 2.16, "平台与工作负载", BLUE_DARK)
    rect(slide, 1.08, 2.74, 1.42, 0.70, "A100\n80GB", fill=BLUE_DARK,
         line=WHITE, size=16, color=WHITE, rounded=True)
    rect(slide, 2.74, 2.74, 1.54, 0.70, "冷 SSD\n存储", fill=GRAY_MID,
         line=GRAY, size=15, rounded=True)
    rect(slide, 1.08, 3.72, 3.20, 0.66, "Mixtral-8×7B", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=17, rounded=True)
    rect(slide, 1.08, 4.59, 3.20, 0.54, "Expert 权重集 ≈ 90GB", fill=GRAY_LIGHT,
         line=GRAY, size=14)
    text_box(slide, 1.08, 5.23, 3.20, 0.28, "真实生成 · 真实冷读", size=13, color=RED)

    rect(slide, 4.98, 1.96, 7.64, 3.70, fill=None, dash=True)
    panel_title(slide, 7.55, 2.08, 2.50, "同预算策略对比", BLUE_DARK)
    policies = [(5.38, "MECC", "HBM + CPU\n联合动态 LRU", BLUE_DARK, WHITE),
                (7.13, "SwapMoE-style", "HBM 动态\nCPU 静态", GRAY_LIGHT, BLACK),
                (8.88, "Fiddler", "CPU 执行\n搬运激活", GRAY_LIGHT, BLACK),
                (10.63, "朴素流式", "每次流式\n搬运权重", GRAY_LIGHT, BLACK)]
    for x, name, body, fill, color in policies:
        rect(slide, x, 2.78, 1.50, 0.50, name, fill=fill,
             line=BLUE_DARK if name == "MECC" else GRAY, size=12, color=color,
             rounded=True)
        rect(slide, x, 3.42, 1.50, 1.12, body,
             fill=BLUE_LIGHT if name == "MECC" else WHITE,
             line=BLUE_DARK if name == "MECC" else GRAY, size=12, rounded=True)
    text_box(slide, 5.38, 4.86, 6.75, 0.42,
             "相同 fp16 · 相同 HBM/CPU 预算 · 相同请求流",
             size=14, color=BLUE_DARK)

    rect(slide, 1.02, 5.98, 2.62, 0.52, "综合加速比", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=15, color=BLUE_DARK)
    rect(slide, 3.90, 5.98, 2.62, 0.52, "SSD / CPU 命中率", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=15, color=BLUE_DARK)
    rect(slide, 6.78, 5.98, 2.62, 0.52, "TTFT / TPOT", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=15, color=BLUE_DARK)
    rect(slide, 9.66, 5.98, 2.62, 0.52, "PPL", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=15, color=BLUE_DARK)


def draw_pair_bars(slide, x, y, title, swap_val, mecc_val, max_val, suffix=""):
    text_box(slide, x, y, 3.18, 0.36, title, size=16, color=BLUE_DARK)
    text_box(slide, x, y + 0.64, 0.78, 0.28, "对照", size=12, align=PP_ALIGN.LEFT)
    text_box(slide, x, y + 1.31, 0.78, 0.28, "MECC", size=12, align=PP_ALIGN.LEFT)
    sw = 2.05 * swap_val / max_val
    mw = 2.05 * mecc_val / max_val
    rect(slide, x + 0.82, y + 0.59, sw, 0.36, "", fill=GRAY_MID, line=GRAY_MID)
    rect(slide, x + 0.82, y + 1.26, mw, 0.36, "", fill=BLUE_MID, line=BLUE_MID)
    text_box(slide, x + 0.88 + sw, y + 0.57, 0.76, 0.38,
             f"{swap_val}{suffix}", size=12, align=PP_ALIGN.LEFT)
    text_box(slide, x + 0.88 + mw, y + 1.24, 0.76, 0.38,
             f"{mecc_val}{suffix}", size=12, color=BLUE_DARK,
             align=PP_ALIGN.LEFT)


def build_results(slide) -> None:
    clean_slide(slide, "主实验结果")
    caption(slide, "A100 上的 Mixtral-8×7B 端到端实验：MECC 相较同预算 SwapMoE-style 综合加速 1.33×。\nCPU 命中率从 23.3% 提升到 38.0%，SSD 命中率从 34.5% 降低到 17.6%。")

    draw_pair_bars(slide, 0.72, 2.08, "综合性能（越高越好）", 1.00, 1.33, 1.45, "×")
    draw_pair_bars(slide, 4.78, 2.08, "SSD 命中率（越低越好）", 34.5, 17.6, 40.0, "%")
    draw_pair_bars(slide, 8.84, 2.08, "CPU 命中率（越高越好）", 23.3, 38.0, 42.0, "%")

    rect(slide, 0.92, 4.52, 3.62, 0.72, "1.33×\n综合加速", fill=BLUE_DARK,
         line=BLUE_DARK, size=17, color=WHITE, rounded=True)
    rect(slide, 4.86, 4.52, 3.62, 0.72, "SSD 访问\n下降 16.9 个百分点", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=15, color=BLUE_DARK, rounded=True)
    rect(slide, 8.80, 4.52, 3.62, 0.72, "CPU 命中\n提升 14.7 个百分点", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=15, color=BLUE_DARK, rounded=True)

    rect(slide, 1.54, 5.72, 10.28, 0.58,
         "fp16 执行 · MECC PPL 24.57 · 不通过量化换取容量",
         fill=GRAY_LIGHT, line=GRAY, size=17)
    text_box(slide, 3.48, 6.40, 6.40, 0.30,
             "更少慢层暴露 → 更短等待时间 → 更高端到端性能",
             size=15, color=RED)


def build_summary(slide) -> None:
    clean_slide(slide, "总结")
    caption(slide, "MECC 将编译期先验、运行期纠偏与 fp16 恒等搬运统一为三级缓存系统。\n它让超出任务内存预算的 MoE 模型更有效地协同使用 HBM、CPU 与 SSD。")

    cards = [(0.82, "1", "编译期放置", "学习路由热度\n在容量约束下\n生成三级初始方案"),
             (4.74, "2", "运行期纠偏", "HBM / CPU 联合 LRU\n随真实路由\n动态升级与降级"),
             (8.66, "3", "无损系统实现", "fp16 权重恒等搬运\n真实 SSD 冷存\n端到端生成验证")]
    for x, num, title, body in cards:
        circle(slide, x, 2.24, 0.58, num, fill=BLUE_DARK, line=BLUE_DARK,
               size=17, color=WHITE)
        rect(slide, x + 0.76, 2.16, 2.80, 0.62, title, fill=BLUE_LIGHT,
             line=BLUE_DARK, size=16, color=BLUE_DARK, rounded=True)
        rect(slide, x, 3.02, 3.56, 1.56, body, fill=GRAY_LIGHT,
             line=GRAY, size=15, rounded=True)

    arrow(slide, 3.80, 3.66, 0.54, 0.16, color=BLUE)
    arrow(slide, 7.72, 3.66, 0.54, 0.16, color=BLUE)
    rect(slide, 2.08, 5.12, 9.20, 0.66,
         "Mixtral-8×7B · A100 80GB · 相较 SwapMoE-style 综合加速 1.33×",
         fill=BLUE_DARK, line=BLUE_DARK, size=19, color=WHITE)
    rect(slide, 3.28, 6.04, 6.80, 0.54,
         "SSD 命中率：34.5% → 17.6%",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=18, color=BLUE_DARK)


def build_problem_model_v2(slide) -> None:
    clean_slide(slide, "问题建模")
    caption(slide, "MECC 需要同时回答两个问题：哪些 Expert 更值得占用快层，以及有限的 HBM 与 CPU 容量应如何分配。\n路由访问频率给出 Expert 的优先级，三级存储容量则给出可行放置边界。")

    # 1. Objects
    circle(slide, 0.74, 2.02, 0.48, "1", fill=BLUE_DARK, line=BLUE_DARK,
           size=15, color=WHITE)
    panel_title(slide, 1.30, 2.07, 2.30, "Expert 权重块", BLUE_DARK)
    rect(slide, 0.70, 2.55, 3.22, 2.60, fill=None, dash=True)
    for idx in range(8):
        rect(slide, 1.02 + (idx % 4) * 0.64, 2.94 + (idx // 4) * 0.74,
             0.50, 0.54, f"E{idx+1}", fill=BLUE_LIGHT if idx < 4 else GRAY_LIGHT,
             line=BLUE_DARK if idx < 4 else GRAY, size=10, rounded=True)
    text_box(slide, 1.00, 4.54, 2.62, 0.34, "只读 · 可独立搬运 · 大小 sᵢ", size=13)

    arrow(slide, 4.08, 3.72, 0.54, 0.16, color=BLUE)

    # 2. Priority from access frequency
    circle(slide, 4.78, 2.02, 0.48, "2", fill=BLUE_DARK, line=BLUE_DARK,
           size=15, color=WHITE)
    panel_title(slide, 5.34, 2.07, 2.36, "路由访问热度", BLUE_DARK)
    rect(slide, 4.74, 2.55, 3.72, 2.60, fill=None, dash=True)
    heights = (1.35,1.05,0.80,0.60,0.44,0.31,0.22,0.16)
    for idx, height in enumerate(heights):
        rect(slide, 5.12 + idx * 0.37, 4.43 - height, 0.23, height,
             fill=BLUE_MID if idx < 2 else GRAY_MID, line=WHITE)
        text_box(slide, 5.08 + idx * 0.37, 4.49, 0.31, 0.22,
                 f"E{idx+1}", size=8, bold=False)
    text_box(slide, 5.14, 4.82, 2.90, 0.28, "p₁ ≥ p₂ ≥ … ≥ pₙ", size=13,
             color=BLUE_DARK)

    arrow(slide, 8.62, 3.72, 0.54, 0.16, color=BLUE)

    # 3. Placement under capacity constraints
    circle(slide, 9.30, 2.02, 0.48, "3", fill=BLUE_DARK, line=BLUE_DARK,
           size=15, color=WHITE)
    panel_title(slide, 9.86, 2.07, 2.22, "容量约束放置", BLUE_DARK)
    rect(slide, 9.26, 2.55, 3.34, 2.60, fill=None, dash=True)
    rect(slide, 9.65, 2.91, 2.56, 0.54, "HBM：最热 Kₕ 个", fill=BLUE_DARK,
         line=WHITE, size=14, color=WHITE, rounded=True)
    rect(slide, 9.65, 3.61, 2.56, 0.54, "CPU：次热 Kᴄ 个", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=14, rounded=True)
    rect(slide, 9.65, 4.31, 2.56, 0.54, "SSD：其余 Expert", fill=GRAY_MID,
         line=GRAY, size=14, rounded=True)

    rect(slide, 1.12, 5.62, 11.10, 0.56,
         "目标：在容量约束下，最小化  Σ pᵢ · T(放置层级)  +  迁移开销",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=18, color=BLUE_DARK)
    text_box(slide, 2.74, 6.34, 7.86, 0.30,
             "访问越频繁的 Expert，越应优先留在低延迟存储层。",
             size=15, color=RED)


def build_compile_placement_v2(slide) -> None:
    clean_slide(slide, "编译期放置")
    caption(slide, "编译期不搬运权重，而是把历史路由轨迹编译成每层的三级初始放置方案。\n整个过程只包含四步：统计访问、估计热度、按概率排序、按容量填充。")

    xs = [0.62, 3.72, 6.82, 9.92]
    titles = ["① 统计路由", "② 估计热度", "③ 排序 Expert", "④ 填充容量"]
    for x, title in zip(xs, titles):
        rect(slide, x, 2.02, 2.78, 0.52, title, fill=BLUE_LIGHT,
             line=BLUE_DARK, size=15, color=BLUE_DARK, rounded=True)
        rect(slide, x, 2.72, 2.78, 2.64, fill=None, dash=True)
    for x in (3.16, 6.26, 9.36):
        arrow(slide, x, 3.75, 0.42, 0.14, color=BLUE)

    # Step 1: trace
    vals = (1,2,1,5,2,1,6,1,2,7,1,5)
    for idx, val in enumerate(vals):
        circle(slide, 0.94 + (idx % 6) * 0.34, 3.08 + (idx // 6) * 0.52,
               0.25, str(val), fill=BLUE_MID if val in (1,2) else WHITE,
               line=BLUE_DARK if val in (1,2) else GRAY, size=8,
               color=WHITE if val in (1,2) else BLACK)
    text_box(slide, 1.00, 4.40, 2.02, 0.34, "计数：c₁, c₂, …, cₙ", size=13)
    text_box(slide, 1.02, 4.86, 1.98, 0.28, "输入：历史路由轨迹", size=12, color=GRAY)

    # Step 2: profile
    text_box(slide, 4.40, 3.00, 1.42, 0.54, "α", size=30, color=BLUE_DARK)
    text_box(slide, 4.10, 3.69, 2.02, 0.34, "热度集中程度", size=14)
    text_box(slide, 4.05, 4.24, 2.12, 0.54, "得到每个 Expert\n的访问概率 pᵢ", size=13, color=GRAY)

    # Step 3: ranked bars
    for idx, height in enumerate((1.35,1.06,0.80,0.60,0.44,0.31)):
        rect(slide, 7.18 + idx * 0.34, 4.45 - height, 0.22, height,
             fill=BLUE_MID if idx < 2 else GRAY_MID, line=WHITE)
    text_box(slide, 7.18, 4.66, 1.98, 0.28, "p₁ ≥ p₂ ≥ … ≥ pₙ", size=12)
    text_box(slide, 7.23, 4.98, 1.86, 0.24, "输出：热度排名", size=12, color=GRAY)

    # Step 4: final plan
    rect(slide, 10.28, 3.00, 2.06, 0.54, "HBM：E1–E2", fill=BLUE_DARK,
         line=WHITE, size=13, color=WHITE)
    rect(slide, 10.28, 3.72, 2.06, 0.54, "CPU：E3–E5", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=13)
    rect(slide, 10.28, 4.44, 2.06, 0.54, "SSD：E6–EN", fill=GRAY_MID,
         line=GRAY, size=13)

    rect(slide, 2.18, 5.85, 9.00, 0.54,
         "等大小对象 + 独立容量上限：按热度从快到慢填满各层即为最优静态放置。",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=16, color=BLUE_DARK)


def build_runtime_migration_v2(slide) -> None:
    clean_slide(slide, "运行期联合迁移")
    caption(slide, "运行期按 HBM → CPU → SSD 的顺序查找 Expert，只在前一层未命中时才访问更慢层。\nCPU 命中项升级到 HBM，HBM 淘汰项降级到 CPU，从而让两层共同跟随当前工作集。")

    # Three explicit access lanes.
    text_box(slide, 0.52, 1.88, 1.14, 0.30, "查找顺序", size=13, color=BLUE_DARK)
    circle(slide, 0.78, 2.10, 0.56, "E", fill=WHITE, size=15)
    arrow(slide, 1.44, 2.29, 0.44, 0.13, color=BLUE)

    rect(slide, 1.98, 2.04, 2.22, 0.66, "HBM 命中", fill=BLUE_DARK,
         line=WHITE, size=16, color=WHITE, rounded=True)
    rect(slide, 1.98, 3.17, 2.22, 0.66, "CPU 命中", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=16, rounded=True)
    rect(slide, 1.98, 4.30, 2.22, 0.66, "SSD 冷读", fill=GRAY_MID,
         line=GRAY, size=16, rounded=True)
    arrow(slide, 2.98, 2.79, 0.18, 0.28, direction="down", color=BLACK)
    text_box(slide, 3.20, 2.80, 0.72, 0.24, "未命中", size=12, color=GRAY)
    arrow(slide, 2.98, 3.92, 0.18, 0.28, direction="down", color=BLACK)
    text_box(slide, 3.20, 3.93, 0.72, 0.24, "未命中", size=12, color=GRAY)

    # Outcomes aligned with each lane.
    arrow(slide, 4.36, 2.28, 0.48, 0.13, color=BLUE)
    arrow(slide, 4.36, 3.41, 0.48, 0.13, color=BLUE)
    arrow(slide, 4.36, 4.54, 0.48, 0.13, color=BLUE)
    rect(slide, 4.96, 2.04, 2.48, 0.66, "直接执行 Expert", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=15, rounded=True)
    rect(slide, 4.96, 3.17, 2.48, 0.66, "搬到 HBM 后执行", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=15, rounded=True)
    rect(slide, 4.96, 4.30, 2.48, 0.66, "SSD→CPU→HBM", fill=GRAY_LIGHT,
         line=GRAY, size=14, rounded=True)

    arrow(slide, 7.62, 3.44, 0.54, 0.14, color=BLUE)

    # Joint HBM/CPU LRU state.
    rect(slide, 8.30, 1.96, 4.18, 3.20, fill=None, dash=True)
    panel_title(slide, 9.18, 2.08, 2.42, "HBM / CPU 联合 LRU", BLUE_DARK)
    rect(slide, 8.72, 2.76, 3.34, 0.66, "HBM · 当前热点", fill=BLUE_DARK,
         line=WHITE, size=15, color=WHITE, rounded=True)
    rect(slide, 8.72, 4.00, 3.34, 0.66, "CPU · 候选热点", fill=BLUE_LIGHT,
         line=BLUE_DARK, size=15, rounded=True)
    arrow(slide, 9.28, 3.48, 0.18, 0.42, direction="down", color=GRAY)
    text_box(slide, 8.47, 3.50, 0.76, 0.26, "淘汰降级", size=12, color=GRAY)
    arrow(slide, 11.22, 3.46, 0.18, 0.42, direction="up", color=BLUE)
    text_box(slide, 11.40, 3.52, 0.78, 0.26, "命中升级", size=12, color=BLUE_DARK)

    rect(slide, 2.20, 5.76, 8.96, 0.54,
         "初始放置提供起点，联合 LRU 用真实路由持续修正 HBM 与 CPU 的内容。",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=17, color=BLUE_DARK)


def chart_axes(slide, x, y, w, h, title, max_value, ticks, values, suffix=""):
    text_box(slide, x, y, w, 0.36, title, size=16, color=BLUE_DARK)
    px, py = x + 0.62, y + 0.58
    pw, ph = w - 0.82, h - 1.02
    # grid and y labels
    for tick in ticks:
        yy = py + ph - ph * tick / max_value
        rect(slide, px, yy, pw, 0.012, fill=GRAY_MID, line=GRAY_MID)
        text_box(slide, x, yy - 0.13, 0.52, 0.26, f"{tick:g}", size=10,
                 bold=False, color=GRAY, align=PP_ALIGN.RIGHT)
    rect(slide, px, py, 0.022, ph, fill=BLACK, line=BLACK)
    rect(slide, px, py + ph, pw, 0.022, fill=BLACK, line=BLACK)
    colors = [GRAY_MID, BLUE_MID]
    labels = ["对照", "MECC"]
    for idx, value in enumerate(values):
        bw = 0.62
        bx = px + 0.52 + idx * 1.08
        bh = ph * value / max_value
        by = py + ph - bh
        rect(slide, bx, by, bw, bh, fill=colors[idx], line=colors[idx])
        text_box(slide, bx - 0.16, by - 0.32, bw + 0.32, 0.28,
                 f"{value}{suffix}", size=12,
                 color=BLUE_DARK if idx == 1 else BLACK)
        text_box(slide, bx - 0.20, py + ph + 0.07, bw + 0.40, 0.28,
                 labels[idx], size=11, bold=False)


def build_results_v2(slide) -> None:
    clean_slide(slide, "主实验结果")
    caption(slide, "A100 上的 Mixtral-8×7B 端到端实验：MECC 相较同预算 SwapMoE-style 综合加速 1.33×。\nCPU 命中率从 23.3% 提升到 38.0%，SSD 命中率从 34.5% 降低到 17.6%。")

    chart_axes(slide, 0.46, 1.92, 3.86, 3.46, "综合性能（倍）",
               1.5, [0,0.5,1.0,1.5], [1.0,1.33], "×")
    chart_axes(slide, 4.74, 1.92, 3.86, 3.46, "SSD 命中率（%）",
               40, [0,10,20,30,40], [34.5,17.6], "%")
    chart_axes(slide, 9.02, 1.92, 3.86, 3.46, "CPU 命中率（%）",
               40, [0,10,20,30,40], [23.3,38.0], "%")

    # Shared legend and interpretation.
    rect(slide, 4.92, 5.45, 0.28, 0.22, fill=GRAY_MID, line=GRAY_MID)
    text_box(slide, 5.27, 5.39, 1.16, 0.32, "SwapMoE-style", size=12,
             align=PP_ALIGN.LEFT)
    rect(slide, 6.75, 5.45, 0.28, 0.22, fill=BLUE_MID, line=BLUE_MID)
    text_box(slide, 7.10, 5.39, 0.82, 0.32, "MECC", size=12,
             color=BLUE_DARK, align=PP_ALIGN.LEFT)
    rect(slide, 1.40, 5.92, 10.54, 0.54,
         "fp16 执行 · MECC PPL 24.57 · 更少 SSD 冷读是 1.33× 综合加速的主要来源",
         fill=BLUE_LIGHT, line=BLUE_DARK, size=16, color=BLUE_DARK)


def build(template: Path, output: Path) -> None:
    prs = Presentation(template)
    # Keep ten title-bearing slides from the approved deck so its masters,
    # divider line, title typography, and page-number style remain intact.
    retain_slides(prs, set(range(1, 11)))
    build_work_introduction(prs.slides[0])
    build_work_motivation(prs.slides[1])
    build_work_insight(prs.slides[2])
    build_problem_model_v2(prs.slides[3])
    build_compile_placement_v2(prs.slides[4])
    build_runtime_migration_v2(prs.slides[5])
    build_system(prs.slides[6])
    build_experiment_setup(prs.slides[7])
    build_results_v2(prs.slides[8])
    build_summary(prs.slides[9])
    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    build(args.template, args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
