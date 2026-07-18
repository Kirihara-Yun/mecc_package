"""Common-trace semantic parity test for core and paper-harness caches."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tiered_engine import ExpertWeights as E2EWeights
from tiered_engine import LayerExpertCache as E2ECache
from mecc_framework.base.config import (CacheBudget, CachePolicy, ExpertSpec,
                                        ModelSpec, OffloadConfig)
from mecc_framework.base.expert import ExpertWeights as CoreWeights
from mecc_framework.cache.engine import LayerExpertCache as CoreCache

TRACE = [(0, e) for e in (0, 1, 2, 0, 1, 2)]
RANKED = [(0, e) for e in range(4)]

class FakeStore:
    def __init__(self, weight_type):
        self.weight_type = weight_type
        self.loads = []

    def load_to_cpu(self, uid, cold=True):
        self.loads.append((uid, cold))
        seed = uid[0] * 10 + uid[1] + 1
        w1 = torch.full((2, 2), float(seed))
        w3 = torch.full((2, 2), float(seed + 1))
        w2 = torch.full((2, 2), float(seed + 2))
        return self.weight_type(w1, w3, w2)

def core_cache(policy):
    spec = ModelSpec("tiny", 1, 4, 1, ExpertSpec(2, 2, 24))
    config = OffloadConfig(spec, CacheBudget(1, 1), CachePolicy(policy), cold_ssd=True)
    return CoreCache(0, FakeStore(CoreWeights), config.budget, torch.device("cpu"),
                     config, RANKED)

def e2e_cache(policy):
    return E2ECache(0, FakeStore(E2EWeights), RANKED, 1, 1,
                    torch.device("cpu"), policy=policy, cold_ssd=True)

def snapshot(cache, implementation):
    hbm = cache.hbm if implementation == "core" else cache.gpu
    return {"hbm": list(hbm), "cpu": list(cache.cpu),
            "static_cpu": list(cache.static_cpu), "hits": list(cache.hits)}

def run_trace(cache, implementation):
    states = []
    for uid in TRACE:
        list(cache.load_experts(uid))
        states.append(snapshot(cache, implementation))
    return states

class CacheConsistencyTest(unittest.TestCase):
    def test_all_registered_baselines_have_identical_trace_semantics(self):
        for policy in ("ours", "swapmoe", "fiddler", "naive"):
            with self.subTest(policy=policy):
                core = core_cache(policy)
                e2e = e2e_cache(policy)
                self.assertEqual(run_trace(core, "core"), run_trace(e2e, "e2e"))

    def test_ours_exercises_cpu_promotion_and_hbm_cpu_demotion(self):
        states = run_trace(core_cache("ours"), "core")
        self.assertEqual(states[0]["hits"], [1, 0, 0, 0])
        self.assertEqual(states[1]["hits"], [1, 1, 0, 0])
        self.assertEqual(states[1]["hbm"], [(0, 1)])
        self.assertEqual(states[1]["cpu"], [(0, 0)])
        self.assertEqual(states[2]["hits"], [1, 1, 1, 0])

if __name__ == "__main__": unittest.main()
