"""Restore the paired-bar design and improve its proportions without adding metrics."""
import hashlib
import json
import re
import shutil
import stat
import sys
from iterate import HERE,PAPER

PREV=HERE/'r18_intro_design'
OUT=HERE/'r19_intro_bars'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (OUT/'SEALED.json').exists()
    if not OUT.exists():
        for rel,h in json.loads((PREV/'SEALED.json').read_text())['hashes'].items():
            assert sha(PREV/rel)==h,rel
            dst=OUT/rel;dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(PREV/rel,dst);dst.chmod(stat.S_IREAD|stat.S_IWRITE)
    source=(PREV/'manuscript.tex').read_text(encoding='utf-8')
    old_caption=re.search(r'\\caption\{Mixtral-8x7B on one A100\.[^\n]+',source).group()
    restored=re.search(r'\\caption\{Mixtral-8x7B on one A100\.[^\n]+',
        (HERE/'r17_figure_type/manuscript.tex').read_text(encoding='utf-8')).group()
    (OUT/'manuscript.tex').write_text(source.replace(old_caption,restored,1),encoding='utf-8')
    sys.path.insert(0,str(PAPER))
    import matplotlib.pyplot as plt
    import build_compact_results as c
    c.setup()
    plt.rcParams.update({'font.size':7.2,'axes.titlesize':8,'axes.labelsize':7.2,
        'xtick.labelsize':7.2,'ytick.labelsize':7.6,'hatch.linewidth':.45})
    data=json.loads((OUT/'INTRO_FIGURE_DATA.json').read_text())
    speed=data['decode_speedups'];demand=[row['shares_hbm_cpu_hdd'][2] for row in data['rows']]
    names=['Streaming','Swap-style','Separate','MECC']
    fig=plt.figure(figsize=(3.5,162/72))
    axes=[fig.add_axes([.16,.17,.35,.72]),fig.add_axes([.615,.17,.35,.72])]
    for i,(ax,values,title,xlabel,limit,ticks) in enumerate(zip(axes,[speed,demand],
        ['(a) Decode speedup','(b) HDD demand'],['Speedup (×)','Demand share (%)'],[2.1,56],[[0,1,2],[0,25,50]])):
        bars=ax.barh(range(4),values,.74,color=[c.GRAY,c.ORANGE,c.GRAY,c.BLUE],
            ec=c.INK,lw=.4,zorder=3)
        for bar,hatch in zip(bars,['///','\\\\','...','xxx']):bar.set_hatch(hatch)
        ax.bar_label(bars,labels=[f'{v:.3f}' if i==0 else f'{v:.1f}' for v in values],padding=2.3,fontsize=6.8,
            bbox={'facecolor':'white','edgecolor':'none','pad':.3})
        ax.set_yticks(range(4),names if i==0 else ['']*4)
        ax.set_ylim(3.55,-.55);ax.set_xlim(0,limit);ax.set_xticks(ticks)
        ax.set_xlabel(xlabel,labelpad=3)
        ax.set_title(title,loc='left',pad=5,fontweight='bold',fontsize=8)
        c.style(ax);ax.tick_params(axis='y',length=0,pad=3)
        ax.spines['left'].set_visible(False)
        if i==0:ax.axvline(1,c='#7E8B98',lw=.55,ls='--',zorder=2)
    for ext in ['pdf','png']:
        fig.savefig(OUT/'measured_figures'/f'intro_evidence.{ext}',dpi=300)
    plt.close(fig)
    data['selected_design']='paired horizontal bars: decode speedup and HDD share; restored colors/hatches'
    data['previous_three_column_alternative']='inherited R18 alternative; not selected or embedded'
    (OUT/'INTRO_FIGURE_DATA.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    (OUT/'INTRO_BAR_DESIGN.json').write_text(json.dumps({'figure':1,'base_style':'original paired horizontal bars',
        'canvas_width_pdf_pt':252,'canvas_height_pdf_pt':162,'bar_height_row_units':.74,
        'x_limits':[2.1,56],'x_axes_start_at_zero':True,'maximum_font_pdf_pt':8,
        'numerical_labels':{'decode':[f'{v:.3f}' for v in speed],'HDD':[f'{v:.1f}' for v in demand]},
        'no_new_metrics_or_runs':True,'colors_and_hatches_restored':True},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
