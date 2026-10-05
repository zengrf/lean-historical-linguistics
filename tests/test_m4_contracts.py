"""M4 failure boundaries: interruptions and incomplete/altered evidence fail closed."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_m4_fixtures import analysis, spec
from reference_reconstruction import evaluate
from run_reconstruction import run_command
from verify_m4 import assert_complete_result


class ReconstructionFailureTests(unittest.TestCase):
    def emit(self, report, code=0):
        program = "import json; print(" + repr(json.dumps(report)) + "); raise SystemExit(" + str(code) + ")"
        return run_command([sys.executable, "-c", program], timeout=5)

    def test_external_timeout_is_incomplete_with_unknown_validation(self):
        r, code = run_command([sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.05)
        self.assertEqual(code, 3)
        self.assertEqual(r["status"], "incomplete")
        self.assertIsNone(r["input_valid"])
        self.assertFalse(r["complete"] or r["no_candidate_in_scope"])

    def test_process_failure_is_not_a_negative_reconstruction(self):
        r, code = run_command([sys.executable, "-c", "raise SystemExit(9)"])
        self.assertEqual(code, 2)
        self.assertFalse(r["no_candidate_in_scope"])

    def test_truncated_output_is_an_operational_error(self):
        r, code = run_command([sys.executable, "-c", "print('{')"])
        self.assertEqual(code, 2)
        self.assertFalse(r["no_candidate_in_scope"])

    def test_complete_empty_result_survives_watchdog_unchanged(self):
        d = spec("empty", [analysis("conflict", [["a"], ["b"]])])
        expected = evaluate(d)
        r, code = self.emit(expected)
        self.assertEqual((r, code), (expected, 0))

    def test_incomplete_result_cannot_assert_no_candidate(self):
        r = evaluate(spec("budget", candidate_budget=0)); r["no_candidate_in_scope"] = True
        actual, code = self.emit(r, 3)
        self.assertEqual(code, 2)
        self.assertFalse(actual["no_candidate_in_scope"])

    def test_complete_status_requires_the_whole_scope(self):
        r = evaluate(spec("budget", candidate_budget=0))
        r.update(status="complete", complete=True, no_candidate_in_scope=True)
        _, code = self.emit(r)
        self.assertEqual(code, 2)

    def test_lost_alternative_fails_inverse_set_check(self):
        d = spec("alternatives", [analysis("one", [["a"], None]), analysis("two", [["a"], None])])
        expected = evaluate(d); altered = deepcopy(expected); altered["candidates"].pop(); altered["history_count"] -= 1
        with self.assertRaises(AssertionError):
            assert_complete_result(d, altered, expected["candidates"])

    def test_corrupt_branch_certificate_fails(self):
        d = spec("identity"); expected = evaluate(d); altered = deepcopy(expected)
        altered["candidates"][0]["branches"][0]["output"] = ["b"]
        with self.assertRaises(AssertionError):
            assert_complete_result(d, altered, expected["candidates"])

    def test_choice_binding_is_part_of_candidate_evidence(self):
        d = spec("identity"); expected = evaluate(d); altered = deepcopy(expected)
        altered["candidates"][0]["choice_bindings"] = [dict(group_id="invented", option_id="invented")]
        with self.assertRaises(AssertionError):
            assert_complete_result(d, altered, expected["candidates"])

    def test_empty_complete_flag_must_agree_with_candidates(self):
        d = spec("identity"); r = evaluate(d); r["no_candidate_in_scope"] = True
        _, code = self.emit(r)
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
