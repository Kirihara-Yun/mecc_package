"""CPU-only tests for high-risk prose claim checks."""
import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).parent / "scripts" / "verify_claims.py"
SPEC = importlib.util.spec_from_file_location("verify_claims", SCRIPT)
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class TextClaimRuleTests(unittest.TestCase):
    def violations(self, text):
        return VERIFY._text_claim_violations("example.md", text)

    def test_rejects_unverified_swapmoe_quality_identity(self):
        found = self.violations("SwapMoE 2-bit 有损 PPL 36.12")
        self.assertEqual(found[0][1], "X6_BASELINE_IDENTITY")

    def test_allows_explicit_unverified_warning(self):
        self.assertFalse(self.violations(
            "SwapMoE 2-bit PPL 36.12 的身份待核"))

    def test_requires_tpot_scope_for_162(self):
        self.assertTrue(self.violations("OURS 快 1.62×"))
        self.assertFalse(self.violations("OURS 的 TPOT 快 1.62×"))

    def test_rejects_wrong_mixtral_main_platform(self):
        found = self.violations("Mixtral 主结果来源 RTX 5090")
        self.assertEqual(found[0][1], "M5_PLATFORM")


if __name__ == "__main__":
    unittest.main()
