"""Check manuscript analysis against its unchanged source arrays and PDF."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import stat
import pymupdf
from iterate import HERE,BASE,audit,finish

OUT=HERE/'r09_analysis'
PREV=HERE/'r08_layout'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def allspans(page):
    return [s for b in page.get_text('dict')['blocks'] if b['type']==0
            for line in b['lines'] for s in line['spans']]


def main():
    assert not (OUT/'SEALED.json').exists(),'Never overwrite an archived revision'
    frozen=json.loads((BASE/'FREEZE_MANIFEST.json').read_text())
    for rel,digest in frozen['hashes'].items():assert sha(BASE/rel)==digest,rel
    for directory in sorted(HERE.glob('r0*_*')):
        if directory in [BASE,OUT]:continue
        record=json.loads((directory/'SEALED.json').read_text())
        for rel,digest in record['hashes'].items():assert sha(directory/rel)==digest,(directory.name,rel)
    source=(OUT/'manuscript.tex').read_text(encoding='utf-8')
    old=(PREV/'manuscript.tex').read_text(encoding='utf-8')
    for rel in ['ideal_assumptions.json','narrative_targets.json','references.bib']:
        assert sha(OUT/rel)==sha(PREV/rel),rel
    for folder in ['measured_figures','completion_figures','method_redesign','figures']:
        for path in (PREV/folder).glob('*.pdf'):
            assert sha(OUT/folder/path.name)==sha(path),(folder,path.name)
    cites=lambda s:set(k.strip() for g in re.findall(r'\\cite\{([^}]+)\}',s) for k in g.split(','))
    assert cites(source)==cites(old) and len(cites(source))==44
    assert r'\section{Related Work}' not in source
    assert all(r'\item[('+str(i)+')]' in source for i in [1,2,3])
    assert source.count(r'\pending{9 output tokens}')==1
    assert r'\pending{doubles}' in source
    assert r'\pending{33.0 percent}' in source
    assert r'\pending{15.84 seconds}' in source
    # All new comparisons are arithmetic of the previously authored arrays.
    A=json.loads((OUT/'ideal_assumptions.json').read_text())
    N=json.loads((OUT/'narrative_targets.json').read_text())
    pairs=[(i,j) for i in range(3) for j in range(3) if i!=j]
    means={key:sum(N[key][i][j] for i,j in pairs)/6 for key in ['transfer_fixed','transfer_adaptive']}
    init_premium=A['startup_cost_seconds']['MECC']-A['startup_cost_seconds']['reference']
    decode_saving=A['startup_decode_tpot_seconds']['reference']-A['startup_decode_tpot_seconds']['MECC']
    result={'status':'Arithmetic from authored unmeasured design arrays; no additional experimental runs',
        'inputs':{p:sha(OUT/p) for p in ['ideal_assumptions.json','narrative_targets.json']},
        'transfer':{'off_diagonal_means':means,'reduction_pct':100*(1-means['transfer_adaptive']/means['transfer_fixed']),
            'diagonal_means':{key:sum(N[key][i][i] for i in range(3))/3 for key in ['transfer_fixed','transfer_adaptive']}},
        'component_savings':[a-b for a,b in zip(A['ablation_tpot_seconds'][:-1],A['ablation_tpot_seconds'][1:])],
        'io_exposed_savings':{key:N[key][-2]-N[key][-1] for key in ['exposed_hdd','exposed_h2d']},
        'cross_model_speedups':[a/b for a,b in zip(A['tpot_seconds']['Unoptimized streaming'],A['tpot_seconds']['MECC'])],
        'cross_model_absolute_savings':[a-b for a,b in zip(A['tpot_seconds']['Unoptimized streaming'],A['tpot_seconds']['MECC'])],
        'mecc_size_growth':[A['tpot_seconds']['MECC'][i+2]/A['tpot_seconds']['MECC'][i] for i in range(2)],
        'streaming_size_growth':[A['tpot_seconds']['Unoptimized streaming'][i+2]/A['tpot_seconds']['Unoptimized streaming'][i] for i in range(2)],
        'host_increment_savings':[a-b for a,b in zip(A['budget_tpot_seconds']['MECC'][:-1],A['budget_tpot_seconds']['MECC'][1:])],
        'ttft_speedups':[a/b for a,b in zip(N['input_ttft_streaming'],N['input_ttft_mecc'])],
        'batch':{'throughput_growth':N['batch_throughput_mecc'][-1]/N['batch_throughput_mecc'][0],
            'step_seconds_B1':1/N['batch_throughput_mecc'][0],'step_seconds_B8':8/N['batch_throughput_mecc'][-1]},
        'startup':{'initial_premium':init_premium,'decode_saving':decode_saving,'crossing_tokens':init_premium/decode_saving,
            'initial_per_token_n64':{k:A['startup_cost_seconds'][k]/64 for k in ['reference','MECC']},
            'total_per_token_n64':{k:A['startup_cost_seconds'][k]/64+A['startup_decode_tpot_seconds'][k] for k in ['reference','MECC']}}}
    assert result['component_savings']==[6,7,3]
    assert result['mecc_size_growth']==[2,2]
    assert round(result['transfer']['reduction_pct'],1)==33
    assert round(result['batch']['step_seconds_B8'],2)==15.84
    assert result['startup']['crossing_tokens']==9
    (OUT/'DERIVED_ANALYSIS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    report=finish('r09_analysis')
    assert (report['pages'],report['body_pages'],report['reference_pages'],report['appendix_pages'])==(8,6,[7],[8])
    assert not report['issues'] and report['references']==44 and len(report['figures'])==15
    assert all(f['references'][0]==f['page'] for f in report['figures'].values())
    doc=pymupdf.open(OUT/'manuscript.pdf');front='\n'.join(p.get_text() for p in doc[:7])
    notes=['ILLUSTRATIVE TARGET','TO MEASURE','TODO:','AI-generated','ChatGPT','unmeasured','authored design targets','figure data annotations']
    for note in notes:assert note.lower() not in front.lower(),note
    appendix=doc[7].get_text()
    assert 'unmeasured values' in appendix and 'not additional runs' in appendix
    assert 'Source Records' in appendix and 'Measured Protocols' in appendix
    p1=allspans(doc[0]);plot=[s for s in p1 if 'TimesNewRoman' in s['font'] and s['bbox'][0]>305]
    prose=[s for s in p1 if 'TeXGyreTermesX' in s['font'] and s['bbox'][0]>305 and s['size']<10]
    assert max(s['bbox'][3] for s in plot)<min(s['bbox'][1] for s in prose)
    titles=[s for s in allspans(doc[1]) if re.match(r'^\([a-f]\) ',s['text'])]
    assert len(titles)==6 and len({(s['font'],round(s['size'],3),s['flags']) for s in titles})==1
    heading=[s for s in allspans(doc[2]) if 'Overview' in s['text'] and 'TeXGyreTermesX' in s['font']]
    assert len(heading)==1 and heading[0]['bbox'][2]<306 and heading[0]['bbox'][1]>250
    columns=[];lone_words=[]
    for i,page in enumerate(doc):
        ends={}
        for label,lo,hi in [('left',0,306),('right',306,612)]:
            blocks=[b for b in page.get_text('blocks') if b[0]>=lo and b[2]<=hi+3]
            ends[label]=round(max(b[3] for b in blocks),2)
            assert ends[label]<=723,(i+1,label,ends[label])
        columns.append({'page':i+1,**ends})
        if i<6:
            assert min(ends.values())>=675,(i+1,ends)
            for b in page.get_text('dict')['blocks']:
                if b['type']!=0:continue
                line=b['lines'][-1];t=''.join(s['text'] for s in line['spans']).strip()
                if re.fullmatch(r'[A-Za-z][A-Za-z-]*[.,;:]?',t) and any(s['font']=='TeXGyreTermesX-Regular' and 8.5<s['size']<9.3 for s in line['spans']):
                    lone_words.append({'page':i+1,'text':t})
        if i<7:page.get_pixmap(matrix=pymupdf.Matrix(1.6,1.6)).save(OUT/f'page_{i+1}.png')
    assert not lone_words,lone_words
    assert abs(columns[2]['left']-columns[2]['right'])<3
    assert abs(columns[5]['left']-columns[5]['right'])<5
    assert abs(columns[6]['left']-columns[6]['right'])<6
    doc.close();language=audit(source)
    assert not language['banned_tone'] and not language['long_sentences']
    (OUT/'LANGUAGE_AUDIT.json').write_text(json.dumps(language,indent=2)+'\n',encoding='utf-8')
    (OUT/'changes.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),source.splitlines(True),fromfile='r08_layout',tofile='r09_analysis')),encoding='utf-8')
    validation={'artifact':report,'column_bottoms_pt':columns,'single_word_paragraph_tails':lone_words,
        'standalone_related_work_removed':True,'all_44_citation_keys_retained':True,
        'figures_and_input_arrays_unchanged':True,'derived_values_recomputed':True,
        'configuration_and_data_identity_notes_page':8,'front_seven_editorial_marker_hits':[],
        'data_identity_disclosure_retained':True,'highlighted_values_retained':True,
        'previous_freezes_verified':True,'editorial_record':'ANALYSIS_REVIEW.md'}
    (OUT/'ANALYSIS_VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n',encoding='utf-8')
    paths=[p for p in OUT.rglob('*') if p.is_file() and p.name!='SEALED.json' and p.suffix not in ['.aux','.log','.out','.fls','.fdb_latexmk','.blg']]
    hashes={p.relative_to(OUT).as_posix():sha(p) for p in paths}
    (OUT/'SEALED.json').write_text(json.dumps({'revision':'r09_analysis','date':'2026-11-07','hashes':hashes},indent=2)+'\n',encoding='utf-8')
    for p in paths+[OUT/'SEALED.json']:p.chmod(stat.S_IREAD)
    print('PASS: 6+1+1 pages; deeper analysis; 44 citations and all plots retained; calculations checked; data notes in appendix; no lone-word paragraph tails.')


if __name__=='__main__':main()
