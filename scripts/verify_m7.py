"""Native completeness, compiler, proposal and trust-boundary checks for M7."""

import argparse
from copy import deepcopy
import hashlib
from itertools import product
import json
from pathlib import Path
import subprocess
import tempfile

from build_pie_corpus import ROOT, encoded
from build_m7_fixtures import build, merger, contextual, request, model, entry, rule
from lexicon import BIN, reconstruct, native, page
from m7_solver import baseline, solve, graph_counts, unrank, IncompleteSearch


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def hashes():
    files = [p for p in (ROOT / "lean").rglob("*.lean") if ".lake" not in p.parts]
    files += list((ROOT / "data/lexicon").glob("*"))
    files += [
        ROOT / n
        for n in [
            "scripts/m7_solver.py",
            "scripts/lexicon.py",
            "scripts/lexicon_api.py",
            "scripts/build_m7_fixtures.py",
            "scripts/verify_m7.py",
            "scripts/benchmark_m7.py",
            "scripts/verify_m7_ui.py",
            "scripts/serve_ui.py",
            "scripts/reference_rules.py",
            "tests/test_m7.py",
            "lean/lakefile.toml",
            "docs/15-m7-delivery.md",
            "data/milestones.json",
            ".github/workflows/exploration.yml",
        ]
    ]
    files += list((ROOT / "web").glob("*.*"))
    return {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(set(files))
        if p.is_file()
    }


def graph_words(m, b):
    ns = m["graphs"][b["graph"]]["nodes"]
    cs = graph_counts(ns)
    return [unrank(ns, cs, b["root"], i) for i in range(cs[b["root"]])]


def exhaustive(binary):
    inv, ds = ["p", "b", "a"], ["A"]
    words = [list(w) for n in range(5) for w in product(inv, repeat=n)]
    cascades = [
        [],
        [rule("b", "p")],
        [rule("a", None)],
        [rule("b", "p"), rule("p", None)],
        [rule("p", "b"), rule("b", "a")],
        [rule("b", "p", mode="feeding")],
        [rule("p", "b", left=[["a"]], right=[["a"]])],
        [rule("p", "b", left=[["b"]], mode="feeding")],
        [rule("p", "b", right=[["b"]], mode="feeding", direction="right-to-left")],
        [rule("p", None, left_edge=True)],
        [rule("a", None, right_edge=True)],
        [rule("p", "b", right=[["p"]], direction="right-to-left")],
    ]
    results, proposals = [], 0
    for i, laws in enumerate(cascades):
        m = model(f"cascade-{i}", ds, inv, [laws])
        es = [entry(f"word-{j}", ds, [w]) for j, w in enumerate(words)]
        es += [
            entry("missing", ds, [None]),
            entry("unknown", ds, [[None, "a"]]),
            entry("boundary", ds, [["+"]]),
        ]
        spec = request(f"exhaustive-{i}", inv, ds, [m], es, maximum=4)
        result = reconstruct(spec, binary=binary)
        oracle = baseline(spec, m)
        found, sample = {}, []
        graph = result["forest"]["models"][0]
        for b in graph["bindings"]:
            ws = graph_words(graph, b)
            assert len(ws) == len({tuple(w) for w in ws}), "Duplicate generated word"
            assert sorted(ws) == sorted(
                oracle[b["entry_id"]]
            ), "Incomplete or unsound inverse language"
            found[b["entry_id"]] = sorted(ws)
            sample.extend(
                dict(analysis_id=m["id"], entry_id=b["entry_id"], word=w) for w in ws
            )
        accepted = native(
            "--derive", dict(request=spec, proposals=sample), binary=binary
        )
        assert all(p["accepted"] for p in accepted["proposals"])
        proposals += len(sample)
        results.append(
            dict(
                cascade=i,
                mode=graph["mode"],
                inverse_sets=len(es),
                complete_sets_sha256=digest(found),
                generated=len(sample),
                accepted=len(sample),
                baseline_exact_agreement=True,
            )
        )
        print(f"M7 cascade {i}: {len(es)} complete inverse sets agree", flush=True)
    return results, proposals


