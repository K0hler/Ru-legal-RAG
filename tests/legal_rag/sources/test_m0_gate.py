import importlib.util
import hashlib
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "m0_gate", ROOT / "docs/assets/generate_m0_gate.py"
)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class M0GateTest(unittest.TestCase):
    def test_gate_blocks_failed_unresolved_missing_or_changed_evidence(self):
        expected = {"M0-01.1", "M0-10.4"}
        decisions = {key: {"status": "pass"} for key in expected}
        self.assertEqual(gate.gate_decision(expected, decisions), "pass")
        for state in ("fail", "unresolved"):
            decisions["M0-10.4"]["status"] = state
            self.assertEqual(gate.gate_decision(expected, decisions), state)
        decisions["M0-10.4"]["status"] = "partial"
        with self.assertRaisesRegex(ValueError, "unsupported"):
            gate.gate_decision(expected, decisions)
        del decisions["M0-10.4"]
        with self.assertRaisesRegex(ValueError, "every acceptance"):
            gate.gate_decision(expected, decisions)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual(len(gate.verify_hashes(root, {"evidence": "bad"})), 1)
            (root / "evidence").write_bytes(b"modified")
            self.assertEqual(len(gate.verify_hashes(root, {"evidence": "bad"})), 1)
            expected_hash = hashlib.sha256(b"modified").hexdigest()
            self.assertEqual(gate.verify_hashes(root, {"evidence": expected_hash}), [])
            (root / "evidence").write_bytes(b"line\r\n")
            expected_hash = hashlib.sha256(b"line\n").hexdigest()
            self.assertEqual(
                gate.verify_hashes(root, {"evidence": expected_hash}, normalize_lf=True), []
            )

    def test_plan_retains_every_multiline_acceptance_criterion(self):
        plan = "### M0-11 — Gold\n\nAcceptance:\n\n- first;\n- second\n  continued;\n\nNotes."
        self.assertEqual(gate.acceptance_criteria(plan), {"M0-11": ["first;", "second continued;"]})
        plan += "\n\nM0 passes only when:\n\n- gate one;\n- gate two.\n\nNotes."
        self.assertEqual(gate.acceptance_criteria(plan)["M0-GATE"], ["gate one;", "gate two."])


if __name__ == "__main__":
    unittest.main()
