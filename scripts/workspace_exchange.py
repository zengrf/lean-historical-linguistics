"""Wordlist interchange with explicit cognacy and retained source readings."""

from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import re
import tempfile
import zipfile
import xml.etree.ElementTree as ET

from build_m7_fixtures import request, model, entry
from lexicon import read_tsv, to_tsv
from workspace_store import new_document
from workspace_backup import safe_members


def cell_key(entry_id, language_id):
    return json.dumps(
        [entry_id, language_id], ensure_ascii=False, separators=(",", ":")
    )


def form_text(form):
    return (
        ""
        if form is None
        else "∅" if not form else " ".join("?" if a is None else a for a in form)
    )


def parse_form(text):
    tokens = text.split()
    if not tokens:
        return None
    if tokens == ["∅"]:
        return []
    if "∅" in tokens:
        raise ValueError("∅ must occupy the whole cell; use ? for an unknown segment")
    return [None if token == "?" else token for token in tokens]


def validate_alignment(text, form):
    if not text.strip():
        return
    if form is None:
        raise ValueError("A missing word cannot have a phonetic alignment")
    tokens = [None if x == "?" else x for x in text.split() if x != "-"]
    if tokens != form:
        raise ValueError(
            "Removing alignment gaps must recover the segmented form exactly"
        )


def from_records(records, title, source):
    languages, labels, rows, annotations, seen_ids, warnings = [], {}, {}, {}, set(), []
    for number, record in enumerate(records, 1):
        row_id = str(record.get("id", number))
        if row_id in seen_ids:
            raise ValueError(f"Duplicate wordlist record ID: {row_id}")
        seen_ids.add(row_id)
        label, cognate = (
            str(record.get("language", "")).strip(),
            str(record.get("cognate", "")).strip(),
        )
        if not label or not cognate or not str(record.get("meaning", "")).strip():
            raise ValueError(
                f"Record {row_id}: language, concept and a cognate-set identifier are required"
            )
        if label not in labels:
            labels[label] = f"language-{len(languages) + 1}"
            languages.append(dict(id=labels[label], label=label))
        language_id = labels[label]
        # Source identifiers remain annotations; internal IDs need not change
        # when source typography includes punctuation or non-Latin characters.
        if cognate not in rows:
            rows[cognate] = dict(
                id=f"set-{len(rows) + 1}", meaning=str(record["meaning"]), forms={}
            )
        row = rows[cognate]
        if language_id in row["forms"]:
            raise ValueError(
                f"Cognate set {cognate}, {label}: multiple readings. Select one for phonological comparison and retain the others in its reading notes; no reading was silently discarded."
            )
        form = record.get("form")
        if form is not None and (
            not isinstance(form, list)
            or any(x is not None and not isinstance(x, str) for x in form)
        ):
            raise ValueError(f"Record {row_id}: invalid segments")
        row["forms"][language_id] = (
            form,
            str(record.get("source") or f"{source}:record{row_id}"),
        )
        alignment = str(record.get("alignment") or "")
        validate_alignment(alignment, form)
        annotations[cell_key(row["id"], language_id)] = dict(
            original=str(record.get("original") or ""),
            witness=str(record.get("witness") or ""),
            locator=str(record.get("locator") or ""),
            certainty=str(record.get("certainty") or "unassessed"),
            note=str(record.get("note") or ""),
            alignment=alignment,
            source_record=row_id,
            source_cognate_set=cognate,
            source_concept=str(record["meaning"]),
            alternatives=[],
            extra=record.get("extra", {}),
        )
    if not rows:
        raise ValueError("No wordlist records found")
    if len(languages) > 32 or len(rows) > 10000:
        raise ValueError(
            "Select at most 32 daughter varieties and 10000 cognate sets for one reconstruction project"
        )
    inventory = sorted(
        {
            atom
            for row in rows.values()
            for form, _ in row["forms"].values()
            for atom in (form or [])
            if atom is not None and atom != "+"
        }
    )
    if len(inventory) > 256:
        raise ValueError(
            "The imported segment inventory exceeds 256 symbols; select a smaller analysis scope"
        )
    proto = inventory if len(inventory) <= 64 else []
    if not proto:
        warnings.append(
            "Choose 1–64 proto-segments before analysis; the imported daughter inventory has not been truncated"
        )
    ids = [language["id"] for language in languages]
    entries = []
    for row in rows.values():
        forms = [
            row["forms"].get(language_id, (None, source))[0] for language_id in ids
        ]
        item = entry(row["id"], ids, forms, meaning=row["meaning"], source=source)
        for reflex in item["reflexes"]:
            reflex["source_ref"] = row["forms"].get(
                reflex["language_id"], (None, source)
            )[1]
        entries.append(item)
    spec = request(
        "imported-wordlist",
        proto,
        ids,
        [
            model(
                "working-hypothesis",
                ids,
                inventory,
                [[] for _ in ids],
                description="Working hypothesis: enter historically justified sound changes; identity is only the starting setting",
                source=source,
            )
        ],
        entries,
        maximum=max(
            8, max(len(r["form"] or []) for e in entries for r in e["reflexes"])
        ),
        description=title,
    )
    if spec["max_length"] > 64:
        raise ValueError(
            "A reflex exceeds 64 segments; divide the analysis into explicit morphological units"
        )
    spec["languages"] = languages
    document = new_document(spec)
    document["annotations"] = annotations
    return dict(document=document, warnings=warnings)


