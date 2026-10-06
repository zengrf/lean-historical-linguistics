"""Verify M6 computations, source boundaries and the remaining review gates.

Exit 0 means the engineering checks passed. --require-complete also requires
the independent specialist assessment in the original milestone criteria.
"""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from build_pie_corpus import ROOT, encoded, digest
from build_kuki_corpus import DEST, generate as corpus_files
from build_sino_tibetan_sources import generate as source_files
from build_m6_experiment import generate as experiment_files, FREEZE_COMMIT
from verify_m5 import invoke, reference
from reference_reconstruction import evaluate
import reference_correspondence as correspondence
from review_sino_tibetan import packet, assess, PACKET, RESPONSE

REPORT=ROOT/"reports/sino-tibetan-evaluation.json"
BINARY=ROOT/"lean/.lake/build/bin/sino_tibetan_check"


def frozen_history():
    p=subprocess.run(["git","merge-base","--is-ancestor",FREEZE_COMMIT,"HEAD"],cwd=ROOT,capture_output=True)
    assert p.returncode==0,"M6 freeze commit missing; use full Git history"
    paths=["data/kuki-chin/"+n for n in ["corpus.json","selection.json","splits.json","study-design.json"]]
    paths += ["data/cross-branch/dossiers.json","data/cross-branch/source-scopes.json"]
    for name in paths:
        assert subprocess.check_output(["git","show",FREEZE_COMMIT+":"+name],cwd=ROOT)==(ROOT/name).read_bytes(),"Frozen source input changed: "+name
    assert not subprocess.check_output(["git","ls-tree","--name-only",FREEZE_COMMIT,"--","data/kuki-chin/experiment.json"],cwd=ROOT),"Model present at the claimed pre-fitting freeze"


def generated_check():
    frozen_history()
    for base,files in [(DEST,corpus_files()),(ROOT/"data/cross-branch",source_files()),(DEST,experiment_files())]:
        for name,obj in files.items():assert (base/name).read_bytes()==encoded(obj),"Stale M6 input: "+str(base/name)


def check_leakage(corpus,design):
    by={s["id"]:s for s in corpus["sets"]};families={}
    for s in corpus["sets"]:
        assert families.get(s["family_id"],s["split"])==s["split"],"A lexical family crosses splits"
        families[s["family_id"]]=s["split"]
    for t in design["training_examples"]:
        s=by[t["set_id"]]
        assert s["split"]=="train","Held-out reflex in training"
        assert t["family_id"]==s["family_id"] and t["record_id"] in {r["id"] for r in s["records"]}
        assert not s["extraction"]["loan_mentioned"],"Possible source loan trained without review"
    assert digest(design["training_examples"])==design["training_sha256"]
    expected={(s["id"],r["id"]) for s in corpus["sets"] for r in s["records"]}
    actual=[(r["set_id"],r["record_id"]) for r in design["outcomes"]]
    assert len(actual)==len(set(actual)) and set(actual)==expected,"A failed, repeated or unsupported source row disappeared"
    return dict(freeze_commit=FREEZE_COMMIT,training_pairs=len(design["training_examples"]),held_out_training_pairs=0,
        known_family_cross_split_edges=0,reference_labels_in_pool=True,inventory_from_frozen_corpus=True,
        blind_historical_discovery=False,limitation="Unrecorded root relations, prior publication and model pretraining prevent a novelty claim.")


def verify_execution(request,result):
    assert result["scope_valid"] is True
    assert result["result"]==reference(request["batch"]),"M6 Lean/Python disagreement in a trace or complete inverse set"


