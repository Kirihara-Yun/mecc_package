"""Compose a vector PDF gallery from the manuscript's original PDF figures."""
from pathlib import Path
import pymupdf

P=Path(__file__).resolve().parent
FIGS=[
 ('01  Deployment challenges','ideal_figures/fig02_challenges.pdf',
  'Hypothetical: equal-capacity placement, cross-tier retention, and response to a working-set shift.'),
 ('02  MECC framework: offline compilation and online execution','figures/fig01_overview.pdf',
  'Schematic: residency plan, unchanged router, three memory tiers, and readiness-checked delivery.'),
 ('03  Promotion and retention, step by step','figures/fig03_retention.pdf',
  'Schematic: actual expert IDs show how HBM victims remain available in bounded CPU memory.'),
 ('04  Delivery dependencies after routing','figures/fig08_delivery.pdf',
  'Schematic: SSD read precedes H2D copy; a readiness event protects expert execution. Not to scale.'),
 ('05  Single-GPU latency and speedup over SSD-native adapter','ideal_figures/fig04_performance.pdf',
  'Hypothetical: TPOT and derived speedup. Local adapters are not published-system measurements.'),
 ('06  Cumulative component targets','ideal_figures/fig05_ablation.pdf',
  'Hypothetical: placement and retention reduce misses; overlap reduces waiting with misses unchanged.'),
 ('07  Host-memory cap, GPU allocation, and initialization','ideal_figures/fig06_budget_cost.pdf',
  'Hypothetical: vary one resource at a time and include initialization in the finite-horizon cost.'),
 ('08  Single-GPU MECC versus 2/4/8-GPU resident references','ideal_figures/fig07_gpu_tradeoff.pdf',
  'Hypothetical: compare GPU count, TPOT, and nominal GPU-seconds per token across every allocation.'),
]


def main():
    d=pymupdf.open()
    for title,path,note in FIGS:
        p=d.new_page(width=842,height=595)
        p.insert_text((40,45),title,fontsize=17,fontname='tiro',color=(.12,.17,.22))
        p.draw_line((40,62),(802,62),color=(.16,.39,.60),width=1)
        src=pymupdf.open(P/path)
        p.show_pdf_page(pymupdf.Rect(42,90,800,488),src,0)
        if note.startswith('Hypothetical'):
            p.draw_rect(pymupdf.Rect(40,510,802,552),color=None,fill=(1,.95,.60),overlay=True)
        p.insert_textbox(pymupdf.Rect(42,514,800,551),note,fontsize=11,fontname='tiro',color=(.16,.19,.22))
        p.draw_rect(pymupdf.Rect(40,563,705,580),color=None,fill=(1,.95,.60),overlay=True)
        p.insert_text((42,574),'DESIGN GALLERY | Numeric outcomes are hypothetical, not measurements.',fontsize=9,fontname='helv',color=(.58,.32,.10))
        src.close()
    d.set_metadata({'title':'MECC DAC 2027 Figure Gallery -- Hypothetical Results',
                    'author':'','subject':'Original vector schematics and explicitly hypothetical result figures'})
    d.save(P/'figure_gallery_polished.pdf',garbage=4,deflate=True)
    print('Saved',P/'figure_gallery_polished.pdf')


if __name__=='__main__': main()
