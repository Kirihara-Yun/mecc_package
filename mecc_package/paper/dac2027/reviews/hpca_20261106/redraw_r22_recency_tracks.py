"""Encode Fig. 5 as expert trajectories through ranked resident positions."""
import difflib
import hashlib
import json
import shutil
import stat
from iterate import HERE

PREV = HERE / 'r21_state_figure'
OUT = HERE / 'r22_recency_tracks'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not (OUT / 'SEALED.json').exists()
    if not OUT.exists():
        for rel, digest in json.loads((PREV / 'SEALED.json').read_text())['hashes'].items():
            assert sha(PREV / rel) == digest, rel
            dst = OUT / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PREV / rel, dst)
            dst.chmod(stat.S_IREAD | stat.S_IWRITE)
    states = json.loads((OUT / 'TRANSITION_AUDIT.json').read_text())['continuous_trace']
    rows = [s['hbm_mru_to_lru'] + s['cpu_mru_to_lru'] for s in states]
    assert rows == [['a1','a2','a3','a4'], ['a2','a1','a3','a4'],
                    ['a3','a2','a1','a4'], ['a5','a3','a2','a1']]
    xs = [44, 106, 168, 230]
    ys = [31, 51, 79, 99]
    tex = [r'''\documentclass[tikz,border=0pt]{standalone}
\usepackage[T1]{fontenc}
\usepackage{newtxtext,newtxmath}
\usepackage{xcolor}
\usetikzlibrary{arrows.meta}
\definecolor{ink}{HTML}{203244}
\definecolor{a1}{HTML}{6D7F99}
\definecolor{a2}{HTML}{2C6D9E}
\definecolor{a3}{HTML}{398E86}
\definecolor{a4}{HTML}{A6B0BA}
\definecolor{a5}{HTML}{C58A46}
\begin{document}
\begin{tikzpicture}[x=1bp,y=-1bp,every node/.style={inner sep=0pt,outer sep=0pt,text=ink,font=\fontsize{7.2}{8.4}\selectfont}]
\path[use as bounding box] (0,0) rectangle (252,130);
\fill[a2!6] (30,21) rectangle (245,61);
\fill[a3!6] (30,69) rectangle (245,109);
\draw[ink!25,densely dashed,line width=.4bp] (30,65)--(245,65);
\node[rotate=90,text=a2,font=\fontsize{7.5}{8.5}\selectfont\bfseries] at (7,41) {HBM};
\node[rotate=90,text=a3,font=\fontsize{7.5}{8.5}\selectfont\bfseries] at (7,89) {CPU};
\node[font=\fontsize{6}{7}\selectfont] at (21,31) {MRU};
\node[font=\fontsize{6}{7}\selectfont] at (21,51) {LRU};
\node[font=\fontsize{6}{7}\selectfont] at (21,79) {MRU};
\node[font=\fontsize{6}{7}\selectfont] at (21,99) {LRU};
''']
    for x, title in zip(xs, ['Initial', r'Request $a_2$', r'Request $a_3$', r'Request $a_5$']):
        tex.append(r'\node at ('+str(x)+',8) {'+title+'};\n')
    # A white under-stroke separates crossings; color follows expert identity.
    edges = []
    def curve(name, x0, y0, x1, y1, dashed=False):
        style = ',densely dashed' if dashed else ''
        d = (x1-x0)*.45
        p = f'({x0},{y0}) .. controls ({x0+d},{y0}) and ({x1-d},{y1}) .. ({x1},{y1})'
        tex.append(r'\draw[white,line width=3.5bp'+style+'] '+p+';\n')
        tex.append(r'\draw['+name+',line width=1.8bp,line cap=round'+style+'] '+p+';\n')
        edges.append({'expert':name, 'from':[x0,y0], 'to':[x1,y1], 'dashed':dashed})
    for step in range(3):
        before, after = rows[step:step+2]
        for name in before:
            if name in after:
                curve(name,xs[step],ys[before.index(name)],xs[step+1],ys[after.index(name)])
        if step == 2:
            curve('a4',xs[step],ys[3],xs[step+1],119,True)
            curve('a5',181,119,xs[step+1],ys[0])
    for x, row in zip(xs, rows):
        for y,name in zip(ys,row):
            tex.append(r'\filldraw[fill='+name+',draw=white,line width=.8bp] ('+str(x)+','+str(y)+') circle[radius=7.7bp];\n')
            tex.append(r'\node[text=white,font=\fontsize{7.8}{8}\selectfont] at ('+str(x)+','+str(y)+') {$a_'+name[1:]+'$};\n')
    tex.append(r'''
\filldraw[fill=a5,draw=white,line width=.8bp] (181,119) circle[radius=7.7bp];
\node[text=white,font=\fontsize{7.8}{8}\selectfont] at (181,119) {$a_5$};
\node[anchor=east,text=a5,font=\fontsize{6.4}{7}\selectfont] at (169,119) {HDD read};
\filldraw[fill=white,draw=a4,line width=.8bp] (230,119) circle[radius=7.7bp];
\node[text=a4,font=\fontsize{7.8}{8}\selectfont] at (230,119) {$a_4$};
\draw[-{Stealth[length=3bp,width=3bp]},ink!55,line width=.4bp] (36,119)--(84,119);
\node[anchor=west,font=\fontsize{6.4}{7}\selectfont] at (90,119) {Time};
\end{tikzpicture}
\end{document}
''')
    (OUT/'method_redesign/residency_cases.tex').write_text(''.join(tex),encoding='utf-8')
    source = (PREV/'manuscript.tex').read_text(encoding='utf-8')
    # Use a literal extracted caption to avoid apostrophe/LaTeX ambiguity.
    start = source.index(r'\caption{A continuous request sequence')
    end = source.index('\n',start)
    caption = r'\caption{Expert recency over three requests. Colored tracks follow the same experts from left to right. Within each tier, the upper position is MRU and the lower position is LRU. A CPU hit promotes $a_3$ and retains $a_1$ on the host. Loading $a_5$ from HDD retains $a_2$ and removes $a_4$ from CPU.}'
    source = source[:start]+caption+source[end:]
    (OUT/'manuscript.tex').write_text(source,encoding='utf-8')
    (OUT/'changes.diff').write_text(''.join(difflib.unified_diff((PREV/'manuscript.tex').read_text().splitlines(True),source.splitlines(True),fromfile=PREV.name,tofile=OUT.name)),encoding='utf-8')
    (OUT/'RECENCY_TRACK_AUDIT.json').write_text(json.dumps({'continuous_states':states,'edges':edges,
        'encoding':'expert identity=color; tier=background band; recency=vertical rank; time=horizontal',
        'source_trace_sha256':sha(OUT/'TRANSITION_AUDIT.json'),'font_packages':['newtxtext','newtxmath'],
        'no_policy_or_measurement_changes':True},indent=2)+'\n',encoding='utf-8')


if __name__ == '__main__':
    main()
