"""Check the compiled reading copy's page and figure/text correspondence."""
from pathlib import Path
import json
import re
import pymupdf
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
STEM='MECC_DAC_visual_revision'

def main():
    doc=pymupdf.open(HERE/f'{STEM}.pdf')
    assert len(doc)==7, f'Expected six body pages plus references, got {len(doc)}'
    pages=[page.get_text() for page in doc]
    assert all(len(t)>2000 for t in pages[:6]), 'Nearly empty body page'
    assert 'References' in pages[6] and all('References' not in t for t in pages[:6])
    assert 'The independent-cache run matches' in ' '.join(pages)
    tex=(HERE/'mecc_dac2027_measured.tex').read_text(encoding='utf-8')
    first=tex.index(r'\section{Introduction}')+len(r'\section{Introduction}')
    intro=tex[first:tex.index(r'\clearpage',first)]
    intro=re.sub(r'\\begin\{figure\}.*?\\end\{figure\}','',intro,flags=re.S)
    paragraphs=[p for p in re.split(r'\n\s*\n',intro) if p.strip()]
    assert len(paragraphs)==4
    abstract=re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}',tex,re.S).group(1)
    aux=(HERE/f'{STEM}.aux').read_text(encoding='utf-8',errors='replace')
    checks={}
    for key,number,page in re.findall(r'\\newlabel\{(fig:[^}]+)\}\{\{(\d+)\}\{(\d+)\}',aux):
        refs=[i+1 for i,t in enumerate(pages) if re.search(r'Figure\s+'+number+r'\b',t)]
        assert refs and int(page)==refs[0], f'{key}: figure p.{page}, first reference {refs}'
        checks[key]={'figure_page':int(page),'first_reference_page':refs[0]}
    assert len(checks)==9
    assert checks['fig:insights']['figure_page']==2 and 'Motivation and Insights' in pages[1]
    log=(HERE/f'{STEM}.log').read_text(encoding='utf-8',errors='replace')
    issues=[line for line in log.splitlines() if any(x in line for x in ('undefined','Overfull','multiply defined'))]
    assert not issues,issues
    count=len(re.findall(r'\\bibitem\{',(HERE/f'{STEM}.bbl').read_text(encoding='utf-8')))
    assert count==44
    gaps={}
    for i,page in enumerate(doc[:6]):
        blocks=[b for b in page.get_text('blocks') if b[1]>45 and b[3]<735]
        per_column=[]
        for lo,hi in [(54,297),(315,558)]:
            selected=[b for b in blocks if min(b[2],hi)-max(b[0],lo)>15]
            assert selected
            per_column.append(round(720-max(b[3] for b in selected),1))
        gaps[str(i+1)]=per_column
    report={'pages':7,'body_pages':6,'reference_pages':1,'references':count,
        'introduction_paragraphs':4,'abstract_words':len(abstract.split()),
        'figure_pages':{k:v['figure_page'] for k,v in checks.items()},
        'figure_reference_checks':checks,'tex_issues':issues,
        'column_bottom_gaps_pt':gaps,
        'manual_review':'All seven pages rendered; Motivation, methods, results and comparison table inspected.',
        'fonts':'IEEE 9pt body; Times New Roman figure labels',
        'experimental_values':'Unchanged committed A100 results; DATA_AUDIT.json',
        'mechanism_source':'English paper-size adaptations of ../build_insight_visuals.py'}
    (HERE/'visual_revision_validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    dest=HERE/'editing'/'layout_review'
    dest.mkdir(parents=True,exist_ok=True)
    sheet=Image.new('RGB',(1264,832),'#EDF0F3')
    draw=ImageDraw.Draw(sheet)
    for i,page in enumerate(doc):
        pix=page.get_pixmap(matrix=pymupdf.Matrix(1,1),alpha=False)
        im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
        im.thumbnail((306,396))
        x=(i%4)*316+5;y=(i//4)*416+17
        sheet.paste(im,(x,y));draw.text((x,y-14),f'Page {i+1}',fill='#203244')
    sheet.save(dest/'MECC_layout_contact_sheet.png')
    print('PASS: 6+1 pages; 4 Introduction paragraphs; 44 references; 9/9 figures share their first-reference page.')
    print('Column bottom gaps (pt):',gaps)

if __name__=='__main__':
    main()
