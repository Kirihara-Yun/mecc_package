"""Create review copies from a frozen baseline, never rewriting that baseline."""
from pathlib import Path
import hashlib,json,re,shutil,stat,difflib
import pymupdf

HERE=Path(__file__).resolve().parent
PAPER=HERE.parent.parent
BASE=HERE/'r00_frozen'
SOURCE='MECC_DAC_research_draft.tex'
BANNED=('however','indeed','notably','importantly','remarkably','highly','very',
        'extremely','significantly','novel','innovative','powerful','seamless',
        'robust','efficient','effective','superior','comprehensive','crucially',
        'substantially','obviously','dramatically','state-of-the-art')

def prose(source):
    source=source[source.index(r'\begin{abstract}'):source.index(r'\bibliographystyle')]
    source=re.sub(r'\\begin\{(figure\*?|table\*?|equation)\}.*?\\end\{\1\}','',source,flags=re.S)
    source=re.sub(r'\\captionof\{figure\}\{[^\n]+','',source)
    source=re.sub(r'\\(?:section|subsection|label|includegraphics|bibliography)[^\n]*','',source)
    source=re.sub(r'\\(?:cite|ref|eqref)\{[^}]*\}','',source)
    source=re.sub(r'\$[^$]*\$','',source)
    source=re.sub(r'\\[A-Za-z]+(?:\[[^]]*\])?','',source)
    source=re.sub(r'[{}~]',' ',source)
    return source

def audit(source):
    paragraphs=[re.sub(r'\s+',' ',p).strip() for p in re.split(r'\n\s*\n',prose(source))]
    sentences=[s.strip() for p in paragraphs for s in re.split(r'(?<=[.!?])\s+',p) if re.search(r'[A-Za-z]{3}',s)]
    rows=[{'words':len(re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*",s)),'text':s} for s in sentences]
    hits={w:len(re.findall(r'\b'+re.escape(w)+r'\b',prose(source),re.I)) for w in BANNED}
    return {'sentences':len(rows),'mean_words':round(sum(x['words'] for x in rows)/len(rows),2),
            'share_at_most_25':round(sum(x['words']<=25 for x in rows)/len(rows),3),
            'long_sentences':[x for x in rows if x['words']>30],
            'banned_tone':{w:n for w,n in hits.items() if n}}

def create(name,source,previous=None):
    out=HERE/name;out.mkdir(exist_ok=False)
    manifest=json.loads((BASE/'FREEZE_MANIFEST.json').read_text())
    for rel in manifest['hashes']:
        if rel.endswith('.pdf') and '/' not in rel:continue
        if rel==SOURCE or rel.endswith('.py') or rel.endswith('.bbl'):continue
        dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(BASE/rel,dst);dst.chmod(stat.S_IWRITE|stat.S_IREAD)
    (out/'manuscript.tex').write_text(source,encoding='utf-8')
    (out/'LANGUAGE_AUDIT.json').write_text(json.dumps(audit(source),indent=2)+'\n',encoding='utf-8')
    if previous:
        diff=''.join(difflib.unified_diff(previous.splitlines(True),source.splitlines(True),fromfile='previous',tofile=name))
        (out/'changes.diff').write_text(diff,encoding='utf-8')
    return out

def finish(name):
    out=HERE/name;doc=pymupdf.open(out/'manuscript.pdf')
    text='\n'.join(p.get_text() for p in doc)
    log=(out/'manuscript.log').read_text(errors='replace')
    issues=[l for l in log.splitlines() if any(w in l for w in ['Overfull','undefined','multiply defined','same identifier'])]
    aux=(out/'manuscript.aux').read_text(errors='replace')
    figs={}
    for key,num,page in re.findall(r'\\newlabel\{(fig:[^}]+)\}\{\{(\d+)\}\{(\d+)\}',aux):
        refs=[i+1 for i,p in enumerate(doc) if re.search(r'Figure\s+'+num+r'\b',p.get_text())]
        figs[key]={'number':int(num),'page':int(page),'references':refs}
    ref_pages=[i+1 for i,p in enumerate(doc) if p.get_text().lstrip().startswith('References')]
    appendix_pages=[i+1 for i,p in enumerate(doc) if p.get_text().lstrip().startswith('Appendix')]
    validation={'pages':len(doc),'body_pages':ref_pages[0]-1 if ref_pages else len(doc),
                'reference_pages':ref_pages,'appendix_pages':appendix_pages,'issues':issues,'figures':figs,
                'references':len(re.findall(r'\\bibitem\{',(out/'manuscript.bbl').read_text())),
                'no_banner':'ILLUSTRATIVE TARGET' not in text,
                'sha256':hashlib.sha256((out/'manuscript.pdf').read_bytes()).hexdigest()}
    (out/'VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n',encoding='utf-8')
    from PIL import Image,ImageDraw
    sheet=Image.new('RGB',(1264,832),'#EDF0F3');pen=ImageDraw.Draw(sheet)
    for i,page in enumerate(doc):
        pix=page.get_pixmap(matrix=pymupdf.Matrix(1,1),alpha=False)
        im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);im.thumbnail((306,396))
        x=(i%4)*316+5;y=(i//4)*416+17;sheet.paste(im,(x,y));pen.text((x,y-14),str(i+1),fill='#203244')
    sheet.save(out/'preview.png')
    doc.close()
    return validation

if __name__=='__main__':
    import sys
    if sys.argv[1]=='audit':print(json.dumps(audit((BASE/SOURCE).read_text()),indent=2))
    elif sys.argv[1]=='finish':print(json.dumps(finish(sys.argv[2]),indent=2))
