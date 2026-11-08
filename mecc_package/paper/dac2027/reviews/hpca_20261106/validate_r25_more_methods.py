"""Check four-series coordinates, inherited arrays, planning labels and layout."""
import hashlib
import json
import math
import re
import stat
import pymupdf as fitz
from iterate import HERE,finish,audit

PREV=HERE/'r24_publication_style'
OUT=HERE/'r25_method_comparison'
CHANGED=['completion_figures/workload_sensitivity.pdf','completion_figures/quota_targets.pdf']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def spans(d):return [s for p in d for b in p.get_text('dict')['blocks'] if b['type']==0 for l in b['lines'] for s in l['spans']]

def main():
    assert not (OUT/'SEALED.json').exists()
    for rel,h in json.loads((PREV/'SEALED.json').read_text())['hashes'].items():assert sha(PREV/rel)==h,rel
    src=(OUT/'manuscript.tex').read_text(encoding='utf-8');old=(PREV/'manuscript.tex').read_text(encoding='utf-8')
    drop=lambda s:re.sub(r'\\captionof\{figure\}\{E7[^\n]*|\\caption\{E6[^\n]*|E6--E10 inherit[^\n]*','',s)
    assert drop(src)==drop(old)
    figs=re.findall(r'\\includegraphics\[[^]]*\]\{([^}]+)\}',src);assert len(figs)==16
    for rel in figs:
        if rel not in CHANGED:assert sha(OUT/rel)==sha(PREV/rel),rel
    for rel in ['narrative_targets.json','ideal_assumptions.json','EXPERIMENT_TARGETS.json','RATIO_AUDIT.json','references.bib']:
        assert sha(OUT/rel)==sha(PREV/rel),rel
    d=json.loads((OUT/'SENSITIVITY_COMPARISON_TARGETS.json').read_text());n=json.loads((OUT/'narrative_targets.json').read_text());a=json.loads((OUT/'ideal_assumptions.json').read_text())
    assert 'NOT BENCHMARK EXECUTIONS' in d['status']
    assert 'The added sweeps are not executions.' in src
    for k,prefix,oldref in [('profile','profile_tpot','uniform'),('input','input_ttft','streaming'),('batch','batch_throughput','streaming')]:
        assert d[k]['series']['MECC']==n[prefix+'_mecc']
        assert d[k]['series']['Reference']==n[prefix+'_'+oldref]
    for key in ['MECC','Three-tier LRU']:assert d['capacity']['series'][key]==a['budget_tpot_seconds'][key]
    for name in ['Fixed CPU','Three-tier LRU','MECC']:
        assert d['capacity']['series'][name][3]==d['profile']['series'][name][-1]
        assert abs(d['batch']['series'][name][0]-1/d['capacity']['series'][name][3])<1e-6
    assert d['capacity']['series']['Streaming'][3]==24
    text=(OUT/'completion_figures/workload_sensitivity.tex').read_text()
    checked=0
    for i,key in enumerate(['profile','input','batch']):
        data=d[key];xs=data['x'];x0=[32,210,388][i]
        assert len(data['series'])==4
        for name,ys in data['series'].items():
            for x,v in zip(xs,ys):
                px=x0+math.log(x/xs[0])/math.log(xs[-1]/xs[0])*123
                py=103-(v-7)/11*80 if i==0 else 103-math.log10(v/10)/math.log10(400)*80 if i==1 else 103-v/.6*80
                assert f'({px:.3f},{py:.3f})' in text,(key,name,x,v)
                checked+=1
    qt=(OUT/'completion_figures/quota_targets.tex').read_text();assert len(d['capacity']['series'])==4
    for name,ys in d['capacity']['series'].items():
        for x,v in zip(d['capacity']['x'],ys):
            assert f'({27+(x-16)/32*111:.3f},{91-v/32*59:.3f})' in qt,(name,x,v)
            checked+=1
    m=d['capacity']['series']['MECC'];savings=[p-q for p,q in zip(m,m[1:])];assert savings==[4,2.5,1.5,1]
    pdf=fitz.open(OUT/'manuscript.pdf');bodyfonts={s['font'] for s in spans(pdf)};fonts={};overlap=[]
    for rel in CHANGED:
        f=fitz.open(OUT/rel);ss=spans(f);fonts[rel]=sorted({s['font'] for s in ss});assert set(fonts[rel])<=bodyfonts
        assert all('DejaVu' not in s['font'] and s['size']<8.3 for s in ss)
        for i,s in enumerate(ss):
            r=fitz.Rect(s['bbox']);bounds=f[0].rect
            assert r.x0>=-.5 and r.y0>=-.5 and r.x1<=bounds.width+.5 and r.y1<=bounds.height+.5,(rel,s)
            for z in ss[i+1:]:
                inter=r&fitz.Rect(z['bbox'])
                if not inter.is_empty and inter.width>1 and inter.height>1:overlap.append([rel,s['text'],z['text']])
        assert any(tuple(round(c,2) for c in (v.get('fill') or ()))==(1.0,.95,.6) for v in f[0].get_drawings()),rel
        f[0].get_pixmap(matrix=fitz.Matrix(3,3)).save((OUT/rel).with_suffix('.png'));f.close()
    assert not overlap,overlap
    orphans=[]
    for i,p in enumerate(pdf):
        for b in p.get_text('dict')['blocks']:
            if b['type']!=0 or i>=6:continue
            tail=b['lines'][-1];word=''.join(s['text'] for s in tail['spans']).strip()
            if re.fullmatch(r'[A-Za-z][A-Za-z-]*[.,;:]?',word) and any(s['font']=='TeXGyreTermesX-Regular' and 8.5<s['size']<9.3 for s in tail['spans']):orphans.append([i+1,word])
        assert max(b[3] for b in p.get_text('blocks'))<=723,i+1
        p.get_pixmap(matrix=fitz.Matrix(1.6,1.6)).save(OUT/f'page_{i+1}.png')
    pdf.close();assert not orphans,orphans
    layout=finish(OUT.name)
    assert (layout['pages'],layout['body_pages'],layout['reference_pages'],layout['appendix_pages'])==(8,6,[7],[8])
    assert layout['references']==45 and not layout['issues']
    assert all(v['references'][0]==v['page'] for v in layout['figures'].values())
    lang=audit(src);assert not lang['banned_tone'] and not lang['long_sentences']
    (OUT/'LANGUAGE_AUDIT.json').write_text(json.dumps(lang,indent=2)+'\n',encoding='utf-8')
    (OUT/'MULTIMETHOD_VALIDATION.json').write_text(json.dumps({'checked_coordinates':checked,'four_methods_per_sweep':True,
        'all_inherited_arrays_unchanged':True,'new_series_explicitly_authored_not_measurements':True,'appendix_disclosure':True,
        'default_setting_anchors_consistent':True,'fourteen_other_figures_unchanged':True,'marginal_savings':savings,
        'font_families':fonts,'text_overlaps':overlap,'body_single_word_tails':orphans,'layout':layout},indent=2)+'\n',encoding='utf-8')
    files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='SEALED.json' and p.suffix not in ['.aux','.log','.out','.fls','.fdb_latexmk','.blg']]
    (OUT/'SEALED.json').write_text(json.dumps({'revision':OUT.name,'date':'2026-11-08','hashes':{p.relative_to(OUT).as_posix():sha(p) for p in files}},indent=2)+'\n',encoding='utf-8')
    for p in files+[OUT/'SEALED.json']:p.chmod(stat.S_IREAD)
    print('PASS: 4 methods; 68 coordinates; inherited arrays retained; explicit target provenance; default anchors; 6+1+1 pages.')

if __name__=='__main__':main()
