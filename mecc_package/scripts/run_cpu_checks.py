#!/usr/bin/env python3
"""Single CPU-CI entry for MECC tests, protected imports, claims, and L0."""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "mecc_package"
E2E = PKG / "e2e"

def run(command, cwd=REPO):
    print("+", " ".join(map(str, command)), f"(cwd={cwd})")
    subprocess.run(list(map(str, command)), cwd=cwd, check=True)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-l0", action="store_true")
    args = ap.parse_args()
    run([sys.executable, "-m", "unittest",
         "mecc_package/test_experiment_launcher.py",
         "mecc_package/test_theory_counterexamples.py"])
    run([sys.executable, "-m", "unittest",
         "test_async_ssd_read.py", "test_cache_consistency.py",
         "test_result_schema.py", "test_store_manifest.py",
         "test_run_e2e_metrics.py"], E2E)
    run([sys.executable, "-c", "import compile_config"], E2E)
    run([sys.executable, "-c", "import runtime_spec"], PKG)
    run([sys.executable, "-c", "import concurrent_tiered_cache"], PKG / "scripts")
    run([sys.executable, PKG / "scripts" / "generate_paper_tables.py", "--check"])
    run([sys.executable, PKG / "scripts" / "verify_claims.py"])
    if not args.skip_l0:
        with tempfile.TemporaryDirectory(prefix="mecc_cpu_ci_") as tmp:
            run([sys.executable, "run_e2e.py", "--smoke", "--n_prompts", "1",
                 "--max_new_tokens", "2", "--store_root", str(Path(tmp) / "store"),
                 "--out", str(Path(tmp) / "result.json"),
                 "--status_file", str(Path(tmp) / "status.json")], E2E)
    print("CPU checks PASS")

if __name__ == "__main__": main()
