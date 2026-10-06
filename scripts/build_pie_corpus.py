"""Freeze a source-backed PIE sample and conservative lexical-family splits.

Selection uses source metadata only. No rule execution, predictions or outcomes
enter selection or split assignment. The upstream snapshot remains unchanged.
"""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from import_cldf import check_snapshot

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/pie"
UPSTREAM = ROOT / "data/upstream/iecor"
CORE = ["21", "39", "44", "82", "86", "131", "146", "153", "210", "219",
        "225", "335", "342", "384", "411", "519", "859", "2456", "2457", "6458"]
SEED = "m5-iecor-lexical-families-v1"


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def table(name):
    with (UPSTREAM / "cldf" / (name + ".csv")).open(newline="") as f:
        return {r["ID"]: r for r in csv.DictReader(f)}


def root_keys(text):
    # Conservative grouping, NOT phonological normalization or proto inference.
    # Accent, length and formatting differences cannot create separate splits.
    text = text.replace("u̯", "w").replace("i̯", "y").replace("₁", "1").replace("₂", "2").replace("₃", "3")
    text = "".join(c for c in unicodedata.normalize("NFD", text.lower()) if not unicodedata.combining(c))
    return {re.sub(r"[^a-z0-9ʰʷ]", "", s) for s in re.split(r"[,~/;]", text)} - {""}


def family_groups(sets, cognates, forms):
    parent = {sid: sid for sid in sets}

    def find(s):
        while parent[s] != s:
            parent[s] = parent[parent[s]]; s = parent[s]
        return s

    def union(a, b):
        if a in parent and b in parent:
            x, y = find(a), find(b)
            if x != y:
                lo, hi = sorted([x, y], key=int); parent[hi] = lo

    roots = {}; row_owner = {}; surface_owner = {}
    for sid, s in sets.items():
        for field in ["supersetid", "proposedAsCognateTo_pk"]:
            for target in re.findall(r"\d+", s[field]):
                union(sid, target)
        for key in root_keys(s["Root_Form"]):
            key = (s["Root_Language"], key)
            if key in roots: union(sid, roots[key])
            roots[key] = sid
    for c in cognates.values():
        sid = c["Cognateset_ID"]; fid = c["Form_ID"]; f = forms[fid]
        if fid in row_owner: union(sid, row_owner[fid])
        row_owner[fid] = sid
        # Even possible homonyms stay together: this errs toward less leakage.
        for surface in [f["Value"], f["Form"]]:
            if not surface: continue
            key = (f["Language_ID"], unicodedata.normalize("NFC", surface))
            if key in surface_owner: union(sid, surface_owner[key])
            surface_owner[key] = sid
    return {sid: "family-" + find(sid) for sid in sets}


