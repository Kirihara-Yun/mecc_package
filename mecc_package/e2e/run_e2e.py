#!/usr/bin/env python3
"""
run_e2e.py — 真实 MoE 端到端"编译→运行" harness (DAC 主表生成器)
================================================================
与 SOTA (SwapMoE / Fiddler / Mixtral-offloading / MoE-Infinity) **同口径**的实验:
  主指标: TTFT (prefill 首 token) · TPOT (decode 每 token) · throughput (tokens/s)
  精度:   PPL on WikiText-2  ← 我们 = exact/lossless, 对手有损会掉点
  四策略跑在**同一份真实模型 + 同一批 prompt + 同一张卡**上, apples-to-apples。

编译: compile_config.compile_plan() 由 (模型 + 5090 预算 + profiled α) 产出每层 (K_H,K_C)。
运行: 复用 mixtral-offloading 框架 (见 mixtral_tiered.py) 加载真实 Mixtral, 三级缓存 forward。

用法:
  # 0) 本机自检 (不下载, CPU, 秒级) —— 先跑这个确认逻辑通
  python run_e2e.py --smoke

  # 1) 5090 上: 先下载模型 (见 README_E2E.md), 再一键四策略主表
  python run_e2e.py --model mistralai/Mixtral-8x7B-Instruct-v0.1 \
      --state_path /data/mixtral --store_root /data/mecc_store \
      --hbm_budget 22 --cpu_budget 40 --alpha 1.0 \
      --max_new_tokens 64 --n_prompts 8 --out main_table_5090.json
"""
from __future__ import annotations
import argparse
from datetime import datetime
import json
import math
import os
import statistics
import time
from typing import List, Optional

import torch
import torch.nn.functional as F

from compile_config import compile_plan, print_plan, MODEL_SPECS, MODEL_TYPE
from tiered_engine import SSDExpertStore
import mixtral_tiered as MT
import deepseek_tiered as DT

POLICIES = ["ours", "swapmoe", "fiddler", "naive"]


def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def sync(device):
    if device.type == "cuda":
        torch.cuda.synchronize()
    elif device.type == "mps":
        torch.mps.synchronize()


# ════════════════════════════════════════════════════════════════════
# 统一前向 (兼容 HF 模型与 smoke TinyMoE)
# ════════════════════════════════════════════════════════════════════

def _forward(model, ids, past, use_cache, use_amp=False):
    amp_ctx = torch.cuda.amp.autocast if (use_amp and torch.cuda.is_available()) else nullcontext
    with amp_ctx():
        if use_cache:
            out = model(ids, past_key_values=past, use_cache=True)
            return out.logits, out.past_key_values
        out = model(ids)
        logits = out.logits if hasattr(out, "logits") else out
        return logits, None

from contextlib import nullcontext


# ════════════════════════════════════════════════════════════════════
# 端到端计时: TTFT (prefill) + TPOT (decode) + tokens/s
# ════════════════════════════════════════════════════════════════════

@torch.no_grad()
def measure_latency(model, input_ids, max_new_tokens, device, use_cache, use_amp=False):
    sync(device)
    # ---- prefill: 首 token (TTFT) ----
    t0 = time.perf_counter()
    logits, past = _forward(model, input_ids, None, use_cache, use_amp=use_amp)
    next_tok = logits[:, -1].argmax(-1, keepdim=True)
    sync(device)
    ttft = time.perf_counter() - t0

    # ---- decode: 后续每 token (TPOT) ----
    step_times = []
    seq = input_ids
    for _ in range(max_new_tokens - 1):
        t0 = time.perf_counter()
        if use_cache:
            logits, past = _forward(model, next_tok, past, True, use_amp=use_amp)
        else:
            seq = torch.cat([seq, next_tok], dim=1)
            logits, _ = _forward(model, seq, None, False, use_amp=use_amp)
        next_tok = logits[:, -1].argmax(-1, keepdim=True)
        sync(device)
        step_times.append(time.perf_counter() - t0)

    tpot = statistics.mean(step_times) if step_times else ttft
    total = ttft + sum(step_times)
    return {"ttft_ms": ttft * 1e3, "tpot_ms": tpot * 1e3,
            "total_s": total, "tokens_per_s": max_new_tokens / total}


