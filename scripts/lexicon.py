"""Generate and check all bounded protolexicons from daughter-language reflexes.

The Python graph solver is untrusted. Only a forest accepted by lexicon_check
is saved as complete. No published protoform list is used.
"""

import argparse
from copy import deepcopy
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import time

from build_pie_corpus import ROOT, encoded
from explore_reconstructions import strict_read
from m7_solver import IncompleteSearch, solve, graph_counts, unrank, decimal, integer

BIN = ROOT / "lean/.lake/build/bin/lexicon_check"


def native(mode, value, *, binary=BIN, timeout=60, allow_rejection=False):
    raw = encoded(value)
    if len(raw) > 134217728:
        raise IncompleteSearch("Certificate exceeds the 128 MiB checker limit")
    with tempfile.TemporaryDirectory(prefix="m7-check-") as directory:
        path = Path(directory) / "input.json"
        path.write_bytes(raw)
        try:
            result = subprocess.run(
                [str(binary), mode, str(path)], capture_output=True, timeout=timeout
            )
        except subprocess.TimeoutExpired as error:
            raise IncompleteSearch(
                "Lean checking timed out; completeness is not established"
            ) from error
    if not result.stdout:
        raise ValueError(
            "Lean checker failed: "
            + result.stderr.decode("utf-8", errors="replace")[:1000]
        )
    data = json.loads(result.stdout)
    if result.returncode and not allow_rejection:
        raise ValueError(data.get("error", "Lean checker rejected the input"))
    return data


def read_tsv(text, languages, source_ref="user:reflex-table"):
    if (
        not isinstance(text, str)
        or not isinstance(source_ref, str)
        or not source_ref.strip()
    ):
        raise ValueError("Provide TSV text and its source reference")
    reader = csv.reader(io.StringIO(text), delimiter="\t", strict=True)
    header = next(reader, None)
    expected = ["id", "meaning"] + [x["id"] for x in languages]
    if header != expected:
        raise ValueError("Expected TSV columns: " + "\t".join(expected))
    entries = []
    for number, row in enumerate(reader, start=2):
        if not row or all(not cell for cell in row):
            continue
        if len(row) != len(header):
            raise ValueError(f"TSV row {number}: expected {len(header)} cells")
        reflexes = []
        for language, value in zip(languages, row[2:]):
            tokens = value.split()
            if "∅" in tokens and tokens != ["∅"]:
                raise ValueError(f"TSV row {number}: ∅ must occupy the whole cell")
            form = (
                None
                if not tokens
                else (
                    [] if tokens == ["∅"] else [None if t == "?" else t for t in tokens]
                )
            )
            reflexes.append(
                dict(
                    language_id=language["id"],
                    form=form,
                    source_ref=f"{source_ref}:row{number}",
                )
            )
        entries.append(dict(id=row[0], meaning=row[1], reflexes=reflexes))
        if len(entries) > 10000:
            raise ValueError("TSV exceeds 10000 cognate rows")
    return entries


def to_tsv(spec):
    stream = io.StringIO()
    writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
    writer.writerow(["id", "meaning"] + [l["id"] for l in spec["languages"]])
    for e in spec["entries"]:
        writer.writerow(
            [e["id"], e["meaning"]]
            + [
                (
                    ""
                    if r["form"] is None
                    else (
                        "∅"
                        if not r["form"]
                        else " ".join("?" if a is None else a for a in r["form"])
                    )
                )
                for r in e["reflexes"]
            ]
        )
    return stream.getvalue()


def constrain(spec, analyses=None, languages=None):
    result = deepcopy(spec)
    for selected, known, label in [
        (analyses, [a["id"] for a in spec["analyses"]], "models"),
        (languages, [l["id"] for l in spec["languages"]], "languages"),
    ]:
        if selected is not None and (
            not isinstance(selected, list)
            or not all(isinstance(x, str) for x in selected)
            or len(set(selected)) != len(selected)
            or not set(selected) <= set(known)
        ):
            raise ValueError("Unknown or repeated selected " + label)
    if analyses is not None:
        result["analyses"] = [a for a in result["analyses"] if a["id"] in analyses]
    if languages is not None:
        for e in result["entries"]:
            for r in e["reflexes"]:
                if r["language_id"] not in languages:
                    r["form"] = None
    return result


def reconstruct(
    spec, *, node_budget=250000, time_limit=60, binary=BIN, force_reference=False
):
    if type(node_budget) is not int or not 1 <= node_budget <= 250000:
        raise ValueError("Node budget must be 1–250000")
    if type(time_limit) not in (float, int) or not 0 < time_limit <= 60:
        raise ValueError(
            "Search time limit must be more than zero and at most 60 seconds"
        )
    native("--validate", spec, binary=binary)
    started = time.monotonic()
    forest = solve(
        spec,
        node_budget=node_budget,
        time_limit=time_limit,
        force_reference=force_reference,
    )
    generation_seconds = time.monotonic() - started
    started = time.monotonic()
    checked = native("--check", forest, binary=binary)
    if not checked.get("complete") or not checked.get("graph_checked"):
        raise ValueError("Lean did not establish completeness")
    # Independent arithmetic check; Python pagination never trusts a proposer count.
    total = 0
    for model, verified in zip(forest["models"], checked["models"]):
        cs = [graph_counts(g["nodes"]) for g in model["graphs"]]
        product = 1
        for b, row in zip(model["bindings"], verified["entries"]):
            count = cs[b["graph"]][b["root"]]
            if decimal(count) != row["count"]:
                raise ValueError("Independent count disagrees with native Lean")
            product *= count
        if decimal(product) != verified["lexicon_count"]:
            raise ValueError("Independent lexicon count disagrees with native Lean")
        total += product
    if decimal(total) != checked["lexicon_count"]:
        raise ValueError("Independent total disagrees with native Lean")
    summary = checked | dict(
        request_sha256=hashlib.sha256(encoded(spec)).hexdigest(),
        certificate_sha256=hashlib.sha256(encoded(forest)).hexdigest(),
        generation_seconds=round(generation_seconds, 6),
        checking_seconds=round(time.monotonic() - started, 6),
        count_unit="model-qualified protolexicons",
        scope="Every supplied cognate row, one shared selected model, declared alphabet, length bounds and slot templates.",
    )
    return dict(forest=forest, summary=summary)


