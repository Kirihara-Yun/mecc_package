#!/usr/bin/env python3
"""Frozen Mixtral policy correctness diagnostic; never a performance result."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback
import torch
import torch.nn.functional as F
from transformers import AutoConfig, AutoTokenizer
from compile_config import compile_plan
from mixtral_tiered import TieredSparseMoe, build_tiered_model
from run_e2e import _forward, measure_ppl
from store_manifest import expected_manifest, validate_store
from tiered_engine import SSDExpertStore

POLICIES = ('naive', 'ours', 'swapmoe')
ATOL, RTOL, PPL_DELTA = .05, .001, .01

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def publish(path: str, value: dict) -> None:
    dst = Path(path).resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.' + dst.name, suffix='.tmp', dir=dst.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(value, out, ensure_ascii=False, indent=2, allow_nan=False)
            out.write('\n'); out.flush(); os.fsync(out.fileno())
        os.replace(tmp, dst)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def phase(args, value, **kw):
    publish(args.status_file, {'phase': value,
        'updated_at': datetime.now().astimezone().isoformat(), **kw})
    print('[phase]', value, kw, flush=True)


def pool_bytes(caches):
    """Logical live storage bytes by cache role, deduplicated by storage pointer."""
    roles = {'gpu': set(), 'cpu_mirror': set(), 'cpu_pool': set(),
             'cpu_staging': set()}
    sizes = {}
    pinned = set()
    for cache in caches:
        entries = [
            ('gpu', (pair[0] for pair in cache.gpu.values())),
            ('cpu_mirror', (pair[1] for pair in cache.gpu.values())),
            ('cpu_pool', cache.cpu.values()),
            ('cpu_pool', cache.static_cpu.values()),
            ('cpu_staging', cache._prefetch_buf.values()),
            ('cpu_staging', getattr(cache, '_nearmiss_buf', {}).values()),
        ]
        for role, weights in entries:
            for ws in weights:
                if ws is None:
                    continue
                for tensor in (ws.w1, ws.w3, ws.w2):
                    storage = tensor.untyped_storage()
                    key = (tensor.device.type, tensor.device.index, storage.data_ptr())
                    sizes[key] = storage.nbytes()
                    roles[role].add(key)
                    if tensor.device.type == 'cpu' and tensor.is_pinned():
                        pinned.add(key)
    return {
        'role_unique_bytes': {role: sum(sizes[key] for key in keys)
                              for role, keys in roles.items()},
        'all_unique_cpu_bytes': sum(size for key, size in sizes.items()
                                    if key[0] == 'cpu'),
        'all_unique_gpu_bytes': sum(size for key, size in sizes.items()
                                    if key[0] == 'cuda'),
        'all_unique_cpu_pinned_bytes': sum(sizes[key] for key in pinned),
        'note': 'live tensor storage only; roles can share a storage; excludes trunk, allocator, page cache',
    }


def checkpoint(args, policy, stage, device, caches=None):
    if not args.resource_trace:
        return
    row = {'time': datetime.now().astimezone().isoformat(timespec='milliseconds'),
           'policy': policy, 'stage': stage,
           'cuda_allocated_bytes': torch.cuda.memory_allocated(device),
           'cuda_reserved_bytes': torch.cuda.memory_reserved(device),
           'pool_bytes': pool_bytes(caches) if caches is not None else None}
    path = Path(args.out).resolve().parent / 'memory_checkpoints.jsonl'
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + '\n')
        stream.flush(); os.fsync(stream.fileno())

def fixture(path, n):
    raw = Path(path).read_bytes()
    obj = json.loads(raw.decode('utf-8'))
    prompts, ppl_text = obj.get('prompts'), obj.get('ppl_text')
    if obj.get('kind') != 'repository_diagnostic_not_benchmark':
        raise ValueError('fixture must be marked repository_diagnostic_not_benchmark')
    if not isinstance(prompts, list) or len(prompts) != n or any(
            not isinstance(p, str) or not p.strip() for p in prompts):
        raise ValueError('fixture prompts must contain exactly n nonempty strings')
    if not isinstance(ppl_text, str) or not ppl_text.strip():
        raise ValueError('fixture ppl_text missing')
    meta = {'source': obj['kind'], 'file_sha256': digest(raw),
            'prompts_sha256': digest(json.dumps(
                prompts, ensure_ascii=False, separators=(',', ':')).encode()),
            'ppl_text_sha256': digest(ppl_text.encode())}
    return prompts, ppl_text, meta

def route_hooks(model):
    routes, handles = {}, []
    for module in model.modules():
        if not isinstance(module, TieredSparseMoe):
            continue
        routes[module.layer_id] = []
        def hook(mod, _input, output, lid=module.layer_id):
            gate_device = output[1].detach()
            selected = F.softmax(gate_device, dim=1, dtype=torch.float).topk(
                mod.top_k, dim=-1).indices.cpu()
            routes[lid].append((selected.tolist(), gate_device.float().cpu()))
        handles.append(module.register_forward_hook(hook))
    if not routes:
        raise RuntimeError('no Mixtral MoE modules found')
    return routes, handles

@torch.no_grad()
def trace(model, ids, steps, forced=None):
    routes, handles = route_hooks(model)
    logits, greedy, past = [], [], None
    try:
        for i in range(steps):
            feed = ids if i == 0 else torch.tensor(
                [[forced[i-1] if forced is not None else greedy[-1]]],
                dtype=torch.long, device=ids.device)
            out, past = _forward(model, feed, past, True, use_amp=False)
            last = out[:, -1, :].detach().float().cpu()
            if not torch.isfinite(last).all():
                raise RuntimeError('nonfinite logits at step ' + str(i))
            logits.append(last)
            greedy.append(int(last.argmax(-1).item()))
        torch.cuda.synchronize(ids.device)
    finally:
        for handle in handles:
            handle.remove()
    for lid, calls in routes.items():
        if len(calls) != steps:
            raise RuntimeError(f'layer {lid}: {len(calls)} calls, expected {steps}')
    return {'routes': routes, 'logits': logits, 'greedy': greedy}

def compare(ref, got):
    first_route = None
    gate_error = 0.
    for lid in sorted(ref['routes']):
        for i, ((ra, ga), (rb, gb)) in enumerate(zip(
                ref['routes'][lid], got['routes'][lid])):
            if ra != rb and first_route is None:
                first_route = {'layer': lid, 'step': i,
                               'reference_selected': ra, 'observed_selected': rb}
            gate_error = max(gate_error, float((ga-gb).abs().max()))
    logit_error = max(float((a-b).abs().max()) for a,b in zip(
        ref['logits'], got['logits']))
    logit_close = all(bool(torch.allclose(a,b,atol=ATOL,rtol=RTOL))
                      for a,b in zip(ref['logits'],got['logits']))
    first_logit = next((i for i,(a,b) in enumerate(zip(
        ref['logits'],got['logits'])) if not torch.allclose(
            a,b,atol=ATOL,rtol=RTOL)), None)
    token_equal = ref['greedy'] == got['greedy']
    first_token = next((i for i,(a,b) in enumerate(zip(
        ref['greedy'],got['greedy'])) if a != b), None)
    return {'passed': first_route is None and logit_close and token_equal,
            'route_equal': first_route is None, 'first_route_mismatch': first_route,
            'logits_allclose': logit_close, 'max_logit_abs_error': logit_error,
            'first_logit_mismatch_step': first_logit,
            'max_gate_abs_error': gate_error, 'tokens_equal': token_equal,
            'first_token_mismatch_step': first_token,
            'greedy_tokens': got['greedy']}

def run(args):
    requested = [p.strip() for p in args.policies.split(',') if p.strip()]
    if not requested or any(p not in POLICIES for p in requested):
        raise ValueError('policies must be a nonempty subset of naive,ours,swapmoe')
    if requested[0] != 'naive':
        raise ValueError('naive must be the first (reference) policy')
    policies = [p for p in POLICIES if p in requested]
    if not 2 <= args.max_new_tokens <= 8:
        raise ValueError('max_new_tokens must be 2..8')
    if not torch.cuda.is_available() or 'A100' not in torch.cuda.get_device_name(0):
        raise RuntimeError('this diagnostic requires an A100')
    device = torch.device('cuda')
    torch.manual_seed(0); torch.cuda.manual_seed_all(0)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    prompts, ppl_text, meta = fixture(args.fixtures, args.n_prompts)
    state = str(Path(args.state_path).resolve())
    tokenizer = AutoTokenizer.from_pretrained(state, trust_remote_code=True,
                                              local_files_only=True)
    cfg = AutoConfig.from_pretrained(state, trust_remote_code=True,
                                    local_files_only=True)
    ids = [tokenizer(p, return_tensors='pt').input_ids for p in prompts]
    ppl_ids = tokenizer(ppl_text, return_tensors='pt').input_ids[:,:args.ppl_tokens]
    if any(not 2 <= x.shape[1] <= 64 for x in ids):
        raise ValueError('prompt must tokenize to 2..64 tokens')
    if ppl_ids.shape[1] != args.ppl_tokens:
        raise ValueError('offline PPL text shorter than frozen token count')
    meta.update({'prompt_input_tokens':[int(x.shape[1]) for x in ids],
                 'prompt_token_sha256':[digest(json.dumps(x.tolist()).encode())
                                        for x in ids],
                 'ppl_input_tokens':int(ppl_ids.shape[1]),
                 'ppl_token_sha256':digest(json.dumps(ppl_ids.tolist()).encode())})
    print('[inputs]', json.dumps(meta, ensure_ascii=False), flush=True)
    plan = compile_plan(args.model, args.hbm_budget, args.cpu_budget,
                        alpha=args.alpha, per_layer_alpha=None)
    store = SSDExpertStore(args.store_root, cfg.hidden_size, cfg.intermediate_size)
    expected = expected_manifest(model=args.model, model_type='mixtral',
        state_path=state, n_layers=plan.n_layers, n_experts=plan.n_experts,
        hidden=cfg.hidden_size, ffn=cfg.intermediate_size,
        expert_bytes=store.total_bytes, dtype=str(store.dtype))
    if not validate_store(args.store_root, expected, allow_empty=False):
        raise RuntimeError('expert store must already be complete')
    result = {'mode':'diagnostic_correctness','platform':args.platform,
        'run_time':datetime.now().astimezone().isoformat(),
        'model':args.model,'model_revision':Path(state).name,
        'store_manifest_sha256':digest(
            (Path(args.store_root)/'manifest.json').read_bytes()),
        'fixture':meta,'compiled_plan':asdict(plan),
        'config':{'hbm_budget_gb':args.hbm_budget,'cpu_budget_gb':args.cpu_budget,
                  'max_new_tokens':args.max_new_tokens,'ppl_tokens':args.ppl_tokens,
                  'policies':list(policies),'cold_ssd':True,'uniform':True,
                  'atol':ATOL,'rtol':RTOL,'max_ppl_delta':PPL_DELTA},
        'results':{}}
    reference = None
    reference_ppl = None
    for policy in policies:
        phase(args,'running_policy',policy=policy,stage='before_load',
              completed_policies=list(result['results']))
        checkpoint(args,policy,'before_load',device)
        model,caches = build_tiered_model(state,state,store,device,
            plan.placement,plan.k_h,plan.k_c,policy=policy,cold_ssd=True,
            per_layer_k_h=plan.per_layer_k_h,per_layer_k_c=plan.per_layer_k_c)
        checkpoint(args,policy,'after_load',device,caches)
        phase(args,'running_policy',policy=policy,stage='after_load',
              completed_policies=list(result['results']))
        cases = [trace(model, inp.to(device), args.max_new_tokens,
                 None if reference is None else reference[i]['greedy'])
                 for i,inp in enumerate(ids)]
        ppl = measure_ppl(model,tokenizer,ppl_text,args.ppl_tokens,device,True)
        if ppl is None or not math.isfinite(ppl):
            raise RuntimeError(policy + ': nonnumeric PPL')
        if reference is None:
            reference,reference_ppl = cases,ppl
            comparisons = [{'passed':True,'reference':True,
                            'greedy_tokens':c['greedy']} for c in cases]
        else:
            comparisons = [compare(a,b) for a,b in zip(reference,cases)]
        passed = all(c['passed'] for c in comparisons) and abs(
            ppl-reference_ppl) <= PPL_DELTA
        result['results'][policy] = {'passed':passed,'ppl':ppl,
            'ppl_delta_vs_naive':ppl-reference_ppl,'cases':comparisons,
            'cuda_allocated_bytes_after':torch.cuda.memory_allocated(device),
            'cuda_reserved_bytes_after':torch.cuda.memory_reserved(device)}
        publish(args.partial_out,result)
        print('[policy]',policy,'passed=',passed,'ppl=',ppl,flush=True)
        checkpoint(args,policy,'before_release',device,caches)
        del model,caches,cases
        gc.collect();torch.cuda.empty_cache()
        checkpoint(args,policy,'after_release',device)
        phase(args,'policy_released',policy=policy,
              completed_policies=list(result['results']))
    result['passed'] = all(v['passed'] for v in result['results'].values())
    publish(args.out,result)
    if not result['passed']:
        phase(args,'failed',error_type='CorrectnessMismatch',
              output=str(Path(args.out).resolve()))
        raise SystemExit(2)
    phase(args,'complete',output=str(Path(args.out).resolve()))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('model','state_path','store_root','fixtures','platform',
                'out','partial_out','status_file'):
        parser.add_argument('--'+key,required=True)
    for key in ('hbm_budget','cpu_budget','alpha'):
        parser.add_argument('--'+key,type=float,required=True)
    for key in ('max_new_tokens','n_prompts','ppl_tokens'):
        parser.add_argument('--'+key,type=int,required=True)
    parser.add_argument('--policies',required=True)
    parser.add_argument('--resource_trace',action='store_true')
    args = parser.parse_args()
    monitor = None
    try:
        if args.resource_trace:
            monitor = subprocess.Popen([sys.executable,
                str(Path(__file__).with_name('resource_monitor.py')),
                '--pid',str(os.getpid()),
                '--out',str(Path(args.out).resolve().parent / 'resource_trace.jsonl'),
                '--status-file',args.status_file,'--interval','1.0'],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
        run(args)
    except SystemExit:
        raise
    except Exception as exc:
        traceback.print_exc()
        phase(args,'failed',error_type=type(exc).__name__,error=str(exc))
        raise
    finally:
        if monitor is not None:
            monitor.terminate()
            try:
                monitor.wait(timeout=5)
            except subprocess.TimeoutExpired:
                monitor.kill(); monitor.wait()

if __name__ == '__main__':
    main()
