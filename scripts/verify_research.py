"""Execute the research operations in Lean and independently check their results."""

import argparse
from copy import deepcopy
import hashlib
from itertools import product
import json
from pathlib import Path
import re
import subprocess
import tempfile

from build_pie_corpus import ROOT, encoded
from build_research_examples import build
from explore_reconstructions import BIN, strict_read, VOICE
from research import (
    checked,
    analyze_bounded,
    analyze_pool,
    analyze_paradigm,
    explore_chronology,
    EXAMPLES,
)


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def verify(binary_dir=BIN):
    for name, value in build().items():
        assert (EXAMPLES / name).read_bytes() == encoded(value), name
    matrices = 0
    matrix_digests = []
    # Exhaust every 3-history/2-axis Boolean agreement matrix and selected domain.
    for bits in product([False, True], repeat=6):
        for selection in [[], [0], [1], [0, 1]]:
            request = dict(
                schema_version="1.0.0",
                id="exhaustive-matrix",
                axes=["A", "B"],
                selected=selection,
                subset_budget=4,
                histories=[
                    dict(
                        id=f"h-{i}",
                        agreements=list(bits[2 * i : 2 * i + 2]),
                        predictions=[str(v) for v in bits[2 * i : 2 * i + 2]],
                    )
                    for i in range(3)
                ],
            )
            result = checked("matrix", request, binary_dir)
            matrix_digests.append(digest(result))
            matrices += 1
    executions = []

    def record(id, result):
        assert result["complete"]
        analysis = result.get("analysis", {})
        executions.append(
            dict(
                id=id,
                complete=result["complete"],
                result_sha256=digest(result),
                histories=len(result.get("histories", [])),
                survivors=analysis.get("survivors", []),
                minimal_conflicts=analysis.get("minimal_conflicts", []),
                equivalence_classes=analysis.get("equivalence_classes", []),
                probes=analysis.get("probes", []),
                orders=[
                    dict(order=x["order"], matches=x["agrees_with_observations"])
                    for x in result.get("orders", [])
                ],
                cyclic=result.get("cyclic"),
            )
        )

    for dataset, case in [
        ("pie", "set-21"),
        ("latin", "latin-21"),
        ("kuki-chin", "vb-1-unmarked"),
        ("tibetan-merger", "merged-affricate-pool"),
    ]:
        result = analyze_pool(dataset, case, binary_dir=binary_dir)
        record(dataset, result)
    for key in ["tone-paradigm", "stem-paradigm", "affix-control"]:
        data = strict_read(EXAMPLES / (key + ".json"))
        result = analyze_paradigm(data, binary_dir=binary_dir)
        assert len(result["analysis"]["survivors"]) == (
            2 if key == "tone-paradigm" else 1
        )
        record(key, result)
    data = strict_read(EXAMPLES / "tone-paradigm.json")
    r = analyze_paradigm(data, selected=["Hakha-Lai"], binary_dir=binary_dir)
    assert (
        len(r["analysis"]["survivors"]) == 5
        and len(r["analysis"]["equivalence_classes"]) == 1
    )
    assert [p["distinguished_pairs"] for p in r["analysis"]["probes"]] == [8, 6, 6]
    record("tone-merger-and-probes", r)
    record(
        "tone-table164-only",
        analyze_paradigm(
            data, ["table-164"], selected=["Hakha-Lai"], binary_dir=binary_dir
        ),
    )
    data = strict_read(EXAMPLES / "affix-control.json")
    for c in data["analyses"][0]["cells"]:
        c["expected"]["tone"] = None
    r = analyze_paradigm(data, binary_dir=binary_dir)
    assert len(r["analysis"]["survivors"]) == 2
    assert len(r["analysis"]["equivalence_classes"]) == 1
    record("unobserved-tone", r)
    data["pool"][0]["tone"] = None
    record("unknown-input-tone", analyze_paradigm(data, binary_dir=binary_dir))
    data = strict_read(EXAMPLES / "evidence-control.json")
    r = analyze_bounded(data, binary_dir=binary_dir)
    assert {tuple(c) for c in r["analysis"]["minimal_conflicts"]} == {(0, 1), (1, 2)}
    record("two-conflicts", r)
    record(
        "withheld-conflict",
        analyze_bounded(data, selected=["A", "C"], binary_dir=binary_dir),
    )
    record(
        "empty-selected-domain",
        analyze_bounded(data, selected=[], binary_dir=binary_dir),
    )
    partial = analyze_bounded(data, subset_budget=0, binary_dir=binary_dir)
    assert not partial["complete"] and not partial["analysis"]["conflicts_complete"]
    assert partial["analysis"]["survivors"] == []
    record(
        "joint-voice-analyses",
        analyze_bounded(strict_read(VOICE), binary_dir=binary_dir),
    )
    for selection in [["N-anticausative"], ["s-devoicing"]]:
        r = analyze_bounded(
            strict_read(VOICE), analyses=selection, binary_dir=binary_dir
        )
        assert len(r["analysis"]["survivors"]) == 1
        record(selection[0], r)
    chronology = strict_read(EXAMPLES / "germanic-chronology.json")
    r = explore_chronology(chronology, binary_dir=binary_dir)
    assert len(r["orders"]) == 6
    assert [o["order"] for o in r["orders"] if o["agrees_with_observations"]] == [
        ["grimm", "verner", "stress"]
    ]
    record("six-chronologies", r)
    edge = dict(earlier="verner", later="grimm")
    r = explore_chronology(chronology, [edge], binary_dir=binary_dir)
    assert len(r["orders"]) == 3 and not any(
        o["agrees_with_observations"] for o in r["orders"]
    )
    record("counterfeeding-orders", r)
    r = explore_chronology(
        chronology, [edge, dict(earlier="grimm", later="verner")], binary_dir=binary_dir
    )
    assert r["cyclic"] and not r["orders"]
    record("cycle", r)
    count = 0
    for n in range(7):
        request = dict(
            schema_version="1.0.0",
            id="permutations",
            rule_ids=list("abcdef"[:n]),
            constraints=[],
        )
        out = checked("chronology", request, binary_dir)
        count += len(out["orders"])
    rejected = []
    matrix = dict(
        schema_version="1.0.0",
        id="valid",
        axes=["A"],
        selected=[0],
        subset_budget=2,
        histories=[dict(id="h", agreements=[True], predictions=["a"])],
    )
    p = strict_read(EXAMPLES / "affix-control.json")
    order = dict(
        schema_version="1.0.0", id="order", rule_ids=["a", "b"], constraints=[]
    )
    invalid = []

    def bad(mode, label, base, mutate):
        data = deepcopy(base)
        mutate(data)
        invalid.append((mode, label, encoded(data)))

    bad("matrix", "empty-history-universe", matrix, lambda x: x.update(histories=[]))
    bad("matrix", "repeated-axis", matrix, lambda x: x.update(axes=["A", "A"]))
    bad("matrix", "unknown-axis", matrix, lambda x: x.update(selected=[1]))
    bad("matrix", "repeated-selection", matrix, lambda x: x.update(selected=[0, 0]))
    bad(
        "matrix",
        "wrong-dimension",
        matrix,
        lambda x: x["histories"][0].update(predictions=[]),
    )
    bad("matrix", "budget-too-large", matrix, lambda x: x.update(subset_budget=4097))
    bad("matrix", "unknown-field", matrix, lambda x: x.update(surprise=True))
    bad(
        "matrix",
        "nested-unknown-field",
        matrix,
        lambda x: x["histories"][0].update(surprise=True),
    )
    bad("matrix", "negative-index", matrix, lambda x: x.update(selected=[-1]))
    bad(
        "chronology",
        "unknown-edge",
        order,
        lambda x: x.update(constraints=[dict(earlier="a", later="c")]),
    )
    bad("chronology", "repeated-rule", order, lambda x: x.update(rule_ids=["a", "a"]))
    bad(
        "chronology",
        "too-many-rules",
        order,
        lambda x: x.update(rule_ids=list("abcdefg")),
    )
    bad("paradigm", "unknown-tone", p, lambda x: x["pool"][0].update(tone="invented"))
    bad("paradigm", "repeated-root", p, lambda x: x["pool"].append(x["pool"][0]))
    bad("paradigm", "no-analyses", p, lambda x: x.update(analyses=[]))
    bad(
        "paradigm",
        "repeated-cell",
        p,
        lambda x: x["analyses"][0]["cells"].append(x["analyses"][0]["cells"][0]),
    )
    bad(
        "paradigm",
        "unknown-conditioning",
        p,
        lambda x: x["analyses"][0]["cells"][0]["tone_rules"][0].update(
            conditioning="hidden"
        ),
    )
    bad(
        "paradigm",
        "unlisted-affix",
        p,
        lambda x: x["analyses"][0]["cells"][0].update(prefix=["x"]),
    )
    bad(
        "paradigm",
        "ambiguous-allomorph",
        p,
        lambda x: x["analyses"][0]["cells"][0].update(
            allomorphs=[
                dict(input=["a"], output=["b"]),
                dict(input=["a"], output=["p"]),
            ]
        ),
    )
    bad(
        "paradigm",
        "invalid-sound-package",
        p,
        lambda x: x["analyses"][0]["cells"][0]["sound"].update(final_stage="unknown"),
    )
    invalid.extend(
        [
            ("matrix", "invalid-utf8", b"\xff"),
            ("matrix", "duplicate-key", b'{"id":"x","id":"y"}'),
            ("matrix", "non-json-number", b'{"id":NaN}'),
        ]
    )
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "invalid.json"
        for mode, label, raw in invalid:
            path.write_bytes(raw)
            out = subprocess.run(
                [str(binary_dir / "research_check"), "--" + mode, str(path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert out.returncode == 1, (label, out.stdout, out.stderr)
            result = json.loads(out.stdout)
            assert result["input_valid"] is False and result["complete"] is False
            rejected.append(label)
    theorem_names = re.findall(
        r"^#print axioms (Historical\.(?:Research|Paradigm)\.\S+)",
        (ROOT / "lean/Audit.lean").read_text(),
        re.M,
    )
    assert len(theorem_names) == 20
    names = [
        str(p.relative_to(ROOT))
        for pattern in ["lean/**/*.lean", "data/research/*.json", "web/*"]
        for p in ROOT.glob(pattern)
        if ".lake" not in p.parts and p.is_file()
    ]
    names += [
        "scripts/research.py",
        "scripts/reference_research.py",
        "scripts/build_research_examples.py",
        "scripts/verify_research.py",
        "scripts/serve_ui.py",
        "scripts/verify_ui.py",
        "tests/test_research.py",
        "scripts/explore_reconstructions.py",
        "scripts/reference_rules.py",
        "scripts/reference_reconstruction.py",
        "scripts/verify_m5.py",
        "scripts/run_reconstruction.py",
        "data/pie/lexical-input.json",
        "data/pie/latin-control-input.json",
        "data/pie/diagnostic-input.json",
        "data/kuki-chin/lexical-input.json",
        "data/kuki-chin/diagnostic-input.json",
        "data/kuki-chin/joint-analysis-input.json",
        "lean/lakefile.toml",
        "lean/lean-toolchain",
        "docs/14-research-workbench.md",
        ".github/workflows/exploration.yml",
    ]
    return dict(
        schema_version="1.0.0",
        passed=True,
        checks=dict(
            exhaustive_matrices=matrices,
            matrix_outputs_sha256=digest(matrix_digests),
            chronology_permutations=count,
            chronology_sizes=list(range(7)),
            integration_executions=len(executions),
            incomplete_conflict_search=digest(partial),
            invalid_requests=rejected,
            lean_python_exact_agreement=True,
        ),
        executions=executions,
        theorems=theorem_names,
        input_hashes={
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in sorted(set(names))
        },
        limitations=[
            "Finite declared models only; source labels and transcriptions require linguistic assessment.",
            "Search, parsing, UI and their connection to the mathematical definitions are additionally tested infrastructure, not end-to-end verified software.",
            "Discriminating pair counts are not probabilities. Morphology and tone examples do not constitute a complete PIE or PST grammar.",
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--binary-dir", type=Path, default=BIN)
    args = parser.parse_args()
    result = encoded(verify(args.binary_dir))
    path = ROOT / "reports/research-workbench.json"
    if args.check:
        assert path.read_bytes() == result, "Stale research verification report"
    else:
        path.write_bytes(result)
    print(
        "Research verification passed: 256 matrices, 874 permutations, 20 integration runs and 23 rejected inputs."
    )


if __name__ == "__main__":
    main()
