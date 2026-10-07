"""Independent small-domain checks of the untrusted solver and its input adapter."""

from copy import deepcopy
from itertools import product
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_m7_fixtures import (
    merger,
    deletion,
    contextual,
    conflict,
    request,
    model,
    entry,
    rule,
)
from lexicon import constrain, read_tsv, to_tsv
from m7_solver import (
    solve,
    baseline,
    graph_counts,
    unrank,
    decimal,
    integer,
    IncompleteSearch,
)


def words(forest, model_id, entry_id):
    m = next(m for m in forest["models"] if m["analysis_id"] == model_id)
    b = next(b for b in m["bindings"] if b["entry_id"] == entry_id)
    ns = m["graphs"][b["graph"]]["nodes"]
    cs = graph_counts(ns)
    return [unrank(ns, cs, b["root"], i) for i in range(cs[b["root"]])]


class InverseSolverTests(unittest.TestCase):
    def agree(self, spec, **kwargs):
        f = solve(spec, **kwargs)
        for m in spec["analyses"]:
            oracle = baseline(spec, m)
            for e in spec["entries"]:
                found = words(f, m["id"], e["id"])
                self.assertEqual(len(found), len({tuple(w) for w in found}))
                self.assertEqual(sorted(found), sorted(oracle[e["id"]]))
        return f

    def test_mergers(self):
        self.agree(merger())

    def test_deletion_including_zero_output_and_missing_word(self):
        self.agree(deletion())

    def test_reference_context(self):
        f = self.agree(contextual())
        self.assertEqual(f["models"][0]["mode"], "pruned")

    def test_compiler_and_reference_exact_agreement(self):
        s = deletion()
        fast, slow = self.agree(s), self.agree(s, force_reference=True)
        for e in s["entries"]:
            self.assertEqual(words(fast, "loss", e["id"]), words(slow, "loss", e["id"]))

    def test_whole_model_conflict_is_not_per_word_union(self):
        s = conflict()
        f = self.agree(s)
        pools = [
            [words(f, m["id"], e["id"]) for e in s["entries"]] for m in s["analyses"]
        ]
        self.assertTrue(all(any(not p for p in ps) for ps in pools))
        self.assertTrue(all(any(ps[i] for ps in pools) for i in range(2)))

    def test_overlapping_templates_do_not_duplicate_words(self):
        s = merger()
        s["phonotactics"] = [[["p", "b"], ["a"]], [["p"], ["a"]]]
        self.agree(s)

    def test_no_templates_permits_no_word(self):
        s = deletion()
        s["phonotactics"] = []
        f = self.agree(s)
        self.assertEqual(words(f, "loss", "empty"), [])

    def test_zero_length_with_empty_template(self):
        s = deletion()
        s["phonotactics"] = [[]]
        s["max_length"] = 0
        f = self.agree(s)
        self.assertEqual(words(f, "loss", "empty"), [[]])

    def test_atom_inventory_is_not_character_inventory(self):
        s = request(
            "atomic",
            ["kʷ", "a"],
            ["A"],
            [model("identity", ["A"], ["kʷ", "a"], [[]])],
            [entry("one", ["A"], [["kʷ", "a"]])],
            maximum=2,
        )
        self.assertEqual(words(self.agree(s), "identity", "one"), [["kʷ", "a"]])

    def test_reference_graph_sharing_respects_observation_tuple(self):
        s = contextual()
        twin = deepcopy(s["entries"][0])
        twin["id"] = "twin"
        s["entries"].append(twin)
        other = deepcopy(twin)
        other["id"] = "other"
        other["reflexes"][0]["form"] = None
        s["entries"].append(other)
        f = self.agree(s)
        self.assertEqual(len(f["models"][0]["graphs"]), 2)

    def test_exhausted_budgets_are_incomplete(self):
        for kwargs in [dict(node_budget=1), dict(time_limit=0)]:
            with self.assertRaises(IncompleteSearch):
                solve(merger(), **kwargs)

    def test_unknown_cell_is_one_segment_not_any_word(self):
        s = contextual()
        s["entries"][0]["reflexes"] = [
            dict(r, form=[None]) for r in s["entries"][0]["reflexes"]
        ]
        self.assertTrue(
            all(len(w) == 1 for w in words(self.agree(s), "intervocalic", "one"))
        )

    def test_arbitrary_precision_decimal_counts(self):
        value = 2**20000
        self.assertEqual(integer(decimal(value)), value)
        for bad in ["", "-1", "1.0", "١", "1e2", 12]:
            with self.assertRaises(ValueError):
                integer(bad)

    def test_unrank_bounds(self):
        f = solve(merger())
        m = f["models"][0]
        ns = m["graphs"][0]["nodes"]
        cs = graph_counts(ns)
        root = m["bindings"][0]["root"]
        for rank in [-1, cs[root]]:
            with self.assertRaises(ValueError):
                unrank(ns, cs, root, rank)

    def test_tsv_round_trip_missing_unknown_empty(self):
        s = deletion()
        s["entries"][0]["meaning"] = 'Meaning with\ta tab and "quote"'
        parsed = read_tsv(to_tsv(s), s["languages"])
        for a, b in zip(parsed, s["entries"]):
            self.assertEqual(a["meaning"], b["meaning"])
            self.assertEqual(
                [r["form"] for r in a["reflexes"]], [r["form"] for r in b["reflexes"]]
            )

    def test_invalid_tsv_does_not_silently_shift_columns(self):
        langs = merger()["languages"]
        for text in [
            "id\tmeaning\tB\tA\n",
            "id\tmeaning\tA\tB\nx\tx\tp\n",
            "id\tmeaning\tA\tB\nx\tx\t∅ a\tb\n",
        ]:
            with self.assertRaises(ValueError):
                read_tsv(text, langs)

    def test_constraint_selection_preserves_source_request(self):
        s = merger()
        old = deepcopy(s)
        selected = constrain(s, ["mergers"], [])
        self.assertEqual(s, old)
        self.assertEqual(len(selected["analyses"]), 1)
        self.assertTrue(
            all(r["form"] is None for e in selected["entries"] for r in e["reflexes"])
        )
        with self.assertRaises(ValueError):
            constrain(s, languages=["unknown"])


if __name__ == "__main__":
    unittest.main()
