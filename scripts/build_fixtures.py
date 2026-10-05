"""Build named representation and adversarial fixtures; none are historical data."""
import copy
import json
import unicodedata
from pathlib import Path
from import_cldf import dump

ROOT = Path(__file__).resolve().parents[1]


def reading(value="pa", rid="reading-1"):
    return {"id": rid, "original": value, "normalized": value,
            "cells": [{"kind": "segment", "value": value}],
            "normalization": [{"method_id": "identity", "method_version": "1", "input": value, "output": value, "reason": "Exact synthetic source value"}], "choices": []}


def base(name):
    return {"schema_version": "1.0.0", "id": name,
            "description": "Synthetic M1 fixture: " + name + "; not a real attestation or reconstruction",
            "sources": [{"id": "synthetic-source", "title": "Constructed representation fixture", "url": "urn:fixture:" + name,
                         "version": "1", "license": "MIT", "kind": "synthetic", "sha256": None}],
            "doculects": [{"id": "fixture-language", "name": "Synthetic variety", "family": "Synthetic", "stage": "Toy stage 1", "kind": "attested", "date_range": None}],
            "meanings": [{"id": "meaning-1", "label": "synthetic meaning"}], "analyses": [],
            "normalization_methods": [{"id": "identity", "version": "1", "description": "Preserve the source exactly"},
                                     {"id": "editorial", "version": "1", "description": "Explicit synthetic editorial change, not a sound law"},
                                     {"id": "unicode-nfc", "version": unicodedata.unidata_version, "description": "Unicode NFC; checked independently by Python"}],
            "choice_groups": [],
            "records": [{"id": name + ":record", "doculect_id": "fixture-language", "meaning_ids": ["meaning-1"],
                         "representation": "phonetic", "attestation": "attested", "evidence_state": "present",
                         "analysis_id": None, "proto_node_id": None,
                         "citations": [{"source_id": "synthetic-source", "locator": "fixture definition, record 1"}],
                         "readings": [reading()], "uncertain": False, "uncertainty_note": None, "imported_from": None}]}


def set_value(d, value, cells=None):
    d["records"][0]["readings"] = [reading(value)]
    if cells is not None: d["records"][0]["readings"][0]["cells"] = cells


def change(d, original, normalized, method="editorial", version="1"):
    set_value(d, original)
    r = d["records"][0]["readings"][0]
    r["normalized"] = normalized
    r["cells"] = [{"kind": "segment", "value": normalized}]
    r["normalization"] = [{"method_id": method, "method_version": version, "input": original,
                           "output": normalized, "reason": "Declared representation change for this synthetic fixture"}]


def proto(d):
    d["doculects"][0]["kind"] = "proto"
    d["analyses"] = [{"id": "analysis-1", "description": "Synthetic reconstruction hypothesis", "source_ids": ["synthetic-source"], "proto_node_id": "proto-1"}]
    d["records"][0].update(attestation="reconstructed", analysis_id="analysis-1", proto_node_id="proto-1")


def choice(d):
    d["choice_groups"] = [{"id": "joint", "options": ["a", "b"], "description": "Coindexed whole-form alternatives"}]
    r = d["records"][0]
    r["readings"] = [reading("pat", "a"), reading("pid", "b")]
    for rd in r["readings"]: rd["choices"] = [{"group_id": "joint", "option_id": rd["id"]}]


def imported(d):
    d["sources"][0]["kind"] = "dataset"
    d["records"][0]["imported_from"] = {"dataset_id": "synthetic-source", "table": "renamed.csv", "row_id": "upstream-1",
        "id_column": "Key", "original_column": "Verbatim", "raw_columns": [{"name": "Key", "value": "upstream-1"}, {"name": "Verbatim", "value": "pa"}, {"name": "Extra", "value": "kept"}]}


