"""A coherent compact line-figure style and an adjacent marginal-benefit plot."""
import difflib
import hashlib
import json
import math
import shutil
import stat
from iterate import HERE
from redraw_r23_sensitivity import start,node,line,end

PREV=HERE/'r23_sensitivity_design'
OUT=HERE/'r24_publication_style'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def preamble(w,h):
    t=start(w,h)
    t[0]=t[0].replace('{9AA7B2}','{75818D}').replace('{E7EBEF}','{E6EAF0}')
    return t

def point(x,y,c,square=False):
    if square:
        return f'\\filldraw[fill=white,draw={c},line width=.8bp] ({x-2:.3f},{y-2:.3f}) rectangle ({x+2:.3f},{y+2:.3f});\n'
    return f'\\filldraw[fill={c},draw=white,line width=.5bp] ({x:.3f},{y:.3f}) circle[radius=2.5bp];\n'

def heading(t,x,y=140):
    return node(t,x,y,7.8,extra=',fill=yellow,inner xsep=1.4bp,inner ysep=1.0bp')

def legend(x,y,reference='Reference'):
    return (line(x,y,x+13,y,'blue',1.15)+point(x+6.5,y,'blue')+node('MECC',x+19,y,7,'west')+
            line(x+81,y,x+94,y,'gray',1,',dashed')+point(x+87.5,y,'gray',True)+node(reference,x+100,y,7,'west'))

def frame(t,x0,x1,y0,y1,yticks,fy):
    for v,label in yticks:
        y=fy(v)
        t.extend([line(x0,y,x1,y,'grid',.35),line(x0-2,y,x0,y,'ink',.45),node(label,x0-5,y,6.7,'east')])
    t.extend([line(x0,y0,x1,y0,'ink!55',.4),line(x1,y0,x1,y1,'ink!55',.4),
              line(x0,y0,x0,y1,'ink',.5),line(x0,y1,x1,y1,'ink',.5)])

def curves(t,coords_ref,coords_mecc,stage='all'):
    vertices=coords_ref+list(reversed(coords_mecc))
    path='--'.join(f'({x:.3f},{y:.3f})' for x,y in vertices)
    if stage!='lines':t.append('\\fill[blue!9] '+path+'--cycle;\n')
    if stage=='fill':return
    for coords,c,sq in [(coords_ref,'gray',True),(coords_mecc,'blue',False)]:
        for (x0,y0),(x1,y1) in zip(coords,coords[1:]):
            t.append(line(x0,y0,x1,y1,c,1 if sq else 1.25,',dashed' if sq else ''))
        for x,y in coords:t.append(point(x,y,c,sq))

def sensitivity(n):
    t=preamble(522,148)
    t.append(legend(185,7,'Reference'))
    configs=[
        (32,155,'profile_samples','profile_tpot_uniform','profile_tpot_mecc','TPOT (s/token)','Profile samples','(a) Calibration coverage',
         [(8,'8'),(10,'10'),(12,'12')],lambda v:103-(v-7)/6*80),
        (210,333,'input_tokens','input_ttft_streaming','input_ttft_mecc','TTFT (s)','Input tokens','(b) Input length',
         [(10,'10'),(100,'100'),(1000,'1000')],lambda v:103-math.log10(v/10)/math.log10(400)*80),
        (388,511,'batch_sizes','batch_throughput_streaming','batch_throughput_mecc','Aggregate tokens/s','Batch size','(c) Batch size',
         [(0,'0.0'),(.2,'0.2'),(.4,'0.4'),(.6,'0.6')],lambda v:103-v/.6*80)]
    for x0,x1,xkey,bkey,mkey,yl,xl,title,ticks,fy in configs:
        xs=n[xkey];fx=lambda v:x0+math.log(v/xs[0])/math.log(xs[-1]/xs[0])*(x1-x0)
        # Draw the interval shading before grid/frame/observed points.
        coords_b=[(fx(x),fy(v)) for x,v in zip(xs,n[bkey])]
        coords_m=[(fx(x),fy(v)) for x,v in zip(xs,n[mkey])]
        curves(t,coords_b,coords_m,'fill')
        frame(t,x0,x1,23,103,ticks,fy)
        curves(t,coords_b,coords_m,'lines')
        for x in xs:
            px=fx(x);t.extend([line(px,103,px,106,'ink',.45),node(str(x),px,112,6.7)])
        t.extend([node(yl,x0-25,63,7.2,extra=',rotate=90'),node(xl,(x0+x1)/2,123,7.2),heading(title,(x0+x1)/2)])
        vb,vm=n[bkey][-1],n[mkey][-1]
        f=lambda v:(f'{v:.3f}' if xkey=='batch_sizes' else f'{v:.1f}' if xkey=='profile_samples' else str(v))
        # End labels identify values, while the common legend identifies policies.
        dy_b=1 if xkey=='input_tokens' else -7
        dy_m={'profile_samples':8,'input_tokens':12,'batch_sizes':14}[xkey]
        t.extend([node(f(vb),x1-8,fy(vb)+dy_b,6.5,'east','gray'),node(f(vm),x1-5,fy(vm)+dy_m,6.5,'east','blue')])
    return end(t)

