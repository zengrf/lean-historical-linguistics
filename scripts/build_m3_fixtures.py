"""Construct the versioned M3 suite. Expected outcomes are explicit, not Lean output.

The 140 counted sites belong to 60 synthetic dossiers with valid alignments and
registries. Structural mutations are extra tests and never pad those counts.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/correspondence"
DOCULECTS = ["synthetic-A", "synthetic-B", "synthetic-C", "synthetic-D"]


def cell(kind, value=None):
    return dict(kind=kind, value=value)


def seg(value):
    return cell("segment", value)


GAP = cell("gap")
UNKNOWN = cell("unknown", "unread")
BOUNDARY = cell("boundary", "+")
MISSING = cell("missing")


def alignment(name, rows, unit=None):
    """Construct a gap insertion example; this is not an acceptance oracle."""
    width = max((len(r) for r in rows if r is not None), default=1)
    return dict(id=name, evidence_unit=unit or name + "-root", width=width, rows=[
        dict(doculect_id=d, source_ref="synthetic:" + name + ":" + d,
             original=None if r is None else [deepcopy(c) for c in r if c != GAP],
             aligned=deepcopy(r)) for d, r in zip(DOCULECTS, rows)])


def one_column(name, cells, unit=None):
    return alignment(name, [None if c is None else [c] for c in cells], unit)


def dossier(name, alignments, blocks=None, supports=None):
    sites = [dict(id=f"{a['id']}-c{i}", alignment_id=a["id"], column_index=i)
             for a in alignments for i in range(a["width"])
             if any(r["aligned"] is not None and r["aligned"][i]["kind"] == "segment" for r in a["rows"])]
    if blocks is None:
        blocks = [list(range(len(sites)))]
    if supports is None:
        supports = [len(alignments)] * len(blocks)
    return dict(alignment_data=dict(schema_version="1.0.0", id=name,
                                   description="Constructed M3 contract example: " + name,
                                   source_kind="synthetic", doculects=DOCULECTS.copy(), alignments=alignments),
                sites=sites, groups=[dict(id=f"group-{i}", members=[sites[j]["id"] for j in block],
                                         claimed_support=supports[i]) for i, block in enumerate(blocks)],
                support_policy="distinct-evidence-units-v1", claim="feasibility-only")


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def generate():
    files = {}; entries = []

    def add(name, value, accept=True, code=None, category="structural", rationale="", counted=False, kind="dossier"):
        path = ("sites/" if counted else "valid/" if accept else "invalid/") + name + ".json"
        assert path not in files and rationale
        assert accept == (code is None)
        files[path] = value if isinstance(value, bytes) else encode(value)
        entries.append(dict(path=path, kind=kind, accept=accept, code=code, category=category,
                            rationale=rationale, counts_toward_site_suite=counted))

    consonants = ["p", "t", "k", "m", "s"]
    reflexes = ["b", "d", "g", "n", "z"]
    for i in range(30):
        p, q = seg(consonants[i // 6]), seg(reflexes[i // 6])
        r = seg(["a̱", "tʰ", "ŋ", "ə", "ɕ"][i // 6]); tone = seg("⁵¹")
        patterns = [
            ([p, q, r, tone], [p, q, r, tone]),
            ([p, q, None, None], [p, None, r, None]),
            ([p, UNKNOWN, r, None], [p, q, None, GAP]),
            ([p, GAP, q, None], [p, GAP, q, UNKNOWN]),
            ([p, GAP, None, tone], [p, GAP, r, tone]),
            ([p, UNKNOWN, r, None], [p, cell("unknown", "unclear-glyph"), r, tone]),
        ]
        x, y = patterns[i % 6]; name = f"shared-{i:02d}"
        d = dossier(name, [one_column(name + "-a", x), one_column(name + "-b", y)])
        add(name, d, category="positive-overlap", counted=True,
            rationale="Two units share observed segments; unavailable cells add neither conflict nor evidence.")
    for i in range(10):
        p, q = seg(consonants[i % 5]), seg(reflexes[i % 5])
        same = i % 2 == 0
        t = p if same else seg("tʰ")
        u = q if same else seg("dʱ")
        name = f"two-columns-{i:02d}"
        a = alignment(name + "-a", [[p, t], [q, u], None, [GAP, GAP if same else seg("m")]])
        b = alignment(name + "-b", [[p, t], [q, u], [seg("a̱"), seg("a̱")], None])
        d = dossier(name, [a, b], [[0, 1, 2, 3]] if same else [[0, 2], [1, 3]], [2] if same else [2, 2])
        add(name, d, category="multiple-sites-per-unit", counted=True,
            rationale="Two columns per alignment; repeated positions retain two distinct evidence units.")
    for i in range(10):
        p = seg(consonants[i % 5]); name = f"conflict-{i:02d}"
        x = [p, seg("t"), None if i < 5 else seg("a"), UNKNOWN]
        y = [p, seg("k"), None if i < 5 else seg("a"), UNKNOWN]
        add(name, dossier(name, [one_column(name + "-a", x), one_column(name + "-b", y)]),
            False, "PAIR_CONFLICT", "observed-conflict",
            "A shared sound does not excuse a conflict at another observed position.", True)
    for i in range(10):
        name = f"disjoint-{i:02d}"
        x = [seg(consonants[i % 5]), None, None, None if i < 5 else GAP]
        y = [None, seg(reflexes[i % 5]), None, None if i < 5 else GAP]
        add(name, dossier(name, [one_column(name + "-a", x), one_column(name + "-b", y)]),
            False, "NO_SHARED_SEGMENT", "missing-only-overlap",
            "Disjoint observations and even an equal gap provide no shared segment.", True)

    base = dossier("base", [one_column("a", [seg("p"), seg("t"), None, GAP]),
                            one_column("b", [seg("p"), seg("t"), None, GAP])])

    def mutation(name, mutate, code, rationale, category="structural"):
        d = deepcopy(base); d["alignment_data"]["id"] = name; mutate(d)
        add(name, d, False, code, category, rationale)

    def row(d, i=0, a=0):
        return d["alignment_data"]["alignments"][a]["rows"][i]

    mutation("substituted-segment", lambda d: row(d).update(aligned=[seg("b")]), "ROW_RECOVERY", "Substitution is not gap insertion.")
    mutation("duplicated-segment", lambda d: row(d).update(aligned=[seg("p"), seg("p")]), "ROW_RECOVERY", "An inserted segment must not be erased as a gap.")
    mutation("omitted-segment", lambda d: row(d).update(aligned=[GAP]), "ROW_RECOVERY", "An observed original cannot disappear.")
    mutation("missing-to-empty", lambda d: row(d, 2).update(aligned=[GAP]), "ROW_RECOVERY", "Absent and present empty words are distinct.")
    mutation("empty-to-missing", lambda d: row(d, 3).update(aligned=None), "ROW_RECOVERY", "A present empty word cannot become absent.")
    mutation("original-gap", lambda d: row(d).update(original=[GAP], aligned=[GAP]), "ORIGINAL_SHAPE", "Gaps are alignment operations, not original symbols.")
    mutation("present-missing-cell", lambda d: row(d).update(original=[MISSING], aligned=[MISSING]), "ALIGNED_SHAPE", "Missing data belongs to absent rows, not present sequences.")
    mutation("ragged-row", lambda d: row(d, 3).update(aligned=[GAP, GAP]), "ALIGNED_SHAPE", "Gap-only present rows still require the declared width.")
    mutation("zero-width", lambda d: d["alignment_data"]["alignments"][0].update(width=0), "ALIGNMENT_DIMENSIONS", "The width must be positive.")
    mutation("one-row", lambda d: d["alignment_data"]["alignments"][0].update(rows=[row(d)]), "ALIGNMENT_DIMENSIONS", "An alignment requires at least two rows.")
    mutation("axis-reordered", lambda d: d["alignment_data"]["alignments"][0]["rows"].reverse(), "DOCULECT_AXIS", "Positional compatibility requires one common ordered axis.")
    mutation("axis-duplicate", lambda d: d["alignment_data"]["doculects"].__setitem__(1, DOCULECTS[0]), "DOCULECT_AXIS", "Duplicate doculect identities are rejected.")
    mutation("empty-source", lambda d: row(d, 2).update(source_ref=""), "SOURCE_REF", "Absence also needs a declared source reference.")
    mutation("empty-description", lambda d: d["alignment_data"].update(description=""), "DATA_METADATA", "The document must describe its source scope.")
    mutation("wrong-version", lambda d: d["alignment_data"].update(schema_version="2"), "SCHEMA_VERSION", "Unrecognized schema versions fail closed.")
    mutation("duplicate-alignment", lambda d: d["alignment_data"]["alignments"].append(deepcopy(d["alignment_data"]["alignments"][0])), "ALIGNMENT_IDS", "An alignment identity cannot be reused.")
    mutation("invalid-unit", lambda d: d["alignment_data"]["alignments"][0].update(evidence_unit=""), "ALIGNMENT_METADATA", "Empty unit labels cannot support a group.")
    mutation("unknown-alignment", lambda d: d["sites"][0].update(alignment_id="absent"), "SITE_REFERENCE", "Every site refers to a supplied alignment.")
    mutation("out-of-range", lambda d: d["sites"][0].update(column_index=1), "SITE_REFERENCE", "Column indices are zero-based and bounded.")
    mutation("duplicate-position", lambda d: d["sites"].append(dict(d["sites"][0], id="alias")), "DUPLICATE_SITE_POSITION", "Aliases cannot multiply one observation.")
    mutation("omitted-site", lambda d: d["sites"].pop(), "SITE_COVERAGE", "All segment-bearing columns must be registered.")
    mutation("duplicate-site-id", lambda d: d["sites"][1].update(id=d["sites"][0]["id"]), "SITE_IDS", "Distinct coordinates require distinct site IDs.")
    mutation("unknown-member", lambda d: d["groups"][0]["members"].append("invented"), "UNKNOWN_SITE", "A certificate cannot invent an observation.")
    mutation("duplicate-member", lambda d: d["groups"][0]["members"].append(d["sites"][0]["id"]), "DUPLICATE_MEMBER", "Within-group repetitions are rejected.")
    mutation("double-assignment", lambda d: d["groups"].append(dict(id="extra", members=[d["sites"][0]["id"]], claimed_support=1)), "PARTITION_COVERAGE", "A required site appears once across all groups.")
    mutation("unassigned-site", lambda d: d["groups"][0].update(members=[d["sites"][0]["id"]], claimed_support=1), "PARTITION_COVERAGE", "A required site cannot be left out.")
    mutation("empty-group", lambda d: d["groups"].append(dict(id="empty", members=[], claimed_support=0)), "EMPTY_GROUP", "Empty groups are not feasible certificates.")
    mutation("duplicate-group-id", lambda d: d["groups"].append(deepcopy(d["groups"][0])), "GROUP_IDS", "Group IDs are unique.")
    mutation("wrong-support", lambda d: d["groups"][0].update(claimed_support=3), "SUPPORT_COUNT", "Reported support must match the distinct-unit count.")
    mutation("zero-support", lambda d: d["groups"][0].update(claimed_support=0), "NO_GROUP_SUPPORT", "Positive support is required.")
    mutation("repeated-source-inflation", lambda d: d["alignment_data"]["alignments"][1].update(evidence_unit="a-root"), "SUPPORT_COUNT", "Two alignment records with one unit label count once.")
    mutation("unknown-support-policy", lambda d: d.update(support_policy="count-every-position"), "SUPPORT_POLICY", "Undeclared support policies cannot change the count.")
    for claim in ["minimum", "optimal", "maximal", "minimum-cover", "score-based"]:
        mutation("claim-" + claim, lambda d, c=claim: d.update(claim=c), "UNSUPPORTED_OPTIMALITY", "This milestone verifies feasibility only.", "optimality-boundary")
    mutation("hidden-optimality", lambda d: d.update(optimal=True), "JSON_SHAPE", "Unknown optimization claims cannot enter through ignored JSON fields.", "parser")
    mutation("external-site-cells", lambda d: d["sites"][0].update(cells=[seg("p")]), "JSON_SHAPE", "Site observations must be derived from the alignment.", "parser")
    mutation("undeclared-spans", lambda d: row(d).update(morpheme_spans=[[0, 1]]), "JSON_SHAPE", "The profile uses explicit boundary cells, not undeclared spans.", "parser")
    mutation("omitted-null", lambda d: row(d, 2).pop("original"), "JSON_SHAPE", "Even nullable fields must be explicit.", "parser")
    mutation("negative-column", lambda d: d["sites"][0].update(column_index=-1), "JSON_SHAPE", "Natural-number coordinates reject negatives.", "parser")
    mutation("empty-unknown", lambda d: row(d).update(original=[cell("unknown", "")], aligned=[cell("unknown", "")]), "CELL_VALUE", "Unknown readings need an explicit nonempty value.")
    mutation("bad-boundary-value", lambda d: row(d).update(original=[cell("boundary", "#")], aligned=[cell("boundary", "#")]), "CELL_VALUE", "Only the declared morpheme marker is accepted.")
    for name, symbol in [("ascii-space", "p q"), ("narrow-nbsp", "p\u202fq"), ("nel", "p\u0085q"), ("control", "p\u0001"), ("reserved-boundary", "+")]:
        mutation("symbol-" + name, lambda d, s=symbol: row(d).update(original=[seg(s)], aligned=[seg(s)]), "CELL_VALUE", "Atomic segments obey the M2 Unicode and marker restrictions.", "unicode")
    for name, raw, code in [
        ("duplicate-json-key", b'{"claim":"x",' + encode(base)[1:], "DUPLICATE_JSON_KEY"),
        ("escaped-duplicate-key", b'{"cl\\u0061im":"x",' + encode(base)[1:], "DUPLICATE_JSON_KEY"),
        ("invalid-utf8", b'\xff', "UTF8"),
        ("invalid-json", b'{', "JSON_SYNTAX"),
        ("surrogate-escape", encode(base).replace(b'"p"', b'"\\ud83d\\ude00"', 1), "UNICODE_ESCAPE"),
    ]:
        add(name, raw, False, code, "parser", "Malformed or ambiguous byte input is rejected before semantic checking.")

    # Boundary and recovery fixtures have multiple columns and are separate from
    # the count-bearing single-site/group examples above.
    a = alignment("boundary-a", [[seg("p"), BOUNDARY, seg("t")], [seg("b"), BOUNDARY, seg("d")], None, [GAP, GAP, GAP]])
    b = alignment("boundary-b", [[seg("p"), BOUNDARY, seg("t")], [seg("b"), BOUNDARY, seg("d")], None, [GAP, GAP, GAP]])
    boundary = dossier("boundaries", [a, b], [[0, 2], [1, 3]], [2, 2])
    add("boundaries", boundary, rationale="Internal morpheme boundaries and present empty rows are preserved; only segment columns become sites.")
    add("standalone-boundaries", boundary["alignment_data"], kind="alignment", rationale="Alignment preservation can be checked without a grouping certificate.")
    d = deepcopy(boundary); row(d)["aligned"][0], row(d)["aligned"][2] = row(d)["aligned"][2], row(d)["aligned"][0]
    add("reordered-original", d, False, "ROW_RECOVERY", "alignment", "A permutation with the same multiset is rejected.")
    d = deepcopy(boundary); row(d).update(original=[seg("p"), seg("t")], aligned=[seg("p"), seg("a"), seg("t")])
    add("mixed-boundary-column", d, False, "BOUNDARY_COLUMN", "alignment", "A morpheme boundary column cannot mix with a segment.")
    d = deepcopy(boundary); d["sites"].append(dict(id="boundary-site", alignment_id="boundary-a", column_index=1))
    add("boundary-promoted-to-site", d, False, "SITE_COVERAGE", "registry", "A boundary is preserved but not promoted to a sound correspondence.")
    for name, cells in [("leading-boundary", [BOUNDARY, seg("p")]), ("trailing-boundary", [seg("p"), BOUNDARY]),
                        ("adjacent-boundaries", [seg("p"), BOUNDARY, BOUNDARY, seg("t")])]:
        d = dossier(name, [alignment(name, [cells, cells, None, None])], supports=[1])
        add(name, d, False, "ORIGINAL_SHAPE", "alignment", "Boundaries separate nonempty original spans.")
    for name, cells in [("all-gap-column", [GAP]), ("all-missing-column", None)]:
        a = alignment(name, [cells, cells, None, None]); d = dossier(name, [a], supports=[1])
        add(name, d, False, "VOID_COLUMN", "alignment", "A column with only gaps and absence has no original material.")
    d = dossier("unknown-only", [alignment("unknown-only", [[UNKNOWN], [UNKNOWN], None, None])], [], [])
    add("unknown-only-alignment", d["alignment_data"], kind="alignment", rationale="Unknown readings remain in a valid alignment.")
    add("unknown-only-dossier", d, False, "NO_SITES", "support", "Unknown readings alone cannot supply a correspondence site.")
    d = deepcopy(base); d["alignment_data"]["alignments"][1]["evidence_unit"] = "a-root"; d["groups"][0]["claimed_support"] = 1
    add("repeated-source-counted-once", d, rationale="One declared unit counts once even through two alignment records.")
    d = deepcopy(base); d["groups"] = [dict(id=f"singleton-{i}", members=[s["id"]], claimed_support=1) for i, s in enumerate(d["sites"])]
    add("nonminimum-feasible-partition", d, rationale="Two singleton groups are feasible even though this data also permits one group; no minimum is asserted.")
    add("one-group-feasible-partition", base, rationale="The same observations also permit one group; feasibility alone selects neither partition.")
    chain = dossier("nontransitive", [one_column("chain-a", [seg("p"), seg("t"), None, None]),
                                      one_column("chain-b", [seg("p"), None, None, None]),
                                      one_column("chain-c", [seg("p"), seg("k"), None, None])])
    add("nontransitive-merge", chain, False, "PAIR_CONFLICT", "nontransitivity", "AB and BC are compatible but AC conflicts; a connected component is not a clique.")
    for name, blocks in [("nontransitive-partition-ab", [[0, 1], [2]]), ("nontransitive-partition-bc", [[0], [1, 2]])]:
        d = dossier(name, chain["alignment_data"]["alignments"], blocks, [len(b) for b in blocks])
        add(name, d, rationale="Each group is checked pairwise; an alternative feasible partition is retained.")
    d = dossier("gap-conflict", [one_column("gap-a", [seg("p"), GAP, None, None]), one_column("gap-b", [seg("p"), seg("t"), None, None])])
    add("gap-is-observed", d, False, "PAIR_CONFLICT", "missing-gap", "Unlike absence, a gap conflicts with a segment in the same position.")
    d = dossier("unicode-literal", [one_column("unicode-a", [seg("a̱"), seg("𐀀"), None, None]), one_column("unicode-b", [seg("a̱"), seg("𐀀"), None, None])])
    add("unicode-literal", d, rationale="Combining marks and literal supplementary characters are atomic and preserved.")
    d = dossier("unicode-distinct", [one_column("unicode-a", [seg("p"), seg("á"), None, None]), one_column("unicode-b", [seg("p"), seg("á"), None, None])])
    add("no-silent-normalization", d, False, "PAIR_CONFLICT", "unicode", "Canonically related Unicode spellings remain distinct unless evidence normalization explicitly records a change.")
    files["manifest.json"] = encode(dict(schema_version="1.0.0", suite="correspondence-sites", fixtures=entries))
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(); files = generate()
    expected = {DEST / p for p in files}
    if args.check:
        assert set(DEST.rglob("*.json")) == expected, "Unexpected or missing M3 fixture file"
        for path, content in files.items():
            assert (DEST / path).read_bytes() == content, "Stale M3 fixture: " + path
    else:
        for path, content in files.items():
            target = DEST / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(content)
        assert set(DEST.rglob("*.json")) == expected, "Remove obsolete generated fixtures explicitly"
    print(f"M3: {len(files)-1} generated fixtures {'verified' if args.check else 'written'}")


if __name__ == "__main__":
    main()
