import copy
import json
from pathlib import Path
import tempfile
import unittest
from result_schema import ResultSchemaError, atomic_write_result, validate_e2e_result

def sample():
    return {"device": "cpu", "mode": "smoke", "model": "tiny", "platform": "CPU",
            "run_time": "2026-07-18T17:00:00+08:00",
            "compiled_plan": {"n_layers": 2, "n_experts": 8, "k_h": 2, "k_c": 3},
            "config": {"max_new_tokens": 2, "prompt_len": 8,
                       "n_prompts": 1, "cold_ssd": True},
            "results": {
                "ours": {"ttft_ms": 1.0, "tpot_ms": 2.0, "tokens_per_s": 0.5,
                         "ppl": "exact(lossless)",
                         "hit_pct": {"hbm": 20.0, "cpu": 30.0, "ssd": 50.0,
                                     "cpu_compute": 0.0},
                         "speedup_vs": {"naive": 2.0}},
                "naive": {"ttft_ms": 2.0, "tpot_ms": 4.0, "tokens_per_s": 0.25,
                          "ppl": 24.5,
                          "hit_pct": {"hbm": 10.0, "cpu": 0.0, "ssd": 90.0,
                                      "cpu_compute": 0.0}}}}

class ResultSchemaTest(unittest.TestCase):
    def test_valid_result_and_atomic_write(self):
        value = sample(); validate_e2e_result(value, ["ours", "naive"])
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nested" / "result.json"
            atomic_write_result(str(target), value, ["ours", "naive"])
            self.assertEqual(json.loads(target.read_text()), value)
            self.assertEqual(list(target.parent.glob("*.tmp")), [])

    def test_rejects_missing_policy_and_metric(self):
        value = sample(); del value["results"]["naive"]
        with self.assertRaises(ResultSchemaError):
            validate_e2e_result(value, ["ours", "naive"])
        value = sample(); del value["results"]["ours"]["ttft_ms"]
        with self.assertRaises(ResultSchemaError):
            validate_e2e_result(value, ["ours", "naive"])

    def test_rejects_bad_hits_timestamp_and_speedup(self):
        for mutate in (
            lambda v: v["results"]["ours"]["hit_pct"].update(ssd=40.0),
            lambda v: v.update(run_time="2026-07-18T17:00:00"),
            lambda v: v["results"]["ours"]["speedup_vs"].update(naive=1.0),
        ):
            value = sample(); mutate(value)
            with self.assertRaises(ResultSchemaError):
                validate_e2e_result(value, ["ours", "naive"])

    def test_validation_failure_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "result.json"; target.write_text("old\n")
            value = sample(); value["platform"] = ""
            with self.assertRaises(ResultSchemaError):
                atomic_write_result(str(target), value, ["ours", "naive"])
            self.assertEqual(target.read_text(), "old\n")

if __name__ == "__main__": unittest.main()
