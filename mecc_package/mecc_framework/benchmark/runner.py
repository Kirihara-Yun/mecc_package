#!/usr/bin/env python3
"""
mecc_framework.benchmark.runner — 端到端 Benchmark 入口
=========================================================
统一入口: 加载模型 → 编译缓存 → 测量 TTFT/TPOT/tokens/s + PPL。
支持 --policy 多策略对比, 输出主表 JSON。
"""
from __future__ import annotations
import argparse, json, os, statistics, time
from typing import List, Optional

import torch
import torch.nn.functional as F

from ..base.config import OffloadConfig, CacheBudget, CachePolicy
from ..base.store import ExpertSSDStore
from ..models import get_adapter


POLICIES = [CachePolicy.OURS, CachePolicy.SWAPMOE,
            CachePolicy.FIDDLER, CachePolicy.NAIVE]


def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda"), "cuda"
    if torch.backends.mps.is_available():
        return torch.device("mps"), "mps"
    return torch.device("cpu"), "cpu"


def sync(device):
    if device.type == "cuda":
        torch.cuda.synchronize()
    elif device.type == "mps":
        torch.mps.synchronize()


@torch.no_grad()
def measure_latency(model, input_ids, max_new_tokens, device):
    """测量 TTFT + TPOT。"""
    sync(device)
    t0 = time.perf_counter()
    out = model(input_ids, use_cache=True)
    logits = out.logits if hasattr(out, "logits") else out
    next_tok = logits[:, -1].argmax(-1, keepdim=True)
    past = out.past_key_values if hasattr(out, "past_key_values") else None
    sync(device)
    ttft = time.perf_counter() - t0

    step_times = []
    for _ in range(max_new_tokens - 1):
        t0 = time.perf_counter()
        out = model(next_tok, past_key_values=past, use_cache=True)
        logits = out.logits if hasattr(out, "logits") else out
        next_tok = logits[:, -1].argmax(-1, keepdim=True)
        past = out.past_key_values if hasattr(out, "past_key_values") else None
        sync(device)
        step_times.append(time.perf_counter() - t0)

    tpot = statistics.mean(step_times) if step_times else ttft
    total = ttft + sum(step_times)
    return {
        "ttft_ms": ttft * 1e3,
        "tpot_ms": tpot * 1e3,
        "total_s": total,
        "tokens_per_s": max_new_tokens / total if total > 0 else 0,
    }


# 内置 prompts
PROMPTS = [
    "The economic policy of the central bank affects inflation rates because",
    "In quantum mechanics, entanglement is a phenomenon where",
    "The history of the Roman Empire can be summarized as",
    "To optimize a deep neural network, engineers typically",
    "Climate change impacts coastal cities through",
]


def main():
    ap = argparse.ArgumentParser(description="MECC Universal MoE Inference Benchmark")
    ap.add_argument("--model", default="mixtral",
                    help="模型 ID 或架构类型 (mixtral / deepseek)")
    ap.add_argument("--state_path", default=None,
                    help="模型 safetensors 目录")
    ap.add_argument("--store_root", default="/tmp/mecc_store",
                    help="SSD expert 冷存目录")
    ap.add_argument("--k_hbm", type=int, default=4,
                    help="每层 HBM 槽数")
    ap.add_argument("--k_cpu", type=int, default=4,
                    help="每层 CPU 槽数")
    ap.add_argument("--policy", default="ours",
                    choices=["ours", "swapmoe", "fiddler", "naive", "all"])
    ap.add_argument("--max_new_tokens", type=int, default=32)
    ap.add_argument("--prompt_len", type=int, default=64)
    ap.add_argument("--out", default="benchmark_results.json")
    args = ap.parse_args()

    device, dev_type = get_device()
    print(f"Mecc Framework Benchmark | Device: {device}")

    # 获取 adapter
    adapter = get_adapter(args.model)
    spec = adapter.model_spec
    print(f"Model: {spec.name}")
    print(f"  {spec.n_layers} layers × {spec.n_experts} experts, "
          f"top-{spec.top_k}, expert size: {spec.expert_spec.size_gb:.3f} GB")

    # 创建 store
    store = ExpertSSDStore(args.store_root, spec.expert_spec.hidden_dim,
                           spec.expert_spec.ffn_dim, model_type=args.model)

    # 确定 state_path
    if args.state_path is None:
        from huggingface_hub import snapshot_download
        args.state_path = snapshot_download(
            args.model,
            allow_patterns=["*.safetensors", "*.json", "tokenizer*"])
        print(f"  Downloaded to {args.state_path}")

    # 物化 expert 到 SSD
    print(f"\n[materialize] streaming experts → {args.store_root}")
    adapter.materialize_experts(args.state_path, store)

    # 编译配置
    budget = CacheBudget(k_hbm=args.k_hbm, k_cpu=args.k_cpu)

    policies_to_run = POLICIES if args.policy == "all" else [
        CachePolicy(args.policy)]

    all_results = {}
    for policy in policies_to_run:
        print(f"\n{'='*60}\n[POLICY = {policy.value}]\n{'='*60}")
        config = OffloadConfig(
            model_spec=spec, budget=budget, policy=policy, cold_ssd=True)

        # 构建模型
        model, caches = adapter.build_tiered_model(
            args.state_path, store, device, config)

        # 测量
        lat = []
        for p in PROMPTS[:3]:
            from transformers import AutoTokenizer
            tok = AutoTokenizer.from_pretrained(
                args.state_path, trust_remote_code=True)
            ids = tok(p, return_tensors="pt").input_ids[:, :args.prompt_len].to(device)
            # warmup
            _ = measure_latency(model, ids, min(4, args.max_new_tokens), device)
            lat.append(measure_latency(model, ids, args.max_new_tokens, device))

        agg = {
            "ttft_ms": round(statistics.mean(l["ttft_ms"] for l in lat), 2),
            "tpot_ms": round(statistics.mean(l["tpot_ms"] for l in lat), 2),
            "tokens_per_s": round(statistics.mean(l["tokens_per_s"] for l in lat), 2),
        }

        # 命中率统计
        tot_hits = [0, 0, 0, 0]
        for c in caches:
            if c is None:
                continue
            for i in range(4):
                tot_hits[i] += c.hits[i]
        s = sum(tot_hits) or 1
        agg["hit_pct"] = {
            "hbm": round(tot_hits[0] / s * 100, 1),
            "cpu": round(tot_hits[1] / s * 100, 1),
            "ssd": round(tot_hits[2] / s * 100, 1),
            "cpu_compute": round(tot_hits[3] / s * 100, 1),
        }

        all_results[policy.value] = agg
        print(f"  TTFT={agg['ttft_ms']}ms  TPOT={agg['tpot_ms']}ms  "
              f"throughput={agg['tokens_per_s']} tok/s")
        print(f"  HBM hit={agg['hit_pct']['hbm']}% CPU={agg['hit_pct']['cpu']}% "
              f"SSD={agg['hit_pct']['ssd']}%")

        del model, caches
        if device.type == "cuda":
            torch.cuda.empty_cache()

    # 输出结果
    out = {
        "model": spec.name,
        "device": str(device),
        "config": {"k_hbm": budget.k_hbm, "k_cpu": budget.k_cpu},
        "results": all_results,
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {args.out}")


if __name__ == "__main__":
    main()
