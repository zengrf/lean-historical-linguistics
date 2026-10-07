"""A small, explicit sound-change notation for the existing M2 rule language.

No regular expression or executable expression from a project is evaluated.
Unsupported processes raise an explanation; they are never approximated.
"""

from copy import deepcopy
import re


def parse_classes(text):
    result = {}
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        if "=" not in line:
            raise ValueError(f"Class line {number}: use V = a e i o u")
        name, values = (part.strip() for part in line.split("=", 1))
        symbols = values.split()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name) or name in result:
            raise ValueError(f"Class line {number}: use a distinct class name")
        if (
            not symbols
            or len(symbols) != len(set(symbols))
            or any(s in {"#", "_", "∅", "+", "?"} for s in symbols)
        ):
            raise ValueError(f"Class {name}: provide distinct segment symbols")
        result[name] = symbols
    return result


def units(text):
    values = re.findall(r"\[[^\[\]]+\]|[^\s\[\]]+", text)
    if re.sub(r"\s+", "", "".join(values)) != re.sub(r"\s+", "", text):
        raise ValueError("Unbalanced segment class; use [p t k]")
    return values


def segment_class(text, classes):
    if text in classes:
        return list(classes[text])
    if text.startswith("[") and text.endswith("]"):
        values = text[1:-1].split()
    else:
        values = [text]
    if (
        not values
        or len(values) != len(set(values))
        or any(
            v in {"", "#", "_", "∅", "+", "?", ">", "/"} or any(c.isspace() for c in v)
            for v in values
        )
    ):
        raise ValueError("Expected an atomic segment or a class such as [p t k]")
    return values


def context(text, classes, *, left):
    values = units(text)
    anchor = False
    if "#" in values:
        if values.count("#") != 1 or values[0 if left else -1] != "#":
            raise ValueError("# is a word boundary: use # V _ or _ V #")
        anchor = True
        values = values[1:] if left else values[:-1]
    if len(values) > 2:
        raise ValueError(
            "This rule language supports at most two context positions on each side"
        )
    tests = []
    for value in values:
        tests.append(
            "+"
            if value == "+"
            else "*" if value == "." else segment_class(value, classes)
        )
    return list(reversed(tests)) if left else tests, anchor


def parse_rule(text, classes=None, *, direction="left-to-right", mode="simultaneous"):
    classes = classes or {}
    if direction not in {"left-to-right", "right-to-left"} or mode not in {
        "simultaneous",
        "feeding",
    }:
        raise ValueError("Unknown application direction or pass convention")
    text, *flags = [part.strip() for part in text.split(";")]
    if (
        len(flags) != len(set(flags))
        or any(flag not in {"ltr", "rtl", "feeding", "simultaneous"} for flag in flags)
        or {"ltr", "rtl"} <= set(flags)
        or {"feeding", "simultaneous"} <= set(flags)
    ):
        raise ValueError(
            "Rule flags may specify one direction (ltr or rtl) and one convention (feeding or simultaneous)"
        )
    if "rtl" in flags:
        direction = "right-to-left"
    if "ltr" in flags:
        direction = "left-to-right"
    if "feeding" in flags:
        mode = "feeding"
    if "simultaneous" in flags:
        mode = "simultaneous"
    text = text.strip().replace("→", ">").replace("⇒", ">")
    if text.count(">") != 1 or text.count("/") > 1:
        raise ValueError("Use p > b / V _ V, or h > ∅ for deletion")
    change, *environment = text.split("/")
    target, replacement = (value.strip() for value in change.split(">"))
    if target in {"∅", "0", ""}:
        raise ValueError("Insertion is not supported by the checked M2 rule language")
    if len(units(target)) != 1:
        raise ValueError(
            "Use [p t k] for alternative targets; multi-segment replacement and metathesis are not supported"
        )
    target = segment_class(target, classes)
    if replacement in {"∅", "0"}:
        replacement = None
    elif (
        len(replacement.split()) != 1
        or replacement in classes
        or replacement.startswith("[")
        or replacement in {"#", "+", ".", "?", "_"}
    ):
        raise ValueError("The replacement must be one atomic segment or ∅")
    left, right, left_edge, right_edge = [], [], False, False
    if environment:
        if environment[0].count("_") != 1:
            raise ValueError("The environment needs one underscore, as in V _ V")
        lhs, rhs = environment[0].split("_")
        left, left_edge = context(lhs, classes, left=True)
        right, right_edge = context(rhs, classes, left=False)
    return dict(
        target=target,
        replacement=replacement,
        left=left,
        right=right,
        left_edge=left_edge,
        right_edge=right_edge,
        direction=direction,
        mode=mode,
    )