def import_edictor(text, title="Imported wordlist", source="user:wordlist"):
    if not isinstance(text, str) or len(text.encode("utf-8")) > 16_000_000:
        raise ValueError("Wordlist text exceeds 16 MB")
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    header = reader.fieldnames or []
    names = [name.upper().strip() for name in header]
    if len(set(names)) != len(names):
        raise ValueError("Duplicate wordlist column")
    if not {"DOCULECT", "CONCEPT", "TOKENS", "COGID"} <= set(names):
        raise ValueError(
            "Use EDICTOR columns ID, DOCULECT, CONCEPT, TOKENS and COGID; partial COGIDS must first be resolved into explicit compared units"
        )
    records = []
    for number, row in enumerate(reader, 2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"Wordlist line {number}: wrong number of cells")
        r = {k.upper().strip(): v for k, v in row.items()}
        known = {
            "ID",
            "DOCULECT",
            "CONCEPT",
            "TOKENS",
            "COGID",
            "IPA",
            "VALUE",
            "SOURCE",
            "WITNESS",
            "LOCATOR",
            "CERTAINTY",
            "NOTE",
            "ALIGNMENT",
        }
        records.append(
            dict(
                id=r.get("ID") or str(number),
                language=r["DOCULECT"],
                meaning=r["CONCEPT"],
                cognate=r["COGID"],
                form=parse_form(r["TOKENS"]),
                original=r.get("VALUE", r.get("IPA", "")),
                source=r.get("SOURCE") or source,
                witness=r.get("WITNESS", ""),
                locator=r.get("LOCATOR", ""),
                certainty=r.get("CERTAINTY", ""),
                note=r.get("NOTE", ""),
                alignment=r.get("ALIGNMENT", ""),
                extra={k: v for k, v in r.items() if k not in known},
            )
        )
    return from_records(records, title, source)


