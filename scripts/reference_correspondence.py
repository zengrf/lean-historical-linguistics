"""Python test oracle for the published M3 contract; outside the proof trust base.

Uses position maps, set intersections and occurrence counters rather than the
Lean recursive checkers. No expected answer is obtained by invoking Lean.
This is a second implementation, not an independent human or agent review.
"""
from collections import Counter
import re

MISSING = dict(kind="missing", value=None)
UNAVAILABLE = {"missing", "unknown"}


def good_id(s):
    return isinstance(s, str) and re.fullmatch(r"[a-zA-Z0-9_.:-]+", s) is not None


def good_cell(c):
    kind, value = c["kind"], c["value"]
    if kind == "segment":
        return bool(value) and value not in {"+", "#", "*"} and not any(
            x.isspace() or ord(x) < 32 or 127 <= ord(x) <= 159 for x in value)
    if kind == "boundary":
        return value == "+"
    if kind == "unknown":
        return bool(value)
    return kind in {"gap", "missing"}


def recover(cells):
    return None if cells is None else [c for c in cells if c["kind"] != "gap"]


def column(a, i):
    return [MISSING if r["aligned"] is None or i >= len(r["aligned"]) else r["aligned"][i] for r in a["rows"]]


def alignment_valid(a):
    if a["width"] <= 0 or len(a["rows"]) < 2:
        return False
    for r in a["rows"]:
        if recover(r["aligned"]) != r["original"]:
            return False
        if r["original"] is not None:
            kinds = [c["kind"] for c in r["original"]]
            if any(k in {"gap", "missing"} for k in kinds):
                return False
            if kinds and (kinds[0] == "boundary" or kinds[-1] == "boundary"):
                return False
            if any(kinds[j] == kinds[j + 1] == "boundary" for j in range(len(kinds) - 1)):
                return False
        if r["aligned"] is not None and (len(r["aligned"]) != a["width"] or any(c["kind"] == "missing" for c in r["aligned"])):
            return False
    for i in range(a["width"]):
        cells = column(a, i)
        if all(c["kind"] in {"gap", "missing"} for c in cells):
            return False
        if any(c["kind"] == "boundary" for c in cells) and any(
            c["kind"] not in {"boundary", "gap", "missing"} or (c["kind"] == "boundary" and c["value"] != "+") for c in cells):
            return False
    return True


def data_valid(d):
    axis = d["doculects"]
    if d["schema_version"] != "1.0.0" or not good_id(d["id"]) or not d["description"] or d["source_kind"] not in {"synthetic", "sourced"}:
        return False
    if len(axis) < 2 or len(set(axis)) != len(axis) or not all(map(good_id, axis)):
        return False
    ids = [a["id"] for a in d["alignments"]]
    if not ids or len(set(ids)) != len(ids):
        return False
    for a in d["alignments"]:
        if not good_id(a["id"]) or not good_id(a["evidence_unit"]) or [r["doculect_id"] for r in a["rows"]] != axis:
            return False
        if not all(r["source_ref"] and all(good_cell(c) for c in (r["original"] or []) + (r["aligned"] or [])) for r in a["rows"]):
            return False
        if not alignment_valid(a):
            return False
    return True


def compare(x, y):
    # A position is observed for conflict when it contains a segment, boundary
    # or gap. Only segment/segment equality can witness positive support.
    left = {i: (c["kind"], c["value"]) for i, c in enumerate(x) if c["kind"] not in UNAVAILABLE}
    right = {i: (c["kind"], c["value"]) for i, c in enumerate(y) if c["kind"] not in UNAVAILABLE}
    both = left.keys() & right.keys()
    no_conflict = len(x) == len(y) and all(left[i] == right[i] for i in both)
    shared = sorted(i for i in both if left[i] == right[i] and left[i][0] == "segment")
    return dict(no_conflict=no_conflict, shared_positions=shared, compatible=no_conflict and bool(shared))


def observed(s):
    return any(c["kind"] == "segment" for c in s["cells"])


def members(sites, group):
    return [s for s in sites if s["id"] in group["members"]]


def support(sites, group):
    return {s["evidence_unit"] for s in members(sites, group) if observed(s)}


def group_valid(sites, group):
    ids = [s["id"] for s in sites]; refs = group["members"]
    if len(set(ids)) != len(ids) or not refs or len(set(refs)) != len(refs) or not set(refs) <= set(ids):
        return False
    selected = members(sites, group)
    if not all(observed(s) for s in selected):
        return False
    if any(not compare(s["cells"], t["cells"])["compatible"] for s in selected for t in selected if s["id"] != t["id"]):
        return False
    return group["claimed_support"] == len(support(sites, group)) and group["claimed_support"] > 0


def partition_valid(sites, groups):
    ids = [s["id"] for s in sites]; group_ids = [g["id"] for g in groups]
    counts = Counter(name for g in groups for name in g["members"])
    return bool(sites) and len(set(ids)) == len(ids) and len(set(group_ids)) == len(group_ids) and all(
        group_valid(sites, g) for g in groups) and all(counts[name] == 1 for name in ids)