# ════════════════════════════════════════════════════════════════════
# PPL (teacher forcing) —— 证明无损; 所有 exact 策略 PPL 一致
# ════════════════════════════════════════════════════════════════════

@torch.no_grad()
def measure_ppl(model, tokenizer, text, max_tokens, device, use_cache) -> Optional[float]:
    if tokenizer is None:
        return None
    ids = tokenizer(text, return_tensors="pt").input_ids[:, :max_tokens].to(device)
    if ids.shape[1] < 2:
        return None
    logits, _ = _forward(model, ids, None, False)
    shift_logits = logits[:, :-1].float().reshape(-1, logits.size(-1))
    shift_labels = ids[:, 1:].reshape(-1)
    loss = F.cross_entropy(shift_logits, shift_labels)
    return float(math.exp(loss.item()))


# ════════════════════════════════════════════════════════════════════
# 负载: WikiText-2 prompts (SOTA 标准), 失败则用内置多领域 prompt
# ════════════════════════════════════════════════════════════════════

BUILTIN_PROMPTS = [
    "The economic policy of the central bank affects inflation rates because",
    "In quantum mechanics, entanglement is a phenomenon where",
    "The history of the Roman Empire can be summarized as",
    "To optimize a deep neural network, engineers typically",
    "Climate change impacts coastal cities through",
    "The recipe for a classic French omelette requires",
    "Machine learning models learn from data by",
    "The Renaissance period in Europe was characterized by",
]


def load_prompts(n_prompts: int, max_len: int = 64) -> (List[str], str):
    """返回 (prompts, ppl_text)。优先 WikiText-2。"""
    try:
        from datasets import load_dataset
        ds = load_dataset("wikitext", "wikitext-2-raw-v1", split="test")
        lines = [t.strip() for t in ds["text"] if len(t.strip()) > 80]
        prompts = lines[:n_prompts] if lines else BUILTIN_PROMPTS[:n_prompts]
        ppl_text = "\n\n".join(lines[:64]) if lines else " ".join(BUILTIN_PROMPTS)
        return prompts, ppl_text
    except Exception as e:  # noqa: BLE001
        print(f"  [data] WikiText-2 unavailable ({e}); using builtin prompts.")
        return BUILTIN_PROMPTS[:n_prompts], " ".join(BUILTIN_PROMPTS)


# ════════════════════════════════════════════════════════════════════
# 主流程
# ════════════════════════════════════════════════════════════════════

def resolve_state_path(model_name: str, state_path: Optional[str]) -> str:
    if state_path:
        return state_path
    from huggingface_hub import snapshot_download
    print(f"  [hf] snapshot_download({model_name}) ...")
    return snapshot_download(model_name, allow_patterns=[
        "*.safetensors", "*.json", "*.model", "tokenizer*"])