def adversarial(binary):
    original = solve(merger())
    variants = []

    def mutate(name, f):
        value = deepcopy(original)
        f(value)
        variants.append((name, value))

    mutate(
        "omitted-transition",
        lambda f: f["models"][0]["graphs"][0]["nodes"][-1]["edges"].pop(),
    )
    mutate(
        "false-accepting",
        lambda f: f["models"][0]["graphs"][0]["nodes"][-1].update(accepting=True),
    )
    mutate(
        "hidden-accepting",
        lambda f: f["models"][0]["graphs"][0]["nodes"][0].update(accepting=False),
    )
    mutate(
        "duplicate-edge",
        lambda f: f["models"][0]["graphs"][0]["nodes"][-1]["edges"].append(
            deepcopy(f["models"][0]["graphs"][0]["nodes"][-1]["edges"][0])
        ),
    )
    mutate(
        "out-of-range-child",
        lambda f: f["models"][0]["graphs"][0]["nodes"][-1]["edges"][0].__setitem__(
            1, 999999
        ),
    )
    mutate(
        "cycle",
        lambda f: f["models"][0]["graphs"][0]["nodes"][-1]["edges"][0].__setitem__(
            1, len(f["models"][0]["graphs"][0]["nodes"]) - 1
        ),
    )
    mutate(
        "unknown-edge-label",
        lambda f: f["models"][0]["graphs"][0]["nodes"][-1]["edges"].append(["z", 0]),
    )
    mutate("wrong-root", lambda f: f["models"][0]["bindings"][0].update(root=0))
    mutate("missing-model", lambda f: f["models"].pop())
    mutate("missing-row", lambda f: f["models"][0]["bindings"].pop())
    mutate("foreign-model", lambda f: f["models"][0].update(analysis_id="foreign"))
    mutate(
        "foreign-row",
        lambda f: f["models"][0]["bindings"][0].update(entry_id="foreign"),
    )
    mutate("foreign-graph", lambda f: f["models"][0]["bindings"][0].update(graph=9))
    mutate("changed-bound", lambda f: f["request"].update(max_length=3))
    mutate(
        "changed-reflex",
        lambda f: f["request"]["entries"][0]["reflexes"][0].update(form=["b"]),
    )
    mutate(
        "changed-model",
        lambda f: f["request"]["analyses"][0]["branches"][0]["package"]["laws"][0][
            "rule"
        ].update(replacement="a"),
    )
    mutate(
        "undeclared-shape",
        lambda f: f["models"][0]["graphs"][0]["nodes"][-1]["state"].update(shapes=[]),
    )
    mutate(
        "unknown-node-field",
        lambda f: f["models"][0]["graphs"][0]["nodes"][0].update(trusted=True),
    )
    mutate("omitted-null-field", lambda f: f["request"].pop("phonotactics"))
    mutate("unknown-request-field", lambda f: f["request"].update(pool=[["p", "a"]]))
    mutate(
        "unsupported-compilation",
        lambda f: f["request"]["analyses"][0]["branches"][0]["package"]["laws"][0][
            "rule"
        ].update(left=[["a"]]),
    )
    mutate("duplicate-inventory", lambda f: f["request"]["proto_inventory"].append("p"))
    mutate(
        "too-many-rows",
        lambda f: f["request"].update(entries=f["request"]["entries"] * 5001),
    )
    mutate("reordered-languages", lambda f: f["request"]["languages"].reverse())
    mutate(
        "invalid-rule-context",
        lambda f: f["request"]["analyses"][0]["branches"][0]["package"]["laws"][0][
            "rule"
        ].update(left=["*"] * 3),
    )
    rejected = []
    for name, f in variants:
        out = native("--check", f, binary=binary, allow_rejection=True)
        assert not out.get("complete") and not out["input_valid"], name
        rejected.append(name)
    # A reference graph cannot be rebound to a different observation tuple.
    f = solve(contextual())
    f["request"]["entries"][0]["reflexes"][0]["form"] = ["p"]
    assert not native("--check", f, binary=binary, allow_rejection=True)["input_valid"]
    rejected.append("reference-observation-rebinding")
    for label, raw in [
        ("duplicate-json-key", b'{"request":null,"request":null,"models":[]}'),
        ("invalid-utf8", b"\xff"),
        ("trailing-json", encoded(original) + b"{}"),
    ]:
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "bad.json"
            file.write_bytes(raw)
            out = subprocess.run(
                [str(binary), "--check", str(file)], capture_output=True, timeout=60
            )
            assert out.returncode != 0 and not json.loads(out.stdout)["input_valid"]
        rejected.append(label)
    return rejected


def proposal_checks(binary):
    spec = merger()
    jobs = [
        dict(analysis_id="mergers", entry_id="one", word=w)
        for w in [["b", "a"], ["a"], ["z"], ["b", "a", "a"]]
    ]
    generated = native("--derive", dict(request=spec, proposals=jobs), binary=binary)[
        "proposals"
    ]
    assert [p["accepted"] for p in generated] == [True, False, False, False]
    good = {k: generated[0][k] for k in ["proposal", "certificates"]}
    proposals = [deepcopy(good) for _ in range(7)]
    proposals[0]["certificates"][0]["output"] = ["b", "a"]
    proposals[1]["certificates"][0]["steps"][0]["output"] = ["b", "a"]
    proposals[2]["certificates"][0]["package_id"] = "foreign"
    proposals[3]["certificates"][0]["steps"].reverse()
    proposals[4]["certificates"].pop()
    proposals[5]["certificates"][0]["input"] = ["p", "a"]
    proposals[6]["proposal"]["entry_id"] = "two"
    out = native(
        "--check-proposals",
        dict(request=spec, proposals=[good] + proposals),
        binary=binary,
    )
    assert [p["accepted"] for p in out["proposals"]] == [True] + [False] * 7
    return dict(
        external_proposals_generated=4,
        certificates_accepted=1,
        candidates_rejected=3,
        corrupted_certificates_rejected=7,
        historical_reference_agreement="not evaluated; synthetic controls",
    )


