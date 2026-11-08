"""Compare compact two/three-panel introductions using the same observed runs."""
import hashlib
import json
from pathlib import Path
import shutil
import stat
import sys
from iterate import HERE,PAPER

PREV=HERE/'r17_figure_type'
OUT=HERE/'r18_intro_design'
PKG=HERE.parents[3]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (OUT/'SEALED.json').exists()
    if not OUT.exists():
        for rel,digest in json.loads((PREV/'SEALED.json').read_text())['hashes'].items():
            assert sha(PREV/rel)==digest,rel
            dst=OUT/rel;dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(PREV/rel,dst);dst.chmod(stat.S_IREAD|stat.S_IWRITE)
    source=(PREV/'manuscript.tex').read_text(encoding='utf-8')
    old='Mixtral-8x7B on one A100. Decode speedup is relative to streaming; Separate uses independent HBM/CPU caches. Swap-style is the SwapMoE-style adapter. Higher speedup and lower HDD demand are better.'
    new=('Mixtral-8x7B on one A100. (a) Decode speedup relative to streaming. '
         '(b) Request shares served by HBM, CPU, and HDD; labels show HBM and HDD shares. '
         'Separate uses independent caches. Swap-style denotes the SwapMoE-style adapter. '
         'The four paths execute experts on GPU.')
    assert old in source
    (OUT/'manuscript.tex').write_text(source.replace(old,new,1),encoding='utf-8')
    sys.path.insert(0,str(PAPER))
    from build_measured_a100 import load
    import build_compact_results as c
    import matplotlib.pyplot as plt
    import numpy as np
    c.setup()
    plt.rcParams.update({'font.size':7.2,'axes.titlesize':7.5,'axes.labelsize':7.2,
        'xtick.labelsize':7,'ytick.labelsize':7.2,'legend.fontsize':6.4})
    data=load();controls=[data['main']['naive'],data['main']['swapmoe'],data['independent'],data['main']['ours']]
    names=['Streaming','Swap-style','Separate','MECC'];ref=controls[0]['metrics']
    speed=[ref['tpot_ms']/row['metrics']['tpot_ms'] for row in controls]
    first=[ref['ttft_ms']/row['metrics']['ttft_ms'] for row in controls]
    shares=[];provenance=[]
    for row in controls:
        path=PKG/'results/runs'/row['run_id']/'result.json'
        assert sha(path)==row['sha256']
        raw=json.loads(path.read_text())['results']
        entry=next(v for v in raw.values() if isinstance(v,dict) and 'phase_hits' in v)
        counts=[sum(v[i] for v in entry['phase_hits'].values()) for i in range(4)]
        assert counts[3]==0
        values=np.array(counts[:3])/sum(counts)*100
        assert round(values[2],1)==row['metrics']['hit_pct']['ssd']
        shares.append(values)
        provenance.append({'run_id':row['run_id'],'source_sha256':sha(path),'counts_hbm_cpu_hdd':counts[:3],
            'shares_hbm_cpu_hdd':values.tolist(),'tpot_ms':row['metrics']['tpot_ms'],'ttft_ms':row['metrics']['ttft_ms']})
    shares=np.array(shares)
    colors=[c.GRAY,c.GRAY,c.GRAY,c.BLUE]
    def save(fig,stem):
        for ext in ['pdf','png']:
            fig.savefig(OUT/'measured_figures'/f'{stem}.{ext}',dpi=300)
        plt.close(fig)
    def common(ax,title,labels=False):
        ax.set_yticks(range(4),names if labels else ['']*4)
        ax.set_ylim(3.62,-.62);ax.tick_params(axis='y',length=0,pad=3)
        ax.set_title(title,loc='left',fontweight='bold',pad=5,fontsize=7.5)
        c.style(ax);ax.tick_params(axis='y',length=0)
        ax.spines['left'].set_visible(False)
    fig=plt.figure(figsize=(3.5,151/72))
    left=fig.add_axes([.205,.27,.30,.60]);right=fig.add_axes([.61,.27,.37,.60])
    bars=left.barh(range(4),speed,.64,color=colors,ec=c.INK,lw=.35,zorder=3)
    left.bar_label(bars,labels=[f'{v:.3f}' for v in speed],padding=2,fontsize=6.6)
    left.set_xlim(0,2.45);left.set_xticks([0,1,2]);left.set_xlabel('Speedup (×)',labelpad=3)
    left.axvline(1,c='#8E9CAA',lw=.55,ls='--',zorder=2)
    common(left,'(a) Decode speedup',True)
    bottom=np.zeros(4)
    for i,(label,color,hatch) in enumerate(zip(['HBM','CPU','HDD'],['#E5EBF0','#9BAEBB',c.ORANGE],['','///',''])):
        right.barh(range(4),shares[:,i],.64,left=bottom,color=color,ec=c.INK,lw=.3,hatch=hatch,label=label,zorder=3)
        if i in [0,2]:
            for j,value in enumerate(shares[:,i]):
                right.text(bottom[j]+value/2,j,f'{value:.1f}',ha='center',va='center',fontsize=6.2,color=c.INK)
        bottom+=shares[:,i]
    right.set_xlim(0,100);right.set_xticks([0,50,100]);right.set_xlabel('Request share (%)',labelpad=3)
    right.get_xticklabels()[-1].set_horizontalalignment('right')
    common(right,'(b) Request source')
    right.legend(loc='lower center',bbox_to_anchor=(.5,-.43),ncol=3,frameon=False,
        handlelength=.9,handletextpad=.3,columnspacing=.6,borderaxespad=0,fontsize=6.4)
    save(fig,'intro_evidence')
    # Alternative: three metric columns. Keep it separate from the selected manuscript figure.
    fig=plt.figure(figsize=(3.5,151/72))
    for i,(values,title,xlabel,limit,ticks) in enumerate(zip([speed,first,shares[:,2]],
        ['(a) Decode','(b) First token','(c) HDD'],['Speedup (×)','Speedup (×)','Share (%)'],[2.8,1.7,70],[[0,1,2],[0,1],[0,25,50]])):
        ax=fig.add_axes([.205+i*.255,.27,.205,.60])
        bars=ax.barh(range(4),values,.64,color=colors,ec=c.INK,lw=.35,zorder=3)
        ax.bar_label(bars,labels=[f'{v:.3f}' if i<2 else f'{v:.1f}' for v in values],padding=1.5,fontsize=6.2)
        ax.set_xlim(0,limit);ax.set_xticks(ticks);ax.set_xlabel(xlabel,labelpad=3)
        common(ax,title,i==0)
        if i<2:ax.axvline(1,c='#8E9CAA',lw=.55,ls='--',zorder=2)
    save(fig,'intro_alternative_three_columns')
    (OUT/'INTRO_FIGURE_DATA.json').write_text(json.dumps({'selected_design':'two panels: decode plus source composition',
        'three_column_alternative':'measured_figures/intro_alternative_three_columns.pdf',
        'source_protocol':'E1; original four controls; no new runs or target data',
        'decode_speedups':speed,'first_token_speedups':first,'rows':provenance,
        'exact_shares_from_counts_not_normalized_rounded_percentages':True,
        'numeric_labels':{'decode_decimals':3,'share_decimals':1},
        'color_scope':'left: neutral controls and MECC emphasis; right: one tier legend'},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