def metrics(corpus,design,execution):
    fs={x["id"]:x for x in execution["result"]["forward"]};inv={x["id"]:x for x in execution["result"]["inverse"]}
    rows=[];by={s["id"]:s for s in corpus["sets"]}
    for r in design["outcomes"]:
        models={}
        for model in ["identity","correspondence"]:
            attempts=[fs[id] for id in r["forward_job_ids"] if id.endswith("-"+model)]
            exact=all(a["exact"] for a in attempts) if attempts else None
            models[model]=dict(status="unsupported" if not attempts else "exact-transcription-match" if exact else "mismatch",exact=exact,
                required_stem_cells=len(attempts),failure_category=r["failure_category"] if not attempts else None if exact else "unmodelled-transcription-morphology-or-sound-change",
                certificate_job_ids=[a["id"] for a in attempts],linguistically_validated=False)
        rows.append(dict(set_id=r["set_id"],record_id=r["record_id"],split=r["split"],core=r["core"],models=models))
    scores={}
    for model in ["identity","correspondence"]:
        scores[model]={}
        for part in ["all","core","train","development","test"]:
            chosen=[r for r in rows if part=="all" or (part=="core" and r["core"]) or r["split"]==part]
            supported=[r["models"][model] for r in chosen if r["models"][model]["exact"] is not None]
            queries=[inv[q["id"]] for q in design["topology_queries"] if q["model"]==model and q["scope"]=="all-groups" and
                (part=="all" or (part=="core" and by[q["set_id"]]["core"]) or by[q["set_id"]]["split"]==part)]
            exact=sum(x["exact"] for x in supported)
            scores[model][part]=dict(reflex_denominator=len(chosen),evaluated_reflexes=len(supported),unsupported_reflexes=len(chosen)-len(supported),
                exact_reflexes=exact,conditional_exact_accuracy=exact/len(supported) if supported else None,
                all_reflex_exact_coverage=exact/len(chosen) if chosen else None,
                inverse_queries=len(queries),reference_recalled=sum(x["reference_recalled"] for x in queries),
                ambiguous=sum(x["ambiguous"] for x in queries),empty_in_scope=sum(x["empty_in_scope"] for x in queries),
                candidate_sizes=[len(x["candidates"]) for x in queries],
                failure_categories=dict(Counter(r["models"][model]["failure_category"] for r in chosen if r["models"][model]["failure_category"])))
    return dict(models=scores,reflex_results=rows,
        interpretation="Tone-excluded transcription baselines. A multi-cell record matches only if all required stem cells match. Exact matches are not independently validated etymologies.")


def sensitivity(corpus,design,lexical,diagnostic,joint):
    inv={x["id"]:x for x in lexical["result"]["inverse"]};comparisons=[]
    for q in design["topology_queries"]:
        if q["scope"]!="northern-only":continue
        full=q["id"].removesuffix("northern-only")+"all-groups"
        strong=inv[full]["candidates"];weak=inv[q["id"]]["candidates"]
        assert all(w in weak for w in strong),"Removing observations lost a compatible candidate"
        comparisons.append(dict(all_groups_query=full,northern_only_query=q["id"],all_groups_candidates=strong,northern_only_candidates=weak,
            changed=strong!=weak,ancestor="vanbik-2009-PKC",interpretation="Same PKC input node and rules; only observation coverage changes"))
    fs=diagnostic["result"]["forward"]
    failures=[j["id"] for j in fs if not j["exact"]]
    expected={"plain-stop-mindat--plain-stop-retention-control","sr-shame--sr-broad","sr-root--sr-broad",
        "wa-horn--fusion-before-wa-control","wa-angle--fusion-before-wa-control","suffix-l-control--unconditioned-t-to-s-control"}
    assert set(failures)==expected,"A source fragment or its authored control no longer has the stated outcome"
    assert [(c["analysis_id"],c["protoform"]) for c in joint["candidates"]]==[("N-anticausative",["p"]),("s-devoicing",["b"])],"A whole-paradigm alternative was lost or mixed"
    scopes={
        "VanBik-all-groups":set(r["doculect_id"] for s in corpus["sets"] for r in s["records"]),
        "VanBik-Northern":set("vb-"+d for d in ["tedim","paite","thado-kuki","sizang"]),
        "Button-overlap-with-explicit-name-matches":set("vb-"+d for d in ["mizo","thado-kuki","tedim","sizang"]),
        "Button-overlap-if-Zahao-Zahau-rows-are-identified":set("vb-"+d for d in ["mizo","thado-kuki","tedim","sizang","falam-lai"])}
    coverage={k:dict(doculects=sorted(v),records=sum(r["doculect_id"] in v for s in corpus["sets"] for r in s["records"]),
        sets_with_two_varieties=sum(len({r["doculect_id"] for r in s["records"] if r["doculect_id"] in v})>=2 for s in corpus["sets"])) for k,v in scopes.items()}
    return dict(observation_coverage_comparisons=comparisons,changed_inverse_sets=sum(c["changed"] for c in comparisons),
        source_scope_coverage=coverage,
        scope_interpretation="Coverage in VanBik's corpus, not a substitute Button corpus. No PKC form is promoted to Button PNC or to PTB/PST. The Zahao/Zahau row identification is a separately labelled assumption.",
        topology=[dict(id="unresolved-ST-polytomy",sr_loss_placement="Separate relevant daughter edges; no exclusive non-Sinitic edge is assumed"),
                  dict(id="ST-with-TB-node",sr_loss_placement="One TB edge is possible only if the topology, cognacy and sound condition are justified")],
        topology_result="Rebracketing with identical composed branch functions leaves predictions and inverse membership unchanged (SourceScope.path_composition and indistinguishable_paths). This experiment does not infer the ST tree; the broad sr condition fails the source's ə counterexamples.",
        source_fragment_certificates=len(fs),source_fragment_matches=len(fs)-len(failures),retained_failures=failures,
        joint_paradigm_candidates=[dict(analysis_id=c["analysis_id"],protoform=c["protoform"],choice_bindings=c["choice_bindings"]) for c in joint["candidates"]],
        merged_ancestor_candidates=diagnostic["result"]["inverse"][0]["candidates"],
        further_evidence="Tibetan prefixes need dialectal/textual paradigms; the OC voice pair needs nasality and derivational direction, and the sr alternatives need Chinese internal and comparative evidence. Matching projected outputs does not supply these observations.")


