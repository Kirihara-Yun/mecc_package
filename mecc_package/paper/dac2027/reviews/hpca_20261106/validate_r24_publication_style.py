"""Validate retained arrays, derived increments, text placement and paper fit."""
import hashlib
import json
import math
import re
import stat
import pymupdf as fitz
from iterate import HERE,finish,audit

PREV=HERE/'r23_sensitivity_design'
OUT=HERE/'r24_publication_style'
CHANGED=['completion_figures/workload_sensitivity.pdf','completion_figures/quota_targets.pdf']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def spans(doc):
    return [s for p in doc for b in p.get_text('dict')['blocks'] if b['type']==0 for l in b['lines'] for s in l['spans']]

def main():
    assert not (OUT/'SEALED.json').exists()
    for rel,h in json.loads((PREV/'SEALED.json').read_text())['hashes'].items():assert sha(PREV/rel)==h,rel
    src=(OUT/'manuscript.tex').read_text(encoding='utf-8');old=(PREV/'manuscript.tex').read_text(encoding='utf-8')
    drop=lambda s:re.sub(r'\\captionof\{figure\}\{E7[^\n]*|\\caption\{E6[^\n]*','',s)
    assert drop(src)==drop(old)
    figs=re.findall(r'\\includegraphics\[[^]]*\]\{([^}]+)\}',src)
    assert len(figs)==16
    for rel in figs:
        if rel not in CHANGED:assert sha(OUT/rel)==sha(PREV/rel),rel
    for rel in ['narrative_targets.json','ideal_assumptions.json','EXPERIMENT_TARGETS.json','RATIO_AUDIT.json','references.bib']:
        assert sha(OUT/rel)==sha(PREV/rel),rel
    n=json.loads((OUT/'narrative_targets.json').read_text());a=json.loads((OUT/'ideal_assumptions.json').read_text())
    t=(OUT/'completion_figures/workload_sensitivity.tex').read_text()
    for i,(xs,b,m) in enumerate([(n['profile_samples'],n['profile_tpot_uniform'],n['profile_tpot_mecc']),
                                  (n['input_tokens'],n['input_ttft_streaming'],n['input_ttft_mecc']),
                                  (n['batch_sizes'],n['batch_throughput_streaming'],n['batch_throughput_mecc'])]):
        x0=[32,210,388][i]
        for x,vb,vm in zip(xs,b,m):
            px=x0+math.log(x/xs[0])/math.log(xs[-1]/xs[0])*123
            for v in [vb,vm]:
                py=103-(v-7)/6*80 if i==0 else 103-math.log10(v/10)/math.log10(400)*80 if i==1 else 103-v/.6*80
                assert f'({px:.3f},{py:.3f})' in t,(i,x,v)
    qt=(OUT/'completion_figures/quota_targets.tex').read_text()
    for x,b,m in zip(a['cpu_budget_gb'],a['budget_tpot_seconds']['Three-tier LRU'],a['budget_tpot_seconds']['MECC']):
        for v in [b,m]:assert f'({27+(x-16)/32*111:.3f},{83-v/30*60:.3f})' in qt,(x,v)
    mecc=a['budget_tpot_seconds']['MECC'];savings=[p-q for p,q in zip(mecc,mecc[1:])]
    assert savings==[4,2.5,1.5,1]
    for x,v in zip([192,208,224,240],savings):
        assert f'({x-4:.3f},{83-v/4.8*60:.3f})' in qt
    d=fitz.open(OUT/'manuscript.pdf');bodyfonts={s['font'] for s in spans(d)};fonts={};overlap=[]
    for rel in CHANGED:
        f=fitz.open(OUT/rel);ss=spans(f);fonts[rel]=sorted({s['font'] for s in ss})
        assert set(fonts[rel])<=bodyfonts
        assert all('Sans' not in s['font'] and 'DejaVu' not in s['font'] and s['size']<8.3 for s in ss)
        for i,s in enumerate(ss):
            r=fitz.Rect(s['bbox']);bounds=f[0].rect
            assert r.x0>=-.5 and r.y0>=-.5 and r.x1<=bounds.width+.5 and r.y1<=bounds.height+.5,(rel,s)
            for z in ss[i+1:]:
                inter=r&fitz.Rect(z['bbox'])
                if not inter.is_empty and inter.width>1 and inter.height>1:overlap.append([rel,s['text'],z['text'],tuple(inter)])
        assert any(tuple(round(c,2) for c in (v.get('fill') or ()))==(1.0,.95,.6) for v in f[0].get_drawings()),rel
        f[0].get_pixmap(matrix=fitz.Matrix(3,3)).save((OUT/rel).with_suffix('.png'));f.close()
    assert not overlap,overlap
    orphan=[]
    for i,p in enumerate(d):
        if i<6:
            for b in p.get_text('dict')['blocks']:
                if b['type']!=0:continue
                tail=b['lines'][-1];word=''.join(s['text'] for s in tail['spans']).strip()
                if re.fullmatch(r'[A-Za-z][A-Za-z-]*[.,;:]?',word) and any(s['font']=='TeXGyreTermesX-Regular' and 8.5<s['size']<9.3 for s in tail['spans']):orphan.append([i+1,word])
        assert max(b[3] for b in p.get_text('blocks'))<=723,i+1
        p.get_pixmap(matrix=fitz.Matrix(1.6,1.6)).save(OUT/f'page_{i+1}.png')
    d.close();assert not orphan,orphan
    layout=finish(OUT.name)
    assert (layout['pages'],layout['body_pages'],layout['reference_pages'],layout['appendix_pages'])==(8,6,[7],[8])
    assert layout['references']==45 and not layout['issues']
    assert all(v['references'][0]==v['page'] for v in layout['figures'].values())
    lang=audit(src);assert not lang['banned_tone'] and not lang['long_sentences']
    (OUT/'LANGUAGE_AUDIT.json').write_text(json.dumps(lang,indent=2)+'\n',encoding='utf-8')
    (OUT/'PUBLICATION_STYLE_VALIDATION.json').write_text(json.dumps({'source_arrays_unchanged':True,
        'all_chart_coordinates_checked':True,'marginal_savings':savings,'fourteen_other_figures_unchanged':True,
        'only_two_captions_changed':True,'font_families':fonts,'text_overlaps':overlap,'body_single_word_tails':orphan,
        'no_clipping':True,'yellow_titles_preserved':True,'layout':layout},indent=2)+'\n',encoding='utf-8')
    files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='SEALED.json' and p.suffix not in ['.aux','.log','.out','.fls','.fdb_latexmk','.blg']]
    (OUT/'SEALED.json').write_text(json.dumps({'revision':OUT.name,'date':'2026-11-08','hashes':{p.relative_to(OUT).as_posix():sha(p) for p in files}},indent=2)+'\n',encoding='utf-8')
    for p in files+[OUT/'SEALED.json']:p.chmod(stat.S_IREAD)
    print('PASS: chart coordinates and marginal gains; shared fonts; no text overlap/clipping; 14 other figures unchanged; 6+1+1 pages.')

if __name__=='__main__':main()
