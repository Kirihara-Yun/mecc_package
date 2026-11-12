# MECC 论文协作包

本包由 2026-11-09 的七页阅读版整理。IEEE 双栏，正文 9 pt；按章节拆分，每句话单独一行，段落之间保留空行。

## 在 Overleaf 上使用

1. 新建项目，选择 **Upload project**，上传同名 ZIP。
2. 项目设置：**Main document = main.tex**，**Compiler = XeLaTeX**。
3. **TeX Live = 2024** 与本地验证环境一致；重新编译即可生成论文。
4. 通过项目的 Share 功能邀请共同作者，在同一个项目中编辑。

官方操作说明：<https://docs.overleaf.com/managing-projects-and-files/uploading-a-project>

## 文件结构与编辑位置

```text
main.tex                         全文入口与章节顺序
preamble.tex                     宏包、版式、标题、作者与自定义命令
sections/
  00_abstract.tex                 摘要与关键词
  01_introduction.tex             引言
  02_background.tex               背景
  03_motivation_insights.tex      动机与洞察
  04_overview.tex                 系统总览
  05_method.tex                   方法
  06_evaluation.tex               实验与分析
  07_conclusion.tex               结论
figures/                         全部 15 张正文配图，均为 PDF
layout/
  page02_motivation_figure.tex    第二页顶部跨栏图与图注
  page03_overview_figure.tex      第三页顶部框架图与图注
references.bib                   参考文献条目
IEEEtran.cls                     论文模板
IEEEtran.bst                     参考文献样式
latexmkrc                        编译配置
```

正文直接修改 `sections/` 对应文件；标题和作者修改 `preamble.tex`。
每个句子末尾换行，只有新段落才空一行。源码换行不等于 PDF 换行，请勿在句末添加 `\\`。
公式和表格保留 LaTeX 自身的分行方式。
两张跨栏图的位置沿用原稿，在 `main.tex` 中按页顶位置载入；图注在 `layout/`，其他图注随章节存放。
配图文件名前缀与正文图号一致，替换图片时保留文件名即可。若调整图顺序，以实际编译的图号为准。
引用沿用 `\cite{...}`、`\label{...}` 和 `\ref{...}`，避免手工填写编号。
所有图片都使用相对路径；编译无需 Python、外部绘图程序或原工作目录。

## 本地编译

在本包根目录执行：

```sh
latexmk -xelatex -synctex=1 -interaction=nonstopmode -halt-on-error main.tex
```

若未安装 latexmk，可按顺序运行 `xelatex main`、`bibtex main`、`xelatex main`、`xelatex main`。
本包不包含配置与数据说明文件。
