"""Generate figures from explicit protocols and execute the actual cache transitions."""
import ast,hashlib,json,sys,textwrap
from collections import OrderedDict
from iterate import HERE

OUT=HERE/'r12_protocols';PAPER=HERE.parent.parent;PKG=HERE.parents[3]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def transitions():
    # Execute the unmodified access/eviction methods on symbolic weights; no GPU or torch needed.
    policy=PKG/'e2e/policy_plugin.py';engine=PKG/'e2e/tiered_engine.py'
    cls=next(n for n in ast.parse(policy.read_text(encoding='utf-8')).body if isinstance(n,ast.ClassDef) and n.name=='OursPolicy')
    cls.bases=[];cls.decorator_list=[]
    cache_cls=next(n for n in ast.parse(engine.read_text(encoding='utf-8')).body if isinstance(n,ast.ClassDef) and n.name=='LayerExpertCache')
    eviction=next(n for n in cache_cls.body if isinstance(n,ast.FunctionDef) and n.name=='_evict_gpu_if_needed')
    ns={};tree=ast.fix_missing_locations(ast.Module(body=[cls,eviction],type_ignores=[]))
    exec(compile(tree,'actual_mecc_transition_methods','exec'),ns)
    class Weight:
        def __init__(self,name):self.name=name
        def pin(self):return self
    class Cache:
        _evict_gpu_if_needed=ns['_evict_gpu_if_needed']
        def __init__(self):
            self.k_h=self.k_c=2;self.hits=[0,0,0,0]
            self.gpu=OrderedDict((e,(Weight(e),Weight(e))) for e in ['a2','a1'])
            self.cpu=OrderedDict((e,Weight(e)) for e in ['a4','a3'])
        def _to_gpu(self,w):return Weight(w.name)
        def consume_nearmiss(self,uid):return None
        def _load_from_ssd(self,uid):return Weight(uid)
        def state(self):return {'hbm_mru_to_lru':list(reversed(self.gpu)),'cpu_mru_to_lru':list(reversed(self.cpu))}
    c=Cache();trace=[{'request':'initial',**c.state()}];p=ns['OursPolicy']()
    for req in ['a2','a3','a5']:
        p.access(c,req)
        assert not set(c.gpu).intersection(c.cpu)
        trace.append({'request':req,**c.state()})
    assert trace[-1]['hbm_mru_to_lru']==['a5','a3']
    assert trace[-1]['cpu_mru_to_lru']==['a2','a1']
    assert trace[2]['cpu_mru_to_lru']==['a1','a4']
    independent=[]
    for req in ['a2','a3','a5']:
        c=Cache();p.access(c,req);independent.append({'request':req,**c.state()})
    (OUT/'TRANSITION_AUDIT.json').write_text(json.dumps({'method_source_sha256':{str(policy.relative_to(PKG)):sha(policy),str(engine.relative_to(PKG)):sha(engine)},
        'execution':'actual access/eviction AST methods on symbolic weights; CPU logic only',
        'continuous_trace':trace,'previous_independent_cases':independent,'case_exclusion_verified':True},indent=2)+'\n',encoding='utf-8')
    return trace


