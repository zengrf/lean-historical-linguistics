"""Untrusted inverse-language solver. Its complete graphs require Lean checking.

No protoform pool or reference reconstruction is read. Compiled models reuse
residual states across words; contextual models use the reference interpreter.
"""

from dataclasses import dataclass
from itertools import product
import time

from reference_rules import run


class IncompleteSearch(RuntimeError):
    pass


def compiled(branches):
    return all(
        not any((r["left"], r["right"], r["left_edge"], r["right_edge"]))
        and r["direction"] == "left-to-right"
        for b in branches
        for law in b["package"]["laws"]
        for r in [law["rule"]]
    )


def output(branch, word):
    return run([law["rule"] for law in branch["package"]["laws"]], list(word))[1]


def approximate(branch, alphabet):
    """Context-free superset only for rejecting impossible input prefixes.

    Lean proves its inclusion of every actual contextual derivation. Terminal
    nodes still use the complete original rules, including direction and mode.
    """
    table = {}
    for atom in alphabet:
        images = {(atom,)}
        for law in branch["package"]["laws"]:
            r = law["rule"]
            exact = (
                not any((r["left"], r["right"], r["left_edge"], r["right_edge"]))
                and r["direction"] == "left-to-right"
            )
            following = set()
            for word in images:
                if exact:
                    following.add(tuple(run([r], list(word))[1]))
                else:
                    following.add(word)
                    if word and word[0] != "+" and word[0] in r["target"]:
                        following.add(
                            () if r["replacement"] is None else (r["replacement"],)
                        )
            images = following
        table[atom] = images
    return table


def matches(mask, word):
    return mask is None or (
        len(mask) == len(word)
        and all((x is None and y != "+") or x == y for x, y in zip(mask, word))
    )


def shape_accept(shapes, word):
    return shapes is None or any(
        len(p) == len(word) and all(a in slot for slot, a in zip(p, word))
        for p in shapes
    )


def freeze_shapes(shapes):
    return (
        None
        if shapes is None
        else tuple(tuple(tuple(slot) for slot in p) for p in shapes)
    )


def masks_for(spec, entry):
    return tuple(
        None if r["form"] is None else tuple(r["form"]) for r in entry["reflexes"]
    )


def native_mask(mask):
    if mask is None:
        return None
    return [
        (
            dict(kind="unknown", value="m7-unknown")
            if x is None
            else (
                dict(kind="boundary", value="+")
                if x == "+"
                else dict(kind="segment", value=x)
            )
        )
        for x in mask
    ]


@dataclass(frozen=True)
class Residual:
    remaining: int
    minimum: int
    masks: tuple
    shapes: tuple | None

    def json(self):
        return dict(
            remaining=self.remaining,
            minimum=self.minimum,
            masks=[native_mask(m) for m in self.masks],
            shapes=self.shapes,
        )


@dataclass(frozen=True)
class Prefix:
    remaining: int
    front: tuple

    def json(self):
        return dict(remaining=self.remaining, front=self.front)


def consume(mask, emitted):
    if mask is None:
        return True, None
    if len(mask) < len(emitted) or not matches(mask[: len(emitted)], emitted):
        return False, None
    return True, mask[len(emitted) :]


def shape_step(shapes, atom):
    if shapes is None:
        return None
    return tuple(p[1:] for p in shapes if p and atom in p[0])


def decimal(value):
    """Serialize arbitrary solution counts without changing Python's global limit."""
    if value < 10**4000:
        return str(value)
    chunks = []
    while value:
        value, remainder = divmod(value, 10**4000)
        chunks.append(str(remainder))
    return chunks[-1] + "".join(x.zfill(4000) for x in reversed(chunks[:-1]))


def integer(text):
    if (
        not isinstance(text, str)
        or not text
        or not text.isascii()
        or not text.isdigit()
    ):
        raise ValueError("A nonnegative decimal integer is required")
    result = 0
    for start in range(0, len(text), 4000):
        chunk = text[start : start + 4000]
        result = result * 10 ** len(chunk) + int(chunk)
    return result


