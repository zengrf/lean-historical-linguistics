"""Reproduce reflex-only examples and a 1000-row scaling control for M7."""

import argparse
from copy import deepcopy
from itertools import islice, product

from build_pie_corpus import ROOT, encoded
from build_research_examples import rule, package
from explore_reconstructions import strict_read
from lexicon import to_tsv
from materials import rows

DEST = ROOT / "data/lexicon"


def request(
    id,
    inventory,
    languages,
    models,
    entries,
    minimum=0,
    maximum=4,
    description="Synthetic inverse-search control; no historical claim.",
):
    return dict(
        schema_version="1.0.0",
        id=id,
        description=description,
        languages=[dict(id=x, label=x) for x in languages],
        proto_inventory=inventory,
        min_length=minimum,
        max_length=maximum,
        phonotactics=None,
        analyses=models,
        entries=entries,
    )


def model(
    id,
    languages,
    inventory,
    rules_by_language,
    description="Explicit synthetic model",
    source="synthetic:M7",
):
    return dict(
        id=id,
        description=description,
        source_ref=source,
        branches=[
            dict(language_id=d, package=package(id + "-" + d, inventory, rs))
            for d, rs in zip(languages, rules_by_language)
        ],
    )


def entry(id, languages, forms, meaning=None, source="synthetic:M7"):
    return dict(
        id=id,
        meaning=meaning or id,
        reflexes=[
            dict(language_id=d, form=f, source_ref=source)
            for d, f in zip(languages, forms)
        ],
    )


def merger():
    ds, inv = ["A", "B"], ["p", "b", "t", "d", "a"]
    ms = [
        model(
            "mergers",
            ds,
            inv,
            [[rule("b", "p"), rule("d", "t")]] * 2,
            "Both daughters merge b with p and d with t",
        ),
        model("identity", ds, inv, [[], []], "Both daughters preserve every segment"),
    ]
    return request(
        "two-mergers",
        inv,
        ds,
        ms,
        [entry("one", ds, [["p", "a"]] * 2), entry("two", ds, [["t", "a"]] * 2)],
        minimum=2,
        maximum=2,
    )


def deletion():
    ds, inv = ["A", "B"], ["p", "h", "a"]
    m = model("loss", ds, inv, [[rule("h", None)]] * 2, "Both daughters lose h")
    return request(
        "deletion",
        inv,
        ds,
        [m],
        [entry("one", ds, [["p", "a"], [None, "a"]]), entry("empty", ds, [[], None])],
        maximum=4,
    )


def conflict():
    ds, inv = ["A", "B"], ["p", "b"]
    ms = [
        model("to-p", ds, inv, [[rule("b", "p")]] * 2),
        model("to-b", ds, inv, [[rule("p", "b")]] * 2),
    ]
    return request(
        "global-conflict",
        inv,
        ds,
        ms,
        [entry("p-row", ds, [["p"]] * 2), entry("b-row", ds, [["b"]] * 2)],
        maximum=1,
    )


def contextual():
    ds, inv = ["A", "B"], ["p", "b", "a"]
    m = model(
        "intervocalic", ds, inv, [[rule("p", "b", left=[["a"]], right=[["a"]])], []]
    )
    return request(
        "contextual",
        inv,
        ds,
        [m],
        [entry("one", ds, [["a", "b", "a"], ["a", "p", "a"]])],
        maximum=3,
    )


def kuki():
    ds, inv = ["Mizo", "Thado-Kuki"], ["b", "ɓ", "a", "n"]
    m = model(
        "b-merger-projection",
        ds,
        inv,
        [[rule("ɓ", "b")]] * 2,
        "Segmental b/ɓ merger projection; tone and the remaining correspondence system are outside this example",
        "vanbik2009:PDF93:entry1; restricted M7 projection",
    )
    return request(
        "kuki-chin-arm",
        inv,
        ds,
        [m],
        [
            entry(
                "arm",
                ds,
                [["b", "a", "a", "n"]] * 2,
                "ARM",
                "vanbik2009:PDF93:entry1; source báan; tone omitted, repeated a retained",
            )
        ],
        minimum=1,
        maximum=6,
        description="VanBik ARM: Mizo and Thado Kuki báan, projected to b a a n with tone omitted. The source's reconstructed form is not supplied. Both b and ɓ are permitted; this projection cannot decide between them. This is not a full Kuki-Chin or Sino-Tibetan sound-law model.",
    )


