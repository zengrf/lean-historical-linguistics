"""Native comparisons, corrupted graphs, and contextual whole-lexicon scaling."""

import argparse
from copy import deepcopy
import hashlib
from itertools import islice, product
import json
from pathlib import Path
import platform
import random
import resource
import time

from build_pie_corpus import ROOT, encoded
from build_m7_fixtures import contextual, request, model, entry, rule
from lexicon import reconstruct, native, page
from m7_solver import baseline, output, graph_counts, unrank


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "reports/contextual-pruning.json"
    )
    args = parser.parse_args()
    rng = random.Random(74129)
    comparisons = []
    for number in range(24):
        laws = []
        for _ in range(1 + number % 3):
            laws.append(
                rule(
                    rng.choice(["p", "b", "a"]),
                    rng.choice(["p", "b", "a", None]),
                    left=rng.choice([[], [["a"]], [["p", "b"]]]),
                    right=rng.choice([[], [["a"]], [["p", "b"]]]),
                    direction=rng.choice(["left-to-right", "right-to-left"]),
                    mode=rng.choice(["feeding", "simultaneous"]),
                )
            )
        m = model("contextual", ["A"], ["p", "b", "a"], [laws])
        observations = [
            None,
            [],
            [None, "a"],
            output(m["branches"][0], ["a", "p", "a"]),
        ]
        entries = [
            entry(f"row-{i}", ["A"], [obs]) for i, obs in enumerate(observations)
        ]
        spec = request(
            f"context-{number}", ["p", "b", "a"], ["A"], [m], entries, maximum=4
        )
        result = reconstruct(spec)
        expected = baseline(spec, m)
        graph = result["forest"]["models"][0]
        for b in graph["bindings"]:
            nodes = graph["graphs"][b["graph"]]["nodes"]
            counts = graph_counts(nodes)
            got = [
                unrank(nodes, counts, b["root"], i) for i in range(counts[b["root"]])
            ]
            assert sorted(got) == sorted(expected[b["entry_id"]])
        comparisons.append(
            dict(
                case=number,
                request_sha256=hashlib.sha256(encoded(spec)).hexdigest(),
                nodes=result["summary"]["nodes"],
                complete=True,
            )
        )
    small = contextual()
    small["max_length"] = 12
    started = time.perf_counter()
    result = reconstruct(small, time_limit=5)
    small_seconds = time.perf_counter() - started
    assert result["summary"]["lexicon_count"] == "1"
    forged = deepcopy(result["forest"])
    forged["models"][0]["graphs"][0]["nodes"][-1]["edges"].pop()
    assert "error" in native("--check", forged, allow_rejection=True)
    forged = deepcopy(result["forest"])
    forged["models"][0]["graphs"][0]["nodes"][-1]["accepting"] = True
    assert "error" in native("--check", forged, allow_rejection=True)
    large = contextual()
    large["max_length"] = 12
    large["entries"] = []
    for i, word in enumerate(islice(product(["p", "b", "a"], repeat=7), 1000)):
        forms = [output(b, word) for b in large["analyses"][0]["branches"]]
        large["entries"].append(entry(f"row-{i}", ["A", "B"], forms))
    started = time.perf_counter()
    solved = reconstruct(large)
    first = page(solved, "intervocalic", limit=1)
    elapsed = time.perf_counter() - started
    assert solved["summary"]["lexicon_count"] == "1"
    assert len(first["items"][0]["derivations"]) == 1000
    assert all(p["accepted"] for p in first["items"][0]["derivations"])
    peak = sum(
        resource.getrusage(k).ru_maxrss
        for k in [resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN]
    )
    if platform.system() != "Darwin":
        peak *= 1024
    report = dict(
        passed=True,
        comparisons=comparisons,
        exact_inverse_sets=96,
        rejected_corruptions=["omitted possible edge", "false accepting state"],
        formerly_exhausted_case=dict(
            max_length=12,
            search_budget_seconds=5,
            elapsed_seconds=small_seconds,
            nodes=result["summary"]["nodes"],
            complete=True,
        ),
        contextual_benchmark=dict(
            rows=1000,
            reflexes=2000,
            length=7,
            max_length=12,
            graph_nodes=solved["summary"]["nodes"],
            lexicons="1",
            branch_certificates=2000,
            elapsed_seconds=elapsed,
            memory_upper_bound_bytes=peak,
            within_delivery_limits=elapsed < 60 and peak < 2 * 1024**3,
        ),
        scope="Synthetic contextual control with one changing daughter and one conservative daughter. This is not a benchmark of a complete historical grammar. Worst-case search remains bounded and can be incomplete.",
        input_hashes={
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                ROOT / "scripts/verify_pruning.py",
                ROOT / "scripts/m7_solver.py",
                ROOT / "lean/Historical/Pruning.lean",
                ROOT / "lean/Historical/LexiconInput.lean",
            ]
        },
    )
    args.output.write_bytes(encoded(report))
    print(
        f"Pruning: 96 exact inverse sets; 1000 contextual rows, {elapsed:.3f}s, {peak/1024**2:.1f} MiB; {report['contextual_benchmark']['within_delivery_limits']}"
    )
    if not report["contextual_benchmark"]["within_delivery_limits"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
