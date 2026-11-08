"""Draw Fig. 5 with the manuscript's exact LaTeX text and math font packages."""
import hashlib
import json
import shutil
import stat
from iterate import HERE

PREV=HERE/'r20_three_columns'
OUT=HERE/'r21_state_figure'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def expert(name):return '$a_'+name[1:]+'$'


def main():
    assert not OUT.exists()
    for rel,digest in json.loads((PREV/'SEALED.json').read_text())['hashes'].items():
        assert sha(PREV/rel)==digest,rel
        dst=OUT/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(PREV/rel,dst);dst.chmod(stat.S_IREAD|stat.S_IWRITE)
    trace=json.loads((OUT/'TRANSITION_AUDIT.json').read_text())
    states=trace['continuous_trace'];initial=states[0]
    assert [x['request'] for x in states[1:]]==['a2','a3','a5']
    assert states[-1]['hbm_mru_to_lru']==['a5','a3'] and states[-1]['cpu_mru_to_lru']==['a2','a1']
    removed=[]
    for previous,current in zip(states,states[1:]):
        before=set(previous['hbm_mru_to_lru']+previous['cpu_mru_to_lru'])
        after=set(current['hbm_mru_to_lru']+current['cpu_mru_to_lru'])
        removed.append(sorted(before-after))
    assert removed==[[],[],['a4']]
    preamble=r'''\documentclass[tikz,border=0pt]{standalone}
\usepackage[T1]{fontenc}
\usepackage{newtxtext,newtxmath}
\usepackage{xcolor}
\definecolor{hbm}{HTML}{326C9B}
\definecolor{cpu}{HTML}{6D9FAD}
\definecolor{ink}{HTML}{203244}
\definecolor{rule}{HTML}{DFE6EC}
\begin{document}
\begin{tikzpicture}[x=1bp,y=-1bp,every node/.style={inner sep=0pt,outer sep=0pt,text=ink,font=\fontsize{7.2}{8.4}\selectfont}]
\path[use as bounding box] (0,0) rectangle (252,115.92);
\node[anchor=west,font=\fontsize{7.5}{9}\selectfont] at (5,7)
  {Initial: HBM $[a_1,a_2]$, CPU $[a_3,a_4]$};
\node[anchor=west,font=\fontsize{7.5}{9}\selectfont\bfseries] at (6,23) {Request};
\node[text=hbm,font=\fontsize{7.5}{9}\selectfont\bfseries] at (130.5,23) {HBM};
\node[text=cpu,font=\fontsize{7.5}{9}\selectfont\bfseries] at (215.5,23) {CPU};
\node[font=\fontsize{6.5}{7.5}\selectfont] at (130.5,33) {MRU $\rightarrow$ LRU};
\node[font=\fontsize{6.5}{7.5}\selectfont] at (215.5,33) {MRU $\rightarrow$ LRU};
\draw[rule,line width=.35bp] (5,38) -- (246,38);
\draw[rule,line width=.3bp] (5,62) -- (246,62);
\draw[rule,line width=.3bp] (5,88) -- (246,88);
'''
    lines=[preamble];note_text=['HBM hit','CPU hit',r'HDD read; evict $a_4$']
    for i,(state,y) in enumerate(zip(states[1:],[49,75,101])):
        lines.append(r'\node[anchor=west] at (6,'+str(y-3)+') {'+str(i+1)+'. '+expert(state['request'])+'};\n')
        lines.append(r'\node[anchor=west,font=\fontsize{6.5}{7.5}\selectfont] at (6,'+str(y+6.5)+') {'+note_text[i]+'};\n')
        for tier,xs,key in [('hbm',[116,145],'hbm_mru_to_lru'),('cpu',[201,230],'cpu_mru_to_lru')]:
            for x,name in zip(xs,state[key]):
                lines.append(r'\fill['+tier+'] ('+str(x-13.5)+','+str(y-7.5)+') rectangle ('+str(x+13.5)+','+str(y+7.5)+');\n')
                lines.append(r'\node[text=white,font=\fontsize{8}{8}\selectfont] at ('+str(x)+','+str(y)+') {'+expert(name)+'};\n')
    lines.append('\\end{tikzpicture}\n\\end{document}\n')
    (OUT/'method_redesign/residency_cases.tex').write_text(''.join(lines),encoding='utf-8')
    (OUT/'STATE_FIGURE_AUDIT.json').write_text(json.dumps({'source_trace_sha256':sha(OUT/'TRANSITION_AUDIT.json'),
        'continuous_states':states,'removed_experts_by_step':removed,'font_packages':['newtxtext','newtxmath'],
        'same_font_packages_as_manuscript':True,'expert_blocks_per_row':4,'standalone_eviction_block':False,
        'eviction_note_location':'request column, third row','diagram_extent_bp':[252,115.92],
        'no_policy_or_measurement_changes':True},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
