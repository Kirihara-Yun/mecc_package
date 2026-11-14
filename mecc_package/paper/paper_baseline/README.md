# Current DAC manuscript source for Issue #2

This directory is an editable export of the Overleaf manuscript as read back on 2026-11-14. It is separate from the legacy `mecc_package/paper/mecc_paper.tex` draft.

- Entry point: `main.tex`
- Evaluation text (Figs. 8–12): `sections/06_evaluation.tex`
- Introduction: `sections/01_introduction.tex`
- Figure files: `figures/`
- Page layout: `layout/`

Compile locally with `latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build main.tex`. The validated manuscript has seven PDF pages: six pages of body text and one references page. This branch provides the source needed to work on [Issue #2](https://github.com/Kirihara-Yun/mecc_package/issues/2); edits here do not automatically update Overleaf.
