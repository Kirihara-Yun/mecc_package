#!/usr/bin/env python3
"""Static structural checks for the MECC paper without requiring a TeX engine."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import re
import sys


DEFAULT_PAPER = Path(__file__).resolve().parents[1] / "paper" / "mecc_paper.tex"


def strip_comments(text: str) -> str:
    """Remove unescaped TeX comments while preserving line boundaries."""
    lines = []
    for line in text.splitlines():
        match = re.search(r"(?<!\\)%", line)
        lines.append(line[: match.start()] if match else line)
    return "\n".join(lines)


def read_with_inputs(path: Path, active: tuple[Path, ...] = ()) -> str:
    """Expand local ``\\input``/``\\include`` files for cross-file checks."""
    path = path.resolve()
    if path in active:
        chain = " -> ".join(str(item) for item in (*active, path))
        raise ValueError(f"recursive TeX input: {chain}")
    text = strip_comments(path.read_text(encoding="utf-8"))

    def expand(match: re.Match[str]) -> str:
        child = Path(match.group(1))
        if not child.suffix:
            child = child.with_suffix(".tex")
        if not child.is_absolute():
            child = path.parent / child
        return read_with_inputs(child, (*active, path))

    return re.sub(r"\\(?:input|include)\{([^{}]+)\}", expand, text)


def check(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        text = read_with_inputs(path)
    except (OSError, ValueError) as exc:
        return [str(exc)]

    bib_keys = re.findall(r"\\bibitem(?:\[[^]]*\])?\{([^{}]+)\}", text)
    cited_keys = {
        key.strip()
        for group in re.findall(r"\\cite(?:\[[^]]*\])?\{([^{}]+)\}", text)
        for key in group.split(",")
        if key.strip()
    }
    duplicate_bib = sorted(key for key, count in Counter(bib_keys).items() if count > 1)
    missing_bib = sorted(cited_keys - set(bib_keys))
    unused_bib = sorted(set(bib_keys) - cited_keys)
    if duplicate_bib:
        errors.append(f"duplicate bibliography keys: {', '.join(duplicate_bib)}")
    if missing_bib:
        errors.append(f"cited keys without bibliography entries: {', '.join(missing_bib)}")
    if unused_bib:
        errors.append(f"unused bibliography entries: {', '.join(unused_bib)}")

    labels = re.findall(r"\\label\{([^{}]+)\}", text)
    refs = set(re.findall(r"\\(?:ref|pageref|eqref)\{([^{}]+)\}", text))
    duplicate_labels = sorted(key for key, count in Counter(labels).items() if count > 1)
    missing_labels = sorted(refs - set(labels))
    if duplicate_labels:
        errors.append(f"duplicate labels: {', '.join(duplicate_labels)}")
    if missing_labels:
        errors.append(f"references to missing labels: {', '.join(missing_labels)}")

    environment_stack: list[str] = []
    for match in re.finditer(r"\\(begin|end)\{([^{}]+)\}", text):
        action, environment = match.groups()
        if action == "begin":
            environment_stack.append(environment)
        elif not environment_stack:
            errors.append(f"unexpected \\end{{{environment}}}")
        elif environment_stack[-1] != environment:
            errors.append(
                f"environment mismatch: expected \\end{{{environment_stack[-1]}}}, "
                f"found \\end{{{environment}}}"
            )
            environment_stack.pop()
        else:
            environment_stack.pop()
    if environment_stack:
        errors.append("unclosed environments: " + ", ".join(environment_stack))

    brace_depth = 0
    for match in re.finditer(r"(?<!\\)[{}]", text):
        brace_depth += 1 if match.group() == "{" else -1
        if brace_depth < 0:
            errors.append("closing brace without matching opening brace")
            break
    if brace_depth > 0:
        errors.append(f"{brace_depth} unclosed opening brace(s)")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paper", nargs="?", type=Path, default=DEFAULT_PAPER)
    args = parser.parse_args()
    errors = check(args.paper)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {args.paper} TeX structure is internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
