#!/usr/bin/env python3
"""
profile_deepseek.py — DeepSeek-V2-Lite MoE expert 激活分布 profiling
===================================================================
适配 decoder-only DeepSeekMoE 架构（top-k routing + shared experts）。

默认模型: deepseek-ai/DeepSeek-V2-Lite  
  - 27 层, 全部 MoE 层
  - 每层 64 routed experts + 2 shared experts
  - top-6 routing (每个 token 选 6 个 expert)

输出: real_alpha_deepseek.json (每层 α + 全局 α + top-k 覆盖率)
"""
import argparse, json, math, time, os
from collections import Counter
import numpy as np
import torch


def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda"), "cuda"
    elif torch.backends.mps.is_available():
        return torch.device("mps"), "mps"
    return torch.device("cpu"), "cpu"


def fit_zipf_alpha_mle(counts):
    """从访问计数拟合 Zipf α (基于排名-频率的对数线性回归)。
    log(freq_rank_r) ≈ log(C) - α·log(r) → 线性回归斜率即 -α。
    """
    c = sorted([x for x in counts if x > 0], reverse=True)
    if len(c) < 3:
        return None
    ranks = np.arange(1, len(c) + 1)
    logr = np.log(ranks)
    logf = np.log(np.array(c, dtype=float))
    A = np.vstack([logr, np.ones_like(logr)]).T
    slope, _ = np.linalg.lstsq(A, logf, rcond=None)[0]
    return float(-slope)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="deepseek-ai/DeepSeek-V2-Lite")
    ap.add_argument(
        "--model_path",
        default="/data/qinzy/models/deepseek-ai/DeepSeek-V2-Lite",
        help="本地模型路径（若已下载）",
    )
    ap.add_argument("--out", default="real_alpha_deepseek.json")
    ap.add_argument("--max_length", type=int, default=128,
                    help="单次前向最大 token 数")
    args = ap.parse_args()

    # 兼容性 monkey-patch: transformers 5.x API 变更
    from transformers.cache_utils import DynamicCache
    if not hasattr(DynamicCache, 'from_legacy_cache'):
        @classmethod
        def _from_legacy_cache(cls, past_key_values):
            return cls() if past_key_values is None else past_key_values
        DynamicCache.from_legacy_cache = _from_legacy_cache
    if not hasattr(DynamicCache, 'get_usable_length'):
        def _get_usable_length(self, seq_length=None, layer_idx=None):
            return self.get_seq_length()
        DynamicCache.get_usable_length = _get_usable_length

    from transformers import AutoModelForCausalLM, AutoTokenizer

    dev, dev_type = get_device()
    print("=" * 70)
    print("DeepSeek MoE Expert Activation Profiling")
    print("=" * 70)
    print(f"Model  : {args.model}")
    print(f"Device : {dev_type}")

    # 优先本地路径
    model_path = args.model_path if os.path.isdir(args.model_path) else args.model
    print(f"Path   : {model_path}")

    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        trust_remote_code=True,
        torch_dtype=torch.float16,
        attn_implementation="eager",
        device_map="auto",
    ).eval()
    print(f"Loaded in {time.time() - t0:.1f}s")

    cfg = model.config
    n_experts = getattr(cfg, "n_routed_experts", None)
    n_shared = getattr(cfg, "n_shared_experts", 0)
    top_k = getattr(cfg, "num_experts_per_tok", 1)
    print(f"Routed experts/layer : {n_experts}")
    print(f"Shared experts/layer : {n_shared}")
    print(f"Top-k routing        : {top_k}")

    # 多样化真实文本（覆盖不同领域）
    texts = [
        "The economic policy of the central bank affects inflation rates across markets.",
        "Photosynthesis converts carbon dioxide and water into glucose using sunlight.",
        "The quarterback threw a touchdown pass in the final seconds of the game.",
        "Quantum entanglement allows particles to share states across vast distances.",
        "The recipe calls for two cups of flour, a teaspoon of salt, and fresh basil.",
        "Supreme Court justices deliberated on the constitutional implications of the case.",
        "The novel explores themes of memory, loss, and the passage of time.",
        "Climate models predict rising sea levels due to melting polar ice caps.",
        "The software engineer refactored the legacy codebase to improve performance.",
        "Renaissance painters mastered perspective, light, and human anatomy.",
        "The orchestra performed a symphony in four movements at the concert hall.",
        "Genetic mutations can lead to variations in phenotype within a population.",
        "The stock market rallied after the central bank cut interest rates.",
        "Ancient civilizations built impressive structures using simple tools.",
        "Machine learning algorithms learn patterns from large labeled datasets.",
        "The chef seared the salmon and served it with a lemon butter sauce.",
    ]

    expert_counts = Counter()
    per_layer = {}  # layer_key -> Counter
    per_layer_trace = {}  # layer_key -> [ [expert_ids per token], ... ]  (M3 用)
    n_tokens = 0  # 被路由的 token 总数

    print(f"Profiling {len(texts)} sentences (max_length={args.max_length})...")

    # ── Hook 机制 ──
    # DeepSeek-V2 的 MoE 结构: DecoderLayer.mlp (DeepseekV2MoE)
    # 其中 mlp.gate (MoEGate) 的 forward 返回 (topk_idx, topk_weight, aux_loss)
    # topk_idx shape: (batch*seq_len, num_experts_per_tok)
    #
    # 我们 hook MoEGate.forward，从输出中抓 topk_idx。

    def make_gate_hook(layer_key):
        def hook(_mod, _inp, out):
            topk_idx = out[0]  # (tokens, top_k)
            # 逐 token 记录选中的 expert id 列表 (M3 共现统计需要)
            token_experts = topk_idx.tolist()  # list of [e1, e2, ...] per token
            per_layer_trace.setdefault(layer_key, [])
            per_layer_trace[layer_key].extend(token_experts)
            # 展平所有被选中的 expert id 用于计数
            eids = topk_idx.reshape(-1).tolist()
            per_layer.setdefault(layer_key, Counter())
            for e in eids:
                # 只统计 routed experts（0..n_experts-1），shared experts 不参与路由计数
                expert_counts[e] += 1
                per_layer[layer_key][e] += 1
        return hook

    handles = []
    for name, mod in model.named_modules():
        # Hook MoEGate 模块（其在 DeepseekV2MoE 内为 .gate）
        if type(mod).__name__ == "MoEGate":
            # 提取层名（例如 "model.layers.0.mlp.gate" → "model.layers.0"）
            layer_key = name.rsplit(".mlp.gate", 1)[0] if ".mlp.gate" in name else name
            handles.append(mod.register_forward_hook(make_gate_hook(layer_key)))

    print(f"Registered {len(handles)} MoE gate hooks")

    # ── 前向推理 ──
    with torch.no_grad():
        for i, txt in enumerate(texts):
            enc = tok(txt, return_tensors="pt", truncation=True,
                       max_length=args.max_length).to(dev)
            # decoder-only causal LM forward
            _ = model(**enc)

            # 统计该句被路由的 token 数
            seq_len = enc.input_ids.shape[1]
            n_tokens += seq_len

            if (i + 1) % 4 == 0:
                print(f"  [{i+1}/{len(texts)}] sentences done, "
                      f"{n_tokens} tokens so far...")

    for h in handles:
        h.remove()

    # ── 统计 ──
    counts = [expert_counts.get(i, 0) for i in range(n_experts)]
    n_active = sum(1 for c in counts if c > 0)
    total = sum(counts)
    srt = sorted(counts, reverse=True)
    top1_cov = srt[0] / total * 100 if total else 0
    top10_cov = sum(srt[:10]) / total * 100 if total else 0
    top25pct_cov = sum(srt[:max(1, n_experts // 4)]) / total * 100 if total else 0
    global_alpha = fit_zipf_alpha_mle(counts)

    layer_alphas = {}
    for k, ctr in per_layer.items():
        cc = [ctr.get(i, 0) for i in range(n_experts)]
        a = fit_zipf_alpha_mle(cc)
        if a is not None:
            layer_alphas[k] = round(a, 3)

    # ── 打印结果 ──
    print("-" * 70)
    print(f"Total tokens processed : {n_tokens}")
    print(f"Total expert selections: {total} ({total/n_tokens:.1f} sel/token)")
    print(f"Active experts         : {n_active}/{n_experts}")
    print(f"Top-1 expert share     : {top1_cov:.1f}%")
    print(f"Top-10 coverage        : {top10_cov:.1f}%")
    print(f"Top-25% coverage       : {top25pct_cov:.1f}%")
    print(f"Top-5 expert counts    : {dict(sorted(enumerate(counts), key=lambda x: -x[1])[:5])}")
    if global_alpha is not None:
        print(f"GLOBAL Zipf α (fit)    : {global_alpha:.3f}")
    else:
        print("GLOBAL Zipf α (fit)    : N/A (insufficient data)")

    if layer_alphas:
        vals = list(layer_alphas.values())
        print(f"Per-layer α            : min={min(vals):.2f} max={max(vals):.2f} "
              f"mean={sum(vals)/len(vals):.2f}  (n={len(vals)} MoE layers)")
    print("=" * 70)

    # ── 准备 per_layer_counts (compile_config 期望格式) ──
    per_layer_counts = {}
    # 为每层生成完整长度的计数列表
    for k, ctr in per_layer.items():
        per_layer_counts[k] = [ctr.get(i, 0) for i in range(n_experts)]

    result = {
        "model": args.model,
        "n_layers": len(handles),
        "n_routed_experts_per_layer": n_experts,
        "n_shared_experts": n_shared,
        "top_k_routing": top_k,
        "n_tokens_processed": n_tokens,
        "n_expert_selections_total": total,
        "n_active_experts": n_active,
        "top1_share_pct": round(top1_cov, 2),
        "top10_coverage_pct": round(top10_cov, 2),
        "top25pct_coverage_pct": round(top25pct_cov, 2),
        "global_zipf_alpha": round(global_alpha, 3) if global_alpha else None,
        "per_layer_alpha": layer_alphas,
        "per_layer_counts": per_layer_counts,
        "per_layer_trace": {k: v for k, v in per_layer_trace.items()},
        "expert_counts_sorted_desc": srt[:40],
        "note": "DeepSeek-V2-Lite decoder-only MoE (top-6 routing, 64 routed + 2 shared experts). "
                "Hooked MoEGate.forward output topk_idx. "
                "Each token selects top_k experts; all selections counted equally. "
                "per_layer_trace added for M3 routing-aware joint placement.",
    }
    json.dump(result, open(args.out, "w"), indent=2, ensure_ascii=False)
    print(f"Saved → {args.out}")


if __name__ == "__main__":
    main()