class Builder:
    def __init__(self, spec, model, deadline, node_budget, force_reference=False):
        self.spec, self.model = spec, model
        self.deadline, self.budget = deadline, node_budget
        self.alphabet = tuple(spec["proto_inventory"])
        self.fast = compiled(model["branches"]) and not force_reference
        self.pruned = not self.fast and not force_reference
        self.approximations = (
            [approximate(b, self.alphabet) for b in model["branches"]]
            if self.pruned
            else []
        )
        self.tables = (
            [
                {a: tuple(output(b, [a])) for a in self.alphabet}
                for b in model["branches"]
            ]
            if self.fast
            else []
        )
        self.nodes, self.counts, self.known = [], [], {}
        self.masks = None

    def viable(self, front):
        for table, mask in zip(self.approximations, self.masks):
            states = {mask}
            for atom in front:
                states = {
                    rest
                    for m in states
                    for emitted in table[atom]
                    for ok, rest in [consume(m, emitted)]
                    if ok
                }
                if not states:
                    return False
        return True

    def check_budget(self):
        if time.monotonic() > self.deadline:
            raise IncompleteSearch(
                "Search time budget exhausted; completeness is not established"
            )
        if len(self.nodes) >= self.budget:
            raise IncompleteSearch(
                "Search graph node budget exhausted; completeness is not established"
            )

    def visit(self, state):
        if state in self.known:
            return self.known[state]
        self.check_budget()
        if self.fast:
            accepting = (
                state.minimum == 0
                and all(m is None or not m for m in state.masks)
                and (state.shapes is None or () in state.shapes)
            )
        else:
            accepting = (
                self.spec["min_length"] <= len(state.front)
                and shape_accept(self.spec["phonotactics"], state.front)
                and all(
                    matches(m, output(b, state.front))
                    for m, b in zip(self.masks, self.model["branches"])
                )
            )
        edges = []
        if state.remaining:
            for atom in self.alphabet:
                if self.fast:
                    residuals = [
                        consume(m, t[atom]) for m, t in zip(state.masks, self.tables)
                    ]
                    if not all(ok for ok, _ in residuals):
                        continue
                    child = Residual(
                        state.remaining - 1,
                        max(0, state.minimum - 1),
                        tuple(m for _, m in residuals),
                        shape_step(state.shapes, atom),
                    )
                else:
                    child = Prefix(state.remaining - 1, state.front + (atom,))
                    if self.pruned and not self.viable(child.front):
                        continue
                edges.append([atom, self.visit(child)])
        self.check_budget()
        index = len(self.nodes)
        self.known[state] = index
        self.nodes.append(dict(state=state.json(), accepting=accepting, edges=edges))
        self.counts.append(int(accepting) + sum(self.counts[j] for _, j in edges))
        return index

    def entry(self, entry):
        masks = masks_for(self.spec, entry)
        if self.fast:
            state = Residual(
                self.spec["max_length"],
                self.spec["min_length"],
                masks,
                freeze_shapes(self.spec["phonotactics"]),
            )
        else:
            # Prefix states for different observation tuples describe different
            # machines and must not share graph nodes.
            self.known = {}
            self.masks = masks
            state = Prefix(self.spec["max_length"], ())
        before = len(self.nodes)
        root = self.visit(state)
        return dict(
            entry_id=entry["id"],
            root=root,
            count=decimal(self.counts[root]),
            new_nodes=len(self.nodes) - before,
        )


def solve(spec, *, node_budget=250_000, time_limit=60, force_reference=False):
    deadline = time.monotonic() + time_limit
    models = []
    remaining = node_budget
    for model in spec["analyses"]:
        builder = Builder(spec, model, deadline, remaining, force_reference)
        if builder.fast:
            roots = [builder.entry(entry) for entry in spec["entries"]]
            graphs = [dict(nodes=builder.nodes)]
            bindings = [
                dict(entry_id=r["entry_id"], graph=0, root=r["root"]) for r in roots
            ]
            counts = [r["count"] for r in roots]
        else:
            # A checked reference trie per distinct observed row.
            graphs, bindings, counts, reused = [], [], [], {}
            for entry in spec["entries"]:
                key = masks_for(spec, entry)
                if key not in reused:
                    one = Builder(spec, model, deadline, remaining, force_reference)
                    r = one.entry(entry)
                    remaining -= len(one.nodes)
                    reused[key] = (len(graphs), r["root"], r["count"])
                    graphs.append(dict(nodes=one.nodes))
                gi, root, count = reused[key]
                bindings.append(dict(entry_id=entry["id"], graph=gi, root=root))
                counts.append(count)
        if builder.fast:
            remaining -= len(builder.nodes)
        total = 1
        for count in counts:
            total *= integer(count)
        models.append(
            dict(
                analysis_id=model["id"],
                mode=(
                    "compiled"
                    if builder.fast
                    else "pruned" if builder.pruned else "reference"
                ),
                graphs=graphs,
                bindings=bindings,
            )
        )
    return dict(request=spec, models=models)


def graph_counts(nodes):
    result = []
    for node in nodes:
        result.append(int(node["accepting"]) + sum(result[j] for _, j in node["edges"]))
    return result


def unrank(nodes, counts, root, rank):
    if not 0 <= rank < counts[root]:
        raise ValueError("Candidate index lies outside the complete inverse set")
    word, current = [], root
    while True:
        node = nodes[current]
        if node["accepting"]:
            if rank == 0:
                return word
            rank -= 1
        for atom, child in node["edges"]:
            if rank < counts[child]:
                word.append(atom)
                current = child
                break
            rank -= counts[child]
        else:
            raise ValueError("Malformed counted graph")


def baseline(spec, model):
    """Exhaustive independent word generation for small verification domains."""
    out = {e["id"]: [] for e in spec["entries"]}
    for length in range(spec["min_length"], spec["max_length"] + 1):
        for word in product(spec["proto_inventory"], repeat=length):
            if not shape_accept(spec["phonotactics"], word):
                continue
            predictions = [output(b, word) for b in model["branches"]]
            for e in spec["entries"]:
                if all(matches(m, w) for m, w in zip(masks_for(spec, e), predictions)):
                    out[e["id"]].append(list(word))
    return out
