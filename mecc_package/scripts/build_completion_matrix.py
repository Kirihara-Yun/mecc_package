"""Freeze the next measured A100 queue; no GPU or model import."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "mecc_package/e2e/configs/completion_20261109.json"
PROFILE = "mecc_package/results/raw/mixtral_profile_20261105.json"
BUNDLE = "mecc_package/e2e/data/completion_tasks_20261109.json"


def matrix():
    protocol = {"version": 1, "task": "wikitext2", "sequence": "none",
                "warmup": "none", "allocation": "uniform", "disable_m3": True,
                "prefill_overlap": True, "equal_uniform_slots": True,
                "bundle": "data/completion_tasks_20261109.json",
                "bundle_sha256": hashlib.sha256((ROOT / BUNDLE).read_bytes()).hexdigest(),
                "profile_sha256": hashlib.sha256((ROOT / PROFILE).read_bytes()).hexdigest()}
    base = {"level": "L2", "smoke": False,
            "model": "mistralai/Mixtral-8x7B-Instruct-v0.1", "platform": "a100-80g",
            "store_root": "/data/mecc_store_mixtral", "hbm_budget": 50.0,
            "cpu_budget": 16.0, "alpha": 1.0, "prompt_len": 64,
            "max_new_tokens": 16, "n_prompts": 4, "ppl_tokens": 1024,
            "policies": "ours", "skip_ppl": False, "uniform": True,
            "init_plan": "avg", "host_memory_max_gib": 80.0}
    jobs = []
    def add(id, stage, config=None, proto=None, profile=False):
        jobs.append({"id": id, "stage": stage, "config": config or {},
                     "protocol": proto or {}, "profile": profile})
    add("pilot", "pilot", {"n_prompts": 1, "max_new_tokens": 2, "skip_ppl": True})
    for task in ["wikitext2", "gsm8k", "humaneval"]:
        for policy in ["ours", "naive"]:
            add(f"main-{task}-{policy}", "main", {"policies": policy}, {"task": task})
    for policy in ["swapmoe", "flashmoe_rf_adaptation", "independent_inclusive"]:
        add(f"main-wikitext2-{policy}", "main", {"policies": policy})
    # A natural-order/uniform control already exists in the main GSM8K arm.
    add("place-uniform-profile", "placement", {"init_plan": "per_layer"}, {"task": "gsm8k"}, True)
    add("place-adaptive-profile", "placement", {"init_plan": "per_layer"},
        {"task": "gsm8k", "allocation": "profile"}, True)
    for sequence in ["a_b", "b_a", "a_a"]:
        for policy in ["ours", "frozen_placement"]:
            add(f"shift-{sequence}-{policy}", "shift", {"policies": policy}, {"sequence": sequence})
    for budget in [8, 24]:
        for policy in ["ours", "naive"]:
            add(f"cpu{budget}-{policy}", "capacity", {"cpu_budget": budget, "policies": policy})
    add("overlap-off", "overlap", {}, {"prefill_overlap": False})
    for length in [32, 128, 512]:
        for policy in ["ours", "naive"]:
            add(f"input{length}-{policy}", "length", {"prompt_len": length, "n_prompts": 2, "max_new_tokens": 8})
    return {"version": 1, "base_commit": "56da814", "run_prefix": "a100-c11",
            "profile_path": PROFILE, "profile_tokens": 346,
            "base": base, "protocol": protocol, "jobs": jobs,
            "default_stages": ["pilot", "main", "placement", "shift", "capacity", "overlap"],
            "policy": {"independent_repeats": 1, "error_bars": False,
                       "max_run_seconds": 28800,
                       "model_revision": "eba92302a2861cdc0098cc54bc9f17cb2c47eb61"}}


if __name__ == "__main__":
    m = matrix()
    OUT.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(OUT, "jobs:", len(m["jobs"]))