def pie():
    source = strict_read(ROOT / "data/pie/lexical-input.json")
    packages = {p["id"]: p for p in source["packages"]}
    # Read only the retained daughter rows and existing rule packages. Never use
    # source['inverse'], its pool/reference fields, or a published root to search.
    raw = {r["ID"]: r for r in rows("iecor", "forms")}
    langs = ["127", "239", "189"]
    names = {r["ID"]: r["Name"] for r in rows("iecor", "languages")}
    inv = [
        "p",
        "b",
        "t",
        "d",
        "k",
        "ḱ",
        "g",
        "ǵ",
        "s",
        "m",
        "n",
        "l",
        "r",
        "w",
        "j",
        "e",
        "o",
        "a",
        "i",
        "u",
        "h1",
        "h2",
        "h3",
    ]
    models = [
        dict(
            id="m5-fitted-correspondences",
            description="M5 fitted segment correspondences; an experimental baseline, not established PIE-to-daughter histories",
            source_ref="data/pie/experiment.json; fitted model retains its original training provenance",
            branches=[
                dict(
                    language_id="ie-" + d,
                    package=deepcopy(packages["correspondence-" + d]),
                )
                for d in langs
            ],
        )
    ]
    forms = [raw[d + "-93-1"]["Phonemic_Segments"].split() for d in langs]
    e = entry(
        "leg",
        ["ie-" + d for d in langs],
        forms,
        "LEG",
        "iecor:cldf/forms.csv; cognateset2156",
    )
    for f, d in zip(e["reflexes"], langs):
        f["source_ref"] = "data/upstream/iecor/cldf/forms.csv#ID=" + d + "-93-1"
    r = request(
        "pie-leg-reflexes",
        inv,
        ["ie-" + d for d in langs],
        models,
        [e],
        maximum=6,
        description="IE-CoR LEG reflexes in Old Irish, Middle Welsh and Neapolitan. Enumerates a segment alphabet under the existing M5 fitted correspondence baseline. No published protoform pool is supplied. Model fit is not independent historical validation; morphology and chronology are incomplete.",
    )
    r["languages"] = [dict(id="ie-" + d, label=names[d]) for d in langs]
    return r


def scaling(n=1000):
    ds = ["A", "B", "C"]
    inv = ["p", "b", "t", "d", "k", "g", "s", "z"]
    laws = [rule("b", "p"), rule("d", "t"), rule("g", "k"), rule("z", "s")]
    m = model("four-mergers", ds, inv, [laws] * 3)
    return request(
        "scaling-1000",
        inv,
        ds,
        [m],
        [
            entry(f"row-{i}", ds, [list(w)] * 3)
            for i, w in enumerate(islice(product(["p", "t", "k", "s"], repeat=6), n))
        ],
        minimum=6,
        maximum=6,
        description="1000 distinct synthetic cognate rows, three daughters, four mergers; each row has 64 roots and one global model licenses 64^1000 protolexicons.",
    )


def build():
    return {
        f.__name__ + ".json": f()
        for f in [merger, deletion, conflict, contextual, kuki, pie, scaling]
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    DEST.mkdir(exist_ok=True)
    for name, value in build().items():
        for path, raw in [
            (DEST / name, encoded(value)),
            (DEST / name.replace(".json", ".tsv"), to_tsv(value).encode()),
        ]:
            if args.check:
                assert path.read_bytes() == raw, "Stale M7 example: " + path.name
            else:
                path.write_bytes(raw)
    print("M7 reflex-only examples and TSV tables reproduced.")


if __name__ == "__main__":
    main()
