"""Check reviewer arithmetic, actual transitions, protocol separation, and PDF layout."""
import difflib,hashlib,json,re,stat,subprocess
import pymupdf
from iterate import HERE,BASE,audit,finish

OUT=HERE/'r12_protocols';PREV=HERE/'r11_positive';PKG=HERE.parents[3]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not (OUT/'SEALED.json').exists()
    for rel,digest in json.loads((BASE/'FREEZE_MANIFEST.json').read_text())['hashes'].items():assert sha(BASE/rel)==digest
    for folder in HERE.glob('r[0-9][0-9]_*'):
        if folder in [BASE,OUT]:continue
        for rel,digest in json.loads((folder/'SEALED.json').read_text())['hashes'].items():assert sha(folder/rel)==digest,(folder.name,rel)
    for name in ['ideal_assumptions.json','narrative_targets.json','references.bib','RATIO_AUDIT.json']:
        assert sha(OUT/name)==sha(PREV/name),name
    source=(OUT/'manuscript.tex').read_text(encoding='utf-8');old=(PREV/'manuscript.tex').read_text(encoding='utf-8')
    N=json.loads((OUT/'narrative_targets.json').read_text())
    pairs=[(i,j) for i in range(3) for j in range(3) if i!=j]
    fixed=[N['transfer_fixed'][i][j] for i,j in pairs];adaptive=[N['transfer_adaptive'][i][j] for i,j in pairs]
    assert sum(fixed)==84 and sum(fixed)/6==14
    reduction=100*(1-sum(adaptive)/sum(fixed));assert round(reduction,1)==33.0
    R=json.loads((OUT/'RATIO_AUDIT.json').read_text())
    raw={}
    for p,row in R['main'].items():
        f=PKG/'results/runs'/row['run_id']/'result.json'
        assert sha(f)==row['source_sha256'],p
        raw[p]=json.loads(f.read_text())['results'][p]
        assert abs(row['decode_speedup']-R['main']['naive']['tpot_ms']/raw[p]['tpot_ms'])<1e-12
    f=PKG/'results/runs'/R['independent']['run_id']/'result.json'
    assert sha(f)==R['independent']['source_sha256']
    indep=json.loads(f.read_text())['results']['independent'];o=raw['ours']
    four=indep['tpot_ms']/o['tpot_ms'];two=raw['fiddler']['ttft_ms']/o['ttft_ms']
    assert round(four,2)==4.46 and round(two,2)==2.86
    phases=o['phase_hits'];counts=[sum(v[i] for v in phases.values()) for i in range(4)]
    assert counts==[29558,3820,4764,0]
    expert_bytes=o['io_bytes']['ssd_read']//counts[2]
    assert expert_bytes==352321536 and expert_bytes*counts[2]==o['io_bytes']['ssd_read']
    expert_mib=expert_bytes/2**20;pool_gib=expert_bytes*256/2**30
    assert expert_mib==336 and pool_gib==84 and 128*expert_bytes/2**30==42
    g=json.loads((OUT/'G1_EVIDENCE.json').read_text())
    data=subprocess.run(['git','show',g['git_commit']+':'+g['source_path']],stdout=subprocess.PIPE,check=True).stdout
    assert hashlib.sha256(data).hexdigest()==g['source_sha256']
    cases=json.loads(data)['results']['ours']['cases'];assert len(cases)==2
    assert all(c['route_equal'] and c['tokens_equal'] and c['max_logit_abs_error']==c['max_gate_abs_error']==0 for c in cases)
    T=json.loads((OUT/'TRANSITION_AUDIT.json').read_text())
    for rel,digest in T['method_source_sha256'].items():assert sha(PKG/rel)==digest
    final=T['continuous_trace'][-1]
    assert final['hbm_mru_to_lru']==['a5','a3'] and final['cpu_mru_to_lru']==['a2','a1']
    assert T['previous_independent_cases'][-1]['hbm_mru_to_lru']==['a5','a1']
    B=json.loads((OUT/'BASELINE_TARGETS.json').read_text());P=json.loads((OUT/'PROTOCOLS.json').read_text())
    assert 'UNMEASURED' in B['status'] and P['E1']['status']=='measured single runs'
    assert P['E1']['input_tokens']==64 and P['E3']['input_tokens']==128 and P['E1']['init']=='uniform' and P['E3']['init']=='profile'
    assert r'p_{\ell,r}=q' not in source and r'\label{tab:protocols}' in source
    assert all(r'\item[('+str(i)+')]' in source for i in [1,2,3])
    keys=lambda s:{k.strip() for v in re.findall(r'\\cite\{([^}]+)\}',s) for k in v.split(',')}
    assert keys(source)==keys(old) and len(keys(source))==44
    report=finish('r12_protocols')
    assert (report['pages'],report['body_pages'],report['reference_pages'],report['appendix_pages'])==(8,6,[7],[8])
    assert not report['issues'] and len(report['figures'])==16 and report['references']==44
    assert all(v['references'][0]==v['page'] for v in report['figures'].values())
    assert report['figures']['fig:target_gpu']['page']==8 and report['figures']['fig:matched']['page']==5
    doc=pymupdf.open(OUT/'manuscript.pdf');app=re.sub(r'\s+',' ',re.sub(r'-\s*\n\s*','',doc[7].get_text()))
    assert all(word in app for word in ['unmeasured','not executions','E1 RF observation','1.81','1.54','84','14.00','9.3833'])
    front='\n'.join(p.get_text() for p in doc[:7])
    assert all(t not in front for t in ['ILLUSTRATIVE TARGET','TO MEASURE','TODO:','ChatGPT','AI-generated'])
    columns=[];lone=[]
    for i,page in enumerate(doc):
        ends={}
        for label,lo,hi in [('left',0,306),('right',306,612)]:
            blocks=[b for b in page.get_text('blocks') if b[0]>=lo and b[2]<=hi+3]
            ends[label]=round(max(b[3] for b in blocks),2)
            assert ends[label]<=723,(i+1,label,ends[label])
        columns.append({'page':i+1,**ends})
        if i<6:
            assert min(ends.values())>=650,(i+1,ends)
            for b in page.get_text('dict')['blocks']:
                if b['type']!=0:continue
                line=b['lines'][-1];text=''.join(s['text'] for s in line['spans']).strip()
                if re.fullmatch(r'[A-Za-z][A-Za-z-]*[.,;:]?',text) and any(s['font']=='TeXGyreTermesX-Regular' and 8.5<s['size']<9.3 for s in line['spans']):lone.append({'page':i+1,'text':text})
        page.get_pixmap(matrix=pymupdf.Matrix(1.6,1.6)).save(OUT/f'page_{i+1}.png')
    assert not lone,lone
    assert abs(columns[5]['left']-columns[5]['right'])<6
    language=audit(source);assert not language['banned_tone'] and not language['long_sentences'],language
    (OUT/'LANGUAGE_AUDIT.json').write_text(json.dumps(language,indent=2)+'\n',encoding='utf-8')
    facts={'transfer':{'fixed_offdiagonal':fixed,'fixed_sum':sum(fixed),'fixed_mean':sum(fixed)/6,'adaptive_mean':sum(adaptive)/6,'reduction_pct':reduction},
        'exact_ratios':{'independent_to_mecc_tpot':four,'fiddler_to_mecc_ttft':two,'streaming_to_mecc_tpot':raw['naive']['tpot_ms']/o['tpot_ms']},
        'rounded_bar_ratio_is_not_exact_ratio':True,'expert_bytes':expert_bytes,'expert_mib':expert_mib,'expert_pool_gib':pool_gib,
        'capacity_4_plus_4':{'hbm_primary_gib':42,'cpu_primary_gib':42,'cpu_mirrors_gib':42,'staging':'additional; not included in 84 GiB host weight storage'},
        'aggregate_access_counts':dict(zip(['hbm','cpu','hdd','cpu_compute'],counts)),
        'G1_cases_checked':2,'continuous_transition_verified':True,'E5_status':'unmeasured author targets, not evidence of wins'}
    (OUT/'REVIEW_FACT_AUDIT.json').write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8')
    (OUT/'changes.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),source.splitlines(True),fromfile='r11_positive',tofile='r12_protocols')),encoding='utf-8')
    validation={'artifact':report,'column_bottoms_pt':columns,'single_word_paragraph_tails':lone,'citation_keys':44,
        'configuration_table':True,'protocol_identifiers':['E1','E2','E3','E4','E5'],'full_appendix_in_delivered_pdf':True,
        'prior_measurements_and_design_arrays_unchanged':True,'new_baselines_status':'authored unmeasured E5 targets; appendix disclosure retained',
        'arithmetic_and_raw_source_hashes_verified':True,'actual_cache_methods_executed_on_symbolic_weights':True,
        'old_independent_cases_were_valid':True,'old_archives_unchanged':True,'no_new_A100_runs':True}
    (OUT/'PROTOCOL_VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n',encoding='utf-8')
    doc.close()
    paths=[p for p in OUT.rglob('*') if p.is_file() and p.name!='SEALED.json' and p.suffix not in ['.aux','.log','.out','.fls','.fdb_latexmk','.blg']]
    hashes={p.relative_to(OUT).as_posix():sha(p) for p in paths}
    (OUT/'SEALED.json').write_text(json.dumps({'revision':'r12_protocols','date':'2026-11-07','hashes':hashes},indent=2)+'\n',encoding='utf-8')
    for p in paths+[OUT/'SEALED.json']:p.chmod(stat.S_IREAD)
    print('PASS: protocols and configuration; reviewer arithmetic; actual transitions; raw-run bytes/ratios; two G1 cases; target disclosure; 6+1+1 pages.')


if __name__=='__main__':main()