def adversarial_checks():
    base=json.loads((DEST/"lexical-input.json").read_text());base["batch"]["forward"]=base["batch"]["forward"][:1]
    base["batch"]["inverse"]=base["batch"]["inverse"][:1];qid=base["batch"]["inverse"][0]["id"]
    base["query_scopes"]=[q for q in base["query_scopes"] if q["query_id"]==qid]
    results=[]
    def bad(name,mutate):
        d=deepcopy(base);mutate(d)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"bad.json";p.write_bytes(encoded(d));r=invoke(BINARY,["--batch",str(p)],1)
        assert r["scope_valid"] is False;results.append(dict(case=name,rejected=True))
    bad("unknown-top-field",lambda d:d.update(unchecked=True))
    bad("unknown-batch-field",lambda d:d["batch"].update(unchecked=True))
    bad("omitted-scopes",lambda d:d.pop("package_scopes"))
    bad("missing-query-scope",lambda d:d.update(query_scopes=[]))
    bad("duplicate-node",lambda d:d["nodes"].append(d["nodes"][0]))
    bad("duplicate-package-scope",lambda d:d["package_scopes"].append(d["package_scopes"][0]))
    def wrong_ancestor(d):
        n=dict(source_id="button2011",node_id="button-2011-PNC");d["nodes"].append(n);d["query_scopes"][0]["ancestor"]=n
    bad("PKC-is-not-Button-PNC",wrong_ancestor)
    def source_alias(d):
        n=deepcopy(d["query_scopes"][0]["ancestor"]);n["source_id"]="another-author";d["nodes"].append(n);d["query_scopes"][0]["ancestor"]=n
    bad("same-node-label-different-source",source_alias)
    bad("observation-for-wrong-variety",lambda d:d["batch"]["inverse"][0]["branches"][0].update(doculect_id="invented-variety"))
    bad("duplicate-inverse-variety",lambda d:d["batch"]["inverse"][0]["branches"][1].update(doculect_id=d["batch"]["inverse"][0]["branches"][0]["doculect_id"]))
    bad("invented-model-operation",lambda d:next(p for p in d["batch"]["packages"] if p["laws"])["laws"][0]["rule"].update(mode="arbitrary-code"))
    for name,raw in [("duplicate-JSON-key",encoded(base).replace(b'"schema_version": "1.0.0"',b'"schema_version": "1.0.0", "schema_version": "1.0.0"',1)),("invalid-UTF8",b'\xff')]:
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"bad.json";p.write_bytes(raw);r=invoke(BINARY,["--batch",str(p)],1)
        assert r["scope_valid"] is False;results.append(dict(case=name,rejected=True))
    joint=json.loads((DEST/"joint-analysis-input.json").read_text());joint["analyses"][0]["choice_bindings"]=[]
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/"mixed.json";p.write_bytes(encoded(joint));r=invoke(ROOT/"lean/.lake/build/bin/reconstruct",["--file",str(p)],1)
    assert not r["input_valid"];results.append(dict(case="unbound-paradigm-choice",rejected=True))
    return results


