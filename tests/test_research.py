"""Research semantics, incomplete searches, provenance and local HTTP contracts.

These tests run without Lean; verify_research.py additionally executes native
Lean and compares every result against the independent interpreter.
"""

from copy import deepcopy
from itertools import combinations, product
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from reference_research import analyze_matrix, chronology, paradigm, realize
from build_research_examples import (
    build,
    tone_example,
    stem_example,
    affix_example,
    chronology_example,
)
from build_pie_corpus import ROOT, encoded
from research import checked, matrix_analysis, IncompleteSearch, explore_chronology
from serve_ui import (
    constrained_bounds,
    browse,
    make_server,
    run_request,
    strict_json,
    describe,
    EXAMPLE_INFO,
)


def matrix(rows, selected=(0, 1, 2), budget=4096):
    return dict(
        schema_version="1.0.0",
        id="test",
        axes=["A", "B", "C"],
        selected=list(selected),
        subset_budget=budget,
        histories=[
            dict(id=f"h-{i}", agreements=list(row), predictions=[str(v) for v in row])
            for i, row in enumerate(rows)
        ],
    )


class EvidenceTests(unittest.TestCase):
    def test_all_two_history_three_axis_minimal_conflicts_against_proper_subsets(self):
        for first, second in product(product([False, True], repeat=3), repeat=2):
            r = matrix([first, second])
            got = analyze_matrix(r)

            def sat(sub):
                return any(all(h[i] for i in sub) for h in [first, second])

            expected = []
            for size in range(4):
                for core in combinations(range(3), size):
                    if not sat(core) and all(
                        sat(sub) for n in range(size) for sub in combinations(core, n)
                    ):
                        expected.append(frozenset(core))
            self.assertEqual(
                set(map(frozenset, got["minimal_conflicts"])), set(expected)
            )

    def test_incomplete_conflict_search_keeps_known_empty_survivor_set(self):
        r = analyze_matrix(
            matrix([[True, False, True], [False, True, False]], budget=0)
        )
        self.assertEqual(r["survivors"], [])
        self.assertEqual(r["minimal_conflicts"], [])
        self.assertFalse(r["complete"])
        self.assertEqual(r["subsets_examined"], 0)

    def test_satisfiable_matrix_needs_no_conflict_search(self):
        r = analyze_matrix(matrix([[True, True, True]], budget=0))
        self.assertTrue(r["conflicts_complete"])
        self.assertEqual(r["minimal_conflicts"], [])

    def test_no_observations_is_vacuous_and_preserves_all_identities(self):
        r = analyze_matrix(
            matrix([[True, False, True], [False, True, False]], selected=[])
        )
        self.assertEqual(r["survivors"], ["h-0", "h-1"])
        self.assertEqual(
            r["equivalence_classes"], [dict(prediction=[], histories=["h-0", "h-1"])]
        )
        self.assertEqual([p["distinguished_pairs"] for p in r["probes"]], [1, 1, 1])

    def test_prediction_pair_counts_include_model_identity_but_not_probability(self):
        m = matrix([[True, True, True]] * 3, selected=[0])
        m["histories"][2]["predictions"][1] = "different"
        r = analyze_matrix(m)
        self.assertEqual([p["distinguished_pairs"] for p in r["probes"]], [2, 0])
        self.assertEqual(len(r["equivalence_classes"]), 1)

    def test_projection_ignores_unobserved_tone_but_retains_probe_tone(self):
        axes = [
            dict(id=x, label=x, observed=True, expected=dict(segments=["a"], tone=None))
            for x in ["A", "B"]
        ]
        states = [
            dict(
                id=f"h-{t}",
                agreements=[True, True],
                predictions=[dict(segments=["a"], tone=t)] * 2,
            )
            for t in ["H", "L"]
        ]
        with patch("research.checked", side_effect=lambda _, m, b: analyze_matrix(m)):
            r = matrix_analysis(axes, states, selected=["A"])
        self.assertEqual(len(r["analysis"]["equivalence_classes"]), 1)
        self.assertEqual(r["analysis"]["probes"][0]["distinguished_pairs"], 1)

    def test_unknown_observation_is_not_interpreted_as_absence(self):
        axis = dict(id="A", label="A", observed=False, expected=None)
        with self.assertRaisesRegex(ValueError, "unobserved"):
            matrix_analysis([axis], [dict(id="h")], selected=["A"])
        with self.assertRaisesRegex(ValueError, "nonempty universe"):
            matrix_analysis([axis], [], selected=[])

    def test_timeout_does_not_claim_completion(self):
        with patch(
            "research.subprocess.run",
            side_effect=subprocess.TimeoutExpired("research_check", 1),
        ):
            with self.assertRaises(IncompleteSearch):
                checked("matrix", matrix([[True] * 3]))

    def test_mutated_native_result_rejected(self):
        r = matrix([[True] * 3])
        out = analyze_matrix(r)
        out["survivors"] = []
        with patch(
            "research.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, json.dumps(out), ""),
        ):
            with self.assertRaisesRegex(ValueError, "disagree"):
                checked("matrix", r)


