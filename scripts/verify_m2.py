"""Verify M2's executable, independent examples, proof audit and delivery evidence.

Build Lean and emit Audit.lean first. --check-report performs the source-hash,
review-attestation and delivered-artifact checks without running Lean; CI also
runs the complete verifier on both supported toolchains.
"""
import argparse
import hashlib
import itertools
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from build_m2_fixtures import ROOT, package, rule, generate
from reference_rules import run as reference_run


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def assess_review(packet, response, semantics):
    errors = []
    cases = packet.get("cases", [])
    expected = {c["id"]: c for c in cases}
    if len(expected) != len(cases) or len(cases) < 10:
        errors.append("At least ten uniquely identified hand-worked cases are required")
    semantics_hash = hashlib.sha256(semantics).hexdigest()
    if packet.get("semantics_sha256") != semantics_hash:
        errors.append("Review packet is not tied to the current prose semantics")
    reviewed = set()
    if response:
        reviewer = response.get("reviewer_id", "")
        if not reviewer or reviewer.lower() in {"codex", "assistant", "importer", "/root"}:
            errors.append("Actual independent reviewer identity is required")
        if response.get("reviewer_type") not in {"independent_ai_agent", "human"}:
            errors.append("Reviewer type must distinguish AI review from human review")
        if response.get("independent_of_implementation") is not True or not response.get("method"):
            errors.append("Independent method and attestation are required")
        if response.get("packet_sha256") != canonical_hash(packet) or response.get("semantics_sha256") != semantics_hash:
            errors.append("Review response is stale for the packet or prose semantics")
        provenance = response.get("provenance", {})
        if any(provenance.get(key) is not False for key in
               ["implementation_read", "interpreter_executed", "expected_answers_consulted"]):
            errors.append("Independent hand-work must precede implementation or expected-answer consultation")
        if provenance.get("answers_frozen_before_comparison") is not True:
            errors.append("Answers must be finalized before comparison")
        if response.get("specification_ambiguities") != []:
            errors.append("Specification ambiguities must be resolved before acceptance")
        for entry in response.get("entries", []):
            name = entry.get("id")
            if name not in expected or name in reviewed:
                errors.append("Unknown or duplicate hand-worked case: " + str(name)); continue
            reviewed.add(name); case = expected[name]
            steps = entry.get("steps", [])
            if len(steps) != len(case["rules"]):
                errors.append("Every pass, including unchanged stages, must be recorded: " + name)
            words = steps + [entry.get("output")]
            if not all(isinstance(w, list) and all(isinstance(s, str) for s in w) for w in words):
                errors.append("Every recorded word must be an explicit list of atomic strings: " + name)
            if entry.get("output") != (steps[-1] if steps else case["input"]):
                errors.append("Final output must agree with the last hand-worked stage: " + name)
            if not entry.get("reasoning", "").strip():
                errors.append("A hand-worked rationale is required: " + name)
    missing = sorted(set(expected) - reviewed)
    return dict(status="passed" if response and not errors and not missing else "pending",
                minimum_cases=10, packet_cases=len(cases), reviewed_cases=len(reviewed),
                missing_cases=missing, errors=errors,
                reviewer_id=response.get("reviewer_id") if response else None,
                reviewer_type=response.get("reviewer_type") if response else None,
                packet_sha256=canonical_hash(packet), semantics_sha256=semantics_hash,
                response_sha256=canonical_hash(response) if response else None,
                limitation="Identity, independence and hand-work are attestations. Separate AI review is not human or family-specialist sign-off; a shared filesystem boundary is enforced by instruction.")


def current_review():
    packet = json.loads((ROOT / "reviews/m2-packet.json").read_text())
    response = json.loads((ROOT / "reviews/m2-responses.json").read_text())
    review = assess_review(packet, response, (ROOT / "docs/rule-semantics.md").read_bytes())
    assert review["status"] == "passed", review
    return packet, response, review


