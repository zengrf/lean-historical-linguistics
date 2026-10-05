"""Boundary tests complementing the Lean fixture suite and real-source imports."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from pycldf import Wordlist

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from import_cldf import make_dossier, check_snapshot, TERMS
from review_m1 import assess
from verify_m1 import strict_json


class AdapterContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);cldf=self.root/"cldf";cldf.mkdir()
        ds=Wordlist.in_dir(cldf)
        ds.properties["dc:title"]="Synthetic adapter contract test"
        ds.add_component("LanguageTable");ds.add_component("ParameterTable")
        ds.add_columns("FormTable",{"name":"Value","propertyUrl":TERMS+"value","datatype":"string"},"Extra")
        mappings={"FormTable":{"ID":"Key","Language_ID":"Doc","Parameter_ID":"Concept","Value":"Verbatim","Form":"Display","Segments":"Phones"},
                  "LanguageTable":{"ID":"LKey","Name":"LLabel"},"ParameterTable":{"ID":"PKey","Name":"PLabel"}}
        for table, columns in mappings.items():
            for original, renamed in columns.items():ds.rename_column(table,original,renamed)
        ds.write(fname=cldf/"cldf-metadata.json",
                 FormTable=[{"Key":"word-1","Doc":"lang-1","Concept":"meaning-1","Verbatim":"a\u0301",
                             "Display":"á","Phones":["á"],"Extra":"opaque; comma, newline\nquote\""}],
                 LanguageTable=[{"LKey":"lang-1","LLabel":"Synthetic language"}],
                 ParameterTable=[{"PKey":"meaning-1","PLabel":"Synthetic meaning"}])
        self.lock={"id":"synthetic","repository":"https://example.org/synthetic","commit":"a"*40,"license":"MIT",
                   "files":[{"path":str(p.relative_to(self.root)),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size}
                            for p in sorted(cldf.glob("*")) if p.is_file()]}
        self.selection={"row_ids":["word-1"],"family":"Synthetic","proto_language_ids":[]}

    def test_property_urls_survive_renaming_and_preserve_opaque_values(self):
        d,report=make_dossier("synthetic",self.lock,self.selection,self.root)
        r=d["records"][0];origin=r["imported_from"]
        self.assertEqual(origin["id_column"],"Key")
        self.assertEqual(origin["original_column"],"Verbatim")
        self.assertEqual(r["readings"][0]["original"],"a\u0301")
        self.assertEqual(r["readings"][0]["normalized"],"á")
        self.assertEqual(next(c["value"] for c in origin["raw_columns"] if c["name"]=="Extra"),'opaque; comma, newline\nquote"')
        self.assertIn("Extra",report["form_columns_not_semantically_interpreted"])

    def test_unknown_selection_is_not_silently_skipped(self):
        self.selection["row_ids"].append("absent")
        with self.assertRaisesRegex(ValueError,"Selection"):
            make_dossier("synthetic",self.lock,self.selection,self.root)

    def test_duplicate_selection_is_rejected(self):
        self.selection["row_ids"]*=2
        with self.assertRaisesRegex(ValueError,"Selection"):
            make_dossier("synthetic",self.lock,self.selection,self.root)

    def test_changed_source_bytes_fail_before_import(self):
        p=self.root/"cldf/forms.csv";p.write_bytes(p.read_bytes()+b"\n")
        with self.assertRaisesRegex(ValueError,"hash mismatch"):
            make_dossier("synthetic",self.lock,self.selection,self.root)

    def test_manifest_cannot_escape_snapshot(self):
        self.lock["files"][0]["path"]="../outside"
        with self.assertRaisesRegex(ValueError,"escapes"):
            check_snapshot(self.root,self.lock)

    def test_unknown_proto_identity_is_not_guessed(self):
        self.selection["proto_language_ids"]=["absent"]
        with self.assertRaisesRegex(ValueError,"proto-language"):
            make_dossier("synthetic",self.lock,self.selection,self.root)

    def test_unpinned_file_is_rejected(self):
        (self.root/"cldf/unrecorded.csv").write_text("ID,Form\n1,pa\n")
        with self.assertRaisesRegex(ValueError,"file set"):
            check_snapshot(self.root,self.lock)

    def test_editorial_reading_flag_survives_reimport(self):
        self.selection["uncertainty_overrides"]={"word-1":"Independent transcription disagrees; preserve both reports"}
        d,report=make_dossier("synthetic",self.lock,self.selection,self.root)
        self.assertTrue(d["records"][0]["uncertain"])
        self.assertEqual(d["records"][0]["readings"][0]["original"],"a\u0301")
        self.assertIn("word-1",report["editorial_uncertainty_flags"])

    def test_editorial_flag_cannot_reference_unselected_row(self):
        self.selection["uncertainty_overrides"]={"absent":"Unresolved reading"}
        with self.assertRaisesRegex(ValueError,"uncertainty overrides"):
            make_dossier("synthetic",self.lock,self.selection,self.root)


class ReviewGateTests(unittest.TestCase):
    def setUp(self):
        self.expected={"toy": {"readings":[{"original":"a\u0301"}],"uncertain":False}}
        self.packet={"minimum_records":1,"items":[{"record_id":"toy"}]}
        self.response={"reviewer_id":"synthetic-test-person","independent_of_encoding":True,
                       "packet_sha256":hashlib.sha256(json.dumps(self.packet,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
                       "entries":[{"record_id":"toy","original":"a\u0301","resolution":None}]}

    def test_absent_review_stays_pending(self):
        self.assertEqual(assess(self.packet,self.expected,None)["status"],"pending")

    def test_valid_synthetic_review_passes(self):
        self.assertEqual(assess(self.packet,self.expected,self.response)["status"],"passed")

    def test_ai_review_provenance_is_explicit_and_bound_to_response(self):
        self.response["reviewer_id"]="synthetic-test-agent"
        self.response["reviewer_type"]="independent_ai_agent"
        r=assess(self.packet,self.expected,self.response)
        self.assertEqual(r["status"],"passed")
        self.assertEqual(r["reviewer_type"],"independent_ai_agent")
        self.assertIs(r["independent_of_encoding"],True)
        self.response["independent_of_encoding"]=False
        changed=assess(self.packet,self.expected,self.response)
        self.assertEqual(changed["status"],"pending")
        self.assertNotEqual(r["response_sha256"],changed["response_sha256"])

    def test_self_review_does_not_close_the_gate(self):
        self.response["reviewer_id"]="assistant:codex"
        self.assertEqual(assess(self.packet,self.expected,self.response)["status"],"pending")

    def test_non_independent_response_does_not_close_gate(self):
        self.response["independent_of_encoding"]=False
        self.assertEqual(assess(self.packet,self.expected,self.response)["status"],"pending")

    def test_visually_equal_unicode_does_not_hide_transcription_change(self):
        self.response["entries"][0]["original"]="á"
        self.assertEqual(assess(self.packet,self.expected,self.response)["status"],"pending")

    def test_stale_packet_is_rejected(self):
        self.response["packet_sha256"]="0"*64
        self.assertEqual(assess(self.packet,self.expected,self.response)["status"],"pending")

    def test_duplicate_entries_do_not_inflate_coverage(self):
        self.response["entries"]*=2
        r=assess(self.packet,self.expected,self.response)
        self.assertEqual(r["status"],"pending");self.assertEqual(r["reviewed_records"],1)

    def test_unflagged_discrepancy_cannot_be_called_resolved(self):
        self.response["entries"][0].update(original="x",resolution={"status":"flagged","reason":"disagrees"})
        self.assertEqual(assess(self.packet,self.expected,self.response)["status"],"pending")


class StrictJsonTests(unittest.TestCase):
    def test_nested_duplicate(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            strict_json('{"a":{"b":1,"b":2}}')

    def test_nonstandard_number(self):
        with self.assertRaisesRegex(ValueError,"Non-JSON"):
            strict_json('{"a":NaN}')


if __name__=="__main__":unittest.main()
