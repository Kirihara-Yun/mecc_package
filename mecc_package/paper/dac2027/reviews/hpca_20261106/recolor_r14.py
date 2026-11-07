"""Change only Fig. 11's model encoding in a separate revision."""
import hashlib
import json
import shutil
import stat
import sys
from iterate import HERE, PAPER

PREV = HERE / 'r13_experiment_audit'
OUT = HERE / 'r14_model_colors'


def main():
    assert not OUT.exists()
    manifest = json.loads((PREV / 'SEALED.json').read_text())
    for rel, digest in manifest['hashes'].items():
        source = PREV / rel
        assert hashlib.sha256(source.read_bytes()).hexdigest() == digest, rel
        dest = OUT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        dest.chmod(stat.S_IREAD | stat.S_IWRITE)
    # Old validation and renders are replaced after the PDF is built.
    sys.path.insert(0, str(PAPER))
    import matplotlib.pyplot as plt
    import numpy as np
    import build_compact_results as c
    c.setup()
    targets = json.loads((OUT / 'EXPERIMENT_TARGETS.json').read_text())
    colors = [c.BLUE, c.TEAL, c.ORANGE]
    hatches = ['///', '...', '\\\\']
    fig, axs = plt.subplots(1, 2, figsize=(3.45, 1.94))
    fig.subplots_adjust(.12, .29, .98, .79, wspace=.27)
    for i, (ax, task) in enumerate(zip(axs, ['GSM8K', 'HumanEval'])):
        values = targets['cross_model'][task]
        ratios = np.array(values['streaming_seconds']) / np.array(values['mecc_seconds'])
        bars = ax.bar(range(3), ratios, .54, color=colors, ec=c.INK, lw=.4, zorder=3)
        for bar, hatch in zip(bars, hatches):
            bar.set_hatch(hatch)
        ax.bar_label(bars, labels=[f'{value:.2f}' for value in ratios], padding=2, fontsize=6.1)
        ax.set_xticks(range(3), ['Mixtral\n8×7B', 'Qwen2\n57B-A14B', 'Mixtral\n8×22B'], fontsize=5.8)
        ax.set_ylim(0, 4.1)
        ax.set_yticks([0, 1, 2, 3, 4])
        ax.axhline(1, c=c.GRAY, ls='--', lw=.6)
        c.style(ax, 'y')
        title = ax.set_title(f'({chr(97+i)}) E3: {task}', loc='left', pad=4, fontsize=7.2)
        title.set_bbox({'facecolor': '#FFF19A', 'edgecolor': 'none', 'pad': 1.2})
    axs[0].set_ylabel('Speedup over streaming (×)', labelpad=2)
    for ext in ['pdf', 'png']:
        fig.savefig(OUT / 'completion_figures' / f'cross_model.{ext}', dpi=280, bbox_inches='tight', pad_inches=.025)
    plt.close(fig)
    (OUT / 'COLOR_ENCODING.json').write_text(json.dumps({
        'figure': 11,
        'model_colors': dict(zip(targets['cross_model']['models'], colors)),
        'model_hatches': dict(zip(targets['cross_model']['models'], hatches)),
        'same_encoding_in_both_workloads': True,
        'numbers_and_text_modified': False,
    }, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
