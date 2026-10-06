"""M5 specialist-review gate. Computational checks never impersonate sign-off."""
import argparse
import hashlib
import json
from pathlib import Path

from build_pie_corpus import ROOT, DEST, encoded, digest

PACKET = ROOT / "reviews/pie-packet.json"
RESPONSE = ROOT / "reviews/pie-responses.json"


def packet():
    corpus=json.loads((DEST/"corpus.json").read_text())
    sources=json.loads((DEST/"source-analyses.json").read_text())
    morphology=json.loads((DEST/"morphology.json").read_text())
    paths=list(DEST.rglob("*.json")) + [ROOT/"reports/pie-lexical-execution.json",ROOT/"reports/pie-diagnostic-execution.json",ROOT/"reports/pie-latin-control-execution.json"]
    return dict(schema_version="1.0.0",id="pie-m5-specialist-review-v1",encoder="Codex AI assistant in the primary implementation session",
        required_reviewer="Independent human specialist in Indo-European historical linguistics; no role in the original encoding",
        input_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)},
        core=[dict(id="core-"+s["id"],set_id=s["id"],source_locator=s["source_locator"],record_ids=[r["id"] for r in s["records"]],
                   tasks=["Check the source forms and exact locators", "Assess normalization, variety and attestation status", "Assess each derivation attempt and retained failure", "Record uncertainty, morphology and chronological limitations"])
              for s in corpus["sets"] if s["core"]],
        disputed=[dict(id="analysis-"+c["id"],source=c["source"],locator=c["locator"],scope=c["scope"],uncertainty=c["uncertainty"])
                  for c in sources["cases"] if c["kind"]=="source-backed-projection"] +
                 [dict(id="morphology-"+m["id"],source=m["source"],locator=m["locator"],tasks=["Assess source attribution and competing analyses", "Record unresolved objections; do not infer agreement from formal validity"])
                  for m in morphology["dossiers"]],
        global_checks=["Check Ringe's scoped chronology and deliberately wrong-order control", "Check secondary attribution of Melchert, Jasanoff and Schindler", "Review conservative family grouping for hidden root or paradigm links", "Confirm no successful full PIE derivation is claimed solely from baseline exact matches", "Assess whether the restricted fragment is sufficient for release"],
        response_policy="Bind the response to this packet's SHA-256. Every core/disputed item needs a decision and rationale. An AI report, missing response, self-review or unresolved release objection does not close the gate.")


def assess(p,response):
    result=dict(status="pending-specialist-review",passed=False,reviewed_core=0,reviewed_disputed=0,objections=[],issues=[])
    if response is None or response.get("status")=="pending":
        result["issues"].append("No independent family-specialist assessment has been supplied.");return result
    def require(ok,message):
        if not ok:result["issues"].append(message)
    reviewer=response.get("reviewer",{})
    require(response.get("packet_sha256")==digest(p),"Review packet has changed or is not identified.")
    require(reviewer.get("type")=="human-family-specialist","Reviewer must be an identified human family specialist.")
    require(bool(reviewer.get("name","").strip()) and bool(reviewer.get("expertise","").strip()),"Reviewer identity and relevant expertise are required.")
    require(reviewer.get("independent_of_encoding") is True,"Reviewer must be independent of the encoding.")
    require(bool(response.get("signed_at")) and bool(response.get("attestation")),"A dated explicit attestation is required.")
    entries=response.get("entries",[]);by={e.get("id"):e for e in entries}
    ids={x["id"] for x in p["core"]+p["disputed"]}
    require(len(by)==len(entries) and set(by)==ids,"Every required item must appear exactly once.")
    for kind,key in [("core","reviewed_core"),("disputed","reviewed_disputed")]:
        for item in p[kind]:
            e=by.get(item["id"],{})
            complete=e.get("decision") in {"approve","unresolved-objection"} and bool(e.get("rationale","").strip()) and bool(e.get("source_locators"))
            require(complete,"Incomplete review item: "+item["id"])
            if complete:result[key]+=1
            if e.get("decision")=="unresolved-objection":result["objections"].append(e)
    require(response.get("global_checks_complete") is True,"Global scope, leakage and attribution checks are not complete.")
    require(response.get("decision")=="approve","Overall specialist approval is absent.")
    result["passed"]=not result["issues"] and not result["objections"]
    result["status"]="passed" if result["passed"] else "reviewed-with-open-issues"
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--prepare",action="store_true");p.add_argument("--require-complete",action="store_true");a=p.parse_args()
    current=packet()
    if a.prepare:
        PACKET.write_bytes(encoded(current))
        if not RESPONSE.exists():RESPONSE.write_bytes(encoded(dict(schema_version="1.0.0",status="pending",reviewer=None,entries=[],note="No specialist response has been received. This file is not a sign-off.")))
    assert json.loads(PACKET.read_text())==current,"Stale specialist packet: regenerate it and obtain a fresh review"
    response=json.loads(RESPONSE.read_text()) if RESPONSE.exists() else None
    result=assess(current,response)
    (ROOT/"reports/pie-review.json").write_bytes(encoded(result))
    print(json.dumps(result,ensure_ascii=False))
    if a.require_complete and not result["passed"]:raise SystemExit(1)


if __name__=="__main__":main()
