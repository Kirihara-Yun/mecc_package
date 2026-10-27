"""D1 controlled cache experiment on synthetic, frozen request streams.

This is an isolated abstract model, NOT the CUDA implementation or MoE inference.
Equal-size immutable objects; H=2/C=4; no mirrors, prefetch or timing model.
Training and test streams are independent. No test-frequency oracle is used.
"""
from collections import Counter, OrderedDict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import subprocess
import statistics

N, H, C, PHASE, WINDOW = 16, 2, 4, 512, 64
SEEDS = [3, 11, 23, 37, 47, 61, 79, 97]
ARMS = ['random_static', 'profile_static', 'random_joint', 'profile_joint',
        'random_independent', 'profile_independent']
OUT = Path(__file__).resolve().parents[1] / 'results/raw/motivation_causal_replay_20261027_v2.json'


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':')).encode()).hexdigest()


def local_stream(rng, weights, count):
    result = []
    for _ in range(count // 32):
        pool = []
        while len(pool) < 4:
            item = rng.choices(range(N), weights=weights)[0]
            if item not in pool:
                pool.append(item)
        result.extend(rng.choices(pool, k=32))
    return result


def replay(trace, ranking, joint, independent=False):
    gpu = OrderedDict((e, None) for e in ranking[:H])
    cpu = OrderedDict((e, None) for e in ranking[H:H+C])
    sources, eviction_reloads, evicted = [], 0, set()
    d2h, overlap_sum, unique_sum = 0, 0, 0
    peak = {'hbm': len(gpu), 'cpu': len(cpu)}
    for eid in trace:
        if eid in gpu:
            gpu.move_to_end(eid); tier = 'hbm'
        else:
            if eid in cpu:
                tier = 'cpu'
                if joint:
                    cpu.pop(eid)
                elif independent:
                    cpu.move_to_end(eid)
            else:
                tier = 'ssd'
                eviction_reloads += eid in evicted
                if independent:
                    cpu[eid] = None
                    if len(cpu) > C:
                        cpu.popitem(last=False)
            if len(gpu) == H:
                victim, _ = gpu.popitem(last=False)
                evicted.add(victim)
                if joint:
                    cpu[victim] = None
                    d2h += 1  # This abstract exclusive model must return the victim.
                    if len(cpu) > C:
                        cpu.popitem(last=False)
            gpu[eid] = None
        sources.append(tier)
        overlap_sum += len(set(gpu) & set(cpu))
        unique_sum += len(set(gpu) | set(cpu))
        assert len(gpu) <= H and len(cpu) <= C
        if joint:
            assert not (set(gpu) & set(cpu))
        peak['hbm'] = max(peak['hbm'], len(gpu))
        peak['cpu'] = max(peak['cpu'], len(cpu))
    counts = Counter(sources)
    return {
        'policy': ('joint' if joint else 'static'),
        'ssd_misses': counts['ssd'], 'requests': len(trace),
        'ssd_per_1000': counts['ssd'] * 1000 / len(trace),
        'counts': dict(counts), 'eviction_reloads': eviction_reloads,
        'ssd_by_window': [sources[i:i+WINDOW].count('ssd') * 1000 / WINDOW
                          for i in range(0, len(trace), WINDOW)],
        'startup_misses': {str(k): sources[:k].count('ssd') for k in [16,32,64,128,256]},
        'h2d_objects': counts['cpu'] + counts['ssd'], 'd2h_objects': d2h,
        'initial_read_objects': H+C, 'peak_slots': peak,
        'mean_overlap_objects': overlap_sum / len(trace),
        'mean_unique_objects': unique_sum / len(trace),
        'ssd_mask': [x == 'ssd' for x in sources],
    }


def global_lru_mask(trace, ranking):
    cache = OrderedDict((e, None) for e in ranking[H:H+C]+ranking[:H])
    result = []
    for eid in trace:
        result.append(eid not in cache)
        cache[eid] = None
        cache.move_to_end(eid)
        if len(cache) > H+C:
            cache.popitem(last=False)
    return result


def main():
    assert H+C < N
    weights = [1/(i+1)**1.2 for i in range(N)]
    shifted = weights[8:] + weights[:8]
    workloads = {name: [] for name in ['stationary', 'drift', 'phase_shuffled', 'uniform']}
    for seed in SEEDS:
        train_rng, test_rng, order_rng = (random.Random(seed+x) for x in [1000,2000,3000])
        training = local_stream(train_rng, weights, 1024)
        ranking = sorted(range(N), key=lambda e: (-training.count(e), e))
        unprofiled = list(range(N)); order_rng.shuffle(unprofiled)
        phase_a = local_stream(test_rng, weights, PHASE)
        phase_b = local_stream(test_rng, shifted, PHASE)
        shuffled_a, shuffled_b = phase_a[:], phase_b[:]
        random.Random(seed+4000).shuffle(shuffled_a)
        random.Random(seed+5000).shuffle(shuffled_b)
        assert Counter(phase_a) == Counter(shuffled_a)
        assert Counter(phase_b) == Counter(shuffled_b)
        traces = {'stationary': phase_a+local_stream(test_rng, weights, PHASE),
                  'drift': phase_a+phase_b,
                  'phase_shuffled': shuffled_a+shuffled_b,
                  'uniform': test_rng.choices(range(N), k=2*PHASE)}
        for name, trace in traces.items():
            results = []
            for arm in ARMS:
                record = replay(trace, ranking if arm.startswith('profile') else unprofiled,
                                arm.endswith('joint'), arm.endswith('independent'))
                record['policy'] = arm
                ssd_mask = record.pop('ssd_mask')
                if arm.endswith('joint'):
                    assert ssd_mask == global_lru_mask(trace, ranking if arm.startswith('profile') else unprofiled)
                    record['equals_global_lru_each_request'] = True
                results.append(record)
            workloads[name].append({'seed': seed, 'training_sha256': digest(training),
                                    'trace_sha256': digest(trace), 'trace': trace,
                                    'profile_ranking': ranking, 'random_ranking': unprofiled,
                                    'results': results})
    summaries = {}
    for name, trials in workloads.items():
        summaries[name] = {}
        for arm in ARMS:
            rows = [next(r for r in t['results'] if r['policy'] == arm) for t in trials]
            values = [r['ssd_per_1000'] for r in rows]
            summaries[name][arm] = {
                'ssd_per_1000_mean': statistics.mean(values),
                'ssd_per_1000_sd': statistics.stdev(values),
                'startup64_mean': statistics.mean(r['startup_misses']['64'] for r in rows),
                'd2h_objects_mean': statistics.mean(r['d2h_objects'] for r in rows),
            }
    output = {
        'platform': 'CPU abstract cache replay (no GPU/SSD timing)',
        'run_time': datetime.now(timezone.utc).isoformat(), 'evidence_level': 'D1',
        'config': {'n_experts': N, 'k_h': H, 'k_c': C, 'phase_requests': PHASE,
                   'window_requests': WINDOW, 'seeds': SEEDS, 'alpha': 1.2,
                   'training_requests': 1024, 'prefetch': False, 'hidden_cpu_mirrors': False,
                   'training_generator': 'same local-stream generator as stationary, independent RNG',
                   'static_independent_cross_tier_duplicates': 'allowed and counted against each physical cap',
                   'joint_cross_tier_duplicates': 'forbidden',
                   'object_size': 'one abstract equal-size unit',
                   'interpretation': 'controlled mechanism only; no real MoE trace or throughput'},
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'git_commit': subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
        'workloads': [{'workload': name, 'paired_trials': trials} for name, trials in workloads.items()],
        'summaries': summaries,
        'checks': {'capacity_assertions': True, 'independent_train_test_rng': True,
                   'per_phase_histogram_preserved': True, 'all_seeds_retained': True,
                   'joint_equals_global_lru_demand_misses': True},
        'counterexample': {'trace': [2,1], 'n': 3, 'h': 1, 'c': 1,
                          'source': 'THEORY TH-006; not run with the H=2/C=4 model here'},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(OUT)
    for block in output['workloads']:
        print(block['workload'], {arm: round(sum(next(r for r in t['results'] if r['policy']==arm)['ssd_per_1000']
                                                 for t in block['paired_trials'])/len(SEEDS), 2)
                                  for arm in ARMS})


if __name__ == '__main__':
    main()
