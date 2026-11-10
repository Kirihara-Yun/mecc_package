#!/usr/bin/env python3
"""
profile_mixtral.py — 针对 Mixtral 的真实逐层路由 profile
=========================================================
在真实 Mixtral-8x7B 上跑真实文本, hook 每层 MoE gate 的 router logits,
采集每 token 的 top-2 expert 激活, 产出 compile_config 需要的三种字段:

  per_layer_counts : {layer: [count_e0, ..., count_e7]}   — 逐层热度排序 (Insight I / M3)
  per_layer_trace  : {layer: [[eid, eid], ...]}           — 每 token 的 top-k expert (M3 共现)
  per_layer_alpha  : {layer: fitted_zipf_alpha}           — 逐层 Zipf α (可选)

与 profile_real_moe.py (Switch Transformer) 的区别: 本脚本直接面向 Mixtral,
gate 是 block_sparse_moe.gate (Linear, hidden→num_local_experts), top-k=2。

用法:
  python3 profile_mixtral.py --state_path <Mixtral snapshot> --out mixtral_profile.json
"""
import argparse
import json
from collections import Counter

import numpy as np
import torch


def fit_zipf_alpha_mle(counts):
    """从访问计数拟合 Zipf α (排名-频率对数线性回归斜率取负)。"""
    c = sorted([x for x in counts if x > 0], reverse=True)
    if len(c) < 3:
        return None
    ranks = np.arange(1, len(c) + 1)
    logr = np.log(ranks)
    logf = np.log(np.array(c, dtype=float))
    A = np.vstack([logr, np.ones_like(logr)]).T
    slope, _ = np.linalg.lstsq(A, logf, rcond=None)[0]
    return float(-slope)


# 多样化真实文本（覆盖 QA / 代码 / 通用领域，让路由分布更有代表性）
DEFAULT_TEXTS = [
    "The economic policy of the central bank affects inflation rates across markets.",
    "Photosynthesis converts carbon dioxide and water into glucose using sunlight.",
    "Quantum entanglement allows particles to share states across vast distances.",
    "def quicksort(arr): return arr if len(arr) <= 1 else quicksort([x for x in arr[1:] if x <= arr[0]]) + [arr[0]] + quicksort([x for x in arr[1:] if x > arr[0]])",
    "The software engineer refactored the legacy codebase to improve performance.",
    "Renaissance painters mastered perspective, light, and human anatomy.",
    "Machine learning algorithms learn patterns from large labeled datasets.",
    "import torch; x = torch.randn(3, 4); y = torch.nn.functional.relu(x)",
    "The orchestra performed a symphony in four movements at the concert hall.",
    "Genetic mutations can lead to variations in phenotype within a population.",
    "The stock market rallied after the central bank cut interest rates.",
    "SELECT user_id, COUNT(*) FROM orders WHERE status = 'paid' GROUP BY user_id;",
    "Ancient civilizations built impressive structures using simple tools.",
    "Climate models predict rising sea levels due to melting polar ice caps.",
    "The novel explores themes of memory, loss, and the passage of time.",
    "def matrix_multiply(a, b): return [[sum(x * y for x, y in zip(row, col)) for col in zip(*b)] for row in a]",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mistralai/Mixtral-8x7B-Instruct-v0.1")
    ap.add_argument("--state_path", default=None, help="本地 snapshot 目录（含 *.safetensors），空则按 model 下载")
    ap.add_argument("--out", default="mixtral_profile.json")
    ap.add_argument("--texts", default=None, help="文本文件（每行一条），缺省用内置多样样本")
    ap.add_argument("--top_k", type=int, default=2, help="每 token 路由的 top-k expert 数（Mixtral=2）")
    args = ap.parse_args()

    from transformers import AutoTokenizer, AutoModelForCausalLM

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    path = args.state_path or args.model
    print(f"Loading {path} ...")
    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(
        path, torch_dtype=torch.float16, device_map="auto", low_cpu_mem_usage=True).eval()

    n_layers = model.config.num_hidden_layers
    n_experts = model.config.num_local_experts
    print(f"layers={n_layers} experts={n_experts} top_k={args.top_k}")

    per_layer_counts = {str(L): [0] * n_experts for L in range(n_layers)}
    per_layer_trace = {str(L): [] for L in range(n_layers)}

    def make_hook(L):
        def hook(_mod, _inp, out):
            # gate 输出 router logits: [tokens, n_experts]
            logits = out[0] if isinstance(out, tuple) else out
            topk = logits.topk(args.top_k, dim=-1).indices  # [tokens, top_k]
            rows = topk.cpu().tolist()
            per_layer_trace[str(L)].extend(rows)
            for row in rows:
                for e in row:
                    per_layer_counts[str(L)][e] += 1
        return hook

    handles = []
    for L in range(n_layers):
        gate = model.model.layers[L].block_sparse_moe.gate
        handles.append(gate.register_forward_hook(make_hook(L)))

    texts = []
    if args.texts:
        with open(args.texts) as f:
            texts = [ln.strip() for ln in f if ln.strip()]
    else:
        texts = DEFAULT_TEXTS

    total_tokens = 0
    with torch.no_grad():
        for txt in texts:
            ids = tok(txt, return_tensors="pt").input_ids.to(dev)
            total_tokens += ids.shape[1]
            model(ids)
            if total_tokens >= 8192:
                break

    for h in handles:
        h.remove()

    per_layer_alpha = {}
    for L in range(n_layers):
        a = fit_zipf_alpha_mle(per_layer_counts[str(L)])
        if a is not None:
            per_layer_alpha[str(L)] = round(a, 3)

    result = {
        "model": args.model,
        "n_layers": n_layers,
        "n_experts": n_experts,
        "top_k": args.top_k,
        "n_tokens": total_tokens,
        "per_layer_counts": per_layer_counts,
        "per_layer_trace": per_layer_trace,
        "per_layer_alpha": per_layer_alpha,
    }
    json.dump(result, open(args.out, "w"), indent=2, ensure_ascii=False)
    print(f"Saved → {args.out}  (tokens={total_tokens}, layers={n_layers})")


if __name__ == "__main__":
    main()
