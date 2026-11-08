"""Check the exported talk and publish the validated current PPT/PDF copies."""
from pathlib import Path
from collections import Counter
from zipfile import ZipFile
import hashlib,json,re,shutil,unicodedata
import pymupdf as fitz
from pptx import Presentation
import numpy as np
from update_talk_from_r27 import HERE,PAPER,OUT,CURRENT,NAME,sha,OLD_INTRO,NEW_INTRO

def compact(s):return re.sub(r'\s+','',unicodedata.normalize('NFKC',s))
def visible_strings(sl):
    values=[]
    for sh in sl.shapes:
        if sh.has_text_frame:values.append(sh.text)
        if sh.has_table:values.extend(c.text for row in sh.table.rows for c in row.cells)
    return [v for v in values if v.strip()]

def main():
    ppt=OUT/(NAME+'.pptx');pdf=OUT/(NAME+'.pdf')
    z=ZipFile(ppt);assert not [n for n,c in Counter(z.namelist()).items() if c>1]
    prs=Presentation(ppt);original=Presentation(OUT/'baseline/MECC_HPCA_current.pptx');doc=fitz.open(pdf)
    assert len(prs.slides)==len(doc)==22
    body=json.loads((OUT/'PAPER_BODY_AUDIT.json').read_text());assert body['status']=='PASS'
    assert sha(PAPER/'manuscript.pdf')==body['paper_sha256']
    unchanged_images={}
    for i in range(12):
        expected_texts=visible_strings(original.slides[i])
        if i==0:expected_texts=[s.replace(OLD_INTRO,NEW_INTRO) for s in expected_texts]
        assert visible_strings(prs.slides[i])==expected_texts,i+1
        if i!=4:
            imgs=lambda sl:sorted(hashlib.sha256(sh.image.blob).hexdigest() for sh in sl.shapes if sh.shape_type==13)
            assert imgs(prs.slides[i])==imgs(original.slides[i]),i+1
            unchanged_images[str(i+1)]=True
    expected=['main.png','ablation.png','models.png','matched_wide.png','capacity.png','sensitivity.png','transfer.png','deployment.png']
    for n,img in enumerate(expected,13):
        sl=prs.slides[n-1];pics=[sh for sh in sl.shapes if sh.shape_type==13]
        assert len(pics)==1 and hashlib.sha256(pics[0].image.blob).hexdigest()==sha(OUT/'assets'/img),n
        assert sl.has_notes_slide and '数据身份' in sl.notes_slide.notes_text_frame.text,n
        for sh in sl.shapes:
            if not sh.has_text_frame or not sh.text.strip():continue
            # Text boxes in the exported new result pages must survive intact.
            assert compact(sh.text) in compact(doc[n-1].get_text()),(n,sh.text)
            for p in sh.text_frame.paragraphs:
                size=p.font.size
                if size:assert size.pt>=14,(n,sh.text,size.pt)
    out_of_slide=[];main_status=[];yellow_counts=[]
    status=re.compile(r'\b(?:authored|unmeasured|hypothetical|illustrative|AI-assisted)\b|理想数据|未实测|模拟数据',re.I)
    for i,(sl,page) in enumerate(zip(prs.slides,doc),1):
        for sh in sl.shapes:
            if sh.left<0 or sh.top<0 or sh.left+sh.width>prs.slide_width+5000 or sh.top+sh.height>prs.slide_height+5000:out_of_slide.append([i,sh.shape_id])
        if i<22:
            hits=status.findall(page.get_text())
            if hits:main_status.append([i,hits])
            pix=page.get_pixmap(matrix=fitz.Matrix(.6,.6),alpha=False)
            arr=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)
            count=int(((arr[:,:,0]>245)&(arr[:,:,1]>230)&(arr[:,:,2]<185)).sum())
            yellow_counts.append(count)
    assert not out_of_slide,out_of_slide
    assert not main_status,main_status
    assert not any(yellow_counts),yellow_counts
    assert '未实测' in doc[21].get_text() and '7.195' in doc[21].get_text()
    # The stronger completed RF observation remains present in the visible appendix.
    assert 'Flash-RF' in doc[21].get_text()
    manifest=json.loads((OUT/'UPDATE_MANIFEST.json').read_text())
    for name,a in manifest['assets'].items():
        if 'figure_text_unchanged' in a:assert a['figure_text_unchanged']
    validation={'status':'PASS','slides':22,'main_slides':21,'appendix_slide':22,
        'paper_front_seven_pages_data_explanation_matches':0,'paper_unchanged_sha256':sha(PAPER/'manuscript.pdf'),
        'main_slide_data_identity_text_matches':main_status,'main_slide_yellow_highlight_pixels':yellow_counts,
        'updated_results_pages':list(range(13,21)),'new_page_native_text_verified':True,
        'first_twelve_native_texts_retained_except_intro_wording':True,'intro_wording':NEW_INTRO,
        'first_twelve_image_assets_retained_except_retention':unchanged_images,
        'out_of_slide_shapes':out_of_slide,'notes_and_visible_appendix_retain_source_status':True,
        'complete_E1_RF_observation_retained_in_appendix':True,
        'pptx_sha256':sha(ppt),'pdf_sha256':sha(pdf)}
    doc.close()
    # Preserve the dated deliverables and update the familiar current entry points.
    try:
        # Check both destinations before replacing either file; preserve open user documents.
        for target in [CURRENT/'MECC_HPCA_current.pptx',CURRENT/'MECC_HPCA_current.pdf']:
            with target.open('r+b'):pass
        shutil.copy2(ppt,CURRENT/'MECC_HPCA_current.pptx')
        shutil.copy2(pdf,CURRENT/'MECC_HPCA_current.pdf')
        assert sha(CURRENT/'MECC_HPCA_current.pptx')==validation['pptx_sha256']
        assert sha(CURRENT/'MECC_HPCA_current.pdf')==validation['pdf_sha256']
        validation['publication']={'current_updated':True}
    except PermissionError:
        validation['publication']={'current_updated':False,'reason':'An existing current file is open; preserved without closing it.',
            'validated_pptx':str(ppt),'validated_pdf':str(pdf)}
    (OUT/'VALIDATION.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS: 22 exported slides; paper checked; no yellow highlights; figure text preserved; current updated:',validation['publication']['current_updated'])

if __name__=='__main__':main()
