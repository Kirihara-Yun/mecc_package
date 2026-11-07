"""Rebuild three R10 vector figures from committed inputs in an unsealed revision."""
import json
import sys
from iterate import HERE

OUT=HERE/"r10_relative"


def plots():
    assert OUT.exists() and not (OUT/'SEALED.json').exists()
    paper=HERE.parent.parent
    sys.path.insert(0,str(paper))
    from build_measured_a100 import load
    import build_compact_results as compact
    import matplotlib.pyplot as plt
    compact.setup()
    d=load();m=d['main'];ref=m['naive']['metrics']
    def save(fig,name):
        for ext in ['pdf','png']:
            fig.savefig(OUT/'measured_figures'/f'{name}.{ext}',dpi=280,bbox_inches='tight',pad_inches=.025)
        plt.close(fig)
    controls=[m['naive'],m['swapmoe'],d['independent'],m['ours']]
    fig,axs=plt.subplots(1,2,figsize=(3.45,2.35))
    fig.subplots_adjust(left=.22,right=.965,bottom=.19,top=.87,wspace=.36)
    for i,(ax,title,xlabel) in enumerate(zip(axs,['(a) Decode speedup','(b) HDD demand'],['Speedup (×)','Demand share (%)'])):
        vals=[ref['tpot_ms']/r['metrics']['tpot_ms'] if i==0 else r['metrics']['hit_pct']['ssd'] for r in controls]
        bars=ax.barh(range(4),vals,height=.58,color=[compact.GRAY,compact.ORANGE,compact.GRAY,compact.BLUE],ec=compact.INK,lw=.4,zorder=3)
        for b,h in zip(bars,['///','\\\\','...','xxx']):b.set_hatch(h)
        ax.bar_label(bars,labels=[f'{v:.2f}' if i==0 else f'{v:.1f}' for v in vals],padding=2,fontsize=6.5)
        ax.set_yticks(range(4),['Streaming','Swap-style','Separate','MECC'] if i==0 else ['']*4)
        ax.invert_yaxis();ax.set_xlim(0,2.45 if i==0 else 64)
        ax.set_xticks([0,1,2] if i==0 else [0,25,50]);ax.set_xlabel(xlabel,labelpad=2)
        ax.set_title(title,loc='left',fontweight='bold',pad=4);compact.style(ax)
        if i==0:ax.axvline(1,c=compact.INK,lw=.5,ls='--',zorder=2)
    save(fig,'intro_evidence')
    order=['naive','swapmoe','fiddler','flashmoe_rf_adaptation','ours_io','ours']
    labels=['Streaming','Swap-style','Fiddler-style','Flash-RF','MECC I/O','MECC']
    colors=[compact.GRAY,compact.ORANGE,'#B9ADBF','#77A18B',compact.TEAL,compact.BLUE]
    hatches=['///','\\\\','...','+++','---','xxx']
    fig,axs=plt.subplots(1,2,figsize=(3.45,1.82))
    fig.subplots_adjust(left=.255,right=.96,bottom=.24,top=.86,wspace=.36)
    for i,(ax,key,title) in enumerate(zip(axs,['tpot_ms','ttft_ms'],['(a) Decode speedup','(b) First-token speedup'])):
        vals=[ref[key]/m[p]['metrics'][key] for p in order]
        bars=ax.barh(range(6),vals,height=.62,color=colors,ec=compact.INK,lw=.4,zorder=3)
        for b,h in zip(bars,hatches):b.set_hatch(h)
        ax.bar_label(bars,labels=[f'{v:.2f}' for v in vals],padding=2,fontsize=6.2)
        ax.set_yticks(range(6),labels if i==0 else ['']*6);ax.invert_yaxis()
        ax.set_xlim(0,2.48 if i==0 else 2.05);ax.set_xticks([0,1,2] if i==0 else [0,1,1.5])
        ax.set_xlabel('Speedup (×)',labelpad=2)
        ax.set_title(title,loc='left',fontweight='bold',pad=4,fontsize=7.3)
        ax.axvline(1,c=compact.INK,lw=.5,ls='--',zorder=2);compact.style(ax)
    save(fig,'main')
    # Reuse the exact six-panel R08 vector drawing; only the adapter label changes.
    # Execute the maintained drawing source in an isolated namespace with the new destination.
    text=(HERE/'redraw_r08_motivation.py').read_text(encoding='utf-8')
    text=text.replace("OUT = HERE/'r08_layout'", "OUT = HERE/'r10_relative'")
    text=text.replace("['Separate','Fixed CPU','MECC']", "['Separate','Swap-style','MECC']")
    env={'__file__':str(HERE/'redraw_r08_motivation.py'),'__name__':'r10_motivation'}
    exec(compile(text,'r10_motivation','exec'),env)
    env['main']()
    audit={'definition':'speedup = reference phase latency / policy phase latency; higher is better',
        'reference':'a100-main-naive-20261104','display_names':dict(zip(order,labels)),
        'main':{p:{'run_id':m[p]['run_id'],'source_sha256':m[p]['sha256'],
                   'tpot_ms':m[p]['metrics']['tpot_ms'],'ttft_ms':m[p]['metrics']['ttft_ms'],
                   'decode_speedup':ref['tpot_ms']/m[p]['metrics']['tpot_ms'],
                   'first_token_speedup':ref['ttft_ms']/m[p]['metrics']['ttft_ms']} for p in order},
        'independent':{'run_id':d['independent']['run_id'],'source_sha256':d['independent']['sha256'],
            'tpot_ms':d['independent']['metrics']['tpot_ms'],
            'streaming_relative_speedup':ref['tpot_ms']/d['independent']['metrics']['tpot_ms'],
            'mecc_speedup':d['independent']['metrics']['tpot_ms']/m['ours']['metrics']['tpot_ms']},
        'mecc_HDD_demand_reduction_vs_independent_pct':100*(1-m['ours']['metrics']['hit_pct']['ssd']/d['independent']['metrics']['hit_pct']['ssd']),
        'budget_mecc_speedup_vs_streaming':{str(c):v['naive']['metrics']['tpot_ms']/v['ours']['metrics']['tpot_ms'] for c,v in d['budget'].items()},
        'original_runs_modified':False,
        'related_system_evidence':{'swapmoe':'completed local FP16 mechanism adapter',
            'fiddler':'completed local CPU-compute mechanism adapter',
            'flashmoe':'completed deterministic RF adapter, not trained original predictor',
            'moe_core':'no completed run found','moe_infinity':'benchmark entry exists; no completed result found'}}
    (OUT/'RATIO_AUDIT.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    plots()
