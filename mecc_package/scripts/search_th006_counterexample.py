#!/usr/bin/env python3
"""Exhaustively search short traces for a counterexample to TH-006."""
from __future__ import annotations
import argparse
from collections import OrderedDict
from itertools import product
import json

class Ours:
    def __init__(self, k_h, k_c, ranked):
        self.k_h, self.k_c = k_h, k_c
        self.hbm = OrderedDict((x, None) for x in ranked[:k_h])
        self.cpu = OrderedDict((x, None) for x in ranked[k_h:k_h + k_c])

    def access(self, item):
        if item in self.hbm:
            self.hbm.move_to_end(item); return "hbm"
        tier = "cpu" if item in self.cpu else "ssd"
        if item in self.cpu: self.cpu.pop(item)
        self.hbm[item] = None
        while len(self.hbm) > self.k_h:
            evicted, _ = self.hbm.popitem(last=False)
            if self.k_c:
                self.cpu[evicted] = None
                while len(self.cpu) > self.k_c: self.cpu.popitem(last=False)
        return tier

class StaticSplit:
    def __init__(self, k_h, k_c, ranked):
        self.k_h = k_h
        self.hbm = OrderedDict((x, None) for x in ranked[:k_h])
        self.static_cpu = set(ranked[k_h:k_h + k_c])

    def access(self, item):
        if item in self.hbm:
            self.hbm.move_to_end(item); return "hbm"
        tier = "cpu" if item in self.static_cpu else "ssd"
        self.hbm[item] = None
        while len(self.hbm) > self.k_h: self.hbm.popitem(last=False)
        return tier

def evaluate(trace, n, k_h, k_c):
    ours, split = Ours(k_h, k_c, range(n)), StaticSplit(k_h, k_c, range(n))
    history = []
    for index, item in enumerate(trace):
        ours_tier, split_tier = ours.access(item), split.access(item)
        history.append({"index": index, "item": item, "ours": ours_tier, "static": split_tier})
        if ours_tier == "ssd" and split_tier != "ssd":
            return {"n": n, "k_h": k_h, "k_c": k_c, "trace": list(trace),
                    "witness_index": index, "history": history}
    return None

def search(max_n=6, max_trace_len=8):
    for n in range(3, max_n + 1):
        for k_h in range(1, n):
            for k_c in range(1, n - k_h):
                for length in range(1, max_trace_len + 1):
                    for trace in product(range(n), repeat=length):
                        witness = evaluate(trace, n, k_h, k_c)
                        if witness: return witness
    return None

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-n", type=int, default=6)
    ap.add_argument("--max-trace-len", type=int, default=8)
    args = ap.parse_args()
    witness = search(args.max_n, args.max_trace_len)
    print(json.dumps({"status": "refuted" if witness else "no_counterexample",
                      "witness": witness}, indent=2))
    return 0 if witness else 1

if __name__ == "__main__": raise SystemExit(main())
