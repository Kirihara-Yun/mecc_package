#!/usr/bin/env python3
"""生成离线固定输入清单（QA/Code/PPL/画像）+ token 哈希，输出 JSON。

用法:
  python3 scripts/build_input_manifest.py \
      --state-path /data/qinzy/models/models--mistralai--Mixtral-8x7B-Instruct-v0.1/snapshots/eba92302... \
      --out mecc_package/e2e/offline_inputs.json
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "e2e"))

from offline_inputs import build_manifest, verify_entries  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-path", required=True, help="模型 snapshot 目录（含 tokenizer）")
    ap.add_argument("--out", default="offline_inputs.json")
    ap.add_argument("--tokenizer-name", default="", help="写入 manifest 的 tokenizer 标识")
    args = ap.parse_args()

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.state_path)

    manifest = build_manifest(tok, args.tokenizer_name)

    # 生成后自校验
    bad = verify_entries(manifest, tok)
    if bad:
        print(f"ERROR: token hash mismatch in entries: {bad}", file=sys.stderr)
        return 1

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    cats = manifest["categories"]
    print(f"wrote {args.out}")
    print(f"  qa={len(cats['qa'])} code={len(cats['code'])} "
          f"profile={len(cats['profile'])} ppl_tokens={cats['ppl']['token_len']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
