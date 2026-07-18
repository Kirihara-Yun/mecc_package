"""CPU-only correctness tests for the compiler's statistical helpers."""
import unittest

import numpy as np

from compiler import estimate_alpha


class EstimateAlphaTests(unittest.TestCase):
    def test_recovers_synthetic_discrete_zipf(self):
        n = 64
        expected = 1.35
        ranks = np.arange(1, n + 1, dtype=np.float64)
        probabilities = ranks ** -expected
        probabilities /= probabilities.sum()
        counts = np.rint(probabilities * 1_000_000).astype(int).tolist()
        self.assertAlmostEqual(estimate_alpha(counts), expected, delta=0.01)

    def test_distribution_changes_estimate(self):
        uniform = [100] * 16
        concentrated = [10_000] + [1] * 15
        self.assertLess(estimate_alpha(uniform), estimate_alpha(concentrated))

    def test_empty_and_all_zero_profiles_are_neutral(self):
        self.assertEqual(estimate_alpha([]), 1.0)
        self.assertEqual(estimate_alpha([0, 0, 0]), 1.0)

    def test_negative_count_is_rejected(self):
        with self.assertRaises(ValueError):
            estimate_alpha([2, -1, 3])


if __name__ == "__main__":
    unittest.main()
