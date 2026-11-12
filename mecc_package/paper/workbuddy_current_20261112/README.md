# Current MECC manuscript for WorkBuddy

`paper.pdf` is the seven-page manuscript compiled from the 2026-11-12 online readback, including the H100 Mixtral-8×22B main comparison.
`source/main.tex` is its LaTeX entry point; compile from `source/` with XeLaTeX or
`latexmk -xelatex main.tex`. This directory contains the source and figures needed
to build the paper. WorkBuddy should read it for context and return experiment
results through the frozen A100 report workflow, leaving paper edits to the author.