def model_context(result, analysis_id):
    forest = result["forest"]
    try:
        model = next(m for m in forest["models"] if m["analysis_id"] == analysis_id)
        summary = next(
            m for m in result["summary"]["models"] if m["analysis_id"] == analysis_id
        )
    except StopIteration as error:
        raise ValueError("Unknown model") from error
    return (
        forest["request"],
        model,
        summary,
        [graph_counts(g["nodes"]) for g in model["graphs"]],
    )


def page(result, analysis_id, *, entry_id=None, offset="0", limit=20, binary=BIN):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Page size must be 1–100")
    if not isinstance(offset, str) or len(offset) > 200000:
        raise ValueError("Invalid decimal offset")
    start = integer(offset)
    spec, model, summary, cs = model_context(result, analysis_id)
    if entry_id is not None:
        try:
            binding = next(b for b in model["bindings"] if b["entry_id"] == entry_id)
            count = integer(
                next(e for e in summary["entries"] if e["entry_id"] == entry_id)[
                    "count"
                ]
            )
        except StopIteration as error:
            raise ValueError("Unknown entry") from error
        rows = []
        for rank in range(start, min(count, start + limit)):
            word = unrank(
                model["graphs"][binding["graph"]]["nodes"],
                cs[binding["graph"]],
                binding["root"],
                rank,
            )
            rows.append(dict(analysis_id=analysis_id, entry_id=entry_id, word=word))
        derived = native("--derive", dict(request=spec, proposals=rows), binary=binary)[
            "proposals"
        ]
        if not all(x["accepted"] for x in derived):
            raise ValueError("Candidate failed independent native forward checking")
        return dict(
            kind="words",
            count=decimal(count),
            offset=decimal(start),
            items=derived,
            has_more=start + len(rows) < count,
        )
    count = integer(summary["lexicon_count"])
    # Prevent accidental giant pages while allowing a complete 10000-row lexicon.
    if limit * len(spec["entries"]) > 10000:
        raise ValueError(
            "A page can contain at most 10000 reconstructed words; reduce page size"
        )
    rows, items = [], []
    for rank in range(start, min(count, start + limit)):
        remaining, words = rank, []
        for b in reversed(model["bindings"]):
            n = cs[b["graph"]][b["root"]]
            remaining, local = divmod(remaining, n)
            words.append(
                dict(
                    analysis_id=analysis_id,
                    entry_id=b["entry_id"],
                    word=unrank(
                        model["graphs"][b["graph"]]["nodes"],
                        cs[b["graph"]],
                        b["root"],
                        local,
                    ),
                )
            )
        words.reverse()
        rows.extend(words)
        items.append(dict(index=decimal(rank), analysis_id=analysis_id, words=words))
    derived = native("--derive", dict(request=spec, proposals=rows), binary=binary)[
        "proposals"
    ]
    if not all(x["accepted"] for x in derived):
        raise ValueError("Lexicon failed independent native forward checking")
    for i, item in enumerate(items):
        item["derivations"] = derived[
            i * len(spec["entries"]) : (i + 1) * len(spec["entries"])
        ]
    return dict(
        kind="lexicons",
        count=decimal(count),
        offset=decimal(start),
        items=items,
        has_more=start + len(items) < count,
    )


def save(result, directory):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "forest.json").write_bytes(encoded(result["forest"]))
    (directory / "summary.json").write_bytes(encoded(result["summary"]))


def load(directory, *, binary=BIN):
    forest = strict_read(directory / "forest.json")
    # Recheck imported/on-disk certificates, including all bindings and edges.
    summary = native("--check", forest, binary=binary)
    return dict(forest=forest, summary=summary)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="command", required=True)
    s = commands.add_parser("solve")
    s.add_argument("request", type=Path)
    s.add_argument("--output", required=True, type=Path)
    s.add_argument("--node-budget", type=int, default=250000)
    s.add_argument("--time-limit", type=float, default=60)
    s.add_argument("--reference", action="store_true")
    for name in ["words", "lexicons"]:
        q = commands.add_parser(name)
        q.add_argument("directory", type=Path)
        q.add_argument("--model", required=True)
        if name == "words":
            q.add_argument("--entry", required=True)
        q.add_argument("--offset", default="0")
        q.add_argument("--limit", type=int, default=1 if name == "lexicons" else 20)
    args = p.parse_args()
    try:
        if args.command == "solve":
            result = reconstruct(
                strict_read(args.request),
                node_budget=args.node_budget,
                time_limit=args.time_limit,
                force_reference=args.reference,
            )
            save(result, args.output)
            print(encoded(result["summary"]).decode(), end="")
        else:
            print(
                encoded(
                    page(
                        load(args.directory),
                        args.model,
                        entry_id=getattr(args, "entry", None),
                        offset=args.offset,
                        limit=args.limit,
                    )
                ).decode(),
                end="",
            )
    except IncompleteSearch as error:
        print(json.dumps(dict(complete=False, status="incomplete", error=str(error))))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
