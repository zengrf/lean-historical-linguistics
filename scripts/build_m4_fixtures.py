"""Build authored M4 cases; expected inverse sets are not obtained from Lean.

Larger exhaustive comparisons are constructed separately by verify_m4.py.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from build_m2_fixtures import rule, package

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/reconstruction"


def cell(s):
    return dict(kind="boundary" if s == "+" else "segment", value=s)


def form(word):
    return None if word is None else [cell(s) for s in word]


def analysis(name, observations, rules=None, inventory=("a", "b"), axis=("A", "B")):
    rules = rules if rules is not None else [[] for _ in axis]
    return dict(id=name, description="Constructed joint analysis: " + name, proto_node_id="s0",
                choice_bindings=[], alignment_evidence=None,
                branches=[dict(doculect_id=d, package=package(name + "-" + d, rs, inventory)) for d, rs in zip(axis, rules)],
                observations=[dict(doculect_id=d, source_ref="synthetic:" + name + ":" + d, form=form(w)) for d, w in zip(axis, observations)])


def spec(name, analyses=None, inventory=("a", "b"), bound=2, axis=("A", "B"), **overrides):
    d = dict(schema_version="1.0.0", id=name, description="Synthetic bounded reconstruction: " + name,
             source_kind="synthetic", claim="bounded-relative-completeness", proto_inventory=list(inventory),
             allow_morphemes=False, max_length=bound, analysis_bound=16, max_rules_per_branch=16,
             doculects=list(axis), choice_groups=[], analyses=analyses if analyses is not None else [analysis("identity", [["a"], ["a"]])],
             candidate_budget=20000, time_limit_ms=None)
    d.update(overrides)
    return d


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def generate():
    files = {}; fixtures = []

    def add(name, d, words=(), status="complete", code=None, reason=None, category="inverse", rationale="", ids=None):
        assert rationale
        reason = reason or {"complete": "exhausted", "incomplete": "candidate-budget", "invalid": "input"}[status]
        path = status + "/" + name + ".json"
        files[path] = d if isinstance(d, bytes) else encode(d)
        if ids is None:
            ids = [d["analyses"][0]["id"]] * len(words) if words else []
        fixtures.append(dict(path=path, status=status, code=code, reason=reason,
                             candidates=[dict(analysis_id=i, protoform=w) for i, w in zip(ids, words)],
                             category=category, rationale=rationale))

    base = spec("identity")
    add("identity", base, [["a"]], rationale="An identity model retains exactly the observed word.")
    merger = analysis("merger", [["a"], ["a"]], [[rule(["b"], "a")]] * 2)
    add("merger", spec("merger", [merger], bound=1), [["a"], ["b"]], category="ambiguity", rationale="A merger preserves both possible ancestors.")
    delete = analysis("delete", [[], []], [[rule(["a", "b"], None)]] * 2)
    add("deletion", spec("deletion", [delete]), [[], ["a"], ["b"], ["a", "a"], ["a", "b"], ["b", "a"], ["b", "b"]], rationale="Every bounded word, including empty, derives the empty reflex.")
    add("conflicting-observations", spec("conflicting", [analysis("conflicting", [["a"], ["b"]])]), rationale="A completed empty set reflects inconsistent observations under this fixed identity model.")
    add("absent-first", spec("absent-first", [analysis("missing", [None, ["b"]])]), [["b"]], rationale="An absent branch provides no word constraint.")
    add("empty-is-observed", spec("empty-is-observed", [analysis("empty", [[], None])]), [[]], rationale="Present empty requires an empty output and differs from absence.")
    missing = spec("all-missing", [analysis("missing", [None, None])], bound=1)
    add("all-missing", missing, [[], ["a"], ["b"]], category="absence", rationale="With no observations the entire bounded space remains visible; no unique ancestor is selected.")
    unknown = analysis("unknown", [["a"], None]); unknown["observations"][0]["form"] = [dict(kind="unknown", value="unread")]
    add("unknown-one-segment", spec("unknown", [unknown]), [["a"], ["b"]], category="uncertainty", rationale="An unknown is exactly one segment, not an arbitrary string or an empty word.")
    u = deepcopy(unknown); u["observations"][0]["form"].append(cell("b"))
    add("unknown-with-known-context", spec("unknown-context", [u]), [["a", "b"], ["b", "b"]], category="uncertainty", rationale="Unknown masks retain length and known neighboring cells.")
    add("length-zero-excludes-observed", spec("length-zero", bound=0), rationale="A length bound may exclude an otherwise fitting ancestor; emptiness is relative to that bound.")
    add("empty-inventory", spec("empty-inventory", [analysis("empty-alphabet", [None, None])], inventory=[], bound=4), [[]], rationale="The empty alphabet has precisely the empty word.")
    a = analysis("unicode", [["a̱"], None], inventory=["a̱", "tʰ"])
    add("unicode-atoms", spec("unicode-atoms", [a], inventory=["a̱", "tʰ"], bound=1), [["a̱"]], rationale="Combining-mark and aspirated strings remain atomic Unicode symbols.")
    a = analysis("supplementary", [["𐀀"], None], inventory=["𐀀", "a̱"])
    add("supplementary-literal", spec("supplementary", [a], inventory=["𐀀", "a̱"], bound=1), [["𐀀"]], rationale="Literal supplementary UTF-8 is retained through enumeration and certificates.")
    alternatives = [analysis("model-1", [["a"], ["a"]]), analysis("model-2", [["a"], ["a"]])]
    add("same-word-distinct-analyses", spec("distinct-analyses", alternatives), [["a"], ["a"]], ids=["model-1", "model-2"], category="ambiguity", rationale="Equal word strings under distinct named analyses are not silently collapsed.")
    linked = spec("linked", [analysis("ab", [["a"], ["b"]]), analysis("ba", [["b"], ["a"]])], bound=1)
    linked["choice_groups"] = [dict(id="reading", options=["ab", "ba"], description="Whole linked reading tuple")]
    for a in linked["analyses"]:
        a["choice_bindings"] = [dict(group_id="reading", option_id=a["id"])]
    add("linked-readings-no-hybrid", linked, category="joint-alternatives", rationale="Neither AB nor BA fits identity; marginal AA/BB combinations must not be invented.")
    models = spec("joint-models", [analysis("history-a", [["a"], ["b"]], [[], [rule(["a"], "b")]]),
                                   analysis("history-b", [["a"], ["b"]], [[rule(["b"], "a")], []])], bound=1)
    models["choice_groups"] = [dict(id="history", options=["a", "b"], description="Joint branch-law analysis")]
    for i, a in enumerate(models["analyses"]):
        a["choice_bindings"] = [dict(group_id="history", option_id=["a", "b"][i])]
    add("joint-model-alternatives", models, [["a"], ["b"]], ids=["history-a", "history-b"], category="joint-alternatives", rationale="Alternative ancestors and branch packages remain attached to their original joint analyses.")
    boundaries = spec("boundaries", [analysis("boundary", [["a", "+", "b"], None])], bound=3, allow_morphemes=True)
    add("morpheme-enumeration", boundaries, [["a", "+", "b"]], category="enumeration", rationale="A declared morpheme atom participates in the length bound and survives derivation.")
    d = deepcopy(boundaries); d["id"] = "morpheme-excluded"; d["allow_morphemes"] = False
    add("morpheme-excluded", d, rationale="A model that cannot create boundaries has no candidate when the proto alphabet excludes them.")
    add("boundary-shape-filter", spec("shape", [analysis("shape", [None, None], inventory=["a"])], inventory=["a"], bound=3, allow_morphemes=True),
        [[], ["a"], ["a", "a"], ["a", "a", "a"], ["a", "+", "a"]], category="enumeration", rationale="Leading, trailing and adjacent boundaries are outside the explicitly defined proto-word space.")
    ordered = [rule(["a"], "b"), rule(["b"], "c")]
    for name, laws, words in [("ordered", ordered, [["a"], ["b"], ["c"]]), ("reversed", ordered[::-1], [["b"], ["c"]])]:
        add(name, spec(name, [analysis(name, [["c"], ["c"]], [laws, laws], inventory=["a", "b", "c"])], inventory=["a", "b", "c"], bound=1), words, category="chronology", rationale="Inverse candidates respect the named M2 cascade order.")
    weak = analysis("fixed-model", [["a"], None], [[rule(["b"], "a")], []])
    add("weak-evidence", spec("weak", [weak], bound=1), [["a"], ["b"]], category="monotonicity", rationale="The weak observation permits two ancestors under a fixed model and space.")
    strong = deepcopy(weak); strong["observations"][1]["form"] = form(["b"])
    add("strong-evidence", spec("strong", [strong], bound=1), [["b"]], category="monotonicity", rationale="Adding a second observation removes a candidate without changing the model or space.")

    m3 = json.loads((ROOT / "data/correspondence/sites/shared-01.json").read_text())
    target = m3["alignment_data"]["alignments"][0]
    axis = m3["alignment_data"]["doculects"]
    a = analysis("m3-linked", [["p"], ["b"], None, None], [[], [rule(["p"], "b")], [], []], inventory=["p", "b"], axis=axis)
    a["observations"] = [dict(doculect_id=r["doculect_id"], source_ref=r["source_ref"], form=r["original"]) for r in target["rows"]]
    a["alignment_evidence"] = dict(dossier=m3, alignment_id=target["id"])
    bridge = spec("m3-bridge", [a], inventory=["p", "b"], bound=1, axis=axis)
    add("m3-bridge", bridge, [["p"]], category="m3-integration", rationale="Original observations and citations exactly match a fully checked M3 alignment.")
    d = deepcopy(base); d["candidate_budget"] = 7
    add("budget-exact-space", d, [["a"]], category="completion", rationale="A budget equal to the entire scope is complete, not exhausted early.")
    for name, d, words, reason in [
        ("zero-budget", dict(base, candidate_budget=0), [], "candidate-budget"),
        ("empty-prefix", dict(base, candidate_budget=1), [], "candidate-budget"),
        ("nonempty-prefix", dict(base, candidate_budget=2), [["a"]], "candidate-budget"),
        ("absent-prefix", dict(missing, candidate_budget=1), [[]], "candidate-budget"),
        ("zero-deadline", dict(base, time_limit_ms=0), [], "time-limit"),
        ("space-ceiling", spec("large", inventory=["a", "b"], bound=15), [], "space-limit"),
    ]:
        add(name, d, words, "incomplete", reason=reason, category="resource-limit", rationale="Unexamined hypotheses prevent a completeness or no-candidate claim, even when the retained prefix is empty.")

    def bad(name, mutate, code, rationale, source=None, category="validation"):
        d = deepcopy(base if source is None else source); d["id"] = name; mutate(d)
        add(name, d, status="invalid", code=code, category=category, rationale=rationale)

    def pkg(d):
        return d["analyses"][0]["branches"][0]["package"]

    def obs(d):
        return d["analyses"][0]["observations"][0]

    bad("duplicate-inventory", lambda d: d["proto_inventory"].append("a"), "PROTO_INVENTORY", "Duplicate alphabet members cannot multiply histories.")
    for name, symbol in [("whitespace", "a\u202fb"), ("reserved", "+"), ("empty-symbol", "")]:
        bad(name, lambda d, s=symbol: d["proto_inventory"].append(s), "PROTO_INVENTORY", "Proto atoms follow the exact M2 symbol contract.")
    bad("wrong-version", lambda d: d.update(schema_version="2"), "SCHEMA_VERSION", "Unknown schema versions fail closed.")
    bad("bad-source-kind", lambda d: d.update(source_kind="unspecified"), "QUERY_METADATA", "Source scope must be explicit.")
    for name, value in [("max_length", 17), ("analysis_bound", 17), ("max_rules_per_branch", 17), ("candidate_budget", 20001), ("time_limit_ms", 60001)]:
        bad("profile-" + name, lambda d, k=name, v=value: d.update({k: v}), "PROFILE_LIMIT", "Unsupported execution limits are invalid input, not a completed empty space.")
    for claim in ["unique-ancestor", "global-completeness", "optimal", "best-only"]:
        bad("claim-" + claim, lambda d, c=claim: d.update(claim=c), "UNSUPPORTED_CLAIM", "The checker only claims bounded relative completeness.")
    bad("empty-analyses", lambda d: d.update(analyses=[]), "ANALYSIS_SPACE", "At least one explicit joint analysis is required.")
    bad("analysis-bound", lambda d: d.update(analysis_bound=0), "ANALYSIS_SPACE", "Actual analyses must fit the declared choice bound.")
    bad("duplicate-analysis-id", lambda d: d["analyses"].append(deepcopy(d["analyses"][0])), "ANALYSIS_SPACE", "Analysis identity cannot be reused.")
    bad("invalid-proto-node", lambda d: d["analyses"][0].update(proto_node_id=""), "ANALYSIS_METADATA", "Every candidate names a valid proto node.")
    bad("missing-branch", lambda d: d["analyses"][0]["branches"].pop(), "DOCULECT_AXIS", "The full declared branch model is required.")
    bad("reordered-observations", lambda d: d["analyses"][0]["observations"].reverse(), "DOCULECT_AXIS", "Observation positions follow a common explicit axis.")
    bad("duplicate-doculect", lambda d: d["doculects"].__setitem__(1, "A"), "DOCULECT_AXIS", "Doculect identities are distinct.")
    bad("missing-source", lambda d: obs(d).update(source_ref=""), "SOURCE_REF", "Observation sources remain explicit.")
    for kind, value in [("gap", None), ("missing", None), ("boundary", "+"), ("unknown", "")]:
        bad("bad-form-" + kind, lambda d, k=kind, v=value: obs(d).update(form=[dict(kind=k, value=v)]), "OBSERVATION_SHAPE", "Original evidence cannot silently become a gap, missing cell, malformed boundary or empty unknown value.")
    bad("unknown-observed-segment", lambda d: obs(d).update(form=form(["z"])), "OBSERVATION_INVENTORY", "Known observations belong to the named branch inventory.")
    bad("proto-not-in-package", lambda d: pkg(d).update(inventory=["a"]), "PROTO_PACKAGE_INVENTORY", "Every possible proto segment belongs to each forward package.")
    bad("wrong-root-stage", lambda d: d["analyses"][0].update(proto_node_id="other-root"), "PROTO_STAGE", "All branches start at the candidate's proto node.")
    bad("rule-count-bound", lambda d: d.update(max_rules_per_branch=0), "RULE_BOUND", "Rules cannot exceed the declared complexity bound.", source=spec("merger", [merger], bound=1))
    bad("broken-stage-chain", lambda d: pkg(d).update(final_stage="wrong"), "STAGE_CHAIN", "M2 chronological package validation remains in the acceptance path.")
    bad("package-identity-collision", lambda d: d["analyses"][0]["branches"][1]["package"].update(id=pkg(d)["id"], description="different-definition"), "PACKAGE_COLLISION", "A package identity/version cannot conceal different models.")
    bad("missing-joint-binding", lambda d: d["analyses"][0].update(choice_bindings=[]), "JOINT_BINDINGS", "Each listed tuple binds every shared choice.", source=linked)
    bad("unknown-choice-option", lambda d: d["analyses"][0]["choice_bindings"][0].update(option_id="invented"), "JOINT_BINDINGS", "Only declared reading alternatives are licensed.", source=linked)
    bad("duplicate-choice-group", lambda d: d["choice_groups"].append(deepcopy(d["choice_groups"][0])), "CHOICE_GROUP", "Linked choice identities are unique.", source=linked)
    bad("m3-corrupt-alignment", lambda d: d["analyses"][0]["alignment_evidence"]["dossier"]["alignment_data"]["alignments"][0]["rows"][0].update(aligned=[cell("b")]), "M3_CERTIFICATE", "The evidence bridge cannot bypass alignment or correspondence checking.", source=bridge)
    bad("m3-unknown-target", lambda d: d["analyses"][0]["alignment_evidence"].update(alignment_id="absent"), "M3_ALIGNMENT", "A bridge must identify an actual checked alignment.", source=bridge)
    bad("m3-changed-original", lambda d: obs(d).update(form=form(["b"])), "M3_OBSERVATIONS", "Claimed observations must match the M3 original values exactly.", source=bridge)
    bad("m3-changed-source", lambda d: obs(d).update(source_ref="different-source"), "M3_OBSERVATIONS", "The bridge retains the source identity as well as the cells.", source=bridge)
    for name, mutate in [
        ("hidden-candidate-list", lambda d: d.update(candidates=[["a"]])),
        ("hidden-score", lambda d: d.update(score=1.0)),
        ("positional-alternatives", lambda d: obs(d).update(alternatives=[["a"], ["b"]])),
        ("omitted-null", lambda d: d.pop("time_limit_ms")),
        ("negative-bound", lambda d: d.update(max_length=-1)),
        ("float-budget", lambda d: d.update(candidate_budget=1.5)),
    ]:
        bad(name, mutate, "JSON_SHAPE", "Undeclared fields or invalid scalar shapes cannot change the finite search contract.", category="parser")
    for name, raw, code in [
        ("duplicate-key", b'{"id":"other",' + encode(base)[1:], "DUPLICATE_JSON_KEY"),
        ("escaped-duplicate-key", b'{"\\u0069d":"other",' + encode(base)[1:], "DUPLICATE_JSON_KEY"),
        ("invalid-utf8", b'\xff', "UTF8"),
        ("invalid-json", b'{', "JSON_SYNTAX"),
        ("surrogate-escape", encode(base).replace(b'"a"', b'"\\ud83d\\ude00"', 1), "UNICODE_ESCAPE"),
    ]:
        add(name, raw, status="invalid", code=code, category="parser", rationale="Malformed or ambiguous bytes are rejected before search.")
    files["manifest.json"] = encode(dict(schema_version="1.0.0", suite="bounded-reconstruction", fixtures=fixtures))
    return files


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("--check", action="store_true"); args = p.parse_args()
    files = generate(); expected = {DEST / name for name in files}
    if args.check:
        assert set(DEST.rglob("*.json")) == expected
        for name, value in files.items():
            assert (DEST / name).read_bytes() == value, "Stale M4 fixture: " + name
    else:
        for name, value in files.items():
            path = DEST / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(value)
        assert set(DEST.rglob("*.json")) == expected
    print(f"M4: {len(files)-1} fixtures {'verified' if args.check else 'written'}")


if __name__ == "__main__":
    main()
