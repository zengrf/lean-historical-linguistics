"""Browse complete retained comparative datasets without changing their analyses.

Source-qualified IDs remain separate across datasets. Original rows, including
uninterpreted columns, are returned verbatim. No cognacy is inferred here.
"""
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path

from build_pie_corpus import ROOT, encoded
from import_cldf import check_snapshot

DEST = ROOT / "data/materials"
CLDF = ("iecor", "hillburmish", "sagartst")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(dataset, table):
    if dataset not in CLDF:
        raise ValueError("Unknown CLDF dataset")
    path = ROOT / "data/upstream" / dataset / "cldf" / (table + ".csv")
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as stream:
        result = list(csv.DictReader(stream))
    if any(None in r or any(v is None for v in r.values()) for r in result):
        raise ValueError("Ragged source table: " + str(path))
    if result and "ID" in result[0] and len({r["ID"] for r in result}) != len(result):
        raise ValueError("Duplicate source row ID: " + str(path))
    return result


def coverage():
    locks = read(ROOT / "data/upstream/manifest.json") + read(DEST / "sources.json")
    result = {}
    for source in locks:
        dataset = source["id"]
        check_snapshot(ROOT / "data/upstream" / dataset, source)
        forms, languages, meanings, cognates, sets = [rows(dataset, t) for t in
            ("forms", "languages", "parameters", "cognates", "cognatesets")]
        lang = {r["ID"]: r for r in languages}
        form_ids = {r["ID"] for r in forms}
        meaning_ids = {r["ID"] for r in meanings}
        set_ids = {s["ID"] for s in sets}
        if any(f["Language_ID"] not in lang or f["Parameter_ID"] not in meaning_ids for f in forms):
            raise ValueError("Dangling language/concept reference")
        if any(c["Form_ID"] not in form_ids for c in cognates):
            raise ValueError("Dangling cognate form reference")
        if sets and any(c["Cognateset_ID"] not in set_ids for c in cognates):
            raise ValueError("Dangling cognate set reference")
        counts = Counter(f["Language_ID"] for f in forms)
        groups = defaultdict(lambda: dict(varieties=0, forms=0))
        for l in languages:
            group = l.get("Clade", "").split(";")[0] or l.get("SubGroup") or "source-unclassified"
            groups[group]["varieties"] += 1
            groups[group]["forms"] += counts[l["ID"]]
        result[dataset] = dict(repository=source["repository"], commit=source["commit"],
            license=source["license"], forms=len(forms), varieties=len(languages), concepts=len(meanings),
            cognate_judgments=len(cognates), cognate_sets=len(sets) if sets else len({c["Cognateset_ID"] for c in cognates}),
            forms_with_embedded_cognacy=sum(bool(f.get("Cognacy") or f.get("Partial_Cognacy")) for f in forms),
            source_groups=dict(sorted(groups.items())),
            varieties_with_counts=[dict(id=l["ID"], name=l["Name"], forms=counts[l["ID"]]) for l in languages],
            table_rows={p.stem: len(rows(dataset, p.stem)) for p in sorted((ROOT / "data/upstream" / dataset / "cldf").glob("*.csv"))},
            scope="All retained CLDF rows; source subgroup labels do not assert a family tree.")
    vb = read(DEST / "vanbik-initials.json")
    result["vanbik2009"] = dict(entries=len(vb["entries"]), reflex_records=sum(len(e["records"]) for e in vb["entries"]),
        varieties=len({r["doculect_id"] for e in vb["entries"] for r in e["records"]}),
        source_levels=dict(Counter(e["source_level"] for e in vb["entries"])),
        extraction_omissions=len(vb["omissions"]), scope=vb["scope"], source_sha256=vb["source_sha256"])
    return dict(schema_version="1.0.0", datasets=result,
        limitations=["Coverage is complete for the three pinned CLDF snapshots, not for either language family.",
            "VanBik extraction covers the initial-consonant chapter only; omissions and unreviewed transcriptions are retained.",
            "Published forms and cognacy judgments are evidence inputs, not newly verified reconstructions.",
            "Forms in different datasets may overlap. Totals are source records, not deduplicated lexemes.",
            "Most expanded records have no executable sound-change model; the hypothesis explorer lists the supported cases."])


