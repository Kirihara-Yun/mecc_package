"""Validation and atomic publication for Schema-A e2e result JSON."""
from __future__ import annotations
from datetime import datetime
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable

REQUIRED_METRICS = ("ttft_ms", "tpot_ms", "tokens_per_s", "ppl", "hit_pct")
HIT_KEYS = ("hbm", "cpu", "ssd", "cpu_compute")

class ResultSchemaError(ValueError):
    pass

def _number(value: Any, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ResultSchemaError(f"{label} must be a finite number")
    if value < 0 or (positive and value == 0):
        raise ResultSchemaError(f"{label} must be {'positive' if positive else 'non-negative'}")
    return float(value)

def validate_e2e_result(out: dict[str, Any], expected_policies: Iterable[str]) -> None:
    required = ("device", "mode", "model", "platform", "run_time",
                "compiled_plan", "config", "results")
    missing = [key for key in required if key not in out]
    if missing:
        raise ResultSchemaError("missing top-level fields: " + ", ".join(missing))
    if out["mode"] not in ("real", "smoke"):
        raise ResultSchemaError("mode must be 'real' or 'smoke'")
    for key in ("device", "model", "platform"):
        if not isinstance(out[key], str) or not out[key].strip():
            raise ResultSchemaError(f"{key} must be a non-empty string")
    try:
        timestamp = datetime.fromisoformat(out["run_time"])
    except (TypeError, ValueError) as exc:
        raise ResultSchemaError("run_time must be ISO 8601") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ResultSchemaError("run_time must include a timezone")
    if not isinstance(out["compiled_plan"], dict) or not isinstance(out["config"], dict):
        raise ResultSchemaError("compiled_plan and config must be objects")
    plan_fields = ("n_layers", "n_experts", "k_h", "k_c")
    if any(key not in out["compiled_plan"] for key in plan_fields):
        raise ResultSchemaError("compiled_plan lacks required placement fields")
    config_fields = ("max_new_tokens", "prompt_len", "n_prompts", "cold_ssd")
    if any(key not in out["config"] for key in config_fields):
        raise ResultSchemaError("config lacks required run fields")
    results = out["results"]
    expected = list(expected_policies)
    if not isinstance(results, dict) or set(results) != set(expected):
        raise ResultSchemaError(f"results policies {sorted(results) if isinstance(results, dict) else results} "
                                f"do not match requested policies {sorted(expected)}")
    for policy, row in results.items():
        if not isinstance(row, dict):
            raise ResultSchemaError(f"results.{policy} must be an object")
        absent = [key for key in REQUIRED_METRICS if key not in row]
        if absent:
            raise ResultSchemaError(f"results.{policy} missing: {', '.join(absent)}")
        _number(row["ttft_ms"], f"results.{policy}.ttft_ms")
        _number(row["tpot_ms"], f"results.{policy}.tpot_ms")
        _number(row["tokens_per_s"], f"results.{policy}.tokens_per_s", positive=True)
        ppl = row["ppl"]
        if not (ppl == "exact(lossless)" or
                (isinstance(ppl, (int, float)) and not isinstance(ppl, bool)
                 and math.isfinite(ppl) and ppl >= 0)):
            raise ResultSchemaError(f"results.{policy}.ppl has invalid semantics")
        hits = row["hit_pct"]
        if not isinstance(hits, dict) or any(key not in hits for key in HIT_KEYS):
            raise ResultSchemaError(f"results.{policy}.hit_pct must contain {HIT_KEYS}")
        total = sum(_number(hits[key], f"results.{policy}.hit_pct.{key}") for key in HIT_KEYS)
        if abs(total - 100.0) > 0.25:
            raise ResultSchemaError(f"results.{policy}.hit_pct sums to {total:.3f}, not 100")
    speedups = results.get("ours", {}).get("speedup_vs", {})
    for baseline, value in speedups.items():
        if baseline not in results or baseline == "ours":
            raise ResultSchemaError(f"speedup_vs references unknown baseline: {baseline}")
        actual = _number(value, f"results.ours.speedup_vs.{baseline}", positive=True)
        expected_value = results["ours"]["tokens_per_s"] / results[baseline]["tokens_per_s"]
        if abs(actual - expected_value) > 0.0015:
            raise ResultSchemaError(f"speedup_vs.{baseline} is inconsistent with throughput")

def atomic_write_result(path: str, out: dict[str, Any], expected_policies: Iterable[str]) -> None:
    validate_e2e_result(out, expected_policies)
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(out, handle, indent=2, ensure_ascii=False)
            handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