def evidence_checks():
    result={}
    for name in ["evidence.json","cross-evidence.json"]:
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"roundtrip.json"
            r=invoke(ROOT/"lean/.lake/build/bin/dossier_check",[str((DEST/name).relative_to(ROOT)),"--strict","--roundtrip",str(path)])
            assert json.loads(path.read_text())==json.loads((DEST/name).read_text()),"M6 Unicode or choice binding changed in serialization"
        assert r["rejected"]==0;result[name]=dict(records=r["records"],accepted=True,exact_roundtrip=True)
    # Separate synthetic interchange controls. They add no source observations.
    d=json.loads((DEST/"evidence.json").read_text());d["id"]="m6-interchange-control";d["records"]=d["records"][:1]
    d["sources"][0]["kind"]="synthetic";d["description"]="Synthetic controls for absent, uncertain and aligned cells; not source data"
    outcomes=[]
    for kind,form,cells in [("missing","",[dict(kind="missing",value=None)]),("unknown","?",[dict(kind="unknown",value="?")]),
        ("present","á",[dict(kind="segment",value="a"),dict(kind="gap",value=None),dict(kind="segment",value="́")])]:
        c=deepcopy(d);rec=c["records"][0];rec["evidence_state"]=kind;rd=rec["readings"][0];rd.update(original=form,normalized=form,cells=cells)
        rd["normalization"][0].update(input=form,output=form)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"control.json";out=Path(tmp)/"roundtrip.json";path.write_bytes(encoded(c))
            r=invoke(ROOT/"lean/.lake/build/bin/dossier_check",[str(path),"--strict","--roundtrip",str(out)])
            assert r["rejected"]==0 and json.loads(out.read_text())==c
        outcomes.append(kind)
    result["synthetic_cell_roundtrips"]=outcomes
    return result


def alignment_checks():
    result={}
    corpus=json.loads((DEST/"corpus.json").read_text());forms={r["id"]:r["source_form"] for s in corpus["sets"] for r in s["records"]}
    for p in sorted((DEST/"alignments").glob("*.json")):
        d=json.loads(p.read_text());out=invoke(ROOT/"lean/.lake/build/bin/correspondence_check",["--file",str(p)])
        expected=correspondence.evaluate(d)
        assert all(out[k]==v for k,v in expected.items()),"M3 reference disagreement"
        assert not out["issues"] and out["id"]==d["alignment_data"]["id"]
        assert all(r["preserved"] and r["recovered"]==r["original"] for a in out["alignments"] for r in a["rows"])
        assert out["accepted"] and out["alignment_accepted"]
        for row in d["alignment_data"]["alignments"][0]["rows"]:
            chars="".join(chr(int(c["value"][1:],16)) for c in row["aligned"] if c["kind"]!="gap")
            assert chars==forms[row["doculect_id"]],"Alignment lost a source space, tone or stem label"
        result[p.stem]=out
    assert len(result)==50
    return result


