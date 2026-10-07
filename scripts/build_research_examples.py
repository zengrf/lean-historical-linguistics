"""Source-worked and synthetic controls for the research interface."""

import argparse
from copy import deepcopy
import hashlib

from build_pie_corpus import ROOT, encoded
from explore_reconstructions import strict_read

DEST = ROOT / "data/research"


def rule(target, replacement, **kwargs):
    return (
        dict(
            target=[target],
            replacement=replacement,
            left=[],
            right=[],
            left_edge=False,
            right_edge=False,
            direction="left-to-right",
            mode="simultaneous",
        )
        | kwargs
    )


def package(id, inventory, rules=()):
    laws = []
    for i, r in enumerate(rules):
        laws.append(
            dict(
                id=f"{id}-law-{i}",
                input_stage="stem" if i == 0 else f"{id}-stage-{i}",
                output_stage=f"{id}-stage-{i+1}",
                rule=r,
            )
        )
    return dict(
        id=id,
        version="1.0.0",
        description="Explicit finite realization package",
        inventory=inventory,
        initial_stage="stem",
        final_stage=laws[-1]["output_stage"] if laws else "stem",
        laws=laws,
    )


def cell(id, inventory, source_ref, expected=None):
    return dict(
        id=id,
        source_ref=source_ref,
        prefix=[],
        suffix=[],
        allomorphs=[],
        stem=package(id + "-stem", inventory),
        sound=package(id + "-sound", inventory),
        tone_rules=[],
        expected=expected,
    )


def tone_rule(id, before, after, **kwargs):
    return (
        dict(
            id=id,
            from_tone=before,
            to_tone=after,
            initial_class=[],
            final_class=[],
            conditioning="stem",
        )
        | kwargs
    )


def tone_example():
    # Both tables were inspected as rendered pages, not inferred from column order in PDF text.
    inventory = ["σ"]
    maps = {
        "Hakha-Lai": ["F", "L", "R", "F"],
        "Mizo": ["R", "F", "L", "H"],
        "Mara": ["H", "H", "M", "L"],
        "Tedim": ["1", "1", "3", "2"],
    }
    proto = [f"vb-PKC-{i}" for i in range(1, 5)]
    tone_inventory = proto + [
        f"vb-{d}-{t}" for d, ts in maps.items() for t in dict.fromkeys(ts)
    ]
    analyses = []
    for aid in ["table-164", "table-166-Hakha-2"]:
        cells = []
        for d, values in maps.items():
            values = list(values)
            if aid == "table-166-Hakha-2" and d == "Hakha-Lai":
                values[1] = "F"
            source = "vanbik2009:PDF482:Table164"
            if aid == "table-166-Hakha-2" and d == "Hakha-Lai":
                source += ";PDF493:Table166"
            c = cell(
                d, inventory, source, dict(segments=[], tone=f"vb-{d}-{maps[d][0]}")
            )
            c["tone_rules"] = [
                tone_rule(f"{d}-tone-{i}", proto[i], f"vb-{d}-{t}")
                for i, t in enumerate(values)
            ]
            cells.append(c)
        analyses.append(
            dict(
                id=aid,
                description=(
                    "Table 164 correspondences"
                    if aid == "table-164"
                    else "Table 164 with the printed Table 166 Hakha Lai tone-2 reading; source inconsistency retained"
                ),
                source_ref="vanbik2009:PDF482,493; observations:PDF485:entry243",
                cells=cells,
            )
        )
    return dict(
        schema_version="1.0.0",
        id="vanbik-smooth-tones",
        source_kind="source-worked",
        source_scope="VanBik 2009 PKC nominal smooth-syllable tone correspondence projection; no segmental derivation. Observed tone-1 pattern exemplified by WATER [243].",
        inventory=inventory,
        tone_inventory=tone_inventory,
        pool=[dict(segments=[], tone=t) for t in proto],
        analyses=analyses,
    )


def stem_example():
    inventory = ["ɓ", "b", "e", "l", "ʔ", "h"]
    first = ["ɓ", "e", "e", "l"]
    second = ["ɓ", "e", "l", "ʔ"]
    cells = []
    for id, expected, allomorph in [
        ("Mizo-I", ["b", "e", "e", "l"], False),
        ("Mizo-II", ["b", "e", "l", "h"], True),
        ("Hakha-I", ["b", "e", "l", "ʔ"], True),
        ("Hakha-II", ["b", "e", "l", "ʔ"], True),
    ]:
        c = cell(
            id, inventory, "vanbik2009:PDF93:entry2", dict(segments=expected, tone=None)
        )
        if allomorph:
            c["allomorphs"] = [dict(input=first, output=second)]
        c["sound"] = package(
            id + "-sound",
            inventory,
            [rule("ɓ", "b")] + ([rule("ʔ", "h")] if id.startswith("Mizo") else []),
        )
        cells.append(c)
    return dict(
        schema_version="1.0.0",
        id="vanbik-attach-stems",
        source_kind="source-worked",
        source_scope="VanBik 2009 entry [2] ATTACH: linked PKC Form I/II and Hakha Lai invariant stem, projected to displayed segment strings with tone omitted. Mizo h is a source-spelling projection, not a new phonetic claim; allomorphy is stipulated from this entry, not inferred as a productive rule.",
        inventory=inventory,
        tone_inventory=[],
        pool=[dict(segments=first, tone=None), dict(segments=second, tone=None)],
        analyses=[
            dict(
                id="linked-stems",
                description="Published paired stems and invariant Hakha Lai reflex",
                source_ref="vanbik2009:PDF93:entry2;PDF38:stem-function caveat",
                cells=cells,
            )
        ],
    )


