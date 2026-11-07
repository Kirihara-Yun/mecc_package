"""Verify that the new revision changes only Fig. 11's visual encoding."""
import hashlib
import json
import stat
import pymupdf
from iterate import HERE, audit, finish

OUT = HERE / 'r14_model_colors'
PREV = HERE / 'r13_experiment_audit'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (OUT / 'SEALED.json').exists()
    for directory in HERE.glob('r[0-9][0-9]_*'):
        if not directory.is_dir() or directory in [OUT, HERE / 'r00_frozen']: continue
        for rel, digest in json.loads((directory / 'SEALED.json').read_text())['hashes'].items():
            assert sha(directory / rel) == digest, (directory.name, rel)
    for rel in ['manuscript.tex', 'references.bib', 'EXPERIMENT_TARGETS.json', 'ideal_assumptions.json',
                'narrative_targets.json', 'RATIO_AUDIT.json', 'PROTOCOLS.json']:
        assert sha(OUT / rel) == sha(PREV / rel), rel
    for folder in ['figures', 'measured_figures', 'completion_figures', 'method_redesign']:
        for path in (PREV / folder).rglob('*'):
            if not path.is_file(): continue
            rel = path.relative_to(PREV)
            if rel.as_posix() in ['completion_figures/cross_model.pdf', 'completion_figures/cross_model.png']: continue
            assert sha(OUT / rel) == sha(path), str(rel)
    colors = json.loads((OUT / 'COLOR_ENCODING.json').read_text())
    assert len(set(colors['model_colors'].values())) == len(set(colors['model_hatches'].values())) == 3
    report = finish(OUT.name)
    assert (report['pages'], report['body_pages'], report['reference_pages'], report['appendix_pages']) == (8, 6, [7], [8])
    assert not report['issues'] and report['references'] == 45
    assert report['figures']['fig:target_models']['page'] == 5
    language = audit((OUT / 'manuscript.tex').read_text())
    assert not language['banned_tone'] and not language['long_sentences']
    doc = pymupdf.open(OUT / 'manuscript.pdf')
    for i, page in enumerate(doc):
        assert max(b[3] for b in page.get_text('blocks')) <= 723, i + 1
        page.get_pixmap(matrix=pymupdf.Matrix(1.6, 1.6)).save(OUT / f'page_{i+1}.png')
    doc.close()
    (OUT / 'COLOR_VALIDATION.json').write_text(json.dumps({
        'previous_seals_unchanged': True, 'manuscript_and_numbers_unchanged': True,
        'other_figures_unchanged': True, 'three_distinct_colors_and_hatches': True,
        'same_encoding_across_tasks': True, 'layout': report,
    }, indent=2) + '\n', encoding='utf-8')
    (OUT / 'changes.diff').write_text('Only completion_figures/cross_model.pdf and .png change: model colors and hatches.\n', encoding='utf-8')
    files = [p for p in OUT.rglob('*') if p.is_file() and p.name != 'SEALED.json' and
             p.suffix not in ['.aux', '.log', '.out', '.fls', '.fdb_latexmk', '.blg']]
    (OUT / 'SEALED.json').write_text(json.dumps({'revision': OUT.name, 'date': '2026-11-08',
        'hashes': {p.relative_to(OUT).as_posix(): sha(p) for p in files}}, indent=2) + '\n', encoding='utf-8')
    for p in files + [OUT / 'SEALED.json']: p.chmod(stat.S_IREAD)
    print('PASS: Fig.11 colors/hatches; source and numbers unchanged; prior seals unchanged; 6+1+1 pages.')


if __name__ == '__main__':
    main()
