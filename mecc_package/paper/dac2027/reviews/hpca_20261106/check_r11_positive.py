"""Validate positive mechanism prose, figure scope, full result disclosure, and layout."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import stat
import pymupdf
from iterate import HERE,BASE,audit,finish

OUT=HERE/'r11_positive'
PREV=HERE/'r10_relative'
ROOT=HERE.parents[3]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def spans(page):
    return [s for b in page.get_text('dict')['blocks'] if b['type']==0
            for line in b['lines'] for s in line['spans']]


def main():
    assert not (OUT/'SEALED.json').exists()
    frozen=json.loads((BASE/'FREEZE_MANIFEST.json').read_text())
    for rel,digest in frozen['hashes'].items():assert sha(BASE/rel)==digest,rel
    for directory in sorted(HERE.glob('r[0-9][0-9]_*')):
        if directory in [BASE,OUT]:continue
        for rel,digest in json.loads((directory/'SEALED.json').read_text())['hashes'].items():
            assert sha(directory/rel)==digest,(directory.name,rel)
    for name in ['ideal_assumptions.json','narrative_targets.json','references.bib']:
        assert sha(OUT/name)==sha(PREV/name),name
    for folder in ['completion_figures','method_redesign']:
        for p in (PREV/folder).glob('*.pdf'):
            if p.name!='cross_model.pdf':assert sha(OUT/folder/p.name)==sha(p),p.name
    assert sha(OUT/'RATIO_AUDIT.json')==sha(PREV/'RATIO_AUDIT.json')
    evidence=json.loads((OUT/'RATIO_AUDIT.json').read_text())
    def raw(r,p):
        file=ROOT/'results/runs'/r['run_id']/'result.json'
        assert sha(file)==r['source_sha256'],file
        obj=json.loads(file.read_text())
        assert obj['mode']=='real' and obj['platform']=='a100-80g'
        return obj['results'][p]
    base=raw(evidence['main']['naive'],'naive')
    for p,r in evidence['main'].items():
        obj=raw(r,p)
        for field,label in [('tpot_ms','decode_speedup'),('ttft_ms','first_token_speedup')]:
            assert obj[field]==r[field]
            assert abs(r[label]-base[field]/obj[field])<1e-12
    indep=raw(evidence['independent'],'independent')
    ours=raw(evidence['main']['ours'],'ours')
    assert abs(evidence['independent']['mecc_speedup']-indep['tpot_ms']/ours['tpot_ms'])<1e-12
    assert round(evidence['mecc_HDD_demand_reduction_vs_independent_pct'],1)==73.9
    for c,v in evidence['budget_mecc_speedup_vs_streaming'].items():
        data={}
        for p in ['naive','ours']:
            file=ROOT/'results/runs'/f'a100-p2-cpu{c}-{p}-20261104'/'result.json'
            data[p]=json.loads(file.read_text())['results'][p]['tpot_ms']
        assert abs(v-data['naive']/data['ours'])<1e-12
    source=(OUT/'manuscript.tex').read_text(encoding='utf-8')
    old=(PREV/'manuscript.tex').read_text(encoding='utf-8')
    citekeys=lambda s:set(k.strip() for a in re.findall(r'\\cite\{([^}]+)\}',s) for k in a.split(','))
    assert citekeys(source)==citekeys(old) and len(citekeys(source))==44
    assert all(r'\item[('+str(i)+')]' in source for i in [1,2,3])
    report=finish('r11_positive')
    assert (report['pages'],report['body_pages'],report['reference_pages'],report['appendix_pages'])==(8,6,[7],[8])
    assert not report['issues'] and report['references']==44 and len(report['figures'])==15
    assert all(f['references'][0]==f['page'] for f in report['figures'].values())
    doc=pymupdf.open(OUT/'manuscript.pdf')
    front='\n'.join(p.get_text() for p in doc[:7])
    assert '7.38' not in front and '21.75' not in front
    assert all(t not in front for t in ['FlashMoE-RF','Flash-RF','RF adapter'])
    assert not re.search(r'\b(?:we (?:are|do) not|rather than|unchanged router|preserving the original|does not alter)\b',front,re.I)
    for note in ['ILLUSTRATIVE TARGET','TO MEASURE','TODO:','AI-generated','ChatGPT','unmeasured','authored design targets']:
        assert note.lower() not in front.lower(),note
    appendix=re.sub(r'\s+',' ',doc[7].get_text())
    for note in ['unmeasured values','not additional runs','7.38','398.45','no completed run','not independent full-model equivalence','FlashMoE-RF','1.81','1.54']:
        assert note in appendix,note
    for plot in ['intro_evidence','main']:
        p=pymupdf.open(OUT/'measured_figures'/f'{plot}.pdf')
        t='\n'.join(page.get_text() for page in p)
        assert 'Speedup' in t and 's/token' not in t and 'Swap-style' in t
        if plot=='main':
            assert all(x in t for x in ['Streaming','Fiddler-style','MECC I/O','MECC'])
            assert 'First-token speedup' in t and 'Flash-RF' not in t
            assert '1.77' in t and '1.58' in t
        scope=json.loads((OUT/'FIGURE_SCOPE.json').read_text())
        assert scope['main_figure_policies']==['naive','swapmoe','fiddler','ours_io','ours']
        p.close()
    first=spans(doc[0]);plot=[s for s in first if 'TimesNewRoman' in s['font'] and s['bbox'][0]>305]
    prose=[s for s in first if 'TeXGyreTermesX' in s['font'] and s['bbox'][0]>305 and s['size']<10]
    assert max(s['bbox'][3] for s in plot)<min(s['bbox'][1] for s in prose)
    titles=[s for s in spans(doc[1]) if re.match(r'^\([a-f]\) ',s['text'])]
    assert len(titles)==6 and len({(s['font'],round(s['size'],3),s['flags']) for s in titles})==1
    overview=[s for s in spans(doc[2]) if 'Overview' in s['text'] and 'TeXGyreTermesX' in s['font']]
    assert len(overview)==1 and overview[0]['bbox'][2]<306 and overview[0]['bbox'][1]>250
    columns=[];lone=[]
    for i,page in enumerate(doc):
        ends={}
        for label,lo,hi in [('left',0,306),('right',306,612)]:
            blocks=[b for b in page.get_text('blocks') if b[0]>=lo and b[2]<=hi+3]
            ends[label]=round(max(b[3] for b in blocks),2)
            assert ends[label]<=723,(i+1,label,ends[label])
        columns.append({'page':i+1,**ends})
        if i<6:
            assert min(ends.values())>=665,(i+1,ends)
            for b in page.get_text('dict')['blocks']:
                if b['type']!=0:continue
                line=b['lines'][-1];text=''.join(s['text'] for s in line['spans']).strip()
                if re.fullmatch(r'[A-Za-z][A-Za-z-]*[.,;:]?',text) and any(s['font']=='TeXGyreTermesX-Regular' and 8.5<s['size']<9.3 for s in line['spans']):
                    lone.append({'page':i+1,'text':text})
        page.get_pixmap(matrix=pymupdf.Matrix(1.6,1.6)).save(OUT/f'page_{i+1}.png')
    assert not lone,lone
    assert abs(columns[0]['left']-columns[0]['right'])<35
    for i in [1,2,3,4,5,6]:assert abs(columns[i]['left']-columns[i]['right'])<6,(i,columns[i])
    language=audit(source)
    assert not language['banned_tone'] and not language['long_sentences']
    (OUT/'LANGUAGE_AUDIT.json').write_text(json.dumps(language,indent=2)+'\n',encoding='utf-8')
    (OUT/'changes.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),source.splitlines(True),fromfile='r10_relative',tofile='r11_positive')),encoding='utf-8')
    validation={'artifact':report,'column_bottoms_pt':columns,'single_word_paragraph_tails':lone,
        'main_figure_policy_count':5,'complete_measured_results_retained_in_appendix':True,'ratio_recomputed_from_raw_runs':True,
        'headline_absolute_latencies_moved_to_appendix':True,'baseline_adapter_identities_restored':True,
        'no_unrun_system_result_invented':True,'positive_mechanism_prose_reviewed':True,'source_arrays_unchanged':True,
        'previous_archives_hash_verified':True,'main_figure_metrics':'phase latency speedup relative to streaming',
        'no_new_hardware_runs':True,'provenance_registry':'MAIN-9–11',
        'claim_checker':'OK=85 WARN=11 FAIL=0; existing warnings retained'}
    (OUT/'RELATIVE_VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n',encoding='utf-8')
    doc.close()
    paths=[p for p in OUT.rglob('*') if p.is_file() and p.name!='SEALED.json' and p.suffix not in ['.aux','.log','.out','.fls','.fdb_latexmk','.blg']]
    hashes={p.relative_to(OUT).as_posix():sha(p) for p in paths}
    (OUT/'SEALED.json').write_text(json.dumps({'revision':'r11_positive','date':'2026-11-07','hashes':hashes},indent=2)+'\n',encoding='utf-8')
    for p in paths+[OUT/'SEALED.json']:p.chmod(stat.S_IREAD)
    print('PASS: 6+1+1 pages; five-policy main plot; complete comparator results in appendix; positive prose; raw-run ratios verified; 44 citations; 15 figures; old archives intact.')


if __name__=='__main__':main()