def generate():
    lock = next(x for x in json.loads((ROOT / "data/upstream/manifest.json").read_text()) if x["id"] == "iecor")
    check_snapshot(UPSTREAM, lock)
    forms, languages, sets, cognates, meanings = [table(n) for n in ["forms", "languages", "cognatesets", "cognates", "parameters"]]
    by_set = defaultdict(list)
    for c in cognates.values(): by_set[c["Cognateset_ID"]].append(c)
    with (UPSTREAM / "cldf/loans.csv").open(newline="") as f: loans = list(csv.DictReader(f))
    groups = family_groups(sets, cognates, forms)

    def branch(c): return languages[forms[c["Form_ID"]]["Language_ID"]]["Clade"].split(";")[0]
    def eligible(c):
        value = forms[c["Form_ID"]]["Value"]
        return bool(value) and "*" not in value
    eligible_sets = [sid for sid, s in sets.items() if s["Root_Language"] == "Proto-Indo-European" and s["Root_Form"]
                     and len([c for c in by_set[sid] if eligible(c)]) >= 3
                     and len({branch(c) for c in by_set[sid] if eligible(c)}) >= 2]
    assert set(CORE) <= set(eligible_sets)
    selected = sorted(set(CORE + [s for s in sorted(eligible_sets, key=int) if s not in CORE][:180]), key=int)
    assert len(selected) == 200
    selected_cognates = {}; excluded = []; sampled = []
    for sid in selected:
        candidates = [c for c in by_set[sid] if eligible(c)]
        def priority(c):
            l = languages[forms[c["Form_ID"]]["Language_ID"]]
            return (l["historical"] != "true", int(l["ID"]), int(c["ID"]))
        candidates.sort(key=priority)
        chosen = []; seen = set()
        for c in candidates:
            if branch(c) not in seen:
                chosen.append(c); seen.add(branch(c))
        for c in candidates:
            if len(chosen) >= 3: break
            if c not in chosen: chosen.append(c)
        chosen_languages = {forms[c["Form_ID"]]["Language_ID"] for c in chosen}
        # Keep every source variant within the selected languages and set.
        chosen = [c for c in candidates if forms[c["Form_ID"]]["Language_ID"] in chosen_languages]
        chosen.sort(key=lambda c: int(c["ID"]))
        selected_cognates[sid] = [c["ID"] for c in chosen]
        for c in by_set[sid]:
            if not eligible(c):
                excluded.append(dict(set_id=sid, cognate_id=c["ID"], form_id=c["Form_ID"],
                                     reason="missing-form" if not forms[c["Form_ID"]]["Value"] else "source-marked-reconstruction",
                                     raw_form=forms[c["Form_ID"]]))
            elif c not in chosen:
                sampled.append(dict(set_id=sid, cognate_id=c["ID"], form_id=c["Form_ID"], reason="outside-frozen-language-sample"))
    family_ids = sorted({groups[sid] for sid in selected})
    order = sorted(family_ids, key=lambda f: hashlib.sha256((SEED + ":" + f).encode()).hexdigest())
    n = len(order); cuts = (round(n * .6), round(n * .8))
    assignment = {f: "train" if i < cuts[0] else "development" if i < cuts[1] else "test" for i, f in enumerate(order)}
    selection = dict(schema_version="1.0.0", upstream_commit=lock["commit"], core_set_ids=CORE,
                     set_ids=selected, cognate_ids_by_set=selected_cognates,
                     policy="20 declared comparative core sets plus the first 180 other eligible IDs. At least two first-level clades and three source-attested rows; earliest historical flag then source language ID per clade, with all its variants retained. No predictions are consulted.",
                     eligible_set_count=len(eligible_sets), excluded_records=excluded, unsampled_records=sampled)
    splits = dict(schema_version="1.0.0", seed=SEED, selection_sha256=digest(selection),
                  upstream_commit=lock["commit"], frozen_before_model_revision=True,
                  evaluation_kind="retrospective-grouped-evaluation; not a blind historical discovery test",
                  grouping="Transitive closure over the entire upstream dataset: superset/proposed-cognacy edges, normalized source root alternatives within a reconstruction level, shared form IDs, and identical spellings within a doculect. Possible homonyms are conservatively joined. Unrecorded semantic family relations still require specialist review.",
                  assignments=[dict(set_id=sid, family_id=groups[sid], split=assignment[groups[sid]]) for sid in selected],
                  family_counts={split: sum(x == split for x in assignment.values()) for split in ["train", "development", "test"]})
    corpus = dict(schema_version="1.0.0", source_kind="sourced", dataset="iecor", upstream_commit=lock["commit"],
                  license=lock["license"], selection_sha256=digest(selection), splits_sha256=digest(splits),
                  source_files=lock["files"], sets=[])
    for sid in selected:
        s = sets[sid]; records = []
        for cid in selected_cognates[sid]:
            c = cognates[cid]; f = forms[c["Form_ID"]]; l = languages[f["Language_ID"]]
            records.append(dict(id="iecor-form-" + f["ID"], source_locator="cldf/forms.csv#" + f["ID"],
                                judgment_locator="cldf/cognates.csv#" + cid, raw_form=f, raw_judgment=c,
                                raw_language=l, raw_meaning=meanings[f["Parameter_ID"]],
                                branch=branch(c), attestation="attested-as-recorded-in-source", date_range=None,
                                normalization=dict(method="upstream-phonemic-segments-v1", original=f["Value"],
                                                   intermediate=f["Phonemic"], tokens=f["Phonemic_Segments"].split() or None,
                                                   phonetic_tokens=f["Segments"].split() or None,
                                                   policy="Keep both source tokenizations verbatim; absent segmentation stays absent. No silent transliteration or phonetic inference."),
                                uncertainty=dict(source_comment=f["Comment"], source_doubt=c["Doubt"],
                                                 reading_markers=any(ch in f["Value"] for ch in ["?", "/", "~", "("]),
                                                 row_bibliography_missing=not f["Source"], specialist_review="pending")))
        corpus["sets"].append(dict(id=sid, core=sid in CORE, source_locator="cldf/cognatesets.csv#" + sid,
                                   raw_cognateset=s, reconstruction=dict(status="published-reconstruction-claim", node=s["Root_Language"], original=s["Root_Form"], source=s["Source"]),
                                   family_id=groups[sid], split=assignment[groups[sid]], records=records,
                                   loans=[x for x in loans if x["Cognateset_ID"] == sid],
                                   derivation_scope="No full chronological derivation supplied by IE-CoR. The experiment records partial-baseline predictions and failures; source-defined diagnostics are separate.",
                                   morphology_status="Source root and lexical forms retained; inflection/derivation is unresolved unless a separate dossier supplies it."))
    assert sum(len(s["records"]) for s in corpus["sets"]) >= 600
    evidence = make_evidence(corpus, lock)
    return {"selection.json": selection, "splits.json": splits, "corpus.json": corpus, "evidence.json": evidence}


