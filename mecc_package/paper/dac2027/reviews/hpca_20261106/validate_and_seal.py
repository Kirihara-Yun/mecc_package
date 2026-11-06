"""Validate immutable inputs, final geometry, and each review artifact."""
from pathlib import Path
import hashlib,json,re,stat
import pymupdf
from iterate import HERE,BASE,finish,audit

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    baseline=json.loads((BASE/'FREEZE_MANIFEST.json').read_text())
    for rel,digest in baseline['hashes'].items():assert sha(BASE/rel)==digest,rel
    paper=HERE.parent.parent
    assert sha(paper/'MECC_DAC_title_highlight.pdf')==baseline['hashes']['MECC_DAC_title_highlight.pdf']
    reports={}
    for name in ['r01_method','r02_story','r03_language','r04_coldread']:
        out=HERE/name
        report=finish(name)
        assert report['pages']==7 and report['references']==44
        assert not report['issues'],(name,report['issues'])
        assert len(report['figures'])==15 and report['no_banner']
        assert all(f['references'][0]==f['page'] for f in report['figures'].values())
        assert (out/'REVIEW.md').exists()
        for rel in ['ideal_assumptions.json','narrative_targets.json','references.bib']:
            assert sha(out/rel)==baseline['hashes'][rel],(name,rel)
        for rel,digest in baseline['hashes'].items():
            if rel.startswith(('completion_figures/','measured_figures/','method_redesign/')):
                assert sha(out/rel)==digest,(name,rel)
        src=(out/'manuscript.tex').read_text()
        assert all(r'\item[('+str(i)+')]' in src for i in [1,2,3])
        assert not re.search(r'\\begin\{table\*?\}',src)
        reports[name]=report
    last=HERE/'r04_coldread';doc=pymupdf.open(last/'manuscript.pdf')
    columns=[]
    for i,page in enumerate(doc[:6],1):
        vals={}
        for name,lo,hi in [('left',0,306),('right',306,612)]:
            b=[b for b in page.get_text('blocks') if b[0]>=lo and b[2]<=hi+3]
            bottom=max(v[3] for v in b)
            assert 680<=bottom<=723,(i,name,bottom)
            vals[name]=round(bottom,2)
        columns.append({'page':i,**vals})
    text='\n'.join(p.get_text() for p in doc);doc.close()
    assert 'not measurements' in text
    src=(last/'manuscript.tex').read_text();language=audit(src)
    assert not language['banned_tone'] and not language['long_sentences']
    assert language['share_at_most_25']==1.0
    report={'baseline_preserved':True,'data_arrays_unchanged':True,'measured_assets_unchanged':True,
            'rounds':reports,'final_columns_pt':columns,'final_language':language,
            'recommendation':3,'target_recommendation':5,'target_achieved':False,
            'remaining':'Technical distinction and implementation/resource contracts; not the ideal-data assumption.'}
    (HERE/'SESSION_VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    for name in reports:
        out=HERE/name
        paths=[p for p in out.rglob('*') if p.is_file() and p.suffix not in ['.aux','.log','.out','.fls','.fdb_latexmk','.blg']]
        hashes={str(p.relative_to(out)).replace('\\','/'):sha(p) for p in paths}
        (out/'SEALED.json').write_text(json.dumps({'revision':name,'hashes':hashes},indent=2)+'\n',encoding='utf-8')
        for p in paths+[out/'SEALED.json']:p.chmod(stat.S_IREAD)
    print('PASS: frozen baseline intact; four separate 6+1 PDFs; all numerical arrays and measured plots unchanged; 15 first-reference matches per round; final columns and language checked.')

if __name__=='__main__':main()
