"""Restore ordinary marginal-savings bars while retaining the approved input panel."""
import difflib
import hashlib
import json
import shutil
import stat
from iterate import HERE
from redraw_r23_sensitivity import node,line
from redraw_r24_publication_style import frame,heading
from redraw_r25_more_methods import quota as previous_quota

PREV=HERE/'r26_input_waterfall'
OUT=HERE/'r27_savings_bars'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def quota(d):
    old=previous_quota(d)
    boundary=old.index('\\draw[grid,line width=0.35bp] (184.000,91.000)')
    t=[old[:boundary].replace(r'\begin{document}',r'\usetikzlibrary{patterns}'+'\n'+r'\begin{document}')]
    fy=lambda v:91-v/5*59
    frame(t,180,251,32,91,[(0,'0'),(2,'2'),(4,'4')],fy)
    m=d['capacity']['series']['MECC'];savings=[p-q for p,q in zip(m,m[1:])]
    bars=[]
    for x,v,cap in zip([189,207,225,243],savings,d['capacity']['x'][1:]):
        path=f'({x-5.2:.3f},{fy(v):.3f}) rectangle ({x+5.2:.3f},91)'
        t.append('\\fill[blue!13] '+path+';\n')
        t.append('\\fill[pattern=north east lines,pattern color=blue!65] '+path+';\n')
        t.append('\\draw[blue,line width=.55bp] '+path+';\n')
        t.extend([node(f'{v:g}',x,fy(v)-6,6.8,color='blue'),node(str(cap),x,100,6.5)])
        bars.append({'at_gib':cap,'saved_seconds':v,'x_center':x,'width_bp':10.4,'top_y':fy(v),'baseline_y':91})
    t.extend([node('TPOT saved (s)',161,61.5,6.9,extra=',rotate=90'),node('Primary host allowance (GiB)',138,112,6.9),
              heading('(a) Decode latency',82.5,126),heading('(b) MECC savings',216.5,126)])
    return ''.join(t)+r'\end{tikzpicture}'+'\n'+r'\end{document}'+'\n',bars

def main():
    assert not (OUT/'SEALED.json').exists()
    if not OUT.exists():
        for rel,h in json.loads((PREV/'SEALED.json').read_text())['hashes'].items():
            assert sha(PREV/rel)==h,rel
            dst=OUT/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PREV/rel,dst);dst.chmod(stat.S_IREAD|stat.S_IWRITE)
    d=json.loads((OUT/'SENSITIVITY_COMPARISON_TARGETS.json').read_text())
    tex,bars=quota(d)
    (OUT/'completion_figures/quota_targets.tex').write_text(tex,encoding='utf-8')
    old=(PREV/'manuscript.tex').read_text(encoding='utf-8')
    before='E6 capacity sensitivity at 50 GiB HBM allowance. (a) Four-policy decode latency. (b) Stepwise MECC latency: floating bars show the reduction from each additional 8 GiB.'
    after='E6 capacity sensitivity at 50 GiB HBM allowance. (a) Four-policy decode latency. (b) MECC TPOT saved per additional 8 GiB, relative to the preceding setting.'
    assert before in old;src=old.replace(before,after)
    (OUT/'manuscript.tex').write_text(src,encoding='utf-8')
    (OUT/'changes.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),src.splitlines(True),fromfile=PREV.name,tofile=OUT.name)),encoding='utf-8')
    (OUT/'SAVINGS_BAR_AUDIT.json').write_text(json.dumps({'source_sha256':sha(OUT/'SENSITIVITY_COMPARISON_TARGETS.json'),
        'formula':'previous MECC TPOT minus current MECC TPOT','bars':bars,'all_bars_start_at_zero':True,
        'raw_arrays_unchanged':True,'input_length_figure_unchanged':True,
        'status':'Exact differences of inherited authored targets, not new experiments'},indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
