"""Verify M3 proofs, every fixture/site report, and finite reference comparisons.

Run after building Lean and emitting Audit.lean. --check-report validates saved
evidence, fixture freshness and source hashes; it never substitutes for Lean.
"""
import argparse
from copy import deepcopy
import hashlib
import itertools
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from build_m3_fixtures import ROOT, DEST, generate, seg, GAP, MISSING, UNKNOWN, BOUNDARY
import reference_correspondence as reference

REPORT = ROOT / "reports/correspondence-sites.json"
CRITERIA = {"M3-alignment", "M3-patterns", "M3-sites", "M3-optimality"}


def generated_check():
    files = generate()
    assert {DEST / p for p in files} == set(DEST.rglob("*.json")), "Missing or unexpected M3 fixtures"
    for path, content in files.items():
        assert (DEST / path).read_bytes() == content, "Stale M3 fixture: " + path


def input_hashes():
    paths = [ROOT / p for p in [
        "lean/CorrespondenceCheck.lean", "lean/Historical.lean", "lean/Comparative.lean", "lean/Audit.lean",
        "lean/lakefile.toml", "lean/lean-toolchain", "lean/lake-manifest.json", ".github/workflows/ci.yml",
        "scripts/build_m3_fixtures.py", "scripts/reference_correspondence.py", "scripts/verify_m3.py",
        "scripts/check_proofs.py", "tests/test_m3_contracts.py", "docs/alignment-correspondence-semantics.md",
        "docs/09-m3-delivery.md", "data/correspondence/README.md"]]
    paths += list((ROOT / "lean/Historical").glob("*.lean"))
    paths += list((ROOT / "lean/Comparative").glob("*.lean"))
    paths += list(DEST.rglob("*.json"))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}


def invoke(binary, args, expected=(0,), cwd=ROOT):
    r = subprocess.run([str(binary), *args], cwd=cwd, capture_output=True, text=True, timeout=120)
    assert r.returncode in expected, (args, r.returncode, r.stderr, r.stdout[:1000])
    return json.loads(r.stdout)


def evaluate_request(binary, mode, value):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "request.json"
        path.write_text(json.dumps(value, ensure_ascii=False))
        return invoke(binary, [mode, str(path)])


def strict_json(content):
    def object_pairs(pairs):
        obj = {}
        for k, v in pairs:
            if k in obj:
                raise ValueError("duplicate key")
            obj[k] = v
        return obj

    value = json.loads(content.decode("utf-8"), object_pairs_hook=object_pairs)
    # The common interchange profile excludes UTF-16 surrogate escapes even
    # when another JSON parser would combine a well-formed pair.
    if re.search(rb'(?<!\\)(?:\\\\)*\\u[dD][89a-fA-F][0-9a-fA-F]{2}', content):
        raise ValueError("surrogate escape")
    return value


def canonical_site(s):
    s = deepcopy(s)
    s["conflicting_with"].sort()
    for count in s["support"]:
        count["evidence_units"].sort()
    return s


def assess_sites(fixtures):
    sites = []; scoped = set()
    for f in fixtures:
        if not f["counts_toward_site_suite"]:
            continue
        for s in f["result"]["sites"]:
            key = (f["fixture"], s["site_id"])
            assert key not in scoped, "Repeated site identity cannot raise the count"
            scoped.add(key); sites.append(s)
            assert s["assignment_count"] == 1 and len(s["assigned_groups"]) == 1, "Baseline sites need explicit group assignments"
            assert s["support"] and all(c["claimed"] == c["computed"] > 0 for c in s["support"])
            assert isinstance(s["pairwise_compatible"], bool) and isinstance(s["site_accepted"], bool)
    counts = dict(site_count=len(sites), incomplete_site_count=sum(s["incomplete"] for s in sites),
                  conflicting_site_count=sum(bool(s["conflicting_with"]) for s in sites),
                  accepted_site_count=sum(s["site_accepted"] for s in sites),
                  rejected_site_count=sum(not s["site_accepted"] for s in sites))
    assert counts["site_count"] >= 100 and counts["incomplete_site_count"] >= 20 and counts["conflicting_site_count"] >= 10, counts
    return counts


