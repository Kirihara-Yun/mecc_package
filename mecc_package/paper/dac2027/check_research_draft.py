"""Artifact checks for the yellow experiment-completion copy."""
from pathlib import Path
import hashlib
import json
import re
import argparse
import pymupdf
from PIL import Image,ImageDraw

HERE=Path(__file__).resolve().parent
STEM='MECC_DAC_research_draft'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--artifact-stem',default='MECC_DAC_title_highlight')
    artifact=parser.parse_args().artifact_stem
    source=(HERE/f'{STEM}.tex').read_text(encoding='utf-8')
    pdf=pymupdf.open(HERE/f'{artifact}.pdf')
    assert len(pdf)==7
    texts=[page.get_text() for page in pdf]
    assert 'References' in texts[6] and all('References' not in t for t in texts[:6])
    assert all(len(t)>2000 for t in texts[:6])
    abstract=re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}',source,re.S).group(1)
    intro=source[source.index(r'\section{Introduction}'):source.index(r'\twocolumn')]
    assert all(r'\item[('+str(i)+')]' in intro for i in (1,2,3))
    item_y=[pdf[0].search_for(f'({i})')[0].y0 for i in (1,2,3)]
    assert item_y[0]<item_y[1]<item_y[2]
    aux=(HERE/f'{artifact}.aux').read_text(errors='replace')
    figures={}
    for key,number,page in re.findall(r'\\newlabel\{(fig:[^}]+)\}\{\{(\d+)\}\{(\d+)\}',aux):
        refs=[i+1 for i,t in enumerate(texts) if re.search(r'Figure\s+'+number+r'\b',t)]
        assert refs and refs[0]==int(page),(key,page,refs)
        figures[key]={'number':int(number),'page':int(page),'first_reference_page':refs[0]}
    assert len(figures)==15
    assert not re.search(r'\\begin\{table\*?\}',source)
    assert not re.search(r'\bto measure\b', '\n'.join(texts), re.I)
    assert figures['fig:insights']['page']==2
    assert 'Motivation and Insights' in texts[1]
    assert texts[1].index('Layer group')<texts[1].index('Background')
    log=(HERE/f'{artifact}.log').read_text(errors='replace')
    issues=[x for x in log.splitlines() if any(y in x for y in ('Overfull','undefined','multiply defined','same identifier'))]
    assert not issues,issues
    refs=len(re.findall(r'\\bibitem\{',(HERE/f'{artifact}.bbl').read_text()))
    assert refs==44
    manifest=json.loads((HERE/'completion_figures/SOURCE_MANIFEST.json').read_text())
    expected_highlights={'motivation_evidence':2,'mechanism_sweeps':3,'cross_model':1,
                         'ablation_startup':2,'gpu_tradeoff':2,'quota_targets':1,
                         'traffic_exposure':2,'workload_sensitivity':3,'profile_mismatch':2}
    target_checks={}
    for name in manifest:
        if name.startswith('_'):continue
        plot=pymupdf.open(HERE/'completion_figures'/f'{name}.pdf')
        text=' '.join(page.get_text() for page in plot).upper()
        assert 'ILLUSTRATIVE TARGET' not in text,name
        yellow=[shape for page in plot for shape in page.get_drawings()
                if shape.get('fill') and max(abs(c-e) for c,e in zip(shape['fill'],(1,241/255,154/255)))<.015]
        assert len(yellow)==expected_highlights[name],(name,len(yellow))
        target_checks[name]={'highlighted_panel_titles':len(yellow),'source':manifest[name]}
    assert 'not measurements' in '\n'.join(texts)
    captions=re.findall(r'\\caption(?:of\{figure\})?\{([^\n]+)',source)
    assert not any(re.search(r'illustrative|ideal target|to measure',c,re.I) for c in captions)
    caption=pdf[0].search_for('Fig. 1.')[0]
    axis=pdf[0].search_for('Demand share (%)')[0]
    caption_gap=round(caption.y0-axis.y1,2)
    assert 0<caption_gap<10,caption_gap
    column_bottoms=[]
    for page_num,page in enumerate(pdf[:6],1):
        bottoms={}
        for name,xlo,xhi in [('left',0,306),('right',306,612)]:
            blocks=[b for b in page.get_text('blocks') if b[0]>=xlo and b[2]<=xhi+3]
            bottom=round(max(b[3] for b in blocks),2)
            assert 680<=bottom<=723,(page_num,name,bottom)
            bottoms[name]=bottom
        column_bottoms.append({'page':page_num,**bottoms})
    assert len(target_checks)==9
    assert manifest['_narrative_targets_sha256']==hashlib.sha256((HERE/'narrative_targets.json').read_bytes()).hexdigest()
    report={'artifact_file':f'{artifact}.pdf','pages':7,'body_pages':6,'references':refs,'figures':figures,'tables':0,
        'contributions':'three separate lines/items','abstract_words':len(abstract.split()),
        'intro_caption_gap_pt':caption_gap,'motivation_position':'top of page 2',
        'target_panels':target_checks,'pending_text_blocks':source.count(r'\pending{'),
        'tex_issues':issues,'data_status':'Yellow panel titles and numerical highlights; identity stated once in Evaluation.',
        'source_targets_sha256':manifest['_source_sha256'],
        'narrative_targets_sha256':manifest['_narrative_targets_sha256'],
        'column_bottoms_pt':column_bottoms,
        'pdf_sha256':hashlib.sha256((HERE/f'{artifact}.pdf').read_bytes()).hexdigest()}
    (HERE/'research_draft_validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    out=HERE/'editing/research_review';out.mkdir(exist_ok=True,parents=True)
    sheet=Image.new('RGB',(1264,832),'#EDF0F3');draw=ImageDraw.Draw(sheet)
    for i,page in enumerate(pdf):
        pix=page.get_pixmap(matrix=pymupdf.Matrix(1,1),alpha=False)
        im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);im.thumbnail((306,396))
        x=(i%4)*316+5;y=(i//4)*416+17
        sheet.paste(im,(x,y));draw.text((x,y-14),f'Page {i+1}',fill='#203244')
    sheet.save(out/'MECC_research_contact_sheet.png')
    print(f'PASS: 6+1 pages, 44 refs, 15/15 figures with first explanations, zero tables, all body columns filled, caption gap {caption_gap}pt, {sum(expected_highlights.values())} panel titles highlighted; no banner labels.')

if __name__=='__main__':main()
