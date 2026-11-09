"""Persistent, bounded serial queue for the frozen A100 completion matrix."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mecc_package/e2e"))
from completion_protocol import load_protocol
import experiment_launcher as launcher


def resource_summary(path):
    peaks = Counter()
    memory_max_values, swap_max_values = set(), set()
    count, invalid_rows = 0, 0
    if path.exists():
        with path.open() as stream:
            for line in stream:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    invalid_rows += 1
                    continue
                count += 1
                for name in ["VmRSS", "VmHWM", "VmLck", "VmPin"]:
                    v = row.get("process", {}).get(name)
                    if v:
                        peaks[name + "_bytes"] = max(peaks[name + "_bytes"], int(v.split()[0]) * 1024)
                cg = row.get("cgroup") or {}
                if cg.get("memory.max") is not None:
                    memory_max_values.add(cg["memory.max"])
                if cg.get("memory.swap.max") is not None:
                    swap_max_values.add(cg["memory.swap.max"])
                for name in ["memory.current", "memory.peak"]:
                    v = cg.get(name)
                    if v and v.isdigit():
                        peaks[name] = max(peaks[name], int(v))
                for line in (cg.get("memory.stat") or "").splitlines():
                    name, v = line.split()
                    if name in ["anon", "file", "shmem", "kernel", "pagetables"]:
                        peaks["cgroup_" + name + "_bytes"] = max(peaks["cgroup_" + name + "_bytes"], int(v))
    return {"samples": count, "invalid_rows": invalid_rows, "sampled_peaks": dict(peaks),
            "memory_max_values": sorted(memory_max_values), "swap_max_values": sorted(swap_max_values),
            "note": "sampled category peaks need not occur together; memory.peak is kernel high-water mark"}


def export(run_id, contract):
    run = ROOT / "mecc_package/results/runs" / run_id
    report = ROOT / "mecc_package/results/reports" / run_id
    report.mkdir(parents=True, exist_ok=True)
    for name in ["run.json", "status.json", "result.json", "partial_result.json", "requests.jsonl", "launch_error.txt"]:
        if (run / name).exists():
            shutil.copy2(run / name, report / name)
    summary = resource_summary(run / "resource_trace.jsonl")
    (report / "resource_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    shutil.copy2(contract, report / "contract.json")
    if (run / "run.log").exists():
        from collections import deque
        with (run / "run.log").open(errors="replace") as stream:
            tail = deque(stream, maxlen=250)
        (report / "run_tail.log").write_text("".join(tail), encoding="utf-8")
    journal = subprocess.run(["journalctl", "--user", "-u", launcher.unit_name(run_id),
                              "--no-pager", "-n", "100"], text=True, capture_output=True)
    (report / "unit_journal.txt").write_text(journal.stdout + journal.stderr, encoding="utf-8")
    files = {p.name: {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
             for p in report.iterdir() if p.is_file() and p.name != "report_manifest.json"}
    (report / "report_manifest.json").write_text(json.dumps({"run_id": run_id, "files": files,
        "raw_resource_trace_retained_on_gpu_host": True}, indent=2) + "\n")
    return summary


def validate_completed(run_id, job):
    path = ROOT / "mecc_package/results/runs" / run_id / "result.json"
    result = json.loads(path.read_text())
    cfg, proto = job["effective_config"], job["effective_protocol"]
    if result.get("mode") != "real" or "completion_protocol" not in result:
        raise ValueError("completed result has wrong protocol identity")
    expected = cfg["n_prompts"] * (2 if proto["sequence"] != "none" else 1)
    for row in result["results"].values():
        if len(row.get("requests", [])) != expected:
            raise ValueError("missing per-request records")
        if not cfg["skip_ppl"] and not isinstance(row.get("ppl"), (int, float)):
            raise ValueError("quality was not measured")
        for req in row["requests"]:
            if req["input_tokens"] <= 0 or req["output_tokens"] != cfg["max_new_tokens"]:
                raise ValueError("invalid token lengths")
            if job["stage"] == "length" and req["input_tokens"] != cfg["prompt_len"]:
                raise ValueError("length sweep input too short; no padding or repetition allowed")
            if {ph["phase"] for ph in req["phases"]} != {"prefill", "decode"}:
                raise ValueError("missing phase records")
        reference = ROOT / "mecc_package/results/runs/a100-c11-main-wikitext2-ours-r1/result.json"
        if not cfg["skip_ppl"] and reference.exists():
            ref_ppl = json.loads(reference.read_text())["results"]["ours"]["ppl"]
            if abs(row["ppl"] - ref_ppl) > .01:
                raise ValueError("fixed-PPL-text result diverged from the measured reference")
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--matrix", default=str(ROOT / "mecc_package/e2e/configs/completion_20261109.json"))
    ap.add_argument("--state-path", required=True)
    ap.add_argument("--gpu", default="0")
    ap.add_argument("--hours", type=float, default=24)
    ap.add_argument("--stages", default=None)
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    matrix = json.loads(Path(args.matrix).read_text())
    if args.hours <= 0:
        ap.error("hours must be positive")
    stages = args.stages.split(",") if args.stages else matrix["default_stages"]
    known = {j["stage"] for j in matrix["jobs"]}
    if set(stages) - known:
        ap.error("unknown stage")
    if args.execute and (not Path(args.state_path).is_dir() or not list(Path(args.state_path).glob("*.safetensors"))):
        ap.error("model snapshot is missing; never download model weights automatically")
    if args.execute:
        for name in ["ours", "frozen", "independent"]:
            gate_dir = ROOT / "mecc_package/results/runs" / f"a100-c11-gate-{name}-r1"
            result_path = gate_dir / "result.json"
            if not result_path.exists():
                ap.error("missing short correctness gate: " + name)
            gate = json.loads(result_path.read_text())
            if not gate.get("passed") or not gate.get("config", {}).get("completion_sequential"):
                ap.error("short correctness gate failed or used the old path: " + name)
    all_jobs = []
    for job in matrix["jobs"]:
        if job["stage"] not in stages:
            continue
        cfg = {**matrix["base"], **job["config"]}
        proto = {**matrix["protocol"], **job["protocol"]}
        if job["profile"]:
            cfg["profile"] = str(ROOT / matrix["profile_path"])
        rid = f"{matrix['run_prefix']}-{job['id']}-r1"
        all_jobs.append({**job, "run_id": rid, "effective_config": cfg, "effective_protocol": proto})
    if not args.execute:
        print(json.dumps({"dry_run": True, "jobs": all_jobs}, indent=2))
        return 0
    deadline = time.monotonic() + args.hours * 3600
    ledger = ROOT / "mecc_package/results/reports/completion_20261109"
    ledger.mkdir(parents=True, exist_ok=True)
    (ledger / "frozen_queue.json").write_text(json.dumps(all_jobs, indent=2) + "\n")
    for job in all_jobs:
        rid = job["run_id"]
        cfg, proto = job["effective_config"], job["effective_protocol"]
        contracts = ledger / "contracts"
        contracts.mkdir(exist_ok=True)
        protocol_file, config_file = contracts / f"{rid}.json", contracts / f"{rid}.config.json"
        cfg = {**cfg, "completion_protocol": str(protocol_file), "state_path": args.state_path}
        for path, data in [(protocol_file, proto), (config_file, cfg)]:
            value = json.dumps(data, indent=2) + "\n"
            if path.exists() and path.read_text() != value:
                raise ValueError("refusing to change a frozen contract")
            path.write_text(value)
        load_protocol(protocol_file)
        run_dir = ROOT / "mecc_package/results/runs" / rid
        if run_dir.exists():
            status = json.loads((run_dir / "status.json").read_text()) if (run_dir / "status.json").exists() else {}
            if status.get("phase") == "complete":
                validate_completed(rid, job)
                print("SKIP_COMPLETE", rid, flush=True)
                continue
            raise ValueError(f"existing incomplete run {rid}: inspect and use a new documented run ID")
        if time.monotonic() >= deadline:
            print("TIME_BUDGET_REACHED before", rid, flush=True)
            break
        gpu_check = subprocess.run(["nvidia-smi", "--id=" + args.gpu,
                                    "--query-compute-apps=pid", "--format=csv,noheader"],
                                   text=True, capture_output=True)
        if gpu_check.returncode or gpu_check.stdout.strip():
            print("STOP_GPU_NOT_IDLE; do not touch other jobs", flush=True)
            return 2
        print("START", rid, flush=True)
        run_args = launcher.parser().parse_args(["run", rid, "--config", str(config_file), "--gpu", args.gpu])
        code = launcher.start(launcher.apply_config(run_args))
        if code:
            export(rid, protocol_file)
            return code
        started = time.monotonic()
        while True:
            status = json.loads((run_dir / "status.json").read_text()) if (run_dir / "status.json").exists() else {}
            phase = status.get("phase")
            if phase == "complete":
                summary = export(rid, protocol_file)
                validate_completed(rid, job)
                if summary["samples"] == 0 or summary["invalid_rows"]:
                    raise ValueError("missing physical memory trace; stop fairness queue")
                if summary["memory_max_values"] != [str(int(cfg["host_memory_max_gib"] * 1024**3))] or summary["swap_max_values"] != ["0"]:
                    raise ValueError("physical memory cap was not enforced")
                print("COMPLETE", rid, "seconds", round(time.monotonic()-started), flush=True)
                break
            active = launcher.systemctl("is-active", launcher.unit_name(rid), check=False).stdout.strip()
            if phase == "failed" or active not in ("active", "activating"):
                export(rid, protocol_file)
                print("STOP_FAILED_OR_DEAD_UNIT", rid, flush=True)
                return 1
            if time.monotonic() >= deadline or time.monotonic()-started > matrix["policy"]["max_run_seconds"]:
                launcher.stop(rid)
                export(rid, protocol_file)
                print("STOP_TIME_LIMIT", rid, flush=True)
                return 2
            time.sleep(15)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
