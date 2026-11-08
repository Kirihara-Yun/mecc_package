"""Check the single revised bar panel and retain all other visuals and data."""
import json,re,stat
import pymupdf as fitz
from iterate import HERE,finish,audit
from validate_r26_input_waterfall import sha,spans,crop

PREV=HERE/'r26_input_waterfall'
OUT=HERE/'r27_savings_bars'
REL='completion_figures/quota_targets.pdf'

def main():
    assert not (OUT/'SEALED.json').exists()
    for rel,h in json.loads((PREV/'SEALED.json').read_text())['hashes'].items():assert sha(PREV/rel)==h,rel
    src=(OUT/'manuscript.tex').read_text(encoding='utf-8');old=(PREV/'manuscript.tex').read_text(encoding='utf-8')
    drop=lambda s:re.sub(r'\\caption\{E6[^\n]*','',s)
    assert drop(src)==drop(old)
    figs=re.findall(r'\\includegraphics\[[^]]*\]\{([^}]+)\}',src);assert len(figs)==16
    for rel in figs:
        if rel!=REL:assert sha(OUT/rel)==sha(PREV/rel),rel
    for rel in ['narrative_targets.json','ideal_assumptions.json','SENSITIVITY_COMPARISON_TARGETS.json','EXPERIMENT_TARGETS.json','RATIO_AUDIT.json','references.bib']:
        assert sha(OUT/rel)==sha(PREV/rel),rel
    data=json.loads((OUT/'SENSITIVITY_COMPARISON_TARGETS.json').read_text());m=data['capacity']['series']['MECC']
    rows=json.loads((OUT/'SAVINGS_BAR_AUDIT.json').read_text())['bars']
    tex=(OUT/'completion_figures/quota_targets.tex').read_text()
    for i,b in enumerate(rows):
        value=m[i]-m[i+1]
        assert b['saved_seconds']==value and b['at_gib']==data['capacity']['x'][i+1]
        assert b['baseline_y']==91 and b['top_y']==91-value/5*59
        assert f"({b['x_center']-5.2:.3f},{b['top_y']:.3f}) rectangle ({b['x_center']+5.2:.3f},91)" in tex
    assert [b['saved_seconds'] for b in rows]==[4,2.5,1.5,1]
    left_hash=crop(OUT/REL,(0,0,154,132));assert left_hash==crop(PREV/REL,(0,0,154,132))
    paper=fitz.open(OUT/'manuscript.pdf');bodyfonts={s['font'] for s in spans(paper)}
    chart=fitz.open(OUT/REL);ss=spans(chart);fonts=sorted({s['font'] for s in ss});assert set(fonts)<=bodyfonts
    overlaps=[]
    for i,s in enumerate(ss):
        r=fitz.Rect(s['bbox']);bounds=chart[0].rect
        assert r.x0>=-.5 and r.y0>=-.5 and r.x1<=bounds.width+.5 and r.y1<=bounds.height+.5,s
        for z in ss[i+1:]:
            inter=r&fitz.Rect(z['bbox'])
            if not inter.is_empty and inter.width>1 and inter.height>1:overlaps.append([s['text'],z['text']])
    assert not overlaps,overlaps
    chart[0].get_pixmap(matrix=fitz.Matrix(3,3)).save((OUT/REL).with_suffix('.png'));chart.close()
    orphans=[]
    for i,p in enumerate(paper):
        if i<6:
            for b in p.get_text('dict')['blocks']:
                if b['type']!=0:continue
                tail=b['lines'][-1];w=''.join(s['text'] for s in tail['spans']).strip()
                if re.fullmatch(r'[A-Za-z][A-Za-z-]*[.,;:]?',w) and any(s['font']=='TeXGyreTermesX-Regular' and 8.5<s['size']<9.3 for s in tail['spans']):orphans.append([i+1,w])
        assert max(b[3] for b in p.get_text('blocks'))<=723,i+1
        p.get_pixmap(matrix=fitz.Matrix(1.6,1.6)).save(OUT/f'page_{i+1}.png')
    paper.close();assert not orphans,orphans
    layout=finish(OUT.name)
    assert (layout['pages'],layout['body_pages'],layout['reference_pages'],layout['appendix_pages'])==(8,6,[7],[8])
    assert layout['references']==45 and not layout['issues']
    assert all(v['references'][0]==v['page'] for v in layout['figures'].values())
    lang=audit(src);assert not lang['banned_tone'] and not lang['long_sentences']
    (OUT/'LANGUAGE_AUDIT.json').write_text(json.dumps(lang,indent=2)+'\n',encoding='utf-8')
    (OUT/'SAVINGS_BAR_VALIDATION.json').write_text(json.dumps({'values':[b['saved_seconds'] for b in rows],
        'zero_baseline':True,'all_arrays_unchanged':True,'fifteen_other_figures_unchanged':True,
        'left_panel_pixel_hash':left_hash,'only_fig14_caption_changed':True,'font_families':fonts,
        'text_overlaps':overlaps,'body_single_word_tails':orphans,'layout':layout},indent=2)+'\n',encoding='utf-8')
    files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='SEALED.json' and p.suffix not in ['.aux','.log','.out','.fls','.fdb_latexmk','.blg']]
    (OUT/'SEALED.json').write_text(json.dumps({'revision':OUT.name,'date':'2026-11-08','hashes':{p.relative_to(OUT).as_posix():sha(p) for p in files}},indent=2)+'\n',encoding='utf-8')
    for p in files+[OUT/'SEALED.json']:p.chmod(stat.S_IREAD)
    print('PASS: zero-baseline savings bars; original values retained; input figure and left panel unchanged; 6+1+1 pages.')

if __name__=='__main__':main()