def generated_check():
    files, packages, _ = generate()
    expected = {ROOT / "data/contextual-rules" / name for name in files}
    assert set((ROOT / "data/contextual-rules").rglob("*.json")) == expected
    for name, content in files.items():
        assert (ROOT / "data/contextual-rules" / name).read_bytes() == content, "Stale fixture: " + name
    assert (ROOT / "data/rule-packages/contextual-examples.json").read_bytes() == packages


def input_hashes():
    paths = [ROOT / rel for rel in [
        "lean/VerifyDossiers.lean", "lean/Historical.lean", "lean/Comparative.lean", "lean/Audit.lean",
        "lean/lakefile.toml", "lean/lean-toolchain", "lean/lake-manifest.json",
        "scripts/build_m2_fixtures.py", "scripts/reference_rules.py", "scripts/verify_m2.py",
        "scripts/check_proofs.py", "tests/test_m2_contracts.py", ".github/workflows/ci.yml",
        "docs/rule-semantics.md", "docs/08-m2-delivery.md",
        "reviews/m2-packet.json", "reviews/m2-responses.json", "reviews/m2-independent-review.md",
        "reviews/m2-code-review.md",
        "data/rule-packages/contextual-examples.json"]]
    paths += list((ROOT / "lean/Historical").glob("*.lean"))
    paths += list((ROOT / "lean/Comparative").glob("*.lean"))
    paths += list((ROOT / "data/contextual-rules").rglob("*.json"))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}


