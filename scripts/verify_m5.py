"""Reproduce M5 results and assess the specialist-review requirement.

Exit 0 establishes engineering checks. --require-complete additionally demands
the independent specialist review required by the unchanged milestone criteria.
"""
import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import build_pie_corpus as corpus_builder
import build_pie_experiment as experiment_builder
import build_pie_controls as controls_builder
from build_pie_corpus import ROOT,DEST,encoded,digest
from reference_rules import run
from review_pie import packet,assess,PACKET,RESPONSE

REPORT=ROOT/"reports/pie-evaluation.json"


def check_freeze_history():
    for commit,paths,model_file in [
        ("83adff4",["data/pie/selection.json","data/pie/splits.json","data/pie/corpus.json"],"data/pie/experiment.json"),
        ("c268e77",["data/pie/latin-control-frozen.json"],"data/pie/latin-control-design.json")]:
        p=subprocess.run(["git","merge-base","--is-ancestor",commit,"HEAD"],cwd=ROOT,capture_output=True)
        assert p.returncode==0,"Missing pre-fitting commit/history; use a full Git clone: "+commit
        for path in paths:
            frozen=subprocess.check_output(["git","show",commit+":"+path],cwd=ROOT)
            assert frozen==(ROOT/path).read_bytes(),"Frozen source bytes changed: "+path
        assert not subprocess.check_output(["git","ls-tree","--name-only",commit,"--",model_file],cwd=ROOT),"Model already present at claimed freeze"


def check_generated():
    check_freeze_history()
    files={**corpus_builder.generate(),**experiment_builder.generate()}
    control=controls_builder.freeze()
    assert (DEST/"latin-control-frozen.json").read_bytes()==encoded(control)
    req,design=controls_builder.generate(control)
    files.update({"latin-control-input.json":req,"latin-control-design.json":design})
    for name,obj in files.items():assert (DEST/name).read_bytes()==encoded(obj),"Stale input: "+name


def input_hashes():
    paths=list(DEST.rglob("*.json"))+list((ROOT/"lean").rglob("*.lean"))
    paths=[p for p in paths if ".lake" not in p.parts]
    names=["scripts/build_pie_corpus.py","scripts/build_pie_experiment.py","scripts/build_pie_controls.py","scripts/verify_m5.py","scripts/review_pie.py","scripts/benchmark_pie.py",
           "scripts/reference_rules.py","scripts/check_proofs.py","scripts/import_cldf.py","tests/test_m5_contracts.py",
           "docs/03-case-studies-and-evaluation.md","docs/11-m5-delivery.md","data/milestones.json","data/pie/README.md","reviews/pie-signoff.md","reviews/pie-packet.json","reviews/pie-responses.json","reports/pie-benchmark-local.json","lean/lakefile.toml",".github/workflows/ci.yml"]
    paths += [ROOT/n for n in names]
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}


def reference(request):
    packages={p["id"]:p for p in request["packages"]}
    @lru_cache(None)
    def predict(pid,w):return run([l["rule"] for l in packages[pid]["laws"]],list(w))
    fs=[];invs=[]
    for j in request["forward"]:
        p=packages[j["package_id"]];steps,out=predict(p["id"],tuple(j["input"]))
        trace=[dict(rule_id=l["id"],input_stage=l["input_stage"],output_stage=l["output_stage"],output=w) for l,w in zip(p["laws"],steps)]
        fs.append(dict(id=j["id"],package_id=p["id"],input=j["input"],steps=trace,output=out,expected=j["expected"],
                       exact=None if j["expected"] is None else out==j["expected"],certificate_accepted=True))
    for j in request["inverse"]:
        found=[w for w in j["pool"] if all(predict(b["package_id"],tuple(w))[1]==b["expected"] for b in j["branches"])]
        invs.append(dict(id=j["id"],complete=True,scope="declared-published-reference-pool",examined=len(j["pool"]),candidates=found,
                         reference=j["reference"],reference_recalled=any(w in j["reference"] for w in found),ambiguous=len(found)>1,empty_in_scope=not found))
    return dict(id=request["id"],input_valid=True,forward=fs,inverse=invs)


