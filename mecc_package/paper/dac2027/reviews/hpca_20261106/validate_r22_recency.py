"""Check the state geometry, manuscript fonts, retained assets and page layout."""
import hashlib
import json
import re
import stat
import pymupdf as fitz
from iterate import HERE, finish, audit

PREV=HERE/'r21_state_figure'
OUT=HERE/'r22_recency_tracks'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def families(doc):
    return {s['font'] for p in doc for b in p.get_text('dict')['blocks'] if b['type']==0
            for line in b['lines'] for s in line['spans']}

def main():
    assert not (OUT/'SEALED.json').exists()
    previous=json.loads((PREV/'SEALED.json').read_text())['hashes']
    for rel,h in previous.items():assert sha(PREV/rel)==h,rel
    src=(OUT/'manuscript.tex').read_text(encoding='utf-8')
    old=(PREV/'manuscript.tex').read_text(encoding='utf-8')
    remove_caption=lambda s:re.sub(r'\\caption\{Expert recency[^\n]*|\\caption\{A continuous request sequence[^\n]*','',s)
    assert remove_caption(src)==remove_caption(old)
    figs=re.findall(r'\\includegraphics\[[^]]*\]\{([^}]+)\}',src)
    unchanged=[p for p in figs if p!='method_redesign/residency_cases.pdf']
    assert len(unchanged)==15
    for rel in unchanged:assert sha(OUT/rel)==sha(PREV/rel),rel
    for rel in previous:
        if rel.endswith('.json') and rel not in ['VALIDATION.json']:
            assert sha(OUT/rel)==sha(PREV/rel),rel
    tracks=json.loads((OUT/'RECENCY_TRACK_AUDIT.json').read_text())
    xs=[44,106,168,230];ys=[31,51,79,99]
    states=tracks['continuous_states']
    rows=[s['hbm_mru_to_lru']+s['cpu_mru_to_lru'] for s in states]
    for i in range(3):
        for name in set(rows[i])&set(rows[i+1]):
            expected={'expert':name,'from':[xs[i],ys[rows[i].index(name)]],
                      'to':[xs[i+1],ys[rows[i+1].index(name)]],'dashed':False}
            assert expected in tracks['edges'],expected
    assert len(tracks['edges'])==13
    assert {'expert':'a4','from':[168,99],'to':[230,119],'dashed':True} in tracks['edges']
    assert {'expert':'a5','from':[181,119],'to':[230,31],'dashed':False} in tracks['edges']
    diagram=fitz.open(OUT/'method_redesign/residency_cases.pdf')
    manuscript=fitz.open(OUT/'manuscript.pdf')
    fonts=families(diagram)
    assert fonts<=families(manuscript),(fonts,families(manuscript))
    assert not any('Sans' in f or 'DejaVu' in f for f in fonts)
    for b in diagram[0].get_text('dict')['blocks']:
        if b['type']!=0:continue
        for line in b['lines']:
            for span in line['spans']:
                x0,y0,x1,y1=span['bbox']
                assert min(x0,y0)>=-.5 and x1<=252.5 and y1<=130.5,span
    diagram[0].get_pixmap(matrix=fitz.Matrix(3.8,3.8)).save(OUT/'method_redesign/residency_cases.png')
    diagram.close()
    orphans=[]
    for i,page in enumerate(manuscript):
        for b in page.get_text('dict')['blocks']:
            if b['type']!=0 or i>=6:continue
            tail=b['lines'][-1]
            word=''.join(s['text'] for s in tail['spans']).strip()
            if re.fullmatch(r'[A-Za-z][A-Za-z-]*[.,;:]?',word) and any(s['font']=='TeXGyreTermesX-Regular' and 8.5<s['size']<9.3 for s in tail['spans']):
                orphans.append([i+1,word])
        assert max(b[3] for b in page.get_text('blocks'))<=723,i+1
        page.get_pixmap(matrix=fitz.Matrix(1.6,1.6)).save(OUT/f'page_{i+1}.png')
    manuscript.close()
    assert not orphans,orphans
    layout=finish(OUT.name)
    assert (layout['pages'],layout['body_pages'],layout['reference_pages'],layout['appendix_pages'])==(8,6,[7],[8])
    assert layout['references']==45 and not layout['issues']
    assert all(v['references'][0]==v['page'] for v in layout['figures'].values())
    lang=audit(src)
    assert not lang['banned_tone'] and not lang['long_sentences']
    (OUT/'LANGUAGE_AUDIT.json').write_text(json.dumps(lang,indent=2)+'\n',encoding='utf-8')
    (OUT/'RECENCY_TRACK_VALIDATION.json').write_text(json.dumps({'continuous_state_edges_verified':True,
        'diagram_font_families':sorted(fonts),'same_font_families_as_manuscript':True,
        'fifteen_other_figures_unchanged':True,'existing_data_arrays_unchanged':True,
        'no_text_clipping':True,'body_single_word_tails':orphans,'layout':layout},indent=2)+'\n',encoding='utf-8')
    files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='SEALED.json' and p.suffix not in ['.aux','.log','.out','.fls','.fdb_latexmk','.blg']]
    (OUT/'SEALED.json').write_text(json.dumps({'revision':OUT.name,'date':'2026-11-08',
        'hashes':{p.relative_to(OUT).as_posix():sha(p) for p in files}},indent=2)+'\n',encoding='utf-8')
    for p in files+[OUT/'SEALED.json']:p.chmod(stat.S_IREAD)
    print('PASS: continuous tracks; matching manuscript fonts; no clipping; 15 other figures unchanged; 6+1+1 pages.')

if __name__=='__main__':main()
