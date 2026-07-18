"""Tests for explicit legacy expert-store migration."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).parent / "scripts" / "migrate_store_manifest.py"
SPEC = importlib.util.spec_from_file_location("migrate_store_manifest", SCRIPT)
MIGRATE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MIGRATE)


class StoreMigrationTest(unittest.TestCase):
    def fixture(self, root: Path, *, complete=True):
        snapshot = root / "snapshots" / "revision"
        snapshot.mkdir(parents=True)
        (snapshot / "model-00001.safetensors").write_bytes(b"shard")
        (snapshot / "config.json").write_text("{}")
        store = root / "store"; store.mkdir()
        (store / "L0_E0.bin").write_bytes(b"1234")
        if complete:
            (store / "L0_E1.bin").write_bytes(b"5678")
        return snapshot, store

    def test_migrates_only_complete_exact_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, store = self.fixture(Path(tmp))
            manifest = MIGRATE.migrate(
                root=str(store), model="model", model_type="mixtral",
                state_path=str(snapshot), n_layers=1, n_experts=2,
                hidden=1, ffn=1, expert_bytes=4, dtype="torch.float16")
            self.assertTrue(manifest.is_file())

    def test_refuses_incomplete_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, store = self.fixture(Path(tmp), complete=False)
            with self.assertRaises(MIGRATE.StoreManifestError):
                MIGRATE.migrate(
                    root=str(store), model="model", model_type="mixtral",
                    state_path=str(snapshot), n_layers=1, n_experts=2,
                    hidden=1, ffn=1, expert_bytes=4, dtype="torch.float16")
            self.assertFalse((store / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