def verify_execution(request,result):
    assert result==reference(request),"Lean result differs from the independent interpreter / exact inverse set"


def invoke(binary,args,code=0):
    p=subprocess.run([str(binary),*args],cwd=ROOT,capture_output=True,text=True,timeout=180)
    assert p.returncode==code,(args,p.returncode,p.stdout[:1200],p.stderr[:1200])
    return json.loads(p.stdout)


def check_leakage(corpus,design):
    by={s["id"]:s for s in corpus["sets"]};family_split={}
    for s in corpus["sets"]:
        if s["family_id"] in family_split:assert family_split[s["family_id"]]==s["split"],"Lexical family crosses splits"
        family_split[s["family_id"]]=s["split"]
    for t in design["training_examples"]:
        assert by[t["set_id"]]["split"]=="train","Held-out observation used to fit a model"
        assert t["family_id"]==by[t["set_id"]]["family_id"]
        assert t["record_id"] in {r["id"] for r in by[t["set_id"]]["records"]}
    assert design["training_sha256"]==digest(design["training_examples"])
    assert len(design["outcomes"])==sum(len(s["records"]) for s in corpus["sets"]),"A failed or unsupported record disappeared"
    expected={(s["id"],r["id"]) for s in corpus["sets"] for r in s["records"]}
    actual=[(r["set_id"],r["record_id"]) for r in design["outcomes"]]
    assert len(actual)==len(set(actual)) and set(actual)==expected
    return dict(known_family_cross_split_edges=0,held_out_training_pairs=0,training_pairs=len(design["training_examples"]),
                source_freeze_commit=experiment_builder.FREEZE_COMMIT,latin_freeze_commit="c268e77",
                reference_labels_in_pool=True,frozen_corpus_defines_inventory=True,blind_historical_discovery=False,
                limitations=["Unrecorded root/paradigm links require specialist review.","Published sources and AI pretraining can contain test etymologies; splits do not establish novelty.","Retrieval uses an explicitly declared pool including test root labels; it is not open-vocabulary reconstruction."])


def metrics(corpus,design,execution):
    fs={x["id"]:x for x in execution["forward"]};ins={x["id"]:x for x in execution["inverse"]};by={s["id"]:s for s in corpus["sets"]}
    models={};rows=[]
    for r in design["outcomes"]:
        outcomes={}
        for model in ["identity","correspondence"]:
            attempts=[fs[jid] for jid in r["forward_job_ids"] if ("-"+model+"-a") in jid]
            exact=any(x["exact"] for x in attempts) if attempts else None
            distances=[sum(a!=b for a,b in experiment_builder.align(x["output"],x["expected"]))/max(len(x["output"]),len(x["expected"]),1) for x in attempts]
            outcomes[model]=dict(status="unsupported" if not attempts else "exact-baseline-match" if exact else "mismatch",
                                 exact=exact,minimum_normalized_edit_distance=min(distances) if distances else None,
                                 failure_category=r["failure_category"] if not attempts else None if exact else "unmodeled-morphology-or-sound-history",
                                 derivation_is_linguistically_validated=False,certificate_job_ids=[x["id"] for x in attempts])
        rows.append(dict(set_id=r["set_id"],record_id=r["record_id"],split=r["split"],core=r["core"],source_loan=r["source_loan"],source_uncertainty=r["source_uncertainty"],outcomes=outcomes))
    for model in ["identity","correspondence"]:
        groups={}
        for split in ["all","train","development","test","core"]:
            selected=[r for r in rows if split=="all" or (split=="core" and r["core"]) or r["split"]==split]
            evaluated=[r["outcomes"][model] for r in selected if r["outcomes"][model]["exact"] is not None]
            inv=[x for jid,x in ins.items() if jid.endswith("-"+model) and
                 (split=="all" or (split=="core" and by[jid.split('-')[1]]["core"]) or by[jid.split('-')[1]]["split"]==split)]
            exact=sum(x["exact"] for x in evaluated)
            groups[split]=dict(reflex_denominator=len(selected),evaluated_reflexes=len(evaluated),unsupported_reflexes=len(selected)-len(evaluated),
                exact_reflexes=exact,conditional_exact_accuracy=exact/len(evaluated) if evaluated else None,
                all_reflex_exact_coverage=exact/len(selected) if selected else None,
                mean_normalized_edit_distance=sum(x["minimum_normalized_edit_distance"] for x in evaluated)/len(evaluated) if evaluated else None,
                inverse_set_denominator=len(inv),reference_recalled=sum(x["reference_recalled"] for x in inv),ambiguous_sets=sum(x["ambiguous"] for x in inv),
                empty_in_declared_pool=sum(x["empty_in_scope"] for x in inv),candidate_sizes=[len(x["candidates"]) for x in inv],
                failure_categories=dict(Counter(r["outcomes"][model]["failure_category"] for r in selected if r["outcomes"][model]["failure_category"])))
        models[model]=groups
    return dict(models=models,reflex_results=rows,
                interpretation="Exact matches are baseline string matches with checked execution, not independently validated historical derivations. Alternative reference forms count as a set; every variant's certificate is retained.")


