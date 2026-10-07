"""Checked conflict analysis, prediction partitions, chronology and paradigms."""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from build_pie_corpus import ROOT, encoded
from explore_reconstructions import (
    BIN,
    strict_read,
    select_pool,
    select_bounded,
    execute_pool,
    execute_bounded,
)
from reference_reconstruction import word_space, matches
from reference_research import (
    analyze_matrix,
    agrees,
    chronology as chronology_reference,
    paradigm as paradigm_reference,
)

EXAMPLES = ROOT / "data/research"


class IncompleteSearch(ValueError):
    pass


def checked(mode, request, binary_dir=BIN, timeout=90):
    with tempfile.TemporaryDirectory(prefix="comparative-research-") as folder:
        path = Path(folder) / "input.json"
        path.write_bytes(encoded(request))
        try:
            p = subprocess.run(
                [str(binary_dir / "research_check"), "--" + mode, str(path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as error:
            raise IncompleteSearch(
                "Lean process timed out; no completion claim is available"
            ) from error
    if p.returncode:
        raise ValueError("Lean rejected the request: " + (p.stdout or p.stderr)[:1600])
    result = json.loads(p.stdout)
    reference = {
        "matrix": analyze_matrix,
        "chronology": chronology_reference,
        "paradigm": paradigm_reference,
    }[mode](request)
    if result != reference:
        raise ValueError("Lean and the independent research interpreter disagree")
    return result


def matrix_analysis(axes, histories, selected=None, subset_budget=4096, binary_dir=BIN):
    if selected is None:
        selected = [a["id"] for a in axes if a["observed"]]
    if len(selected) != len(set(selected)) or set(selected) - {a["id"] for a in axes}:
        raise ValueError("Unknown or repeated observation axis")
    if any(a["id"] in selected and not a["observed"] for a in axes):
        raise ValueError("An unobserved probe cannot constrain the reconstruction")
    if not histories or len(histories) > 1024:
        raise ValueError(
            "Evidence analysis requires a nonempty universe of at most 1024 histories"
        )

    def projection(h, i):
        value = h["predictions"][i]
        if axes[i]["id"] not in selected:
            return value
        expected = h.get("observations", [a["expected"] for a in axes])[i]
        if isinstance(expected, dict) and "form" in expected:
            expected = expected["form"]
        if (
            isinstance(value, dict)
            and isinstance(expected, dict)
            and expected.get("tone") is None
        ):
            return {"segments": value["segments"], "tone": "unobserved"}
        if isinstance(expected, list) and expected and isinstance(expected[0], dict):
            return [
                (
                    "unobserved"
                    if i < len(expected) and expected[i]["kind"] == "unknown"
                    else v
                )
                for i, v in enumerate(value)
            ]
        return value

    matrix = dict(
        schema_version="1.0.0",
        id="finite-evidence-analysis",
        axes=[a["id"] for a in axes],
        selected=[i for i, a in enumerate(axes) if a["id"] in selected],
        subset_budget=subset_budget,
        histories=[
            dict(
                id=h["id"],
                agreements=h["agreements"],
                predictions=[
                    json.dumps(
                        projection(h, i),
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    for i in range(len(axes))
                ],
            )
            for h in histories
        ],
    )
    result = checked("matrix", matrix, binary_dir)
    # The explicit selected axes also identify the domain of equivalence.
    return dict(
        axes=axes,
        selected=selected,
        histories=histories,
        matrix=matrix,
        analysis=result,
        request_sha256=hashlib.sha256(encoded(matrix)).hexdigest(),
        complete=result["complete"],
        interpretation="Finite declared histories; partitions and pair counts are not historical probabilities.",
    )


def checked_forwards(request, jobs, binary_dir=BIN):
    """Retain the original inverse scope checks while deriving all input histories."""
    results = {}
    for start in range(0, len(jobs), 5000):
        part = deepcopy(request)
        batch = part.get("batch", part)
        batch["forward"] = jobs[start : start + 5000]
        result, code = execute_pool(part, binary_dir)
        if code == 3:
            raise IncompleteSearch("Forward derivations timed out")
        if code != 0:
            raise ValueError("Forward derivations were not accepted")
        results.update({r["id"]: r for r in result["result"]["forward"]})
    return results


def analyze_pool(
    dataset,
    case,
    hypotheses=(),
    scope="all-groups",
    selected=None,
    subset_budget=4096,
    binary_dir=BIN,
):
    request = select_pool(dataset, case, hypotheses, scope)
    batch = request.get("batch", request)
    queries = batch["inverse"]
    branches = queries[0]["branches"]
    if any(
        [b["doculect_id"] for b in q["branches"]]
        != [b["doculect_id"] for b in branches]
        for q in queries
    ):
        raise ValueError("Selected hypotheses use different observation axes")
    if sum(len(q["pool"]) for q in queries) > 1024 or len(branches) > 16:
        raise ValueError(
            "Evidence analysis profile: at most 1024 histories and 16 axes"
        )
    axes = [
        dict(
            id=b["doculect_id"],
            label=b["doculect_id"],
            expected=b["expected"],
            observed=True,
            source_ref=f"{dataset}:{case}:{b['doculect_id']}",
        )
        for b in branches
    ]
    jobs = []
    states = []
    for ai, q in enumerate(queries):
        for wi, word in enumerate(q["pool"]):
            hid = f"h-{ai}-{wi}"
            states.append(
                dict(
                    id=hid,
                    analysis_id=q["id"],
                    protoform=word,
                    source_scope=dataset + ":" + case,
                    branch_refs=[dict(b) for b in q["branches"]],
                )
            )
            for bi, b in enumerate(q["branches"]):
                jobs.append(
                    dict(
                        id=f"{hid}-b-{bi}",
                        package_id=b["package_id"],
                        input=word,
                        expected=b["expected"],
                    )
                )
    forwards = checked_forwards(request, jobs, binary_dir)
    for state in states:
        trace = [forwards[f"{state['id']}-b-{bi}"] for bi in range(len(branches))]
        state.update(
            predictions=[t["output"] for t in trace],
            agreements=[t["exact"] for t in trace],
            certificates=trace,
        )
    return dict(
        kind="pool",
        input_request=request,
        **matrix_analysis(axes, states, selected, subset_budget, binary_dir),
    )


def analyze_bounded(
    spec, analyses=(), choices=(), selected=None, subset_budget=4096, binary_dir=BIN
):
    request = select_bounded(spec, analyses, choices)
    initial, code = execute_bounded(request, binary_dir)
    if code == 3:
        raise IncompleteSearch("The underlying word enumeration is incomplete")
    if code != 0:
        raise ValueError("Invalid bounded specification")
    if initial["scope_size"] > 1024:
        raise ValueError("Evidence analysis is limited to 1024 complete histories")
    words = word_space(
        request["proto_inventory"], request["max_length"], request["allow_morphemes"]
    )
    axes = [
        dict(
            id=o["doculect_id"],
            label=o["doculect_id"],
            expected=o["form"],
            observed=o["form"] is not None,
            source_ref=o["source_ref"],
        )
        for o in request["analyses"][0]["observations"]
    ]
    packages = {}
    jobs, states = [], []
    for ai, a in enumerate(request["analyses"]):
        for b in a["branches"]:
            p = b["package"]
            if p["id"] in packages and packages[p["id"]] != p:
                raise ValueError("A package ID names different models")
            packages[p["id"]] = p
        for wi, word in enumerate(words):
            hid = f"h-{ai}-{wi}"
            states.append(
                dict(
                    id=hid,
                    analysis_id=a["id"],
                    protoform=word,
                    source_scope=a["proto_node_id"],
                    choice_bindings=a["choice_bindings"],
                    observations=a["observations"],
                )
            )
            for bi, b in enumerate(a["branches"]):
                jobs.append(
                    dict(
                        id=f"{hid}-b-{bi}",
                        package_id=b["package"]["id"],
                        input=word,
                        expected=None,
                    )
                )
    forward_request = dict(
        schema_version="1.0.0",
        id="bounded-evidence-predictions",
        packages=list(packages.values()),
        forward=[],
        inverse=[],
    )
    forwards = checked_forwards(forward_request, jobs, binary_dir)
    for s in states:
        trace = [forwards[f"{s['id']}-b-{bi}"] for bi in range(len(axes))]
        s.update(
            predictions=[t["output"] for t in trace],
            agreements=[
                matches(o["form"], t["output"])
                for o, t in zip(s["observations"], trace)
            ],
            certificates=trace,
        )
    # All supplied joint readings must mark an axis observed before it can be selected.
    for i, axis in enumerate(axes):
        axis["observed"] = all(
            a["observations"][i]["form"] is not None for a in request["analyses"]
        )
    return dict(
        kind="bounded",
        input_request=request,
        **matrix_analysis(axes, states, selected, subset_budget, binary_dir),
    )


def analyze_paradigm(
    request, analyses=(), selected=None, subset_budget=4096, binary_dir=BIN
):
    request = deepcopy(request)
    ids = {a["id"] for a in request["analyses"]}
    if set(analyses) - ids:
        raise ValueError("Unknown paradigm analysis")
    if analyses:
        request["analyses"] = [a for a in request["analyses"] if a["id"] in analyses]
    result = checked("paradigm", request, binary_dir)
    cells = request["analyses"][0]["cells"]
    if any(
        [c["id"] for c in a["cells"]] != [c["id"] for c in cells]
        for a in request["analyses"]
    ):
        raise ValueError("Joint paradigms have different cell axes")
    axes = [
        dict(
            id=c["id"],
            label=c["id"],
            expected=c["expected"],
            observed=all(
                a["cells"][i]["expected"] is not None for a in request["analyses"]
            ),
            source_ref=c["source_ref"],
        )
        for i, c in enumerate(cells)
    ]
    by = {a["id"]: a for a in request["analyses"]}
    states = []
    for i, h in enumerate(result["histories"]):
        a = by[h["analysis_id"]]
        predicted = [c["output"] for c in h["cells"]]
        states.append(
            dict(
                id=f"h-{i}",
                analysis_id=h["analysis_id"],
                protoform=h["input"],
                source_scope=request["source_scope"],
                predictions=predicted,
                observations=[c["expected"] for c in a["cells"]],
                agreements=[
                    agrees(out, c["expected"]) for c, out in zip(a["cells"], predicted)
                ],
                certificates=h["cells"],
            )
        )
    return dict(
        kind="paradigm",
        input_request=request,
        paradigm_result=result,
        **matrix_analysis(axes, states, selected, subset_budget, binary_dir),
    )


def explore_chronology(request, constraints=None, binary_dir=BIN):
    required = {
        "schema_version",
        "id",
        "description",
        "source_kind",
        "source_ref",
        "inventory",
        "blocks",
        "constraints",
        "probes",
    }
    if set(request) != required:
        raise ValueError("Unknown or missing chronology fields")
    if not request["probes"] or len(request["probes"]) > 16:
        raise ValueError("Provide 1–16 explicit chronology probes")
    if (
        len(request["blocks"]) > 6
        or sum(len(b["rules"]) for b in request["blocks"]) > 64
    ):
        raise ValueError("At most six chronology blocks and 64 rule passes")
    if any(set(b) != {"id", "label", "rules", "source_ref"} for b in request["blocks"]):
        raise ValueError("Unknown or missing chronology block fields")
    if any(
        set(p) != {"id", "input", "expected", "source_ref"} for p in request["probes"]
    ):
        raise ValueError("Unknown or missing chronology probe fields")
    if not all(
        isinstance(request[k], str) and request[k]
        for k in ["description", "source_kind", "source_ref"]
    ):
        raise ValueError(
            "Chronology description and source attribution must be nonempty strings"
        )
    if len({p["id"] for p in request["probes"]}) != len(request["probes"]):
        raise ValueError("Repeated chronology probe ID")
    if not all(
        isinstance(p[k], str) and p[k]
        for p in request["probes"]
        for k in ["id", "source_ref"]
    ):
        raise ValueError("Every chronology probe needs an ID and source reference")
    if not all(
        isinstance(b[k], str) and b[k]
        for b in request["blocks"]
        for k in ["label", "source_ref"]
    ):
        raise ValueError("Every chronology block needs a label and source reference")
    order_request = dict(
        schema_version=request["schema_version"],
        id=request["id"],
        rule_ids=[b["id"] for b in request["blocks"]],
        constraints=request["constraints"] if constraints is None else constraints,
    )
    orders = checked("chronology", order_request, binary_dir)
    blocks = {b["id"]: b for b in request["blocks"]}
    packages, jobs = [], []
    # Validate even unused/cyclic blocks through a package: cycles must not hide malformed rules.
    validation_orders = orders["orders"] or [list(blocks)]
    for i, order in enumerate(validation_orders):
        pid = f"chronology-{i}"
        laws = []
        for block in order:
            for ri, rule in enumerate(blocks[block]["rules"]):
                start = "published-root" if not laws else f"{pid}-stage-{len(laws)}"
                laws.append(
                    dict(
                        id=f"{block}-pass-{ri}",
                        input_stage=start,
                        output_stage=f"{pid}-stage-{len(laws)+1}",
                        rule=rule,
                    )
                )
        packages.append(
            dict(
                id=pid,
                version="1.0.0",
                description="Declared order of fixed rule blocks",
                inventory=request["inventory"],
                initial_stage="published-root",
                final_stage=laws[-1]["output_stage"] if laws else "published-root",
                laws=laws,
            )
        )
        for j, p in enumerate(request["probes"]):
            jobs.append(
                dict(
                    id=f"order-{i}-probe-{j}",
                    package_id=pid,
                    input=p["input"],
                    expected=p["expected"],
                )
            )
    batch = dict(
        schema_version="1.0.0",
        id="chronology-derivations",
        packages=packages,
        forward=[],
        inverse=[],
    )
    forwards = checked_forwards(batch, jobs, binary_dir)
    derived = []
    if not orders["cyclic"]:
        for i, order in enumerate(orders["orders"]):
            traces = [
                forwards[f"order-{i}-probe-{j}"] for j in range(len(request["probes"]))
            ]
            derived.append(
                dict(
                    order=order,
                    probes=traces,
                    agrees_with_observations=all(
                        t["exact"] is not False for t in traces
                    ),
                )
            )
    return dict(
        kind="chronology",
        complete=True,
        cyclic=orders["cyclic"],
        orders=derived,
        input_request=deepcopy(request) | {"constraints": order_request["constraints"]},
        order_enumeration=orders,
        scope="All permutations of the declared fixed blocks satisfying precedence constraints",
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("kind", choices=["pool", "bounded", "paradigm", "chronology"])
    p.add_argument("--dataset", default="tibetan-merger")
    p.add_argument("--case", default="merged-affricate-pool")
    p.add_argument("--input", type=Path)
    p.add_argument("--hypothesis", action="append", default=[])
    p.add_argument("--observe", action="append", default=None)
    p.add_argument("--subset-budget", type=int, default=4096)
    p.add_argument("--report", type=Path)
    args = p.parse_args()
    try:
        if args.kind == "pool":
            out = analyze_pool(
                args.dataset,
                args.case,
                args.hypothesis,
                selected=args.observe,
                subset_budget=args.subset_budget,
            )
        else:
            if not args.input:
                p.error("--input is required")
            d = strict_read(args.input)
            if args.kind == "chronology":
                out = explore_chronology(d)
            elif args.kind == "paradigm":
                out = analyze_paradigm(
                    d, args.hypothesis, args.observe, args.subset_budget
                )
            else:
                out = analyze_bounded(
                    d,
                    args.hypothesis,
                    selected=args.observe,
                    subset_budget=args.subset_budget,
                )
        code = 0 if out["complete"] else 3
    except IncompleteSearch as e:
        out, code = dict(complete=False, error=str(e), status="incomplete"), 3
    except (ValueError, KeyError, TypeError, OSError) as e:
        out, code = dict(complete=False, error=str(e), status="error"), 2
    if args.report:
        args.report.write_bytes(encoded(out))
    print(encoded(out).decode(), end="")
    return code


if __name__ == "__main__":
    sys.exit(main())