def verify_suite(suite):
    manifest = json.loads((DEST / "manifest.json").read_text())
    assert suite["passed"] and len(suite["results"]) == len(manifest["fixtures"])
    accepted = rejected = checked_rows = reference_cases = 0
    fixtures = suite["results"]
    assert len({f["fixture"] for f in fixtures}) == len(fixtures)
    for expected, f in zip(manifest["fixtures"], fixtures):
        assert f["fixture"] == expected["path"]
        for k in ["kind", "category", "counts_toward_site_suite"]:
            assert f[k] == expected[k]
        assert f["expected_accept"] == expected["accept"] and f["expected_error"] == expected["code"]
        result = f["result"]
        assert f["passed"] and result["accepted"] == expected["accept"], f["fixture"]
        if expected["code"]:
            assert expected["code"] in {i["code"] for i in result["issues"]}, f["fixture"]
        else:
            assert result["issues"] == [], f["fixture"]
        accepted += result["accepted"]; rejected += not result["accepted"]
        try:
            data = strict_json((DEST / f["fixture"]).read_bytes())
        except (UnicodeDecodeError, ValueError):
            assert not result["accepted"] and not expected["counts_toward_site_suite"]
            continue
        shape = reference.data_shape if f["kind"] == "alignment" else reference.dossier_shape
        if not shape(data):
            assert not result["accepted"] and not expected["counts_toward_site_suite"]
            continue
        reference_cases += 1
        alignment_data = data if f["kind"] == "alignment" else data["alignment_data"]
        if f["kind"] == "alignment":
            assert reference.data_valid(data) == result["accepted"]
        else:
            calculated = reference.evaluate(data)
            assert calculated["accepted"] == result["accepted"], f["fixture"]
            assert calculated["alignment_accepted"] == result["alignment_accepted"], f["fixture"]
            assert [canonical_site(s) for s in calculated["sites"]] == [canonical_site(s) for s in result["sites"]], f["fixture"]
            assert result["claim"] == data["claim"] and result["minimum_cover_verified"] is False
            if expected["counts_toward_site_suite"]:
                assert reference.data_valid(alignment_data) and reference.registry(data)[1], "Invalid inputs cannot pad the site floor"
        assert len(result["alignments"]) == len(alignment_data["alignments"])
        for a, checked in zip(alignment_data["alignments"], result["alignments"]):
            assert checked["alignment_id"] == a["id"] and checked["accepted"] == reference.alignment_valid(a)
            assert len(checked["rows"]) == len(a["rows"])
            for source, row in zip(a["rows"], checked["rows"]):
                assert row["doculect_id"] == source["doculect_id"] and row["original"] == source["original"]
                assert row["recovered"] == reference.recover(source["aligned"])
                assert row["preserved"] == (row["recovered"] == row["original"])
                if checked["accepted"]:
                    assert row["preserved"] and ((row["original"] is None) == (source["aligned"] is None))
                    checked_rows += 1
    assert accepted == suite["valid_fixtures"] and rejected == suite["rejected_fixtures"]
    assert accepted + rejected == suite["matched_expectations"]
    counts = assess_sites(fixtures)
    for k in ["site_count", "incomplete_site_count", "conflicting_site_count"]:
        assert suite[k] == counts[k]
    return counts | dict(valid_fixtures=accepted, rejected_fixtures=rejected,
                         typed_reference_fixtures=reference_cases, accepted_alignment_rows_checked=checked_rows)


def matrix_check(binary):
    alphabet = [seg("p"), seg("t"), GAP, MISSING, UNKNOWN, BOUNDARY]
    columns = [list(xs) for n in range(4) for xs in itertools.product(alphabet, repeat=n)]
    result = evaluate_request(binary, "--matrix", dict(columns=columns))
    assert result["scope"] == "typed-core-evaluation" and len(result["rows"]) == len(columns)
    for i, x in enumerate(columns):
        assert len(result["rows"][i]) == len(columns)
        for j, y in enumerate(columns):
            actual = result["rows"][i][j]
            assert actual == reference.compare(x, y), (x, y, actual)
            assert actual == result["rows"][j][i], "Pair compatibility and witnesses must be symmetric"
    return dict(alphabet=alphabet, max_column_length=3, columns=len(columns), comparisons=len(columns) ** 2,
                all_passed=True, symmetry_checked=True, includes_unequal_lengths=True)


