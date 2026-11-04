"""离线固定输入清单（QA / Code / PPL / 画像）与 token 哈希。

目的（对应 G0 契约 §4 输入清单 + GPT 审计「固定可离线复现的 QA/Code/PPL 输入及 token 哈希」）：
  1. 输入不再依赖网络（WikiText-2 下载失败即回退的问题在此终结）；
  2. 每类输入带原文 sha256 + token 序列 sha256 + token 长度，可验证复现一致性；
  3. 「画像(profile)」与「评估(qa/code/ppl)」样本不重叠，避免用评估数据画像的泄漏。

清单由 `scripts/build_input_manifest.py` 生成；`run_e2e.py` 通过 `--input_manifest` 加载。
"""

import hashlib
import json
from typing import Dict, List, Optional, Tuple

# ── 内置固定样本（评估与画像不重叠）────────────────────────────────────
# 说明：这些是占位固定样本，用于固化「离线 + 哈希」机制；正式实验前应替换为
# 真实离线数据集（先离线下载一次、校验哈希后冻结），样本内容不影响机制正确性。

QA_PROMPTS: List[str] = [
    "Janet buys 3 packs of 4 pencils and 2 packs of 6 erasers. How many items in total?",
    "A train travels 240 kilometers in 3 hours. What is its average speed in km per hour?",
    "If x plus 3 equals 10, what is the value of x?",
]

CODE_PROMPTS: List[str] = [
    "def fibonacci(n):\n    \"\"\"Return the n-th Fibonacci number.\"\"\"\n",
    "def reverse_list(items):\n    \"\"\"Return a reversed copy of items.\"\"\"\n",
    "def is_palindrome(s):\n    \"\"\"Return True if s is a palindrome.\"\"\"\n",
]

PPL_TEXT: str = (
    "The history of computing spans the development of machines that perform "
    "calculations automatically. Early devices such as the abacus and the slide "
    "rule aided arithmetic long before electronic computers existed. The modern "
    "era of computing began in the twentieth century with electromechanical and "
    "electronic machines. Over successive decades, computing hardware grew faster "
    "and smaller, while software became more abstract and portable. These advances "
    "transformed science, industry, and daily life in ways that continue to unfold."
)

# 画像文本：与上面 QA/Code/PPL 评估样本完全不重叠，专用于 profile（per_layer_counts）。
PROFILE_TEXTS: List[str] = [
    "Meteorological observations over several decades reveal long-term trends in "
    "average temperature and precipitation across continental regions.",
    "The taxonomy of marine invertebrates classifies organisms by body symmetry, "
    "developmental patterns, and molecular phylogenetic evidence.",
]

MANIFEST_VERSION = 1


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def tokenize_ids(tokenizer, text: str) -> List[int]:
    """用 tokenizer 得到 input_ids（无 padding/truncation）。"""
    enc = tokenizer(text, return_tensors="pt", truncation=False, padding=False)
    return enc["input_ids"][0].tolist()


def token_sha256(tokenizer, text: str) -> Tuple[str, int]:
    ids = tokenize_ids(tokenizer, text)
    payload = json.dumps(ids, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest(), len(ids)


def _entry(tokenizer, idx: int, text: str) -> Dict:
    t_sha, t_len = token_sha256(tokenizer, text)
    return {
        "id": f"{idx:03d}",
        "text": text,
        "sha256": sha256_hex(text),
        "token_sha256": t_sha,
        "token_len": t_len,
    }


def build_manifest(tokenizer, tokenizer_name: str = "") -> Dict:
    """生成清单 dict（不含文件写出）。"""
    qa = [_entry(tokenizer, i, t) for i, t in enumerate(QA_PROMPTS)]
    code = [_entry(tokenizer, i, t) for i, t in enumerate(CODE_PROMPTS)]
    profile = [_entry(tokenizer, i, t) for i, t in enumerate(PROFILE_TEXTS)]
    ppl_sha, ppl_len = token_sha256(tokenizer, PPL_TEXT)
    return {
        "version": MANIFEST_VERSION,
        "tokenizer": tokenizer_name,
        "categories": {
            "qa": qa,
            "code": code,
            "ppl": {
                "text": PPL_TEXT,
                "sha256": sha256_hex(PPL_TEXT),
                "token_sha256": ppl_sha,
                "token_len": ppl_len,
            },
            "profile": profile,
        },
        "profile_disjoint_from_eval": True,
    }


def load_manifest(path: str) -> Dict:
    """加载清单并做基础格式校验；失败即抛异常，不静默回退。"""
    with open(path, "r", encoding="utf-8") as f:
        m = json.load(f)
    if m.get("version") != MANIFEST_VERSION:
        raise ValueError(f"unsupported manifest version: {m.get('version')}")
    cats = m.get("categories", {})
    for key in ("qa", "code", "profile"):
        if not isinstance(cats.get(key), list):
            raise ValueError(f"manifest.categories.{key} must be a list")
    if not isinstance(cats.get("ppl"), dict):
        raise ValueError("manifest.categories.ppl must be an object")
    return m


def select_prompts(manifest: Dict, category: str, n: int) -> List[str]:
    """从清单某类别取前 n 条评估 prompt 文本。"""
    cats = manifest["categories"]
    items = cats[category]
    return [it["text"] for it in items[:n]]


def select_ppl_text(manifest: Dict) -> str:
    return manifest["categories"]["ppl"]["text"]


def verify_entries(manifest: Dict, tokenizer) -> List[str]:
    """校验清单内所有条目的 token 哈希；返回不一致条目 id 列表（空=全部一致）。"""
    bad = []
    cats = manifest["categories"]
    for cat in ("qa", "code", "profile"):
        for it in cats[cat]:
            t_sha, t_len = token_sha256(tokenizer, it["text"])
            if t_sha != it["token_sha256"] or t_len != it["token_len"]:
                bad.append(f"{cat}/{it['id']}")
    ppl = cats["ppl"]
    t_sha, t_len = token_sha256(tokenizer, ppl["text"])
    if t_sha != ppl["token_sha256"] or t_len != ppl["token_len"]:
        bad.append("ppl")
    return bad
