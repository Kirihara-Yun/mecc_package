"""Extend the R17 figure style by one measured first-token column."""
import hashlib
import json
import re
import shutil
import stat
import sys
from iterate import HERE,PAPER

PREV=HERE/'r19_intro_bars'
STYLE=HERE/'r17_figure_type'
OUT=HERE/'r20_three_columns'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (OUT/'SEALED.json').exists()
    if not OUT.exists():
        for rel,h in json.loads((PREV/'SEALED.json').read_text())['hashes'].items():
            assert sha(PREV/rel)==h,rel
            target=OUT/rel;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(PREV/rel,target);target.chmod(stat.S_IREAD|stat.S_IWRITE)
    text=(PREV/'manuscript.tex').read_text(encoding='utf-8')
    assert 'Decode speedup is relative to streaming;' in text
    text=text.replace('Decode speedup is relative to streaming;', 'Speedups are relative to streaming;',1)
    (OUT/'manuscript.tex').write_text(text,encoding='utf-8')
    sys.path.insert(0,str(PAPER))
    import matplotlib.pyplot as plt
    import pymupdf
    import build_compact_results as c
    c.setup()
    regular=9*72/72.27
    numbers=6.826
    plt.rcParams.update({'font.size':regular,'axes.titlesize':regular,'axes.labelsize':regular,
        'xtick.labelsize':regular,'ytick.labelsize':regular,'hatch.linewidth':.6})
    d=json.loads((PREV/'INTRO_FIGURE_DATA.json').read_text())
    speed=d['decode_speedups'];first=d['first_token_speedups']
    hdd=[row['shares_hbm_cpu_hdd'][2] for row in d['rows']]
    f=pymupdf.open(STYLE/'measured_figures/intro_evidence.pdf')
    height=f[0].rect.height*252/f[0].rect.width;f.close()
    fig=plt.figure(figsize=(3.5,height/72))
    configs=[(speed,'(a) Decode','Speedup (×)',2.45,[0,1,2]),
        (first,'(b) First token','Speedup (×)',1.7,[0,1]),
        (hdd,'(c) HDD','Share (%)',64,[0,25,50])]
    for i,(values,title,xlabel,limit,ticks) in enumerate(configs):
        ax=fig.add_axes([.205+i*.265,.22,.205,.66])
        bars=ax.barh(range(4),values,.58,color=[c.GRAY,c.ORANGE,c.GRAY,c.BLUE],ec=c.INK,lw=.4,zorder=3)
        for bar,hatch in zip(bars,['///','\\\\','...','xxx']):bar.set_hatch(hatch)
        ax.bar_label(bars,labels=[f'{v:.3f}' if i<2 else f'{v:.1f}' for v in values],padding=1.6,
            fontsize=numbers,bbox={'fc':'white','ec':'none','pad':.15})
        ax.set_ylim(3.55,-.55);ax.set_xlim(0,limit);ax.set_xticks(ticks)
        ax.set_yticks(range(4),['Streaming','Swap-style','Separate','MECC'] if i==0 else ['']*4)
        ax.set_title(title,loc='left',pad=5,fontweight='bold',fontsize=regular)
        ax.set_xlabel(xlabel,labelpad=3,fontsize=regular)
        c.style(ax)
        if i<2:ax.axvline(1,c='#7E8B98',lw=.5,ls='--',zorder=2)
    for ext in ['pdf','png']:
        fig.savefig(OUT/'measured_figures'/f'intro_evidence.{ext}',dpi=320)
    plt.close(fig)
    audit={'style_source':'R17, after reducing oversized type','style_source_sha256':sha(STYLE/'measured_figures/intro_evidence.pdf'),
        'panels':['decode speedup','first-token speedup','HDD demand share'],
        'added_panel':'first-token speedup = streaming TTFT / policy TTFT',
        'decode_speedups':speed,'first_token_speedups':first,'HDD_shares':hdd,
        'source_rows':d['rows'],'regular_font_pdf_pt':regular,'value_font_pdf_pt':numbers,
        'colors_and_hatches_from_original':True,'bar_height_row_units':.58,
        'no_new_runs_or_targets':True,'canvas_height_pdf_pt':height}
    (OUT/'THREE_COLUMN_DATA.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    d['selected_design']='R17 font-adjusted horizontal bars, extended with a first-token speedup column'
    d['panel_order']=['decode speedup','first-token speedup','HDD demand share']
    (OUT/'INTRO_FIGURE_DATA.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
