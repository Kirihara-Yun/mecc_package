"""Validate exact normalization, waterfall arithmetic and unchanged subpanels."""
import hashlib
import json
import re
import stat
import pymupdf as fitz
from iterate import HERE,finish,audit

PREV=HERE/'r25_method_comparison'
OUT=HERE/'r26_input_waterfall'
CHANGED=['completion_figures/workload_sensitivity.pdf','completion_figures/quota_targets.pdf']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def spans(d):return [s for p in d for b in p.get_text('dict')['blocks'] if b['type']==0 for l in b['lines'] for s in l['spans']]
def crop(path,rect):
    d=fitz.open(path);p=d[0].get_pixmap(matrix=fitz.Matrix(3,3),clip=fitz.Rect(rect),alpha=False);return hashlib.sha256(p.samples).hexdigest()

def main():
    assert not (OUT/'SEALED.json').exists()
    for rel,h in json.loads((PREV/'SEALED.json').read_text())['hashes'].items():assert sha(PREV/rel)==h,rel
    src=(OUT/'manuscript.tex').read_text(encoding='utf-8');old=(PREV/'manuscript.tex').read_text(encoding='utf-8')
    drop=lambda s:re.sub(r'\\captionof\{figure\}\{E7[^\n]*|\\caption\{E6[^\n]*','',s)
    assert drop(src)==drop(old)
    figs=re.findall(r'\\includegraphics\[[^]]*\]\{([^}]+)\}',src);assert len(figs)==16
    for rel in figs:
        if rel not in CHANGED:assert sha(OUT/rel)==sha(PREV/rel),rel
    for rel in ['narrative_targets.json','ideal_assumptions.json','EXPERIMENT_TARGETS.json','SENSITIVITY_COMPARISON_TARGETS.json','RATIO_AUDIT.json','references.bib']:
        assert sha(OUT/rel)==sha(PREV/rel),rel
    d=json.loads((OUT/'SENSITIVITY_COMPARISON_TARGETS.json').read_text());a=json.loads((OUT/'INPUT_WATERFALL_AUDIT.json').read_text())
    tex=(OUT/'completion_figures/workload_sensitivity.tex').read_text();qtex=(OUT/'completion_figures/quota_targets.tex').read_text()
    for i,denom in enumerate(d['input']['series']['Reference']):
        for j,(name,values) in enumerate(d['input']['series'].items()):
            expected=values[i]/denom;assert a['normalized_ttft'][name][i]==expected
            assert f'({226+30*i+(j-1.5)*6.2-2.7:.3f},{103-expected/1.15*80:.3f})' in tex,(name,i)
    m=d['capacity']['series']['MECC'];assert len(a['waterfall_steps'])==4
    for i,step in enumerate(a['waterfall_steps'],1):
        assert (step['from_seconds'],step['to_seconds'],step['saved_seconds'])==(m[i-1],m[i],m[i-1]-m[i])
        assert f'({[185,200,215,230,245][i]-3.5:.3f},{91-m[i-1]/20*59:.3f})' in qtex
    assert a['waterfall_initial_seconds']-sum(s['saved_seconds'] for s in a['waterfall_steps'])==m[-1]
    crop_checks={}
    for name,rel,rect in [('13a',CHANGED[0],(0,20,173,148)),('13c',CHANGED[0],(355,20,522,148)),('14a',CHANGED[1],(0,0,154,132))]:
        h=crop(OUT/rel,rect);assert h==crop(PREV/rel,rect),name;crop_checks[name]=h
    paper=fitz.open(OUT/'manuscript.pdf');bodyfonts={s['font'] for s in spans(paper)};fonts={};overlaps=[]
    for rel in CHANGED:
        f=fitz.open(OUT/rel);ss=spans(f);fonts[rel]=sorted({s['font'] for s in ss});assert set(fonts[rel])<=bodyfonts
        assert all('DejaVu' not in s['font'] and s['size']<8.3 for s in ss)
        for i,s in enumerate(ss):
            r=fitz.Rect(s['bbox']);bounds=f[0].rect
            assert r.x0>=-.5 and r.y0>=-.5 and r.x1<=bounds.width+.5 and r.y1<=bounds.height+.5,(rel,s)
            for z in ss[i+1:]:
                inter=r&fitz.Rect(z['bbox'])
                if not inter.is_empty and inter.width>1 and inter.height>1:overlaps.append([rel,s['text'],z['text']])
        assert any(tuple(round(c,2) for c in (v.get('fill') or ()))==(1.0,.95,.6) for v in f[0].get_drawings()),rel
        f[0].get_pixmap(matrix=fitz.Matrix(3,3)).save((OUT/rel).with_suffix('.png'));f.close()
    assert not overlaps,overlaps
    orphan=[]
    for i,p in enumerate(paper):
        for b in p.get_text('dict')['blocks']:
            if b['type']!=0 or i>=6:continue
            tail=b['lines'][-1];w=''.join(s['text'] for s in tail['spans']).strip()
            if re.fullmatch(r'[A-Za-z][A-Za-z-]*[.,;:]?',w) and any(s['font']=='TeXGyreTermesX-Regular' and 8.5<s['size']<9.3 for s in tail['spans']):orphan.append([i+1,w])
        assert max(b[3] for b in p.get_text('blocks'))<=723,i+1
        p.get_pixmap(matrix=fitz.Matrix(1.6,1.6)).save(OUT/f'page_{i+1}.png')
    paper.close();assert not orphan,orphan
    layout=finish(OUT.name)
    assert (layout['pages'],layout['body_pages'],layout['reference_pages'],layout['appendix_pages'])==(8,6,[7],[8])
    assert layout['references']==45 and not layout['issues']
    assert all(v['references'][0]==v['page'] for v in layout['figures'].values())
    lang=audit(src);assert not lang['banned_tone'] and not lang['long_sentences']
    (OUT/'LANGUAGE_AUDIT.json').write_text(json.dumps(lang,indent=2)+'\n',encoding='utf-8')
    (OUT/'INPUT_WATERFALL_VALIDATION.json').write_text(json.dumps({'all_inherited_arrays_unchanged':True,
        'normalization_exact':True,'waterfall_sum_exact':True,'unchanged_subpanel_pixel_hashes':crop_checks,
        'fourteen_other_figures_unchanged':True,'only_two_captions_changed':True,'font_families':fonts,
        'text_overlaps':overlaps,'body_single_word_tails':orphan,'layout':layout},indent=2)+'\n',encoding='utf-8')
    files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='SEALED.json' and p.suffix not in ['.aux','.log','.out','.fls','.fdb_latexmk','.blg']]
    (OUT/'SEALED.json').write_text(json.dumps({'revision':OUT.name,'date':'2026-11-08','hashes':{p.relative_to(OUT).as_posix():sha(p) for p in files}},indent=2)+'\n',encoding='utf-8')
    for p in files+[OUT/'SEALED.json']:p.chmod(stat.S_IREAD)
    print('PASS: exact ratios and waterfall; 3 other subpanels pixel-identical; raw arrays retained; no overlap/clipping; 6+1+1 pages.')

if __name__=='__main__':main()
