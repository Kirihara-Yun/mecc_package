# R21：图 5 字体与对齐重绘

图 5 改用与正文相同的 newtxtext/newtxmath 字体排版。英文为 TeX Gyre Termes，专家符号使用 NewTX 数学字体，下标也按正文数学排版处理，移除原图的 DejaVu Sans 字形。

三行均按“请求、HBM 两个槽位、CPU 两个槽位”对齐。移除最右侧单独的 a4 方块，把“evict a4”放在第三行请求说明中。各行分别标明 HBM hit、CPU hit 和 HDD read。

初始状态和三个请求的状态不变，逐项读取 TRANSITION_AUDIT.json 的连续轨迹。移出的专家集合依次为空、空、a4，末态仍为 HBM [a5,a3]、CPU [a2,a1]。图注和正文不变。

图形仍为可缩放的矢量 PDF，绘图源为 method_redesign/residency_cases.tex。图的字体资源均能在论文正文页找到；图幅与上一版相同，不改变全篇八页结构。图 1 的三列及其余十四张图保持不变。
