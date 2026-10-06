"""Check catalogue coverage and execute selected reconstruction queries in Lean."""
import argparse
import hashlib
from pathlib import Path
from pycldf import Dataset

from build_pie_corpus import ROOT, encoded
from materials import coverage, read, DEST
from explore_reconstructions import (BIN, VOICE, SOURCES, catalogue, strict_read,
    select_pool, select_bounded, execute_pool, execute_bounded)


def verify(binary_dir=BIN):
    current = coverage()
    assert current == read(DEST / "coverage.json"), "Stale coverage"
    for dataset in ("iecor", "hillburmish", "sagartst"):
        assert Dataset.from_metadata(ROOT / "data/upstream" / dataset / "cldf/cldf-metadata.json").validate(), dataset
    runs = []
    for dataset, case, explain in [("pie", "set-21", None), ("latin", "latin-21", None),
            ("kuki-chin", "vb-1-unmarked", ["ɓ", "a", "a", "n"]),
            ("tibetan-merger", "merged-affricate-pool", ["p"])]:
        request = select_pool(dataset, case, explain=explain)
        r, code = execute_pool(request, binary_dir)
        assert code == 0 and r["complete"]
        if dataset == "tibetan-merger":
            assert r["result"]["inverse"][0]["candidates"] == [["ndz"], ["dz"]]
            assert not r["explanations"][0]["satisfies_observations"]
            assert all(not b["exact"] and b["certificate_accepted"] for b in r["explanations"][0]["branches"])
        runs.append(dict(id=dataset + ":" + case, result=r))
    for scope, omit in [("northern-only", []), ("all-groups", ["vb-mara"])]:
        request = select_pool("kuki-chin", "vb-1-unmarked", ["correspondence"], scope, omit=omit)
        r, code = execute_pool(request, binary_dir)
        assert code == 0
        runs.append(dict(id="kuki-chin:" + scope + (":withheld" if omit else ""), result=r))
    for choices, budget, expected in [([], None, [["p"], ["b"]]),
            (["voice-analysis=N-anticausative"], None, [["p"]]),
            (["voice-analysis=s-devoicing"], None, [["b"]]), ([], 0, [])]:
        request = select_bounded(strict_read(VOICE), choices=choices, budget=budget)
        r, code = execute_bounded(request, binary_dir)
        assert code == (3 if budget == 0 else 0)
        assert [c["protoform"] for c in r["candidates"]] == expected
        assert r["complete"] is (budget != 0)
        if budget == 0:
            assert not r["no_candidate_in_scope"]
        runs.append(dict(id="voice:" + (choices[0] if choices else "all") + (":budget0" if budget == 0 else ""), result=r))
    sources = ["scripts/materials.py", "scripts/build_materials.py", "scripts/explore_reconstructions.py", "scripts/verify_explorer.py",
        "scripts/run_reconstruction.py", "scripts/reference_reconstruction.py", "scripts/reference_rules.py", "scripts/verify_m5.py",
        "scripts/build_kuki_corpus.py", "scripts/build_pie_corpus.py", "scripts/import_cldf.py", "data/upstream/manifest.json",
        "tests/test_explorer.py", "data/materials/sources.json", "data/materials/coverage.json", "data/materials/vanbik-initials.json",
        "data/kuki-chin/joint-analysis-input.json", *SOURCES.values(), "docs/13-materials-and-exploration.md", ".github/workflows/exploration.yml"]
    sources += [str(p.relative_to(ROOT)) for p in (ROOT / "lean").rglob("*.lean") if ".lake" not in p.parts]
    sources += ["lean/lakefile.toml", "lean/lean-toolchain", "requirements.txt"]
    return dict(schema_version="1.0.0", passed=True, catalogue=current,
        registered_pool_queries={dataset: len(catalogue(dataset)) for dataset in SOURCES},
        checks=dict(snapshot_hashes=True, cldf_validation=True, complete_source_row_unit_tests="tests/test_explorer.py",
            lean_and_independent_interpreter_agree=True, selected_lean_runs=len(runs), frozen_studies="unchanged"),
        input_hashes={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sorted(set(sources))},
        executions=runs,
        limitations=["No new sound-change models are inferred from the expanded catalogue.",
            "The 509 registered pool queries retain their original experimental limitations; identity/correspondence are baselines.",
            "Source transcription and historical hypotheses still require specialist review."])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary-dir", type=Path, default=BIN)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = encoded(verify(args.binary_dir.resolve()))
    path = ROOT / "reports/materials-and-exploration.json"
    if args.check:
        assert path.read_bytes() == result, "Stale exploration verification report"
    else:
        path.write_bytes(result)
    print("Source coverage, CLDF validity, hypothesis selection and 10 Lean executions passed.")


if __name__ == "__main__":
    main()
