"""Failures that would inflate M5's coverage, leak held-out data or fake review."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from build_pie_corpus import DEST,digest
from build_pie_experiment import fit_correspondences,proto_tokens
from review_pie import assess
from verify_m5 import check_leakage,reference,verify_execution


class PieEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus=json.loads((DEST/"corpus.json").read_text())
        cls.design=json.loads((DEST/"experiment.json").read_text())

    def test_unresolved_proto_symbols_are_not_guessed(self):
        for form in ["*Hneh₃-mn̥","*kʷ(e)tu̯r̥-","?*delh₁-","*k⁽ʷ⁾sep-"]:
            self.assertIsNone(proto_tokens(form),form)
        self.assertEqual(proto_tokens("*du̯o-, *du̯i-"),[["d","w","o"],["d","w","i"]])

    def test_held_out_transcriptions_do_not_fit_the_model(self):
        mutated=deepcopy(self.corpus["sets"])
        for s in mutated:
            if s["split"]!="train":
                for r in s["records"]:r["normalization"]["tokens"]=["arbitrary-held-out-transcription"]
        self.assertEqual(fit_correspondences(mutated),fit_correspondences(self.corpus["sets"]))

    def test_injected_test_training_pair_fails(self):
        d=deepcopy(self.design);s=next(s for s in self.corpus["sets"] if s["split"]=="test")
        d["training_examples"].append(dict(set_id=s["id"],family_id=s["family_id"],record_id=s["records"][0]["id"]))
        d["training_sha256"]=digest(d["training_examples"])
        with self.assertRaises(AssertionError):check_leakage(self.corpus,d)

    def test_related_roots_cannot_cross_splits(self):
        c=deepcopy(self.corpus);a=c["sets"][0];b=next(s for s in c["sets"] if s["family_id"]!=a["family_id"])
        b["family_id"]=a["family_id"];b["split"]="test" if a["split"]!="test" else "train"
        with self.assertRaises(AssertionError):check_leakage(c,self.design)

    def test_unsupported_record_cannot_disappear(self):
        d=deepcopy(self.design);d["outcomes"]=[r for r in d["outcomes"] if r["status"]!="unsupported"]
        with self.assertRaises(AssertionError):check_leakage(self.corpus,d)

    def test_corrupt_certificate_fails_independent_comparison(self):
        req=json.loads((DEST/"diagnostic-input.json").read_text());req["forward"]=req["forward"][:1]
        expected=reference(req);expected["forward"][0]["steps"][0]["output"]=["invented"]
        with self.assertRaises(AssertionError):verify_execution(req,expected)

    def test_lost_inverse_candidate_fails(self):
        req=json.loads((DEST/"lexical-input.json").read_text());req["forward"]=[];req["inverse"]=req["inverse"][:1]
        q=req["inverse"][0];q["pool"]=[["a"],["e"]];q["reference"]=[["a"]]
        for b in q["branches"]:b.update(package_id="identity",expected=["a"])
        out=reference(req);self.assertEqual(out["inverse"][0]["candidates"],[["a"]])
        out["inverse"][0]["candidates"]=[]
        with self.assertRaises(AssertionError):verify_execution(req,out)


class PieReviewTests(unittest.TestCase):
    def synthetic(self):
        p=dict(core=[dict(id="core-example")],disputed=[dict(id="disputed-example")])
        r=dict(status="complete",packet_sha256=digest(p),reviewer=dict(type="human-family-specialist",name="Synthetic test identity",expertise="Synthetic PIE expertise field",independent_of_encoding=True),
               signed_at="2000-01-01",attestation="Synthetic test only; not a real review",global_checks_complete=True,decision="approve",
               entries=[dict(id=i,decision="approve",rationale="Synthetic boundary test",source_locators=["synthetic:1"]) for i in ["core-example","disputed-example"]])
        return p,r

    def test_absent_review_remains_pending(self):
        p,_=self.synthetic();self.assertFalse(assess(p,None)["passed"])

    def test_ai_review_cannot_supply_specialist_signoff(self):
        p,r=self.synthetic();r["reviewer"]["type"]="independent-ai-agent";self.assertFalse(assess(p,r)["passed"])

    def test_self_review_cannot_close_gate(self):
        p,r=self.synthetic();r["reviewer"]["independent_of_encoding"]=False;self.assertFalse(assess(p,r)["passed"])

    def test_stale_packet_cannot_close_gate(self):
        p,r=self.synthetic();p["new_disagreement"]="changed";self.assertFalse(assess(p,r)["passed"])

    def test_missing_disputed_review_cannot_close_gate(self):
        p,r=self.synthetic();r["entries"].pop();self.assertFalse(assess(p,r)["passed"])

    def test_unresolved_objection_blocks_linguistic_validation(self):
        p,r=self.synthetic();r["entries"][0]["decision"]="unresolved-objection";out=assess(p,r)
        self.assertFalse(out["passed"]);self.assertEqual(len(out["objections"]),1)

    def test_only_complete_synthetic_attestation_passes_contract(self):
        p,r=self.synthetic();self.assertTrue(assess(p,r)["passed"])


if __name__=="__main__":unittest.main()
