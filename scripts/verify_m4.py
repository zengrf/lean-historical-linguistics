"""M4 delivery checks: exhaustive inverse sets, certificates, ambiguity and limits.

--check-report validates generated inputs, recorded results and source hashes.
Only the full command executes Lean and checks a freshly emitted theorem audit.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from build_m4_fixtures import ROOT, DEST, generate, spec, analysis, rule, form
import reference_reconstruction as reference
from reference_rules import run as forward_run
from run_reconstruction import run_command

REPORT = ROOT / "reports/exhaustive-small-domain.json"
CRITERIA = {"M4-enumeration", "M4-correctness", "M4-ambiguity", "M4-reference"}


def generated_check():
    files = generate()
    assert {DEST / p for p in files} == set(DEST.rglob("*.json")), "Missing or unexpected M4 fixture"
    for p, content in files.items():
        assert (DEST / p).read_bytes() == content, "Stale M4 fixture: " + p


def input_hashes():
    paths = [ROOT / p for p in [
        "lean/Reconstruct.lean", "lean/Historical.lean", "lean/Comparative.lean", "lean/Audit.lean",
        "lean/lakefile.toml", "lean/lean-toolchain", "lean/lake-manifest.json", ".github/workflows/ci.yml",
        "scripts/build_m4_fixtures.py", "scripts/reference_reconstruction.py", "scripts/verify_m4.py",
        "scripts/run_reconstruction.py", "scripts/build_m2_fixtures.py", "scripts/reference_rules.py", "scripts/check_proofs.py",
        "tests/test_m4_contracts.py", "docs/bounded-reconstruction-semantics.md", "docs/10-m4-delivery.md",
        "data/reconstruction/README.md", "data/correspondence/sites/shared-01.json"]]
    paths += list((ROOT / "lean/Historical").glob("*.lean"))
    paths += list((ROOT / "lean/Comparative").glob("*.lean"))
    paths += list(DEST.rglob("*.json"))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}


def invoke(binary, args, expected=(0,), cwd=ROOT):
    p = subprocess.run([str(binary), *args], cwd=cwd, capture_output=True, text=True, timeout=120)
    assert p.returncode in expected, (args, p.returncode, p.stderr, p.stdout[:1000])
    return json.loads(p.stdout)


def batch(binary, queries):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "batch.json"
        path.write_text(json.dumps(dict(queries=queries), ensure_ascii=False))
        results = invoke(binary, ["--batch", str(path)])
    assert len(results["results"]) == len(queries)
    return results["results"]


def candidate_keys(result):
    return [(c["analysis_id"], tuple(c["protoform"])) for c in result.get("candidates", [])]


def assert_complete_result(d, result, expected_candidates):
    assert result["input_valid"] and result["status"] == "complete" and result["complete"]
    assert result["reason"] == "exhausted" and result["examined"] == result["scope_size"]
    assert result["no_candidate_in_scope"] == (len(expected_candidates) == 0)
    assert result["candidates"] == expected_candidates, d["id"]
    assert result["history_count"] == len(expected_candidates)
    assert len(set(candidate_keys(result))) == len(expected_candidates), "Duplicate histories cannot replace alternatives"
    assert result["distinct_protoform_count"] == len({tuple(c["protoform"]) for c in expected_candidates})
    assert result["issues"] == [] and result["claim"] == d["claim"]


def verify_suite(suite):
    manifest = json.loads((DEST / "manifest.json").read_text())
    assert suite["passed"] and len(suite["results"]) == len(manifest["fixtures"])
    assert len({f["fixture"] for f in suite["results"]}) == len(suite["results"])
    counts = dict(complete_fixtures=0, incomplete_fixtures=0, invalid_fixtures=0, candidate_certificates_checked=0)
    for expected, f in zip(manifest["fixtures"], suite["results"]):
        assert f["fixture"] == expected["path"] and f["category"] == expected["category"]
        assert f["expected_status"] == expected["status"] and f["expected_error"] == expected["code"]
        assert f["expected_reason"] == expected["reason"] and f["passed"]
        result = f["result"]
        assert result["status"] == expected["status"] and result["reason"] == expected["reason"]
        assert candidate_keys(result) == [(c["analysis_id"], tuple(c["protoform"])) for c in expected["candidates"]]
        counts[result["status"] + "_fixtures"] += 1
        assert result["complete"] == (result["status"] == "complete")
        if result["status"] != "complete":
            assert result["no_candidate_in_scope"] is False, "An invalid or interrupted search is not an empty completed inverse set"
        if expected["code"]:
            assert expected["code"] in {i["code"] for i in result["issues"]}
            assert result["input_valid"] is False
        else:
            d = json.loads((DEST / f["fixture"]).read_text())
            assert result == reference.evaluate(d), f["fixture"]
            counts["candidate_certificates_checked"] += sum(len(c["branches"]) for c in result["candidates"])
    for k in ["complete_fixtures", "incomplete_fixtures", "invalid_fixtures"]:
        assert counts[k] == suite[k]
    assert counts["complete_fixtures"] >= 15 and counts["incomplete_fixtures"] >= 3 and counts["invalid_fixtures"] >= 25
    assert suite["matched_expectations"] == len(suite["results"])
    return counts


def cascades():
    result = [
        ("identity", []), ("merger", [rule(["c"], "b")]),
        ("delete-a", [rule(["a"], None)]), ("delete-all", [rule(["a", "b", "c"], None)]),
    ]
    for direction in ["left-to-right", "right-to-left"]:
        for mode in ["simultaneous", "feeding"]:
            side = dict(left=[["b"]]) if direction == "left-to-right" else dict(right=[["b"]])
            result.append((f"replace-{direction}-{mode}", [rule(["a"], "b", direction=direction, mode=mode, **side)]))
            result.append((f"delete-{direction}-{mode}", [rule(["a"], None, direction=direction, mode=mode, **side)]))
    result += [
        ("ordered", [rule(["a"], "b"), rule(["b"], "c")]),
        ("reverse-order", [rule(["b"], "c"), rule(["a"], "b")]),
        ("initial-deletion", [rule(["a"], None, left_edge=True, mode="feeding")]),
        ("final-deletion", [rule(["a"], None, right_edge=True, direction="right-to-left", mode="feeding")]),
    ]
    return result


def exhaustive(binary):
    words = reference.word_space(["a", "b", "c"], 4)
    assert len(words) == 121
    reports = []
    for name, laws in cascades():
        # Independent inverse index: execute each protoform once in Python,
        # then bucket by output. Lean separately filters its proved enumeration.
        inverse = {tuple(w): [] for w in words}
        for w in words:
            _, out = forward_run(laws, w)
            assert tuple(out) in inverse
            inverse[tuple(out)].append(w)
        queries = [spec(f"exhaustive-{name}-{i}", [analysis(name, [observed, None], [laws, []], inventory=["a", "b", "c"])],
                        inventory=["a", "b", "c"], bound=4) for i, observed in enumerate(words)]
        results = batch(binary, queries); rows = []
        for d, observed, r in zip(queries, words, results):
            expected = [reference.candidate(d["analyses"][0], w) for w in inverse[tuple(observed)]]
            assert_complete_result(d, r, expected)
            assert r["scope_size"] == 121 and r["raw_hypothesis_upper_bound"] == 121
            rows.append(dict(observed=observed, candidates=[c["protoform"] for c in r["candidates"]],
                             matched=True, branch_certificates_checked=sum(len(c["branches"]) for c in r["candidates"])))
        reports.append(dict(id=name, package=queries[0]["analyses"][0]["branches"][0]["package"],
                            protoforms=121, observation_queries=121, membership_decisions=121 ** 2,
                            all_passed=True, queries=rows))
        print(f"M4 inverse reference: {name}: 121 exact candidate sets matched", flush=True)
    assert len(reports) >= 10
    return dict(alphabet=["a", "b", "c"], max_word_length=4, words=121, cascades=len(reports),
                inverse_queries=121 * len(reports), membership_decisions=121 ** 2 * len(reports),
                all_passed=True, results=reports)


def monotonicity(binary):
    words = reference.word_space(["a", "b", "c"], 4)
    laws = [rule(["c"], "b")]
    queries = []
    for i, w in enumerate(words):
        _, observed = forward_run(laws, w)
        a = analysis("fixed-model", [observed, None], [laws, []], inventory=["a", "b", "c"])
        weak = spec(f"weak-{i}", [a], inventory=["a", "b", "c"], bound=4)
        strong = deepcopy(weak); strong["id"] = f"strong-{i}"; strong["analyses"][0]["observations"][1]["form"] = form(w)
        queries.extend([weak, strong])
    results = batch(binary, queries); rows = []
    for i, w in enumerate(words):
        weak, strong = results[2 * i:2 * i + 2]
        for d, r in zip(queries[2 * i:2 * i + 2], [weak, strong]):
            assert r == reference.evaluate(d)
        assert candidate_keys(strong) == [("fixed-model", tuple(w))]
        assert set(candidate_keys(strong)) <= set(candidate_keys(weak))
        rows.append(dict(added_observation=w, weak_candidates=len(weak["candidates"]), strong_candidates=1, passed=True))
    return dict(fixed_alphabet=True, fixed_length_bound=True, fixed_model=True,
                missing_replaced_by_known=True, comparisons=len(words), all_passed=True, cases=rows)


def cli_checks(binary):
    with tempfile.TemporaryDirectory() as temp:
        base = json.loads((DEST / "complete/unicode-atoms.json").read_text())
        path = Path(temp) / "reordered.json"; saved = Path(temp) / "result.json"
        path.write_text(json.dumps(base, ensure_ascii=True, sort_keys=True))
        result = invoke(binary, ["--file", str(path), "--report", str(saved)])
        assert result == reference.evaluate(base) and json.loads(saved.read_text()) == result
        for args in [[], ["--file", str(Path(temp) / "absent.json")], ["--suite", "absent"]]:
            p = subprocess.run([str(binary), *args], cwd=ROOT, capture_output=True, text=True, timeout=30)
            assert p.returncode == 2 and "IO_OR_INPUT_ERROR" in p.stderr
    invalid = invoke(binary, ["--file", "data/reconstruction/invalid/duplicate-inventory.json"], expected=(1,))
    incomplete = invoke(binary, ["--file", "data/reconstruction/incomplete/empty-prefix.json"], expected=(3,), cwd=ROOT / "lean")
    assert not invalid["no_candidate_in_scope"] and not incomplete["no_candidate_in_scope"]
    timed, code = run_command([sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.05)
    assert code == 3 and timed["reason"] == "process-timeout" and timed["no_candidate_in_scope"] is False and timed["input_valid"] is None
    wrapped, code = run_command([str(binary), "--file", str(DEST / "complete/conflicting-observations.json")], timeout=30)
    assert code == 0 and wrapped["complete"] and wrapped["no_candidate_in_scope"]
    failed, code = run_command([sys.executable, "-c", "raise SystemExit(7)"])
    assert code == 2 and failed["no_candidate_in_scope"] is False
    return dict(complete_exit=0, invalid_exit=1, invocation_io_exit=2, incomplete_exit=3,
                report_equals_stdout=True, json_key_order_and_bmp_escapes=True, root_and_lean_paths=True,
                external_timeout_checked=True, process_failure_not_empty=True, empty_prefix_not_empty_search=True)


def verify(binary, audit):
    generated_check()
    p = subprocess.run([sys.executable, str(ROOT / "scripts/check_proofs.py"), str(audit)], cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    print(p.stdout.strip(), flush=True)
    all_theorems = re.findall(r"^#print axioms\s+(\S+)", (ROOT / "lean/Audit.lean").read_text(), re.M)
    m4 = [n for n in all_theorems if n.startswith(("Historical.Reconstruction.", "Historical.Identifiability.", "Historical.ReconstructionInput."))]
    suite = invoke(binary, ["--suite", "bounded-reconstruction"]); counts = verify_suite(suite)
    for f in suite["results"]:
        f["result"]["issues"] = [{k: i[k] for k in ["code", "path"]} for i in f["result"]["issues"]]
    inverse = exhaustive(binary); mono = monotonicity(binary); cli = cli_checks(binary)
    return dict(milestone="M4", status="delivered", all_deliverables_accepted=True,
                criteria=[
                    dict(id="M4-enumeration", status="passed", result="Exact finite sequence enumeration, length counts, explicit proto shape and named joint-analysis bounds", evidence=["lean/Historical/Reconstruction.lean", "docs/bounded-reconstruction-semantics.md"]),
                    dict(id="M4-correctness", status="passed", result="Candidate soundness and relative completeness via M2 inductive derivations; sound prefixes and complete-result equivalence", evidence=["lean/Historical/Reconstruction.lean", "lean/Historical/ReconstructionInput.lean"]),
                    dict(id="M4-ambiguity", status="passed", result="Observational-equivalence theorem across histories; fixed-model monotonicity and observation refinement; joint alternatives serialized without recombination", evidence=["lean/Historical/Identifiability.lean", "data/reconstruction/complete/joint-model-alternatives.json"]),
                    dict(id="M4-reference", status="passed", result=f"{inverse['inverse_queries']} exact inverse sets over 121 words and {inverse['cascades']} cascades; cooperative/process timeouts distinct from complete empty searches", evidence=["scripts/reference_reconstruction.py", "scripts/run_reconstruction.py"])
                ],
                source_kind="synthetic", claim="bounded-relative-completeness", counts=counts,
                fixtures=suite["results"], exhaustive_inverse=inverse, observation_refinement=mono, cli_contracts=cli,
                proof_audit=dict(total_declarations=len(all_theorems), m4_declarations=m4, all_declarations_audited=True,
                                 project_axioms=False, proof_placeholders=False),
                limitations=["Complete means complete within the declared finite space and supplied M2 models, not historical truth or global coverage.",
                             "The suite is synthetic; empirical PIE and Sino-Tibetan reconstruction and specialist review remain M5/M6 work.",
                             "Unknown cells mask exactly one segment; uncertainty in length or correlated readings needs explicit joint analyses.",
                             "M3 bridges certify preservation and grouping feasibility, not cognacy or the linguistic interpretation of sound correspondences.",
                             "Resource control, JSON parsing, metadata and serialization are executable trust boundaries; cooperative deadlines are not hard interruption guarantees.",
                             "The Python oracle is a separately implemented finite test, not a formal proof or an independent human/agent review."],
                input_hashes=input_hashes())


def check_saved_report(report):
    generated_check()
    assert report["input_hashes"] == input_hashes(), "Stale M4 report: rebuild, audit and rerun verification"
    assert report["milestone"] == "M4" and report["status"] == "delivered" and report["all_deliverables_accepted"]
    assert {c["id"] for c in report["criteria"]} == CRITERIA and all(c["status"] == "passed" for c in report["criteria"])
    suite = dict(passed=True, results=report["fixtures"], matched_expectations=len(report["fixtures"]), **report["counts"])
    assert verify_suite(suite) == report["counts"]
    inverse = report["exhaustive_inverse"]
    assert inverse["all_passed"] and inverse["alphabet"] == ["a", "b", "c"] and inverse["max_word_length"] == 4
    assert inverse["cascades"] == len(cascades()) >= 10 and inverse["words"] == 121
    assert inverse["inverse_queries"] == 121 * len(cascades()) and inverse["membership_decisions"] == 121 ** 2 * len(cascades())
    words = reference.word_space(["a", "b", "c"], 4)
    assert len(inverse["results"]) == len(cascades())
    for (name, laws), result in zip(cascades(), inverse["results"]):
        assert result["id"] == name and result["all_passed"] and len(result["queries"]) == 121
        buckets = {tuple(w): [] for w in words}
        for w in words:
            buckets[tuple(forward_run(laws, w)[1])].append(w)
        for observed, row in zip(words, result["queries"]):
            assert row["observed"] == observed and row["matched"] and row["candidates"] == buckets[tuple(observed)]
    assert report["observation_refinement"]["all_passed"] and report["observation_refinement"]["comparisons"] == 121
    assert report["cli_contracts"]["external_timeout_checked"] and report["cli_contracts"]["empty_prefix_not_empty_search"]
    milestone = next(m for m in json.loads((ROOT / "data/milestones.json").read_text()) if m["id"] == "M4")
    assert milestone["status"] == "delivered" and {c["id"] for c in milestone["acceptance"]} == CRITERIA
    for path in milestone["artifacts"]:
        assert (ROOT / path).exists(), "Missing M4 artifact: " + path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary", type=Path, default=ROOT / "lean/.lake/build/bin/reconstruct")
    p.add_argument("--audit", type=Path, default=ROOT / "reports/lean-axioms-local.txt")
    p.add_argument("--check-report", action="store_true"); args = p.parse_args()
    if args.check_report:
        check_saved_report(json.loads(REPORT.read_text()))
        print("M4: all four criteria accepted; saved inverse sets, hashes and artifact paths verified")
    else:
        report = verify(args.binary.resolve(), args.audit.resolve())
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        print("M4:", json.dumps(report["counts"], sort_keys=True))
        print(f"M4: {report['exhaustive_inverse']['inverse_queries']} exact inverse sets, {report['exhaustive_inverse']['membership_decisions']} membership decisions; all passed")


if __name__ == "__main__":
    main()
