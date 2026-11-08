"""Verify shrinking only, unchanged smaller text, and the first-page column fill."""
from collections import Counter
import difflib
import hashlib
import json
import re
import stat
import pymupdf as fitz
from iterate import HERE,finish,audit
from revise_r17_typography import BODY

PREV=HERE/'r16_contributions'
OUT=HERE/'r17_figure_type'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def spans(path):
    doc=fitz.open(path);width=doc[0].rect.width
    values=[s for b in doc[0].get_text('dict')['blocks'] if b['type']==0 for line in b['lines'] for s in line['spans']]
    doc.close();return width,values


def main():
    assert not (OUT/'SEALED.json').exists()
    old=(PREV/'manuscript.tex').read_text(encoding='utf-8');source=(OUT/'manuscript.tex').read_text(encoding='utf-8')
    for directory in HERE.glob('r[0-9][0-9]_*'):
        if not directory.is_dir() or directory in [OUT,HERE/'r00_frozen']:continue
        for rel,digest in json.loads((directory/'SEALED.json').read_text())['hashes'].items():assert sha(directory/rel)==digest,(directory.name,rel)
    for rel in ['references.bib','RATIO_AUDIT.json','EXPERIMENT_TARGETS.json','narrative_targets.json','ideal_assumptions.json','G1_EVIDENCE.json','PROTOCOLS.json']:
        assert sha(OUT/rel)==sha(PREV/rel),rel
    report=json.loads((OUT/'FIGURE_FONT_AUDIT.json').read_text());changed=[]
    for spec,rel in re.findall(r'\\includegraphics\[width=\\(columnwidth|textwidth)\]\{([^}]+)\}',source):
        row=report['figures'][rel];width=252 if spec=='columnwidth' else 522
        if not row['changed']:
            assert sha(OUT/rel)==sha(PREV/rel),rel
            continue
        changed.append(rel)
        ow,previous=spans(PREV/rel);nw,current=spans(OUT/rel)
        # Exact numerical labels are invariant despite the new PDF text insertion order.
        nums=lambda rows:Counter(v for s in rows for v in re.findall(r'\d+(?:\.\d+)?',s['text']))
        assert nums(previous)==nums(current),(rel,'numerical labels')
        smaller=Counter((s['text'],round(s['size']*width/ow,2)) for s in previous if s['size']*width/ow<=BODY+.15)
        present=Counter((s['text'],round(s['size']*width/nw,2)) for s in current)
        assert not (smaller-present),(rel,'smaller text changed',smaller-present)
        assert all(s['size']*width/nw<=BODY+.15 for s in current),rel
        assert all(c['new_pdf_pt']<c['old_pdf_pt'] for c in row['changes'])
    assert len(changed)==4 and sum(len(v.get('changes',[])) for v in report['figures'].values())==33
    layout=finish(OUT.name)
    assert (layout['pages'],layout['body_pages'],layout['reference_pages'],layout['appendix_pages'])==(8,6,[7],[8])
    assert not layout['issues'] and layout['references']==45
    assert all(v['references'][0]==v['page'] for v in layout['figures'].values())
    lang=audit(source);assert not lang['banned_tone'] and not lang['long_sentences']
    (OUT/'LANGUAGE_AUDIT.json').write_text(json.dumps(lang,indent=2)+'\n',encoding='utf-8')
    doc=fitz.open(OUT/'manuscript.pdf');ends=[]
    for i,page in enumerate(doc):
        for b in page.get_text('dict')['blocks']:
            if b['type']!=0 or i>=6:continue
            line=b['lines'][-1];tail=''.join(s['text'] for s in line['spans']).strip()
            if re.fullmatch(r'[A-Za-z][A-Za-z-]*[.,;:]?',tail):
                assert not any(s['font']=='TeXGyreTermesX-Regular' and 8.5<s['size']<9.3 for s in line['spans']),(i+1,tail)
        assert max(b[3] for b in page.get_text('blocks'))<=723,i+1
        page.get_pixmap(matrix=fitz.Matrix(1.6,1.6)).save(OUT/f'page_{i+1}.png')
        if i==0:
            ends=[max(b[3] for b in page.get_text('blocks') if b[0]>=lo and b[2]<=hi+3) for lo,hi in [(0,306),(306,612)]]
    assert abs(ends[0]-ends[1])<10,ends
    doc.close()
    (OUT/'changes.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),source.splitlines(True),fromfile=PREV.name,tofile=OUT.name)),encoding='utf-8')
    (OUT/'TYPOGRAPHY_VALIDATION.json').write_text(json.dumps({'only_oversized_text_shrunk':True,
        'smaller_figure_text_unchanged':True,'unchanged_figures':12,'changed_figures':changed,
        'data_and_prior_seals_unchanged':True,'page1_column_ends_pdf_pt':ends,'layout':layout},indent=2)+'\n',encoding='utf-8')
    files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='SEALED.json' and p.suffix not in ['.aux','.log','.out','.fls','.fdb_latexmk','.blg']]
    (OUT/'SEALED.json').write_text(json.dumps({'revision':OUT.name,'date':'2026-11-08',
        'hashes':{p.relative_to(OUT).as_posix():sha(p) for p in files}},indent=2)+'\n',encoding='utf-8')
    for p in files+[OUT/'SEALED.json']:p.chmod(stat.S_IREAD)
    print('PASS: 33 oversized labels shrunk; small labels unchanged; 12 figures byte-identical; first-page columns within one line; 6+1+1 pages.')


if __name__=='__main__':main()
