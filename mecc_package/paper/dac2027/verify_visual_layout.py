"""Check active PDF layout/figure consistency, never research validity."""
from pathlib import Path
import json
import re
import pymupdf

P=Path(__file__).resolve().parent
FIGS=['figures/fig01_overview.pdf','figures/fig03_retention.pdf',
      'figures/fig08_delivery.pdf','ideal_figures/fig02_challenges.pdf',
      'ideal_figures/fig04_performance.pdf','ideal_figures/fig05_ablation.pdf',
      'ideal_figures/fig06_budget_cost.pdf']

def main():
    report=json.loads((P/'validation.json').read_text(encoding='utf-8'))
    d=pymupdf.open(P/report['pdf_file'])
    texts=[p.get_text() for p in d]
    overview=[i for i,t in enumerate(texts) if re.search(r'III\.\s*Overview',t,re.I)]
    framework=[i for i,t in enumerate(texts) if 'MECC framework.' in t]
    figures={}; all_text=''; all_fonts=set(); outside=[]
    for name in FIGS:
        f=pymupdf.open(P/name); t=f[0].get_text(); all_text+=t+'\n'
        fonts=sorted({x[3] for x in f[0].get_fonts()}); all_fonts.update(fonts)
        for b in f[0].get_text('dict')['blocks']:
            for line in b.get('lines',[]):
                for sp in line['spans']:
                    if not f[0].rect.contains(pymupdf.Rect(sp['bbox'])):
                        outside.append({'figure':name,'text':sp['text']})
        figures[name]={'fonts':fonts,'embedded_raster_images':len(f[0].get_images())}
    last=d[report['body_pages']-1]
    bottoms=[line['bbox'][3] for b in last.get_text('dict')['blocks']
      for line in b.get('lines',[])
      if 'HYPOTHETICAL RESULTS DESIGN DRAFT' not in ''.join(s['text'] for s in line['spans'])]
    checks={
      'author_placeholder_removed':'Anonymous Authors' not in texts[0],
      'overview_has_framework_on_same_page':len(overview)==1 and overview==framework,
      'all_active_figures_are_vector':all(x['embedded_raster_images']==0 for x in figures.values()),
      'figure_text_inside_pdf_bounds':not outside,
      'consistent_times_family':all(('TimesNewRoman' in x or 'STIX' in x) for x in all_fonts),
      'no_old_metric_aliases':not any(x in all_text for x in ['Decode time / token','Token latency','Task CPU budget']),
      'sixth_body_page_substantially_used':report['body_pages']==6 and max(bottoms)>680,
    }
    result={'scope':'Layout/terminology checks only; no accept or evidence certification',
      'checks':checks,'overview_page':[x+1 for x in overview],
      'sixth_body_page_last_text_y_pt':max(bottoms),'figure_details':figures,
      'outside_text':outside}
    (P/'visual_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    assert all(checks.values()),'Visual consistency checks failed'

if __name__=='__main__': main()
