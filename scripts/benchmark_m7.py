"""Measure generation, complete-graph checking and 1000 whole-word derivations."""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import resource
import subprocess
import time

from build_pie_corpus import ROOT, encoded
from build_m7_fixtures import scaling, deletion
from lexicon import reconstruct, page
from m7_solver import decimal, baseline, solve, graph_counts, unrank


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--output", type=Path, default=ROOT / "reports/m7-benchmark-local.json"
    )
    p.add_argument("--lean-version", required=True)
    args = p.parse_args()
    small = deletion()
    small["max_length"] = 8
    started = time.perf_counter()
    reference = baseline(small, small["analyses"][0])
    reference_seconds = time.perf_counter() - started
    started = time.perf_counter()
    symbolic = solve(small)
    symbolic_seconds = time.perf_counter() - started
    m = symbolic["models"][0]
    for b in m["bindings"]:
        ns = m["graphs"][b["graph"]]["nodes"]
        cs = graph_counts(ns)
        assert sorted(reference[b["entry_id"]]) == sorted(
            unrank(ns, cs, b["root"], i) for i in range(cs[b["root"]])
        )
    spec = scaling()
    start = time.perf_counter()
    result = reconstruct(spec)
    generation_and_checking = time.perf_counter() - start
    started = time.perf_counter()
    first = page(result, "four-mergers", limit=1)
    derivation_seconds = time.perf_counter() - started
    elapsed = time.perf_counter() - start
    assert result["summary"]["lexicon_count"] == decimal(64**1000)
    assert all(e["count"] == "64" for e in result["summary"]["models"][0]["entries"])
    derived = first["items"][0]["derivations"]
    assert len(derived) == 1000 and all(d["accepted"] for d in derived)
    certificates = sum(len(d["certificates"]) for d in derived)
    assert certificates == 3000
    peaks = [
        resource.getrusage(kind).ru_maxrss
        for kind in [resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN]
    ]
    if platform.system() != "Darwin":
        peaks = [p * 1024 for p in peaks]
    hardware = dict(
        system=platform.system(),
        release=platform.release(),
        machine=platform.machine(),
        python=platform.python_version(),
        lean=args.lean_version,
    )
    if platform.system() == "Darwin":
        info = subprocess.check_output(
            ["sysctl", "-n", "hw.model", "machdep.cpu.brand_string", "hw.memsize"],
            text=True,
        ).splitlines()
        hardware.update(model=info[0], cpu=info[1], ram_bytes=int(info[2]))
    else:
        hardware.update(
            cpu=platform.processor(), runner="ordinary CI runner; see workflow"
        )
    peak = sum(peaks)
    names = [
        "scripts/benchmark_m7.py",
        "scripts/m7_solver.py",
        "scripts/lexicon.py",
        "scripts/build_m7_fixtures.py",
        "scripts/reference_rules.py",
        "data/lexicon/scaling.json",
    ]
    names += [
        str(p.relative_to(ROOT))
        for p in (ROOT / "lean").rglob("*.lean")
        if ".lake" not in p.parts
    ]
    report = dict(
        passed=elapsed < 60 and peak < 2 * 1024**3,
        hardware=hardware,
        generation_comparison=dict(
            baseline_seconds=reference_seconds,
            symbolic_seconds=symbolic_seconds,
            alphabet_size=3,
            max_length=8,
            candidate_words=9841,
            cognate_rows=2,
            exact_inverse_sets_equal=True,
            scope="Generation only, independent Python forward interpreter versus residual graph; measured before the large benchmark.",
        ),
        distinct_cognate_rows=1000,
        daughter_reflexes=3000,
        alphabet_size=8,
        word_length=6,
        models=1,
        rules_per_branch=4,
        inverse_words_per_row=64,
        lexicons_power="64^1000 = 2^6000",
        checked_graph_nodes=result["summary"]["nodes"],
        bounded_reconstructions=1000,
        branch_certificates=certificates,
        certificate_target=1000,
        elapsed_seconds=elapsed,
        generation_and_graph_checking_seconds=generation_and_checking,
        forward_certificate_seconds=derivation_seconds,
        memory_upper_bound_bytes=peak,
        python_peak_bytes=peaks[0],
        largest_child_peak_bytes=peaks[1],
        memory_method="Sum of Python and largest sequential child peaks; conservative upper bound, not simultaneous RSS sampling.",
        seconds_limit=60,
        memory_limit_bytes=2 * 1024**3,
        scope="End-to-end synthetic scaling control: native request validation, external inverse search, native complete-graph check, exact counts, first whole lexicon and all 3000 native branch certificates. No historical accuracy claim.",
        input_hashes={
            n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest()
            for n in sorted(names)
        },
    )
    args.output.write_bytes(encoded(report))
    print(
        f"M7: {certificates} certificates, 1000 distinct rows, {elapsed:.3f}s, memory upper bound {peak/1024**2:.1f} MiB; passed={report['passed']}"
    )
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
