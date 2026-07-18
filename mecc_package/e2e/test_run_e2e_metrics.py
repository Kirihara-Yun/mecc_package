"""CPU-only regression tests for result derivation and provenance metadata."""
import argparse
import unittest

import torch

from run_e2e import _compute_speedups, _detect_platform


class ResultMetricTests(unittest.TestCase):
    def test_speedup_uses_preserved_throughput_precision(self):
        results = {
            "ours": {"tokens_per_s": 0.037421},
            "swapmoe": {"tokens_per_s": 0.024318},
        }
        _compute_speedups(results)
        self.assertEqual(results["ours"]["speedup_vs"]["swapmoe"], 1.539)

    def test_explicit_platform_is_authoritative(self):
        args = argparse.Namespace(platform="A100 80GB")
        self.assertEqual(_detect_platform(args, torch.device("cpu")), "A100 80GB")

    def test_cpu_platform_is_detected(self):
        args = argparse.Namespace(platform=None)
        self.assertEqual(_detect_platform(args, torch.device("cpu")), "CPU")


if __name__ == "__main__":
    unittest.main()