def invoke(binary, args, expected_codes=(0,)):
    result = subprocess.run([str(binary), *args], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert result.returncode in expected_codes, (args, result.returncode, result.stderr, result.stdout[:2000])
    return json.loads(result.stdout)


def evaluate(binary, model, inputs):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "evaluation.json"
        path.write_text(json.dumps(dict(model=model, inputs=inputs), ensure_ascii=False))
        result = invoke(binary, ["--evaluate", str(path)])
    assert result["accepted"] and len(result["results"]) == len(inputs)
    return result["results"]


def forward_packages():
    """Cross every mode/direction with distinct local matching situations."""
    templates = [
        rule(["a"], "b"), rule(["a"], "b", left=[["b"]]),
        rule(["a"], "b", right=[["b"]]), rule(["a"], None, left=[["b"]]),
        rule(["a"], None, right_edge=True), rule(["a"], None, left_edge=True),
        rule(["a", "b"], "c", left=["+"], right=["*"]),
        rule(["a"], "b", left=["*", "*"], left_edge=True),
        rule(["a"], "b", right=["*", "*"], right_edge=True),
        rule(["a"], "b", left=["*", "+"], right=["*"]),
    ]
    result = []
    for i, template in enumerate(templates):
        for direction in ["left-to-right", "right-to-left"]:
            for mode in ["simultaneous", "feeding"]:
                r = dict(template, direction=direction, mode=mode)
                result.append(package(f"enumeration-{i}-{direction}-{mode}", [r], ["a", "b", "c"]))
    for i, rules in enumerate([
        [rule(["a"], "b"), rule(["b"], "c")],
        [rule(["b"], "c"), rule(["a"], "b")],
        [rule(["a"], None, left=[["b"]], mode="feeding"), rule(["b"], "c", right_edge=True)],
        [rule(["a"], None, right=[["b"]], direction="right-to-left", mode="feeding"), rule(["b"], "c", left_edge=True)],
    ]):
        result.append(package(f"enumeration-cascade-{i}", rules, ["a", "b", "c"]))
    return result


def verify(binary, audit):
    packet, response, review = current_review()
    generated_check()
    audit_run = subprocess.run([sys.executable, str(ROOT / "scripts/check_proofs.py"), str(audit)],
                               cwd=ROOT, capture_output=True, text=True)
    assert audit_run.returncode == 0, audit_run.stdout + audit_run.stderr
    print(audit_run.stdout.strip())
    declarations = re.findall(r"^#print axioms\s+(\S+)", (ROOT / "lean/Audit.lean").read_text(), re.M)
    m2_theorems = [n for n in declarations if n.startswith(("Historical.Rules.", "Historical.Certificates.", "Historical.RuleInput."))]
    assert len(m2_theorems) >= 17
    suite = invoke(binary, ["--suite", "contextual-rules"])
    assert suite["passed"] and suite["valid_fixtures"] >= 10 and suite["adversarial_fixtures"] >= 40
    fixtures = [{k: row[k] for k in ["fixture", "category", "expected_accept", "expected_error", "accepted", "passed"]}
                | {"error_codes": [i["code"] for i in row["issues"]]} for row in suite["results"]]
    assert all(f["passed"] for f in fixtures)
    required_rejections = {"whole-word-lookup", "lexical-exceptions", "insertion-operation",
                           "word-replacement", "hidden-predicate", "unbounded-left-context", "unbounded-right-context"}
    assert required_rejections <= {Path(f["fixture"]).stem for f in fixtures if not f["accepted"]}
    answers = {a["id"]: a for a in response["entries"]}
    hand_results = []
    for c in packet["cases"]:
        result = evaluate(binary, package(c["id"], c["rules"]), [c["input"]])[0]
        steps = [s["output"] for s in result["steps"]]
        answer = answers[c["id"]]
        assert result["input"] == c["input"] and steps == answer["steps"] and result["output"] == answer["output"], c["id"]
        reference_steps, reference_out = reference_run(c["rules"], c["input"])
        assert reference_steps == answer["steps"] and reference_out == answer["output"], c["id"]
        hand_results.append(dict(id=c["id"], passes=len(steps), lean_matches_hand_work=True,
                                 python_matches_hand_work=True))
    words = sorted({w for alphabet in [("a", "b", "c"), ("a", "b", "+")]
                    for n in range(5) for w in itertools.product(alphabet, repeat=n)}, key=lambda w: (len(w), w))
    inputs = [list(w) for w in words]
    comparisons = []
    for model in forward_packages():
        results = evaluate(binary, model, inputs)
        for word, result in zip(inputs, results):
            expected_steps, expected_out = reference_run([law["rule"] for law in model["laws"]], word)
            assert result["input"] == word
            assert [s["output"] for s in result["steps"]] == expected_steps, (model["id"], word, result, expected_steps)
            assert result["output"] == expected_out, (model["id"], word)
            assert len(result["output"]) <= len(word)
            assert result["output"].count("+") == word.count("+")
        comparisons.append(dict(package=model["id"], words=len(inputs), passed=True))
    # Input handling must not depend on JSON field order or BMP escape spelling.
    base = json.loads((ROOT / "data/contextual-rules/valid/unicode-atoms.json").read_text())
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "reordered.json"
        path.write_text(json.dumps(base, ensure_ascii=True, sort_keys=True))
        saved = Path(temp) / "result.json"
        accepted = invoke(binary, ["--file", str(path), "--report", str(saved)])
        assert accepted["accepted"] and json.loads(saved.read_text()) == accepted
        missing = subprocess.run([str(binary), "--file", str(Path(temp) / "absent.json")],
                                 cwd=ROOT, capture_output=True, text=True, timeout=30)
        assert missing.returncode == 2
    rejected = invoke(binary, ["--file", "data/contextual-rules/invalid/missing-step.json"], expected_codes=(1,))
    assert not rejected["accepted"] and any(i["code"] == "TRACE_LENGTH" for i in rejected["issues"])
    usage = subprocess.run([str(binary)], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert usage.returncode == 2
    return dict(milestone="M2", status="delivered", all_deliverables_accepted=True,
                criteria=[
                    dict(id="M2-semantics", status="passed", result=f"Total interpreter; {len(hand_results)} independently hand-worked cases and {sum(x['passes'] for x in hand_results)} passes agree exactly", evidence=["docs/rule-semantics.md", "reviews/m2-independent-review.md"]),
                    dict(id="M2-checker", status="passed", result=f"{len(m2_theorems)} new kernel-checked theorems; entire-trace soundness/completeness and dossier acceptance reflection", evidence=["lean/Historical/Rules.lean", "lean/Historical/Certificates.lean", "lean/Historical/RuleInput.lean", "lean/Audit.lean"]),
                    dict(id="M2-adversarial", status="passed", result=f"{suite['valid_fixtures']} valid and {suite['adversarial_fixtures']} adversarial fixtures; every intended outcome/rejection reason matched", evidence="data/contextual-rules/manifest.json"),
                    dict(id="M2-no-memorization", status="passed", result="Typed local grammar, finite inventory, two-token context bounds; lexical lookup, callbacks, word replacement, insertion and unrestricted iteration rejected", evidence=["docs/rule-semantics.md", "data/rule-packages/contextual-examples.json"])
                ],
                valid_fixtures=suite["valid_fixtures"], adversarial_fixtures=suite["adversarial_fixtures"], fixtures=fixtures,
                independent_review=review, hand_worked_examples=hand_results,
                implementation_review=dict(evidence="reviews/m2-code-review.md",
                                           reviewer_type="independent_ai_agent",
                                           findings=[dict(id="M2-R1", status="resolved",
                                                          regression_category="unicode-whitespace")],
                                           limitation="Recorded AI code-review finding and recheck; not an automated guarantee of exhaustive review."),
                forward_cross_check=dict(max_word_length=4, alphabets=[["a", "b", "c"], ["a", "b", "+"]],
                                         distinct_words_per_package=len(inputs), packages=len(comparisons),
                                         comparisons=sum(x["words"] for x in comparisons), all_passed=True, results=comparisons),
                proof_audit=dict(total_declarations=len(declarations), m2_declarations=m2_theorems,
                                 all_declarations_audited=True, project_axioms=False, proof_placeholders=False),
                json_order_and_bmp_escapes_preserved=True,
                cli_contracts=dict(accept_exit=0, reject_exit=1, invocation_and_io_exit=2,
                                   saved_report_equals_stdout=True),
                limitations=["These packages are synthetic semantics examples, not verified historical sound laws.",
                             "Formal results are relative to the declared tokenization, local tests, pass convention and ordered package.",
                             "The byte parser and package validators are executable infrastructure; their entire implementation is not formally verified.",
                             "Grammar restrictions do not prove natural classes or prevent every form of empirical overfitting.",
                             "The Python comparison oracle is test infrastructure, not part of the proof trust base.",
                             "Independent hand-work is by a separate AI agent, not a human or family specialist."],
                input_hashes=input_hashes())


def check_saved_report(report):
    _, _, review = current_review(); generated_check()
    assert report["input_hashes"] == input_hashes(), "Stale M2 report: rerun after building and auditing current source"
    assert report["independent_review"] == review
    assert report["all_deliverables_accepted"] and report["status"] == "delivered"
    assert {c["id"] for c in report["criteria"]} == {"M2-semantics", "M2-checker", "M2-adversarial", "M2-no-memorization"}
    assert all(c["status"] == "passed" for c in report["criteria"])
    assert all(f["passed"] for f in report["fixtures"])
    assert report["valid_fixtures"] >= 10 and report["adversarial_fixtures"] >= 40
    assert report["forward_cross_check"]["all_passed"]
    milestone = next(m for m in json.loads((ROOT / "data/milestones.json").read_text()) if m["id"] == "M2")
    assert milestone["status"] == "delivered", "M2 register must agree with completed acceptance evidence"
    for artifact in milestone["artifacts"]:
        assert (ROOT / artifact).exists(), "Missing M2 artifact: " + artifact


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary", type=Path, default=ROOT / "lean/.lake/build/bin/verify_dossiers")
    p.add_argument("--audit", type=Path, default=ROOT / "reports/lean-axioms-local.txt")
    p.add_argument("--check-report", action="store_true")
    args = p.parse_args(); path = ROOT / "reports/contextual-rules.json"
    if args.check_report:
        check_saved_report(json.loads(path.read_text()))
        print("M2: all four criteria accepted; review, input hashes and delivered artifact paths verified")
    else:
        report = verify(args.binary.resolve(), args.audit.resolve())
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(f"M2: {report['valid_fixtures']} valid, {report['adversarial_fixtures']} adversarial, "
              f"{len(report['hand_worked_examples'])} independent examples, "
              f"{report['forward_cross_check']['comparisons']} forward comparisons; all passed")


if __name__ == "__main__":
    main()