def registry(d):
    required = {(a["id"], i) for a in d["alignment_data"]["alignments"] for i in range(a["width"])
                if any(c["kind"] == "segment" for c in column(a, i))}
    actual = [(s["alignment_id"], s["column_index"]) for s in d["sites"]]
    sites = []
    for ref in d["sites"]:
        a = next((a for a in d["alignment_data"]["alignments"] if a["id"] == ref["alignment_id"]), None)
        if a is not None and ref["column_index"] < a["width"]:
            sites.append(dict(id=ref["id"], evidence_unit=a["evidence_unit"], cells=column(a, ref["column_index"])))
    site_ids = [s["id"] for s in d["sites"]]; group_ids = [g["id"] for g in d["groups"]]
    valid = d["claim"] == "feasibility-only" and d["support_policy"] == "distinct-evidence-units-v1" and bool(required)
    valid = valid and len(set(site_ids)) == len(site_ids) and all(map(good_id, site_ids))
    valid = valid and len(set(group_ids)) == len(group_ids) and all(map(good_id, group_ids))
    valid = valid and len(set(actual)) == len(actual) and set(actual) == required and len(sites) == len(d["sites"])
    return sites, valid


def evaluate(d):
    sites, registry_ok = registry(d)
    input_ok = data_valid(d["alignment_data"]) and registry_ok
    accepted = input_ok and partition_valid(sites, d["groups"])
    counts = Counter(name for g in d["groups"] for name in g["members"])
    reports = []
    for s in sites:
        assigned = [g for g in d["groups"] if s["id"] in g["members"]]
        pairs = []; units = []; conflicts = set()
        for g in assigned:
            count = support(sites, g)
            units.append(dict(group_id=g["id"], claimed=g["claimed_support"], computed=len(count),
                              evidence_units=sorted(count), group_accepted=group_valid(sites, g)))
            for t in members(sites, g):
                if s["id"] == t["id"]:
                    continue
                pair = compare(s["cells"], t["cells"])
                if not pair["no_conflict"]:
                    conflicts.add(t["id"])
                pairs.append(dict(group_id=g["id"], with_site=t["id"], no_conflict=pair["no_conflict"],
                                  compatible=pair["compatible"], shared_segment_count=len(pair["shared_positions"]),
                                  shared_doculects=[d["alignment_data"]["doculects"][i] for i in pair["shared_positions"] if i < len(d["alignment_data"]["doculects"])]))
        ref = next(r for r in d["sites"] if r["id"] == s["id"])
        reports.append(dict(site_id=s["id"], alignment_id=ref["alignment_id"], column_index=ref["column_index"],
                            evidence_unit=s["evidence_unit"], cells=s["cells"], incomplete=any(c["kind"] in UNAVAILABLE for c in s["cells"]),
                            assigned_groups=[g["id"] for g in assigned], assignment_count=counts[s["id"]], support=units,
                            pairwise_compatible=bool(assigned) and all(p["compatible"] for p in pairs),
                            conflicting_with=sorted(conflicts), pair_checks=pairs,
                            site_accepted=input_ok and counts[s["id"]] == 1 and all(group_valid(sites, g) for g in assigned),
                            document_accepted=accepted))
    return dict(accepted=accepted, alignment_accepted=data_valid(d["alignment_data"]), sites=reports)


def exact_fields(obj, fields):
    return isinstance(obj, dict) and set(obj) == set(fields)


def cell_shape(c):
    if not exact_fields(c, ["kind", "value"]):
        return False
    return ((c["kind"] in {"segment", "boundary", "unknown"} and isinstance(c["value"], str)) or
            (c["kind"] in {"gap", "missing"} and c["value"] is None))


def data_shape(d):
    if not exact_fields(d, ["schema_version", "id", "description", "source_kind", "doculects", "alignments"]):
        return False
    if not all(isinstance(d[k], str) for k in ["schema_version", "id", "description", "source_kind"]):
        return False
    if not isinstance(d["doculects"], list) or not all(isinstance(s, str) for s in d["doculects"]) or not isinstance(d["alignments"], list):
        return False
    for a in d["alignments"]:
        if not exact_fields(a, ["id", "evidence_unit", "width", "rows"]) or not all(isinstance(a[k], str) for k in ["id", "evidence_unit"]):
            return False
        if type(a["width"]) is not int or a["width"] < 0 or not isinstance(a["rows"], list):
            return False
        for r in a["rows"]:
            if not exact_fields(r, ["doculect_id", "source_ref", "original", "aligned"]) or not all(isinstance(r[k], str) for k in ["doculect_id", "source_ref"]):
                return False
            for k in ["original", "aligned"]:
                if r[k] is not None and (not isinstance(r[k], list) or not all(map(cell_shape, r[k]))):
                    return False
    return True


def dossier_shape(d):
    if not exact_fields(d, ["alignment_data", "sites", "groups", "support_policy", "claim"]):
        return False
    if not data_shape(d["alignment_data"]) or not all(isinstance(d[k], str) for k in ["support_policy", "claim"]):
        return False
    if not isinstance(d["sites"], list) or not isinstance(d["groups"], list):
        return False
    for s in d["sites"]:
        if not exact_fields(s, ["id", "alignment_id", "column_index"]) or not all(isinstance(s[k], str) for k in ["id", "alignment_id"]):
            return False
        if type(s["column_index"]) is not int or s["column_index"] < 0:
            return False
    for g in d["groups"]:
        if not exact_fields(g, ["id", "members", "claimed_support"]) or not isinstance(g["id"], str):
            return False
        if not isinstance(g["members"], list) or not all(isinstance(s, str) for s in g["members"]):
            return False
        if type(g["claimed_support"]) is not int or g["claimed_support"] < 0:
            return False
    return True