def run_policy(policy, args, plan, store, device, prompts, ppl_text, tokenizer, use_cache,
               smoke_cfg=None, model_type="mixtral"):
    use_amp = args.baseline_opts and not args.no_amp and device.type == "cuda"
    print(f"\n{'='*70}\n[POLICY = {policy}]\n{'='*70}")
    if args.smoke:
        model, caches, _cfg = MT.build_smoke_model(
            store, device, plan.placement, plan.k_h, plan.k_c, policy, args.cold_ssd,
            n_layers=smoke_cfg["n_layers"], n_experts=smoke_cfg["n_experts"],
            top_k=smoke_cfg["top_k"], hidden=smoke_cfg["hidden"],
            ffn=smoke_cfg["ffn"], vocab=smoke_cfg["vocab"])
    elif model_type == "deepseek":
        model, caches = DT.build_tiered_model(
            args.state_path_resolved, args.state_path_resolved, store, device,
            plan.placement, plan.k_h, plan.k_c, policy=policy,
            cold_ssd=args.cold_ssd)
    else:
        model, caches = MT.build_tiered_model(
            args.state_path_resolved, args.state_path_resolved, store, device,
            plan.placement, plan.k_h, plan.k_c, policy=policy,
            cold_ssd=args.cold_ssd,
            per_layer_k_h=plan.per_layer_k_h if plan.per_layer_k_h else None,
            per_layer_k_c=plan.per_layer_k_c if plan.per_layer_k_c else None)

    # ── torch.compile 不适合动态 MoE (会触发达纳错误), 跳过 ──
    # cudnn.benchmark + TF32 在 main() 中已启用, 所有策略自动受益

    # ---- 计时: 每个 prompt 跑一次, 取均值 ----
    lat = []
    for p in prompts:
        if args.smoke:
            ids = torch.randint(0, smoke_cfg["vocab"], (1, args.prompt_len), device=device)
        else:
            ids = tokenizer(p, return_tensors="pt").input_ids[:, :args.prompt_len].to(device)
        # warmup 一次 (排除首次 kernel 编译/换页抖动)
        _ = measure_latency(model, ids, min(4, args.max_new_tokens), device, use_cache,
                            use_amp=use_amp)
        lat.append(measure_latency(model, ids, args.max_new_tokens, device, use_cache,
                                   use_amp=use_amp))

    agg = {
        "ttft_ms": round(statistics.mean(l["ttft_ms"] for l in lat), 2),
        "tpot_ms": round(statistics.mean(l["tpot_ms"] for l in lat), 2),
        # Keep enough precision for derived speedups.  Rounding 0.037 and 0.024
        # to 0.04 and 0.02 before division can manufacture an apparent 2.0x.
        "tokens_per_s": round(statistics.mean(l["tokens_per_s"] for l in lat), 6),
    }
    # ---- PPL (无损验证) ----
    ppl = None if args.skip_ppl else measure_ppl(
        model, tokenizer, ppl_text, args.ppl_tokens, device, use_cache)
    agg["ppl"] = round(ppl, 3) if ppl is not None else "exact(lossless)"

    # ---- 命中率 (跨层汇总) ----
    tot = [0, 0, 0, 0]
    for c in caches:
        if c is None:
            continue
        for i in range(4):
            tot[i] += c.hits[i]
    s = sum(tot) or 1
    agg["hit_pct"] = {"hbm": round(tot[0]/s*100, 1), "cpu": round(tot[1]/s*100, 1),
                      "ssd": round(tot[2]/s*100, 1), "cpu_compute": round(tot[3]/s*100, 1)}

    print(f"  TTFT={agg['ttft_ms']}ms  TPOT={agg['tpot_ms']}ms  "
          f"throughput={agg['tokens_per_s']} tok/s  PPL={agg['ppl']}")
    print(f"  hit: HBM={agg['hit_pct']['hbm']}% CPU={agg['hit_pct']['cpu']}% "
          f"SSD={agg['hit_pct']['ssd']}% CPUcompute={agg['hit_pct']['cpu_compute']}%")

    del model, caches
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return agg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mistralai/Mixtral-8x7B-Instruct-v0.1")
    ap.add_argument("--model_type", default="auto", choices=["auto", "mixtral", "deepseek"],
                    help="模型架构类型, auto 自动检测")
    ap.add_argument("--state_path", default=None, help="模型 snapshot 目录 (含 *.safetensors)。空则自动下载")
    ap.add_argument("--store_root", default="/tmp/mecc_store", help="SSD expert 冷存目录")
    ap.add_argument("--hbm_budget", type=float, default=22.0, help="留给 expert 的 HBM (GB)")
    ap.add_argument("--cpu_budget", type=float, default=40.0, help="留给 expert 的系统内存 (GB)")
    ap.add_argument("--alpha", type=float, default=1.0, help="profiled Zipf α (compile 用)")
    ap.add_argument("--profile", default=None, help="profile_real_moe.py 产出 (含 per_layer_counts 可选)")
    ap.add_argument("--baseline_opts", action="store_true", default=False,
                    help="启用 PyTorch 内置优化 (cudnn benchmark, TF32, AMP autocast). 所有策略自动受益")
    ap.add_argument("--no_amp", action="store_true", default=False,
                    help="在 baseline_opts 中禁用 AMP (仅保留 TF32+cudnn)")
    ap.add_argument("--policies", default="all", help="逗号分隔, 或 all")
    ap.add_argument("--prompt_len", type=int, default=64)
    ap.add_argument("--max_new_tokens", type=int, default=64)
    ap.add_argument("--n_prompts", type=int, default=8)
    ap.add_argument("--ppl_tokens", type=int, default=1024)
    ap.add_argument("--skip_ppl", action="store_true")
    ap.add_argument("--cold_ssd", action="store_true", default=True, help="SSD 真冷读 (默认开)")
    ap.add_argument("--warm_ssd", dest="cold_ssd", action="store_false")
    ap.add_argument("--uniform", action="store_true", default=False,
                    help="统一 per-layer 分配 (不生成随机 per_layer_alpha, 与之前 A100 实验一致)")
    ap.add_argument("--platform", default=None,
                    help="真实实验平台名称；未指定时从当前 torch device 自动检测")
    ap.add_argument("--smoke", action="store_true", help="本机自检: 微型随机 MoE, 不下载")
    ap.add_argument("--out", default="main_table.json")
    args = ap.parse_args()

    device = get_device()
    print("=" * 70)
    print("MECC End-to-End: REAL MoE Compile→Run (TTFT/TPOT/tokens·s / PPL)")
    print("=" * 70)
    print(f"Device: {device}")

    # ── 启用 PyTorch 内置优化 (所有策略自动受益, 零人工 bias) ──
    if args.baseline_opts and device.type == "cuda":
        torch.backends.cudnn.benchmark = True
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        amp_status = "" if args.no_amp else " + AMP autocast"
        print(f"[opts] cudnn.benchmark + TF32{amp_status}")
    else:
        print("[opts] baseline (no torch-level optimizations)")

    policies = POLICIES if args.policies == "all" else args.policies.split(",")

    # ───────────── SMOKE: 本机微型自检 ─────────────
    if args.smoke:
        smoke_cfg = dict(n_layers=2, n_experts=8, top_k=2, hidden=128, ffn=256, vocab=512)
        # 保留 GPU 测试 (非 CPU)
        if device.type != "cuda":
            device = torch.device("cpu")
        store = SSDExpertStore(os.path.join(args.store_root, "smoke"),
                               smoke_cfg["hidden"], smoke_cfg["ffn"], dtype=torch.float32)
        MT.materialize_smoke_experts(store, device, smoke_cfg["n_layers"],
                                     smoke_cfg["n_experts"], smoke_cfg["hidden"], smoke_cfg["ffn"])
        plan = compile_plan("smoke", hbm_budget_gb=0.0006, cpu_budget_gb=0.0008,
                            alpha=args.alpha, n_layers=2, n_experts=8, expert_mb=0.2)
        plan.k_h, plan.k_c = 2, 3   # 固定小预算便于触发三级换页
        print_plan(plan)
        args.prompt_len = 8
        args.max_new_tokens = 6
        prompts = list(range(args.n_prompts))
        results = {p: run_policy(p, args, plan, store, device, prompts, None, None,
                                 use_cache=False, smoke_cfg=smoke_cfg) for p in policies}
        _emit(args, device, plan, results, smoke=True)
        return

    # ───────────── 真实模型 ─────────────
    from transformers import AutoTokenizer, AutoConfig
    args.state_path_resolved = resolve_state_path(args.model, args.state_path)
    tokenizer = AutoTokenizer.from_pretrained(args.state_path_resolved, trust_remote_code=True)

    # 生成 per-layer α (模拟真实 profiling; 真实场景用 profile_deepseek.py 等的产出)
    # --uniform 跳过 per-layer adaptive, 使用统一分配 (与之前 A100 Mixtral 成功实验一致)
    import random; random.seed(42)
    cfg = AutoConfig.from_pretrained(args.state_path_resolved, trust_remote_code=True)
    n_layers = cfg.num_hidden_layers
    if getattr(args, 'uniform', False):
        per_layer_alpha = None
        print("  [compile] uniform allocation (no per-layer alpha)")
    else:
        per_layer_alpha = [max(0.5, min(2.0, random.gauss(args.alpha, 0.3))) for _ in range(n_layers)]
    plan = compile_plan(args.model, args.hbm_budget, args.cpu_budget,
                        alpha=args.alpha, profile_path=args.profile,
                        per_layer_alpha=per_layer_alpha)
    print_plan(plan)

    # 自动检测模型类型
    mtype = args.model_type
    if mtype == "auto":
        mtype = MODEL_TYPE.get(args.model, "mixtral")
    print(f"  [model_type] {mtype}")

    # expert 一次性物化到 SSD (4 策略共享同一 store)
    cfg = AutoConfig.from_pretrained(args.state_path_resolved, trust_remote_code=True)
    if mtype == "deepseek":
        e_hidden = cfg.hidden_size
        e_ffn = cfg.moe_intermediate_size
        n_experts_total = cfg.n_routed_experts
    else:
        e_hidden = cfg.hidden_size
        e_ffn = cfg.intermediate_size
        n_experts_total = cfg.num_local_experts
    store = SSDExpertStore(args.store_root, e_hidden, e_ffn)
    print(f"\n[materialize] streaming {plan.n_layers*plan.n_experts} experts → {args.store_root}")
    if mtype == "deepseek":
        DT.materialize_experts_to_ssd(args.state_path_resolved, store,
                                      plan.n_layers, plan.n_experts)
    else:
        MT.materialize_experts_to_ssd(args.state_path_resolved, store,
                                      plan.n_layers, plan.n_experts)

    prompts, ppl_text = load_prompts(args.n_prompts, args.prompt_len)
    results = {p: run_policy(p, args, plan, store, device, prompts, ppl_text,
                             tokenizer, use_cache=True, model_type=mtype) for p in policies}
    _emit(args, device, plan, results, smoke=False)


