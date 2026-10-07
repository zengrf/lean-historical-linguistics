"""Independent finite-set and paradigm calculations; never invokes Lean."""

from collections import defaultdict
from itertools import combinations, permutations

from reference_rules import run


def analyze_matrix(r):
    selected = r["selected"]
    rows = r["histories"]

    def fits(row, axes):
        return all(row["agreements"][i] for i in axes)

    def satisfiable(axes):
        return any(fits(row, axes) for row in rows)

    survivors = [row for row in rows if fits(row, selected)]
    subsets = [
        list(c)
        for size in range(len(selected) + 1)
        for c in combinations(selected, size)
    ]
    position = {v: i for i, v in enumerate(selected)}
    subsets.sort(key=lambda xs: sum(2 ** (len(selected) - 1 - position[i]) for i in xs))
    examined = subsets[: r["subset_budget"]] if not survivors else []
    cores = [
        xs
        for xs in examined
        if not satisfiable(xs)
        and all(satisfiable([j for j in xs if j != i]) for i in xs)
    ]

    def groups(axes):
        grouped = defaultdict(list)
        for h in survivors:
            grouped[tuple(h["predictions"][i] for i in axes)].append(h["id"])
        return [
            dict(prediction=list(key), histories=ids) for key, ids in grouped.items()
        ]

    probes = []
    for i in range(len(r["axes"])):
        if i in selected:
            continue
        pairs = sum(
            a["predictions"][i] != b["predictions"][i]
            for a, b in combinations(survivors, 2)
        )
        probes.append(
            dict(
                axis=i,
                partitions=groups([i]),
                distinguished_pairs=pairs,
                discriminating=bool(pairs),
            )
        )
    complete = bool(survivors) or len(subsets) <= r["subset_budget"]
    return dict(
        input_valid=True,
        id=r["id"],
        complete=complete,
        conflicts_complete=complete,
        subsets_examined=len(examined),
        subset_space=len(subsets),
        minimal_conflicts=cores,
        survivors=[h["id"] for h in survivors],
        equivalence_classes=groups(selected),
        probes=probes,
    )


def chronology(r):
    orders = [
        list(order)
        for order in permutations(r["rule_ids"])
        if all(
            order.index(e["earlier"]) < order.index(e["later"])
            for e in r["constraints"]
        )
    ]
    return dict(
        input_valid=True, complete=True, id=r["id"], cyclic=not orders, orders=orders
    )


def realize(cell, root):
    base = next(
        (a["output"] for a in cell["allomorphs"] if a["input"] == root["segments"]),
        root["segments"],
    )
    stem_steps, stem = run([l["rule"] for l in cell["stem"]["laws"]], base)
    affixed = cell["prefix"] + stem + cell["suffix"]
    sound_steps, surface = run([l["rule"] for l in cell["sound"]["laws"]], affixed)
    tone = root["tone"]
    tones = []
    for rule in cell["tone_rules"]:
        word = [
            s for s in (stem if rule["conditioning"] == "stem" else surface) if s != "+"
        ]
        applies = (
            tone == rule["from_tone"]
            and (
                not rule["initial_class"]
                or bool(word and word[0] in rule["initial_class"])
            )
            and (
                not rule["final_class"]
                or bool(word and word[-1] in rule["final_class"])
            )
        )
        after = rule["to_tone"] if applies else tone
        tones.append(
            dict(
                rule_id=rule["id"],
                input=tone,
                output=after,
                applied=applies,
                conditioning=rule["conditioning"],
            )
        )
        tone = after

    def trace(package, outputs):
        return [
            dict(
                rule_id=l["id"],
                input_stage=l["input_stage"],
                output_stage=l["output_stage"],
                output=w,
            )
            for l, w in zip(package["laws"], outputs)
        ]

    return dict(
        cell_id=cell["id"],
        source_ref=cell["source_ref"],
        input=root,
        allomorph_input=base,
        stem_steps=trace(cell["stem"], stem_steps),
        stem_output=stem,
        prefix=cell["prefix"],
        suffix=cell["suffix"],
        affixed=affixed,
        sound_steps=trace(cell["sound"], sound_steps),
        tone_steps=tones,
        output=dict(segments=surface, tone=tone),
        certificate_accepted=True,
    )


def agrees(output, expected):
    return expected is None or (
        output["segments"] == expected["segments"]
        and (expected["tone"] is None or expected["tone"] == output["tone"])
    )


def paradigm(r):
    histories = []
    for a in r["analyses"]:
        for root in r["pool"]:
            cells = [realize(c, root) for c in a["cells"]]
            accepted = all(
                agrees(out["output"], c["expected"])
                for c, out in zip(a["cells"], cells)
            )
            histories.append(
                dict(analysis_id=a["id"], input=root, accepted=accepted, cells=cells)
            )
    return dict(
        input_valid=True,
        complete=True,
        id=r["id"],
        scope="declared-joint-paradigm-pool",
        examined=len(histories),
        histories=histories,
    )
