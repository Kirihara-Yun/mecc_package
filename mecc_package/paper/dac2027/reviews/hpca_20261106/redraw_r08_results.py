"""Reflow unchanged plot data into readable axes at their final paper size."""
import ast
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from redraw_r08_motivation import OUT, PAPER

sys.path.insert(0,str(PAPER))
from build_measured_a100 import load
import build_compact_results as compact
import build_completion_figures as completion


def introduction():
    compact.setup(); data=load()
    controls=[data['main']['naive'],data['main']['swapmoe'],data['independent'],data['main']['ours']]
    fig,axs=plt.subplots(1,2,figsize=(3.45,2.03))
    fig.subplots_adjust(left=.19,right=.96,bottom=.19,top=.87,wspace=.31)
    for ax,key,title,xlabel,limit in zip(axs,['tpot_ms','ssd'],
        ['(a) Decode latency','(b) HDD demand'],['TPOT (s/token)','Demand share (%)'],[43,63]):
        vals=[r['metrics']['hit_pct']['ssd'] if key=='ssd' else r['metrics'][key]/1000 for r in controls]
        bars=ax.barh(range(4),vals,height=.58,color=[compact.GRAY,compact.ORANGE,compact.GRAY,compact.BLUE],ec=compact.INK,lw=.4,zorder=3)
        for bar,hatch in zip(bars,['///','\\\\','...','xxx']):bar.set_hatch(hatch)
        ax.bar_label(bars,labels=[f'{v:.1f}' for v in vals],padding=2,fontsize=6.5)
        ax.set_yticks(range(4),['Streaming','Fixed CPU','Separate','MECC'] if ax is axs[0] else ['']*4)
        ax.invert_yaxis();ax.set_xlim(0,limit);ax.set_xticks([0,20,40] if key=='tpot_ms' else [0,25,50])
        ax.set_xlabel(xlabel,labelpad=2);ax.set_title(title,loc='left',fontweight='bold',pad=4);compact.style(ax)
    for ext in ['pdf','png']:
        fig.savefig(OUT/'measured_figures'/f'intro_evidence.{ext}',dpi=260,bbox_inches='tight',pad_inches=.025)
    plt.close(fig)


def sensitivity():
    # Reuse the existing drawing routine, changing the canvas height only.
    # Its data lookup, axes, labels, and source manifest remain unchanged.
    tree=ast.parse((PAPER/'build_completion_figures.py').read_text(encoding='utf-8'))
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='workload_sensitivity')
    class Taller(ast.NodeTransformer):
        def visit_Tuple(self,n):
            if len(n.elts)==2 and all(isinstance(x,ast.Constant) for x in n.elts) and [x.value for x in n.elts]==[7.1,1.9]:
                return ast.copy_location(ast.Tuple(elts=[ast.Constant(7.1),ast.Constant(2.90)],ctx=ast.Load()),n)
            return self.generic_visit(n)
    node=Taller().visit(node)
    env=dict(vars(completion)); env['OUT']=OUT/'completion_figures'
    def save_local(fig,name,source):
        for ext in ['pdf','png']:
            fig.savefig(OUT/'completion_figures'/f'{name}.{ext}',dpi=280,bbox_inches='tight',pad_inches=.025)
        plt.close(fig)
    env['save']=save_local
    env['plt'].rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],
        'font.size':7.5,'axes.titlesize':8,'axes.labelsize':7.5,'xtick.labelsize':6.8,
        'ytick.labelsize':7,'legend.fontsize':6.2,'axes.linewidth':.5})
    module=ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[]))
    exec(compile(module,'unchanged_sensitivity_data','exec'),env)
    env['workload_sensitivity']()


if __name__=='__main__':
    introduction()
    sensitivity()