def input_hashes():
    paths=list(DEST.rglob("*.json"))+list((ROOT/"data/cross-branch").glob("*.json"))+[p for p in (ROOT/"lean").rglob("*.lean") if ".lake" not in p.parts]
    names=["scripts/build_kuki_corpus.py","scripts/build_sino_tibetan_sources.py","scripts/build_m6_experiment.py","scripts/verify_m6.py","scripts/review_sino_tibetan.py","scripts/benchmark_m6.py",
        "scripts/build_pie_experiment.py","scripts/reference_rules.py","scripts/reference_correspondence.py","scripts/reference_reconstruction.py","scripts/verify_m5.py","scripts/review_pie.py",
        "tests/test_m6_contracts.py","docs/03-case-studies-and-evaluation.md","docs/12-m6-delivery.md","data/milestones.json","data/kuki-chin/README.md","data/cross-branch/README.md",
        "reviews/sino-tibetan-signoff.md","reviews/sino-tibetan-packet.json","reviews/sino-tibetan-responses.json","reports/sino-tibetan-benchmark-local.json","lean/lakefile.toml",".github/workflows/ci.yml"]
    paths += [ROOT/n for n in names]
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}


def summary(corpus,design,executions,artifacts):
    current=packet();assert json.loads(PACKET.read_text())==current,"Stale M6 specialist packet"
    review=assess(current,json.loads(RESPONSE.read_text()))
    assert json.loads((ROOT/"reports/sino-tibetan-review.json").read_text())==review,"Stale specialist status report"
    ds=json.loads((ROOT/"data/cross-branch/dossiers.json").read_text())["dossiers"]
    assert len(ds)==30 and all(len(d["analyses"])>=2 and d["discriminating_evidence"] and d["non_discriminating_evidence"] for d in ds)
    assert all(len({e["branch"] for e in d["evidence"]})>=2 for d in ds),"A purported cross-branch dossier has only one branch"
    assert all(s["node_id"]=="vanbik-2009-PKC" and len({r["branch"] for r in s["records"]})>=2 for s in corpus["sets"])
    counts=dict(sets=len(corpus["sets"]),reflex_records=sum(len(s["records"]) for s in corpus["sets"]),
        distinct_set_variety_form_triples=len({(s["id"],r["doculect_id"],r["source_form"]) for s in corpus["sets"] for r in s["records"]}),
        core_sets=sum(s["core"] for s in corpus["sets"]),core_reflexes=sum(len(s["records"]) for s in corpus["sets"] if s["core"]),cross_branch_dossiers=len(ds),
        unresolved_dossiers=sum(d["outcome"]=="unresolved" for d in ds),rejected_source_comparisons=sum(d["outcome"]=="rejected-in-primary-source" for d in ds),
        forward_certificates=sum(len(e["result"]["forward"]) for k,e in executions.items() if k!="joint"),
        finite_pool_queries=sum(len(e["result"]["inverse"]) for k,e in executions.items() if k!="joint"),
        joint_analysis_candidates=len(executions["joint"]["candidates"]))
    assert counts["sets"]>=100 and counts["reflex_records"]>=300 and counts["core_sets"]==50 and counts["core_reflexes"]>=150 and counts["unresolved_dossiers"]>=10
    benchmark=json.loads((ROOT/"reports/sino-tibetan-benchmark-local.json").read_text());assert benchmark["passed"] and benchmark["certificates"]==1000
    for name,h in benchmark["input_hashes"].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,"Stale M6 benchmark: "+name
    return dict(milestone="M6",status="delivered" if review["passed"] else "in_review",engineering_passed=True,all_deliverables_accepted=review["passed"],
        label="linguistically validated" if review["passed"] else "computationally checked, linguistically unreviewed",counts=counts,
        criteria=[dict(id="M6-core",status="passed" if review["passed"] else "awaiting-specialist-review",evidence="50 source-located core sets, strict evidence checks, source-preserving alignments, normalization and complete outcome records; human review remains required"),
            dict(id="M6-scale",status="passed",evidence="100 sets and 580 reflex records; all unsupported and mismatching records retained"),
            dict(id="M6-cross-branch",status="passed",evidence="30 dossiers distinguish written/transcribed evidence, reconstructions, morphology, competing analyses and unresolved outcomes"),
            dict(id="M6-sensitivity",status="passed",evidence="Source-qualified scopes, conditional topology assumptions, coverage sensitivity, explicit counterexamples and indistinguishable whole paradigms"),
            dict(id="M6-signoff",status="passed" if review["passed"] else "pending",evidence="Independent human specialist review of the 50 core sets and 30 cross-branch dossiers has not been supplied" if not review["passed"] else "Independent specialist assessment supplied")],
        lexical=metrics(corpus,design,executions["lexical"]),sensitivity=sensitivity(corpus,design,executions["lexical"],executions["diagnostic"],executions["joint"]),
        leakage=check_leakage(corpus,design),review=review,benchmark=benchmark,**artifacts,
        proof_audit=dict(declarations=137,new_scope_theorems=4,project_axioms=False,proof_placeholders=False),
        limitations=["The core transcriptions and etymological claims are not independently reviewed.","Learned mappings operate on transcription graphemes, exclude tone and provide no chronological sound-law account.",
            "Cross-branch rule fragments reproduce specified features. Several dossiers are documentary rather than executable full derivations.","Some rival accounts are available only through the primary paper's discussion; their original publications have not all been independently checked.",
            "The data do not identify a unique Proto-Sino-Tibetan system or family topology."],input_hashes=input_hashes())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--audit",type=Path,default=ROOT/"reports/lean-axioms-local.txt");p.add_argument("--check-report",action="store_true");p.add_argument("--require-complete",action="store_true");p.add_argument("--prepare-review",action="store_true");a=p.parse_args()
    generated_check();corpus=json.loads((DEST/"corpus.json").read_text());design=json.loads((DEST/"experiment.json").read_text())
    if not a.check_report:subprocess.run([sys.executable,str(ROOT/"scripts/check_proofs.py"),str(a.audit)],check=True,cwd=ROOT)
    executions={}
    for name in ["lexical","diagnostic","joint"]:
        inp=DEST/("joint-analysis-input.json" if name=="joint" else name+"-input.json");out=ROOT/("reports/sino-tibetan-"+name+"-execution.json")
        request=json.loads(inp.read_text())
        if a.check_report:result=json.loads(out.read_text())
        elif name=="joint":result=invoke(ROOT/"lean/.lake/build/bin/reconstruct",["--file",str(inp)])
        else:result=invoke(BINARY,["--batch",str(inp)])
        if name=="joint":assert result==evaluate(request),"Joint paradigm differs from independent enumeration"
        else:verify_execution(request,result)
        executions[name]=result
        if not a.check_report:out.write_bytes(encoded(result))
        print("M6",name,"Lean/Python agreement",flush=True)
    if a.check_report:
        previous=json.loads(REPORT.read_text());artifacts={k:previous[k] for k in ["evidence","alignments","adversarial"]}
    else:artifacts=dict(evidence=evidence_checks(),alignments=alignment_checks(),adversarial=adversarial_checks())
    if a.prepare_review:
        assert not RESPONSE.exists() or json.loads(RESPONSE.read_text()).get("status")=="pending","Do not replace a reviewed packet without obtaining a new assessment"
        subprocess.run([sys.executable,str(ROOT/"scripts/review_sino_tibetan.py"),"--prepare"],check=True,cwd=ROOT)
    result=summary(corpus,design,executions,artifacts)
    milestone=next(m for m in json.loads((ROOT/"data/milestones.json").read_text()) if m["id"]=="M6")
    assert milestone["status"]==result["status"] and {c["id"] for c in milestone["acceptance"]}=={c["id"] for c in result["criteria"]}
    for name in milestone["artifacts"]:
        if name!="reports/sino-tibetan-evaluation.json" or a.check_report:assert (ROOT/name).exists(),"Missing M6 artifact: "+name
    if a.check_report:assert json.loads(REPORT.read_text())==result,"Stale M6 report"
    else:REPORT.write_bytes(encoded(result))
    print("M6:",result["label"],json.dumps(result["counts"],sort_keys=True))
    if a.require_complete and not result["all_deliverables_accepted"]:raise SystemExit(1)


if __name__=="__main__":main()
