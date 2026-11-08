"""Replace figurative cache wording and name the measured waiting time directly."""
import ast
import hashlib
import json
import shutil
import stat
import sys
from iterate import HERE, PAPER

PREV = HERE / 'r14_model_colors'
OUT = HERE / 'r15_direct_terms'


def main():
    assert not OUT.exists()
    for rel, digest in json.loads((PREV / 'SEALED.json').read_text())['hashes'].items():
        src = PREV / rel
        assert hashlib.sha256(src.read_bytes()).hexdigest() == digest, rel
        dst = OUT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        dst.chmod(stat.S_IREAD | stat.S_IWRITE)
    path = OUT / 'manuscript.tex'
    s = path.read_text(encoding='utf-8')
    edits = {
        'Layer dependencies expose these reads on the inference critical path.':
            'Each selected expert executes once its weights are available in HBM.',
        'SSD-LLaMA retains GPU victims in RAM':
            'SSD-LLaMA retains evicted expert weights in RAM',
        'GPU turnover then determines which of those weights survive on the host.':
            'GPU replacement then determines which weights remain on the host.',
        'Promoting a CPU expert vacates a host position just as an HBM victim loses its GPU position. Using that position for the victim preserves its place in the reuse order.':
            'Promoting a CPU expert frees a host slot for the expert evicted from HBM. Using that slot maintains the evicted expert\'s position in the reuse order.',
        'demotes the GPU victim': 'demotes the GPU LRU expert',
        'joint promotion and victim demotion': 'promotion and GPU-to-host demotion',
        'joint victim retention': 'retention after GPU eviction',
        'A GPU victim is also a candidate for host admission.':
            'An expert evicted from the GPU can remain on the host.',
        'shows a CPU promotion vacating a host position as the GPU selects its victim. Joint retention admits that victim into the vacated position, carrying recency across the tier boundary.':
            'shows a CPU promotion freeing a host slot for the GPU LRU expert. Joint retention fills that slot with the evicted expert and maintains its recency.',
        'frees a host position for an HBM victim.': 'frees a host slot for an expert evicted from HBM.',
        'Retaining Victims across the Tier Boundary': 'Retaining Evicted Experts on the Host',
        'The GPU LRU victim then becomes CPU MRU.': 'The evicted GPU LRU expert then becomes CPU MRU.',
        'keeping GPU victims available on the host.': 'keeping evicted experts available on the host.',
        'profile-based placement, victim retention, and history-based caching':
            'profile-based placement, host retention, and history-based caching',
        'This key connects a profiled rank to its initial location, later cache updates, and FP16 execution.':
            'This key links profiled experts to placement, cache updates, and FP16~execution.',
    }
    for old, new in edits.items():
        assert old in s, old
        s = s.replace(old, new)
    assert 'victim' not in s.lower() and 'critical' not in s.lower()
    path.write_text(s, encoding='utf-8')
    sys.path.insert(0, str(PAPER))
    # Rebuild the existing vector canvas, replacing labels only.
    script = (HERE / 'redraw_r08_motivation.py').read_text(encoding='utf-8')
    script = script.replace("OUT = HERE/'r08_layout'", "OUT = HERE/'r15_direct_terms'")
    script = script.replace("['Separate','Fixed CPU','MECC']", "['Separate','Swap-style','MECC']")
    script = script.replace('Correct the initial profile online', 'Adapt residency to new requests')
    script = script.replace('Promote and retain the victim', 'Retain evicted experts')
    ns = {'__file__': str(HERE / 'redraw_r08_motivation.py'), '__name__': 'r15_motivation'}
    exec(compile(script, 'r15_motivation', 'exec'), ns)
    ns['main']()
    import matplotlib.pyplot as plt
    import build_completion_figures as base
    import build_compact_results as compact
    compact.setup()
    src = (PAPER / 'build_completion_figures.py').read_text(encoding='utf-8')
    node = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == 'traffic_exposure')
    code = ast.unparse(node).replace('Critical-path time', 'Exposed time')
    env = dict(vars(base))
    env['N'] = json.loads((OUT / 'narrative_targets.json').read_text())
    def save(fig, name, record):
        for ext in ['pdf', 'png']:
            fig.savefig(OUT / 'completion_figures' / f'{name}.{ext}', dpi=280, bbox_inches='tight', pad_inches=.025)
        plt.close(fig)
    env['save'] = save
    exec(compile(code, 'r15_exposed_time', 'exec'), env)
    env['traffic_exposure']()
    (OUT / 'TERM_REPLACEMENTS.json').write_text(json.dumps(edits, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
