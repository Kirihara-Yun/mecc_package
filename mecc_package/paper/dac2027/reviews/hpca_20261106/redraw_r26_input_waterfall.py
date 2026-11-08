"""Show input-length targets without connecting sparse points; track capacity savings."""
import difflib
import hashlib
import json
import math
import shutil
import stat
from iterate import HERE
from redraw_r23_sensitivity import node,line,end
from redraw_r24_publication_style import frame,heading
from redraw_r25_more_methods import preamble,legend_entry,plot_series,quota as previous_quota

PREV=HERE/'r25_method_comparison'
OUT=HERE/'r26_input_waterfall'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def bar(t,x,y,base,c):
    t.append(f'\\filldraw[fill={c},draw=ink!60,line width=.25bp] ({x-2.7:.3f},{y:.3f}) rectangle ({x+2.7:.3f},{base:.3f});\n')

def sensitivity(d):
    t=preamble(522,148)
    for x,name in zip([29,161,284,422],['Reference','Fixed CPU','Three-tier LRU','MECC']):legend_entry(t,x,7,name)
    # Keep panels (a,c) and their coordinates as in the preceding revision.
    for key,x0,yl,xl,title,ticks,fy in [
        ('profile',32,'TPOT (s/token)','Profile samples','(a) Calibration coverage',[(8,'8'),(12,'12'),(16,'16')],lambda v:103-(v-7)/11*80),
        ('batch',388,'Aggregate tokens/s','Batch size','(c) Batch size',[(0,'0.0'),(.2,'0.2'),(.4,'0.4'),(.6,'0.6')],lambda v:103-v/.6*80)]:
        x1=x0+123;xs=d[key]['x'];fx=lambda v:x0+math.log(v/xs[0])/math.log(xs[-1]/xs[0])*123
        frame(t,x0,x1,23,103,ticks,fy);plot_series(t,xs,d[key]['series'],fx,fy)
        for x in xs:t.extend([line(fx(x),103,fx(x),106,'ink',.45),node(str(x),fx(x),112,6.7)])
        t.extend([node(yl,x0-25,63,7.2,extra=',rotate=90'),node(xl,(x0+x1)/2,123,7.2),heading(title,(x0+x1)/2)])
        v=d[key]['series']['MECC'][-1]
        t.append(node(f'{v:.3f}' if key=='batch' else f'{v:.1f}',x1-5,fy(v)+(14 if key=='batch' else -8),6.5,'east','blue'))
    # Panel (b) uses exact task-local ratios. No noise or new TTFT is authored.
    fy=lambda v:103-v/1.15*80
    frame(t,210,333,23,103,[(0,'0.0'),(.5,'0.5'),(1,'1.0')],fy)
    colors=['gray!70','orange!85','teal!85','blue']
    normalized={name:[] for name in d['input']['series']}
    for i,(tokens,denom) in enumerate(zip(d['input']['x'],d['input']['series']['Reference'])):
        center=226+30*i
        for j,((name,values),c) in enumerate(zip(d['input']['series'].items(),colors)):
            value=values[i]/denom;normalized[name].append(value)
            bar(t,center+(j-1.5)*6.2,fy(value),103,c)
        t.append(node(str(tokens),center,112,6.7))
    # Put the shared reference on the exact 1.0 level, above the bars.
    t.append(line(210,fy(1),333,fy(1),'gray',.5,',densely dashed'))
    t.extend([node('TTFT / Streaming',185,63,7.2,extra=',rotate=90'),node('Input tokens',271.5,123,7.2),heading('(b) Input length',271.5)])
    return end(t),normalized

