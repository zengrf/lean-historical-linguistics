"""M6 failures that would alter source scope, evaluation or joint analyses."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from build_kuki_corpus import DEST
from build_m6_experiment import parse_form,match_cells,lexical,joint_analysis
from build_pie_corpus import digest
from verify_m6 import check_leakage,verify_execution
from verify_m5 import reference
from reference_reconstruction import evaluate
from review_pie import assess


class SinoTibetanContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus=json.loads((DEST/"corpus.json").read_text())
        cls.design=json.loads((DEST/"experiment.json").read_text())

    def test_tone_and_original_remain_available(self):
        raw="ba ́an";p=parse_form(raw,"vb-hakha-lai")
        self.assertEqual(p["original"],raw)
        self.assertEqual(p["cells"],{"unmarked":["b","a","a","n"]})
        self.assertEqual(p["tone_marks"][0]["marks"][0]["mark"],"́")

    def test_glottal_question_mark_has_source_scope(self):
        self.assertEqual(parse_form("bel?3","vb-tedim")["cells"],{"unmarked":["b","e","l","ʔ"]})
        self.assertIsNone(parse_form("bel?3","vb-mizo")["cells"])

    def test_allofams_and_optional_segments_are_not_chosen(self):
        for s in ["*ɗeeŋ ⪤ *ɗeek","*thu(u)r","*(p)raŋ","*ɓan-hlaa"]:
            self.assertIsNone(parse_form(s)["cells"],s)

    def test_unlabelled_reflex_does_not_choose_a_stem(self):
        root=parse_form("*ɓeel-I, *ɓelʔ-II")
        pairs,why=match_cells(root,parse_form("beel","vb-mizo"))
        self.assertEqual(pairs,[]);self.assertEqual(why,"unmatched-stem-cell-labels")

    def test_stem_labels_and_invariance_are_preserved(self):
        root=parse_form("*ɓeel-I, *ɓelʔ-II")
        pairs,why=match_cells(root,parse_form("beel-I, belh-II","vb-mizo"))
        self.assertIsNone(why);self.assertEqual([p[0] for p in pairs],["I","II"])
        inv,why=match_cells(root,parse_form("belʔ-INV","vb-hakha-lai"))
        self.assertIsNone(why);self.assertEqual(len(inv),2);self.assertEqual(inv[0][2],inv[1][2])

    def test_test_reflexes_do_not_fit_mappings(self):
        c=deepcopy(self.corpus)
        for s in c["sets"]:
            if s["split"]!="train":
                for r in s["records"]:r["source_form"]="arbitrary-unsupported-held-out-form"
        _,design=lexical(c)
        self.assertEqual(design["models"],self.design["models"])
        self.assertEqual(design["training_examples"],self.design["training_examples"])

    def test_training_injection_fails(self):
        d=deepcopy(self.design);s=next(s for s in self.corpus["sets"] if s["split"]=="test")
        d["training_examples"].append(dict(set_id=s["id"],record_id=s["records"][0]["id"],family_id=s["family_id"]))
        d["training_sha256"]=digest(d["training_examples"])
        with self.assertRaises(AssertionError):check_leakage(self.corpus,d)

    def test_dropped_unsupported_row_fails(self):
        d=deepcopy(self.design);d["outcomes"]=[r for r in d["outcomes"] if r["failure_category"] is None]
        with self.assertRaises(AssertionError):check_leakage(self.corpus,d)

    def test_family_split_leakage_fails(self):
        c=deepcopy(self.corpus);a=c["sets"][0];b=next(s for s in c["sets"] if s["family_id"]!=a["family_id"])
        b.update(family_id=a["family_id"],split="test" if a["split"]!="test" else "train")
        with self.assertRaises(AssertionError):check_leakage(c,self.design)

    def test_whole_paradigms_remain_distinct_candidates(self):
        r=evaluate(joint_analysis())
        self.assertEqual([(c["analysis_id"],c["protoform"]) for c in r["candidates"]],[("N-anticausative",["p"]),("s-devoicing",["b"])])
        self.assertEqual(r["examined"],6)

    def test_omitted_merger_candidate_is_detected(self):
        req=json.loads((DEST/"diagnostic-input.json").read_text());req["batch"]["forward"]=[]
        result=dict(scope_valid=True,result=reference(req["batch"]))
        self.assertEqual(result["result"]["inverse"][0]["candidates"],[["ndz"],["dz"]])
        result["result"]["inverse"][0]["candidates"].pop()
        with self.assertRaises(AssertionError):verify_execution(req,result)

    def test_wrong_intermediate_certificate_is_detected(self):
        req=json.loads((DEST/"diagnostic-input.json").read_text())
        req["batch"]["forward"]=[j for j in req["batch"]["forward"] if j["id"]=="wa-horn--early-wa-late-fusion"]
        result=dict(scope_valid=True,result=reference(req["batch"]))
        result["result"]["forward"][0]["steps"][0]["output"]=["r","o"]
        with self.assertRaises(AssertionError):verify_execution(req,result)

    def test_review_absence_cannot_pass(self):
        self.assertFalse(assess(dict(core=[],disputed=[]),None)["passed"])


if __name__=="__main__":unittest.main()
