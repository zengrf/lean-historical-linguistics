"""Run M1's executable representation, adversarial, source and round-trip checks.

This verifies engineering artifacts. Independent review is reported by the
separate review gate and is never inferred from passing software checks.
"""
import argparse
import concurrent.futures
import hashlib
import json
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from jsonschema import Draft202012Validator
from import_cldf import ROOT, dump, make_dossier


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError("Duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError("Non-JSON number: " + x)))


def run_checker(binary, path, roundtrip=None):
    cmd = [str(binary), str(path), "--strict"]
    if roundtrip: cmd += ["--roundtrip", str(roundtrip)]
    run = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if run.returncode not in (0, 1):
        # Invalid UTF-8 is a per-file rejection, not an invocation failure.
        raise ValueError(f"Checker process failed for {path.name}: {run.stderr} {run.stdout}")
    return run.returncode, json.loads(run.stdout)


def representation_checks(d):
    for record in d["records"]:
        for reading in record["readings"]:
            for step in reading["normalization"]:
                if step["method_id"] == "unicode-nfc":
                    assert step["method_version"] == unicodedata.unidata_version
                    assert unicodedata.normalize("NFC", step["input"]) == step["output"]
    # Do not infer source correctness or a historic sound law from this check.


def fixture_check(item, binary, validator):
    path = ROOT / "data/fixtures" / item["path"]
    schema_errors = []
    try:
        data = strict_json(path.read_text(encoding="utf-8"))
        schema_errors = [e.message for e in validator.iter_errors(data)]
    except (ValueError, UnicodeError) as e:
        data = None; schema_errors = [str(e)]
    with tempfile.TemporaryDirectory() as temp:
        target = Path(temp) / "roundtrip.json" if item["accept"] else None
        code, result = run_checker(binary, path, target)
        actual = code == 0
        issues = [issue["code"] for row in result["results"] for issue in row["issues"]]
        assert actual == item["accept"], (item["path"], result)
        if actual:
            assert not schema_errors, (item["path"], schema_errors)
            # Full structural equality includes original code points, metadata,
            # cells, variants, linked bindings and every retained source column.
            assert strict_json(target.read_text()) == data, item["path"]
            representation_checks(data)
        else:
            assert item["code"] in issues, (item["path"], item["code"], issues)
    return {"fixture": item["path"], "expected_accept": item["accept"],
            "accepted": actual, "expected_error": item.get("code"), "error_codes": issues,
            "json_schema_accepts": not schema_errors,
            "roundtrip_equal": True if actual else None, "passed": True}


def verify(binary):
    schema = strict_json((ROOT / "schema/v1/dossier.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    manifest = strict_json((ROOT / "data/fixtures/manifest.json").read_text())
    listed = {i["path"] for i in manifest}
    present = {str(p.relative_to(ROOT/"data/fixtures")) for category in ["valid", "invalid"]
               for p in (ROOT/"data/fixtures"/category).glob("*.json")}
    assert len(listed) == len(manifest) and listed == present
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda i: fixture_check(i, binary, validator), manifest))
    accepted = sum(i["accept"] for i in manifest)
    assert accepted >= 30 and len(manifest)-accepted >= 20
    with tempfile.TemporaryDirectory() as temp:
        # JSON object ordering and BMP escape spelling are not source changes.
        data = strict_json((ROOT/"data/fixtures/valid/combining-tone.json").read_text())
        path = Path(temp)/"reordered.json";target = Path(temp)/"roundtrip.json"
        path.write_text(json.dumps(data, sort_keys=True, ensure_ascii=True))
        code, result = run_checker(binary,path,target)
        assert code == 0 and strict_json(target.read_text()) == data, result
    pilots = []
    selections = strict_json((ROOT / "data/import-selection.json").read_text())
    for lock in strict_json((ROOT / "data/upstream/manifest.json").read_text()):
        name = lock["id"]; path = ROOT / "data/pilots" / (name + ".json")
        data = strict_json(path.read_text()); validator.validate(data)
        rebuilt, import_report = make_dossier(name, lock, selections[name], ROOT / "data/upstream" / name)
        assert data == rebuilt, f"Pilot differs from deterministic source import: {name}"
        assert import_report == strict_json((ROOT/"reports"/("cldf-"+name+".json")).read_text())
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)/"roundtrip.json"
            code, result = run_checker(binary, path, target)
            assert code == 0, result
            assert strict_json(target.read_text()) == data, "Lean serialization lost source data"
        pilots.append({"dataset":name,"records":len(data["records"]),"commit":lock["commit"],
                       "cldf_valid":True,"source_import_equal":True,"roundtrip_equal":True,
                       "pilot_sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    # Check the actual directory invocation and cross-file duplicate detection.
    code, result = run_checker(binary, ROOT/"data/pilots")
    assert code == 0 and result["records"] == sum(p["records"] for p in pilots), result
    with tempfile.TemporaryDirectory() as temp:
        a = strict_json((ROOT/"data/pilots/iecor.json").read_text())
        b = dict(a); b["id"] += "-duplicate-records"
        dump(Path(temp)/"a.json",a);dump(Path(temp)/"b.json",b)
        code, output = run_checker(binary, Path(temp))
        assert code == 1 and any(i["code"] == "DUPLICATE_GLOBAL_RECORD" for r in output["results"] for i in r["issues"])
    # Hash every input that can alter this report or the engineering behavior.
    paths = sorted(set([*list((ROOT/"lean/Historical").glob("*.lean")), ROOT/"lean/DossierCheck.lean",
        ROOT/"schema/v1/dossier.schema.json",ROOT/"scripts/import_cldf.py",ROOT/"scripts/verify_m1.py",
        ROOT/"data/import-selection.json",ROOT/"data/upstream/manifest.json",
        *list((ROOT/"data/pilots").glob("*.json")),ROOT/"data/fixtures/manifest.json",
        *[ROOT/"data/fixtures"/i["path"] for i in manifest]]))
    return {"milestone":"M1","schema_version":"1.0.0","engineering_checks_passed":True,
            "valid_fixtures":accepted,"adversarial_fixtures":len(manifest)-accepted,
            "cross_file_duplicate_rejected":True,"json_key_order_and_bmp_escapes_preserved":True,
            "pilots":pilots,"fixtures":results,
            "independent_review":"See reports/m1-review.json; software success is not independent review",
            "limitations":["CLDF and JSON validation do not establish historical accuracy.",
                           "The Lean input parser and CLI are executable infrastructure, not a verified byte-level JSON parser.",
                           "Normalization-chain continuity is proved; linguistic correctness of upstream transformations is not.",
                           "Original Unicode strings survive structural round trips; JSON whitespace/key order need not."],
            "input_hashes":{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary",type=Path,default=ROOT/"lean/.lake/build/bin/dossier_check")
    p.add_argument("--output",type=Path,default=ROOT/"reports/schema-validation.json")
    a=p.parse_args(); report=verify(a.binary.resolve());dump(a.output,report)
    print(f"M1 engineering: {report['valid_fixtures']} valid, {report['adversarial_fixtures']} adversarial, "
          f"{sum(p['records'] for p in report['pilots'])} imported records; all checks passed")
