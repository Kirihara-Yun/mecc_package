"""CPU regressions for the handoff; no torch, transformers or model download."""
import argparse
import ast
from collections import OrderedDict
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mecc_package/e2e"))
import completion_protocol as cp
import experiment_launcher as launcher
from build_completion_matrix import matrix


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.matrix = matrix()

    def test_frozen_input_hash_and_no_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "protocol.json"
            path.write_text(json.dumps(self.matrix["protocol"]))
            protocol, bundle = cp.load_protocol(path)
            self.assertEqual(len(bundle["tasks"]["humaneval"]), 8)
            protocol["bundle_sha256"] = "wrong"
            path.write_text(json.dumps({k:v for k,v in protocol.items() if k != "sha256"}))
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                cp.load_protocol(path)

    def test_task_sequences_have_equal_request_counts(self):
        bundle = json.loads((cp.E2E / self.matrix["protocol"]["bundle"]).read_text(encoding="utf-8"))
        for sequence, tasks in [("a_b", ["wikitext2", "gsm8k"]),
                                ("b_a", ["gsm8k", "wikitext2"]),
                                ("a_a", ["wikitext2", "wikitext2"])]:
            prompts, _, rows = cp.select_inputs({**self.matrix["protocol"], "sequence": sequence}, bundle, 4)
            self.assertEqual(len(prompts), 8)
            self.assertEqual([rows[0]["task"], rows[4]["task"]], tasks)
        with self.assertRaises(ValueError):
            cp.select_inputs(self.matrix["protocol"], bundle, 100)

    def test_phase_delta_does_not_mix_prefill_and_decode(self):
        cache = SimpleNamespace(phase_hits={}, io_bytes={"ssd_read": 0}, set_phase=lambda p: None)
        recorder = cp.RequestRecorder([cache], lambda: 100, None)
        recorder.boundary("prefill")
        cache.phase_hits["prefill"] = [2, 3, 1, 0]
        cache.io_bytes["ssd_read"] = 336
        recorder.boundary("decode")
        cache.phase_hits["decode"] = [7, 2, 0, 0]
        recorder.boundary("done")
        self.assertEqual(recorder.rows[0]["hits"]["prefill"], [2, 3, 1, 0])
        self.assertEqual(recorder.rows[1]["hits"]["prefill"], [0, 0, 0, 0])
        self.assertEqual(recorder.rows[1]["io"]["ssd_read"], 0)

    def test_profile_plan_modes_differ_when_m3_is_disabled(self):
        from compile_config import compile_plan
        profile = str(ROOT / self.matrix["profile_path"])
        with redirect_stdout(io.StringIO()):
            avg = compile_plan("mistralai/Mixtral-8x7B-Instruct-v0.1", 42, 10.5,
                               profile_path=profile, init_plan="avg", enable_m3=False)
            ranked = compile_plan("mistralai/Mixtral-8x7B-Instruct-v0.1", 42, 10.5,
                                  profile_path=profile, init_plan="per_layer", enable_m3=False)
            alpha = cp.measured_alpha(profile, 32)
            adaptive = compile_plan("mistralai/Mixtral-8x7B-Instruct-v0.1", 42, 10.5,
                profile_path=profile, per_layer_alpha=alpha, enable_m3=False)
        self.assertNotEqual(avg.placement, ranked.placement)
        self.assertEqual(sum(avg.per_layer_k_h), sum(adaptive.per_layer_k_h))
        self.assertEqual(sum(avg.per_layer_k_c), sum(adaptive.per_layer_k_c))
        self.assertTrue(all(h+c <= 8 for h,c in zip(adaptive.per_layer_k_h,adaptive.per_layer_k_c)))

    def test_every_config_is_supported_and_single_policy(self):
        for job in self.matrix["jobs"]:
            config = {**self.matrix["base"], **job["config"], "completion_protocol": "/tmp/protocol.json"}
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(config, f)
                name = f.name
            try:
                launcher.load_config(name)
                args = launcher.apply_config(launcher.parser().parse_args(["run", "test-protocol", "--config", name]))
                command = launcher.build_command(args, Path("result.json"))
                self.assertIn("--completion-protocol", command)
                self.assertNotIn(",", args.policies)
            finally:
                Path(name).unlink()

    def test_memory_limit_is_a_systemd_property_not_an_e2e_argument(self):
        args = launcher.apply_config(launcher.parser().parse_args([
            "run", "test-completion-dry-run", "--dry-run", "--host-memory-max-gib", "64",
            "--completion-protocol", "/tmp/protocol.json", "--platform", "a100-80g"]))
        original = launcher.active_units
        launcher.active_units = lambda: []
        try:
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(launcher.start(args), 0)
            dry = json.loads(output.getvalue())
            self.assertIn("--property=MemoryMax=68719476736", dry["launch"])
            self.assertIn("--property=MemorySwapMax=0", dry["launch"])
            self.assertNotIn("--host-memory-max-gib", dry["metadata"]["command"])
        finally:
            launcher.active_units = original

    def test_frozen_policy_preserves_membership(self):
        # Extract only the real comparator class, avoiding GPU library imports.
        tree = ast.parse((cp.E2E / "policy_plugin.py").read_text(encoding="utf-8"))
        node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "FrozenPlacementPolicy")
        namespace = {"CachePolicy": object, "register": lambda cls: cls}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "frozen_policy", "exec"), namespace)
        class Weights:
            def nbytes(self): return 336
            def pin(self): return self
        cache = SimpleNamespace(gpu=OrderedDict({"a": (Weights(), Weights())}),
            cpu=OrderedDict({"b": Weights()}), _to_gpu=lambda x: x,
            _load_from_ssd=lambda uid: Weights(), record_hit=lambda *a, **kw: None)
        policy = namespace["FrozenPlacementPolicy"]()
        for uid in ["a", "b", "c", "b"]:
            policy.access(cache, uid)
        self.assertEqual(list(cache.gpu), ["a"])
        self.assertEqual(list(cache.cpu), ["b"])

    def test_independent_control_refills_cpu_and_retains_hit(self):
        tree = ast.parse((cp.E2E / "policy_plugin.py").read_text(encoding="utf-8"))
        node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "IndependentCachesPolicy")
        namespace = {"CachePolicy": object, "register": lambda cls: cls}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "independent_control", "exec"), namespace)
        class Weights:
            def nbytes(self): return 336
            def pin(self): return self
        cache = SimpleNamespace(gpu=OrderedDict(), cpu=OrderedDict(), k_c=2,
            _to_gpu=lambda x: x, _load_from_ssd=lambda uid: Weights(),
            record_hit=lambda *a, **kw: None,
            _evict_gpu_if_needed=lambda **kw: None)
        policy = namespace["IndependentCachesPolicy"]()
        policy.access(cache, "a")
        self.assertIn("a", cache.cpu)
        cache.gpu.clear()
        policy.access(cache, "a")
        self.assertIn("a", cache.cpu)
        policy.access(cache, "b")
        policy.access(cache, "c")
        self.assertEqual(list(cache.cpu), ["b", "c"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
