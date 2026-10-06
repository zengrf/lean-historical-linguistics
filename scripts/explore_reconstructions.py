"""Select whole hypotheses, enumerate with Lean, and compare their candidates.

The material catalogue is broader than the executable models. Published-pool
queries and bounded word enumeration have different completeness claims.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from build_pie_corpus import ROOT, encoded
from run_reconstruction import run_command
from verify_m5 import reference
from reference_reconstruction import evaluate

SOURCES = {
    "pie": "data/pie/lexical-input.json",
    "latin": "data/pie/latin-control-input.json",
    "kuki-chin": "data/kuki-chin/lexical-input.json",
    "tibetan-merger": "data/kuki-chin/diagnostic-input.json",
}
VOICE = ROOT / "data/kuki-chin/joint-analysis-input.json"
BIN = ROOT / "lean/.lake/build/bin"


def strict_read(path):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError("Duplicate JSON key: " + k)
            result[k] = v
        return result
    def constant(value):
        raise ValueError("Non-JSON constant: " + value)
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=constant)


def identify(query_id):
    match = re.fullmatch(r"(.+)-(identity|correspondence)(?:-(all-groups|northern-only))?", query_id)
    if match:
        return dict(case=match[1], hypothesis=match[2], scope=match[3] or "all-groups")
    return dict(case=query_id, hypothesis="source-fragment", scope="all-groups")


def catalogue(dataset):
    data = strict_read(ROOT / SOURCES[dataset])
    batch = data.get("batch", data)
    return [dict(id=q["id"], **identify(q["id"]), pool_size=len(q["pool"]),
        observations=len(q["branches"]), packages=[b["package_id"] for b in q["branches"]]) for q in batch["inverse"]]


def select_pool(dataset, case, hypotheses=(), scope="all-groups", explain=None, omit=()):
    data = strict_read(ROOT / SOURCES[dataset])
    batch = data.get("batch", data)
    cases = [q for q in batch["inverse"] if identify(q["id"])["case"] == case and identify(q["id"])["scope"] == scope]
    if not cases:
        raise ValueError("Unknown case/scope; use list to inspect supported cases")
    available = {identify(q["id"])["hypothesis"] for q in cases}
    if set(hypotheses) - available:
        raise ValueError("Unknown hypothesis; available: " + ", ".join(sorted(available)))
    queries = [q for q in cases if not hypotheses or identify(q["id"])["hypothesis"] in hypotheses]
    axes = {b["doculect_id"] for q in queries for b in q["branches"]}
    if set(omit) - axes:
        raise ValueError("Unknown observation to withhold")
    for q in queries:
        q["branches"] = [b for b in q["branches"] if b["doculect_id"] not in omit]
        if len(q["branches"]) < 2:
            raise ValueError("Pool execution requires at least two remaining observations")
    if explain is not None and (not isinstance(explain, list) or any(not isinstance(x, str) for x in explain)):
        raise ValueError("--explain requires a JSON array of segment tokens")
    forward = []
    if explain is not None:
        for q in queries:
            for i, b in enumerate(q["branches"]):
                forward.append(dict(id=f"explain-{q['id']}-{i}", package_id=b["package_id"], input=explain, expected=b["expected"]))
    pids = {b["package_id"] for q in queries for b in q["branches"]}
    batch["packages"] = [p for p in batch["packages"] if p["id"] in pids]
    batch["inverse"], batch["forward"] = queries, forward
    if "batch" in data:
        ids = {q["id"] for q in queries}
        data["package_scopes"] = [s for s in data["package_scopes"] if s["package_id"] in pids]
        data["query_scopes"] = [s for s in data["query_scopes"] if s["query_id"] in ids]
    return data


def select_bounded(data, analyses=(), choices=(), budget=None):
    data = deepcopy(data)
    available = {a["id"] for a in data["analyses"]}
    if set(analyses) - available:
        raise ValueError("Unknown analysis ID")
    groups = {g["id"]: set(g["options"]) for g in data["choice_groups"]}
    selected = {}
    for choice in choices:
        group, separator, option = choice.partition("=")
        if not separator or group not in groups or option not in groups[group]:
            raise ValueError("Unknown choice binding: " + choice)
        selected.setdefault(group, set()).add(option)
    retained = []
    for a in data["analyses"]:
        bindings = {b["group_id"]: b["option_id"] for b in a["choice_bindings"]}
        if (not analyses or a["id"] in analyses) and all(bindings.get(g) in options for g, options in selected.items()):
            retained.append(a)
    if not retained:
        raise ValueError("No declared joint analysis satisfies these selections; this is not an empty reconstruction result")
    data["analyses"] = retained
    if budget is not None:
        if budget < 0:
            raise ValueError("Budget must be nonnegative")
        data["candidate_budget"] = budget
    return data


def compare_pool(results):
    by_word = {}
    for r in results:
        for word in r["candidates"]:
            by_word.setdefault(tuple(word), []).append(r["id"])
    return dict(candidate_support=[dict(protoform=list(w), hypotheses=ids) for w, ids in sorted(by_word.items())],
        common_to_all=[list(w) for w, ids in sorted(by_word.items()) if len(ids) == len(results)],
        interpretation="Agreement/disagreement within this case and its declared pools; these counts are not probabilities.")


def execute_pool(request, binary_dir=BIN, timeout=180):
    scoped = "batch" in request
    binary = binary_dir / ("sino_tibetan_check" if scoped else "pie_check")
    with tempfile.TemporaryDirectory(prefix="reconstruction-") as directory:
        path = Path(directory) / "request.json"
        path.write_bytes(encoded(request))
        try:
            process = subprocess.run([str(binary), "--batch", str(path)], cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return dict(status="incomplete", complete=False, reason="process-timeout", no_candidate_in_scope=False), 3
        if process.returncode:
            raise ValueError("Lean rejected the request: " + (process.stdout or process.stderr)[:2000])
        result = json.loads(process.stdout)
    if scoped:
        if result.get("scope_valid") is not True:
            raise ValueError("Source scopes were not validated")
        result = result["result"]
    batch = request.get("batch", request)
    if result != reference(batch):
        raise ValueError("Lean and the independent interpreter disagree")
    explanations = []
    by_id = {f["id"]: f for f in result["forward"]}
    for q in batch["inverse"]:
        traces = [by_id[f"explain-{q['id']}-{i}"] for i in range(len(q["branches"]))
                  if f"explain-{q['id']}-{i}" in by_id]
        if traces:
            explanations.append(dict(query_id=q["id"], in_declared_pool=traces[0]["input"] in q["pool"],
                satisfies_observations=all(t["exact"] for t in traces),
                branches=[dict(doculect_id=b["doculect_id"], **t) for b, t in zip(q["branches"], traces)]))
    return dict(status="complete", complete=True, scope="selected-declared-pools", result=result,
        comparison=compare_pool(result["inverse"]), explanations=explanations,
        no_candidate_in_scope=all(r["empty_in_scope"] for r in result["inverse"])), 0


def execute_bounded(request, binary_dir=BIN, timeout=180):
    with tempfile.TemporaryDirectory(prefix="reconstruction-") as directory:
        path = Path(directory) / "request.json"
        path.write_bytes(encoded(request))
        result, code = run_command([str(binary_dir / "reconstruct"), "--file", str(path)], timeout)
    if code == 0 or (code == 3 and result.get("reason") in {"space-limit", "candidate-budget"}):
        # Positive cooperative deadlines have nondeterministic prefixes.
        if request["time_limit_ms"] is None and result != evaluate(request):
            raise ValueError("Lean and independent bounded enumeration disagree")
    return result, code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    ls = sub.add_parser("list")
    ls.add_argument("--dataset", choices=SOURCES)
    ls.add_argument("--spec", type=Path)
    pool = sub.add_parser("pool")
    pool.add_argument("--dataset", required=True, choices=SOURCES)
    pool.add_argument("--case", required=True)
    pool.add_argument("--hypothesis", action="append", default=[])
    pool.add_argument("--scope", choices=["all-groups", "northern-only"], default="all-groups")
    pool.add_argument("--explain", help='JSON token array, e.g. ["ndz"]')
    pool.add_argument("--omit-doculect", action="append", default=[])
    bounded = sub.add_parser("bounded")
    bounded.add_argument("--spec", type=Path, default=VOICE)
    bounded.add_argument("--analysis", action="append", default=[])
    bounded.add_argument("--choose", action="append", default=[], help="GROUP=OPTION; OR within a group, AND across groups")
    bounded.add_argument("--budget", type=int)
    for p in (pool, bounded):
        p.add_argument("--binary-dir", type=Path, default=BIN)
        p.add_argument("--timeout", type=float, default=180)
        p.add_argument("--save-request", type=Path)
        p.add_argument("--report", type=Path)
    args = parser.parse_args()
    code = 0
    try:
        if args.command == "list":
            if args.dataset and args.spec:
                raise ValueError("Choose --dataset or --spec")
            if args.dataset:
                result = dict(dataset=args.dataset, queries=catalogue(args.dataset),
                    hypothesis_note="identity and correspondence are experimental baselines, not complete historical theories")
            else:
                d = strict_read(args.spec or VOICE)
                result = {k: d[k] for k in ("id", "description", "choice_groups", "proto_inventory", "max_length", "source_kind")}
                result["analyses"] = [{k: a[k] for k in ("id", "description", "choice_bindings", "proto_node_id")} for a in d["analyses"]]
        else:
            if not math.isfinite(args.timeout) or args.timeout <= 0:
                raise ValueError("Timeout must be finite and positive")
            if args.command == "pool":
                original = ROOT / SOURCES[args.dataset]
                request = select_pool(args.dataset, args.case, args.hypothesis, args.scope,
                    json.loads(args.explain) if args.explain is not None else None, args.omit_doculect)
                execute = execute_pool
            else:
                original = args.spec
                request = select_bounded(strict_read(original), args.analysis, args.choose, args.budget)
                execute = execute_bounded
            if args.save_request:
                args.save_request.write_bytes(encoded(request))
            result, code = execute(request, args.binary_dir.resolve(), args.timeout)
            result = dict(schema_version="1.0.0", mode=args.command, request=request,
                original_input_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
                selected_request_sha256=hashlib.sha256(encoded(request)).hexdigest(), execution=result,
                withheld_observations=args.omit_doculect if args.command == "pool" else [])
            if args.report:
                args.report.write_bytes(encoded(result))
    except (ValueError, KeyError, TypeError, OSError) as error:
        result, code = dict(status="error", complete=False, no_candidate_in_scope=False, error=str(error)), 2
    print(encoded(result).decode(), end="")
    return code


if __name__ == "__main__":
    sys.exit(main())