def export_edictor(document):
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter="\t", lineterminator="\n")
    columns = [
        "ID",
        "DOCULECT",
        "CONCEPT",
        "TOKENS",
        "COGID",
        "VALUE",
        "SOURCE",
        "WITNESS",
        "LOCATOR",
        "CERTAINTY",
        "NOTE",
        "ALIGNMENT",
    ]
    extra = sorted(
        {
            k
            for note in document["annotations"].values()
            if isinstance(note, dict)
            for k in note.get("extra", {})
        }
        - set(columns)
    )
    writer.writerow(columns + extra)
    languages = {l["id"]: l["label"] for l in document["request"]["languages"]}
    for row in document["request"]["entries"]:
        source_cognate = next(
            (
                document["annotations"]
                .get(cell_key(row["id"], r["language_id"]), {})
                .get("source_cognate_set")
                for r in row["reflexes"]
                if document["annotations"]
                .get(cell_key(row["id"], r["language_id"]), {})
                .get("source_cognate_set")
            ),
            row["id"],
        )
        for reflex in row["reflexes"]:
            note = document["annotations"].get(
                cell_key(row["id"], reflex["language_id"]), {}
            )
            writer.writerow(
                [
                    note.get("source_record", f"{row['id']}-{reflex['language_id']}"),
                    languages[reflex["language_id"]],
                    row["meaning"],
                    form_text(reflex["form"]),
                    source_cognate,
                    note.get("original", ""),
                    reflex["source_ref"],
                    note.get("witness", ""),
                    note.get("locator", ""),
                    note.get("certainty", "unassessed"),
                    note.get("note", ""),
                    note.get("alignment", ""),
                ]
                + [note.get("extra", {}).get(k, "") for k in extra]
            )
    return buffer.getvalue()


def cldf_zip(document):
    """Export a CLDF Wordlist using the official pycldf writer and validator.

    The complete project document accompanies the standard data so that rule
    hypotheses, alternatives and philological notes are not lost in exchange.
    """
    from pycldf import Wordlist

    with tempfile.TemporaryDirectory(prefix="comparative-cldf-") as directory:
        root = Path(directory).resolve()
        dataset = Wordlist.in_dir(root)
        for component in ["LanguageTable", "ParameterTable", "CognateTable"]:
            dataset.add_component(component)
        dataset.add_columns(
            "FormTable",
            "Witness",
            "Locator",
            "Certainty",
            "Editorial_Note",
            "Observation_Status",
        )
        spec = document["request"]
        forms, cognates = [], []
        for row in spec["entries"]:
            for reflex in row["reflexes"]:
                if reflex["form"] is None:
                    continue
                fid = f"{row['id']}-{reflex['language_id']}"
                note = document["annotations"].get(
                    cell_key(row["id"], reflex["language_id"]), {}
                )
                tokens = ["?" if t is None else t for t in reflex["form"]]
                forms.append(
                    dict(
                        ID=fid,
                        Language_ID=reflex["language_id"],
                        Parameter_ID=row["id"],
                        Value=note.get("original") or "".join(tokens),
                        Form="".join(tokens) if tokens else "∅",
                        Segments=tokens,
                        Comment=reflex["source_ref"],
                        Witness=note.get("witness", ""),
                        Locator=note.get("locator", ""),
                        Certainty=note.get("certainty", "unassessed"),
                        Editorial_Note=note.get("note", ""),
                        Observation_Status="empty" if not tokens else "observed",
                    )
                )
                cognates.append(
                    dict(
                        ID=fid,
                        Form_ID=fid,
                        Cognateset_ID=row["id"],
                        Alignment=note.get("alignment", "").split() or tokens,
                    )
                )
        dataset.write(
            LanguageTable=[
                dict(ID=l["id"], Name=l["label"]) for l in spec["languages"]
            ],
            ParameterTable=[
                dict(ID=r["id"], Name=r["meaning"]) for r in spec["entries"]
            ],
            FormTable=forms,
            CognateTable=cognates,
        )
        if not dataset.validate():
            raise ValueError("CLDF export failed validation")
        (root / "project.json").write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n"
        )
        (root / "README.txt").write_text(
            "CLDF Wordlist plus project.json for lossless project recovery. Comment retains the source locator; no bibliographic identity is invented. Unknown segments are ?. Empty observed forms are explicitly tagged Observation_Status=empty with Form ∅ and empty Segments. Missing forms, alternative readings, raw source columns and hypotheses remain in project.json. Import project.json to recover the complete project; CLDF import reads the tables as a new wordlist.\n"
        )
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(root.iterdir()):
                archive.write(path, path.name)
        return output.getvalue()