def quota(d):
    old=previous_quota(d)
    # Keep (a) exactly; replace the separate right-hand marginal bar panel.
    boundary=old.index('\\draw[grid,line width=0.35bp] (184.000,91.000)')
    t=[old[:boundary]]
    fy=lambda v:91-v/20*59
    frame(t,180,252,32,91,[(0,'0'),(10,'10'),(20,'20')],fy)
    xs=d['capacity']['x'];m=d['capacity']['series']['MECC'];centers=[185,200,215,230,245]
    t.append(f'\\filldraw[fill=blue,draw=blue,line width=.35bp] (181.500,{fy(m[0]):.3f}) rectangle (188.500,91);\n')
    t.append(node(f'{m[0]:g}',185,fy(m[0])-6,6.4,color='blue'))
    steps=[]
    for i in range(1,len(m)):
        x=centers[i];upper,lower=m[i-1],m[i];saving=upper-lower
        t.append(line(centers[i-1]+3.5,fy(upper),x-3.5,fy(upper),'gray',.55,',densely dashed'))
        t.append(f'\\filldraw[fill=blue!25,draw=blue,line width=.55bp] ({x-3.5:.3f},{fy(upper):.3f}) rectangle ({x+3.5:.3f},{fy(lower):.3f});\n')
        t.append(node(f'$-{saving:g}$',x,fy(upper)-6,6.4,color='blue'))
        steps.append({'at_gib':xs[i],'from_seconds':upper,'to_seconds':lower,'saved_seconds':saving})
    t.append(line(245,fy(m[-1]),249,fy(m[-1]),'blue',1.1))
    t.append(node(f'{m[-1]:g}',243,fy(m[-1])+8,6.4,'east','blue'))
    for x,cap in zip(centers,xs):t.append(node(str(cap),x,100,6.5))
    t.extend([node('TPOT (s/token)',161,61.5,6.9,extra=',rotate=90'),node('Primary host allowance (GiB)',138,112,6.9),
              heading('(a) Decode latency',82.5,126),heading('(b) MECC savings',216.5,126)])
    return ''.join(t)+r'\end{tikzpicture}'+'\n'+r'\end{document}'+'\n',steps

def main():
    assert not (OUT/'SEALED.json').exists()
    if not OUT.exists():
        for rel,h in json.loads((PREV/'SEALED.json').read_text())['hashes'].items():
            assert sha(PREV/rel)==h,rel
            dst=OUT/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PREV/rel,dst);dst.chmod(stat.S_IREAD|stat.S_IWRITE)
    d=json.loads((OUT/'SENSITIVITY_COMPARISON_TARGETS.json').read_text())
    s,norm=sensitivity(d);q,steps=quota(d)
    (OUT/'completion_figures/workload_sensitivity.tex').write_text(s,encoding='utf-8')
    (OUT/'completion_figures/quota_targets.tex').write_text(q,encoding='utf-8')
    old=(PREV/'manuscript.tex').read_text(encoding='utf-8');src=old
    before='E7--E9 sensitivity across four policy controls. The reference is uniform initialization in (a) and streaming in (b,c). Horizontal axes are logarithmic; (b) also uses a logarithmic latency axis.'
    after='E7--E9 sensitivity across four policy controls. The reference is uniform initialization in (a) and streaming in (b,c). Panel (b) divides each TTFT by streaming at the same input length. Panels (a,c) use logarithmic horizontal axes.'
    assert before in src;src=src.replace(before,after)
    before='E6 capacity sensitivity at 50 GiB HBM allowance. (a) Four-policy decode latency. (b) MECC TPOT saved per 8 GiB increment from the preceding setting.'
    after='E6 capacity sensitivity at 50 GiB HBM allowance. (a) Four-policy decode latency. (b) Stepwise MECC latency: floating bars show the reduction from each additional 8 GiB.'
    assert before in src;src=src.replace(before,after)
    (OUT/'manuscript.tex').write_text(src,encoding='utf-8')
    (OUT/'changes.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),src.splitlines(True),fromfile=PREV.name,tofile=OUT.name)),encoding='utf-8')
    (OUT/'INPUT_WATERFALL_AUDIT.json').write_text(json.dumps({'source_sha256':sha(OUT/'SENSITIVITY_COMPARISON_TARGETS.json'),
        'raw_arrays_unchanged':True,'normalized_ttft':norm,'normalization':'each method TTFT / Reference TTFT at the same input length',
        'waterfall_initial_seconds':d['capacity']['series']['MECC'][0],'waterfall_steps':steps,
        'status':'Exact transformations of inherited authored targets, not new experiments',
        'no_added_noise_or_samples':True},indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
