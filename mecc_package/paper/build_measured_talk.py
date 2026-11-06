"""Build the group-meeting deck using only committed A100 numeric results."""
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches
from pptx.enum.text import PP_ALIGN

import refine_hpca_talk as r
from dac2027.build_measured_a100 import load, OUT as FIGS

HERE = Path(__file__).resolve().parent
OUT = HERE / "current" / "MECC_A100_measured.pptx"


def slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def figure_page(prs, n, title, lead, figure, caption):
    s = slide(prs)
    r.base(s, n, title, lead)
    s.shapes.add_picture(str(FIGS / (figure + ".png")), Inches(.83), Inches(2.38),
                         width=Inches(11.65))
    r.box(s, .97, 6.03, 11.39, .48, r.PALE)
    r.t(s, 1.08, 6.11, 11.12, .32, caption, 15, True, r.NAVY, PP_ALIGN.CENTER)
    return s


def protocol(prs):
    s = slide(prs)
    r.base(s, 7, "Evaluation Setup: 单卡真实推理",
           "主对比使用 Mixtral-8×7B、A100 80 GB 和系统报告为旋转介质的 RAID 逻辑盘。\n"
           "六种策略在相同模型、相同名义缓存槽位和相同输入规模下各运行一次。")
    items = [
        ("模型与设备", "Mixtral-8×7B · 单张 A100 · FP16 权重"),
        ("输入与输出", "WikiText-2 测试集 · 8 条输入 · 每条生成 64 token"),
        ("缓存配置", "每层显存 4 个槽位 · CPU 内存 3 个槽位 · 其余冷存储"),
        ("对比方案", "流式读取 · 固定 CPU 缓存 · 独立缓存 · MECC · RF 适配版"),
    ]
    for i, (head, body) in enumerate(items):
        y = 2.34 + i * .83
        r.box(s, 1.03, y, 11.22, .65, r.LIGHT)
        r.box(s, 1.03, y, .07, .65, r.BLUE)
        r.t(s, 1.29, y + .14, 2.10, .34, head, 17, True, r.NAVY)
        r.t(s, 3.45, y + .14, 8.55, .34, body, 17, False, r.DARK)
    r.foot(s, "下列图只使用已提交的 A100 result.json；每个柱子对应一次完整运行。")


def conclusion(prs):
    s = slide(prs)
    r.base(s, 11, "Conclusion: 单卡缓存更新的实测收益",
           "在本次单卡 Mixtral-8×7B 测试中，MECC 的联合缓存更新减少了冷存储访问，\n"
           "解码延迟低于流式读取和固定 CPU 缓存；RF 适配版在同一主测试中略快。")
    items = [
        ("2.95×", "相对固定 CPU 缓存的 TPOT 比"),
        ("1.77×", "相对未优化流式读取的 TPOT 比"),
        ("12.5%", "MECC 的全阶段冷存储需求比例"),
    ]
    for i, (value, label) in enumerate(items):
        x = 1.03 + i * 4.08
        r.box(s, x, 2.58, 3.66, 2.37, r.LIGHT)
        r.box(s, x, 2.58, 3.66, .06, r.BLUE)
        r.t(s, x + .18, 3.02, 3.30, .65, value, 31, True, r.BLUE, PP_ALIGN.CENTER)
        r.t(s, x + .20, 3.88, 3.26, .66, label, 17, False, r.DARK, PP_ALIGN.CENTER)
    r.foot(s, "结果基于统一初始放置；逐层画像和跨任务切换仍需独立实验。")


def main():
    load()  # fail early if any source result or status is absent
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    r.intro(slide(prs))
    r.related_work(slide(prs))
    r.bridge(slide(prs))
    figure_page(prs, 4, "Motivation: 冷存储访问进入解码路径",
                "单卡运行时，所选专家若不在显存或 CPU 内存，就要从冷存储读取。\n"
                "相同模型与输入下，不同缓存策略的访问比例和每 token 延迟同时变化。",
                "main", "主对比：六种本地策略均使用一张 A100；右图为全阶段需求比例。")
    figure_page(prs, 5, "Insight: 联合更新两级缓存",
                "访问 CPU 内存中的专家后，MECC 将其提升至显存，并把显存中被替换的专家保留在 CPU 内存。\n"
                "同配置实验比较独立缓存、固定 CPU 缓存和联合更新。",
                "retention", "联合更新的 TPOT 为 7.38 秒/token；独立缓存为 32.94 秒/token。")
    r.overview(slide(prs))
    protocol(prs)
    r.method1(slide(prs))
    r.method2(slide(prs))
    figure_page(prs, 10, "Results: CPU 内存槽位的影响",
                "同一组 WikiText-2 输入下，将名义 CPU 预算从 30 GB 增至 60 GB，\n"
                "每层可缓存的专家从 2 个增至 4 个；五种策略的解码延迟与冷存储访问随之变化。",
                "budget", "30/60 GB 为同输入规模；20 GB 的输入来源不同，未并入这张图。")
    conclusion(prs)
    # Existing slide generators use their historical page numbers. Replace only
    # the visible page-number text on the slides we reuse.
    for idx, s in enumerate(prs.slides, start=1):
        for shape in s.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        run.text = r.display_text(run.text)
                if shape.text.strip() in {"10", "11", "12", "17"} and shape.left / Inches(1) > 12:
                    shape.text = str(idx)
        s.notes_slide.notes_text_frame.text = ""
    prs.core_properties.title = "MECC: A100 Measured Results"
    prs.core_properties.subject = "Internal group meeting; one completed run per point"
    prs.core_properties.author = ""
    OUT.parent.mkdir(exist_ok=True)
    prs.save(OUT)
    print("Saved", OUT, "slides", len(prs.slides))


if __name__ == "__main__":
    main()