def class_text(values):
    return values[0] if len(values) == 1 else "[" + " ".join(values) + "]"


def format_rule(rule):
    def side(tests):
        return " ".join(
            "." if t == "*" else "+" if t == "+" else class_text(t) for t in tests
        )

    text = class_text(rule["target"]) + " > " + (rule["replacement"] or "∅")
    if rule["left"] or rule["right"] or rule["left_edge"] or rule["right_edge"]:
        lhs = ("# " if rule["left_edge"] else "") + side(list(reversed(rule["left"])))
        rhs = side(rule["right"]) + (" #" if rule["right_edge"] else "")
        text += " / " + lhs.strip() + " _ " + rhs.strip()
    text = text.strip()
    if rule["direction"] == "right-to-left":
        text += "; rtl"
    if rule["mode"] == "feeding":
        text += "; feeding"
    return text


def compile_branch(
    package,
    text,
    classes,
    proto_inventory,
    *,
    direction="left-to-right",
    mode="simultaneous",
):
    result = deepcopy(package)
    laws, symbols = [], set(proto_inventory)
    stage = result["initial_stage"]
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("//"):
            continue
        try:
            rule = parse_rule(line, classes, direction=direction, mode=mode)
        except ValueError as error:
            raise ValueError(f"Rule line {number}: {error}") from error
        symbols.update(rule["target"])
        if rule["replacement"] is not None:
            symbols.add(rule["replacement"])
        for test in rule["left"] + rule["right"]:
            if isinstance(test, list):
                symbols.update(test)
        output_stage = f"{result['id']}-stage-{len(laws) + 1}"
        laws.append(
            dict(
                id=f"{result['id']}-law-{len(laws)}",
                input_stage=stage,
                output_stage=output_stage,
                rule=rule,
            )
        )
        stage = output_stage
    if len(laws) > 128 or len(symbols) > 256:
        raise ValueError("A branch supports at most 128 rules and 256 segment symbols")
    result.update(laws=laws, final_stage=stage, inventory=sorted(symbols))
    return result


def parse_shapes(text, classes):
    if not text.strip():
        return None
    shapes = []
    for alternative in text.replace("\n", "|").split("|"):
        alternative = alternative.strip()
        if not alternative:
            raise ValueError("Empty word-shape alternative; use ∅ explicitly")
        shapes.append(
            []
            if alternative == "∅"
            else [segment_class(value, classes) for value in units(alternative)]
        )
    if len(shapes) > 256 or any(len(shape) > 64 for shape in shapes):
        raise ValueError("At most 256 word shapes with 64 slots each are supported")
    return shapes


def segmentations(value, inventory, limit=16):
    """Inventory-based proposals; return ambiguity rather than silently choose."""
    if len(value) > 1024 or len(inventory) > 256:
        raise ValueError("Segmentation input exceeds the editor limit")
    memo = {len(value): [[]]}
    for start in range(len(value) - 1, -1, -1):
        ways = []
        for atom in inventory:
            if atom and value.startswith(atom, start):
                for rest in memo[start + len(atom)]:
                    ways.append([atom] + rest)
                    if len(ways) >= limit + 1:
                        break
            if len(ways) >= limit + 1:
                break
        memo[start] = ways
    found = memo[0]
    return dict(
        options=found[:limit], truncated=len(found) > limit, unique=len(found) == 1
    )
