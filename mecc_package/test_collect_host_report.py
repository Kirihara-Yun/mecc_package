import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "mecc_package" / "scripts" / "collect_host_report.py"


class CollectHostReportTest(unittest.TestCase):
    def test_report_is_written_without_gpu_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "nested" / "host.json"
            subprocess.run(
                [sys.executable, str(SCRIPT), "--state-path", tmp,
                 "--store-root", str(Path(tmp) / "new-store"), "--out", str(output)],
                cwd=REPO, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True,
            )
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["schema"], "mecc-host-report-v1")
            self.assertIn("commit", report["git"])
            self.assertTrue(report["paths"]["state_path"]["exists"])
            self.assertFalse(report["paths"]["store_root"]["exists"])
            self.assertGreater(report["paths"]["store_root"]["disk_free_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
