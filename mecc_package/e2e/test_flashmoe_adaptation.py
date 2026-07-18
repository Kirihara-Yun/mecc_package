"""CPU-only behavioral tests for the paper-derived FlashMoE adaptation."""
from __future__ import annotations

import unittest

import torch

from tiered_engine import ExpertWeights, LayerExpertCache


class FakeStore:
    def load_to_cpu(self, uid, cold=True):
        value = float(uid[1] + 1)
        tensor = torch.full((2, 2), value)
        return ExpertWeights(tensor, tensor + 1, tensor + 2)


def make_cache(policy="flashmoe_rf_adaptation", k_h=1, k_c=1):
    ranked = [(0, expert) for expert in range(5)]
    return LayerExpertCache(0, FakeStore(), ranked, k_h, k_c,
                            torch.device("cpu"), policy=policy, cold_ssd=True)


class FlashMoeAdaptationTest(unittest.TestCase):
    def test_frequent_expert_can_survive_over_more_recent_candidate(self):
        cache = make_cache()
        hot = (0, 1)
        for _ in range(10):
            list(cache.load_experts(hot))
        list(cache.load_experts((0, 3)))
        list(cache.load_experts((0, 4)))
        self.assertIn(hot, cache.cpu)
        self.assertNotIn((0, 3), cache.cpu)

    def test_preserves_exact_weights_across_ssd_cpu_and_hbm_hits(self):
        cache = make_cache(k_c=2)
        uid = (0, 4)
        expected = FakeStore().load_to_cpu(uid)
        for _ in range(3):
            actual = next(cache.load_experts(uid))[1]
            self.assertTrue(torch.equal(actual.w1, expected.w1))
            self.assertTrue(torch.equal(actual.w2, expected.w2))
            self.assertTrue(torch.equal(actual.w3, expected.w3))
        self.assertEqual(sum(cache.hits), 3)


if __name__ == "__main__":
    unittest.main()