def search(dataset, query="", language=None, concept=None, set_id=None):
    if dataset == "vanbik2009":
        for e in read(DEST / "vanbik-initials.json")["entries"]:
            if set_id is not None and e["id"] != set_id:
                continue
            for r in e["records"]:
                if language and language != r["doculect_id"]:
                    continue
                if concept and concept != e["label"]:
                    continue
                if query.casefold() in json.dumps([e["label"], e["source_reconstruction"], r], ensure_ascii=False).casefold():
                    yield dict(id="vanbik2009:" + r["id"], dataset=dataset, entry_id=e["id"],
                        source_level=e["source_level"], source_reconstruction=e["source_reconstruction"],
                        entry_extraction=e["extraction"], source_row=r)
        return
    languages = {r["ID"]: r for r in rows(dataset, "languages")}
    meanings = {r["ID"]: r for r in rows(dataset, "parameters")}
    judgments = defaultdict(list)
    sets = {r["ID"]: r for r in rows(dataset, "cognatesets")}
    loans = defaultdict(list)
    for r in rows(dataset, "loans"):
        loans[r["Cognateset_ID"]].append(r)
    for r in rows(dataset, "cognates"):
        judgments[r["Form_ID"]].append(r)
    for r in rows(dataset, "forms"):
        if language and r["Language_ID"] != language:
            continue
        if concept and r["Parameter_ID"] != concept:
            continue
        if set_id is not None and not any(c["Cognateset_ID"] == set_id for c in judgments[r["ID"]]):
            continue
        l, m = languages[r["Language_ID"]], meanings[r["Parameter_ID"]]
        if query.casefold() not in json.dumps([r, l, m], ensure_ascii=False).casefold():
            continue
        yield dict(id=dataset + ":" + r["ID"], dataset=dataset,
            source_locator=f"data/upstream/{dataset}/cldf/forms.csv#ID={r['ID']}",
            source_row=r, language=l, concept=m, cognate_judgments=judgments[r["ID"]],
            source_cognate_sets=[sets[c["Cognateset_ID"]] for c in judgments[r["ID"]]] if sets else [],
            source_loan_events=[event for c in judgments[r["ID"]] for event in loans[c["Cognateset_ID"]]],
            representation_note="Source transcription/analysis; no blanket attestation status is assigned. ProtoBurmish is reconstructed; Old Chinese and Tangut pronunciation transcriptions also require their source analyses.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("coverage")
    table = sub.add_parser("table", help="Read any retained source table, including reconstruction claims and loans")
    table.add_argument("--dataset", required=True, choices=CLDF)
    table.add_argument("--table", required=True, choices=["forms", "languages", "parameters", "cognates", "cognatesets", "loans", "clades", "authors"])
    table.add_argument("--id")
    table.add_argument("--limit", type=int, default=20, help="0 returns every row")
    find = sub.add_parser("search")
    find.add_argument("--dataset", required=True, choices=(*CLDF, "vanbik2009"))
    find.add_argument("--text", default="")
    find.add_argument("--language")
    find.add_argument("--concept")
    find.add_argument("--set", dest="set_id")
    find.add_argument("--limit", type=int, default=20, help="0 returns every match")
    args = parser.parse_args()
    if args.command == "coverage":
        out = coverage()
    else:
        if args.limit < 0:
            parser.error("--limit must be nonnegative")
        if args.command == "table":
            found = rows(args.dataset, args.table)
            if args.id is not None:
                found = [r for r in found if r.get("ID") == args.id]
        else:
            if args.dataset == "hillburmish" and args.set_id is not None:
                parser.error("Burmish cognacy is embedded in source columns, not a separate set table; inspect those columns without inventing set IDs")
            found = list(search(args.dataset, args.text, args.language, args.concept, args.set_id))
        out = dict(total=len(found), returned=len(found) if not args.limit else min(len(found), args.limit),
            truncated=bool(args.limit and len(found) > args.limit), records=found[:args.limit] if args.limit else found)
    print(encoded(out).decode(), end="")


if __name__ == "__main__":
    main()