def partition_check(binary):
    p, t, k = seg("p"), seg("t"), seg("k")
    contexts = [
        ("nontransitive", [[p, t], [p, MISSING], [p, k]], ["a", "b", "c"]),
        ("complete", [[p, t], [p, t], [p, t]], ["a", "b", "c"]),
        ("repeated-unit", [[p, t], [p, t], [p, t]], ["a", "a", "b"]),
        ("disjoint", [[p, MISSING], [MISSING, t], [MISSING, MISSING]], ["a", "b", "c"]),
        ("gap-observation", [[p, GAP], [p, t], [p, MISSING]], ["a", "b", "c"]),
        ("unknown", [[p, UNKNOWN], [p, t], [UNKNOWN, UNKNOWN]], ["a", "b", "c"]),
        ("boundary-only", [[BOUNDARY], [BOUNDARY], [BOUNDARY]], ["a", "b", "c"]),
        ("unequal-axes", [[p], [p, t], [p, MISSING]], ["a", "b", "c"]),
    ]
    subsets = [list(xs) for n in range(1, 4) for xs in itertools.combinations(range(3), n)]
    checks = []
    for name, columns, units in contexts:
        sites = [dict(id=f"s{i}", evidence_unit=units[i], cells=columns[i]) for i in range(3)]
        proposals = []
        for n in range(4):
            for blocks in itertools.product(subsets, repeat=n):
                groups = [dict(id=f"g{i}", members=[f"s{j}" for j in block], claimed_support=0) for i, block in enumerate(blocks)]
                for g in groups:
                    g["claimed_support"] = len(reference.support(sites, g))
                proposals.append(groups)
                if groups:
                    corrupted = deepcopy(groups); corrupted[0]["claimed_support"] += 1
                    proposals.append(corrupted)
        result = evaluate_request(binary, "--partitions", dict(sites=sites, proposals=proposals))
        assert result["scope"] == "typed-core-evaluation"
        assert result["results"] == [reference.partition_valid(sites, g) for g in proposals], name
        checks.append(dict(context=name, proposals=len(proposals), accepted=sum(result["results"]), all_passed=True))
    return dict(contexts=checks, comparisons=sum(c["proposals"] for c in checks), all_passed=True,
                scope="All ordered lists of zero to three nonempty subsets of three sites, plus incorrect-support variants; testing only, no optimality claim")


def cli_check(binary):
    base = json.loads((DEST / "sites/shared-12.json").read_text())
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "reordered.json"; saved = Path(temp) / "report.json"
        path.write_text(json.dumps(base, ensure_ascii=True, sort_keys=True))
        result = invoke(binary, ["--file", str(path), "--report", str(saved)])
        assert result["accepted"] and json.loads(saved.read_text()) == result
        # Avoid embedding machine-dependent temporary file paths in the report.
        for args in [[], ["--file", str(Path(temp) / "absent.json")], ["--suite", "unknown"]]:
            r = subprocess.run([str(binary), *args], cwd=ROOT, capture_output=True, text=True, timeout=30)
            assert r.returncode == 2 and "IO_OR_INPUT_ERROR" in r.stderr
    result = invoke(binary, ["--file", "data/correspondence/invalid/nontransitive-merge.json"], expected=(1,))
    assert not result["accepted"] and "PAIR_CONFLICT" in {i["code"] for i in result["issues"]}
    standalone = invoke(binary, ["--alignment", "data/correspondence/valid/standalone-boundaries.json"], cwd=ROOT / "lean")
    assert standalone["accepted"]
    return dict(accept_exit=0, reject_exit=1, invocation_and_io_exit=2, saved_report_equals_stdout=True,
                reordered_keys_and_bmp_escapes=True, root_and_lean_directory_paths=True, standalone_alignment=True)