def import_cldf_zip(data, title="Imported CLDF", source="user:cldf"):
    """Read only local CLDF Wordlist tables; never fetch metadata dependencies."""
    from pycldf import Dataset
    from import_cldf import table_info

    if len(data) > 11_000_000:
        raise ValueError("Select a CLDF ZIP of at most 11 MB for browser import")
    with tempfile.TemporaryDirectory(prefix="comparative-import-") as directory:
        root = Path(directory).resolve()
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = safe_members(archive, maximum=64_000_000, count=256)
            for item in members:
                if item.is_dir():
                    continue
                path = root / item.filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(item))
        candidates = []
        for path in root.rglob("*.json"):
            metadata = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(metadata, dict) and "tables" in metadata:
                candidates.append((path, metadata))
        if len(candidates) != 1:
            raise ValueError("The ZIP must contain exactly one CLDF metadata document")
        path, metadata = candidates[0]

        def local_file(value):
            if not isinstance(value, str) or ":" in value or "\\" in value:
                raise ValueError("CLDF dependencies must be local files inside the ZIP")
            file = (path.parent / value).resolve()
            if not file.is_relative_to(root) or not file.is_file():
                raise ValueError("CLDF dependency is missing or outside the ZIP")

        for table in metadata["tables"]:
            local_file(table["url"])
            if not isinstance(table.get("tableSchema"), dict):
                raise ValueError("External CLDF table schemas are not supported")
        if metadata.get("dc:source"):
            sources = metadata["dc:source"]
            for value in sources if isinstance(sources, list) else [sources]:
                local_file(value)
        dataset = Dataset.from_metadata(path)
        if dataset.module != "Wordlist" or not dataset.validate():
            raise ValueError("Import requires a valid CLDF Wordlist")
        _, fc, raw_forms, _ = table_info(dataset, "FormTable")
        _, lc, languages, _ = table_info(dataset, "LanguageTable")
        language_names = [row[lc["name"]] for row in languages.values()]
        _, pc, parameters, _ = table_info(dataset, "ParameterTable")
        _, cc, _, _ = table_info(dataset, "CognateTable")
        cognacy = {}
        for row in dataset["CognateTable"]:
            if row.get(cc.get("segmentSlice")):
                raise ValueError(
                    "Partial cognacy must be resolved into explicit compared morphological units before import"
                )
            fid = row[cc["formReference"]]
            if fid in cognacy:
                raise ValueError(
                    f"Form {fid} has multiple cognate judgments; select a hypothesis before import"
                )
            cognacy[fid] = row
        records = []
        for row in dataset["FormTable"]:
            fid = row[fc["id"]]
            if fid not in cognacy:
                raise ValueError(f"Form {fid} has no explicit cognate-set judgment")
            c = cognacy[fid]
            tokens = row.get(fc.get("segments")) or []
            if not isinstance(tokens, list):
                raise ValueError("CLDF Segments must declare a token separator")
            if tokens:
                form = [None if t == "?" else t for t in tokens]
            elif row.get("Observation_Status") == "empty":
                form = []
            elif row.get(fc.get("form")) in (None, "", "-"):
                form = None
            else:
                raise ValueError(
                    f"Form {fid} has no explicit segmentation; segment it before import"
                )
            language_id, parameter_id = (
                row[fc["languageReference"]],
                row[fc["parameterReference"]],
            )
            if not isinstance(parameter_id, str):
                raise ValueError(
                    "Resolve multiple concept assignments before importing a comparison"
                )
            references = row.get(fc.get("source")) or []
            records.append(
                dict(
                    id=fid,
                    language=languages[language_id][lc["name"]]
                    + (
                        f" [{language_id}]"
                        if language_names.count(languages[language_id][lc["name"]]) > 1
                        else ""
                    ),
                    meaning=parameters[parameter_id][pc["name"]],
                    cognate=c[cc["cognatesetReference"]],
                    form=form,
                    original=row.get(fc.get("value")) or "",
                    source="; ".join(map(str, references))
                    or row.get(fc.get("comment"))
                    or source,
                    witness=row.get("Witness") or "",
                    locator=row.get("Locator") or "",
                    certainty=row.get("Certainty") or "unassessed",
                    note=row.get("Editorial_Note") or "",
                    alignment=" ".join(c.get(cc.get("alignment")) or []),
                    extra=raw_forms[fid],
                )
            )
        result = from_records(records, title, source)
        result["warnings"].append(
            "Imported explicit whole-word cognacy and segmented readings from CLDF tables. Retain the original archive for bibliographies and other tables. To recover hypotheses and alternative readings from this application's exports, import its accompanying project.json instead."
        )
        return result