def main():
    valid = []
    def add(name, edit=lambda d: None):
        d = base(name); edit(d); valid.append(d); return d
    add("identity")
    for name, value in [("combining-tone", "a\u0301"), ("superscript-tone", "ma⁵⁵"), ("decomposed-voiceless", "n\u0325a"),
                        ("tibetan-script", "བོད"), ("chinese-script", "水"), ("supplementary-unicode", "𐀀"),
                        ("stress", "ˈpa"), ("aspiration", "pʰa"), ("length", "aː"), ("diphthong-token", "ai"),
                        ("punctuation", "p'a"), ("escaped-quote", 'p"a'), ("stacked-diacritics", "a\u0303\u0301"),
                        ("zero-width-joiner", "क्‍ष"), ("right-to-left", "ب")]:
        add(name, lambda d, v=value: set_value(d, v))
    add("unicode-nfc", lambda d: change(d, "a\u0301", "á", "unicode-nfc", unicodedata.unidata_version))
    add("boundary", lambda d: set_value(d, "ka+pa", [{"kind": "segment", "value": "ka"}, {"kind": "boundary", "value": "+"}, {"kind": "segment", "value": "pa"}]))
    add("alignment-gap", lambda d: set_value(d, "pa", [{"kind": "segment", "value": "p"}, {"kind": "gap", "value": None}, {"kind": "segment", "value": "a"}]))
    def missing(d):
        set_value(d, "", [{"kind": "missing", "value": None}]);d["records"][0]["evidence_state"] = "missing"
    add("missing", missing)
    def unknown(d):
        set_value(d, "?", [{"kind": "unknown", "value": "?"}]);d["records"][0].update(evidence_state="unknown", uncertain=True, uncertainty_note="Unresolved synthetic glyph")
    add("unknown", unknown)
    def partial(d):
        set_value(d, "p?", [{"kind": "segment", "value": "p"}, {"kind": "unknown", "value": "?"}]);d["records"][0].update(uncertain=True, uncertainty_note="Second synthetic glyph unresolved")
    add("partial-unknown", partial)
    add("reconstructed", proto)
    def meanings(d):
        d["meanings"].append({"id": "meaning-2", "label": "second meaning"});d["records"][0]["meaning_ids"].append("meaning-2")
    add("multiple-meanings", meanings)
    add("multiple-variants", lambda d: d["records"][0]["readings"].append(reading("ba", "reading-2")))
    add("joint-alternatives", choice)
    def coindex(d):
        choice(d); other=copy.deepcopy(d["records"][0]);other["id"] += "-linked";d["records"].append(other)
    add("coindexed-records", coindex)
    def citations(d):
        s=copy.deepcopy(d["sources"][0]);s["id"]="second-source";d["sources"].append(s)
        d["records"][0]["citations"].append({"source_id":"second-source","locator":"independent synthetic witness"})
    add("multiple-sources", citations)
    add("dated-bce", lambda d: d["doculects"][0].update(date_range={"earliest":-100,"latest":-1,"convention":"astronomical-year"}))
    add("dated-ce", lambda d: d["doculects"][0].update(date_range={"earliest":100,"latest":200,"convention":"astronomical-year"}))
    add("whitespace-preserved", lambda d: change(d, " pa ", "pa"))
    add("case-preserved", lambda d: change(d, "PA", "pa"))
    add("newline-preserved", lambda d: change(d, "p\na", "pa"))
    def multistep(d):
        change(d, "A\u0301", "á");r=d["records"][0]["readings"][0]
        r["normalization"][0]["output"]="Á"
        r["normalization"].append({"method_id":"editorial","method_version":"1","input":"Á","output":"á","reason":"Explicit case change"})
    add("multiple-normalizations", multistep)
    add("renamed-import-columns", imported)
    add("orthographic", lambda d: d["records"][0].update(representation="orthographic"))
    add("phonemic", lambda d: d["records"][0].update(representation="phonemic"))
    add("source-sha256", lambda d: d["sources"][0].update(sha256="a"*64))
    by = {d["id"]: d for d in valid}
    manifest = []
    for d in valid:
        path = "valid/" + d["id"] + ".json";dump(ROOT/"data/fixtures"/path,d)
        manifest.append({"path":path,"accept":True,"reason":d["id"]})
    def bad(name, code, edit, template="identity"):
        d=copy.deepcopy(by[template]);edit(d)
        path="invalid/"+name+".json";dump(ROOT/"data/fixtures"/path,d)
        manifest.append({"path":path,"accept":False,"code":code,"reason":name})
    bad("duplicate-record", "DUPLICATE_ID", lambda d: d["records"].append(copy.deepcopy(d["records"][0])))
    bad("duplicate-source", "DUPLICATE_ID", lambda d: d["sources"].append(copy.deepcopy(d["sources"][0])))
    bad("broken-source", "BROKEN_SOURCE", lambda d: d["records"][0]["citations"][0].update(source_id="absent"))
    bad("missing-source", "MISSING_SOURCE", lambda d: d["records"][0].update(citations=[]))
    bad("empty-locator", "SOURCE_LOCATOR", lambda d: d["records"][0]["citations"][0].update(locator=""))
    bad("broken-doculect", "BROKEN_DOCULECT", lambda d: d["records"][0].update(doculect_id="absent"))
    bad("broken-meaning", "BROKEN_MEANING", lambda d: d["records"][0].update(meaning_ids=["absent"]))
    bad("no-normalization", "NORMALIZATION_MISSING", lambda d: d["records"][0]["readings"][0].update(normalization=[]))
    bad("broken-chain", "NORMALIZATION_CHAIN", lambda d: d["records"][0]["readings"][0]["normalization"][0].update(input="wrong"))
    bad("unknown-method", "NORMALIZATION_METHOD", lambda d: d["records"][0]["readings"][0]["normalization"][0].update(method_id="absent"))
    bad("wrong-method-version", "NORMALIZATION_METHOD", lambda d: d["records"][0]["readings"][0]["normalization"][0].update(method_version="2"))
    bad("identity-change", "IDENTITY_CHANGED", lambda d: change(d,"pa","ba","identity"))
    bad("empty-original", "PRESENT_CONTENT", lambda d: set_value(d,""))
    bad("gap-as-missing", "MISSING_CONTENT", lambda d: d["records"][0]["readings"][0].update(cells=[{"kind":"gap","value":None}]),"missing")
    bad("unknown-unflagged", "UNKNOWN_UNFLAGGED", lambda d: d["records"][0].update(uncertain=False,uncertainty_note=None),"unknown")
    bad("unknown-as-segment", "UNKNOWN_CELL", lambda d: d["records"][0]["readings"][0].update(cells=[{"kind":"segment","value":"?"}]),"unknown")
    bad("cell-output-mismatch", "CELL_RENDER", lambda d: d["records"][0]["readings"][0]["cells"][0].update(value="wrong"))
    bad("reconstruction-without-analysis", "RECONSTRUCTION_ANALYSIS", lambda d: d["records"][0].update(analysis_id=None),"reconstructed")
    bad("wrong-proto-node", "PROTO_NODE", lambda d: d["records"][0].update(proto_node_id="wrong"),"reconstructed")
    bad("attested-proto", "ATTESTATION_NODE", lambda d: d["doculects"][0].update(kind="proto"))
    bad("attested-analysis", "ATTESTED_ANALYSIS", lambda d: d["records"][0].update(analysis_id="pretend"))
    bad("duplicate-reading", "DUPLICATE_ID", lambda d: d["records"][0]["readings"].append(copy.deepcopy(d["records"][0]["readings"][0])))
    bad("broken-choice", "BROKEN_CHOICE", lambda d: d["records"][0]["readings"][0]["choices"][0].update(option_id="absent"),"joint-alternatives")
    bad("conflicting-binding", "CHOICE_CONFLICT", lambda d: d["records"][0]["readings"][0]["choices"].append({"group_id":"joint","option_id":"b"}),"joint-alternatives")
    bad("duplicate-choice-option", "CHOICE_GROUP", lambda d: d["choice_groups"][0].update(options=["a","a"]),"joint-alternatives")
    bad("inverted-date", "DATE_RANGE", lambda d: d["doculects"][0]["date_range"].update(earliest=1,latest=-1),"dated-bce")
    bad("invalid-status", "ATTESTATION", lambda d: d["records"][0].update(attestation="probably"))
    bad("invalid-representation", "REPRESENTATION", lambda d: d["records"][0].update(representation="unspecified"))
    bad("uncertain-without-note", "UNCERTAINTY_NOTE", lambda d: d["records"][0].update(uncertain=True))
    bad("changed-import-row", "IMPORT_ROW_ID", lambda d: d["records"][0]["imported_from"].update(row_id="wrong"),"renamed-import-columns")
    bad("changed-import-original", "IMPORT_ORIGINAL", lambda d: change(d,"wrong","pa"),"renamed-import-columns")
    bad("duplicate-raw-column", "IMPORT_ORIGIN", lambda d: d["records"][0]["imported_from"]["raw_columns"].append({"name":"Key","value":"upstream-1"}),"renamed-import-columns")
    bad("wrong-version", "SCHEMA_VERSION", lambda d: d.update(schema_version="2.0.0"))
    bad("extra-field", "JSON_SHAPE", lambda d: d.update(secret_field="ignored?"))
    bad("nested-extra-field", "JSON_SHAPE", lambda d: d["records"][0]["readings"][0].update(confidence=0.9))
    bad("wrong-type", "JSON_SHAPE", lambda d: d["records"][0].update(uncertain="false"))
    bad("omitted-null", "JSON_SHAPE", lambda d: d["records"][0].pop("analysis_id"))
    bad("gap-with-string", "JSON_SHAPE", lambda d: d["records"][0]["readings"][0].update(cells=[{"kind":"gap","value":"-"}]))
    bad("invalid-id", "INVALID_ID", lambda d: d["records"][0].update(id="../outside"))
    text=json.dumps(base("raw-invalid"),ensure_ascii=False)
    for name,code,payload in [
        ("duplicate-json-key","DUPLICATE_JSON_KEY",text.replace('"schema_version":', '"id":"shadow", "schema_version":',1).encode()),
        ("escaped-duplicate-key","DUPLICATE_JSON_KEY",text.replace('"schema_version":', '"\\u0069d":"shadow", "schema_version":',1).encode()),
        ("malformed-json","JSON_SYNTAX",b'{"broken":'),
        ("invalid-utf8","UTF8",text.encode()+b'\xff'),
        ("surrogate-escape","UNICODE_ESCAPE",text.replace('"pa"','"\\ud800\\udc00"').encode()),
    ]:
        path="invalid/"+name+".json";(ROOT/"data/fixtures"/path).write_bytes(payload)
        manifest.append({"path":path,"accept":False,"code":code,"reason":name})
    dump(ROOT/"data/fixtures/manifest.json",manifest)
    print(f"Built {len(valid)} valid and {len(manifest)-len(valid)} adversarial fixtures")


if __name__ == "__main__": main()
