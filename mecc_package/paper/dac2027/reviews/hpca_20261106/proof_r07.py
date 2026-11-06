"""Final semantic proof pass over the separately archived R06 copy."""
from pathlib import Path
import shutil
from iterate import HERE,create

def main():
    previous=HERE/'r06_editorial'
    source=(previous/'manuscript.tex').read_text(encoding='utf-8')
    edits={
        'The runtime promotes selected experts and retains displaced GPU weights in the host cache.':
            'The runtime promotes router-selected experts and retains displaced GPU weights in the host cache.',
        "Promotions and demotions update residency from the original router's selections.":
            'The delivery path orders HDD reads and H2D copies before GPU consumption.',
        'HBM residents execute in place;':
            'HBM residents are ready for GPU execution;',
        'GPU eviction is an admission decision for the host cache.':
            'A GPU victim is also a candidate for host admission.',
    }
    for old,new in edits.items():
        assert source.count(old)==1,old
        source=source.replace(old,new,1)
    out=create('r07_proof',source,(previous/'manuscript.tex').read_text(encoding='utf-8'))
    for rel in ['figures/fig01_overview.pdf','figures/fig01_overview.png','redraw_framework.py']:
        shutil.copy2(previous/rel,out/rel)
    print(out)

if __name__=='__main__':main()