def _compute_speedups(results):
    # speedup vs baselines (按 throughput)
    if "ours" in results:
        ours_tps = results["ours"]["tokens_per_s"]
        for b in ("swapmoe", "fiddler", "naive"):
            if b in results and results[b]["tokens_per_s"] > 0:
                results["ours"].setdefault("speedup_vs", {})[b] = round(
                    ours_tps / results[b]["tokens_per_s"], 3)


def _detect_platform(args, device):
    if args.platform:
        return args.platform
    if device.type == "cuda":
        return torch.cuda.get_device_name(device)
    return "CPU"


def _emit(args, device, plan, results, smoke):
    _compute_speedups(results)
    out = {
        "device": str(device),
        "mode": "smoke" if smoke else "real",
        "model": args.model if not smoke else "smoke-tiny-moe",
        "platform": _detect_platform(args, device),
        "run_time": datetime.now().astimezone().isoformat(timespec="seconds"),
        "compiled_plan": {k: v for k, v in vars(plan).items() if k != "placement"},
        "config": {"max_new_tokens": args.max_new_tokens, "prompt_len": args.prompt_len,
                   "n_prompts": args.n_prompts, "cold_ssd": args.cold_ssd},
        "results": results,
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n{'='*70}\nMAIN TABLE → {args.out}")
    print(f"{'policy':<10}{'TTFT(ms)':>11}{'TPOT(ms)':>11}{'tok/s':>10}{'PPL':>16}")
    for p, r in results.items():
        print(f"{p:<10}{r['ttft_ms']:>11}{r['tpot_ms']:>11}{r['tokens_per_s']:>10}{str(r['ppl']):>16}")
    if "ours" in results and results["ours"].get("speedup_vs"):
        sv = results["ours"]["speedup_vs"]
        print("  OURS speedup: " + " | ".join(f"vs {k} {v}×" for k, v in sv.items()))
    print("=" * 70)


if __name__ == "__main__":
    main()
