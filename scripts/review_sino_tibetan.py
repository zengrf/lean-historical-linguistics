"""Prepare the M6 packet and check for an independent specialist response."""
import argparse
import hashlib
import json

from build_pie_corpus import ROOT, encoded, digest
from build_kuki_corpus import DEST
from review_pie import assess

PACKET=ROOT/"reviews/sino-tibetan-packet.json"
RESPONSE=ROOT/"reviews/sino-tibetan-responses.json"


def packet():
    corpus=json.loads((DEST/"corpus.json").read_text())
    ds=json.loads((ROOT/"data/cross-branch/dossiers.json").read_text())
    paths=list(DEST.rglob("*.json"))+list((ROOT/"data/cross-branch").glob("*.json"))
    paths += [ROOT/("reports/sino-tibetan-"+n+"-execution.json") for n in ["lexical","diagnostic","joint"]]
    return dict(schema_version="1.0.0",id="m6-sino-tibetan-specialist-review-v1",
        encoder="Codex AI assistant in the primary implementation session",
        required_reviewer="Independent human specialist in Sino-Tibetan historical linguistics with relevant Kuki-Chin expertise; no role in the original encoding. Additional specialists may review particular branches.",
        input_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)},
        core=[dict(id="core-"+s["id"],set_id=s["id"],source_locator=s["source_locator"],record_ids=[r["id"] for r in s["records"]],
            tasks=["Check every extracted form, gloss and doculect against the PDF", "Check source discussion, allofams and possible loans", "Assess normalization, tone, stem cells and unsupported records", "Assess the derivation attempts without treating baseline matches as established histories"])
              for s in corpus["sets"] if s["core"]],
        disputed=[dict(id="cross-"+d["id"],citations=d["citations"],outcome=d["outcome"],
            tasks=["Check transcription, including Chinese written versus reconstructed evidence", "Assess all named analyses and their attribution", "Check topology and the limits of each formal projection", "Record unresolved claims and any objection to releasing this restricted study"])
                  for d in ds["dossiers"]],
        global_checks=["Verify the sample and conservative family grouping, including compounds and repeated source rows", "Keep VanBik and Button reconstruction levels and tone labels separate", "Check whether the declared fragment is sufficient for the milestone's empirical scope", "Check all source-defined controls and whole-paradigm choices", "Distinguish an unresolved historical hypothesis from an unresolved objection to release"],
        response_policy="Bind a dated response to this packet's SHA-256. Each of the 50 core sets and 30 cross-branch dossiers requires a decision and rationale. Unresolved historical results are allowed, but absent review or an unresolved release objection keeps the gate open.")


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--prepare",action="store_true");p.add_argument("--require-complete",action="store_true");a=p.parse_args()
    current=packet()
    if a.prepare:
        PACKET.write_bytes(encoded(current))
        if not RESPONSE.exists():RESPONSE.write_bytes(encoded(dict(schema_version="1.0.0",status="pending",reviewer=None,entries=[],note="No independent specialist response has been supplied. This is not a sign-off.")))
    assert json.loads(PACKET.read_text())==current,"Stale M6 specialist packet"
    response=json.loads(RESPONSE.read_text()) if RESPONSE.exists() else None
    result=assess(current,response)
    (ROOT/"reports/sino-tibetan-review.json").write_bytes(encoded(result))
    print(json.dumps(result))
    if a.require_complete and not result["passed"]:raise SystemExit(1)


if __name__=="__main__":main()
