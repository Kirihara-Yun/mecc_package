#!/usr/bin/env python3
"""Bind a verified legacy expert store to an explicit model snapshot."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


E2E = Path(__file__).resolve().parents[1] / "e2e"
sys.path.insert(0, str(E2E))

from store_manifest import (  # noqa: E402
    MANIFEST_NAME,
    StoreManifestError,
    expected_manifest,
    validate_store,
    write_manifest,
)


def migrate(*, root: str, model: str, model_type: str, state_path: str,
            n_layers: int, n_experts: int, hidden: int, ffn: int,
            expert_bytes: int, dtype: str) -> Path:
    store = Path(root).resolve()
    if (store / MANIFEST_NAME).exists():
        raise StoreManifestError(f"store already has {MANIFEST_NAME}: {store}")
    manifest = expected_manifest(
        model=model, model_type=model_type, state_path=state_path,
        n_layers=n_layers, n_experts=n_experts, hidden=hidden, ffn=ffn,
        expert_bytes=expert_bytes, dtype=dtype,
    )
    bins = list(store.glob("L*_E*.bin"))
    expected_names = {
        f"L{layer}_E{expert}.bin"
        for layer in range(n_layers)
        for expert in range(n_experts)
    }
    actual_names = {path.name for path in bins}
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)[:5]
        extra = sorted(actual_names - expected_names)[:5]
        raise StoreManifestError(
            f"legacy store layout mismatch; missing={missing}, extra={extra}")
    # write_manifest checks every expected file and size before publishing.
    # validate_store then additionally rejects surplus expert files.
    write_manifest(str(store), manifest)
    if not validate_store(str(store), manifest, allow_empty=False):
        raise StoreManifestError("migrated store did not validate")
    return store / MANIFEST_NAME


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-type", required=True)
    parser.add_argument("--state-path", required=True)
    parser.add_argument("--n-layers", type=int, required=True)
    parser.add_argument("--n-experts", type=int, required=True)
    parser.add_argument("--hidden", type=int, required=True)
    parser.add_argument("--ffn", type=int, required=True)
    parser.add_argument("--expert-bytes", type=int, required=True)
    parser.add_argument("--dtype", required=True)
    args = parser.parse_args()
    try:
        path = migrate(
            root=args.root, model=args.model, model_type=args.model_type,
            state_path=args.state_path, n_layers=args.n_layers,
            n_experts=args.n_experts, hidden=args.hidden, ffn=args.ffn,
            expert_bytes=args.expert_bytes, dtype=args.dtype,
        )
    except StoreManifestError as exc:
        print(f"migration refused: {exc}", file=sys.stderr)
        return 2
    print(f"legacy store manifest published and validated: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
