"""Create a new review draft; observations and sealed revisions remain immutable."""
import ast
import copy
import json
import shutil
import stat
import sys
from iterate import HERE, PAPER, create

OUT = HERE / 'r13_experiment_audit'
PREV = HERE / 'r12_protocols'


def write_json(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def prepare():
    old = (PREV / 'manuscript.tex').read_text(encoding='utf-8')
    s = old
    edits = [
        (r'\pending{E2} & GSM8K & 8; 128/128', r'\pending{E2} & GSM8K $\to$ HumanEval & 8+8; 128/128'),
        (r'\pending{E3} & GSM8K, HumanEval & 8; 128/128 & $50/\{40,64\}^{a}$', r'\pending{E3} & GSM8K, HumanEval & 8/task; 128/128 & per model$^{a}$'),
        (r'\pending{E5} & GSM8K & 8; 128/128 & 30/20', r'\pending{E5} & GSM8K, HumanEval & 8/task; 128/128 & 30/20'),
        ('compares equal budgets, global hotness, and layer profiles.', 'compares equal quotas, count allocation, and the rank-model plan.'),
        ('Panel (c) follows a task switch;', 'Panel (c) switches from eight GSM8K prompts to eight HumanEval prompts;'),
        ('(b) Online initialization versus compiled initialization; curves include initial placement and decode cost.', '(b) Uniform versus compiled plans; curves sum amortized placement and decode time.'),
        ('across the four model/workload groups.', 'across six model/workload groups.'),
        ('Moving from 8x7B to 8x22B \\pending{doubles} MECC TPOT; the corresponding streaming increase is \\pending{2.00--2.04}$\\times$.', 'Qwen2-57B-A14B gives \\pending{3.17}$\\times$ on GSM8K and \\pending{3.21}$\\times$ on HumanEval.'),
        ('E5 matched FP16 policy paths. Latency is normalized to MECC within each phase. Lower values are better.', 'E5 candidate FP16 policy paths. Geometric means combine task-local latency ratios on GSM8K and HumanEval. MECC is 1.0; lower is better.'),
        ('MoE-CORE, MoE-Infinity, and SSD-LLaMA supply the corresponding policy designs~\\cite{core,moeinfinity,ssdllama}.', 'The candidates cover MoE-CORE, MoE-Infinity, SSD-LLaMA, FlashMoE-RF, MoEpic, and Diff-MoE~\\cite{core,moeinfinity,ssdllama,flashmoe,moepic,diffmoe}.'),
        ('Profile, input-length, and batch sensitivity.', 'E7--E9 profile, input-length, and batch sensitivity.'),
        ('\\caption{Decode latency across host-memory allowances.}', '\\caption{E6 decode latency across primary host allowances; HBM allowance is 50 GiB.}'),
        ('\\caption{Profile transfer across tasks.', '\\caption{E10 profile transfer across tasks.'),
        ('The E3 startup control crosses at', 'The uniform/compiled plan control crosses at'),
        ('uses \\pending{18 seconds} of extra initialization and \\pending{2 seconds} of saving, giving \\pending{9 output tokens}.', 'uses \\pending{18 seconds} of extra placement and \\pending{4 seconds} of decode saving. The crossover is \\pending{4.5 tokens}, so compiled placement pays off from the \\pending{fifth token}.'),
        ('total average costs are \\pending{8.47 s/token} for compiled initialization and \\pending{10.19} for online initialization.', 'placement-plus-decode averages are \\pending{8.47 s/token} for the compiled plan and \\pending{12.19} for uniform placement.'),
        ('E2 uses GSM8K with 128/128 tokens, eight prompts, and calibrated initialization.', 'E2(a,b) use eight GSM8K prompts at 128/128 tokens. E2(c) adds eight HumanEval prompts after that first window; the profile comes from GSM8K. Allocation compares equal quotas, empirical-count allocation, and Zipf-smoothed marginal allocation at fixed runtime. Retention/adaptation share the same initial state.'),
        ('E3 uses 50/40 for 8x7B and 50/64 for 8x22B,', 'E3 uses 50/40 for 8x7B, 30/16 for Qwen2-57B-A14B, and 50/64 for 8x22B,'),
        ('E5 is a matched FP16 policy-path design at 30/20~GiB on Mixtral-8x7B/GSM8K, eight 128/128-token prompts. The MoE-CORE, MoE-Infinity, SSD-LLaMA, and FlashMoE-RF entries are authored latency targets for local path adaptations.', 'E5 uses Mixtral-8x7B at 30/20~GiB, with eight 128/128-token prompts per task on GSM8K and HumanEval. Its six baseline entries are authored latency targets for candidate local adaptations. MoEpic uses a whole-expert allocation control here; its split-expert system is outside that control. Diff-MoE is a candidate pending full-text and implementation checks.'),
        ('Their raw targets, assumptions, and status are in BASELINE\\_TARGETS.json.', 'Task-local targets, geometric means, and added model points are in EXPERIMENT\\_TARGETS.json.'),
        ('The startup control uses 12/30-second initialization and 10/8-second decode. Its crossing is 9 tokens; 64 tokens is an amortization example.', 'The startup control uses 12/30-second placement and 12/8-second decode for uniform/compiled plans. Its continuous crossing is 4.5 tokens; the first integer win is five. These curves exclude prefill. Uniform decode matches the E7 uniform control; compiled decode matches E3 GSM8K, E6 at 40 GiB, E7 at 2048 samples, and E9 at batch one.'),
    ]
    for a, b in edits:
        assert a in s, a
        s = s.replace(a, b)
    # Fix the startup reference identity, not an observed latency. Prefill belongs to TTFT.
    s = s.replace('for online initialization.', 'for uniform placement.')
    if not OUT.exists(): create(OUT.name, s, old)
    else: (OUT / 'manuscript.tex').write_text(s, encoding='utf-8')
    for p in OUT.rglob('*'):
        if p.is_file(): p.chmod(stat.S_IREAD | stat.S_IWRITE)
    for folder in ['figures', 'measured_figures', 'completion_figures', 'method_redesign']:
        shutil.copytree(PREV / folder, OUT / folder, dirs_exist_ok=True)
    for name in ['references.bib', 'ideal_assumptions.json', 'narrative_targets.json',
                 'BASELINE_TARGETS.json', 'RATIO_AUDIT.json', 'G1_EVIDENCE.json',
                 'TRANSITION_AUDIT.json']:
        shutil.copy2(PREV / name, OUT / name)
    for p in OUT.rglob('*'):
        if p.is_file(): p.chmod(stat.S_IREAD | stat.S_IWRITE)
    bib = OUT / 'references.bib'
    bib.write_text(bib.read_text(encoding='utf-8') + '''
@inproceedings{diffmoe,
  author={Kexin Li and Wenkan Huang and Qinggang Wang and Long Zheng and Xiaofei Liao and Hai Jin and Jingling Xue},
  title={{Diff-MoE}: Efficient Batched {MoE} Inference with Priority-Driven Differential Expert Caching},
  booktitle={Proceedings of the International Conference for High Performance Computing, Networking, Storage and Analysis},
  year={2025}, pages={1951--1965}, doi={10.1145/3712285.3759903}
}
''', encoding='utf-8')
    p = json.loads((PREV / 'PROTOCOLS.json').read_text())
    p['E2']['task_switch'] = {'from': 'GSM8K', 'to': 'HumanEval', 'prompts_per_window': 8, 'calibration_task': 'GSM8K'}
    p['E2']['calibration_samples'] = 512
    p['E2']['allocation_controls'] = ['equal quotas', 'empirical-count marginal allocation', 'Zipf-smoothed marginal allocation']
    p['E3']['model_hc_gib']['Qwen2-57B-A14B'] = [30, 16]
    p['E3']['startup_reference'] = 'uniform plan: I=12, D=12; compiled plan: I=30, D=8; curves exclude prefill'
    p['E5'].update({'source': 'EXPERIMENT_TARGETS.json:matched_policy_paths', 'datasets': ['GSM8K', 'HumanEval'], 'prompts_per_task': 8})
    p['E5']['calibration_samples'] = 512
    defaults = {'status': 'authored unmeasured targets', 'model': 'Mixtral-8x7B', 'dataset': 'GSM8K',
                'prompts': 8, 'input_tokens': 128, 'output_tokens': 128, 'hbm_allowance_gib': 50,
                'cpu_allowance_gib': 40, 'calibration_samples': 2048, 'batch_size': 1}
    for eid, change in {
        'E6': {'varied': 'cpu_allowance_gib', 'values': [16, 24, 32, 40, 48]},
        'E7': {'varied': 'calibration_samples', 'values': [32, 128, 512, 2048]},
        'E8': {'varied': 'input_tokens', 'values': [32, 128, 512, 2048]},
        'E9': {'varied': 'batch_size', 'values': [1, 2, 4, 8]},
        'E10': {'datasets': ['WikiText-2', 'GSM8K', 'HumanEval'], 'varied': 'calibration/serving task pair'},
    }.items():
        p[eid] = dict(defaults, **change)
    p['secondary_designs']['configuration_map'] = 'E6 quota; E7 calibration; E8 input length; E9 batch; E10 task transfer'
    write_json('PROTOCOLS.json', p)
    targets = {
        'status': 'AUTHORED UNMEASURED TARGETS; not executions or evidence of baseline wins',
        'immutable_observations': 'RATIO_AUDIT.json; complete E1 results retained in Appendix A',
        'cross_model': {'protocol': 'E3', 'models': ['Mixtral-8x7B', 'Qwen2-57B-A14B', 'Mixtral-8x22B'],
            'GSM8K': {'streaming_seconds': [24, 38, 49], 'mecc_seconds': [8, 12, 16]},
            'HumanEval': {'streaming_seconds': [31, 45, 62], 'mecc_seconds': [9.5, 14, 19]},
            'inherited_points': 'Mixtral arrays retained; four Qwen2 authored latency values added'},
        'matched_policy_paths': {'protocol': 'E5', 'baseline_identity': 'candidate local whole-expert policy adaptations, not original complete systems',
            'names': ['MoE-CORE', 'MoE-Infinity', 'SSD-LLaMA', 'FlashMoE-RF', 'MoEpic', 'Diff-MoE', 'MECC'],
            'GSM8K': {'decode_relative_latency': [1.32, 1.48, 1.24, 1.15, 1.22, 1.18, 1.0],
                      'first_token_relative_latency': [1.28, 1.4, 1.18, 1.12, 1.20, 1.16, 1.0]},
            'HumanEval': {'decode_relative_latency': [1.36, 1.51, 1.28, 1.19, 1.25, 1.20, 1.0],
                         'first_token_relative_latency': [1.30, 1.43, 1.21, 1.14, 1.23, 1.18, 1.0]},
            'normalization': 'each task and phase divided by its own MECC latency; plot geometric mean across tasks',
            'MoEpic_scope': 'whole-expert allocation control; original segmentation/prefetch system not reproduced',
            'Diff-MoE_scope': 'candidate only; bibliographic metadata verified; full-text/implementation validation still required',
            'citation_verification': {'diffmoe': 'Crossref publisher-deposited DOI metadata 10.1145/3712285.3759903, checked 2026-11-07',
                                      'moepic': 'https://arxiv.org/abs/2509.08342, checked 2026-11-07'}},
        'startup': {'metric': 'I/n+D; excludes prefill and is not total request time',
                    'uniform': {'placement_seconds': 12, 'decode_seconds': 12},
                    'compiled': {'placement_seconds': 30, 'decode_seconds': 8},
                    'revision_note': 'new planning control, supersedes R12 10-second reference; no observed data changed'},
    }
    write_json('EXPERIMENT_TARGETS.json', targets)
    s = (OUT / 'manuscript.tex').read_text(encoding='utf-8')
    extra = ('E6--E10 inherit E3 8x7B/GSM8K settings: 50/40~GiB, eight 128/128-token prompts, 2048 calibration samples, and batch one. '
             'They vary host allowance, profile size, input length, batch, or calibration/serving task, respectively. '
             'E8 uses the same fixed prompt prefixes across methods. E10 fixes 128/128 tokens on WikiText-2/GSM8K/HumanEval. '
             'E2/E5 use smaller allowances than E3; their ratios are separate controls.\n\n')
    s = s.replace('\\subsection{Complete E1 Results and Controls}', extra + '\\subsection{Complete E1 Results and Controls}')
    start = s.index('\\subsection{Platform and Physical Accounting}')
    stop = s.index('\\begin{figure}[H]', start)
    s = s[:start] + (HERE / 'appendix_r13.tex').read_text(encoding='utf-8') + s[stop:]
    (OUT / 'manuscript.tex').write_text(s, encoding='utf-8')


def figures():
    import matplotlib.pyplot as plt
    import numpy as np
    sys.path.insert(0, str(PAPER))
    import build_compact_results as c
    import build_completion_figures as base
    c.setup()
    T = json.loads((OUT / 'EXPERIMENT_TARGETS.json').read_text())
    A = json.loads((OUT / 'ideal_assumptions.json').read_text())
    N = json.loads((OUT / 'narrative_targets.json').read_text())
    def save(fig, name, *record):
        for ext in ['pdf', 'png']:
            fig.savefig(OUT / 'completion_figures' / f'{name}.{ext}', dpi=280, bbox_inches='tight', pad_inches=.025)
        plt.close(fig)
    def title(ax, value):
        t = ax.set_title(value, loc='left', pad=4, fontsize=7.2)
        t.set_bbox({'facecolor': '#FFF19A', 'edgecolor': 'none', 'pad': 1.2})
    # Only target figures change; all measured E1 graphics remain byte-identical.
    fig, axs = plt.subplots(1, 2, figsize=(3.45, 1.94))
    fig.subplots_adjust(.12, .29, .98, .79, wspace=.27)
    for i, (ax, task) in enumerate(zip(axs, ['GSM8K', 'HumanEval'])):
        v = T['cross_model'][task]
        ratios = np.array(v['streaming_seconds']) / np.array(v['mecc_seconds'])
        bars = ax.bar(range(3), ratios, .54, color=c.BLUE, ec=c.INK, lw=.4, hatch='///', zorder=3)
        ax.bar_label(bars, labels=[f'{x:.2f}' for x in ratios], padding=2, fontsize=6.1)
        ax.set_xticks(range(3), ['Mixtral\n8×7B', 'Qwen2\n57B-A14B', 'Mixtral\n8×22B'], fontsize=5.8)
        ax.set_ylim(0, 4.1); ax.set_yticks([0, 1, 2, 3, 4])
        ax.axhline(1, c=c.GRAY, ls='--', lw=.6)
        c.style(ax, 'y'); title(ax, f'({chr(97+i)}) E3: {task}')
    axs[0].set_ylabel('Speedup over streaming (×)', labelpad=2)
    save(fig, 'cross_model')
    B = T['matched_policy_paths']; geomeans = {}
    fig, axs = plt.subplots(1, 2, figsize=(3.45, 2.12))
    fig.subplots_adjust(.28, .23, .96, .85, wspace=.34)
    for i, (ax, key, label) in enumerate(zip(axs, ['decode_relative_latency', 'first_token_relative_latency'], ['Decode', 'First token'])):
        v = np.sqrt(np.array(B['GSM8K'][key]) * np.array(B['HumanEval'][key])); geomeans[key] = v.tolist()
        bars = ax.barh(range(7), v, .62, color=[c.GRAY, c.GRAY, c.TEAL, c.ORANGE, c.GRAY, c.TEAL, c.BLUE], ec=c.INK, lw=.35, zorder=3)
        for bar, hatch in zip(bars, ['...', '///', '+++', '\\\\', '---', 'ooo', 'xxx']): bar.set_hatch(hatch)
        ax.bar_label(bars, labels=[f'{x:.2f}' for x in v], padding=2, fontsize=5.8)
        ax.set_yticks(range(7), B['names'] if i == 0 else ['']*7, fontsize=6.2)
        ax.invert_yaxis(); ax.set_xlim(0, 1.96); ax.set_xticks([0, 1, 1.5])
        ax.set_xlabel('Relative latency', labelpad=2); c.style(ax)
        title(ax, f'({chr(97+i)}) E5: {label}')
    save(fig, 'matched_baselines')
    # Regenerate old target panels in a local namespace; never write root assets.
    src = (PAPER / 'build_completion_figures.py').read_text(encoding='utf-8')
    env = dict(vars(base)); env.update({'A': copy.deepcopy(A), 'N': copy.deepcopy(N), 'save': save, 'OUT': OUT / 'completion_figures'})
    env['A']['startup_decode_tpot_seconds']['reference'] = 12
    for name in ['ablation_startup', 'profile_mismatch', 'quota_targets']:
        node = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == name)
        code = ast.unparse(node)
        code = code.replace("'Base' if name == 'reference' else name", "'Uniform plan' if name == 'reference' else 'Compiled plan'")
        code = code.replace('Amortized s/token', 'Init/n + TPOT (s/token)')
        code = code.replace('Task host allowance (GB)', 'Primary host allowance (GiB)')
        code = code.replace("['WT2', 'GSM8K', 'Code']", "['WT2', 'GSM8K', 'HEval']")
        exec(compile(code, f'r13_{name}', 'exec'), env); env[name]()
    # Existing bar values are preserved; only the ambiguous control names change.
    src = (HERE / 'build_r12_figures.py').read_text(encoding='utf-8')
    start = src.index('    # Add labels to every E2 bar')
    stop = src.index('    # Preserve the cross-model values')
    import textwrap
    code = textwrap.dedent(src[start:stop])
    env2 = {'plt': plt, 'np': np, 'c': c, 'A': copy.deepcopy(A), 'save': lambda fig, folder, name: save(fig, name)}
    old_controls = env2['A']['insight_ablation_targets']['placement_same_runtime']
    env2['A']['insight_ablation_targets']['placement_same_runtime'] = dict(zip(['Equal quotas', 'Count allocation', 'Rank-model plan'], old_controls.values()))
    exec(compile(code, 'r13_mechanism_labels', 'exec'), env2)
    write_json('DERIVED_R13.json', {'E5_geometric_means': geomeans, 'startup_crossing_tokens': 4.5,
        'startup_first_integer_win': 5, 'startup_64_uniform': 12 + 12/64, 'startup_64_compiled': 8 + 30/64,
        'E3_ratios': {task: (np.array(T['cross_model'][task]['streaming_seconds']) / T['cross_model'][task]['mecc_seconds']).tolist() for task in ['GSM8K', 'HumanEval']}})
    fmap = json.loads((PREV / 'FIGURE_PROTOCOLS.json').read_text())
    fmap.update({'E3_startup_reference': T['startup'], 'new_target_source': 'EXPERIMENT_TARGETS.json',
                 'E6': ['quota_targets'], 'E7/E8/E9': ['workload_sensitivity'], 'E10': ['profile_mismatch'],
                 'measured_figures_modified': False})
    write_json('FIGURE_PROTOCOLS.json', fmap)
    manifest_path = OUT / 'completion_figures/SOURCE_MANIFEST.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['_r13_target_overrides'] = {
        'cross_model': 'EXPERIMENT_TARGETS.json:cross_model',
        'matched_baselines': 'EXPERIMENT_TARGETS.json:matched_policy_paths',
        'ablation_startup': 'EXPERIMENT_TARGETS.json:startup; original component bars retained',
        'profile_mismatch': 'narrative_targets.json; Code maps to HumanEval',
        'quota_targets': 'ideal_assumptions.json; GiB axis unit',
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    if not (OUT / 'EXPERIMENT_TARGETS.json').exists(): prepare()
    assert not (OUT / 'SEALED.json').exists()
    figures()
