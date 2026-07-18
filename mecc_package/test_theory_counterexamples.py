import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).parent / "scripts" / "search_th006_counterexample.py"
SPEC = importlib.util.spec_from_file_location("th006_search", SCRIPT)
searcher = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(searcher)

class TH006CounterexampleTest(unittest.TestCase):
    def test_minimal_counterexample_is_stable(self):
        witness = searcher.search(max_n=3, max_trace_len=2)
        self.assertIsNotNone(witness)
        self.assertEqual((witness["n"], witness["k_h"], witness["k_c"]), (3, 1, 1))
        self.assertEqual(witness["trace"], [2, 1])
        self.assertEqual(witness["history"][-1]["ours"], "ssd")
        self.assertEqual(witness["history"][-1]["static"], "cpu")

    def test_single_access_has_no_counterexample_in_search_space(self):
        self.assertIsNone(searcher.search(max_n=5, max_trace_len=1))

    def test_th005_static_cpu_can_have_positive_asymptotic_hit_rate(self):
        cache = searcher.StaticSplit(1, 1, range(3))
        tiers = [cache.access(item) for _ in range(20) for item in (1, 2)]
        self.assertEqual(tiers.count("cpu"), 20)
        self.assertEqual(len(tiers), 40)

if __name__ == "__main__": unittest.main()