def verify(binary, audit):
    generated_check()
    r = subprocess.run([sys.executable, str(ROOT / "scripts/check_proofs.py"), str(audit)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    print(r.stdout.strip())
    declarations = re.findall(r"^#print axioms\s+(\S+)", (ROOT / "lean/Audit.lean").read_text(), re.M)
    m3 = [s for s in declarations if s.startswith(("Historical.Alignment.", "Historical.Correspondence.", "Historical.CorrespondenceInput."))]
    assert len(m3) >= 35
    suite = invoke(binary, ["--suite", "correspondence-sites"])
    counts = verify_suite(suite)
    # Standard-library parser wording can change between supported Lean
    # versions. Save stable error codes/paths; the CLI retains full messages.
    for f in suite["results"]:
        f["result"]["issues"] = [{k: issue[k] for k in ["code", "path"]} for issue in f["result"]["issues"]]
        if "sites" in f["result"]:
            f["result"]["sites"] = [canonical_site(s) for s in f["result"]["sites"]]
    matrix = matrix_check(binary); partitions = partition_check(binary); cli = cli_check(binary)
    return dict(milestone="M3", status="delivered", all_deliverables_accepted=True,
                criteria=[
                    dict(id="M3-alignment", status="passed", result="Gap-insertion equivalence, row recovery, preserved absence, width/material/boundary validation and strict input bridge", evidence=["lean/Historical/Alignment.lean", "lean/Historical/CorrespondenceInput.lean"]),
                    dict(id="M3-patterns", status="passed", result="Pairwise positive observed support; non-transitivity counterexample; distinct-unit counts; exact partition coverage", evidence=["lean/Historical/Correspondence.lean", "docs/alignment-correspondence-semantics.md"]),
                    dict(id="M3-sites", status="passed", result=f"{counts['site_count']} counted sites, {counts['incomplete_site_count']} incomplete, {counts['conflicting_site_count']} conflicting; every fixture and site diagnostic cross-checked", evidence="data/correspondence/manifest.json"),
                    dict(id="M3-optimality", status="passed", result="Feasibility-only; all minimum/optimal/maximal/score-based claims rejected; distinct feasible partitions explicitly accepted", evidence=["docs/09-m3-delivery.md", "data/correspondence/invalid/claim-minimum.json"])
                ],
                source_kind="synthetic", claim="feasibility-only", minimum_cover_verified=False,
                counts=counts, fixtures=suite["results"], compatibility_cross_check=matrix,
                partition_cross_check=partitions, cli_contracts=cli,
                proof_audit=dict(total_declarations=len(declarations), m3_declarations=m3,
                                 all_declarations_audited=True, project_axioms=False, proof_placeholders=False),
                limitations=["All M3 fixtures are constructed examples, not empirical PIE or Sino-Tibetan evidence.",
                             "Support counts verify distinct declared unit labels, not their historical independence or cognacy.",
                             "The checker certifies the supplied alignments and feasible partition; it does not infer an alignment, optimize a cover or prove a unique reconstruction.",
                             "Unknown readings are unavailable for conflict/support; this explicit profile choice is not an imputation of their sounds.",
                             "Byte parsing, source references, metadata and the transcription into this profile remain executable or empirical trust boundaries.",
                             "The second Python implementation and finite comparisons are test infrastructure, not formal proofs or an independent human/agent review."],
                input_hashes=input_hashes())


def check_saved_report(report):
    generated_check()
    assert report["input_hashes"] == input_hashes(), "Stale M3 report: rebuild, audit and rerun full verification"
    assert report["milestone"] == "M3" and report["status"] == "delivered" and report["all_deliverables_accepted"]
    assert {c["id"] for c in report["criteria"]} == CRITERIA and all(c["status"] == "passed" for c in report["criteria"])
    suite = dict(passed=True, results=report["fixtures"], matched_expectations=len(report["fixtures"]), **report["counts"])
    assert verify_suite(suite) == report["counts"]
    assert report["claim"] == "feasibility-only" and report["minimum_cover_verified"] is False
    assert report["compatibility_cross_check"]["comparisons"] == 67081 and report["compatibility_cross_check"]["all_passed"]
    assert report["partition_cross_check"]["comparisons"] == 6392 and report["partition_cross_check"]["all_passed"]
    milestone = next(m for m in json.loads((ROOT / "data/milestones.json").read_text()) if m["id"] == "M3")
    assert milestone["status"] == "delivered" and {c["id"] for c in milestone["acceptance"]} == CRITERIA
    for path in milestone["artifacts"]:
        assert (ROOT / path).exists(), "Missing M3 artifact: " + path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "lean/.lake/build/bin/correspondence_check")
    parser.add_argument("--audit", type=Path, default=ROOT / "reports/lean-axioms-local.txt")
    parser.add_argument("--check-report", action="store_true")
    args = parser.parse_args()
    if args.check_report:
        check_saved_report(json.loads(REPORT.read_text()))
        print("M3: all four criteria accepted; every saved site, source hash and delivered path verified")
    else:
        report = verify(args.binary.resolve(), args.audit.resolve())
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        print("M3:", json.dumps(report["counts"], sort_keys=True))
        print(f"M3: {report['compatibility_cross_check']['comparisons']} pair comparisons and {report['partition_cross_check']['comparisons']} partition comparisons; all passed")


if __name__ == "__main__":
    main()
