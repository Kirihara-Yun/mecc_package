"""Redesign Figs. 13/14 without changing their source arrays."""
import difflib
import hashlib
import json
import math
import shutil
import stat
from iterate import HERE

PREV=HERE/'r22_recency_tracks'
OUT=HERE/'r23_sensitivity_design'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def start(w,h):
    return [r'''\documentclass[tikz,border=0pt]{standalone}
\usepackage[T1]{fontenc}
\usepackage{newtxtext,newtxmath}
\usepackage{xcolor}
\definecolor{blue}{HTML}{326C9B}
\definecolor{gray}{HTML}{9AA7B2}
\definecolor{ink}{HTML}{203244}
\definecolor{grid}{HTML}{E7EBEF}
\definecolor{yellow}{HTML}{FFF19A}
\begin{document}
\begin{tikzpicture}[x=1bp,y=-1bp,every node/.style={inner sep=0pt,outer sep=0pt,text=ink,font=\fontsize{7.2}{8.2}\selectfont}]
''',f'\\path[use as bounding box] (0,0) rectangle ({w},{h});\n']

def node(t,x,y,s=7.2,anchor='center',color='ink',extra=''):
    return f'\\node[anchor={anchor},text={color},font=\\fontsize{{{s}}}{{{s+1}}}\\selectfont{extra}] at ({x:.3f},{y:.3f}) {{{t}}};\n'

def line(x0,y0,x1,y1,c='grid',lw=.4,extra=''):
    return f'\\draw[{c},line width={lw}bp{extra}] ({x0:.3f},{y0:.3f})--({x1:.3f},{y1:.3f});\n'

def mark(x,y,c='blue',square=False,r=2.4):
    if square:return f'\\fill[{c}] ({x-r:.3f},{y-r:.3f}) rectangle ({x+r:.3f},{y+r:.3f});\n'
    return f'\\filldraw[fill={c},draw=white,line width=.45bp] ({x:.3f},{y:.3f}) circle[radius={r}bp];\n'

def title(t,x):return node(t,x,7,8.2,'west',extra=',fill=yellow,inner xsep=1.5bp,inner ysep=1.2bp')

def legend(x,label,y=21):
    return mark(x,y,'gray',True,2)+node(label,x+5,y,6.5,'west')+mark(x+71,y,'blue',False,2.2)+node('MECC',x+76,y,6.5,'west')

def end(lines):return ''.join(lines)+r'\end{tikzpicture}'+'\n'+r'\end{document}'+'\n'

def sensitivity(n):
    t=start(522,159)
    t += [title('(a) Calibration coverage',2),title('(b) Input length',183),title('(c) Batch size',364)]
    # Discrete profile sizes: paired endpoints avoid an empty zero-to-eight band.
    t += [legend(36,'Uniform')]
    ys=[42,65,88,111];xmin,xmax=7.5,12.5
    px=lambda v:36+(v-xmin)/(xmax-xmin)*119
    for v in [8,10,12]:
        x=px(v);t += [line(x,32,x,124),line(x,124,x,127,'ink',.45),node(str(v),x,134,6.7)]
    t += [line(36,124,155,124,'ink',.5),node('TPOT (s/token)',95.5,151,7.3),node('Profile samples',7,77,7.2,extra=',rotate=90')]
    for samples,b,m,y in zip(n['profile_samples'],n['profile_tpot_uniform'],n['profile_tpot_mecc'],ys):
        t += [line(36,y,155,y,'grid',.25),node(str(samples),29,y,6.8,'east'),
              line(px(m),y,px(b),y,'gray!55',1.6),mark(px(b),y,'gray',True),mark(px(m),y),
              node(f'{m:.1f}',px(m)-4,y-6,6.6,'east','blue')]
    t += [node('12.0',px(12),32.5,6.5,color='gray')]
    # Logarithmic axes expose all four input sizes and their cost growth.
    t += [legend(219,'Streaming')]
    bx0,bx1,by0,by1=216,337,33,124
    fx=lambda v:bx0+math.log(v/32,4)/3*(bx1-bx0)
    fy=lambda v:by1-math.log10(v/10)/math.log10(400)*(by1-by0)
    for v in [10,100,1000]:
        y=fy(v);t += [line(bx0,y,bx1,y),node(str(v),bx0-5,y,6.6,'east')]
    for v in n['input_tokens']:
        x=fx(v);t += [line(x,by1,x,by1+3,'ink',.45),node(str(v),x,134,6.7)]
    t += [line(bx0,by0,bx0,by1,'ink',.5),line(bx0,by1,bx1,by1,'ink',.5),
          node('Input tokens (log scale)',(bx0+bx1)/2,151,7.3),node('TTFT (s, log scale)',187,78,7.2,extra=',rotate=90')]
    for key,c,sq in [('input_ttft_streaming','gray',True),('input_ttft_mecc','blue',False)]:
        coords=[(fx(x),fy(v)) for x,v in zip(n['input_tokens'],n[key])]
        for (x0,y0),(x1,y1) in zip(coords,coords[1:]):t += [line(x0,y0,x1,y1,c,1,',dashed' if sq else '')]
        for x,y in coords:t += [mark(x,y,c,sq)]
        x,y=coords[-1]
        t += [node(str(n[key][-1]),x-1,y+(-7 if sq else 8),6.5,'center',c)]
    # Batches are discrete settings: grouped bars show aggregate work per second.
    t += [legend(393,'Streaming')]
    cx0,cx1,cy0,cy1=390,517,33,124
    fy=lambda v:cy1-v/.56*(cy1-cy0)
    for v,label in [(0,'0'),(.25,'0.25'),(.5,'0.50')]:
        y=fy(v);t += [line(cx0,y,cx1,y),node(label,cx0-5,y,6.6,'east')]
    t += [line(cx0,cy1,cx1,cy1,'ink',.5),node('Aggregate tokens/s',366,78,7.2,extra=',rotate=90'),node('Batch size',453.5,151,7.3)]
    for i,(b,m,bs) in enumerate(zip(n['batch_throughput_streaming'],n['batch_throughput_mecc'],n['batch_sizes'])):
        x=402+33*i
        for val,col,off in [(b,'gray',-4.7),(m,'blue',4.7)]:
            t += [f'\\fill[{col}] ({x+off-3.8:.3f},{fy(val):.3f}) rectangle ({x+off+3.8:.3f},{cy1});\n']
        t += [node(str(bs),x,134,6.7),node(f'{m:.3f}',x+4.7,fy(m)-6,6.2,color='blue')]
    return end(t)

