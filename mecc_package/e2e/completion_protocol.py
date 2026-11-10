"""Opt-in measured-request protocol. Standard-library helpers; no model changes."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import time

E2E = Path(__file__).resolve().parent


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def load_protocol(path):
    raw = Path(path).read_bytes()
    cfg = json.loads(raw)
    allowed = {"version", "task", "sequence", "warmup", "allocation", "disable_m3",
               "prefill_overlap", "bundle_sha256", "bundle", "profile_sha256",
               "equal_uniform_slots"}
    if set(cfg) - allowed or cfg.get("version") != 1:
        raise ValueError("unsupported completion protocol")
    if cfg.get("warmup") not in ("none", "per_request"):
        raise ValueError("warmup must be explicit")
    if cfg.get("allocation") not in ("uniform", "profile"):
        raise ValueError("allocation must be explicit")
    if cfg.get("sequence", "none") not in ("none", "a_b", "b_a", "a_a"):
        raise ValueError("unsupported sequence")
    source = (E2E / cfg["bundle"]).resolve()
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != cfg["bundle_sha256"]:
        raise ValueError("input bundle hash mismatch")
    bundle = json.loads(data)
    for entries in bundle["tasks"].values():
        for entry in entries:
            if hashlib.sha256(entry["text"].encode()).hexdigest() != entry["sha256"]:
                raise ValueError("input entry hash mismatch")
    cfg["sha256"] = hashlib.sha256(raw).hexdigest()
    return cfg, bundle


def select_inputs(cfg, bundle, n):
    task = cfg["task"]
    first = bundle["tasks"][task][:n]
    if len(first) != n:
        raise ValueError("insufficient unique inputs; do not repeat examples")
    sequence = cfg.get("sequence", "none")
    selected = [(task, x) for x in first]
    if sequence != "none":
        a = [("wikitext2", x) for x in bundle["tasks"]["wikitext2"][:n]]
        b = [("gsm8k", x) for x in bundle["tasks"]["gsm8k"][:n]]
        selected = {"a_b": a + b, "b_a": b + a, "a_a": a + a}[sequence]
        if len(selected) != 2 * n:
            raise ValueError("sequence tasks must have equal declared sizes")
    rows = [{"task": name, **entry} for name, entry in selected]
    return [r["text"] for r in rows], bundle["ppl_text"], rows


def counters(caches):
    hits, io, layers = {}, Counter(), {}
    for index, cache in enumerate(caches):
        if cache is None:
            continue
        for name, values in cache.phase_hits.items():
            acc = hits.setdefault(name, [0, 0, 0, 0])
            for i, value in enumerate(values):
                acc[i] += value
        io.update(cache.io_bytes)
        layers[str(index)] = {"hits": {k: list(v) for k,v in cache.phase_hits.items()}, "io": dict(cache.io_bytes)}
    return {"hits": hits, "io": dict(io), "layers": layers}


def subtract(after, before):
    result = {
        "hits": {name: [v - before["hits"].get(name, [0]*4)[i] for i, v in enumerate(values)]
                 for name, values in after["hits"].items()},
        "io": {key: value - before["io"].get(key, 0) for key, value in after["io"].items()},
    }
    if "layers" in after:
        result["layers"] = {name: subtract(value, before.get("layers", {}).get(name, {"hits": {}, "io": {}}))
                            for name, value in after["layers"].items()}
    return result


def resident_state(caches):
    return [{"layer": i, "hbm": list(cache.gpu), "cpu": list(cache.cpu),
             "static_cpu": list(cache.static_cpu)}
            for i, cache in enumerate(caches) if cache is not None]


def storage_bytes(caches):
    sizes, roles, pinned = {}, {}, set()
    for cache in caches:
        if cache is None:
            continue
        groups = {
            "gpu": [v[0] for v in cache.gpu.values()],
            "mirrors": [v[1] for v in cache.gpu.values()],
            "cpu": list(cache.cpu.values()) + list(cache.static_cpu.values()),
            "staging": list(cache._prefetch_buf.values()) + list(getattr(cache, "_nearmiss_buf", {}).values()),
        }
        for role, entries in groups.items():
            keys = roles.setdefault(role, set())
            for ws in entries:
                if ws is None:
                    continue
                for tensor in (ws.w1, ws.w3, ws.w2):
                    store = tensor.untyped_storage()
                    key = (tensor.device.type, tensor.device.index, store.data_ptr())
                    sizes[key] = store.nbytes()
                    keys.add(key)
                    if tensor.device.type == "cpu" and tensor.is_pinned():
                        pinned.add(key)
    return {"role_bytes": {role: sum(sizes[k] for k in keys) for role, keys in roles.items()},
            "unique_cpu_bytes": sum(v for k, v in sizes.items() if k[0] == "cpu"),
            "unique_gpu_bytes": sum(v for k, v in sizes.items() if k[0] == "cuda"),
            "unique_pinned_bytes": sum(sizes[k] for k in pinned),
            "excludes": "trunk, allocator, pending I/O futures, page cache; OS trace accounts process/cgroup"}


def process_io():
    try:
        return {key: int(value) for key, value in (line.split(":") for line in Path("/proc/self/io").read_text().splitlines())}
    except (OSError, ValueError):
        return None


class RequestRecorder:
    def __init__(self, caches, disk_bytes, memory):
        self.caches, self.disk_bytes, self.memory = caches, disk_bytes, memory
        self.phase, self.before, self.rows = None, None, []

    def snapshot(self):
        return {"counters": counters(self.caches), "process_io": process_io(),
                "disk_bytes": self.disk_bytes(), "monotonic_s": time.monotonic()}

    def boundary(self, phase):
        after = self.snapshot()
        if self.before is not None:
            delta = subtract(after["counters"], self.before["counters"])
            before_io, after_io = self.before["process_io"], after["process_io"]
            self.rows.append({"phase": self.phase, **delta,
                "wall_s_with_boundary_overhead": after["monotonic_s"] - self.before["monotonic_s"],
                "disk_read_bytes": None if after["disk_bytes"] is None or self.before["disk_bytes"] is None
                    else after["disk_bytes"] - self.before["disk_bytes"],
                "process_io_delta": None if before_io is None or after_io is None else {
                    k: v - before_io.get(k, 0) for k, v in after_io.items()}})
        self.phase, self.before = phase, after
        for cache in self.caches:
            if cache is not None:
                cache.set_phase(phase)


def append_request(path, row):
    # Save each request before beginning the next one. Failed runs retain rows.
    with Path(path).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        stream.flush()


def measured_alpha(profile, n_layers):
    data = json.loads(Path(profile).read_text())
    alpha = data.get("per_layer_alpha", {})
    result = [float(alpha[str(i)]) for i in range(n_layers)]
    if any(not (0 <= x < 10) for x in result):
        raise ValueError("invalid measured alpha")
    return result
