import argparse
import contextlib
import io
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import json


SCRIPT = Path(__file__).parent / "scripts" / "experiment_launcher.py"
SPEC = importlib.util.spec_from_file_location("experiment_launcher", SCRIPT)
launcher = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(launcher)


class ExperimentLauncherTest(unittest.TestCase):
    def test_config_fingerprint_is_stable_and_sensitive(self):
        first = launcher.config_fingerprint(["python", "run.py", "--alpha", "1"], "abc")
        self.assertEqual(first, launcher.config_fingerprint(
            ["python", "run.py", "--alpha", "1"], "abc"))
        self.assertNotEqual(first, launcher.config_fingerprint(
            ["python", "run.py", "--alpha", "2"], "abc"))

    def test_unit_name_rejects_unsafe_ids(self):
        self.assertEqual(launcher.unit_name("l2-20260718"), "mecc-exp-l2-20260718")
        for value in ("", "UPPER", "../escape", "has space"):
            with self.assertRaises(ValueError):
                launcher.unit_name(value)

    def test_build_command_uses_explicit_output_and_platform(self):
        args = argparse.Namespace(
            smoke=True, model="unused", state_path=None, store_root="/tmp/store",
            hbm_budget=1.0, cpu_budget=2.0, alpha=1.0, prompt_len=8,
            max_new_tokens=2, n_prompts=1, policies="ours,naive",
            platform="CPU", skip_ppl=True, uniform=True,
        )
        command = launcher.build_command(args, Path("/tmp/result.json"))
        self.assertIn("--smoke", command)
        self.assertEqual(command[command.index("--out") + 1], str(Path("/tmp/result.json")))
        self.assertEqual(command[command.index("--partial_out") + 1],
                         str(Path("/tmp/partial_result.json")))
        self.assertEqual(command[command.index("--platform") + 1], "CPU")
        self.assertEqual(command[command.index("--status_file") + 1],
                         str(Path("/tmp/status.json")))
        self.assertIn("--uniform", command)

    def test_start_refuses_active_job_before_creating_directory(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            launcher, "active_units", return_value=["mecc-exp-running.service"]
        ):
            args = argparse.Namespace(run_id="new", runs_root=tmp, allow_concurrent=False)
            self.assertEqual(launcher.start(args), 2)
            self.assertFalse((Path(tmp) / "new").exists())

    def test_dry_run_does_not_create_run_directory(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            launcher, "active_units", return_value=[]
        ), mock.patch.object(launcher, "environment_snapshot", return_value={}):
            args = argparse.Namespace(
                run_id="dry", runs_root=tmp, allow_concurrent=False, dry_run=True,
                gpu="0", smoke=True, model="unused", state_path=None,
                store_root="/tmp/store", hbm_budget=1.0, cpu_budget=2.0,
                alpha=1.0, prompt_len=8, max_new_tokens=2, n_prompts=1,
                policies="all", platform="CPU", skip_ppl=True,
                uniform=False,
            )
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(launcher.start(args), 0)
            self.assertFalse((Path(tmp) / "dry").exists())

    def test_explicit_configs_are_valid_and_level_safe(self):
        configs = launcher.E2E / "configs"
        for name in ("l0_smoke.json", "l1_deepseek_control.json", "l2_mixtral_main.json"):
            value = launcher.load_config(str(configs / name))
            self.assertIn(value["level"], ("L0", "L1", "L2"))
        bad = {"level": "L0", "smoke": False}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"; path.write_text(__import__("json").dumps(bad))
            with self.assertRaises(ValueError): launcher.load_config(str(path))

    def test_explicit_cli_values_override_config(self):
        config = launcher.E2E / "configs" / "l2_mixtral_main.json"
        args = launcher.parser().parse_args([
            "run", "override", "--config", str(config),
            "--store-root", "/data/custom", "--max-new-tokens", "2",
            "--n-prompts", "1", "--policies", "flashmoe_rf_adaptation",
            "--skip-ppl", "--uniform",
        ])
        merged = launcher.apply_config(args)
        self.assertEqual(merged.store_root, "/data/custom")
        self.assertEqual(merged.max_new_tokens, 2)
        self.assertEqual(merged.n_prompts, 1)
        self.assertEqual(merged.policies, "flashmoe_rf_adaptation")
        self.assertTrue(merged.skip_ppl)
        self.assertTrue(merged.uniform)
        self.assertEqual(merged.platform, "a100-80g")

    def test_resume_retargets_output_and_preserves_store(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            launcher, "active_units", return_value=[]
        ), mock.patch.object(launcher, "environment_snapshot", return_value={}):
            root = Path(tmp); old = root / "old"; old.mkdir()
            command = ["python3", "run_e2e.py", "--store_root", "/data/store",
                       "--out", str(old / "result.json"),
                       "--partial_out", str(old / "partial_result.json"),
                       "--status_file", str(old / "status.json")]
            (old / "run.json").write_text(__import__("json").dumps({"command": command}))
            args = argparse.Namespace(from_run="old", run_id="new", runs_root=tmp,
                                      gpu="0", allow_concurrent=False, dry_run=True)
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(launcher.resume(args), 0)
            rendered = __import__("json").loads(stdout.getvalue())
            resumed = rendered["metadata"]["command"]
            self.assertEqual(resumed[resumed.index("--store_root") + 1], "/data/store")
            self.assertEqual(resumed[resumed.index("--out") + 1], str(root / "new" / "result.json"))
            self.assertEqual(resumed[resumed.index("--partial_out") + 1],
                             str(root / "new" / "partial_result.json"))
            self.assertEqual(resumed[resumed.index("--status_file") + 1],
                             str(root / "new" / "status.json"))
            self.assertFalse((root / "new").exists())

    def test_status_treats_failed_phase_as_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "failed-run"; run.mkdir()
            (run / "status.json").write_text(json.dumps({
                "phase": "failed", "error": "application traceback"}))
            service = mock.Mock(returncode=0, stdout="Result=success\n", stderr="")
            with mock.patch.object(launcher, "systemctl", return_value=service), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(launcher.status("failed-run", tmp), 1)

    def test_status_explains_missing_run_before_querying_systemd(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            launcher, "systemctl"
        ) as systemctl, contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(launcher.status("dry-only", tmp), 2)
            systemctl.assert_not_called()
            self.assertIn("--dry-run does not create it", stderr.getvalue())

    def test_status_requires_result_after_complete_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "complete-run"; run.mkdir()
            (run / "status.json").write_text(json.dumps({"phase": "complete"}))
            service = mock.Mock(returncode=0, stdout="Result=success\n", stderr="")
            with mock.patch.object(launcher, "systemctl", return_value=service), \
                    contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(launcher.status("complete-run", tmp), 1)

    def test_status_reports_partial_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "partial-run"; run.mkdir()
            (run / "status.json").write_text(json.dumps({"phase": "running_policy"}))
            (run / "partial_result.json").write_text("{}\n")
            service = mock.Mock(returncode=0, stdout="Result=success\n", stderr="")
            with mock.patch.object(launcher, "systemctl", return_value=service), \
                    contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(launcher.status("partial-run", tmp), 0)
            rendered = stdout.getvalue()
            self.assertIn('"partial_result_exists": true', rendered)

    def test_report_exports_compact_diagnostic_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); runs = root / "runs"; reports = root / "reports"
            run = runs / "gpu-run"; run.mkdir(parents=True)
            (run / "run.json").write_text(json.dumps({"git_commit": "abc"}))
            (run / "status.json").write_text(json.dumps({"phase": "failed"}))
            (run / "partial_result.json").write_text(json.dumps({"results": {}}))
            (run / "run.log").write_text("first\nsecond\nthird\n")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(launcher.export_report(
                    "gpu-run", str(runs), str(reports), tail_lines=2), 0)
            report = reports / "gpu-run"
            self.assertEqual((report / "run_tail.log").read_text(), "second\nthird\n")
            manifest = json.loads((report / "report_manifest.json").read_text())
            self.assertEqual(manifest["source_log"]["size_bytes"],
                             (run / "run.log").stat().st_size)
            self.assertEqual(manifest["source_log"]["included_tail_lines"], 2)
            self.assertIn("partial_result.json", manifest["files"])
            self.assertFalse((report / "run.log").exists())

    def test_report_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); run = root / "runs" / "same"; run.mkdir(parents=True)
            report = root / "reports" / "same"; report.mkdir(parents=True)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(launcher.export_report(
                    "same", str(root / "runs"), str(root / "reports")), 2)


if __name__ == "__main__":
    unittest.main()
