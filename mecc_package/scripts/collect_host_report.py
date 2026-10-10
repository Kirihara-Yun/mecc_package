#!/usr/bin/env python3
"""Collect a Git-friendly, read-only report for an MECC GPU experiment host."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys


REPO = Path(__file__).resolve().parents[2]


def run(command: list[str]) -> dict:
    try:
        result = subprocess.run(
            command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=30, check=False,
        )
        return {
            "command": command,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"command": command, "error": f"{type(exc).__name__}: {exc}"}


def git_snapshot() -> dict:
    head = run(["git", "rev-parse", "HEAD"])
    dirty = run(["git", "status", "--short"])
    return {
        "commit": head.get("stdout") or "unknown",
        "dirty": bool(dirty.get("stdout")),
        "status": dirty.get("stdout", ""),
    }


def package_versions() -> dict[str, str]:
    versions = {}
    for name in ("torch", "transformers", "safetensors", "numpy"):
        try:
            module = importlib.import_module(name)
            versions[name] = str(getattr(module, "__version__", "unknown"))
        except Exception as exc:  # Import failures are evidence, not fatal here.
            versions[name] = f"unavailable: {type(exc).__name__}: {exc}"
    return versions


def torch_snapshot() -> dict:
    try:
        import torch
        cuda = bool(torch.cuda.is_available())
        value = {
            "version": str(torch.__version__),
            "cuda_available": cuda,
            "torch_cuda": str(torch.version.cuda),
            "cudnn": torch.backends.cudnn.version(),
            "device_count": torch.cuda.device_count() if cuda else 0,
        }
        if cuda:
            value["devices"] = [
                {
                    "index": index,
                    "name": torch.cuda.get_device_name(index),
                    "total_memory_bytes": torch.cuda.get_device_properties(index).total_memory,
                    "capability": list(torch.cuda.get_device_capability(index)),
                }
                for index in range(torch.cuda.device_count())
            ]
        return value
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def nearest_existing(path: Path) -> Path:
    candidate = path.expanduser().resolve(strict=False)
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def path_snapshot(raw_path: str | None) -> dict | None:
    if not raw_path:
        return None
    requested = Path(raw_path).expanduser().resolve(strict=False)
    probe = nearest_existing(requested)
    usage = shutil.disk_usage(probe)
    return {
        "requested": str(requested),
        "exists": requested.exists(),
        "is_dir": requested.is_dir(),
        "probe_path": str(probe),
        "disk_total_bytes": usage.total,
        "disk_used_bytes": usage.used,
        "disk_free_bytes": usage.free,
        "filesystem": run(["df", "-T", str(probe)]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-path")
    parser.add_argument("--store-root")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    report = {
        "schema": "mecc-host-report-v1",
        "collected_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "git": git_snapshot(),
        "python": sys.version.splitlines()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "packages": package_versions(),
        "torch": torch_snapshot(),
        "gpu": run([
            "nvidia-smi",
            "--query-gpu=index,name,driver_version,memory.total,memory.free,utilization.gpu",
            "--format=csv,noheader,nounits",
        ]),
        "gpu_processes": run([
            "nvidia-smi",
            "--query-compute-apps=gpu_name,pid,used_memory",
            "--format=csv,noheader,nounits",
        ]),
        "cpu": run(["lscpu"]),
        "memory": run(["free", "-b"]),
        "block_devices": run([
            "lsblk", "-J", "-b", "-o",
            "NAME,PATH,TYPE,SIZE,FSTYPE,MOUNTPOINTS,MODEL,ROTA",
        ]),
        "user_systemd": run(["systemctl", "--user", "is-system-running"]),
        "paths": {
            "state_path": path_snapshot(args.state_path),
            "store_root": path_snapshot(args.store_root),
        },
        "environment": {
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", "unset"),
        },
    }
    output = Path(args.out).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"host report written: {output}")
    print("Review GPU, CPU available memory, filesystem type, free space, dependencies, and git.dirty.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