class ParadigmTests(unittest.TestCase):
    def test_examples_reproduce_exactly_with_source_hash(self):
        for name, value in build().items():
            self.assertEqual(
                (ROOT / "data/research" / name).read_bytes(), encoded(value)
            )

    def test_source_discrepancy_preserved_as_whole_readings(self):
        d = tone_example()
        cells = [a["cells"][0] for a in d["analyses"]]
        self.assertEqual(
            [realize(c, d["pool"][1])["output"]["tone"] for c in cells],
            ["vb-Hakha-Lai-L", "vb-Hakha-Lai-F"],
        )
        self.assertEqual(sum(h["accepted"] for h in paradigm(d)["histories"]), 2)

    def test_lexical_allomorphy_keeps_one_stem_linked_across_all_cells(self):
        r = paradigm(stem_example())
        accepted = [h for h in r["histories"] if h["accepted"]]
        self.assertEqual(len(accepted), 1)
        self.assertEqual(
            [c["output"]["segments"] for c in accepted[0]["cells"]],
            [
                ["b", "e", "e", "l"],
                ["b", "e", "l", "h"],
                ["b", "e", "l", "ʔ"],
                ["b", "e", "l", "ʔ"],
            ],
        )

    def test_affixes_vowel_alternation_and_conditioning_stage(self):
        d = affix_example()
        root = d["pool"][0]
        c = d["analyses"][0]["cells"][1]
        r = realize(c, root)
        self.assertEqual(
            r["output"], dict(segments=["n", "+", "p", "e", "+", "s"], tone="H")
        )
        c["tone_rules"][0]["conditioning"] = "surface"
        self.assertEqual(realize(c, root)["output"]["tone"], "T")
        c["tone_rules"][0]["initial_class"] = ["n"]
        c["tone_rules"][0]["final_class"] = ["s"]
        self.assertEqual(realize(c, root)["output"]["tone"], "H")

    def test_unknown_root_tone_is_not_filled_in(self):
        d = affix_example()
        root = d["pool"][0]
        root["tone"] = None
        self.assertIsNone(realize(d["analyses"][0]["cells"][0], root)["output"]["tone"])

    def test_missing_tone_ignores_tone_while_empty_segments_still_constrain(self):
        d = affix_example()
        for c in d["analyses"][0]["cells"]:
            c["expected"]["tone"] = None
        self.assertEqual(sum(h["accepted"] for h in paradigm(d)["histories"]), 2)
        d["analyses"][0]["cells"][0]["expected"]["segments"] = []
        self.assertFalse(any(h["accepted"] for h in paradigm(d)["histories"]))
        d["analyses"][0]["cells"][0]["expected"] = None
        self.assertTrue(all(h["accepted"] for h in paradigm(d)["histories"]))

    def test_sequential_tone_rules_feed_only_in_declared_order(self):
        d = affix_example()
        c = d["analyses"][0]["cells"][0]
        r = deepcopy(c["tone_rules"][0])
        r.update(id="second", from_tone="L", to_tone="H")
        c["tone_rules"].append(r)
        self.assertEqual(realize(c, d["pool"][0])["output"]["tone"], "H")
        c["tone_rules"].reverse()
        self.assertEqual(realize(c, d["pool"][0])["output"]["tone"], "L")