def affix_example():
    inventory = ["b", "p", "a", "e", "s", "n"]
    cells = []
    for id, prefix, suffix, vowel, tone in [
        ("singular", [], [], "a", "L"),
        ("plural", ["n", "+"], ["+", "s"], "e", "H"),
    ]:
        expected = prefix + ["p", vowel] + suffix
        c = cell(
            id,
            inventory,
            "synthetic:affix-and-tone-control",
            dict(segments=expected, tone=tone),
        )
        c.update(prefix=prefix, suffix=suffix)
        if id == "plural":
            c["stem"] = package(id + "-stem", inventory, [rule("a", "e")])
        c["sound"] = package(id + "-sound", inventory, [rule("b", "p")])
        c["tone_rules"] = [tone_rule(id + "-tone", "T", tone, initial_class=["b"])]
        cells.append(c)
    return dict(
        schema_version="1.0.0",
        id="affix-tone-control",
        source_kind="synthetic",
        source_scope="Synthetic linked singular/plural: prefixation, suffixation, vowel alternation and tone conditioned on the stem before devoicing. No historical claim.",
        inventory=inventory,
        tone_inventory=["T", "L", "H"],
        pool=[dict(segments=[s, "a"], tone="T") for s in ["b", "p"]],
        analyses=[
            dict(
                id="stem-conditioned",
                description="Morphology precedes the declared word-level sound change",
                source_ref="synthetic",
                cells=cells,
            )
        ],
    )


def chronology_example():
    original = strict_read(ROOT / "data/pie/diagnostic-input.json")["packages"][0]
    blocks = []
    for id, label, start, end in [
        ("grimm", "Grimm fragment", 0, 16),
        ("verner", "Verner fragment", 16, 21),
        ("stress", "Initial stress", 21, 31),
    ]:
        blocks.append(
            dict(
                id=id,
                label=label,
                rules=[l["rule"] for l in original["laws"][start:end]],
                source_ref="ringe2022:pp55-56:M5-VCV-fragment",
            )
        )
    return dict(
        schema_version="1.0.0",
        id="germanic-order",
        description="Order the three fixed M5 rule blocks. Restricted accent-marked VCV controls, not full PIE-to-Germanic histories.",
        source_kind="source-inspired-control",
        source_ref="data/pie/source-analyses.json:Ringe2022",
        inventory=original["inventory"],
        blocks=blocks,
        constraints=[],
        probes=[
            dict(
                id="unaccented-medial",
                input=["a", "t", "é"],
                expected=["á", "ð", "e"],
                source_ref="M5:ringe-vcv-control",
            ),
            dict(
                id="accented-medial",
                input=["á", "t", "e"],
                expected=["á", "θ", "e"],
                source_ref="M5:ringe-vcv-control",
            ),
        ],
    )


def build():
    # Existing bounded fixtures remain available; a small explicit source-free case
    # demonstrates a pairwise conflict and a useful withheld observation.
    inventory = ["p", "b"]
    branches = [
        dict(doculect_id=d, package=package("demo-" + d, inventory))
        for d in ["A", "B", "C"]
    ]
    spec = dict(
        schema_version="1.0.0",
        id="evidence-control",
        description="Synthetic identity branches: A=p and B=b conflict; withholding B preserves p. C is an additional explicit observation.",
        source_kind="synthetic",
        claim="bounded-relative-completeness",
        proto_inventory=inventory,
        allow_morphemes=False,
        max_length=1,
        analysis_bound=1,
        max_rules_per_branch=0,
        doculects=["A", "B", "C"],
        choice_groups=[],
        candidate_budget=100,
        time_limit_ms=None,
        analyses=[
            dict(
                id="identity",
                description="Synthetic identity model",
                proto_node_id="stem",
                choice_bindings=[],
                branches=branches,
                observations=[
                    dict(
                        doculect_id=d,
                        source_ref="synthetic",
                        form=[dict(kind="segment", value=v)],
                    )
                    for d, v in [("A", "p"), ("B", "b"), ("C", "p")]
                ],
                alignment_evidence=None,
            )
        ],
    )
    readings = dict(
        source_id="vanbik2009",
        sha256=hashlib.sha256(
            (ROOT / "library/open/vanbik2009.pdf").read_bytes()
        ).hexdigest(),
        pages_read=[37, 38, 93, 479, 480, 481, 482, 483, 484, 485, 493],
        rendered_tables_checked=[164, 166],
        discrepancy="Table164 (PDF482) gives Hakha Lai L for PKC tone2; Table166 (PDF493) prints F, while entry7 on that page gives L. Both table readings are retained as explicit analyses; no emendation or specialist signoff is claimed.",
        limitations=[
            "Only smooth nominal tone correspondences are modeled; Khumi's conditioned variants are excluded.",
            "Verbal tones, sandhi, polysyllabic association and the functions of Form I/II are not inferred.",
            "Entry2 stem allomorphy is lexical and is not generalized to a productive rule.",
        ],
    )
    return {
        "tone-paradigm.json": tone_example(),
        "stem-paradigm.json": stem_example(),
        "affix-control.json": affix_example(),
        "germanic-chronology.json": chronology_example(),
        "evidence-control.json": spec,
        "source-readings.json": readings,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    DEST.mkdir(exist_ok=True)
    for name, value in build().items():
        path = DEST / name
        if args.check:
            assert path.read_bytes() == encoded(value), (
                "Stale research example: " + name
            )
        else:
            path.write_bytes(encoded(value))
    print("Research examples and source reading record reproduced.")


if __name__ == "__main__":
    main()
