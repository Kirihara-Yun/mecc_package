#!/usr/bin/env python3
"""Persist process and cgroup memory samples for an experiment unit.

The monitor is a child in the same systemd unit. Each JSONL row is flushed and
fsynced so the last completed sample survives a unit-wide SIGKILL.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import time


CGROUP_FIELDS = (
    'memory.current', 'memory.peak', 'memory.max', 'memory.high', 'memory.stat',
    'memory.events', 'memory.pressure', 'memory.swap.current',
    'memory.swap.max', 'memory.swap.events',
)


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding='utf-8').strip()
    except (OSError, UnicodeError):
        return None


def key_values(path: Path) -> dict[str, str] | None:
    raw = read_text(path)
    if raw is None:
        return None
    result = {}
    for line in raw.splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            result[key] = value.strip()
    return result


def cgroup_path(pid: int) -> str | None:
    raw = read_text(Path('/proc') / str(pid) / 'cgroup')
    if raw is None:
        return None
    return next((line.split('::', 1)[1] for line in raw.splitlines()
                 if line.startswith('0::')), None)


def sample(pid: int, status_path: Path) -> dict:
    proc = Path('/proc') / str(pid)
    cg = cgroup_path(pid)
    ancestors = {}
    if cg:
        current = Path(cg)
        while True:
            path = Path('/sys/fs/cgroup') / str(current).lstrip('/')
            ancestors[str(current)] = {
                name: read_text(path / name) for name in CGROUP_FIELDS}
            if current == Path('/'):
                break
            current = current.parent
    status = key_values(proc / 'status') or {}
    meminfo = key_values(Path('/proc/meminfo')) or {}
    phase = None
    try:
        phase = json.loads(status_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        pass
    return {
        'time': datetime.now().astimezone().isoformat(timespec='milliseconds'),
        'monotonic_ns': time.monotonic_ns(), 'pid_alive': proc.exists(),
        'pid': pid, 'phase': phase, 'cgroup_path': cg,
        'cgroup': ancestors.get(cg), 'cgroup_ancestors': ancestors,
        'process': {key: status.get(key) for key in
                    ('VmRSS', 'VmHWM', 'VmSize', 'VmLck', 'VmPin', 'Threads')},
        'host': {key: meminfo.get(key) for key in
                 ('MemAvailable', 'MemFree', 'SwapTotal', 'SwapFree')},
        'host_memory_pressure': read_text(Path('/proc/pressure/memory')),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pid', type=int, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--status-file', type=Path, required=True)
    ap.add_argument('--interval', type=float, default=1.0)
    args = ap.parse_args()
    if args.interval < 0.2:
        ap.error('interval must be >= 0.2 seconds')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('a', encoding='utf-8', buffering=1) as stream:
        while True:
            row = sample(args.pid, args.status_file)
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
            if not row['pid_alive']:
                break
            time.sleep(args.interval)


if __name__ == '__main__':
    main()
