"""Evaluate supplied reference forms after reconstruction, never during search."""

from collections import Counter
from lexicon import native


def evaluate(request, annotations, summary):
    references = annotations.get("_references", {})
    splits = annotations.get("_splits", {})
    entries = {row["id"] for row in request["entries"]}
    rows, totals = [], {}
    for model in request["analyses"]:
        selected = [(key, word) for key, word in references.items() if key in entries]
        accepted = {}
        for start in range(0, len(selected), 1000):
            proposals = [
                dict(analysis_id=model["id"], entry_id=key, word=word)
                for key, word in selected[start : start + 1000]
            ]
            checked = native("--derive", dict(request=request, proposals=proposals))
            accepted.update(
                {p["proposal"]["entry_id"]: p["accepted"] for p in checked["proposals"]}
            )
        model_summary = next(
            m for m in summary["models"] if m["analysis_id"] == model["id"]
        )
        counts = {r["entry_id"]: r["count"] for r in model_summary["entries"]}
        for key, word in selected:
            split = splits.get(key, "unassigned")
            outside = (
                any(a not in request["proto_inventory"] for a in word)
                or not request["min_length"] <= len(word) <= request["max_length"]
                or (
                    request["phonotactics"] is not None
                    and not any(
                        len(shape) == len(word)
                        and all(a in slot for a, slot in zip(word, shape))
                        for shape in request["phonotactics"]
                    )
                )
            )
            row = dict(
                analysis_id=model["id"],
                entry_id=key,
                partition=split,
                reference=word,
                reference_in_scope=not outside,
                reference_recovered=accepted[key],
                unique_reference=accepted[key] and counts[key] == "1",
                candidate_count=counts[key],
            )
            rows.append(row)
            bucket = totals.setdefault((model["id"], split), Counter())
            bucket.update(
                references=1,
                in_scope=int(not outside),
                recovered=int(accepted[key]),
                unique_reference=int(row["unique_reference"]),
            )
    return dict(
        protocol="Reference forms are evaluated after search; they are not search inputs. Partitions are researcher declarations, not proof of an uncontaminated held-out experiment.",
        rows=rows,
        totals=[
            dict(analysis_id=model, partition=split, **counts)
            for (model, split), counts in totals.items()
        ],
    )
