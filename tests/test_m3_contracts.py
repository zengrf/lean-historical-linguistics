"""Acceptance gate regressions: malformed reports cannot satisfy M3's site floor."""
from copy import deepcopy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_m3_fixtures import generate
from reference_correspondence import evaluate
from verify_m3 import assess_sites, strict_json


class M3EvidenceGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        files = generate(); manifest = json.loads(files["manifest.json"])
        cls.baseline = [dict(fixture=f["path"], counts_toward_site_suite=True,
                             result=evaluate(json.loads(files[f["path"]])))
                        for f in manifest["fixtures"] if f["counts_toward_site_suite"]]

    def setUp(self):
        self.fixtures = deepcopy(self.baseline)

    def test_baseline_exceeds_each_separate_floor(self):
        counts = assess_sites(self.fixtures)
        self.assertEqual((counts["site_count"], counts["incomplete_site_count"], counts["conflicting_site_count"]), (140, 125, 20))

    def test_repeating_a_site_cannot_increase_the_count(self):
        self.fixtures.append(deepcopy(self.fixtures[0]))
        with self.assertRaises(AssertionError):
            assess_sites(self.fixtures)

    def test_structural_mutations_do_not_pad_the_floor(self):
        for f in self.fixtures[30:]:
            f["counts_toward_site_suite"] = False
        with self.assertRaises(AssertionError):
            assess_sites(self.fixtures)

    def test_support_must_be_computed_not_just_claimed(self):
        self.fixtures[0]["result"]["sites"][0]["support"][0]["computed"] = 0
        with self.assertRaises(AssertionError):
            assess_sites(self.fixtures)

    def test_every_counted_site_needs_an_assignment(self):
        self.fixtures[0]["result"]["sites"][0]["assignment_count"] = 0
        with self.assertRaises(AssertionError):
            assess_sites(self.fixtures)

    def test_conflicting_and_incomplete_are_separate_floors(self):
        for f in self.fixtures:
            for s in f["result"]["sites"]:
                s["conflicting_with"] = []
        with self.assertRaises(AssertionError):
            assess_sites(self.fixtures)

    def test_low_incomplete_count_fails_despite_enough_total_sites(self):
        for f in self.fixtures:
            for s in f["result"]["sites"]:
                s["incomplete"] = False
        with self.assertRaises(AssertionError):
            assess_sites(self.fixtures)

    def test_python_byte_oracle_rejects_escaped_duplicate_keys(self):
        with self.assertRaises(ValueError):
            strict_json(b'{"claim":1,"cl\\u0061im":2}')

    def test_surrogate_escape_profile_does_not_reject_literal_backslash(self):
        with self.assertRaises(ValueError):
            strict_json(b'"\\ud800\\udc00"')
        self.assertEqual(strict_json(b'"\\\\ud800"'), r"\ud800")


if __name__ == "__main__":
    unittest.main()
