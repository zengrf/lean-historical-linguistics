"""Freeze and execute a separate attested-Latin / Romance control.

The source Latin variety is retained verbatim. No claim that literary Latin is
the exact spoken ancestor, or that loans automatically become inherited forms.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json

from build_pie_corpus import DEST, UPSTREAM, table, family_groups, encoded, digest
from build_pie_experiment import align, package, compile_map


def freeze():
    forms,languages,sets,cognates=[table(n) for n in ["forms","languages","cognatesets","cognates"]]
    groups=family_groups(sets,cognates,forms);by=defaultdict(list)
    for c in cognates.values():by[c["Cognateset_ID"]].append(forms[c["Form_ID"]])
    samples=[]
    for sid in sorted(sets,key=int):
        rows=by[sid]
        good=lambda f: f["Phonemic_Segments"] and not any(x in f["Value"]+f["Phonemic_Segments"] for x in "?*#/_")
        lat=[f for f in rows if f["Language_ID"]=="112" and good(f)]
        rom=[f for f in rows if languages[f["Language_ID"]]["Clade"]=="Italic;Roman" and
             f["Language_ID"]!="112" and languages[f["Language_ID"]]["historical"]=="false" and good(f)]
        rom=sorted(rom,key=lambda f:(int(f["Language_ID"]),f["ID"]))
        chosen={}
        for f in rom:chosen.setdefault(f["Language_ID"],f)
        if lat and len(chosen)>=3:
            samples.append(dict(id=sid,family_id=groups[sid],latin=lat[0],latin_variety=languages["112"],
                                daughters=list(chosen.values())[:3],raw_cognateset=sets[sid],
                                daughter_varieties=[languages[k] for k in list(chosen)[:3]]))
        if len(samples)==20:break
    families=sorted({s["family_id"] for s in samples},key=lambda s:hashlib.sha256(("m5-latin-v1:"+s).encode()).hexdigest())
    cut1,cut2=round(len(families)*.6),round(len(families)*.8)
    assign={f:"train" if i<cut1 else "development" if i<cut2 else "test" for i,f in enumerate(families)}
    for s in samples:s["split"]=assign[s["family_id"]]
    return dict(schema_version="1.0.0",id="latin-romance-control-v1",policy="First 20 numeric cognate-set IDs with a segmented attested Latin row and three segmented modern Romance varieties. First source language IDs; no outcomes consulted.",
                provenance="Same pinned IE-CoR snapshot as the PIE sample; exact forms.csv and cognatesets.csv IDs retained in every row.",
                relationship_to_pie="A separate control, not additional PIE sets or independent family-transfer evidence. Lexical families may overlap the PIE corpus; its parameters are fitted separately.",
                ancestor_status="Latin is source-attested; its phonemic interpretation is the dataset's analysis. Literary Latin is not asserted to be the exact spoken ancestor of these varieties.",
                inheritance="Source cognacy, loan and uncertainty annotations remain in the raw cognate-set record; no inherited-only claim is made.",samples=samples)


def generate(frozen):
    with (UPSTREAM/"cldf/loans.csv").open(newline="") as f:
        loans=list(csv.DictReader(f))
    loan_annotations={s["id"]:dict(
        set_links=[r for r in loans if r["Cognateset_ID"]==s["id"] or r["SourceCognateset_ID"]==s["id"]],
        form_flags={r["ID"]:r["Loan"] for r in [s["latin"]]+s["daughters"]},
        inheritance_status="source-cognacy claim; inherited-versus-learned status independently unreviewed") for s in frozen["samples"]}
    inventory=sorted({t for s in frozen["samples"] for f in [s["latin"]]+s["daughters"] for t in f["Phonemic_Segments"].split() if t!="+"})
    counts=defaultdict(lambda:defaultdict(Counter));training=[]
    for s in frozen["samples"]:
        if s["split"]!="train":continue
        for f in s["daughters"]:
            a=s["latin"]["Phonemic_Segments"].split();b=f["Phonemic_Segments"].split()
            training.append(dict(set_id=s["id"],family_id=s["family_id"],latin_row=s["latin"]["ID"],daughter_row=f["ID"],input=a,output=b))
            for x,y in align(a,b):
                if x is not None and x!="+":counts[f["Language_ID"]][x][y]+=1
    mappings={d:{a:sorted(cs,key=lambda b:(-cs[b],b!=a,"" if b is None else b))[0] for a,cs in ds.items()} for d,ds in counts.items()}
    docs=sorted({f["Language_ID"] for s in frozen["samples"] for f in s["daughters"]})
    ps=[package("latin-identity",[],inventory,"Attested-ancestor no-change control; not a sound-law account.")]
    ps += [compile_map("latin-correspondence-"+d,mappings.get(d,{}),inventory) for d in docs]
    pool=[list(w) for w in dict.fromkeys(tuple(s["latin"]["Phonemic_Segments"].split()) for s in frozen["samples"])]
    forward=[];inverse=[]
    for s in frozen["samples"]:
        w=s["latin"]["Phonemic_Segments"].split()
        for model in ["identity","correspondence"]:
            branches=[]
            for f in s["daughters"]:
                pid="latin-identity" if model=="identity" else "latin-correspondence-"+f["Language_ID"]
                expected=f["Phonemic_Segments"].split()
                forward.append(dict(id=f"latin-{s['id']}-{f['ID']}-{model}",package_id=pid,input=w,expected=expected))
                branches.append(dict(doculect_id="romance-"+f["Language_ID"],package_id=pid,expected=expected))
            inverse.append(dict(id=f"latin-{s['id']}-{model}",pool=pool,reference=[w],branches=branches))
    return dict(schema_version="1.0.0",id="latin-romance-control-v1",packages=ps,forward=forward,inverse=inverse),dict(
        frozen_sha256=digest(frozen),training_examples=training,training_sha256=digest(training),mappings=mappings,
        loan_annotations_by_set=loan_annotations,
        metadata_clarification="The frozen manifest's inheritance note refers to source annotations generally. Loan-table links are separate from cognatesets.csv and are explicitly projected here; an absent loan flag does not prove inheritance.",
        scope="Retrospective closed-set recovery of the held-out Latin target from Romance query rows. The declared pool includes all 20 Latin labels; this is not open-vocabulary reconstruction. Latin observations are absent from inverse branches.")


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--freeze",action="store_true");p.add_argument("--check",action="store_true");a=p.parse_args()
    frozen=freeze();f=DEST/"latin-control-frozen.json"
    if a.freeze:
        if f.exists() and f.read_bytes()!=encoded(frozen):raise ValueError("Frozen Latin control changed")
        f.write_bytes(encoded(frozen));print("Frozen 20 Latin/Romance control sets before fitting their models");return
    assert f.read_bytes()==encoded(frozen),"Freeze the Latin control first"
    request,design=generate(frozen)
    for name,obj in [("latin-control-input.json",request),("latin-control-design.json",design)]:
        path=DEST/name
        if a.check:assert path.read_bytes()==encoded(obj),"Stale control: "+name
        else:path.write_bytes(encoded(obj))
    print("Latin control: 20 source-attested targets, 60 daughter records, 120 forward jobs and 40 inverse queries")


if __name__=="__main__":main()
