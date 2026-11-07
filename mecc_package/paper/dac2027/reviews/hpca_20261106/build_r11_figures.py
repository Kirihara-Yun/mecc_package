"""Draw the focused main figure and positive framework labels for R11."""
import json
import sys
from iterate import HERE

OUT=HERE/'r11_positive'
PAPER=HERE.parent.parent


def main():
    assert OUT.exists() and not (OUT/'SEALED.json').exists()
    sys.path.insert(0,str(PAPER))
    from build_measured_a100 import load
    import build_compact_results as c
    import matplotlib.pyplot as plt
    import numpy as np
    c.setup();d=load();m=d['main'];ref=m['naive']['metrics']
    order=['naive','swapmoe','fiddler','ours_io','ours']
    labels=['Streaming','Swap-style','Fiddler-style','MECC I/O','MECC']
    colors=[c.GRAY,c.ORANGE,'#B9ADBF',c.TEAL,c.BLUE]
    hatches=['///','\\\\','...','---','xxx']
    fig,axs=plt.subplots(1,2,figsize=(3.45,1.82))
    fig.subplots_adjust(left=.255,right=.96,bottom=.24,top=.86,wspace=.36)
    for i,(ax,key,title) in enumerate(zip(axs,['tpot_ms','ttft_ms'],['(a) Decode speedup','(b) First-token speedup'])):
        values=[ref[key]/m[p]['metrics'][key] for p in order]
        bars=ax.barh(range(len(order)),values,height=.62,color=colors,ec=c.INK,lw=.4,zorder=3)
        for b,h in zip(bars,hatches):b.set_hatch(h)
        ax.bar_label(bars,labels=[f'{v:.2f}' for v in values],padding=2,fontsize=6.2)
        ax.set_yticks(range(len(order)),labels if i==0 else ['']*len(order));ax.invert_yaxis()
        ax.set_xlim(0,2.48 if i==0 else 2.05);ax.set_xticks([0,1,2] if i==0 else [0,1,1.5])
        ax.set_xlabel('Speedup (×)',labelpad=2);ax.set_title(title,loc='left',fontweight='bold',pad=4,fontsize=7.3)
        ax.axvline(1,c=c.INK,lw=.5,ls='--',zorder=2);c.style(ax)
    for ext in ['pdf','png']:
        fig.savefig(OUT/'measured_figures'/f'main.{ext}',dpi=280,bbox_inches='tight',pad_inches=.025)
    plt.close(fig)
    # The framework layout is retained; the router label names its operation.
    script=(HERE/'r09_analysis/redraw_framework.py').read_text(encoding='utf-8')
    script=script.replace('Router (unchanged)','Expert routing')
    env={'__file__':str(OUT/'redraw_framework.py'),'__name__':'r11_framework'}
    exec(compile(script,'r11_framework','exec'),env);env['framework']()
    script=(HERE/'redraw_r08_motivation.py').read_text(encoding='utf-8')
    script=script.replace("OUT = HERE/'r08_layout'","OUT = HERE/'r11_positive'")
    script=script.replace("['Separate','Fixed CPU','MECC']","['Separate','Swap-style','MECC']")
    script=script.replace('Correct the initial profile online','Adapt residency to new requests')
    env={'__file__':str(HERE/'redraw_r08_motivation.py'),'__name__':'r11_motivation'}
    exec(compile(script,'r11_motivation','exec'),env);env['main']()
    # Cross-model arrays stay unchanged; show the streaming/MECC comparison used in its text.
    A=json.loads((OUT/'ideal_assumptions.json').read_text())
    c.setup();fig,ax=plt.subplots(figsize=(3.45,1.75));fig.subplots_adjust(.14,.25,.98,.75)
    x=np.arange(4)
    for offset,key,col,hatch,label in [(-.14,'Unoptimized streaming',c.GRAY,'...','Streaming'),(.14,'MECC',c.BLUE,'xxx','MECC')]:
        ax.bar(x+offset,A['tpot_seconds'][key],.26,color=col,ec=c.INK,lw=.35,hatch=hatch,label=label,zorder=3)
    ax.set_xticks(x,['8×7B / QA','8×7B / Code','8×22B / QA','8×22B / Code']);ax.set_ylim(0,72)
    c.style(ax,'y');ax.set_ylabel('TPOT (s/token)',labelpad=2)
    ax.legend(frameon=False,ncol=2,loc='upper left',handlelength=1,columnspacing=.7)
    t=ax.set_title('Model and workload',loc='left',pad=4)
    t.set_bbox({'facecolor':'#FFF19A','edgecolor':'none','pad':1.2})
    for ext in ['pdf','png']:
        fig.savefig(OUT/'completion_figures'/f'cross_model.{ext}',dpi=280,bbox_inches='tight',pad_inches=.025)
    plt.close(fig)
    manifest=json.loads((OUT/'completion_figures/SOURCE_MANIFEST.json').read_text())
    manifest['cross_model']['target_fields']=['groups','tpot_seconds.Unoptimized streaming','tpot_seconds.MECC']
    manifest['cross_model']['scope']='Two-policy design comparison. Source arrays retained unchanged.'
    (OUT/'completion_figures/SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    record={'main_figure_policies':order,'main_figure_display_names':labels,
            'additional_measured_adapter_location':'Appendix A, Measured Protocols; complete RATIO_AUDIT.json',
            'data_modified':False,'framework_label':'Expert routing',
            'cross_model_series':['Unoptimized streaming','MECC'],
            'main_figure_values':{p:{'decode':ref['tpot_ms']/m[p]['metrics']['tpot_ms'],
                'first_token':ref['ttft_ms']/m[p]['metrics']['ttft_ms']} for p in order}}
    (OUT/'FIGURE_SCOPE.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
