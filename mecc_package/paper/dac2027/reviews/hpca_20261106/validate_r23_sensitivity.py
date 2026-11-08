"""Validate typography, retained arrays, chart geometry and page fit."""
import hashlib
import json
import math
import re
import stat
import pymupdf as fitz
from iterate import HERE, finish, audit

PREV=HERE/'r22_recency_tracks'
OUT=HERE/'r23_sensitivity_design'
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
    geometry={
        'calibration':list(zip(n['profile_samples'],n['profile_tpot_uniform'],n['profile_tpot_mecc'])),
        'ttft':list(zip(n['input_tokens'],n['input_ttft_streaming'],n['input_ttft_mecc'])),
        'throughput':list(zip(n['batch_sizes'],n['batch_throughput_streaming'],n['batch_throughput_mecc'])),
        'capacity':list(zip(a['cpu_budget_gb'],a['budget_tpot_seconds']['Three-tier LRU'],a['budget_tpot_seconds']['MECC']))}
    st=(OUT/'completion_figures/workload_sensitivity.tex').read_text()
    qt=(OUT/'completion_figures/quota_targets.tex').read_text()
    for x,b,m in geometry['ttft']:
        px=216+math.log(x/32,4)/3*121
        for v in [b,m]:
            py=124-math.log10(v/10)/math.log10(400)*91
            assert f'({px:.3f},{py:.3f})' in st,(x,v)
    for _,b,m in geometry['capacity']:
        for v in [b,m]:assert f'{{{v:g}}}' in qt,v
    manuscript=fitz.open(OUT/'manuscript.pdf');bodyfonts={s['font'] for s in spans(manuscript)}
    fonts={}
    for rel in CHANGED:
        d=fitz.open(OUT/rel);ss=spans(d);fonts[rel]=sorted({s['font'] for s in ss})
        assert set(fonts[rel])<=bodyfonts
        assert all('Sans' not in s['font'] and 'DejaVu' not in s['font'] and s['size']<=8.3 for s in ss)
        for s in ss:
            x0,y0,x1,y1=s['bbox'];r=d[0].rect
            assert x0>=-.5 and y0>=-.5 and x1<=r.width+.5 and y1<=r.height+.5,(rel,s)
        # Highlighted titles remain separate from the source data arrays.
        assert any(tuple(round(c,2) for c in (draw.get('fill') or ()))==(1.0,.95,.6) for draw in d[0].get_drawings()),rel
        d[0].get_pixmap(matrix=fitz.Matrix(3,3)).save((OUT/rel).with_suffix('.png'));d.close()
    orphan=[]
    for i,p in enumerate(manuscript):
        if i<6:
            for b in p.get_text('dict')['blocks']:
                if b['type']!=0:continue
                tail=b['lines'][-1];w=''.join(s['text'] for s in tail['spans']).strip()
                if re.fullmatch(r'[A-Za-z][A-Za-z-]*[.,;:]?',w) and any(s['font']=='TeXGyreTermesX-Regular' and 8.5<s['size']<9.3 for s in tail['spans']):orphan.append([i+1,w])
        assert max(b[3] for b in p.get_text('blocks'))<=723,i+1
        p.get_pixmap(matrix=fitz.Matrix(1.6,1.6)).save(OUT/f'page_{i+1}.png')
    manuscript.close();assert not orphan,orphan
    layout=finish(OUT.name)
    assert (layout['pages'],layout['body_pages'],layout['reference_pages'],layout['appendix_pages'])==(8,6,[7],[8])
    assert not layout['issues'] and layout['references']==45
    assert all(v['references'][0]==v['page'] for v in layout['figures'].values())
    lang=audit(src);assert not lang['banned_tone'] and not lang['long_sentences']
    (OUT/'LANGUAGE_AUDIT.json').write_text(json.dumps(lang,indent=2)+'\n',encoding='utf-8')
    (OUT/'SENSITIVITY_DESIGN_VALIDATION.json').write_text(json.dumps({'data_geometry':geometry,'source_arrays_unchanged':True,
        'fourteen_other_figures_unchanged':True,'only_two_captions_changed':True,'font_families':fonts,
        'no_clipping':True,'yellow_titles_preserved':True,'body_single_word_tails':orphan,'layout':layout},indent=2)+'\n',encoding='utf-8')
    files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='SEALED.json' and p.suffix not in ['.aux','.log','.out','.fls','.fdb_latexmk','.blg']]
    (OUT/'SEALED.json').write_text(json.dumps({'revision':OUT.name,'date':'2026-11-08','hashes':{p.relative_to(OUT).as_posix():sha(p) for p in files}},indent=2)+'\n',encoding='utf-8')
    for p in files+[OUT/'SEALED.json']:p.chmod(stat.S_IREAD)
    print('PASS: chart values retained; matching fonts; no clipping; 14 other figures unchanged; 6+1+1 pages.')

if __name__=='__main__':main()
