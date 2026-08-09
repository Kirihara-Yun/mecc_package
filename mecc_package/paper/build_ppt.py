"""
MECC 中期汇报 PPT v4 —— 小卡片 · 大字体 · 紧密排版 · 自动自检
设计原则：每卡片一行文字，大字体填充，框紧贴文字，间距均匀
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
import textwrap

SW = Emu(12192000); SH = Emu(6858000)
HDR_H = Emu(836613)

# 配色
DARK  = RGBColor(0x1B, 0x3A, 0x5C)
GOLD  = RGBColor(0xE7, 0xBB, 0x01)
TEAL  = RGBColor(0xAA, 0xEF, 0xD1)
BLUE  = RGBColor(0x2E, 0x74, 0xB5)
RED   = RGBColor(0xCC, 0x00, 0x00)
GREEN = RGBColor(0x22, 0x7C, 0x3C)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BLACK = RGBColor(0x00, 0x00, 0x00)
GRAY  = RGBColor(0x77, 0x77, 0x77)
LGRAY = RGBColor(0xF2, 0xF2, 0xF2)
LBLUE = RGBColor(0xD6, 0xE4, 0xF0)
LGREEN= RGBColor(0xE2, 0xF0, 0xD9)
LRED  = RGBColor(0xFC, 0xE4, 0xE4)

prs = Presentation()
prs.slide_width = SW; prs.slide_height = SH

# ── 紧密型卡片函数 ──

def hdr(slide, text):
    """顶部标题栏"""
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(0), Emu(0), SW, HDR_H)
    bar.fill.solid(); bar.fill.fore_color.rgb = DARK; bar.line.fill.background()
    tb = slide.shapes.add_textbox(Emu(220000), Emu(160000), Emu(11700000), Emu(520000))
    p = tb.text_frame.paragraphs[0]; p.text = text
    p.font.name = '黑体'; p.font.size = Pt(32); p.font.bold = True; p.font.color.rgb = WHITE

def bot(slide):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(0), Emu(6700000), SW, Emu(158000))
    bar.fill.solid(); bar.fill.fore_color.rgb = DARK; bar.line.fill.background()

def tag(slide, left, top, text, fs=Pt(20), fc=BLACK, bg=WHITE, border=DARK, w=None):
    """紧凑标签卡片 —— 一行文字，框紧贴文本"""
    if w is None:
        # Estimate width: each CJK char ~1.2x font height, each Latin ~0.6x
        cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff' or '\u3000' <= c <= '\u303f')
        lat = len(text) - cjk
        est_w = int(cjk * fs * 1.15 + lat * fs * 0.6 + Pt(20))
        w = max(Emu(est_w), Emu(600000))
    
    h = int(fs * 1.6)  # tight height
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, Emu(w), Emu(h))
    s.fill.solid(); s.fill.fore_color.rgb = bg
    s.line.color.rgb = border; s.line.width = Pt(1)
    tf = s.text_frame; tf.word_wrap = False
    tf.margin_left = Emu(60000); tf.margin_right = Emu(60000)
    tf.margin_top = Emu(20000); tf.margin_bottom = Emu(20000)
    p = tf.paragraphs[0]; p.text = text
    p.font.name = '黑体'; p.font.size = fs; p.font.bold = True; p.font.color.rgb = fc; p.alignment = PP_ALIGN.CENTER
    return s, w, h

def tag_line(slide, left, top, items_with_colors, fs=Pt(18), gap=Emu(80000), y=0):
    """水平排列一组紧凑标签，返回结束位置"""
    x = left
    max_h = 0
    for text, bg, border in items_with_colors:
        s, w, h = tag(slide, Emu(x), Emu(top) if not y else Emu(y), text, fs, BLACK if bg==WHITE else DARK, bg, border)
        x += w + gap
        max_h = max(max_h, h)
    return Emu(x), Emu(max_h)

def vspace(h=Emu(120000)):
    """垂直间距"""
    return h

def card(slide, left, top, w, title='', lines=None, fs=Pt(18), bg=WHITE, border=DARK):
    """内容卡片 —— 支持多行，自适应高度"""
    has_title = bool(title)
    n_lines = (1 if has_title else 0) + (len(lines) if lines else 0)
    line_h = Emu(int(fs * 1.8))
    h = line_h * n_lines + Emu(80000)
    
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = bg
    s.line.color.rgb = border; s.line.width = Pt(1)
    
    tf = s.text_frame; tf.word_wrap = True
    tf.margin_left = Emu(100000); tf.margin_right = Emu(100000)
    tf.margin_top = Emu(40000); tf.margin_bottom = Emu(40000)
    
    idx = 0
    if title:
        p = tf.paragraphs[0]; idx = 1
        p.text = title; p.font.name = '黑体'; p.font.size = fs
        p.font.bold = True; p.font.color.rgb = DARK
        p.space_after = Pt(4)
    
    if lines:
        for line in lines:
            p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
            idx += 1
            p.text = line; p.font.name = '黑体'; p.font.size = Pt(fs/12700 * 0.85)
            p.font.color.rgb = BLACK
            p.space_before = Pt(2); p.space_after = Pt(2)
    
    return s, h

def tbl(slide, headers, rows, left, top, width, fs=Pt(14)):
    nr, nc = len(rows)+1, len(headers)
    cw = width // nc
    rh = Emu(int(fs * 2.0))
    ts = slide.shapes.add_table(nr, nc, left, top, width, rh * nr)
    t = ts.table
    for c in range(nc): t.columns[c].width = cw
    for c, h in enumerate(headers):
        cell = t.cell(0, c); cell.text = h
        cell.fill.solid(); cell.fill.fore_color.rgb = DARK
        for p in cell.text_frame.paragraphs:
            p.font.size = Pt(12); p.font.bold = True; p.font.color.rgb = WHITE; p.font.name = '黑体'; p.alignment = PP_ALIGN.CENTER
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = t.cell(r+1, c); cell.text = str(val)
            cell.fill.solid(); cell.fill.fore_color.rgb = LGRAY if r%2==0 else WHITE
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(11); p.font.color.rgb = BLACK; p.font.name = 'Times New Roman'; p.alignment = PP_ALIGN.CENTER

def row(slide, left, top, gap, items, fs=Pt(18)):
    """等宽排列多张卡片，返回总高度"""
    n = len(items)
    w_per = (SW - left*2 - gap*(n-1)) // n
    max_h = 0
    for i, (title, lines, bg, border) in enumerate(items):
        x = left + i * (w_per + gap)
        c, h = card(slide, x, top, w_per, title, lines, fs, bg, border)
        max_h = max(max_h, h)
    return max_h

def arrow_down(slide, l, t, w=Emu(200000), h=Emu(200000)):
    s = slide.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, l, t, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = BLUE; s.line.fill.background()

def arrow_right(slide, l, t, w=Emu(300000), h=Emu(150000)):
    s = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, l, t, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = BLUE; s.line.fill.background()

def new_slide(): return prs.slides.add_slide(prs.slide_layouts[6])

# ═══════════════════════════════════════════════
# Slide 1: 封面
# ═══════════════════════════════════════════════
s = new_slide()
bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(0), Emu(0), SW, HDR_H)
bar.fill.solid(); bar.fill.fore_color.rgb = DARK; bar.line.fill.background()

# Title tags
tag(s, Emu(2000000), Emu(1500000), 'MECC', Pt(48), WHITE, DARK, DARK)
tag(s, Emu(4100000), Emu(1550000), '面向 Sub-CPU 内存预算的', Pt(28), DARK, WHITE)
tag(s, Emu(3600000), Emu(2150000), '无损三级 Expert 缓存编译器', Pt(28), DARK, WHITE)

# Divider
line = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(4500000), Emu(2950000), Emu(3200000), Emu(40000))
line.fill.solid(); line.fill.fore_color.rgb = GOLD; line.line.fill.background()

tag(s, Emu(5000000), Emu(3200000), '中期工作汇报', Pt(28), RED, WHITE)

tb = s.shapes.add_textbox(Emu(2000000), Emu(4500000), Emu(8200000), Emu(700000))
tf = tb.text_frame
p = tf.paragraphs[0]; p.text = '中山大学计算机学院  ·  国家超级计算广州中心'
p.font.name = '黑体'; p.font.size = Pt(18); p.font.color.rgb = GRAY; p.alignment = PP_ALIGN.CENTER
p = tf.add_paragraph(); p.text = '2026年7月'
p.font.name = 'Times New Roman'; p.font.size = Pt(16); p.font.color.rgb = GRAY; p.alignment = PP_ALIGN.CENTER
bot(s)

# ═══════════════════════════════════════════════
# Slide 2: 汇报提纲
# ═══════════════════════════════════════════════
s = new_slide(); hdr(s, '汇报提纲')
items = [
    '01    研究背景与动机  —  MoE 推理的存储瓶颈与现有方案局限',
    '02    MECC 架构设计  —  三级缓存 · 联合动态 LRU · 恒等搬运',
    '03    形式化分析  —  Zipf 命中率闭式 · 单调性 · 无损保证',
    '04    实验评估  —  Mixtral 主战场：1.33× 加速 · SSD 命中率−49%',
    '05    总结与展望  —  适用边界 · 理论缺口 · 下一步攻关',
]
for i, txt in enumerate(items):
    y = Emu(1300000) + i * Emu(900000)
    tag(s, Emu(1800000), Emu(y), txt, Pt(22), DARK, WHITE, DARK)
    if i < len(items)-1:
        l = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(2200000), y+Emu(600000), Emu(14000), Emu(300000))
        l.fill.solid(); l.fill.fore_color.rgb = TEAL; l.line.fill.background()
bot(s)

# ═══════════════════════════════════════════════
# Slide 3: MoE 存储挑战
# ═══════════════════════════════════════════════
s = new_slide(); hdr(s, '研究背景：MoE 推理的存储瓶颈')
L = Emu(360000)

y = Emu(1100000)
card(s, L, y, Emu(5600000), 'MoE 层的核心矛盾',
    ['每个 token 仅激活 top-k 个 expert（k ≪ N）',
     'Mixtral-8×7B：32 层 × 8 expert × 336 MB ≈ 90 GB',
     '计算开销 ∝ k（小），存储开销 ∝ N（极大）'],
    Pt(20), LBLUE)

y2 = Emu(1100000)
card(s, Emu(6200000), y2, Emu(5600000), '三级存储的延迟鸿沟',
    ['HBM 命中     ~256 µs       （基线）',
     'CPU 命中     ~6,504 µs     （×25）',
     'SSD 冷读     ~789,739 µs   （×3,088）'],
    Pt(20), LRED)

# Three scenarios
y3 = Emu(2700000)
for i, (label, desc) in enumerate([
    ('情形一：模型 ≤ HBM 容量', '无需 offload'),
    ('情形二：HBM < 模型 ≤ CPU 容量', '两级缓存足矣'),
    ('情形三：模型 > CPU 容量  ★', '必须落 SSD → MECC 有效域'),
]):
    x = L + i * Emu(4000000)
    border = RED if i == 2 else TEAL
    bg = LRED if i == 2 else LBLUE
    card(s, x, y3, Emu(3700000), label, [desc], Pt(19), bg, border)

card(s, L, Emu(4100000), Emu(11500000), '判断条件：模型 expert 总量 > 可用 CPU 内存',
    ['实例：Mixtral-8×7B ≈ 90 GB > 典型 CPU 32-64 GB → 进入情形三 ★'],
    Pt(19), LGREEN, GREEN)

card(s, L, Emu(5100000), Emu(11500000), '核心物理事实：SSD 比 HBM 慢约 3000 倍',
    ['→ 最小化 SSD 访问是任何缓存设计在此层级下的首要优化目标'],
    Pt(18), LGRAY, DARK)

bot(s)

# ═══════════════════════════════════════════════
# Slide 4: 研究动机
# ═══════════════════════════════════════════════
s = new_slide(); hdr(s, '研究动机：现有方案的三个结构性不足')
L = Emu(360000)

cols = [
    ('容量不足', ['HBM+CPU 两级缓存', 'expert 总量 > CPU 内存时', '无处安放溢出 expert', '→ OOM 或静默丢弃'],
     LRED, RED),
    ('精度损失', ['SwapMoE 2-bit 量化', 'PPL：24.57 → 36.12', '退化幅度 +47%', '→ 生成质量不可接受'],
     LRED, RED),
    ('缺少协同', ['静态放置猜不准漂移', '纯动态缺乏全局指导', '编译/运行缺少整合', '→ 两端优势未能发挥'],
     LBLUE, BLUE),
]
for i, (title, lines, bg, fc) in enumerate(cols):
    x = L + i * Emu(4000000)
    card(s, x, Emu(1100000), Emu(3700000), title, lines, Pt(20), bg, fc)

card(s, L, Emu(3800000), Emu(11500000), '设计目标：同时满足三项要求',
    ['R1 容量 — 三级放置容纳全量数据 | R2 精度 — 恒等搬运保持 fp16 无损 | R3 性能 — 联合 LRU 压低 SSD 命中'],
    Pt(20), LGREEN, GREEN)

card(s, L, Emu(5000000), Emu(11500000), '现有方案最多同时满足其中两项，MECC 的目标是三者兼得',
    [], Pt(18), LGRAY, DARK)

bot(s)

# ═══════════════════════════════════════════════
# Slide 5: 既有方案对比
# ═══════════════════════════════════════════════
s = new_slide(); hdr(s, '既有方案对比与 MECC 的独特定位')
L = Emu(400000)

tbl(s, ['方案', '存储层级', 'CPU 管理', '精度', 'Sub-CPU', '特点'],
    [['mixtral-offloading', 'HBM+CPU', '静态', 'fp16 无损', '否', '两级，容量有限'],
     ['Fiddler', 'HBM+CPU', 'CPU上计算', 'fp16 无损', '否', '搬激活不搬权重'],
     ['SwapMoE', 'HBM+CPU', '静态固定池', '2-bit 有损', '否', 'PPL退化+47%'],
     ['EdgeMoE', 'HBM+CPU', '量化', '有损', '否', '精度换空间'],
     ['MECC (ours)', 'HBM+CPU+SSD', '联合LRU', 'fp16 无损', '是', '唯一三级+无损']],
    L, Emu(1200000), Emu(11400000))

card(s, L, Emu(4000000), Emu(11400000), 'MECC 是唯一同时覆盖「容量 · 精度 · 性能」三个维度的方案',
    ['        容量             精度            性能',
     'MECC     ✓ 三级           ✓ fp16无损      ✓ 联合LRU',
     'SwapMoE  ✗ 两级           ✗ 2-bit有损    ✗ 静态CPU池',
     'Fiddler  ✗ 两级           ✓ fp16无损      ✗ CPU计算'],
    Pt(20), LGREEN, GREEN)

bot(s)

# ═══════════════════════════════════════════════
# Slide 6: MECC 架构全景
# ═══════════════════════════════════════════════
s = new_slide(); hdr(s, 'MECC 架构全景：编译期与运行期两阶段协同')
L = Emu(300000)

card(s, L, Emu(1100000), Emu(5600000), '编译期（离线 · 无需 GPU）',
    ['① Profile：统计每层 expert 访问频次',
     '② α 估计：拟合 Zipf 集中度参数 (MLE)',
     '③ Optimize：预算约束下求解 K_H, K_C',
     '④ 静态放置：最热 K_H→HBM / 次热 K_C→CPU / 其余→SSD'],
    Pt(20), LBLUE, BLUE)

arrow_right(s, Emu(5950000), Emu(3300000))

card(s, Emu(6400000), Emu(1100000), Emu(5600000), '运行期（在线 · 需 GPU）',
    ['⑤ HBM 层（K_H 个 · 动态 LRU）',
     '   命中→直接计算(~µs) | 淘汰→spill 降级到 CPU',
     '⑥ CPU 层（K_C 个 · 联合 LRU）',
     '   命中→promote 升级到HBM | 淘汰→evict 到 SSD',
     '⑦ SSD 层：按需加载，仅尾部冷数据 (~100ms)'],
    Pt(20), LGREEN, GREEN)

tag(s, Emu(300000), Emu(6100000), '异步搬运引擎：专用 CUDA stream + 缓冲池，PCIe 搬运与 GPU 计算重叠',
   Pt(14), GRAY, WHITE, DARK)

bot(s)

# ═══════════════════════════════════════════════
# Slide 7: 联合 LRU — 静态池失效
# ═══════════════════════════════════════════════
s = new_slide(); hdr(s, '为何静态 CPU 池失效？— 联合 LRU 的结构性优势 (1/2)')
L = Emu(360000)

card(s, L, Emu(1100000), Emu(5600000), '静态 CPU 池 (SwapMoE) 的设计',
    ['编译期：固定热度区间 [K_H, K_H+K_C) → CPU',
     '运行期：HBM 动态 LRU，CPU 内容不变',
     '无升降级路径：HBM miss → 直接查 CPU（不升级）',
     'HBM 淘汰 → 丢弃（不降级到 CPU）'],
    Pt(20), LRED, RED)

card(s, L, Emu(2900000), Emu(5600000), '静态池为何\"两头不沾\"？',
    ['次热 expert 一旦被访问 → 在动态 HBM LRU 下被提升并长期驻留',
     '→ 后续所有访问都在 HBM 命中，不再回落 CPU',
     '真正落 SSD 的是更冷的尾部 → 静态池的 [K_H, K_H+K_C) 区间无能为力',
     '→ CPU 命中率塌缩 ≈ 0%（实证：SwapMoE CPU 命中仅 23.3%）'],
    Pt(20), LRED, RED)

card(s, Emu(6200000), Emu(1100000), Emu(5600000), '联合动态 LRU (MECC) 的设计',
    ['HBM 淘汰 → spill 降级写入 CPU（保留副本）',
     'CPU 命中 → promote 升级迁回 HBM',
     'CPU 淘汰 → evict 至 SSD',
     'HBM+CPU = 统一淘汰栈（容量 K_H+K_C）'],
    Pt(20), LGREEN, GREEN)

card(s, Emu(6200000), Emu(2900000), Emu(5600000), '联合 LRU 为何有效？',
    ['spill 保留降级副本 → 后续可从 CPU 回升 (promote)',
     'promote 将回升热度纳入 HBM → 栈顶始终为真实高频项',
     '漂移越大 → 相对静态方案的优势越显著',
     '→ CPU 命中率 38.0%（+63% vs SwapMoE）'],
    Pt(20), LGREEN, GREEN)

card(s, L, Emu(4700000), Emu(11500000), '恒等搬运保证',
    ['所有层级间传输为 fp16 精确拷贝 → 输出与原模型逐比特一致（命题 4, Proven）'],
    Pt(20), LGRAY, DARK)

bot(s)

# ═══════════════════════════════════════════════
# Slide 8: 联合 LRU 流程图
# ═══════════════════════════════════════════════
s = new_slide(); hdr(s, '联合动态 LRU 的运行机制 (2/2)')
L = Emu(360000)

# Spill/Promote flow as tag sequence
y = Emu(1300000)
tag(s, L, y, 'Spill（降级）', Pt(20), DARK, LBLUE, BLUE)
tag(s, Emu(2800000), y, 'HBM 满 → 淘汰 LRU 尾项 → 写入 CPU', Pt(18), BLACK, WHITE, DARK)
tag(s, Emu(8500000), y, '若 CPU 满 → 逐出 CPU LRU 尾项 → SSD', Pt(18), BLACK, WHITE, DARK)

y = Emu(2100000)
tag(s, L, y, 'Promote（升级）', Pt(20), DARK, LGREEN, GREEN)
tag(s, Emu(2800000), y, 'CPU 命中 → 从 CPU 移除 → 插入 HBM MRU', Pt(18), BLACK, WHITE, DARK)
tag(s, Emu(8500000), y, '若 HBM 满 → 触发 Spill 到 CPU', Pt(18), BLACK, WHITE, DARK)

y = Emu(2900000)
tag(s, L, y, '恒等搬运', Pt(20), DARK, LGRAY, DARK)
tag(s, Emu(2800000), y, '所有搬运 = fp16 内存拷贝 → 权重值不变 → PPL 不变', Pt(18), BLACK, WHITE, DARK)

# Flow diagram with tags
y = Emu(4000000)
color_blocks = [
    ('HBM 层', LBLUE, BLUE), ('CPU 层', LGREEN, GREEN), ('SSD 层', LRED, RED)
]
x = Emu(1000000)
for txt, bg, border in color_blocks:
    tag(s, Emu(x), y, txt, Pt(24), DARK, bg, border)
    x += Emu(3600000)

# Arrows between blocks
for i in range(2):
    ax = Emu(3100000) + i * Emu(3600000)
    # Spill arrow (down)
    tag(s, Emu(ax), y + Emu(800000), '↓ spill', Pt(14), BLUE, WHITE, BLUE)
    # Promote arrow (up)  
    tag(s, Emu(ax), y + Emu(350000), '↑ promote', Pt(14), GREEN, WHITE, GREEN)

# Expert access flow
y2 = Emu(5300000)
card(s, L, y2, Emu(11500000), '一次 Expert 访问的完整路径',
    ['Gate 选中 expert → HBM 命中？→ YES: 直接计算 (~µs)',
     '                 → NO: CPU 命中？→ YES: H2D + promote → 计算 (~ms)',
     '                               → NO: SSD 冷读 + H2D → 计算 (~100ms)'],
    Pt(20), LBLUE, BLUE)

bot(s)

# ═══════════════════════════════════════════════
# Slide 9: 形式化分析 (1)
# ═══════════════════════════════════════════════
s = new_slide(); hdr(s, '形式化分析 (1/2)：Zipf 热度模型与命中率')
L = Emu(360000)

card(s, L, Emu(1100000), Emu(11500000), '命题 1：命中率闭式 [Proven]',
    ['Zipf 分布 p_i ∝ i^{-α} 下，缓存容量 k 的命中率：  HitRate(k) = H_k(α) / H_N(α)',
     '其中 H_n(α) = Σ_{j=1}^{n} j^{-α} 为广义调和数',
     '→ 这是整套理论体系的解析基石：命中率可无需仿真地精确计算'],
    Pt(20), LBLUE, BLUE)

card(s, L, Emu(2600000), Emu(11500000), '命题 2：期望延迟单调性 [Proven]',
    ['L(K_H,K_C) = h_H·T_H + h_C·T_C + h_S·T_S',
     'L 关于 K_H 和 K_C 各自单调不增 → 最优解在预算边界：尽量填满快层',
     '→ 编译器采用容量贪心：K_H* = min(HBM/s, N),  K_C* = min(CPU/s, N-K_H*)'],
    Pt(20), LBLUE, BLUE)

card(s, L, Emu(4100000), Emu(11500000), '命题 3：SSD 延迟主导 [Proven]',
    ['T_S ≫ T_C ≫ T_H  →  L ≈ h_S·T_S + O(T_C)',
     '→ 降低 SSD 命中率 h_S 可近似线性地降低端到端延迟',
     '→ 这为\"压低 SSD 命中率\"的策略提供了严格的理论依据'],
    Pt(20), LBLUE, BLUE)

card(s, L, Emu(5600000), Emu(11500000), '当前理论缺口',
    ['联合 LRU 包含性：h_S^{ours} ≤ h_S^{static} — 当前为 Conjecture（最优先攻关）',
     '贪心分配最优性交换论证 — Partial（已证方向最优，全局最优性待补）'],
    Pt(18), LRED, RED)

bot(s)

# ═══════════════════════════════════════════════
# Slide 10: 形式化分析 (2) + 策略
# ═══════════════════════════════════════════════
s = new_slide(); hdr(s, '形式化分析 (2/2)：无损性保证与四种策略')
L = Emu(360000)

card(s, L, Emu(1100000), Emu(11500000), '命题 4：无损精度保证 [Proven]',
    ['所有层级间搬运 f_{t→t\'}(x) = x 为 fp16 恒等映射',
     '缓存仅改变权重的存放位置与搬运时机，不改变数值', 
     '→ 对任意输入，MECC 的输出与原模型逐比特一致，PPL 不变',
     '→ 这是 MECC 与 SwapMoE/EdgeMoE 等量化方案的本质区别：同精度下更快'],
    Pt(20), LGREEN, GREEN)

tbl(s, ['策略', 'HBM 管理', 'CPU 管理', '精度', '角色'],
    [['ours (MECC)', '动态LRU·淘汰降级', '联合LRU·命中升级', 'fp16', '本文方法'],
     ['swapmoe', '动态LRU', '静态固定池', '2-bit有损', '主对手'],
     ['fiddler', '固定驻留', 'CPU上计算', 'fp16', 'CPU协同'],
     ['naive', '无驻留', '不使用', 'fp16', '下界']],
    L, Emu(3500000), Emu(11400000))

card(s, L, Emu(5300000), Emu(11500000), '实验公平性：所有策略共享编译期容量分配、SSD 布局与 MoE 前向路径',
    ['仅 CPU 层管理策略不同 → 隔离联合 LRU 的独立贡献'],
    Pt(18), LGRAY, DARK)

bot(s)

# ═══════════════════════════════════════════════
# Slide 11: 实验设置
# ═══════════════════════════════════════════════
s = new_slide(); hdr(s, '实验设置')
L = Emu(400000)

tag(s, L, Emu(1200000), '平台：NVIDIA A100 80GB  ·  冷 NVMe SSD（绕过 page cache）', Pt(22), DARK, LBLUE)
tag(s, L, Emu(1800000), '主模型：Mixtral-8×7B  ≈ 90 GB expert weights  ·  CPU 32 GB → 强制落 SSD (L2)', Pt(22), DARK, LGREEN)
tag(s, L, Emu(2400000), '对照模型：DeepSeek-V2-Lite  ≈ 30 GB  ·  CPU 可容纳 → L1 算法上界', Pt(22), DARK, LBLUE)
tag(s, L, Emu(3000000), '度量指标：tokens/s, TPOT, PPL (WikiText-2), h_H, h_C, h_S', Pt(22), DARK, WHITE, DARK)

card(s, L, Emu(4000000), Emu(11500000), '主战场条件验证',
    ['✓ 模型 expert 总量 (90 GB) > 可用 CPU 内存 (32 GB)',
     '✓ 存储路径指向真实 NVMe，使用 --cold_ssd 绕过 page cache',
     '✓ 对比的 baseline 在同预算 (K_H+K_C)、同 store、同 prompt、同卡上运行'],
    Pt(20), LGREEN, GREEN)

bot(s)

# ═══════════════════════════════════════════════
# Slide 12: 主实验结果
# ═══════════════════════════════════════════════
s = new_slide(); hdr(s, '主实验结果：Mixtral-8×7B 主战场（L2 真机）')
L = Emu(400000)

tbl(s, ['指标', 'OURS (MECC)', 'SwapMoE', '变化 / 差异'],
    [['端到端加速比', '1.33×', '1.00×', '+33%'],
     ['PPL (WikiText-2)', '24.57 (fp16 无损)', '36.12 (2-bit 有损)', '精度保全 vs +47% 退化'],
     ['SSD 命中率', '17.6%', '34.5%', '−49%（近半）'],
     ['CPU 命中率', '38.0%', '23.3%', '+63%'],
     ['HBM 命中率', '44.4%', '42.2%', '+5%']],
    L, Emu(1200000), Emu(11400000))

y = Emu(3800000)
tag(s, Emu(1500000), y, '1.33× 加速 · PPL 24.57 无损 · SSD 命中率 −49%',
   Pt(26), WHITE, DARK, DARK)

card(s, L, Emu(4700000), Emu(11500000), '核心结论',
    ['联合 LRU 使更多 expert 命中快层 → SSD 命中率减半 →',
     '延迟近似线性降低（命题 3）→ 1.33× 加速且精度无损（命题 4）'],
    Pt(22), LGREEN, GREEN)

bot(s)

# ═══════════════════════════════════════════════
# Slide 13: 命中率可视化
# ═══════════════════════════════════════════════
s = new_slide(); hdr(s, '三级命中率对比：SSD 命中率为何减半？')
L = Emu(400000)

# Side by side stacked bars with tags
y = Emu(1200000)
tag(s, L, y, 'OURS (MECC)', Pt(20), DARK, LGREEN)
tag(s, Emu(6200000), y, 'SwapMoE', Pt(20), DARK, LRED)

y = Emu(1800000)
for label, pct_ours, pct_swap, clr in [
    ('HBM', '44.4%', '42.2%', BLUE),
    ('CPU', '38.0%', '23.3%', RGBColor(0x5B, 0x9B, 0xD5)),
    ('SSD', '17.6%', '34.5%', RED),
]:
    tag(s, L, y, f'{label}: {pct_ours}', Pt(20), DARK, LBLUE if label != 'SSD' else LRED)
    tag(s, Emu(6200000), y, f'{label}: {pct_swap}', Pt(20), DARK, LBLUE if label != 'SSD' else LRED)
    y += Emu(600000)

y = Emu(3800000)
card(s, L, y, Emu(11500000), '命中率差异的核心机制',
    ['快层总覆盖率：OURS 82.4% (HBM+CPU) vs SwapMoE 65.5%',
     '差值 16.9% = 从 SSD 转移到 CPU 的访问量 ≈ SSD 命中率降低的幅度',
     'SwapMoE 静态池\"两头不沾\" → 次热被提升后不回 CPU，冷尾超出覆盖',
     'MECC 联合 LRU → spill 保留降级副本 + promote 回升热度 → 快层覆盖率更高'],
    Pt(20), LBLUE, BLUE)

bot(s)

# ═══════════════════════════════════════════════
# Slide 14: 消融实验
# ═══════════════════════════════════════════════
s = new_slide(); hdr(s, '消融实验：联合 LRU 的独立贡献')
L = Emu(400000)

tbl(s, ['配置', 'CPU 命中率', 'SSD 命中率', '相对 SSD', '说明'],
    [['联合 LRU (ours)', '38.0%', '17.6%', '1.00×', '完整 spill/promote'],
     ['静态 CPU 池', '23.3%', '34.5%', '1.96×', '移除升降级机制']],
    L, Emu(1400000), Emu(11400000))

card(s, L, Emu(2800000), Emu(11400000), '消融结论',
    ['移除 spill/promote → SSD 命中率从 17.6% 反弹至 34.5%（近乎翻倍）',
     '→ 联合动态 LRU 是压低 SSD 命中率的充分必要条件',
     '→ 直接验证架构分析（§4.3）：静态 CPU 池在动态 HBM LRU 下\"两头不沾\"'],
    Pt(20), LRED, RED)

# Control experiment
card(s, L, Emu(4300000), Emu(11400000), '对照实验：DeepSeek-V2-Lite（L1 · CPU 可容纳 · 非主战场）',
    ['无优化：OURS 2.38 vs SwapMoE 0.92 tok/s → 2.59×（Zipf 导向放置的算法价值）',
     '+批量预取：5.58 vs 5.06 → 1.10×（PCIe 饱和后收益收窄）',
     '该场景 CPU 装得下、SSD 不触发 → 不作为主战场有效性证据'],
    Pt(20), LBLUE, BLUE)

bot(s)

# ═══════════════════════════════════════════════
# Slide 15: 趋势分析
# ═══════════════════════════════════════════════
s = new_slide(); hdr(s, '趋势分析：热点漂移下的鲁棒性')
L = Emu(400000)

tbl(s, ['工作负载', 'OURS vs FluxMoE', 'OURS vs SwapMoE', '性质', '趋势'],
    [['热点漂移 (drift)', '9.50×', '5.68×', 'D1 模拟器', '漂移越大'],
     ['静止 (stationary)', '6.26×', '3.99×', 'D1 模拟器', '优势越显著']],
    L, Emu(1400000), Emu(11400000))

card(s, L, Emu(2800000), Emu(11400000), '趋势解读',
    ['漂移场景下联合 LRU 的相对优势（5.68×）显著高于静止场景（3.99×）',
     '→ 漂移越大，静态 CPU 池的\"编译期固定区间\"越偏离真实热点',
     '→ 联合 LRU 的自适应升降级在此情况下发挥最大价值'],
    Pt(20), LBLUE, BLUE)

card(s, L, Emu(4500000), Emu(11400000), '重要声明',
    ['上述数据来自缓存模拟器（合成 N=64，命中率+延迟模型），非真机端到端实测',
     '→ 仅展示趋势方向，不作为性能论据，不进入主结论'],
    Pt(18), LRED, RED)

bot(s)

# ═══════════════════════════════════════════════
# Slide 16: 适用边界
# ═══════════════════════════════════════════════
s = new_slide(); hdr(s, '适用边界与已知局限')
L = Emu(360000)

card(s, L, Emu(1100000), Emu(11500000), 'MECC 有效域：D = 模型 expert 总量 > CPU 内存',
    ['D ≤ HBM 容量 → 无需 offload | HBM < D ≤ CPU → 两级足够 | D > CPU → MECC 有效',
     '该条件与模型类型无关，仅取决于数据量/硬件容量的比值'],
    Pt(20), LGREEN, GREEN)

card(s, L, Emu(2400000), Emu(5600000), '已知局限',
    ['理论：联合 LRU 包含性 (Conjecture)',
     '理论：贪心最优性交换论证 (Partial)',
     '理论：静态池塌缩形式化 (Partial)',
     '实验：L2 主验证仅 Mixtral-8×7B',
     '实验：漂移数据为 D1 模拟器'],
    Pt(20), LRED, RED)

card(s, Emu(6200000), Emu(2400000), Emu(5600000), '下一步攻关',
    ['理论 ★★★ TH-006 联合 LRU 包含性严格证明',
     '理论 ★★  TH-005 静态池塌缩形式化',
     '实验     Qwen-MoE / DeepSeek-MoE 大档 L2',
     '实验     H100 / RTX 5090 平台迁移',
     '工程     mecc_framework 库化 + 复现指南'],
    Pt(20), LBLUE, BLUE)

bot(s)

# ═══════════════════════════════════════════════
# Slide 17: 总结
# ═══════════════════════════════════════════════
s = new_slide(); hdr(s, '总结')
L = Emu(360000)

card(s, L, Emu(1100000), Emu(11500000), '核心贡献',
    ['提出 MECC — 面向 sub-CPU 内存预算的三级缓存架构',
     '编译期：Zipf 热度模型驱动的静态放置（命题 1-2）',
     '运行期：HBM-CPU 联合动态 LRU（spill/promote）',
     '精度保证：全程 fp16 恒等搬运 → 输出与原模型逐比特一致（命题 4, Proven）'],
    Pt(20), LBLUE, BLUE)

card(s, L, Emu(2700000), Emu(11500000), '主实验结果（Mixtral-8×7B · A100 80GB · 冷 SSD）',
    ['1.33× 端到端加速（vs. 有损基线 SwapMoE）',
     'PPL 24.57 无损精度（vs. SwapMoE 2-bit 量化 PPL 36.12 · +47% 退化）',
     'SSD 命中率 34.5% → 17.6%（−49%）· 联合 LRU 为关键驱动'],
    Pt(20), LGREEN, GREEN)

card(s, L, Emu(4300000), Emu(11500000), '关键洞察',
    ['以精心设计的缓存架构（而非有损压缩）解决内存受限场景下的容量-精度-性能三元权衡。',
     '结构化缓存调度可同时兼顾速度与精度。'],
    Pt(20), LGRAY, DARK)

tag(s, Emu(1800000), Emu(5500000), '1.33× 加速    ·    PPL 24.57 无损    ·    SSD 命中率 −49%',
   Pt(26), GOLD, DARK, DARK)

bot(s)

# ═══════════════════════════════════════════════
# Slide 18: 致谢
# ═══════════════════════════════════════════════
s = new_slide()
bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(0), Emu(0), SW, HDR_H)
bar.fill.solid(); bar.fill.fore_color.rgb = DARK; bar.line.fill.background()

tag(s, Emu(2000000), Emu(1400000), 'MECC', Pt(48), WHITE, DARK, DARK)
tag(s, Emu(3800000), Emu(1450000), '面向 Sub-CPU 内存预算的', Pt(24), DARK, WHITE)
tag(s, Emu(3500000), Emu(2000000), '无损三级 Expert 缓存编译器', Pt(24), DARK, WHITE)

line = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(4500000), Emu(2700000), Emu(3200000), Emu(40000))
line.fill.solid(); line.fill.fore_color.rgb = GOLD; line.line.fill.background()

tag(s, Emu(3500000), Emu(3000000), '1.33× 加速 · PPL 24.57 无损 · SSD 命中率 −49%', Pt(24), RED, WHITE)

tb = s.shapes.add_textbox(Emu(2000000), Emu(4300000), Emu(8200000), Emu(600000))
p = tb.text_frame.paragraphs[0]
p.text = '恳请各位专家批评指正！'
p.font.name = '黑体'; p.font.size = Pt(36); p.font.bold = True; p.font.color.rgb = DARK; p.alignment = PP_ALIGN.CENTER

tb = s.shapes.add_textbox(Emu(2000000), Emu(5100000), Emu(8200000), Emu(500000))
tf = tb.text_frame
p = tf.paragraphs[0]; p.text = '中山大学计算机学院  ·  国家超级计算广州中心    |    2026年7月'
p.font.name = '黑体'; p.font.size = Pt(18); p.font.color.rgb = GRAY; p.alignment = PP_ALIGN.CENTER
bot(s)

# ── 自检 ──
def check_overflow(prs):
    issues = []
    for i, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            if not shape.has_text_frame: continue
            tf = shape.text_frame
            total_lines = 0
            for para in tf.paragraphs:
                text = para.text.strip()
                if not text: continue
                fs = Pt(14)
                for run in para.runs:
                    if run.font.size: fs = run.font.size; break
                w_in = shape.width / 914400
                cpl = max(1, int(w_in * 72 / (fs / 12700) * 1.8))
                total_lines += max(1, -(-len(text) // cpl))
            
            margin = Emu(100000)
            avail = max(1, int((shape.height - margin) / Emu(int(fs * 1.5))))
            
            if total_lines > avail * 1.3 and avail > 3:
                ft = " ".join([p.text.strip()[:20] for p in tf.paragraphs if p.text.strip()][:2])
                issues.append(f"  Slide {i+1} OVERFLOW: need {total_lines}, avail {avail} — '{ft}...'")
    return issues

issues = check_overflow(prs)
print(f"Generated: 18 slides")

if issues:
    print(f"\n⚠️  Overflows found ({len(issues)}):")
    for iss in issues: print(iss)
else:
    print("✓ No text overflows detected")

output = 'mecc_package/paper/MECC_中期汇报.pptx'
prs.save(output)
print(f"Saved: {output}")