def verify(binary):
    examples = {}
    for name, spec in build().items():
        if name == "scaling.json":
            continue
        r = reconstruct(spec, binary=binary)
        summary = {k: v for k, v in r["summary"].items() if not k.endswith("seconds")}
        examples[name] = summary
        if name == "merger.json":
            whole = page(r, "mergers", limit=4, binary=binary)
            assert len(whole["items"]) == 4 and not whole["has_more"]
            assert (
                len(
                    {
                        tuple(tuple(w["word"]) for w in x["words"])
                        for x in whole["items"]
                    }
                )
                == 4
            )
            assert not page(r, "mergers", offset="4", limit=1, binary=binary)["items"]
        if name in {"merger.json", "deletion.json", "kuki.json"}:
            slow = reconstruct(spec, binary=binary, force_reference=True)
            for a, b in zip(r["summary"]["models"], slow["summary"]["models"]):
                assert (
                    a["lexicon_count"] == b["lexicon_count"]
                    and a["entries"] == b["entries"]
                )
    assert examples["pie.json"]["lexicon_count"] == "1"
    assert examples["kuki.json"]["lexicon_count"] == "2"
    assert examples["conflict.json"]["lexicon_count"] == "0"
    ex, accepted = exhaustive(binary)
    rejected = adversarial(binary)
    for options in [dict(node_budget=1), dict(time_limit=0.000000001)]:
        try:
            reconstruct(merger(), binary=binary, **options)
        except IncompleteSearch:
            pass
        else:
            raise AssertionError("Exhausted search incorrectly reported complete")
    return dict(
        milestone="M7",
        engineering_passed=True,
        examples=examples,
        exhaustive=ex,
        inverse_sets=sum(x["inverse_sets"] for x in ex),
        external_generated_and_native_accepted=accepted,
        malformed_graphs_rejected=rejected,
        proposal_interface=proposal_checks(binary),
        budgets_report_incomplete=True,
        input_hashes=hashes(),
        limits=[
            "Completeness is relative to supplied cognacy, finite sound-law models, alphabet, length bounds and templates.",
            "PIE and Kuki-Chin examples have explicit limited model scope; historical correctness is not proved.",
            "Native graph-language equivalence is proved. Parsing, orchestration, counts and pagination are additionally tested infrastructure.",
        ],
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    p.add_argument(
        "--check-report",
        action="store_true",
        help="Check retained evidence hashes without invoking Lean",
    )
    p.add_argument("--binary", type=Path, default=BIN)
    args = p.parse_args()
    if args.check_report:
        report = json.loads((ROOT / "reports/m7-verification.json").read_text())
        assert (
            report["engineering_passed"] and report["input_hashes"] == hashes()
        ), "Stale M7 report"
        benchmark = json.loads((ROOT / "reports/m7-benchmark-local.json").read_text())
        assert benchmark["passed"] and benchmark["branch_certificates"] >= 1000
        assert (
            benchmark["elapsed_seconds"] < 60
            and benchmark["memory_upper_bound_bytes"] < 2 * 1024**3
        )
        browser = json.loads((ROOT / "reports/m7-ui/checks.json").read_text())
        assert browser["passed"] and len(browser["checks"]) >= 19
        for artifact in [benchmark, browser]:
            for name, sha in artifact["input_hashes"].items():
                assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha, (
                    "Stale M7 evidence: " + name
                )
        milestone = next(
            m
            for m in json.loads((ROOT / "data/milestones.json").read_text())
            if m["id"] == "M7"
        )
        assert all((ROOT / n).exists() for n in milestone["artifacts"])
        print(
            "M7 retained verification, benchmark, browser evidence and artifact paths are current."
        )
        return
    raw = encoded(verify(args.binary))
    file = ROOT / "reports/m7-verification.json"
    if args.check:
        assert file.read_bytes() == raw, "Stale M7 verification report"
    else:
        file.write_bytes(raw)
    print("M7 native inverse-language, proposal and corruption checks passed.")


if __name__ == "__main__":
    main()
