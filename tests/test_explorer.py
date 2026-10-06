"""Selection must preserve scientific alternatives and search completeness."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from explore_reconstructions import (VOICE, strict_read, select_bounded, select_pool,
    catalogue, SOURCES, compare_pool, execute_pool)
from reference_reconstruction import evaluate
from verify_m5 import reference
from materials import search, rows, ROOT


class SelectionTests(unittest.TestCase):
    def test_joint_options_select_whole_paradigms(self):
        d = strict_read(VOICE)
        a = select_bounded(d, choices=["voice-analysis=N-anticausative"])
        b = select_bounded(d, choices=["voice-analysis=s-devoicing"])
        self.assertEqual([c["protoform"] for c in evaluate(a)["candidates"]], [["p"]])
        self.assertEqual([c["protoform"] for c in evaluate(b)["candidates"]], [["b"]])
        self.assertEqual(len(d["analyses"]), 2)
        self.assertEqual(a["analyses"][0]["branches"], d["analyses"][0]["branches"])

    def test_incompatible_selections_are_not_negative_reconstruction(self):
        with self.assertRaisesRegex(ValueError, "No declared joint analysis"):
            select_bounded(strict_read(VOICE), analyses=["s-devoicing"], choices=["voice-analysis=N-anticausative"])
        with self.assertRaises(ValueError):
            select_bounded(strict_read(VOICE), choices=["voice-analysis=typo"])

    def test_budget_exhaustion_preserves_incompleteness(self):
        r = evaluate(select_bounded(strict_read(VOICE), budget=0))
        self.assertFalse(r["complete"])
        self.assertFalse(r["no_candidate_in_scope"])

    def test_unknown_hypothesis_is_rejected(self):
        with self.assertRaises(ValueError):
            select_pool("pie", "set-18", ["invented"])

    def test_every_catalogued_query_can_be_selected_exactly(self):
        for dataset in SOURCES:
            original = strict_read(ROOT / SOURCES[dataset])
            original = original.get("batch", original)
            by_id = {q["id"]: q for q in original["inverse"]}
            for c in catalogue(dataset):
                request = select_pool(dataset, c["case"], [c["hypothesis"]], c["scope"])
                selected = request.get("batch", request)
                self.assertEqual(selected["inverse"], [by_id[c["id"]]])
                self.assertEqual({p["id"] for p in selected["packages"]}, set(c["packages"]))
                if "batch" in request:
                    self.assertEqual([s["query_id"] for s in request["query_scopes"]], [c["id"]])

    def test_pool_merger_keeps_both_ancestors(self):
        d = select_pool("tibetan-merger", "merged-affricate-pool")
        result = reference(d["batch"])["inverse"]
        self.assertEqual(result[0]["candidates"], [["ndz"], ["dz"]])
        self.assertEqual(len(compare_pool(result)["candidate_support"]), 2)

    def test_withholding_observations_is_explicit_and_does_not_mutate_source(self):
        original = select_pool("kuki-chin", "vb-1-unmarked")
        reduced = select_pool("kuki-chin", "vb-1-unmarked", omit=["vb-mara"])
        for q in reduced["batch"]["inverse"]:
            self.assertNotIn("vb-mara", [b["doculect_id"] for b in q["branches"]])
        self.assertIn("vb-mara", [b["doculect_id"] for b in original["batch"]["inverse"][0]["branches"]])
        with self.assertRaises(ValueError):
            select_pool("tibetan-merger", "merged-affricate-pool", omit=["onset-a"])

    def test_timeouts_never_prove_absence(self):
        import subprocess
        with patch("explore_reconstructions.subprocess.run", side_effect=subprocess.TimeoutExpired("lean", 1)):
            r, code = execute_pool(select_pool("tibetan-merger", "merged-affricate-pool"))
        self.assertEqual(code, 3)
        self.assertFalse(r["complete"])
        self.assertFalse(r["no_candidate_in_scope"])

    def test_mutated_lean_candidate_result_is_detected(self):
        import subprocess
        d = select_pool("tibetan-merger", "merged-affricate-pool")
        r = reference(d["batch"])
        r["inverse"][0]["candidates"].pop()
        process = subprocess.CompletedProcess([], 0, json.dumps(dict(scope_valid=True, result=r)), "")
        with patch("explore_reconstructions.subprocess.run", return_value=process):
            with self.assertRaisesRegex(ValueError, "disagree"):
                execute_pool(d)

    def test_duplicate_keys_fail_before_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "bad.json"
            p.write_text('{"analyses":[],"analyses":[]}')
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                strict_read(p)


class MaterialTests(unittest.TestCase):
    def test_complete_rows_and_original_unicode_are_preserved(self):
        for dataset, count in [("iecor", 25731), ("hillburmish", 4032), ("sagartst", 12179)]:
            original = {r["ID"]: r for r in rows(dataset, "forms")}
            seen = set()
            for item in search(dataset):
                r = item["source_row"]
                self.assertEqual(r, original[r["ID"]])
                self.assertEqual(item["id"], dataset + ":" + r["ID"])
                seen.add(r["ID"])
            self.assertEqual(len(seen), count)

    def test_old_chinese_is_not_marked_as_phonetic_attestation(self):
        row = next(search("sagartst", language="OldChinese"))
        self.assertNotIn("attestation", row)
        self.assertIn("source analyses", row["representation_note"])

    def test_set_lookup_preserves_published_root(self):
        found = list(search("iecor", set_id="21"))
        self.assertTrue(found)
        original = next(r for r in rows("iecor", "cognatesets") if r["ID"] == "21")
        self.assertIn(original, found[0]["source_cognate_sets"])

    def test_vanbik_keeps_lower_nodes_and_omissions(self):
        d = strict_read(ROOT / "data/materials/vanbik-initials.json")
        self.assertEqual([e["id"] for e in d["entries"]], [str(i) for i in range(1, 1356)])
        self.assertEqual({e["source_level"] for e in d["entries"]}, {"PKC", "PCC", "PNC", "PPC", "PSPC"})
        self.assertEqual(len(d["omissions"]), 1)
        self.assertEqual(d["omissions"][0]["entry_id"], "461")
        self.assertIn("khup", d["omissions"][0]["source_span"])
        self.assertEqual(sum(1 for _ in search("vanbik2009")), 6752)

    def test_expanded_parser_preserves_every_frozen_m6_source_record(self):
        expanded = {e["id"]: e for e in strict_read(ROOT / "data/materials/vanbik-initials.json")["entries"]}
        frozen = strict_read(ROOT / "data/kuki-chin/corpus.json")["sets"]
        for e in frozen:
            for field in ("records", "label", "source_level", "source_reconstruction", "source_locator"):
                self.assertEqual(e[field], expanded[e["id"]][field])


if __name__ == "__main__":
    unittest.main()
