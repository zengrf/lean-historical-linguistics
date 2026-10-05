"""Acceptance-boundary tests for independent M2 hand-work evidence."""
import copy
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_m2 import assess_review, canonical_hash


class IndependentM2ReviewTests(unittest.TestCase):
    def setUp(self):
        self.semantics = b"Synthetic test-only semantics; not a real reviewer response."
        digest = hashlib.sha256(self.semantics).hexdigest()
        self.packet = dict(semantics_sha256=digest,
                           cases=[dict(id=f"case-{i}", input=["a"], rules=[{}]) for i in range(10)])
        self.response = dict(reviewer_id="synthetic-test-reviewer", reviewer_type="independent_ai_agent",
                             independent_of_implementation=True, method="Synthetic test fixture only",
                             packet_sha256=canonical_hash(self.packet), semantics_sha256=digest,
                             provenance=dict(implementation_read=False, interpreter_executed=False,
                                             expected_answers_consulted=False, answers_frozen_before_comparison=True),
                             specification_ambiguities=[],
                             entries=[dict(id=c["id"], steps=[["a"]], output=["a"], reasoning="Unchanged synthetic stage.")
                                      for c in self.packet["cases"]])

    def assess(self):
        return assess_review(self.packet, self.response, self.semantics)

    def test_complete_synthetic_attestation_has_explicit_ai_type(self):
        r = self.assess()
        self.assertEqual(r["status"], "passed")
        self.assertEqual(r["reviewer_type"], "independent_ai_agent")

    def test_absent_response_does_not_pass(self):
        self.assertEqual(assess_review(self.packet, None, self.semantics)["status"], "pending")

    def test_implementation_consultation_does_not_pass(self):
        self.response["provenance"]["implementation_read"] = True
        self.assertEqual(self.assess()["status"], "pending")

    def test_interpreter_execution_is_not_hand_work(self):
        self.response["provenance"]["interpreter_executed"] = True
        self.assertEqual(self.assess()["status"], "pending")

    def test_expected_answer_consultation_is_not_blind(self):
        self.response["provenance"]["expected_answers_consulted"] = True
        self.assertEqual(self.assess()["status"], "pending")

    def test_stale_semantics_reopens_review(self):
        self.semantics += b" changed"
        self.assertEqual(self.assess()["status"], "pending")

    def test_changed_case_reopens_review(self):
        self.packet["cases"][0]["input"] = ["b"]
        self.assertEqual(self.assess()["status"], "pending")

    def test_duplicate_cases_cannot_inflate_coverage(self):
        self.response["entries"][-1] = copy.deepcopy(self.response["entries"][0])
        r = self.assess()
        self.assertEqual(r["status"], "pending")
        self.assertEqual(r["reviewed_cases"], 9)

    def test_unchanged_stage_must_be_written(self):
        self.response["entries"][0]["steps"] = []
        self.assertEqual(self.assess()["status"], "pending")

    def test_final_word_must_match_last_stage(self):
        self.response["entries"][0]["output"] = ["b"]
        self.assertEqual(self.assess()["status"], "pending")

    def test_missing_rationale_does_not_pass(self):
        self.response["entries"][0]["reasoning"] = ""
        self.assertEqual(self.assess()["status"], "pending")

    def test_self_review_does_not_pass(self):
        self.response["reviewer_id"] = "/root"
        self.assertEqual(self.assess()["status"], "pending")

    def test_unknown_reviewer_type_does_not_pass(self):
        self.response.pop("reviewer_type")
        self.assertEqual(self.assess()["status"], "pending")

    def test_unresolved_specification_question_does_not_pass(self):
        self.response["specification_ambiguities"] = ["Which side sees deletions?"]
        self.assertEqual(self.assess()["status"], "pending")


if __name__ == "__main__":
    unittest.main()
