#!/usr/bin/env python3
"""MoE-Infinity baseline benchmark — 与 MECC 同口径对比
===========================================================
用 MoE-Infinity 的 forward 逐 token 生成，测量 TTFT/TPOT/tok·s。
"""
import argparse, json, os, statistics, time
import torch

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
BUILTIN_PROMPTS = [
    "The economic policy of the central bank affects inflation rates because",
    "In quantum mechanics, entanglement is a phenomenon where",
    "The history of the Roman Empire can be summarized as",
    "The recipe for a classic French omelette requires",
    "Climate change impacts coastal cities through",
    "Machine learning models learn from data by",
    "The Renaissance period in Europe was characterized by",
    "To optimize a deep neural network, engineers typically",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="deepseek-ai/DeepSeek-V2-Lite")
    ap.add_argument("--state_path", default=None)
    ap.add_argument("--offload_dir", default="/data/mei_store")
    ap.add_argument("--ratio", type=float, default=0.2)
    ap.add_argument("--prompt_len", type=int, default=32)
    ap.add_argument("--max_new_tokens", type=int, default=16)
    ap.add_argument("--n_prompts", type=int, default=4)
    ap.add_argument("--out", default="main_table_mei.json")
    args = ap.parse_args()

    print("=" * 60)
    print(f"MoE-Infinity: {args.model}  ratio={args.ratio}")
    print("=" * 60)

    from transformers import AutoTokenizer
    from moe_infinity import MoE

    checkpoint = args.state_path or args.model
    tokenizer = AutoTokenizer.from_pretrained(checkpoint, trust_remote_code=True)
    config = {"offload_path": args.offload_dir,
              "device_memory_ratio": args.ratio}
    t0 = time.time()
    model = MoE(checkpoint, config)
    print(f"  Loaded in {time.time()-t0:.0f}s")

    prompts = BUILTIN_PROMPTS[:args.n_prompts]
    results_raw = []

    for i, p in enumerate(prompts):
        ids = tokenizer(p, return_tensors="pt").input_ids[:, :args.prompt_len].to(DEVICE)
        seq = ids.clone()

        # Prefill (TTFT): 一次性处理 prompt
        torch.cuda.synchronize()
        t0_step = time.perf_counter()
        with torch.no_grad():
            out = model(seq)
        logits = (out.logits if hasattr(out, "logits") else
                  out[0] if isinstance(out, tuple) else out)
        next_tok = logits[:, -1].argmax(-1, keepdim=True)
        torch.cuda.synchronize()
        ttft = time.perf_counter() - t0_step

        # Decode (TPOT): 每步拼接完整序列 forward
        step_times = []
        for _ in range(args.max_new_tokens - 1):
            seq = torch.cat([seq, next_tok], dim=1)
            t0_step = time.perf_counter()
            with torch.no_grad():
                out = model(seq)
            logits = (out.logits if hasattr(out, "logits") else
                      out[0] if isinstance(out, tuple) else out)
            next_tok = logits[:, -1].argmax(-1, keepdim=True)
            torch.cuda.synchronize()
            step_times.append(time.perf_counter() - t0_step)

        n_tokens = args.max_new_tokens
        total = ttft + sum(step_times)
        tpot = statistics.mean(step_times) if step_times else ttft
        tok_s = n_tokens / total if total > 0 else 0

        print(f"  [{i+1}/{len(prompts)}] TTFT={ttft*1e3:.0f}ms "
              f"TPOT={tpot*1e3:.0f}ms tok/s={tok_s:.2f}")
        results_raw.append({"ttft_ms": round(ttft * 1e3, 2),
                            "tpot_ms": round(tpot * 1e3, 2),
                            "tokens_per_s": round(tok_s, 2)})

    agg = {
        "ttft_ms": round(statistics.mean(r["ttft_ms"] for r in results_raw), 2),
        "tpot_ms": round(statistics.mean(r["tpot_ms"] for r in results_raw), 2),
        "tokens_per_s": round(statistics.mean(r["tokens_per_s"] for r in results_raw), 2),
    }
    out = {
        "baseline": "MoE-Infinity",
        "model": args.model,
        "config": {"device_memory_ratio": args.ratio,
                   "max_new_tokens": args.max_new_tokens,
                   "n_prompts": args.n_prompts},
        "results": {"moe_infinity": agg},
    }
    print(f"\nMoE-Infinity: TTFT={agg['ttft_ms']}ms TPOT={agg['tpot_ms']}ms "
          f"tok/s={agg['tokens_per_s']}")
    json.dump(out, open(args.out, "w"), indent=2, ensure_ascii=False)
    print(f"Saved → {args.out}")


if __name__ == "__main__":
    main()