def make_evidence(corpus, lock):
    """M1 projection is explicitly orthographic; no character is inferred as a phone."""
    records = {}; langs = {}; meanings = {}
    for s in corpus["sets"]:
        for r in s["records"]:
            f = r["raw_form"]; l = r["raw_language"]; m = r["raw_meaning"]
            langs[l["ID"]] = l; meanings[m["ID"]] = m
            records[f["ID"]] = dict(id="form-" + f["ID"], doculect_id="doc-" + l["ID"], meaning_ids=["meaning-" + m["ID"]],
                representation="orthographic", attestation="attested", evidence_state="present", analysis_id=None, proto_node_id=None,
                citations=[dict(source_id="iecor", locator=r["source_locator"])],
                readings=[dict(id="source-orthography", original=f["Value"], normalized=f["Value"],
                               cells=[dict(kind="segment", value=c) for c in f["Value"]],
                               normalization=[dict(method_id="identity-orthography", method_version="1", input=f["Value"], output=f["Value"],
                                                   reason="Retain every source character without phonological interpretation")], choices=[])],
                uncertain=True, uncertainty_note="Source spelling retained, including any alternatives. Row-level bibliography and specialist transcription review are absent; these character cells are not phonological observations.",
                imported_from=dict(dataset_id="iecor", table="forms.csv", row_id=f["ID"], id_column="ID", original_column="Value",
                                   raw_columns=[dict(name=k, value=v) for k, v in f.items()]))
    return dict(schema_version="1.0.0", id="pie-m5-evidence", description="Lossless M1 orthographic evidence projection of the frozen PIE pilot; not a phonological analysis.",
        sources=[dict(id="iecor", title="Heggarty, Anderson and Scarborough: Indo-European Cognate Relationships database", url=lock["repository"] + "/tree/" + lock["commit"],
                      version=lock["commit"], license=lock["license"], kind="dataset", sha256=next(f["sha256"] for f in lock["files"] if f["path"] == "cldf/forms.csv"))],
        doculects=[dict(id="doc-"+lid, name=l["Name"], family="Indo-European", stage=l["Variety"] or "As distinguished by the source; date unspecified", kind="attested", date_range=None) for lid,l in sorted(langs.items())],
        meanings=[dict(id="meaning-"+mid, label=m["Name"]) for mid,m in sorted(meanings.items())],
        analyses=[], normalization_methods=[dict(id="identity-orthography", version="1", description="Exact identity of source orthography; code points are display cells, not inferred phonemes")],
        choice_groups=[], records=list(records.values()))


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("--check", action="store_true"); args = p.parse_args()
    generated = generate(); DEST.mkdir(parents=True, exist_ok=True)
    for name, value in generated.items():
        path = DEST / name; data = encoded(value)
        if args.check:
            assert path.read_bytes() == data, "Changed frozen corpus/split: " + name
        else:
            if name != "evidence.json" and path.exists() and path.read_bytes() != data:
                raise ValueError("Frozen input changed; create a new explicitly versioned study instead: " + name)
            path.write_bytes(data)
    c = generated["corpus.json"]
    print(f"PIE: {len(c['sets'])} sets, {sum(len(s['records']) for s in c['sets'])} set/reflex memberships, {len(generated['evidence.json']['records'])} distinct form rows; splits frozen")


if __name__ == "__main__": main()