def quota(a):
    t=preamble(252,124)
    t.append(legend(37,7,'Three-tier LRU'))
    xs=a['cpu_budget_gb'];b=a['budget_tpot_seconds']['Three-tier LRU'];m=a['budget_tpot_seconds']['MECC']
    x0,x1,y0,y1=27,138,23,83
    fx=lambda v:x0+(v-16)/32*(x1-x0)
    fy=lambda v:y1-v/30*(y1-y0)
    coords_b=[(fx(x),fy(v)) for x,v in zip(xs,b)]
    coords_m=[(fx(x),fy(v)) for x,v in zip(xs,m)]
    curves(t,coords_b,coords_m,'fill')
    frame(t,x0,x1,y0,y1,[(0,'0'),(15,'15'),(30,'30')],fy)
    curves(t,coords_b,coords_m,'lines')
    for x in [16,32,48]:
        t.extend([line(fx(x),y1,fx(x),y1+3,'ink',.45),node(str(x),fx(x),92,6.6)])
    t.extend([node('TPOT (s/token)',7,53,7,extra=',rotate=90'),
              heading('(a) Decode latency',82.5,118),
              node('12',143,fy(12)-2,6.5,'west','gray'),node('7',143,fy(7)+2,6.5,'west','blue')])
    # These bars are adjacent differences of the existing MECC series.
    rx0,rx1=184,249
    rfy=lambda v:83-v/4.8*60
    frame(t,rx0,rx1,23,83,[(0,'0'),(2,'2'),(4,'4')],rfy)
    savings=[p-q for p,q in zip(m,m[1:])]
    for x,value,capacity in zip([192,208,224,240],savings,xs[1:]):
        t.append(f'\\filldraw[fill=blue!83,draw=blue,line width=.35bp] ({x-4:.3f},{rfy(value):.3f}) rectangle ({x+4:.3f},83);\n')
        t.extend([node(f'{value:g}',x,rfy(value)-6,6.4,color='blue'),node(str(capacity),x,92,6.5)])
    t.extend([node('TPOT saved (s)',163,53,6.9,extra=',rotate=90'),node('Primary host allowance (GiB)',138,104,6.9),heading('(b) Per +8 GiB',216.5,118)])
    return end(t),savings

def main():
    assert not (OUT/'SEALED.json').exists()
    if not OUT.exists():
        for rel,h in json.loads((PREV/'SEALED.json').read_text())['hashes'].items():
            assert sha(PREV/rel)==h,rel
            dst=OUT/rel;dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(PREV/rel,dst);dst.chmod(stat.S_IREAD|stat.S_IWRITE)
    n=json.loads((OUT/'narrative_targets.json').read_text());a=json.loads((OUT/'ideal_assumptions.json').read_text())
    (OUT/'completion_figures/workload_sensitivity.tex').write_text(sensitivity(n),encoding='utf-8')
    q,savings=quota(a)
    (OUT/'completion_figures/quota_targets.tex').write_text(q,encoding='utf-8')
    old=(PREV/'manuscript.tex').read_text(encoding='utf-8');s=old
    before='E7--E9 workload sensitivity. (a) Paired decode latencies under uniform and profile-based initialization. (b) First-token latency on logarithmic axes. (c) Aggregate throughput at each batch size.'
    after='E7--E9 workload sensitivity. The reference is uniform initialization in (a) and streaming in (b,c). Horizontal axes are logarithmic; (b) also uses a logarithmic latency axis. Shading marks the gap between policies.'
    assert before in s;s=s.replace(before,after)
    before='E6 decode latency at each primary host allowance. Paired endpoints compare MECC with three-tier LRU; HBM allowance is 50 GiB.'
    after='E6 capacity sensitivity (HBM: 50 GiB). (a) Decode latency. (b) MECC TPOT saved per 8 GiB increment from the preceding setting.'
    assert before in s;s=s.replace(before,after)
    (OUT/'manuscript.tex').write_text(s,encoding='utf-8')
    (OUT/'changes.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile=PREV.name,tofile=OUT.name)),encoding='utf-8')
    (OUT/'PUBLICATION_STYLE_AUDIT.json').write_text(json.dumps({'source_hashes':{r:sha(OUT/r) for r in ['narrative_targets.json','ideal_assumptions.json']},
        'source_arrays_unchanged':True,'new_measurements':False,'savings_formula':'previous MECC TPOT - current MECC TPOT',
        'marginal_savings':savings,'savings_at_gib':a['cpu_budget_gb'][1:],
        'shading':'gap between series, not uncertainty','highlight_preserved':True,
        'references_inspected':['MoE-Lightning ASPLOS 2025 pages 9-11','SFD HPCA 2026 pages 9-11'],
        'font_packages':['newtxtext','newtxmath']},indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
