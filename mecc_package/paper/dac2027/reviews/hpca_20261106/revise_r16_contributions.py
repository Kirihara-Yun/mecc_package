"""Align the three introduction contributions with the three motivations."""
import hashlib
import json
import shutil
import stat
from iterate import HERE

PREV = HERE / 'r15_direct_terms'
OUT = HERE / 'r16_contributions'

CONTRIBUTIONS = r"""\item[(1)] \textbf{Allocating capacity by layer.} We compile per-layer HBM/CPU capacities and initial expert IDs from routing profiles. Comparing each layer's next uncovered rank assigns shared slots to the demand they cover. Initialization loads the highest-ranked experts into HBM and the next ranks into CPU.
\item[(2)] \textbf{Retaining experts after GPU eviction.} We maintain recency across HBM and CPU. A CPU promotion frees a host slot for the evicted GPU expert, preserving its weights for later reuse. Demotion reuses the host mirror through a metadata update.
\item[(3)] \textbf{Adapting residency to serving requests.} We combine profile-based initialization with request-driven admission. Experts selected during serving enter the resident set and displace older entries within the compiled capacities. Residency persists across tokens and requests as the active expert set changes.
"""


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
    source = path.read_text(encoding='utf-8')
    start = source.index(r'\item[(1)]')
    stop = source.index(r'\end{list}', start)
    path.write_text(source[:start] + CONTRIBUTIONS + source[stop:], encoding='utf-8')


if __name__ == '__main__':
    main()
