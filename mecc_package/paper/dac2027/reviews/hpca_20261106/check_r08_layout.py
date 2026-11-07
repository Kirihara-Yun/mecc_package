"""Check the four reported defects against the rendered PDF, then seal it."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import stat
import pymupdf
from PIL import Image, ImageDraw
from iterate import HERE, BASE, audit, finish

OUT=HERE/'r08_layout'
PREVIOUS=HERE/'r07_proof'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def spans(page):
    return [s for b in page.get_text('dict')['blocks'] if b['type']==0
            for line in b['lines'] for s in line['spans']]


def main():
    assert not (OUT/'SEALED.json').exists(), 'Do not overwrite an archived revision'
    frozen=json.loads((BASE/'FREEZE_MANIFEST.json').read_text())
    for rel,digest in frozen['hashes'].items():assert sha(BASE/rel)==digest,rel
    for directory in sorted(HERE.glob('r0*_*')):
        if directory in [BASE,OUT]:continue
        record=json.loads((directory/'SEALED.json').read_text())
        for rel,digest in record['hashes'].items():assert sha(directory/rel)==digest,(directory.name,rel)
    source=(OUT/'manuscript.tex').read_text(encoding='utf-8')
    old=(PREVIOUS/'manuscript.tex').read_text(encoding='utf-8')
    assert source.split(r'\appendices',1)[1]==old.split(r'\appendices',1)[1]
    for rel in ['ideal_assumptions.json','narrative_targets.json','references.bib']:
        assert sha(OUT/rel)==sha(PREVIOUS/rel),rel
    citekeys=lambda s:set(k.strip() for g in re.findall(r'\\cite\{([^}]+)\}',s) for k in g.split(','))
    assert citekeys(source)==citekeys(old) and len(citekeys(source))==44
    changed_figures={'measured_figures/intro_evidence.pdf','completion_figures/workload_sensitivity.pdf'}
    for folder in ['measured_figures','completion_figures','method_redesign','figures']:
        for p in (PREVIOUS/folder).glob('*.pdf'):
            rel=p.relative_to(PREVIOUS).as_posix()
            if rel not in changed_figures:assert sha(OUT/rel)==sha(p),rel
    report=finish('r08_layout')
    assert (report['pages'],report['body_pages'],report['reference_pages'],report['appendix_pages'])==(8,6,[7],[8])
    assert report['references']==44 and len(report['figures'])==15 and not report['issues']
    assert all(f['references'][0]==f['page'] for f in report['figures'].values())
    doc=pymupdf.open(OUT/'manuscript.pdf')
    # Figure 1 is above every right-column body/caption line.
    page1=spans(doc[0])
    plot=[s for s in page1 if 'TimesNewRoman' in s['font'] and s['bbox'][0]>305]
    prose=[s for s in page1 if 'TeXGyreTermesX' in s['font'] and s['bbox'][0]>305 and s['size']<10]
    assert plot and prose
    assert max(s['bbox'][3] for s in plot)<min(s['bbox'][1] for s in prose)
    # Six subplot labels use the same font, size, weight, x grid, and row y.
    titles=[s for s in spans(doc[1]) if re.match(r'^\([a-f]\) ',s['text'])]
    titles.sort(key=lambda s:s['text'])
    assert len(titles)==6
    assert len({(s['font'],round(s['size'],3),s['flags']) for s in titles})==1
    assert all(abs(titles[i]['bbox'][0]-titles[i+3]['bbox'][0])<.1 for i in range(3))
    assert all(max(titles[i]['bbox'][1] for i in row)-min(titles[i]['bbox'][1] for i in row)<.1 for row in [(0,1,2),(3,4,5)])
    # Overview title belongs to the first body column, below Figure 3's caption.
    heading=[s for s in spans(doc[2]) if 'Overview' in s['text'] and 'TeXGyreTermesX' in s['font']]
    assert len(heading)==1 and heading[0]['bbox'][2]<306 and heading[0]['bbox'][1]>250
    header=source[source.index(r'\twocolumn[{',source.index(r'\section{Motivation')):source.index(r'\nobalance',source.index(r'\section{Motivation'))]
    assert r'\section{Overview}' not in header
    # Actual glyph bounds supplement compiler overflow diagnostics.
    columns=[]; single_words=[]
    for index,page in enumerate(doc):
        ends={}
        for label,lo,hi in [('left',0,306),('right',306,612)]:
            blocks=[b for b in page.get_text('blocks') if b[0]>=lo and b[2]<=hi+3]
            ends[label]=round(max(b[3] for b in blocks),2)
            assert ends[label]<=723,(index+1,label,ends[label])
        columns.append({'page':index+1,**ends})
        if index<6:
            for b in page.get_text('dict')['blocks']:
                if b['type']!=0:continue
                line=b['lines'][-1];text=''.join(s['text'] for s in line['spans']).strip()
                if re.fullmatch(r'[A-Za-z][A-Za-z\-]*[.,;:]?',text) and any(s['font']=='TeXGyreTermesX-Regular' and 8.5<s['size']<9.3 for s in line['spans']):
                    single_words.append({'page':index+1,'text':text,'bbox':line['bbox']})
    assert not single_words,single_words
    assert abs(columns[2]['left']-columns[2]['right'])<3,columns[2]
    assert all(min(row['left'],row['right'])>=675 for row in columns[:6]),columns
    assert abs(columns[5]['left']-columns[5]['right'])<3,columns[5]
    # No mid-sentence carryover above the mechanism explanation on page 5.
    page5body=[s for s in spans(doc[4]) if s['font']=='TeXGyreTermesX-Regular' and 8.5<s['size']<9.3 and s['bbox'][0]<306]
    assert min(page5body,key=lambda s:s['bbox'][1])['text'].startswith('Figure')
    language=audit(source)
    assert not language['banned_tone'] and not language['long_sentences']
    # Retain full-size page renders for manual inspection and a four-crop proof.
    for i,page in enumerate(doc[:7]):
        page.get_pixmap(matrix=pymupdf.Matrix(1.7,1.7)).save(OUT/f'page_{i+1}.png')
    boxes=[(0,(306,132,566,321),'1. Figure at column top'),
           (1,(48,44,564,286),'2. One subplot-title style'),
           (2,(48,224,304,314),'3. Overview title in body'),
           (2,(48,590,565,726),'4. Method column endings')]
    canvas=Image.new('RGB',(1500,1160),'#edf0f3');draw=ImageDraw.Draw(canvas)
    for n,(page,box,label) in enumerate(boxes):
        pix=doc[page].get_pixmap(matrix=pymupdf.Matrix(2.5,2.5),clip=pymupdf.Rect(box))
        im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
        im.thumbnail((730,520));x=(n%2)*750+10;y=(n//2)*580+35
        canvas.paste(im,(x,y));draw.text((x,y-22),label,fill='#203244')
    canvas.save(OUT/'LAYOUT_FIXES.png')
    doc.close()
    (OUT/'LANGUAGE_AUDIT.json').write_text(json.dumps(language,indent=2)+'\n',encoding='utf-8')
    (OUT/'changes.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),source.splitlines(True),fromfile='r07_proof',tofile='r08_layout')),encoding='utf-8')
    result={'artifact':report,'reported_defects':{'figure1_at_right_column_top':True,
        'figure2_six_title_styles_identical':True,'overview_heading_in_body':True,
        'method_column_bottom_difference_pt':round(abs(columns[2]['left']-columns[2]['right']),2)},
        'single_word_paragraph_tails':single_words,'column_bottoms_pt':columns,
        'figure2_title_styles':[{'text':s['text'],'font':s['font'],'size':s['size']} for s in titles],
        'frozen_versions_preserved':True,'appendix_unchanged':True,'data_arrays_unchanged':True,
        'citation_keys_unchanged':True,'manual_page_inspection':'pages 1–7 at 170%; LAYOUT_REVIEW.md',
        'scope':'Typography and plot geometry. No new measurements or performance claims.'}
    (OUT/'LAYOUT_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    paths=[p for p in OUT.rglob('*') if p.is_file() and p.name!='SEALED.json' and p.suffix not in ['.aux','.log','.out','.fls','.fdb_latexmk','.blg']]
    hashes={p.relative_to(OUT).as_posix():sha(p) for p in paths}
    (OUT/'SEALED.json').write_text(json.dumps({'revision':'r08_layout','date':'2026-11-07','hashes':hashes},indent=2)+'\n',encoding='utf-8')
    for p in paths+[OUT/'SEALED.json']:p.chmod(stat.S_IREAD)
    print('PASS: four reported layout defects, paragraph tails, 15 same-page explanations, 6+1+1 pages, unchanged arrays and 44 citations.')


if __name__=='__main__':main()
