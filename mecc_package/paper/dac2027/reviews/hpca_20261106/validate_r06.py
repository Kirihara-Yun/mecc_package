"""Artifact checks for R06; editorial judgment stays in the review record."""
from pathlib import Path
import hashlib,json,re,stat,argparse
import pymupdf
from iterate import HERE,BASE,audit,finish

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--revision',default='r06_editorial')
    parser.add_argument('--previous',default='r05_direct')
    args=parser.parse_args()
    out=HERE/args.revision;previous=HERE/args.previous
    manifest=json.loads((BASE/'FREEZE_MANIFEST.json').read_text())
    for rel,digest in manifest['hashes'].items():assert sha(BASE/rel)==digest,rel
    history=['r01_method','r02_story','r03_language','r04_coldread','r05_direct']
    if args.revision=='r07_proof':history.append('r06_editorial')
    for name in history:
        directory=HERE/name;sealed=json.loads((directory/'SEALED.json').read_text())
        for rel,digest in sealed['hashes'].items():assert sha(directory/rel)==digest,(name,rel)
    report=finish(args.revision)
    assert report['pages']==8 and report['body_pages']==6
    assert report['reference_pages']==[7] and report['appendix_pages']==[8]
    assert not report['issues'] and report['references']==44
    assert len(report['figures'])==15 and report['no_banner']
    assert all(v['references'][0]==v['page'] for v in report['figures'].values())
    new=(out/'manuscript.tex').read_text();old=(previous/'manuscript.tex').read_text()
    assert new.split(r'\appendices',1)[1]==old.split(r'\appendices',1)[1]
    cites=lambda t:set(k.strip() for group in re.findall(r'\\cite\{([^}]+)\}',t) for k in group.split(','))
    assert cites(new)==cites(old) and len(cites(new))==44
    assert all(r'\item[('+str(i)+')]' in new for i in (1,2,3))
    assert not re.search(r'\\begin\{table\*?\}',new)
    assert new.count(r'Appendix~\ref{app:setup}')==1
    for folder in ['completion_figures','measured_figures','method_redesign','figures']:
        for f in (previous/folder).glob('*'):
            if f.is_file():assert sha(out/folder/f.name)==sha(f),(folder,f.name)
    for rel in ['ideal_assumptions.json','narrative_targets.json','references.bib']:
        assert sha(out/rel)==sha(previous/rel),rel
    doc=pymupdf.open(out/'manuscript.pdf');columns=[]
    front='\n'.join(p.get_text() for p in doc[:7])
    for marker in ['ILLUSTRATIVE TARGET','TO MEASURE','TODO:','AI-generated','ChatGPT','OpenAI']:
        assert marker not in front,marker
    for i in [1,2,3,4,5,6,8]:
        page=doc[i-1];values={}
        for name,lo,hi in [('left',0,306),('right',306,612)]:
            blocks=[b for b in page.get_text('blocks') if b[0]>=lo and b[2]<=hi+3]
            bottom=max(b[3] for b in blocks)
            # Allow the final few lines after a paragraph/list ends; reject
            # large unfilled columns and text outside the body frame.
            assert 675<=bottom<=723,(i,name,bottom)
            values[name]=round(bottom,2)
        columns.append({'page':i,**values})
    assert 'unmeasured values' in doc[7].get_text()
    doc.close()
    language=audit(new)
    assert not language['banned_tone'] and not language['long_sentences']
    result={'artifact':report,'column_bottoms_pt':columns,'language_screen':language,
            'frozen_versions_preserved':True,'appendix_unchanged':True,
            'figures_and_data_unchanged':True,'citation_keys_unchanged':True,
            'editorial_record':'EDITORIAL_REVIEW.md'}
    (out/'EDITORIAL_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    paths=[p for p in out.rglob('*') if p.is_file() and p.suffix not in ['.aux','.log','.out','.fls','.fdb_latexmk','.blg']]
    hashes={str(p.relative_to(out)).replace('\\','/'):sha(p) for p in paths}
    (out/'SEALED.json').write_text(json.dumps({'revision':args.revision,'date':'2026-11-07','hashes':hashes},indent=2)+'\n',encoding='utf-8')
    for p in paths+[out/'SEALED.json']:p.chmod(stat.S_IREAD)
    print('PASS: 6+1+1 pages, 15 same-page figure explanations, 44 unchanged citation keys, stable data and appendix, frozen versions intact.')

if __name__=='__main__':main()
