"""Independent finite enumeration using itertools and the M2 Python interpreter.

This module never invokes Lean. It evaluates already validated M4 specifications;
parser/metadata rejection expectations are authored separately in the fixtures.
"""
import itertools

from reference_rules import run


def word_space(inventory, bound, allow_morphemes=False):
    alphabet = list(inventory) + (["+"] if allow_morphemes else [])
    words = []
    for n in range(bound + 1):
        for w in itertools.product(alphabet, repeat=n):
            if w and (w[0] == "+" or w[-1] == "+"):
                continue
            if any(x == y == "+" for x, y in zip(w, w[1:])):
                continue
            words.append(list(w))
    assert len({tuple(w) for w in words}) == len(words), "Validated alphabets must not generate duplicate words"
    return words


def matches(form, word):
    if form is None:
        return True
    if len(form) != len(word):
        return False
    for c, s in zip(form, word):
        if c["kind"] == "unknown":
            if s == "+":
                return False
        elif c["kind"] == "boundary":
            if c["value"] != "+" or s != "+":
                return False
        elif c["kind"] == "segment":
            if s == "+" or c["value"] != s:
                return False
        else:
            return False
    return True


def outputs(analysis, word):
    return {b["doculect_id"]: run([law["rule"] for law in b["package"]["laws"]], word)
            for b in analysis["branches"]}


def fits(analysis, word):
    predicted = outputs(analysis, word)
    return all(matches(o["form"], predicted[o["doculect_id"]][1]) for o in analysis["observations"])


def candidate(analysis, word):
    predicted = outputs(analysis, word); obs = {o["doculect_id"]: o for o in analysis["observations"]}
    branches = []
    for b in analysis["branches"]:
        p = b["package"]; steps, output = predicted[b["doculect_id"]]
        branches.append(dict(doculect_id=b["doculect_id"], package_id=p["id"], package_version=p["version"], input=word,
                             steps=[dict(rule_id=law["id"], input_stage=law["input_stage"], output_stage=law["output_stage"], output=w)
                                    for law, w in zip(p["laws"], steps)], output=output,
                             certificate_accepted=True, observation_satisfied=matches(obs[b["doculect_id"]]["form"], output)))
    return dict(analysis_id=analysis["id"], proto_node_id=analysis["proto_node_id"],
                choice_bindings=analysis["choice_bindings"], protoform=word, branches=branches)


def evaluate(d):
    k = len(d["proto_inventory"]) + int(d["allow_morphemes"])
    raw = len(d["analyses"]) * sum(k ** n for n in range(d["max_length"] + 1))
    result = dict(id=d["id"], input_valid=True, claim=d["claim"], issues=[], raw_hypothesis_upper_bound=raw,
                  candidates=[], history_count=0, distinct_protoform_count=0, no_candidate_in_scope=False)
    if raw > 20000 or d["time_limit_ms"] == 0:
        return result | dict(status="incomplete", complete=False, reason="space-limit" if raw > 20000 else "time-limit",
                             examined=0, scope_size=None)
    assert d["time_limit_ms"] is None, "Positive wall-clock limits have nondeterministic examined prefixes"
    words = word_space(d["proto_inventory"], d["max_length"], d["allow_morphemes"])
    scope = [(a, w) for a in d["analyses"] for w in words]
    examined = min(len(scope), d["candidate_budget"])
    candidates = [candidate(a, w) for a, w in scope[:examined] if fits(a, w)]
    complete = examined == len(scope)
    return result | dict(status="complete" if complete else "incomplete", complete=complete,
                         reason="exhausted" if complete else "candidate-budget", scope_size=len(scope), examined=examined,
                         candidates=candidates, history_count=len(candidates),
                         distinct_protoform_count=len({tuple(c["protoform"]) for c in candidates}),
                         no_candidate_in_scope=complete and not candidates)
