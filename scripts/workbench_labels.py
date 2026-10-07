"""Display names from retained sources; identifiers and model inputs stay intact."""

from functools import lru_cache
import re

from build_pie_corpus import ROOT
from explore_reconstructions import strict_read


@lru_cache(maxsize=3)
def source_sets(dataset):
    path, key = {
        "pie": ("data/pie/corpus.json", "sets"),
        "latin": ("data/pie/latin-control-frozen.json", "samples"),
        "kuki-chin": ("data/kuki-chin/corpus.json", "sets"),
    }[dataset]
    return {s["id"]: s for s in strict_read(ROOT / path)[key]}


def case_labels(dataset, case):
    if dataset == "tibetan-merger":
        return dict(title="Affricate merger · source fragment", languages={})
    number = re.search(r"\d+", case).group()
    source = source_sets(dataset)[number]
    if dataset == "pie":
        meaning = ", ".join(
            dict.fromkeys(r["raw_meaning"]["Name"] for r in source["records"])
        )
        languages = {r["id"]: r["raw_language"]["Name"] for r in source["records"]}
        title = f"{meaning} · set {number}"
    elif dataset == "latin":
        title = f"{source['latin']['Gloss']} · {source['latin']['Form']} · set {number}"
        languages = {
            f"romance-{r['ID']}": r["Name"] for r in source["daughter_varieties"]
        }
    else:
        stem = case.removeprefix(f"vb-{number}-").replace("unmarked", "unmarked forms")
        title = f"{source['label'].lower()} · entry {number} · {stem}"
        languages = {r["doculect_id"]: r["source_alias"] for r in source["records"]}
    return dict(title=title, languages=languages)


def analysis_label(identifier):
    return {
        "table-164": "Table 164 correspondences",
        "table-166-Hakha-2": "Table 166 reading for Hakha Lai tone 2",
        "identity": "Identity model (no sound changes)",
        "correspondence": "Declared sound correspondences",
        "N-anticausative": "N-anticausative analysis",
        "s-devoicing": "s-devoicing analysis",
    }.get(identifier, identifier.replace("-", " "))


def axis_label(identifier):
    return {
        "Hakha-Lai": "Hakha Lai",
        "MC-transitive": "Middle Chinese · transitive",
        "MC-intransitive": "Middle Chinese · intransitive",
    }.get(identifier, identifier.replace("-", " "))
