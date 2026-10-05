"""Independent test oracle using stable input positions and mutable output slots.

Unlike Lean's recursive prefix scan and mirrored RTL implementation, this
oracle visits original indices directly in either direction. It is unverified
test infrastructure and is never part of certificate acceptance.
"""


def side_matches(tests, edge, tokens):
    if len(tokens) < len(tests):
        return False
    for test, token in zip(tests, tokens):
        if test == "+":
            match = token == "+"
        elif test == "*":
            match = token != "+"
        else:
            match = token != "+" and token in test
        if not match:
            return False
    return not edge or len(tokens) == len(tests)


def apply_rule(rule, word):
    slots = [[token] for token in word]
    order = range(len(word))
    if rule["direction"] == "right-to-left":
        order = reversed(order)
    for i in order:
        if word[i] == "+" or word[i] not in rule["target"]:
            continue
        if rule["mode"] == "simultaneous":
            left, right = word[:i], word[i + 1:]
        else:
            left = [x for slot in slots[:i] for x in slot]
            right = [x for slot in slots[i + 1:] for x in slot]
        if side_matches(rule["left"], rule["left_edge"], left[::-1]) and \
                side_matches(rule["right"], rule["right_edge"], right):
            replacement = rule["replacement"]
            slots[i] = [] if replacement is None else [replacement]
    return [x for slot in slots for x in slot]


def run(rules, word):
    steps = []
    for rule in rules:
        word = apply_rule(rule, word)
        steps.append(word)
    return steps, word