def main():
    assert not (OUT/'SEALED.json').exists()
    sys.path.insert(0,str(PAPER))
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    import numpy as np
    import build_compact_results as c
    c.setup()
    def save(fig,folder,name):
        for ext in ['pdf','png']:
            fig.savefig(OUT/folder/f'{name}.{ext}',dpi=280,bbox_inches='tight',pad_inches=.025)
        plt.close(fig)
    # Retain E1's observations, with an extra digit to reduce round-again ambiguity.
    from build_measured_a100 import load
    d=load();m=d['main'];ref=m['naive']['metrics']
    parent=(HERE/'build_r10_figures.py').read_text(encoding='utf-8')
    code=textwrap.dedent(parent[parent.index("    controls=[m['naive']"):parent.index("    order=['naive'")])
    code=code.replace("f'{v:.2f}'","f'{v:.3f}'")
    def save_intro(fig,name):save(fig,'measured_figures',name)
    exec(compile(code,'r12_E1_intro_precision','exec'),{'compact':c,'m':m,'d':d,'ref':ref,'plt':plt,'OUT':OUT,'save':save_intro})
    parent=(HERE/'build_r11_figures.py').read_text(encoding='utf-8')
    code=textwrap.dedent(parent[parent.index("    order=['naive'"):parent.index('    # The framework layout')])
    code=code.replace("f'{v:.2f}'","f'{v:.3f}'")
    exec(compile(code,'r12_E1_precision','exec'),{'c':c,'m':m,'ref':ref,'plt':plt,'OUT':OUT})
    trace=transitions()
    fig,ax=plt.subplots(figsize=(3.45,1.56));fig.subplots_adjust(0,0,1,1)
    ax.set(xlim=(0,10),ylim=(0,5));ax.axis('off')
    ax.text(.15,4.65,'Start: HBM [a₁, a₂]   CPU [a₃, a₄]',weight='bold',color=c.INK)
    ax.text(3.36,4.05,'HBM',ha='center',weight='bold',color=c.BLUE)
    ax.text(6.5,4.05,'CPU',ha='center',weight='bold',color=c.TEAL)
    for i,row in enumerate(trace[1:]):
        y=2.95-i*1.10
        req=row['request'].replace('2','₂').replace('3','₃').replace('5','₅')
        ax.text(.2,y+.31,f'{i+1}. Request '+req,va='center',fontsize=7.2)
        for ids,x,col in [(row['hbm_mru_to_lru'],2.45,c.BLUE),(row['cpu_mru_to_lru'],5.6,c.TEAL)]:
            for j,e in enumerate(ids):
                ax.add_patch(Rectangle((x+j*.94,y),.9,.63,fc=col,ec='white',lw=.8))
                ax.text(x+j*.94+.45,y+.315,'$a_'+e[1:]+'$',ha='center',va='center',fontsize=8.5,color='white')
        if i<2:
            ax.annotate('',xy=(1.05,y-.42),xytext=(1.05,y-.05),arrowprops={'arrowstyle':'->','lw':.7,'color':c.INK})
        if i==2:
            ax.add_patch(Rectangle((8.35,y),.83,.63,fc='#E9EDF0',ec='white'))
            ax.text(8.765,y+.315,'$a_4$',ha='center',va='center',fontsize=8.5)
            ax.text(8.76,y-.25,'Evict',ha='center',fontsize=6.4)
    ax.plot([4.9,4.9],[.5,3.85],c='#B9C4CC',lw=.7,ls='--')
    for x in [3.35,6.5]:ax.text(x,.1,'MRU → LRU',ha='center',fontsize=6.5)
    save(fig,'method_redesign','residency_cases')
    A=json.loads((OUT/'ideal_assumptions.json').read_text())
    # Add labels to every E2 bar; show the fixed-host, independent, and joint controls explicitly.
    fig,axs=plt.subplots(1,3,figsize=(7.1,1.78));fig.subplots_adjust(.055,.27,.985,.83,wspace=.31)
    for ax,key,title in zip(axs,['placement_same_runtime','retention_same_initial_plan','adaptation_same_initial_plan'],
        ['(a) E2: Placement','(b) E2: Retention','(c) E2: Adaptation']):
        x=np.arange(3)
        for j,((name,vals),col,hatch) in enumerate(zip(A['insight_ablation_targets'][key].items(),[c.GRAY,c.ORANGE,c.BLUE],['...','///','xxx'])):
            bars=ax.bar(x+(j-1)*.23,vals,.21,color=col,ec=c.INK,lw=.35,hatch=hatch,label=name,zorder=3)
            ax.bar_label(bars,labels=[f'{v:.1f}' for v in vals],padding=1.5,fontsize=6.2,rotation=90)
        ax.set_xticks(x,['Mixtral\n8×7B','Qwen2\n57B-A14B','Mixtral\n8×22B']);ax.set_ylim(0,100)
        c.style(ax,'y');ax.set_ylabel('TPOT (s/token)',labelpad=2)
        t=ax.set_title(title,loc='left',pad=4);t.set_bbox({'facecolor':'#FFF19A','edgecolor':'none','pad':1.2})
        ax.legend(loc='upper left',frameon=False,fontsize=5.8,handlelength=1,labelspacing=.15)
    save(fig,'completion_figures','mechanism_sweeps')
    # Preserve the cross-model values and display their workload/protocol identities.
    fig,ax=plt.subplots(figsize=(3.45,1.85));fig.subplots_adjust(.14,.29,.98,.77)
    x=np.arange(4)
    for offset,key,col,hatch,label in [(-.14,'Unoptimized streaming',c.GRAY,'...','Streaming'),(.14,'MECC',c.BLUE,'xxx','MECC')]:
        ax.bar(x+offset,A['tpot_seconds'][key],.26,color=col,ec=c.INK,lw=.35,hatch=hatch,label=label,zorder=3)
    ax.set_xticks(x,['8×7B\nGSM8K','8×7B\nHumanEval','8×22B\nGSM8K','8×22B\nHumanEval']);ax.set_ylim(0,72)
    c.style(ax,'y');ax.set_ylabel('TPOT (s/token)',labelpad=2);ax.legend(frameon=False,ncol=2,loc='upper left',handlelength=1)
    t=ax.set_title('E3: Calibrated model/workload comparison',loc='left',pad=4,fontsize=7.5)
    t.set_bbox({'facecolor':'#FFF19A','edgecolor':'none','pad':1.2});save(fig,'completion_figures','cross_model')
    B=json.loads((OUT/'BASELINE_TARGETS.json').read_text())
    fig,axs=plt.subplots(1,2,figsize=(3.45,1.92));fig.subplots_adjust(left=.28,right=.96,bottom=.24,top=.83,wspace=.35)
    names=['MoE-CORE','MoE-Infinity','SSD-LLaMA','FlashMoE-RF','MECC']
    for i,(ax,key,title) in enumerate(zip(axs,['decode_relative_latency','first_token_relative_latency'],['(a) E5: Decode','(b) E5: First token'])):
        bars=ax.barh(range(5),B[key],height=.6,color=[c.GRAY,c.GRAY,c.TEAL,c.ORANGE,c.BLUE],ec=c.INK,lw=.4,zorder=3)
        for bar,hatch in zip(bars,['...','///','+++','\\\\','xxx']):bar.set_hatch(hatch)
        ax.bar_label(bars,labels=[f'{v:.2f}' for v in B[key]],padding=2,fontsize=6.0)
        ax.set_yticks(range(5),names if i==0 else ['']*5);ax.invert_yaxis();ax.set_xlim(0,1.95)
        ax.set_xticks([0,1,1.5]);ax.set_xlabel('Relative latency',labelpad=2);c.style(ax)
        t=ax.set_title(title,loc='left',pad=4,fontsize=7.3);t.set_bbox({'facecolor':'#FFF19A','edgecolor':'none','pad':1.2})
    save(fig,'completion_figures','matched_baselines')
    # Startup has a separate online-initialization reference (10 s/token), not the 24 s/token streaming control.
    import build_completion_figures as old
    source=(PAPER/'build_completion_figures.py').read_text(encoding='utf-8')
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='ablation_startup')
    code=ast.unparse(node).replace("'Base' if name == 'reference' else name","'Online init' if name == 'reference' else 'Compiled init'")
    env=dict(vars(old));env['A']=A;env['OUT']=OUT/'completion_figures'
    env['save']=lambda fig,name,record:save(fig,'completion_figures',name)
    exec(compile(code,'r12_startup','exec'),env);env['ablation_startup']()
    (OUT/'FIGURE_PROTOCOLS.json').write_text(json.dumps({'E1':['intro_evidence','main','motivation panel b'],
        'E2':['mechanism_sweeps'],'E3':['ablation_startup','cross_model','traffic_exposure'],'E4':['measured capacity paragraph'],
        'E5':['matched_baselines'],'E3_startup_reference':'online initialization, 10 s/token; separate from the 24 s/token streaming base',
        'target_arrays_modified':False,'baseline_targets':'BASELINE_TARGETS.json; authored, not measured'},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
