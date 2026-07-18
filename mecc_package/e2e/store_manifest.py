"""Manifest and integrity checks for materialized expert stores."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

MANIFEST_NAME = "manifest.json"
PENDING_NAME = "manifest.pending.json"
FORMAT_VERSION = 1

class StoreManifestError(RuntimeError):
    pass

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def source_identity(state_path: str) -> dict[str, Any]:
    root = Path(state_path).resolve()
    if not root.is_dir():
        raise StoreManifestError(f"model state path is not a directory: {root}")
    shards = sorted(root.glob("*.safetensors"))
    if not shards:
        raise StoreManifestError(f"no .safetensors files in model state path: {root}")
    metadata = []
    for name in ("model.safetensors.index.json", "config.json"):
        path = root / name
        if path.is_file():
            metadata.append({"name": name, "size": path.stat().st_size, "sha256": _sha256(path)})
    return {
        "state_path": str(root),
        "revision": root.name if root.parent.name == "snapshots" else None,
        "shards": [{"name": p.name, "size": p.stat().st_size} for p in shards],
        "metadata": metadata,
    }

def expected_manifest(*, model: str, model_type: str, state_path: str,
                      n_layers: int, n_experts: int, hidden: int, ffn: int,
                      expert_bytes: int, dtype: str) -> dict[str, Any]:
    return {
        "format_version": FORMAT_VERSION, "model": model, "model_type": model_type,
        "source": source_identity(state_path),
        "layout": {"n_layers": n_layers, "n_experts": n_experts,
                   "hidden": hidden, "ffn": ffn, "dtype": dtype,
                   "expert_bytes": expert_bytes,
                   "file_pattern": "L{layer}_E{expert}.bin"},
    }

def _identity_view(value: dict[str, Any]) -> dict[str, Any]:
    source = dict(value.get("source") or {})
    source.pop("state_path", None)  # relocation does not change snapshot identity
    return {"format_version": value.get("format_version"),
            "model": value.get("model"), "model_type": value.get("model_type"),
            "source": source, "layout": value.get("layout")}

def validate_store(root: str, expected: dict[str, Any], *, allow_empty: bool = True) -> bool:
    """Return False only for an empty store; reject unidentified or corrupt data."""
    store = Path(root)
    manifest_path = store / MANIFEST_NAME
    pending_path = store / PENDING_NAME
    bins = list(store.glob("L*_E*.bin")) if store.exists() else []
    if not manifest_path.exists():
        if pending_path.exists():
            try:
                pending = json.loads(pending_path.read_text())
            except (OSError, json.JSONDecodeError) as exc:
                raise StoreManifestError(f"invalid pending manifest {pending_path}: {exc}") from exc
            if _identity_view(pending) != _identity_view(expected):
                raise StoreManifestError(f"pending store belongs to a different model/revision: {store}")
            expert_bytes = expected["layout"]["expert_bytes"]
            bad = [path.name for path in bins if path.stat().st_size != expert_bytes]
            if bad:
                raise StoreManifestError("partial store has wrong-sized files: " + ", ".join(bad[:5]))
            return False
        if not bins and allow_empty:
            return False
        raise StoreManifestError(
            f"expert store has data but no {MANIFEST_NAME}: {store}; use a new "
            "store_root or explicitly migrate it after verifying its source")
    try:
        actual = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise StoreManifestError(f"invalid store manifest {manifest_path}: {exc}") from exc
    if _identity_view(actual) != _identity_view(expected):
        raise StoreManifestError(
            f"store manifest does not match requested model/revision/layout: {manifest_path}")
    layout = expected["layout"]
    bad = []
    for layer in range(layout["n_layers"]):
        for expert in range(layout["n_experts"]):
            path = store / f"L{layer}_E{expert}.bin"
            if not path.is_file() or path.stat().st_size != layout["expert_bytes"]:
                bad.append(path.name)
                if len(bad) == 5:
                    break
        if len(bad) == 5:
            break
    if bad:
        raise StoreManifestError("missing or wrong-sized expert files: " + ", ".join(bad))
    expected_count = layout["n_layers"] * layout["n_experts"]
    if len(bins) != expected_count:
        raise StoreManifestError(f"store contains {len(bins)} expert files; expected {expected_count}")
    return True

def write_pending_manifest(root: str, manifest: dict[str, Any]) -> None:
    """Bind a new/partial store to its source before writing expert data."""
    store = Path(root)
    store.mkdir(parents=True, exist_ok=True)
    path = store / PENDING_NAME
    if path.exists():
        return
    _atomic_write(path, manifest)

def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)

def write_manifest(root: str, manifest: dict[str, Any]) -> None:
    """Atomically publish the manifest after verifying every expected file."""
    store = Path(root)
    store.mkdir(parents=True, exist_ok=True)
    layout = manifest["layout"]
    for layer in range(layout["n_layers"]):
        for expert in range(layout["n_experts"]):
            path = store / f"L{layer}_E{expert}.bin"
            if not path.is_file() or path.stat().st_size != layout["expert_bytes"]:
                raise StoreManifestError(f"cannot finalize incomplete store; bad file: {path}")
    _atomic_write(store / MANIFEST_NAME, manifest)
    pending = store / PENDING_NAME
    if pending.exists():
        pending.unlink()
