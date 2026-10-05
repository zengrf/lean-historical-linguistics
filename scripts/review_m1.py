"""Prepare a blinded source-entry packet and check M1's independent review gate.

No review is synthesized. A missing/partial response produces a pending report.
--require-complete exits nonzero unless the recorded review meets the criteria.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from import_cldf import ROOT, dump


def packet_and_expected():
    rows=[]; selected=[]
    locks={x["id"]:x for x in json.loads((ROOT/"data/upstream/manifest.json").read_text())}
    for path in sorted((ROOT/"data/pilots").glob("*.json")):
        d=json.loads(path.read_text());name=path.stem;lock=locks[name]
        records=d["records"];rows.extend(records)
        # Fixed SHA-based sample: reproducible, not selected for easy agreement.
        sample=sorted(records,key=lambda r:hashlib.sha256(r["id"].encode()).hexdigest())[:math.ceil(len(records)*0.1)]
        for r in records:
            if r["uncertain"] and r not in sample:sample.append(r)
        for r in sample:
            origin=r["imported_from"]
            selected.append({"record_id":r["id"],"dataset":name,"commit":lock["commit"],
                "source_url":lock["repository"]+"/blob/"+lock["commit"]+"/cldf/"+origin["table"],
                "source_file":"data/upstream/"+name+"/cldf/"+origin["table"],
                "row_id":origin["row_id"],"id_column":origin["id_column"],
                "column_to_transcribe":origin["original_column"],"uncertain":r["uncertain"],
                "source_snapshot_sha256":hashlib.sha256((ROOT/"data/upstream"/name/"cldf"/origin["table"]).read_bytes()).hexdigest()})
    packet={"schema_version":"1.0.0","kind":"independent-double-entry",
            "instructions":"A reviewer independent of the import/encoding must open each pinned source row and transcribe the requested column without consulting data/pilots or expected imported values. This is a source-entry check, not a historical-linguistic sign-off.",
            "core_records":len(rows),"minimum_records":math.ceil(len(rows)*0.1),"items":selected,
            "responses_file":"reviews/m1-responses.json"}
    return packet,{r["id"]:r for r in rows}


def assess(packet, expected, responses):
    errors=[]; entries=[]; reviewed=set()
    if responses:
        reviewer=responses.get("reviewer_id","")
        if not reviewer or reviewer.lower() in {"codex","assistant","assistant:codex","importer"}:
            errors.append("Reviewer identity must name the actual independent reviewer")
        if responses.get("independent_of_encoding") is not True:
            errors.append("Independent-of-encoding attestation is absent")
        if responses.get("packet_sha256") != hashlib.sha256(json.dumps(packet,ensure_ascii=False,sort_keys=True).encode()).hexdigest():
            errors.append("Review is not tied to the current packet/source snapshot")
        for entry in responses.get("entries",[]):
            rid=entry.get("record_id")
            if rid not in expected or rid in reviewed:
                errors.append("Unknown or repeated review record: "+str(rid));continue
            reviewed.add(rid);record=expected[rid]
            match=entry.get("original") == record["readings"][0]["original"]
            resolution=entry.get("resolution")
            resolved=match or (isinstance(resolution,dict) and resolution.get("status")=="flagged" and
                               bool(resolution.get("reason")) and record["uncertain"])
            if not resolved:errors.append("Unresolved transcription discrepancy: "+rid)
            entries.append({"record_id":rid,"matches_import":match,"resolved_or_flagged":bool(resolved)})
    required={i["record_id"] for i in packet["items"]}
    missing=sorted(required-reviewed)
    complete=bool(responses) and not errors and not missing and len(reviewed)>=packet["minimum_records"]
    return {"milestone":"M1","criterion":"M1-review","status":"passed" if complete else "pending",
            "core_records":len(expected),"minimum_reviewed":packet["minimum_records"],
            "required_record_ids":sorted(required),"reviewed_records":len(reviewed),
            "coverage":len(reviewed)/len(expected),"uncertain_records":sum(r["uncertain"] for r in expected.values()),
            "missing_record_ids":missing,"entries":entries,"errors":errors,
            "reviewer_id":responses.get("reviewer_id") if responses else None,
            "limitation":"The script verifies recorded coverage and transcription agreement. Reviewer identity and independence are attestations; it cannot authenticate people or replace specialist review."}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prepare",action="store_true")
    p.add_argument("--require-complete",action="store_true")
    a=p.parse_args();packet,expected=packet_and_expected()
    if a.prepare:
        dump(ROOT/"reviews/m1-packet.json",packet)
        template={"reviewer_id":"","independent_of_encoding":False,
                  "packet_sha256":hashlib.sha256(json.dumps(packet,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
                  "entries":[{"record_id":i["record_id"],"original":"","resolution":None} for i in packet["items"]]}
        dump(ROOT/"reviews/m1-response-template.json",template)
    else:
        if json.loads((ROOT/"reviews/m1-packet.json").read_text()) != packet:
            raise SystemExit("Stale review packet; regenerate and review changed sources")
    response_path=ROOT/"reviews/m1-responses.json"
    report=assess(packet,expected,json.loads(response_path.read_text()) if response_path.exists() else None)
    dump(ROOT/"reports/m1-review.json",report)
    print(f"M1 independent review: {report['status']}; {report['reviewed_records']}/{report['minimum_reviewed']} required entries")
    if report["errors"] or (a.require_complete and report["status"]!="passed"):raise SystemExit(1)


if __name__=="__main__":main()