def adversarial_checks(binary):
    base=json.loads((DEST/"diagnostic-input.json").read_text());base["forward"]=base["forward"][:1]
    mutations={
        "duplicate-package":lambda d:d["packages"].append(d["packages"][0]),
        "unknown-package":lambda d:d["forward"][0].update(package_id="absent"),
        "unsupported-symbol":lambda d:d["forward"][0].update(input=["UNDECLARED"]),
        "broken-chronology":lambda d:d["packages"][0]["laws"][0].update(input_stage="wrong"),
        "duplicate-job":lambda d:d["forward"].append(d["forward"][0]),
        "unknown-field":lambda d:d.update(historical_truth=True),
        "omitted-null":lambda d:d["forward"][0].pop("expected"),
    }
    from copy import deepcopy
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/"invalid.json"
        for name,mutate in mutations.items():
            d=deepcopy(base);mutate(d);path.write_bytes(encoded(d));r=invoke(binary,["--batch",str(path)],1);assert r["input_valid"] is False,name
        inv=json.loads((DEST/"lexical-input.json").read_text());inv["forward"]=[];inv["inverse"]=inv["inverse"][:1]
        for name,mutate in {
            "empty-observations":lambda d:d["inverse"][0].update(branches=[]),
            "duplicate-pool":lambda d:d["inverse"][0]["pool"].append(d["inverse"][0]["pool"][0]),
            "reference-outside-pool":lambda d:d["inverse"][0].update(reference=[["OUTSIDE"]]),
        }.items():
            d=deepcopy(inv);mutate(d);path.write_bytes(encoded(d));r=invoke(binary,["--batch",str(path)],1);assert r["input_valid"] is False,name
    return dict(rejected_inputs=10,all_passed=True)


