"""One-shot editorial marking of the pre-highlight design draft."""
from pathlib import Path
import re

P=Path(__file__).resolve().parents[1]
p=P/'mecc_dac2027.tex'
s=p.read_text(encoding='utf-8')
pre,body=s.split(r'\begin{abstract}',1)
# Never mark numeric LaTeX arguments in the preamble.
pre=re.sub(r'\\draftvalue\{([^{}]*)\}',r'\1',pre)
body=re.sub(r'\\draftvalue\{([^{}]*)\}',r'\1',body)
s=body
notes=[
 'Illustrative targets specify',
 'All numerical outcomes below are authored scenarios.',
 'The hypothetical plan',
 'The fourth configuration, profile cost, no-shift control, uniform access, and mismatched profiles remain unmeasured.',
 'All values and request windows are hypothetical.',
 'The plots do not use measured MoE routes.',
 'Hypothetical performance.', 'Hypothetical ablation.', 'Hypothetical sensitivity.',
 'Hypothetical 8x7B deployment point; not measured.',
 'All results and quality checks below are authored targets. They are not measurements.',
 'Dataset, model, and input revisions remain to be frozen for execution.',
 'RF and SSD-native are hypothetical local mechanism adapters.',
 'The eight-GPU point is an authored scenario reference, independent of the cited systems.',
 'We omit authored repeat variation from the plots.',
 'No uncertainty estimate is available in this draft.',
 'These cases remain planned; the current curves cover only the displayed scenario points.',
 'These checks remain hypothetical.',
 'Submission requires replacing all scenario outcomes with measurements.',
 'these tests remain to be executed.',
]
for old in notes:
    assert old in s, old
    if r'\draftnote{'+old+'}' not in s:
        s=s.replace(old,r'\draftnote{'+old+'}')

# Only paragraphs that describe authored outcomes. Hardware facts and equations
# in the method are not marked as invented data. Math stays intact in a box.
starts=[
 'We study single-GPU',
 'Figure~\\ref{fig:performance}(a) fixes',
 'The SSD-native adapter takes',
 'Scenario TTFT is',
 'Figure~\\ref{fig:performance}(b) gives',
 'Table~\\ref{tab:gpu} includes',
 'Figure~\\ref{fig:ablation} adds',
 'SSD demand-miss shares are',
 'Figure~\\ref{fig:budget}(a) increases',
 'Figure~\\ref{fig:budget}(b) varies',
 'Figure~\\ref{fig:budget}(c) adds',
 'The quality targets are',
 '\\begin{tabular}{lrr}',
]
# Protect macros, references and source formulas before marking plain numbers.
token=re.compile(r'\$[^$]*\$|\\(?:draftnote|ref|cite|label)\{[^}]*\}')
number=re.compile(r'(?<![\w\\])\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)*(?!\w)')
def mark(par):
    out=[]; end=0
    for m in token.finditer(par):
        out.append(number.sub(lambda n:r'\draftvalue{'+n[0]+'}',par[end:m.start()]))
        t=m[0]
        # Do not color the generic full-request equation as a measured result.
        if t.startswith('$') and re.search(r'\d',t) and not t.startswith('$J('):
            t=r'\draftvalue{'+t+'}'
        out.append(t); end=m.end()
    out.append(number.sub(lambda n:r'\draftvalue{'+n[0]+'}',par[end:]))
    return ''.join(out)
starts=[x.replace('\\\\','\\') for x in starts]
paras=s.split('\n\n')
for i,par in enumerate(paras):
    if i==0 or any(line.startswith(x) for line in par.splitlines() for x in starts) or r'\begin{tabular}{lrr}' in par:
        # Preserve structural commands and model identifiers inside table headers.
        paras[i]=mark(par)
s='\n\n'.join(paras)
# Spell-out targets in the abstract also need visible replacement anchors.
s=s.replace('eight seconds per token; a two-GPU resident target takes',
            r'\draftnote{eight seconds per token}; a two-GPU resident target takes')
p.write_text(pre+r'\begin{abstract}'+s,encoding='utf-8')
print('Marked hypothetical data/status and AI disclosure; original values preserved.')