def quota(a):
    t=start(252,104)
    t += [title('Host-memory allowance',2),legend(70,'Three-tier LRU',19)]
    px=lambda v:44+v/30*196
    for v in [0,10,20,30]:
        x=px(v);t += [line(x,25,x,79),line(x,81,x,84,'ink',.4),node(str(v),x,90,6.7)]
    t += [line(44,81,240,81,'ink',.5),node('TPOT (s/token)',142,99,7.3),node('Host allowance (GiB)',7,51,7.1,extra=',rotate=90')]
    for allowance,b,m,y in zip(a['cpu_budget_gb'],a['budget_tpot_seconds']['Three-tier LRU'],a['budget_tpot_seconds']['MECC'],[29,40,51,62,73]):
        t += [line(44,y,240,y,'grid',.25),node(str(allowance),30,y,6.9,'east'),
              line(px(m),y,px(b),y,'gray!60',1.8),mark(px(b),y,'gray',True),mark(px(m),y),
              node(f'{m:g}',px(m)-5,y,6.8,'east','blue'),node(f'{b:g}',px(b)+5,y,6.8,'west','gray')]
    return end(t)

def main():
    assert not (OUT/'SEALED.json').exists()
    if not OUT.exists():
        for rel,h in json.loads((PREV/'SEALED.json').read_text())['hashes'].items():
            assert sha(PREV/rel)==h,rel
            dst=OUT/rel;dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(PREV/rel,dst);dst.chmod(stat.S_IREAD|stat.S_IWRITE)
    n=json.loads((OUT/'narrative_targets.json').read_text());a=json.loads((OUT/'ideal_assumptions.json').read_text())
    (OUT/'completion_figures/workload_sensitivity.tex').write_text(sensitivity(n),encoding='utf-8')
    (OUT/'completion_figures/quota_targets.tex').write_text(quota(a),encoding='utf-8')
    old=(PREV/'manuscript.tex').read_text(encoding='utf-8');s=old
    before=r'E7--E9 profile, input-length, and batch sensitivity. Profile size changes initialization quality, input length changes first-token work, and batch size changes aggregate throughput. The panels vary one workload parameter at a time.'
    after=r'E7--E9 workload sensitivity. (a) Paired decode latencies under uniform and profile-based initialization. (b) First-token latency on logarithmic axes. (c) Aggregate throughput at each batch size.'
    assert before in s;s=s.replace(before,after)
    before=r'E6 decode latency across primary host allowances; HBM allowance is 50 GiB.'
    after=r'E6 decode latency at each primary host allowance. Paired endpoints compare MECC with three-tier LRU; HBM allowance is 50 GiB.'
    assert before in s;s=s.replace(before,after)
    (OUT/'manuscript.tex').write_text(s,encoding='utf-8')
    (OUT/'changes.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile=PREV.name,tofile=OUT.name)),encoding='utf-8')
    (OUT/'SENSITIVITY_DESIGN_AUDIT.json').write_text(json.dumps({'source_hashes':{r:sha(OUT/r) for r in ['narrative_targets.json','ideal_assumptions.json']},
        'data_unchanged':True,'target_highlight_preserved':True,
        'figure13':{'a':'paired horizontal latency endpoints; uniform=12 s/token','b':'log-log TTFT; all original values retained','c':'grouped aggregate-throughput bars'},
        'figure14':'paired latency endpoints at five primary host allowances',
        'new_measurements':False,'font_packages':['newtxtext','newtxmath']},indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
