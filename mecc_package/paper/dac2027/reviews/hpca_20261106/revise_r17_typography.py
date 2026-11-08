"""Shrink oversized figure labels only; keep smaller type and all data unchanged."""
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import stat
import pymupdf as fitz
from iterate import HERE

PREV = HERE / 'r16_contributions'
OUT = HERE / 'r17_figure_type'
BODY = 9 * 72 / 72.27
FONT_DIR = Path('C:/Windows/Fonts')
FONT_FILES = {'R':'times.ttf','B':'timesbd.ttf','I':'timesi.ttf','BI':'timesbi.ttf'}
FONTS = {key:fitz.Font(fontfile=str(FONT_DIR/file)) for key,file in FONT_FILES.items()}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font_key(name):
    name=name.lower()
    return ('B' if 'bold' in name else '')+('I' if 'italic' in name or 'oblique' in name else '') or 'R'


def shrink(src,dst,width):
    original=fitz.open(src)
    scale=width/original[0].rect.width
    oversized=[span for block in original[0].get_text('dict')['blocks'] if block['type']==0
        for line in block['lines'] for span in line['spans'] if span['size']*scale>BODY+.15]
    before=[span['size']*scale for block in original[0].get_text('dict')['blocks'] if block['type']==0
        for line in block['lines'] for span in line['spans']]
    if not oversized:
        original.close()
        return {'changed':False,'source_sha256':sha(src),'source_font_sizes_pdf_pt':sorted(set(round(x,3) for x in before))}
    doc=fitz.open();page=doc.new_page(width=width,height=original[0].rect.height*scale)
    page.show_pdf_page(page.rect,original,0)
    changes=[]
    for block in page.get_text('dict')['blocks']:
        if block['type']!=0:continue
        for line in block['lines']:
            for span in line['spans']:
                if span['size']<=BODY+.15:continue
                changes.append({'span':span,'dir':line['dir']})
                box=fitz.Rect(span['bbox']);box.x0+=.12;box.x1-=.12;box.y0+=.12;box.y1-=.12
                page.add_redact_annot(box,fill=False,cross_out=False)
    page.apply_redactions(images=0,graphics=0,text=0)
    for key,file in FONT_FILES.items():page.insert_font(fontname='label'+key,fontfile=str(FONT_DIR/file))
    audit=[]
    right_aligned={'Streaming','Swap-style','Separate','MECC','Fiddler-style','MECC I/O'}
    for change in changes:
        span=change['span'];u=change['dir'];v=(-u[1],u[0]);box=fitz.Rect(span['bbox'])
        key=font_key(span['font']);font=FONTS[key]
        text=span['text'];length=font.text_length(text,fontsize=BODY)
        cx=(box.x0+box.x1)/2;cy=(box.y0+box.y1)/2
        middle_v=-(font.ascender+font.descender)*BODY/2
        base=fitz.Point(cx-u[0]*length/2-v[0]*middle_v,cy-u[1]*length/2-v[1]*middle_v)
        if text in right_aligned:base.x=box.x1-length
        if text.startswith(('(a)','(b)','Start:')):base.x=box.x0
        options={'fontname':'label'+key,'fontsize':BODY,'color':fitz.sRGB_to_pdf(span['color'])}
        angle=-math.degrees(math.atan2(u[1],u[0]))
        if abs(angle)>.01:options['morph']=(base,fitz.Matrix(angle))
        page.insert_text(base,text,**options)
        audit.append({'text':text,'old_pdf_pt':span['size'],'new_pdf_pt':BODY})
    doc.save(dst,garbage=4,deflate=True)
    page.get_pixmap(matrix=fitz.Matrix(2.2,2.2)).save(dst.with_suffix('.png'))
    doc.close();original.close()
    return {'changed':True,'source_sha256':sha(src),'source_font_sizes_pdf_pt':sorted(set(round(x,3) for x in before)),
        'only_oversized_spans_retypeset':True,'changes':audit}


def main():
    assert not OUT.exists()
    for rel,digest in json.loads((PREV/'SEALED.json').read_text())['hashes'].items():
        assert sha(PREV/rel)==digest,rel
        target=OUT/rel;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(PREV/rel,target);target.chmod(stat.S_IREAD|stat.S_IWRITE)
    source=(OUT/'manuscript.tex').read_text(encoding='utf-8')
    source=source.replace(r'\setlength{\itemsep}{3pt}\setlength{\topsep}{3pt}',
        r'\setlength{\itemsep}{9pt}\setlength{\topsep}{6pt}',1)
    source=source.replace('Runtime requests update membership within the compiled capacities.',
        "Serving requests update the profiled resident set within each layer's compiled capacity. "
        'The resulting cache state is reused across tokens and requests.',1)
    (OUT/'manuscript.tex').write_text(source,encoding='utf-8')
    report={}
    for spec,rel in re.findall(r'\\includegraphics\[width=\\(columnwidth|textwidth)\]\{([^}]+)\}',source):
        report[rel]=shrink(PREV/rel,OUT/rel,252 if spec=='columnwidth' else 522)
    (OUT/'FIGURE_FONT_AUDIT.json').write_text(json.dumps({'body_tex_pt':9,'body_pdf_pt':BODY,
        'rule':'shrink text larger than body; never enlarge smaller text','figures':report},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
