import json
from pathlib import Path
import tempfile
import unittest
from store_manifest import (StoreManifestError, expected_manifest, validate_store,
                            write_manifest, write_pending_manifest)

class StoreManifestTest(unittest.TestCase):
    def make_source(self, root):
        source = root / "snapshots" / "revision123"
        source.mkdir(parents=True)
        (source / "model-00001-of-00001.safetensors").write_bytes(b"weights")
        (source / "model.safetensors.index.json").write_text('{"weight_map": {}}')
        (source / "config.json").write_text('{"model_type": "mixtral"}')
        return source

    def manifest(self, root):
        return expected_manifest(model="model", model_type="mixtral",
            state_path=str(self.make_source(root)), n_layers=2, n_experts=2,
            hidden=2, ffn=3, expert_bytes=8, dtype="torch.float16")

    def fill_store(self, store):
        store.mkdir()
        for layer in range(2):
            for expert in range(2):
                (store / f"L{layer}_E{expert}.bin").write_bytes(b"12345678")

    def test_empty_store_is_not_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(validate_store(str(root / "store"), self.manifest(root)))

    def test_refuses_legacy_unidentified_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fill_store(root / "store")
            with self.assertRaises(StoreManifestError):
                validate_store(str(root / "store"), self.manifest(root))

    def test_pending_manifest_allows_safe_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); store = root / "store"; store.mkdir()
            manifest = self.manifest(root)
            write_pending_manifest(str(store), manifest)
            (store / "L0_E0.bin").write_bytes(b"12345678")
            self.assertFalse(validate_store(str(store), manifest))

    def test_write_and_validate_complete_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); store = root / "store"; self.fill_store(store)
            manifest = self.manifest(root); write_manifest(str(store), manifest)
            self.assertTrue(validate_store(str(store), manifest))
            saved = json.loads((store / "manifest.json").read_text())
            self.assertEqual(saved["source"]["revision"], "revision123")

    def test_detects_corrupt_and_wrong_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); store = root / "store"; self.fill_store(store)
            manifest = self.manifest(root); write_manifest(str(store), manifest)
            (store / "L1_E1.bin").write_bytes(b"bad")
            with self.assertRaises(StoreManifestError): validate_store(str(store), manifest)
            (store / "L1_E1.bin").write_bytes(b"12345678")
            wrong = json.loads(json.dumps(manifest)); wrong["source"]["revision"] = "other"
            with self.assertRaises(StoreManifestError): validate_store(str(store), wrong)

if __name__ == "__main__": unittest.main()
