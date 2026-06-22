#!/usr/bin/env python3
"""
profile_real_moe.py — 真实 MoE expert 激活分布 profiling
=========================================================
在真实训练好的 MoE 模型上跑真实文本, 从 router 采集 expert 激活计数,
拟合真实 Zipf α —— 替换之前**假设**的 α=1.2。

默认模型: google/switch-base-128 (T5 MoE, 每 MoE 层 128 experts, 真实训练, ~3GB)
  Switch Transformer 每个 token 只路由到 top-1 expert。

输出: real_alpha.json (每层 α + 全局 α + top-k 覆盖率)
"""
import argparse, json, math, time
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
    counts: list[int], 每个 expert 的访问次数。
    log(freq_rank_r) ≈ log(C) - α·log(r)  → 线性回归斜率即 -α。
    """
    c = sorted([x for x in counts if x > 0], reverse=True)
    if len(c) < 3:
        return None
    ranks = np.arange(1, len(c) + 1)
    logr = np.log(ranks)
    logf = np.log(np.array(c, dtype=float))
    # 最小二乘斜率
    A = np.vstack([logr, np.ones_like(logr)]).T
    slope, _ = np.linalg.lstsq(A, logf, rcond=None)[0]
    return float(-slope)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="google/switch-base-128")
    ap.add_argument("--out", default="real_alpha.json")
    args = ap.parse_args()

    from transformers import AutoTokenizer, SwitchTransformersForConditionalGeneration

    dev, dev_type = get_device()
    print("=" * 70)
    print("REAL MoE Expert Activation Profiling")
    print("=" * 70)
    print(f"Model  : {args.model}")
    print(f"Device : {dev_type}")

    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(args.model)
    model = SwitchTransformersForConditionalGeneration.from_pretrained(
        args.model, torch_dtype=torch.float32).to(dev).eval()
    print(f"Loaded in {time.time()-t0:.1f}s")

    cfg = model.config
    n_experts = getattr(cfg, "num_experts", None)
    print(f"Num experts/layer : {n_experts}")

    # 多样化真实文本 (覆盖不同领域)
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
    n_tokens = 0

    print(f"Profiling {len(texts)} sentences...")
    # 在每个 Top1Router 上挂 forward hook 直接捕获 top-1 expert 分配,
    # 绕过 seq2seq 顶层 _unpack_router_logits 的已知 bug, 也不依赖各版本
    # 不一致的 router_probs/router_logits 输出字段。
    # router 输出为 (expert_prob, expert_onehot_mask[..., num_experts], router_logits),
    # 对 one-hot 掩码沿最后一维 argmax 即得每 token 选中的 expert id。
    def make_hook(layer_key):
        def hook(_mod, _inp, out):
            mask = out[1]  # (tokens, 1, num_experts) int64 one-hot
            eids = mask.argmax(dim=-1).reshape(-1).tolist()
            per_layer.setdefault(layer_key, Counter())
            for e in eids:
                expert_counts[e] += 1
                per_layer[layer_key][e] += 1
        return hook

    handles = []
    for name, mod in model.named_modules():
        if name.endswith("mlp.router"):
            handles.append(mod.register_forward_hook(make_hook(name)))

    with torch.no_grad():
        for txt in texts:
            enc = tok(txt, return_tensors="pt").to(dev)
            dec = tok("translate", return_tensors="pt").to(dev)
            enc_out = model.encoder(input_ids=enc.input_ids, return_dict=True)
            # decoder 需要 encoder_hidden_states 才能前向
            model.decoder(input_ids=dec.input_ids,
                          encoder_hidden_states=enc_out.last_hidden_state,
                          return_dict=True)

    for h in handles:
        h.remove()

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

    print("-" * 70)
    print(f"Total routed tokens : {total}")
    print(f"Active experts      : {n_active}/{n_experts}")
    print(f"Top-1 expert share  : {top1_cov:.1f}%")
    print(f"Top-10 coverage     : {top10_cov:.1f}%")
    print(f"Top-25% coverage    : {top25pct_cov:.1f}%")
    print(f"GLOBAL Zipf α (fit) : {global_alpha:.3f}" if global_alpha is not None
          else "GLOBAL Zipf α (fit) : N/A (insufficient data)")
    if layer_alphas:
        vals = list(layer_alphas.values())
        print(f"Per-layer α         : min={min(vals):.2f} max={max(vals):.2f} "
              f"mean={sum(vals)/len(vals):.2f}  (n={len(vals)} MoE layers)")
    print("=" * 70)
    if global_alpha is not None:
        print(f"Note: assumed α was 1.2 in original work. Measured α = {global_alpha:.2f}.")

    result = {
        "model": args.model,
        "n_experts_per_layer": n_experts,
        "n_routed_tokens": total,
        "n_active_experts": n_active,
        "top1_share_pct": round(top1_cov, 2),
        "top10_coverage_pct": round(top10_cov, 2),
        "top25pct_coverage_pct": round(top25pct_cov, 2),
        "global_zipf_alpha": round(global_alpha, 3) if global_alpha else None,
        "per_layer_alpha": layer_alphas,
        "expert_counts_sorted_desc": srt[:40],
        "note": "Switch-Transformer top-1 routing on 16 diverse English sentences. "
                "Original work ASSUMED alpha=1.2; this is a MEASURED estimate.",
    }
    json.dump(result, open(args.out, "w"), indent=2, ensure_ascii=False)
    print(f"Saved → {args.out}")


if __name__ == "__main__":
    main()
