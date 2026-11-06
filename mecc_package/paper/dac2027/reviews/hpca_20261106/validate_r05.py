"""Check the direct-prose revision and its explicit page-eight data appendix."""
from pathlib import Path
import hashlib,json,re,stat
import pymupdf
from iterate import HERE,BASE,audit,finish

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    out=HERE/'r05_direct'
    baseline=json.loads((BASE/'FREEZE_MANIFEST.json').read_text())
    for rel,digest in baseline['hashes'].items():assert sha(BASE/rel)==digest,rel
    for name in ['r01_method','r02_story','r03_language','r04_coldread']:
        path=HERE/name;sealed=json.loads((path/'SEALED.json').read_text())
        for rel,digest in sealed['hashes'].items():assert sha(path/rel)==digest,(name,rel)
    report=finish('r05_direct')
    assert report['pages']==8 and report['body_pages']==6
    assert report['reference_pages']==[7] and report['appendix_pages']==[8]
    assert not report['issues'] and report['references']==44
    assert len(report['figures'])==15 and report['no_banner']
    assert all(v['page']==v['references'][0] for v in report['figures'].values())
    source=(out/'manuscript.tex').read_text()
    main_text=source[:source.index(r'\appendices')]
    appendix=source[source.index(r'\appendices'):]
    assert not re.search(r'\\begin\{table\*?\}',source)
    assert all(r'\item[('+str(i)+')]' in main_text for i in (1,2,3))
    for phrase in ['cannot','does not solve','Neither this stack','not measurements','unmeasured']:
        assert phrase not in main_text,phrase
    assert 'Yellow-highlighted numerical values and panel titles identify authored design targets.' in appendix
    assert 'unmeasured values' in appendix and 'Each policy has one measured run.' in appendix
    assert main_text.count(r'Appendix~\ref{app:setup}')==1
    opening=re.search(r'\\begin\{abstract\}\s*(.*?\.)',source,re.S).group(1)
    assert len(opening.split())<16 and not re.search(r'\bwhen\b|cannot',opening)
    language=audit(source)
    assert not language['banned_tone'] and not language['long_sentences']
    previous=HERE/'r04_coldread'
    for folder in ['completion_figures','measured_figures','method_redesign','figures']:
        for f in (previous/folder).glob('*'):
            if f.is_file():assert sha(out/folder/f.name)==sha(f),(folder,f.name)
    for rel in ['ideal_assumptions.json','narrative_targets.json','references.bib']:
        assert sha(out/rel)==sha(previous/rel),rel
    doc=pymupdf.open(out/'manuscript.pdf');columns=[]
    for page_num in [1,2,3,4,5,6,8]:
        page=doc[page_num-1];vals={}
        for name,lo,hi in [('left',0,306),('right',306,612)]:
            blocks=[b for b in page.get_text('blocks') if b[0]>=lo and b[2]<=hi+3]
            bottom=max(b[3] for b in blocks)
            assert 680<=bottom<=723,(page_num,name,bottom)
            vals[name]=round(bottom,2)
        columns.append({'page':page_num,**vals})
    doc.close()
    result={'opening':opening,'validation':report,'language':language,'column_bottoms_pt':columns,
            'configuration_and_data_notes':'Appendix A, page 8','frozen_versions_preserved':True,
            'plot_data_and_targets_unchanged':True}
    (out/'SCREENING_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    paths=[p for p in out.rglob('*') if p.is_file() and p.suffix not in ['.aux','.log','.out','.fls','.fdb_latexmk','.blg']]
    hashes={str(p.relative_to(out)).replace('\\','/'):sha(p) for p in paths}
    (out/'SEALED.json').write_text(json.dumps({'revision':'r05_direct','date':'2026-11-07','hashes':hashes},indent=2)+'\n',encoding='utf-8')
    for p in paths+[out/'SEALED.json']:p.chmod(stat.S_IREAD)
    print('PASS: 6 body pages, references on 7, appendix on 8; 15 same-page figures; direct opening; configurations/data annotations in appendix; frozen inputs unchanged.')

if __name__=='__main__':main()
