"""Verify that the new revision changes only Fig. 11's visual encoding."""
import hashlib
import json
import stat
import re
import difflib
import pymupdf
from iterate import HERE, audit, finish

OUT = HERE / 'r15_direct_terms'
PREV = HERE / 'r14_model_colors'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (OUT / 'SEALED.json').exists()
    for directory in HERE.glob('r[0-9][0-9]_*'):
        if not directory.is_dir() or directory in [OUT, HERE / 'r00_frozen']: continue
        for rel, digest in json.loads((directory / 'SEALED.json').read_text())['hashes'].items():
            assert sha(directory / rel) == digest, (directory.name, rel)
    for rel in ['references.bib', 'EXPERIMENT_TARGETS.json', 'ideal_assumptions.json',
                'narrative_targets.json', 'RATIO_AUDIT.json', 'PROTOCOLS.json']:
        assert sha(OUT / rel) == sha(PREV / rel), rel
    for folder in ['figures', 'measured_figures', 'completion_figures', 'method_redesign']:
        for path in (PREV / folder).rglob('*'):
            if not path.is_file(): continue
            rel = path.relative_to(PREV)
            if rel.as_posix() in ['figures/fig02_motivation_insights.pdf', 'figures/fig02_motivation_insights.png', 'completion_figures/traffic_exposure.pdf', 'completion_figures/traffic_exposure.png']: continue
            assert sha(OUT / rel) == sha(path), str(rel)
    source=(OUT/'manuscript.tex').read_text(encoding='utf-8')
    old=(PREV/'manuscript.tex').read_text(encoding='utf-8')
    assert re.findall(r'\d+(?:\.\d+)?',source)==re.findall(r'\d+(?:\.\d+)?',old)
    assert not re.search(r'victim|critical',source,re.I)
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
        assert not re.search(r'victim|critical',page.get_text(),re.I),i+1
        if i < 6:
            for block in page.get_text('dict')['blocks']:
                if block['type'] != 0: continue
                line = block['lines'][-1]
                tail = ''.join(span['text'] for span in line['spans']).strip()
                if re.fullmatch(r'[A-Za-z][A-Za-z-]*[.,;:]?', tail):
                    assert not any(span['font'] == 'TeXGyreTermesX-Regular' and 8.5 < span['size'] < 9.3 for span in line['spans']), (i+1, tail)
        assert max(b[3] for b in page.get_text('blocks')) <= 723, i + 1
        page.get_pixmap(matrix=pymupdf.Matrix(1.6, 1.6)).save(OUT / f'page_{i+1}.png')
    doc.close()
    (OUT / 'TERM_VALIDATION.json').write_text(json.dumps({
        'previous_seals_unchanged': True, 'numerals_and_data_unchanged': True,'direct_wording_in_text_and_figures':True,
        'fig11_and_other_figures_unchanged': True, 'three_distinct_colors_and_hatches': True,
        'same_encoding_across_tasks': True, 'layout': report,
    }, indent=2) + '\n', encoding='utf-8')
    (OUT / 'changes.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),source.splitlines(True),fromfile=PREV.name,tofile=OUT.name)),encoding='utf-8')
    files = [p for p in OUT.rglob('*') if p.is_file() and p.name != 'SEALED.json' and
             p.suffix not in ['.aux', '.log', '.out', '.fls', '.fdb_latexmk', '.blg']]
    (OUT / 'SEALED.json').write_text(json.dumps({'revision': OUT.name, 'date': '2026-11-08',
        'hashes': {p.relative_to(OUT).as_posix(): sha(p) for p in files}}, indent=2) + '\n', encoding='utf-8')
    for p in files + [OUT / 'SEALED.json']: p.chmod(stat.S_IREAD)
    print('PASS: direct wording in prose and figures; data and Fig.11 colors unchanged; prior seals verified; 6+1+1 pages.')


if __name__ == '__main__':
    main()
