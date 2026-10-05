"""Import an explicitly selected CLDF Wordlist subset without losing source rows.

All column names come from CLDF property URLs. Uninterpreted fields/tables remain
in the pinned snapshot and are listed in the report. No remote data are fetched.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from pycldf import Dataset

ROOT = Path(__file__).resolve().parents[1]
TERMS = "http://cldf.clld.org/v1.0/terms.rdf#"


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def check_snapshot(root, lock):
    declared = [item["path"] for item in lock["files"]]
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
    if len(declared) != len(set(declared)) or set(declared) != actual:
        # Check path containment first so traversal has an unambiguous error.
        if any(not (root / p).resolve().is_relative_to(root.resolve()) for p in declared):
            raise ValueError("Snapshot path escapes its directory")
        raise ValueError("Snapshot file set differs from the pinned manifest")
    for item in lock["files"]:
        path = (root / item["path"]).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Snapshot path escapes its directory")
        data = path.read_bytes()
        if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError(f"Snapshot hash mismatch: {item['path']}")


def table_info(ds, name):
    table = ds[name]
    path = (ds.directory / str(table.url)).resolve()
    if not path.is_relative_to(ds.directory.resolve()):
        raise ValueError("Only local tables inside the snapshot are supported")
    props = {}
    for col in table.tableSchema.columns:
        prop = str(col.propertyUrl)
        if prop.startswith(TERMS):
            key = prop[len(TERMS):]
            if key in props:
                raise ValueError(f"Ambiguous CLDF property: {key}")
            props[key] = col.name
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("Duplicate CSV header")
        raw = list(reader)
        headers = reader.fieldnames
    if any(None in r or any(v is None for v in r.values()) for r in raw):
        raise ValueError("Ragged CSV rows")
    id_col = props["id"]
    by = {r[id_col]: r for r in raw}
    if len(by) != len(raw):
        raise ValueError("Duplicate source row ID")
    return table, props, by, headers


def make_dossier(name, lock, selection, source_root):
    check_snapshot(source_root, lock)
    metadata = source_root / "cldf/cldf-metadata.json"
    ds = Dataset.from_metadata(metadata)
    if ds.module != "Wordlist":
        raise ValueError("Only CLDF Wordlist is supported")
    if not ds.validate():
        raise ValueError("Upstream CLDF validation failed")
    table, cols, raw, headers = table_info(ds, "FormTable")
    _, lc, languages, _ = table_info(ds, "LanguageTable")
    _, pc, meanings, _ = table_info(ds, "ParameterTable")
    required = {"id", "languageReference", "parameterReference", "value", "form", "segments"}
    if not required <= cols.keys():
        raise ValueError("This adapter requires original Value, Form, Segments and explicit references")
    ids = selection["row_ids"]
    if not ids or len(ids) != len(set(ids)) or not set(ids) <= raw.keys():
        raise ValueError("Selection must contain distinct existing row IDs")
    overrides = selection.get("uncertainty_overrides", {})
    if not isinstance(overrides, dict) or not set(overrides) <= set(ids) or not all(
            isinstance(note, str) and note.strip() for note in overrides.values()):
        raise ValueError("Editorial uncertainty overrides require selected row IDs and nonempty reasons")
    # Use the CLDF parser to respect declared separators and null values.
    parsed = {r[cols["id"]]: r for r in ds["FormTable"]}
    prefix = name + ":"
    source_id = prefix + "snapshot"
    doculect_ids = list(dict.fromkeys(raw[i][cols["languageReference"]] for i in ids))
    meaning_ids = list(dict.fromkeys(raw[i][cols["parameterReference"]] for i in ids))
    proto = set(selection["proto_language_ids"])
    if not proto <= languages.keys():
        raise ValueError("Configured proto-language ID is absent from the dataset")
    forms_hash = next(x["sha256"] for x in lock["files"] if x["path"] == "cldf/" + str(table.url))
    d = {
        "schema_version": "1.0.0", "id": name + "-m1",
        "description": "M1 representation/import pilot. Published data claims are retained; no historical reconstruction is verified here.",
        "sources": [{"id": source_id, "title": ds.properties.get("dc:bibliographicCitation", ds.properties["dc:title"]),
                     "url": lock["repository"] + "/tree/" + lock["commit"], "version": lock["commit"],
                     "license": lock["license"], "kind": "dataset", "sha256": forms_hash}],
        "doculects": [{"id": prefix + lid, "name": languages[lid][lc["name"]],
                       "family": selection["family"], "stage": "As distinguished in the pinned dataset; date unspecified",
                       "kind": "proto" if lid in proto else "attested", "date_range": None} for lid in doculect_ids],
        "meanings": [{"id": prefix + mid, "label": meanings[mid][pc["name"]]} for mid in meaning_ids],
        "analyses": [{"id": prefix + "analysis:" + lid, "description": "Published reconstruction attributed to the pinned dataset, not independently validated",
                      "source_ids": [source_id], "proto_node_id": prefix + "node:" + lid} for lid in sorted(proto & set(doculect_ids))],
        "normalization_methods": [
            {"id": "cldf-form", "version": "1", "description": "Retain upstream Value-to-Form mapping without inferring its linguistic correctness"},
            {"id": "cldf-segments", "version": "1", "description": "Concatenate upstream Segments tokens, preserving boundary and alias notation exactly"}],
        "choice_groups": [], "records": []}
    unknown_source_rows = []
    for rid in ids:
        r = raw[rid]; typed = parsed[rid]; lang = r[cols["languageReference"]]
        original = r[cols["value"]]; form = r[cols["form"]]; segments = typed[cols["segments"]]
        if not original or not form or not segments:
            raise ValueError(f"Selected row lacks original, form or segments: {rid}; choose another row or extend the explicit adapter policy")
        uncertain = rid in overrides or any(x in original for x in ["?", "�"]) or any("?" in s or "�" in s for s in segments)
        source_refs = typed.get(cols.get("source"), [])
        if not source_refs:
            unknown_source_rows.append(rid)
        record = {
            "id": prefix + rid, "doculect_id": prefix + lang,
            "meaning_ids": [prefix + r[cols["parameterReference"]]], "representation": "mixed",
            "attestation": "reconstructed" if lang in proto else "attested",
            "evidence_state": "present", "analysis_id": prefix + "analysis:" + lang if lang in proto else None,
            "proto_node_id": prefix + "node:" + lang if lang in proto else None,
            "citations": [{"source_id": source_id, "locator": str(table.url) + "#" + rid}],
            "readings": [{"id": "source-reading", "original": original, "normalized": "".join(segments),
                          "cells": [{"kind": "unknown" if "?" in s or "�" in s else "boundary" if s == "+" else "segment", "value": s} for s in segments],
                          "normalization": [
                              {"method_id": "cldf-form", "method_version": "1", "input": original, "output": form,
                               "reason": "Upstream Form column at the cited pinned row"},
                              {"method_id": "cldf-segments", "method_version": "1", "input": form, "output": "".join(segments),
                               "reason": "Upstream Segments column at the cited pinned row; joining is a display convention"}],
                          "choices": []}],
            "uncertain": uncertain,
            "uncertainty_note": ("Editorial source-reading concern: " + overrides[rid]) if rid in overrides else
                ("Source contains a question mark or replacement glyph; independent reading required" if uncertain else None),
            "imported_from": {"dataset_id": source_id, "table": str(table.url), "row_id": rid,
                              "id_column": cols["id"], "original_column": cols["value"],
                              "raw_columns": [{"name": h, "value": r[h]} for h in headers]}}
        d["records"].append(record)
    mapped = {cols[k] for k in required}
    report = {
        "dataset": name, "commit": lock["commit"], "cldf_valid": True,
        "source_form_rows": len(raw), "selected_rows": len(ids), "imported_rows": len(d["records"]),
        "source_ids": ids, "record_ids": [r["id"] for r in d["records"]],
        "column_mapping": {k: cols[k] for k in sorted(required)},
        "raw_form_columns_retained": headers,
        "form_columns_not_semantically_interpreted": [h for h in headers if h not in mapped],
        "tables_not_semantically_imported": [str(t.url) for t in ds.tables if str(t.url) not in
                                             {str(ds[n].url) for n in ["FormTable", "LanguageTable", "ParameterTable"]}],
        "loss_policy": "Every source table is retained byte-for-byte. Every selected raw form column is retained in the dossier. Only listed mappings acquire evidence-schema semantics. Language/meaning IDs and labels are projected; other metadata remain in the snapshot. Cognacy, loans, morphology and source bibliographies are not promoted to checked claims.",
        "rows_without_upstream_source_references": unknown_source_rows,
        "uncertain_record_ids": [r["id"] for r in d["records"] if r["uncertain"]],
        "editorial_uncertainty_flags": overrides,
    }
    return d, report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true", help="Compare rebuilt results with committed artifacts without writing")
    a = p.parse_args()
    selections = json.loads((ROOT / "data/import-selection.json").read_text())
    for lock in json.loads((ROOT / "data/upstream/manifest.json").read_text()):
        name = lock["id"]
        d, report = make_dossier(name, lock, selections[name], ROOT / "data/upstream" / name)
        for path, value in [(ROOT / "data/pilots" / (name + ".json"), d),
                            (ROOT / "reports" / ("cldf-" + name + ".json"), report)]:
            if a.check:
                if json.loads(path.read_text()) != value: raise ValueError(f"Stale import artifact: {path}")
            else: dump(path, value)
        print(f"{name}: validated {report['source_form_rows']} source rows; imported {len(d['records'])}; every raw column retained")


if __name__ == "__main__": main()
