"""Expand the marked sensitivity planning figures with explicit method targets."""
import difflib
import hashlib
import json
import math
import shutil
import stat
from iterate import HERE
from redraw_r23_sensitivity import start,node,line,end
from redraw_r24_publication_style import frame,heading

PREV=HERE/'r24_publication_style'
OUT=HERE/'r25_method_comparison'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

STYLES={
    'Reference':('gray','square',',dashed'),
    'Streaming':('gray','square',',dashed'),
    'Fixed CPU':('orange','triangle',',dash pattern=on 4bp off 1.5bp'),
    'Three-tier LRU':('teal','diamond',',dash pattern=on 1bp off 1.5bp'),
    'MECC':('blue','circle','')}

def preamble(w,h):
    t=start(w,h)
    t[0]=t[0].replace('{9AA7B2}','{7F8993}').replace('{E7EBEF}','{E5EAF0}')
    t[0]=t[0].replace(r'\begin{document}',r'\definecolor{orange}{HTML}{BD8547}'+'\n'+r'\definecolor{teal}{HTML}{488E85}'+'\n'+r'\begin{document}')
    return t

def marker(x,y,c,shape):
    if shape=='square':path=f'({x-2:.3f},{y-2:.3f}) rectangle ({x+2:.3f},{y+2:.3f})'
    elif shape=='triangle':path=f'({x:.3f},{y-2.6:.3f})--({x-2.4:.3f},{y+1.8:.3f})--({x+2.4:.3f},{y+1.8:.3f})--cycle'
    elif shape=='diamond':path=f'({x:.3f},{y-2.7:.3f})--({x-2.4:.3f},{y:.3f})--({x:.3f},{y+2.7:.3f})--({x+2.4:.3f},{y:.3f})--cycle'
    else:path=f'({x:.3f},{y:.3f}) circle[radius=2.5bp]'
    fill='white' if shape=='square' else c
    return f'\\filldraw[fill={fill},draw={c if shape=="square" else "white"},line width=.65bp] '+path+';\n'

def legend_entry(t,x,y,label,name=None,size=6.8):
    c,shape,dash=STYLES[name or label]
    t.extend([line(x,y,x+13,y,c,1.1,dash),marker(x+6.5,y,c,shape),node(label,x+19,y,size,'west')])

def plot_series(t,xs,values,fx,fy):
    for name,ys in values.items():
        c,shape,dash=STYLES[name];coords=[(fx(x),fy(v)) for x,v in zip(xs,ys)]
        for (x0,y0),(x1,y1) in zip(coords,coords[1:]):t.append(line(x0,y0,x1,y1,c,1.2 if name=='MECC' else .95,dash))
        for x,y in coords:t.append(marker(x,y,c,shape))

def targets(n,a):
    return {
        'status':'AUTHORED UNMEASURED DESIGN TARGETS; NOT BENCHMARK EXECUTIONS; NOT FOR SUBMISSION',
        'purpose':'Four-method layout and sensitivity experiment planning; not evidence of relative performance.',
        'definitions':{
            'Reference':'E7 uses the inherited uniform-initialization control; E8/E9 use inherited streaming targets.',
            'Fixed CPU':'Candidate local fixed-host-membership control with GPU replacement; not published SwapMoE system performance.',
            'Three-tier LRU':'Candidate local unprofiled per-tier LRU control; retains the inherited E6 legacy series.',
            'MECC':'Inherited authored targets, not new measurements.'},
        'profile':{'x':n['profile_samples'],'metric':'TPOT s/token','series':{
            'Reference':n['profile_tpot_uniform'],'Fixed CPU':[15.0,14.0,13.4,13.0],
            'Three-tier LRU':[16.4,15.4,14.6,14.0],'MECC':n['profile_tpot_mecc']}},
        'input':{'x':n['input_tokens'],'metric':'TTFT seconds','series':{
            'Reference':n['input_ttft_streaming'],'Fixed CPU':[39,139,545,2150],
            'Three-tier LRU':[35,122,470,1840],'MECC':n['input_ttft_mecc']}},
        'batch':{'x':n['batch_sizes'],'metric':'aggregate tokens/s','series':{
            'Reference':n['batch_throughput_streaming'],'Fixed CPU':[1/13,.137,.225,.310],
            'Three-tier LRU':[1/14,.145,.258,.390],'MECC':n['batch_throughput_mecc']}},
        'capacity':{'x':a['cpu_budget_gb'],'metric':'TPOT s/token','series':{
            'Streaming':[24,24,24,24,24],'Fixed CPU':[23,18,15,13,11.5],
            'Three-tier LRU':a['budget_tpot_seconds']['Three-tier LRU'],'MECC':a['budget_tpot_seconds']['MECC']}},
        'authorship':'All new Fixed CPU and Three-tier LRU sweep values, and the capacity Streaming series, are explicitly authored planning values. They are not extrapolated measured results.',
        'anchors':'At 40 GiB, capacity MECC=8, Fixed CPU=13 and Three-tier LRU=14 match the 2048-sample profile endpoints and reciprocal batch-one rates. Streaming=24 matches the inherited E3 GSM8K target.',
        'source_hashes':{r:sha(OUT/r) for r in ['narrative_targets.json','ideal_assumptions.json','EXPERIMENT_TARGETS.json']}}