def summaries(corpus,design,executions,alignment_results,evidence,adversarial):
    leakage=check_leakage(corpus,design)
    p=packet();assert json.loads(PACKET.read_text())==p,"Stale specialist packet"
    review=assess(p,json.loads(RESPONSE.read_text()))
    benchmark=json.loads((ROOT/"reports/pie-benchmark-local.json").read_text())
    assert benchmark["certificates"]==1000 and benchmark["passed"]
    assert benchmark["elapsed_seconds"]<60 and benchmark["peak_resident_bytes"]<2*1024**3
    for name,sha in benchmark["input_hashes"].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,"Stale benchmark input: "+name
    core=[s for s in corpus["sets"] if s["core"]]
    counts=dict(cognate_sets=len(corpus["sets"]),reflex_records=sum(len(s["records"]) for s in corpus["sets"]),
                distinct_reflex_rows=len({r["id"] for s in corpus["sets"] for r in s["records"]}),core_sets=len(core),
                core_reflex_records=sum(len(s["records"]) for s in core),branches=sorted({r["branch"] for s in corpus["sets"] for r in s["records"]}),
                core_alignments=len(alignment_results),morphology_dossiers=3,
                forward_certificates=sum(len(r["forward"]) for r in executions.values()),inverse_queries=sum(len(r["inverse"]) for r in executions.values()),
                source_backed_onset_projections=8,synthetic_chronology_controls=10,latin_control_sets=20,latin_daughter_records=60)
    assert counts["cognate_sets"]>=200 and counts["distinct_reflex_rows"]>=600 and counts["core_sets"]==20 and counts["core_reflex_records"]>=60
    assert all(len({r["branch"] for r in s["records"]})>=2 for s in core) and len(counts["branches"])>=5
    assert evidence["accepted"]==1 and evidence["rejected"]==0 and evidence["records"]==counts["distinct_reflex_rows"]
    assert len(alignment_results)==20 and all(x["accepted"] for x in alignment_results.values())
    diag=executions["diagnostic"];package_scores={}
    for pid in {x["package_id"] for x in diag["forward"]}:
        xs=[x for x in diag["forward"] if x["package_id"]==pid]
        package_scores[pid]=dict(cases=len(xs),exact=sum(x["exact"] for x in xs),mismatches=[x["id"] for x in xs if not x["exact"]])
    assert package_scores["ringe-2022-vcv"]["exact"]==10
    assert package_scores["kloekhorst-2006-written-onset"]["exact"]==8
    assert package_scores["stress-before-verner-control"]["exact"]<10
    assert package_scores["melchert-retention-as-reported-2006"]["exact"]<8
    control=json.loads((DEST/"latin-control-frozen.json").read_text());control_design=json.loads((DEST/"latin-control-design.json").read_text())
    split={s["id"]:s["split"] for s in control["samples"]}
    assert all(split[t["set_id"]]=="train" for t in control_design["training_examples"])
    latin={}
    for model in ["identity","correspondence"]:
        latin[model]={}
        for part in ["train","development","test"]:
            fs=[r for r in executions["latin-control"]["forward"] if r["id"].endswith("-"+model) and split[r["id"].split('-')[1]]==part]
            inv=[r for r in executions["latin-control"]["inverse"] if r["id"].endswith("-"+model) and split[r["id"].split('-')[1]]==part]
            latin[model][part]=dict(reflexes=len(fs),exact=sum(x["exact"] for x in fs),inverse_queries=len(inv),recalled=sum(x["reference_recalled"] for x in inv),ambiguous=sum(x["ambiguous"] for x in inv),empty=sum(x["empty_in_scope"] for x in inv))
    return dict(milestone="M5",status="delivered" if review["passed"] else "in_review",engineering_passed=True,
                all_deliverables_accepted=review["passed"],label="linguistically validated" if review["passed"] else "computationally checked, linguistically unreviewed",
                counts=counts,criteria=[
                    dict(id="M5-core",status="passed" if review["passed"] else "awaiting-specialist-review",evidence="20 core sets / 161 reflexes, source locators, explicit normalization, baseline attempts and failures; the independent review remains required."),
                    dict(id="M5-scale",status="passed",evidence="200 sets and 843 distinct source forms; all unsuccessful and unsupported outcomes retained."),
                    dict(id="M5-analyses",status="passed",evidence="Scoped source-defined chronology and alternative laryngeal packages; three morphology dossiers preserve disputed predictions. Attribution limitations remain explicit."),
                    dict(id="M5-evaluation",status="passed",evidence="Committed family-grouped splits predate model fitting; deterministic baselines, Latin control, complete finite-pool queries, denominators and leakage limitations retained."),
                    dict(id="M5-signoff",status="passed" if review["passed"] else "pending",evidence="Independent human family-specialist approval is required; computational checks cannot supply it.")],
                lexical=metrics(corpus,design,executions["lexical"]),source_analysis_comparison=package_scores,latin_control=latin,
                leakage=leakage,review=review,evidence=evidence,alignments=alignment_results,adversarial=adversarial,benchmark=benchmark,
                proof_audit=dict(declarations=133,new_case_study_theorems=6,project_axioms=False,proof_placeholders=False),
                limitations=["This is an empirical baseline pilot with low full-word coverage, not a completed PIE sound-law reconstruction.",
                             "Root-to-lexeme morphology and many sound changes are outside the lexical baselines; exact matches alone are not validated etymologies.",
                             "Eight laryngeal cases test projected onsets, not full-word reflexes. Ten chronology controls are synthetic.",
                             "Some competing analyses are attributed through a source discussion rather than an independently read original monograph.",
                             "The review packet is ready, but no independent specialist sign-off is supplied by this implementation."],input_hashes=input_hashes())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--audit",type=Path,default=ROOT/"reports/lean-axioms-local.txt");p.add_argument("--check-report",action="store_true");p.add_argument("--require-complete",action="store_true");a=p.parse_args()
    check_generated();corpus=json.loads((DEST/"corpus.json").read_text());design=json.loads((DEST/"experiment.json").read_text());executions={}
    binary=ROOT/"lean/.lake/build/bin/pie_check"
    if not a.check_report:
        subprocess.run([sys.executable,str(ROOT/"scripts/check_proofs.py"),str(a.audit)],check=True,cwd=ROOT)
    for name in ["lexical","diagnostic","latin-control"]:
        request=json.loads((DEST/(name+"-input.json")).read_text());out=ROOT/f"reports/pie-{name}-execution.json"
        result=json.loads(out.read_text()) if a.check_report else invoke(binary,["--batch",str(DEST/(name+"-input.json"))])
        verify_execution(request,result);executions[name]=result
        if not a.check_report:out.write_bytes(encoded(result))
        print("M5",name,"Lean/Python agreement:",len(result["forward"]),"certificates,",len(result["inverse"]),"inverse sets",flush=True)
    if a.check_report:
        previous=json.loads(REPORT.read_text());alignment_results=previous["alignments"];evidence=previous["evidence"];adversarial=previous["adversarial"]
    else:
        alignment_results={p.stem:invoke(ROOT/"lean/.lake/build/bin/correspondence_check",["--file",str(p)]) for p in sorted((DEST/"alignments").glob("*.json"))}
        evidence=invoke(ROOT/"lean/.lake/build/bin/dossier_check",["data/pie/evidence.json","--strict"])
        adversarial=adversarial_checks(binary)
    result=summaries(corpus,design,executions,alignment_results,evidence,adversarial)
    milestone=next(m for m in json.loads((ROOT/"data/milestones.json").read_text()) if m["id"]=="M5")
    assert milestone["status"]==result["status"],"Milestone register disagrees with specialist-review status"
    assert {c["id"] for c in milestone["acceptance"]}=={c["id"] for c in result["criteria"]}
    for name in milestone["artifacts"]:
        if name!="reports/pie-evaluation.json" or a.check_report:
            assert (ROOT/name).exists(),"Missing M5 artifact: "+name
    if a.check_report:assert json.loads(REPORT.read_text())==result,"Stale M5 report"
    else:REPORT.write_bytes(encoded(result))
    print("M5:",result["label"],json.dumps(result["counts"],sort_keys=True))
    if a.require_complete and not result["all_deliverables_accepted"]:raise SystemExit(1)


if __name__=="__main__":main()