class ChronologyTests(unittest.TestCase):
    def test_all_permutations_and_transitive_constraints(self):
        r = dict(
            schema_version="1.0.0", id="order", rule_ids=["a", "b", "c"], constraints=[]
        )
        self.assertEqual(len(chronology(r)["orders"]), 6)
        r["constraints"] = [dict(earlier="a", later="b"), dict(earlier="b", later="c")]
        self.assertEqual(chronology(r)["orders"], [["a", "b", "c"]])
        r["constraints"].append(dict(earlier="c", later="a"))
        self.assertTrue(chronology(r)["cyclic"])

    def test_empty_rule_set_has_one_empty_order(self):
        r = chronology(dict(id="empty", rule_ids=[], constraints=[]))
        self.assertFalse(r["cyclic"])
        self.assertEqual(r["orders"], [[]])

    def test_cyclic_blocks_still_undergo_native_validation(self):
        request = chronology_example()
        request["constraints"] = [dict(earlier="grimm", later="grimm")]
        with patch("research.checked", return_value=dict(orders=[], cyclic=True)):
            with patch(
                "research.checked_forwards", side_effect=ValueError("bad rule")
            ) as forwards:
                with self.assertRaisesRegex(ValueError, "bad rule"):
                    explore_chronology(request)
                self.assertTrue(forwards.called)


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_every_registered_example_has_real_specification(self):
        for key in EXAMPLE_INFO:
            d = describe(dict(key=key))
            self.assertTrue(d["request"])
            self.assertEqual(d["kind"], EXAMPLE_INFO[key][0])

    def test_friendly_labels_preserve_source_identifiers(self):
        d = describe(dict(dataset="pie", case="set-21"))
        self.assertIn("dog", d["title"].lower())
        self.assertEqual(d["axes"][0]["id"], "iecor-form-81-31-1")
        self.assertEqual(d["axes"][0]["label"], "Tocharian A")
        self.assertEqual(d["hypotheses"][0]["id"], "identity")

    def test_bounds_change_search_space_without_mutating_models(self):
        request = describe(dict(key="voice"))["request"]
        original = deepcopy(request)
        narrowed = constrained_bounds(
            request, dict(proto_inventory=["p"], max_length=3), ["N-anticausative"]
        )
        self.assertEqual(request, original)
        self.assertEqual(narrowed["analyses"], original["analyses"])
        self.assertEqual(narrowed["proto_inventory"], ["p"])
        self.assertEqual(narrowed["max_length"], 3)

    def test_unsupported_or_excessive_bounds_are_errors(self):
        request = describe(dict(key="voice"))["request"]
        for inventory, length in [
            ([], 1),
            (["x"], 1),
            (["p", "p"], 1),
            (["p"], True),
            (["p"], -1),
            (["p"], 17),
            (["p", "b"], 10),
        ]:
            with self.assertRaises(ValueError):
                constrained_bounds(
                    request,
                    dict(proto_inventory=inventory, max_length=length),
                    ["N-anticausative"],
                )
        with self.assertRaisesRegex(ValueError, "only to bounded"):
            run_request(dict(kind="paradigm", key="tones", bounds={}))

    def test_original_theme_assets_are_pinned_and_served(self):
        from verify_theme import verify

        manifest = verify()
        self.assertEqual(
            manifest["repository"], "https://github.com/zengrf/kiwari-slides"
        )
        for path in ["slides.css", "materials.css", "lib/fonts/font-0.ttf"]:
            with urlopen(self.url + "/vendor/kiwari/" + path) as response:
                self.assertEqual(
                    response.read(), (ROOT / "web/vendor/kiwari" / path).read_bytes()
                )

    def test_empty_hypothesis_selection_and_unknown_fields_fail(self):
        for body in [
            dict(kind="paradigm", key="tones", hypotheses=[]),
            dict(kind="paradigm", key="tones", surprise=True),
        ]:
            with self.assertRaises(ValueError):
                run_request(body)

    def test_import_preserves_strict_duplicate_key_and_constant_rejection(self):
        for text in ['{"x":1,"x":2}', '{"value":NaN}']:
            with self.assertRaises(ValueError):
                strict_json(text.encode())
            req = Request(
                self.url + "/api/import",
                data=encoded(dict(text=text)),
                headers={"Content-Type": "application/json"},
            )
            with self.assertRaises(HTTPError) as caught:
                urlopen(req)
            self.assertEqual(caught.exception.code, 400)

    def test_static_page_and_origin_restriction(self):
        with urlopen(self.url) as result:
            self.assertIn(b"Comparative reconstruction", result.read())
            self.assertIn(
                "frame-ancestors 'none'", result.headers["Content-Security-Policy"]
            )
        for headers in [
            {"Host": "hostile.example"},
            {"Origin": "https://hostile.example"},
        ]:
            with self.assertRaises(HTTPError) as caught:
                urlopen(Request(self.url + "/api/catalogue", headers=headers))
            self.assertEqual(caught.exception.code, 403)

    def test_only_public_assets_are_served(self):
        for path in [
            "/../.git/config",
            "/%2e%2e/.git/config",
            "/sources/../downloads/ringe2022.pdf",
            "/library/downloads/ringe2022.pdf",
        ]:
            with self.assertRaises(HTTPError) as caught:
                urlopen(self.url + path)
            self.assertIn(caught.exception.code, [400, 404])

    def test_source_pagination_matches_retained_rows(self):
        page1 = browse(dict(dataset="hillburmish", limit="2"))
        page2 = browse(dict(dataset="hillburmish", limit="2", offset="2"))
        self.assertEqual(page1["total"], 4032)
        self.assertTrue(page1["has_more"])
        self.assertFalse(
            {r["id"] for r in page1["records"]} & {r["id"] for r in page2["records"]}
        )
        self.assertIn("source_row", page1["records"][0])


if __name__ == "__main__":
    unittest.main()
