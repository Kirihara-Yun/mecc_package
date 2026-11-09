"""Recompute the handoff audit from immutable prior runs; collect no new GPU data."""
from pathlib import Path
from contextlib import redirect_stdout
import hashlib
import io
import json
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mecc_package/e2e"))
from compile_config import compile_plan


def main():
    names = ["a100-e05-avg-20261105", "a100-e05-global-20261105",
             "a100-e05-per_layer-20261105-retry1", "a100-e07-a_b-20261105",
             "a100-e08-b_a-20261105", "a100-e08-a_a-20261105"]
    rows = []
    for name in names:
        directory = ROOT / "mecc_package/results/runs" / name
        relative = (directory / "result.json").relative_to(ROOT).as_posix()
        raw = subprocess.check_output(["git", "show", "56da814:" + relative], cwd=ROOT)
        result = json.loads(raw)
        run = json.loads((directory / "run.json").read_text())
        row = {"run_id": name, "result_sha256": hashlib.sha256(raw).hexdigest(),
               "run_commit": run["git_commit"],
               "recorded_placement_available": "placement" in result["compiled_plan"],
               "request_records_available": any("requests" in r for r in result["results"].values()),
               "window_counts": [len(r.get("window_hits", [])) for r in result["results"].values()],
               "phase_hits_sha256": hashlib.sha256(json.dumps(
                   [r.get("phase_hits") for r in result["results"].values()], sort_keys=True).encode()).hexdigest()}
        if "e05" in name:
            command = run["command"]
            mode = command[command.index("--init-plan") + 1]
            with redirect_stdout(io.StringIO()):
                plan = compile_plan(result["model"], 50, 40, alpha=1,
                    profile_path=str(ROOT / "mecc_package/results/raw/mixtral_profile_20261105.json"),
                    init_plan=mode, enable_m3=True)
            row["reconstructed_placement_sha256"] = hashlib.sha256(json.dumps(plan.placement, sort_keys=True).encode()).hexdigest()
        rows.append(row)
    audit = {"audited_remote_commit": "56da814", "existing_runs": rows,
        "e05_reconstructed_plans_identical": len({r["reconstructed_placement_sha256"] for r in rows[:3]}) == 1,
        "e05_observed_phase_histograms_identical": len({r["phase_hits_sha256"] for r in rows[:3]}) == 1,
        "note": "Prior result files omit placement IDs. Reconstruction follows their uniform budgets, init flags, unchanged compile_plan and committed profile; it is not a saved runtime placement trace.",
        "new_gpu_data_collected": False,
        "local_validation": {"protocol_tests": 8, "verify_claims_ok": 121,
                              "verify_claims_warn": 11, "verify_claims_fail": 0,
                              "torch_available": False, "gpu_gate": "pending_remote"},
        "hash_portability": "Git blobs use LF; .gitattributes prevents CRLF changing frozen input/evidence hashes; historical result values unchanged"}
    path = ROOT / "docs/a100_completion_20261109/AUDIT.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(audit, indent=2) + "\n")
    print(path)


if __name__ == "__main__":
    main()