def tei_apparatus(document):
    """A limited TEI apparatus of source readings, not an inferred critical edition."""
    ns = "http://www.tei-c.org/ns/1.0"
    ET.register_namespace("", ns)

    def add(parent, name, text=None, **attributes):
        node = ET.SubElement(parent, "{" + ns + "}" + name, attributes)
        node.text = text
        return node

    root = ET.Element("{" + ns + "}TEI")
    header = add(root, "teiHeader")
    desc = add(header, "fileDesc")
    titles = add(desc, "titleStmt")
    add(titles, "title", document["request"]["description"])
    add(
        add(desc, "publicationStmt"),
        "p",
        "Private research export; no textual affiliation is inferred.",
    )
    source_desc = add(desc, "sourceDesc")
    add(
        source_desc,
        "p",
        "Source readings and editorial notes recorded in the comparative workbench. The selected reading is a comparison choice, not an established archetype.",
    )
    witnesses = add(source_desc, "listWit")
    known = {}
    body = add(add(root, "text"), "body")
    langs = {l["id"]: l["label"] for l in document["request"]["languages"]}
    for number, row in enumerate(document["request"]["entries"], 1):
        paragraph = add(body, "p")
        add(paragraph, "seg", row["meaning"])
        for reflex in row["reflexes"]:
            note = document["annotations"].get(
                cell_key(row["id"], reflex["language_id"]), {}
            )
            app = add(paragraph, "app")
            for i, reading in enumerate(
                [note | dict(form=reflex["form"], source=reflex["source_ref"])]
                + note.get("alternatives", [])
            ):
                witness = (
                    reading.get("witness")
                    or reading.get("source")
                    or "Unspecified source"
                )
                if witness not in known:
                    known[witness] = f"w{len(known)+1}"
                    item = add(witnesses, "witness", witness)
                    item.set("{http://www.w3.org/XML/1998/namespace}id", known[witness])
                attrs = {
                    "wit": "#" + known[witness],
                    "type": "selected" if i == 0 else "alternative",
                }
                certainty = reading.get("certainty")
                if certainty in {"high", "medium", "low"}:
                    attrs["cert"] = certainty
                rdg = add(app, "rdg", reading.get("original") or "", **attrs)
                add(
                    rdg,
                    "note",
                    langs[reflex["language_id"]]
                    + "; comparison segments: "
                    + (form_text(reading.get("form")) or "no observation"),
                    type="segmentation",
                )
                add(
                    rdg,
                    "note",
                    "; ".join(
                        str(reading.get(k) or "") for k in ["source", "locator", "note"]
                    ),
                    type="editorial",
                )
    ET.indent(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def correspondences(document):
    """Count supplied alignment columns only; gaps and unknowns stay distinct."""
    from collections import Counter

    counts, skipped = Counter(), []
    for row in document["request"]["entries"]:
        aligned = []
        for reflex in row["reflexes"]:
            alignment = (
                document["annotations"]
                .get(cell_key(row["id"], reflex["language_id"]), {})
                .get("alignment", "")
            )
            validate_alignment(alignment, reflex["form"])
            aligned.append(alignment.split() if alignment.strip() else None)
        lengths = {len(a) for a in aligned if a is not None}
        if len(lengths) != 1 or sum(a is not None for a in aligned) < 2:
            skipped.append(row["id"])
            continue
        for i in range(next(iter(lengths))):
            counts[tuple(a[i] if a is not None else "(missing)" for a in aligned)] += 1
    return dict(
        columns=[dict(segments=list(k), count=v) for k, v in counts.most_common()],
        skipped=skipped,
    )