def sensitivity(d):
    t=preamble(522,148)
    for x,name in zip([29,161,284,422],['Reference','Fixed CPU','Three-tier LRU','MECC']):legend_entry(t,x,7,name)
    confs=[('profile',32,'TPOT (s/token)','Profile samples','(a) Calibration coverage',[(8,'8'),(12,'12'),(16,'16')],lambda v:103-(v-7)/11*80),
           ('input',210,'TTFT (s)','Input tokens','(b) Input length',[(10,'10'),(100,'100'),(1000,'1000')],lambda v:103-math.log10(v/10)/math.log10(400)*80),
           ('batch',388,'Aggregate tokens/s','Batch size','(c) Batch size',[(0,'0.0'),(.2,'0.2'),(.4,'0.4'),(.6,'0.6')],lambda v:103-v/.6*80)]
    for key,x0,yl,xl,title,ticks,fy in confs:
        x1=x0+123;xs=d[key]['x'];fx=lambda v:x0+math.log(v/xs[0])/math.log(xs[-1]/xs[0])*123
        frame(t,x0,x1,23,103,ticks,fy)
        plot_series(t,xs,d[key]['series'],fx,fy)
        for x in xs:t.extend([line(fx(x),103,fx(x),106,'ink',.45),node(str(x),fx(x),112,6.7)])
        t.extend([node(yl,x0-25,63,7.2,extra=',rotate=90'),node(xl,(x0+x1)/2,123,7.2),heading(title,(x0+x1)/2)])
        value=d[key]['series']['MECC'][-1]
        txt=f'{value:.3f}' if key=='batch' else f'{value:.1f}' if key=='profile' else str(value)
        t.append(node(txt,x1-5,fy(value)+(14 if key=='batch' else 12 if key=='input' else -8),6.5,'east','blue'))
    return end(t)

def quota(d):
    t=preamble(252,132)
    for x,y,name in [(25,7,'Streaming'),(135,7,'Fixed CPU'),(25,19,'Three-tier LRU'),(135,19,'MECC')]:legend_entry(t,x,y,name,size=6.5)
    xs=d['capacity']['x'];series=d['capacity']['series'];fx=lambda v:27+(v-16)/32*111;fy=lambda v:91-v/32*59
    frame(t,27,138,32,91,[(0,'0'),(16,'16'),(32,'32')],fy)
    plot_series(t,xs,series,fx,fy)
    for x in [16,32,48]:t.extend([line(fx(x),91,fx(x),94,'ink',.45),node(str(x),fx(x),100,6.5)])
    t.extend([node('TPOT (s/token)',7,61.5,7,extra=',rotate=90'),node('7',143,fy(7)+1,6.5,'west','blue')])
    # A second panel uses an exact adjacent difference, not another invented run.
    rfy=lambda v:91-v/4.8*59
    frame(t,184,249,32,91,[(0,'0'),(2,'2'),(4,'4')],rfy)
    m=series['MECC'];savings=[p-q for p,q in zip(m,m[1:])]
    for x,v,cap in zip([192,208,224,240],savings,xs[1:]):
        t.append(f'\\filldraw[fill=blue!83,draw=blue,line width=.35bp] ({x-4:.3f},{rfy(v):.3f}) rectangle ({x+4:.3f},91);\n')
        t.extend([node(f'{v:g}',x,rfy(v)-6,6.4,color='blue'),node(str(cap),x,100,6.5)])
    t.extend([node('TPOT saved (s)',163,61.5,6.9,extra=',rotate=90'),node('Primary host allowance (GiB)',138,112,6.9),heading('(a) Decode latency',82.5,126),heading('(b) MECC savings',216.5,126)])
    return end(t)

def main():
    assert not (OUT/'SEALED.json').exists()
    if not OUT.exists():
        for rel,h in json.loads((PREV/'SEALED.json').read_text())['hashes'].items():
            assert sha(PREV/rel)==h,rel
            dst=OUT/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PREV/rel,dst);dst.chmod(stat.S_IREAD|stat.S_IWRITE)
    n=json.loads((OUT/'narrative_targets.json').read_text());a=json.loads((OUT/'ideal_assumptions.json').read_text());d=targets(n,a)
    (OUT/'SENSITIVITY_COMPARISON_TARGETS.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
    (OUT/'completion_figures/workload_sensitivity.tex').write_text(sensitivity(d),encoding='utf-8')
    (OUT/'completion_figures/quota_targets.tex').write_text(quota(d),encoding='utf-8')
    old=(PREV/'manuscript.tex').read_text(encoding='utf-8');s=old
    before='E7--E9 workload sensitivity. The reference is uniform initialization in (a) and streaming in (b,c). Horizontal axes are logarithmic; (b) also uses a logarithmic latency axis. Shading marks the gap between policies.'
    after='E7--E9 sensitivity across four policy controls. The reference is uniform initialization in (a) and streaming in (b,c). Horizontal axes are logarithmic; (b) also uses a logarithmic latency axis.'
    assert before in s;s=s.replace(before,after)
    before='E6 capacity sensitivity (HBM: 50 GiB). (a) Decode latency. (b) MECC TPOT saved per 8 GiB increment from the preceding setting.'
    after='E6 capacity sensitivity at 50 GiB HBM allowance. (a) Four-policy decode latency. (b) MECC TPOT saved per 8 GiB increment from the preceding setting.'
    assert before in s;s=s.replace(before,after)
    before='All target configurations require implementation and hardware checks.'
    after='Figures 13/14 add authored policy targets in SENSITIVITY\\_COMPARISON\\_TARGETS.json. Fixed CPU holds host membership static. Three-tier LRU uses unprofiled per-tier replacement. The added sweeps are not executions. All target configurations require implementation and hardware checks.'
    assert before in s;s=s.replace(before,after)
    (OUT/'manuscript.tex').write_text(s,encoding='utf-8')
    (OUT/'changes.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile=PREV.name,tofile=OUT.name)),encoding='utf-8')

if __name__=='__main__':main()
