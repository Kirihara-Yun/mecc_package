"""Common-trace semantic parity test for core and paper-harness caches."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest
from unittest import mock
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

class TrackingWeights:
    cpu_copies = 0

    def __init__(self, uid, device="cpu"):
        self.uid = uid
        self.device = torch.device(device)

    def to(self, device, non_blocking=False):
        target = torch.device(device)
        if target.type == "cpu" and self.device.type != "cpu":
            TrackingWeights.cpu_copies += 1
        return TrackingWeights(self.uid, target.type)

    def pin_memory(self):
        return self

class TrackingStore:
    def load_to_cpu(self, uid, cold=True):
        return TrackingWeights(uid, "cpu")

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

    def test_core_ours_demotes_hbm_without_gpu_to_cpu_copy(self):
        TrackingWeights.cpu_copies = 0
        spec = ModelSpec("tiny", 1, 3, 1, ExpertSpec(2, 2, 24))
        config = OffloadConfig(spec, CacheBudget(1, 1), CachePolicy.OURS, cold_ssd=True)
        cache = CoreCache(0, TrackingStore(), config.budget, torch.device("meta"),
                          config, [(0, e) for e in range(3)])
        cache._access((0, 1))
        cache._access((0, 2))
        self.assertEqual(TrackingWeights.cpu_copies, 0)

    def test_e2e_oversized_cpu_batch_falls_back_to_sequential_access(self):
        cache = E2ECache(0, FakeStore(E2EWeights), RANKED, 1, 2,
                         torch.device("cpu"), policy="ours", cold_ssd=True)
        with mock.patch.object(cache, "batch_prefetch") as batch:
            loaded = list(cache.load_experts((0, 1), (0, 2)))
        batch.assert_not_called()
        self.assertEqual([uid for uid, _ in loaded], [(0, 1), (0, 2)])
        self.assertLessEqual(len(cache.gpu), cache.k_h)

    def test_e2e_decode_sized_cpu_batch_keeps_prefetch_path(self):
        cache = E2ECache(0, FakeStore(E2EWeights), RANKED, 2, 1,
                         torch.device("cpu"), policy="ours", cold_ssd=True)
        with mock.patch.object(cache, "batch_prefetch") as batch:
            list(cache.load_experts((0, 2)))
        batch.assert_called_once_with([(0, 2)])

if __name__ == "__main__": unittest.main()
