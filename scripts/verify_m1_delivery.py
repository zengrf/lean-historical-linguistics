"""Reconcile M1 deliverables without treating independent review as automated.

Run after verify_m1.py and review_m1.py. --require-complete fails while any
criterion is pending. The default validates engineering delivery and reports
the remaining gate, allowing CI to test work awaiting an external reviewer.
"""
import argparse
import hashlib
import json
from pathlib import Path
from import_cldf import ROOT, dump
from review_m1 import packet_and_expected, assess


def verify():
    engineering=json.loads((ROOT/"reports/schema-validation.json").read_text())
    assert engineering["engineering_checks_passed"]
    for rel, expected in engineering["input_hashes"].items():
        assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==expected, "Stale engineering report: "+rel
    assert engineering["valid_fixtures"]>=30 and engineering["adversarial_fixtures"]>=20
    assert all(x["passed"] for x in engineering["fixtures"])
    assert all(p["roundtrip_equal"] and p["source_import_equal"] and p["cldf_valid"] for p in engineering["pilots"])
    packet,expected=packet_and_expected()
    assert json.loads((ROOT/"reviews/m1-packet.json").read_text())==packet
    path=ROOT/"reviews/m1-responses.json"
    review=assess(packet,expected,json.loads(path.read_text()) if path.exists() else None)
    assert review==json.loads((ROOT/"reports/m1-review.json").read_text()), "Stale independent review report"
    assert not review["errors"], review["errors"]
    m=next(m for m in json.loads((ROOT/"data/milestones.json").read_text()) if m["id"]=="M1")
    for artifact in m["artifacts"]:
        if artifact!="reports/m1-delivery.json":assert (ROOT/artifact).exists(), "Missing artifact: "+artifact
    complete=review["status"]=="passed"
    assert m["status"]==("delivered" if complete else "in_review"), "Milestone status does not match acceptance evidence"
    return {"milestone":"M1","status":"delivered" if complete else "in_review",
            "all_deliverables_accepted":complete,"engineering_deliverables_accepted":True,
            "criteria":[
                {"id":"M1-fixtures","status":"passed","evidence":"reports/schema-validation.json",
                 "result":f"{engineering['valid_fixtures']} valid and {engineering['adversarial_fixtures']} adversarial fixtures; intended rejection reasons checked"},
                {"id":"M1-lossless","status":"passed","evidence":"reports/schema-validation.json",
                 "result":"Every valid fixture and all 60 imported records survive structural Lean JSON round trips; immutable source snapshots and exact original strings retained"},
                {"id":"M1-cldf","status":"passed","evidence":["reports/cldf-iecor.json","reports/cldf-hillburmish.json","docs/07-m1-delivery.md"],
                 "result":"Both full upstream CLDF snapshots validate; 30 records from each imported reproducibly; unsupported fields/tables retained and explicitly reported"},
                {"id":"M1-review","status":review["status"],"evidence":"reports/m1-review.json",
                 "result":f"{review['reviewed_records']} independently entered records; at least {review['minimum_reviewed']} required; {review['uncertain_records']} flagged imported readings"}],
            "artifacts":m["artifacts"],
            "next_action":None if complete else "Independent reviewer completes reviews/m1-response-template.json as reviews/m1-responses.json; resolve/flag discrepancies, rerun review and delivery checks, and only then mark M1 delivered."}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--require-complete",action="store_true")
    a=p.parse_args();report=verify();dump(ROOT/"reports/m1-delivery.json",report)
    print(f"M1: {report['status']}; engineering passed; all deliverables accepted={report['all_deliverables_accepted']}")
    if a.require_complete and not report["all_deliverables_accepted"]:raise SystemExit(1)
