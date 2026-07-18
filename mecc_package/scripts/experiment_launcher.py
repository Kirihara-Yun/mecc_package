#!/usr/bin/env python3
"""Persistent launcher for MECC experiments via user systemd services."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys


UNIT_PREFIX = "mecc-exp-"
RUN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")
ROOT = Path(__file__).resolve().parents[2]
E2E = ROOT / "mecc_package" / "e2e"
CONFIG_KEYS = {"smoke", "model", "state_path", "store_root", "hbm_budget",
               "cpu_budget", "alpha", "prompt_len", "max_new_tokens",
               "n_prompts", "policies", "platform", "skip_ppl"}


def unit_name(run_id: str) -> str:
    if not RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run id must match [a-z0-9][a-z0-9_.-]{0,63}")
    return UNIT_PREFIX + run_id


def systemctl(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["systemctl", "--user", *args], check=check, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def active_units() -> list[str]:
    result = systemctl(
        "list-units", f"{UNIT_PREFIX}*", "--state=activating,running",
        "--no-legend", "--plain", check=False,
    )
    return [line.split()[0] for line in result.stdout.splitlines() if line.strip()]


def git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    return result.stdout.strip() or "unknown"


def environment_snapshot() -> dict[str, str]:
    dirty = subprocess.run(
        ["git", "status", "--short"], cwd=ROOT, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    ).stdout.strip()
    return {
        "hostname": platform.node(),
        "python": sys.version.splitlines()[0],
        "kernel": platform.platform(),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", "unset"),
        "git_dirty": "yes" if dirty else "no",
    }


def config_fingerprint(command: list[str], commit: str) -> str:
    normalized = []
    skip = False
    for token in command:
        if skip:
            skip = False
            continue
        if token in ("--out", "--status_file"):
            skip = True
            continue
        normalized.append(token)
    payload = json.dumps({"command": normalized, "git_commit": commit},
                         sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def build_command(args: argparse.Namespace, output: Path) -> list[str]:
    command = [sys.executable, "run_e2e.py"]
    if args.smoke:
        command += ["--smoke"]
    else:
        command += ["--model", args.model]
        if args.state_path:
            command += ["--state_path", str(Path(args.state_path).resolve())]
        command += [
            "--hbm_budget", str(args.hbm_budget),
            "--cpu_budget", str(args.cpu_budget),
            "--alpha", str(args.alpha),
        ]
    command += [
        "--store_root", str(Path(args.store_root).resolve()),
        "--prompt_len", str(args.prompt_len),
        "--max_new_tokens", str(args.max_new_tokens),
        "--n_prompts", str(args.n_prompts),
        "--policies", args.policies,
        "--platform", args.platform,
        "--out", str(output),
        "--status_file", str(output.parent / "status.json"),
    ]
    if args.skip_ppl:
        command.append("--skip_ppl")
    return command


def load_config(path: str) -> dict:
    value = json.loads(Path(path).read_text())
    if not isinstance(value, dict) or value.get("level") not in ("L0", "L1", "L2"):
        raise ValueError("experiment config must be an object with level L0/L1/L2")
    unknown = set(value) - CONFIG_KEYS - {"level"}
    if unknown:
        raise ValueError("unknown experiment config keys: " + ", ".join(sorted(unknown)))
    missing = {"smoke", "platform", "store_root", "prompt_len", "max_new_tokens",
               "n_prompts", "policies", "skip_ppl"} - set(value)
    if missing:
        raise ValueError("missing experiment config keys: " + ", ".join(sorted(missing)))
    if value["level"] == "L0" and not value["smoke"]:
        raise ValueError("L0 config must set smoke=true")
    if value["level"] != "L0" and value["smoke"]:
        raise ValueError("L1/L2 config must set smoke=false")
    return value


def apply_config(args: argparse.Namespace) -> argparse.Namespace:
    if not getattr(args, "config", None):
        if not args.platform:
            raise ValueError("--platform is required when --config is not used")
        return args
    value = load_config(args.config)
    for key in CONFIG_KEYS:
        if key in value:
            setattr(args, key, value[key])
    return args


def start(args: argparse.Namespace) -> int:
    unit = unit_name(args.run_id)
    conflicts = active_units()
    if conflicts and not args.allow_concurrent:
        print("refusing to start: active MECC job(s): " + ", ".join(conflicts), file=sys.stderr)
        print("use --allow-concurrent only after assigning non-conflicting GPU resources", file=sys.stderr)
        return 2

    run_dir = Path(args.runs_root).resolve() / args.run_id
    if run_dir.exists():
        print(f"refusing to overwrite existing run directory: {run_dir}", file=sys.stderr)
        return 2
    output = run_dir / "result.json"
    log = run_dir / "run.log"
    command = build_command(args, output)
    commit = git_commit()
    metadata = {
        "run_id": args.run_id,
        "unit": unit,
        "created_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_commit": commit,
        "config_fingerprint": config_fingerprint(command, commit),
        "environment": environment_snapshot(),
        "cwd": str(E2E),
        "gpu": args.gpu,
        "command": command,
        "log": str(log),
        "output": str(output),
    }
    launch = [
        "systemd-run", "--user", f"--unit={unit}", "--collect",
        f"--property=WorkingDirectory={E2E}",
        f"--property=StandardOutput=append:{log}",
        f"--property=StandardError=append:{log}",
        f"--setenv=CUDA_VISIBLE_DEVICES={args.gpu}",
        *command,
    ]
    if args.dry_run:
        print(json.dumps({"metadata": metadata, "launch": launch}, indent=2))
        return 0
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
    try:
        subprocess.run(launch, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        (run_dir / "launch_error.txt").write_text(str(exc) + "\n")
        print(f"launch failed; diagnostics retained in {run_dir}: {exc}", file=sys.stderr)
        return 1
    print(f"started {unit}\nrun: {run_dir}\nstatus: {Path(__file__).name} status {args.run_id}")
    return 0


def resume(args: argparse.Namespace) -> int:
    """Start a new run from a prior command; the validated store is reused."""
    unit = unit_name(args.run_id)
    if active_units() and not args.allow_concurrent:
        print("refusing to resume while another MECC job is active", file=sys.stderr)
        return 2
    runs_root = Path(args.runs_root).resolve()
    source = runs_root / args.from_run / "run.json"
    if not source.is_file():
        print(f"prior run metadata not found: {source}", file=sys.stderr); return 2
    prior = json.loads(source.read_text())
    run_dir = runs_root / args.run_id
    if run_dir.exists():
        print(f"refusing to overwrite existing run directory: {run_dir}", file=sys.stderr); return 2
    command = list(prior["command"])
    output = run_dir / "result.json"; log = run_dir / "run.log"
    if "--out" not in command:
        print("prior command has no --out argument", file=sys.stderr); return 2
    command[command.index("--out") + 1] = str(output)
    commit = git_commit()
    metadata = {**prior, "run_id": args.run_id, "unit": unit,
                "resumed_from": args.from_run,
                "created_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                "git_commit": commit,
                "config_fingerprint": config_fingerprint(command, commit),
                "environment": environment_snapshot(),
                "gpu": args.gpu, "command": command, "log": str(log), "output": str(output)}
    launch = ["systemd-run", "--user", f"--unit={unit}", "--collect",
              f"--property=WorkingDirectory={E2E}",
              f"--property=StandardOutput=append:{log}",
              f"--property=StandardError=append:{log}",
              f"--setenv=CUDA_VISIBLE_DEVICES={args.gpu}", *command]
    if args.dry_run:
        print(json.dumps({"metadata": metadata, "launch": launch}, indent=2)); return 0
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
    try:
        subprocess.run(launch, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        (run_dir / "launch_error.txt").write_text(str(exc) + "\n"); return 1
    print(f"started {unit} from {args.from_run}; store will be manifest-validated and reused")
    return 0


def status(run_id: str) -> int:
    unit = unit_name(run_id)
    result = systemctl(
        "show", unit, "-p", "ActiveState", "-p", "SubState", "-p", "MainPID",
        "-p", "ExecMainStatus", "-p", "Result", check=False,
    )
    sys.stdout.write(result.stdout or result.stderr)
    return 0 if result.returncode == 0 else 1


def stop(run_id: str) -> int:
    unit = unit_name(run_id)
    result = systemctl("stop", unit, check=False)
    if result.returncode:
        sys.stderr.write(result.stderr)
    else:
        print(f"stopped {unit}")
    return result.returncode


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run", help="start a persistent experiment")
    run.add_argument("run_id")
    run.add_argument("--runs-root", default=str(ROOT / "mecc_package" / "results" / "runs"))
    run.add_argument("--gpu", default="0")
    run.add_argument("--allow-concurrent", action="store_true")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--smoke", action="store_true")
    run.add_argument("--model", default="mistralai/Mixtral-8x7B-Instruct-v0.1")
    run.add_argument("--state-path")
    run.add_argument("--store-root", default="/tmp/mecc_store")
    run.add_argument("--hbm-budget", type=float, default=22.0)
    run.add_argument("--cpu-budget", type=float, default=40.0)
    run.add_argument("--alpha", type=float, default=1.0)
    run.add_argument("--prompt-len", type=int, default=64)
    run.add_argument("--max-new-tokens", type=int, default=64)
    run.add_argument("--n-prompts", type=int, default=8)
    run.add_argument("--policies", default="all")
    run.add_argument("--platform")
    run.add_argument("--config", help="explicit L0/L1/L2 JSON config")
    run.add_argument("--skip-ppl", action="store_true")
    resume_cmd = sub.add_parser("resume-from-store", help="rerun a prior command with its store")
    resume_cmd.add_argument("from_run")
    resume_cmd.add_argument("run_id")
    resume_cmd.add_argument("--runs-root", default=str(ROOT / "mecc_package" / "results" / "runs"))
    resume_cmd.add_argument("--gpu", default="0")
    resume_cmd.add_argument("--allow-concurrent", action="store_true")
    resume_cmd.add_argument("--dry-run", action="store_true")
    for action in ("status", "stop"):
        cmd = sub.add_parser(action)
        cmd.add_argument("run_id")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.action == "run":
        try:
            return start(apply_config(args))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"invalid experiment configuration: {exc}", file=sys.stderr)
            return 2
    if args.action == "status":
        return status(args.run_id)
    if args.action == "resume-from-store":
        return resume(args)
    return stop(args.run_id)


if __name__ == "__main__":
    raise SystemExit(main())
