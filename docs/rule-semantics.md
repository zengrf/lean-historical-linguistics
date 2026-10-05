# Contextual rule semantics, version 1.0.0

This is the M2 contract for synthetic contextual sound-law packages. It defines
an executable, deterministic fragment. It makes no claim that a package is a
historically justified PIE or Sino-Tibetan analysis.

## Alphabet and grammar

A word is a list of atomic segment strings and explicit morpheme boundaries,
written `"+"`. Word edges are implicit at the ends of the list. Segment strings
may contain several Unicode code points: the interpreter never splits or
normalizes them. An explicit finite inventory declares all permitted segments;
`"+"`, `"#"`, `"*"`, empty strings and whitespace/control characters are reserved
or forbidden. Tone, stress and accent have no implicit interpretation: encode
them as declared atomic segments or within segment symbols at the named stage.

Each rule contains:

```text
target       nonempty finite list of segment symbols
replacement  one segment symbol, or null for deletion
left, right  lists of at most two context tests per side
left_edge, right_edge  Boolean word-edge anchors
direction    "left-to-right" | "right-to-left"
mode         "simultaneous" | "feeding"
context test nonempty array of segments | "*" | "+"
```

`"*"` matches one segment, never a boundary. An array matches membership in the
declared class. `"+"` matches a morpheme boundary. Both context lists are written
**nearest to the target first**. Tests consume adjacent tokens; they do not skip
boundaries. After all tests on a side have matched, an edge anchor requires that
no tokens remain on that side. With no anchor, further tokens are unconstrained.
Thus `left=[["a"],["p"]], right=[], right_edge=true` describes `p a _ #`.
An empty unanchored context imposes no condition. A boundary can be inspected
explicitly, but cannot be a target, replacement, or implicit wildcard match.

A target occurrence matches exactly when the token belongs to `target` and
both contexts and anchors hold. Every matching occurrence is replaced or
deleted. Every nonmatching token and every morpheme boundary is copied.

## One pass

Every original input token is visited exactly once, in the declared direction.
Produced tokens are not revisited. A deletion still consumes its original input
token. There is no insertion, iteration to a fixed point, optional application,
word identifier, lexical exception, arbitrary callback, regular expression, or
whole-word replacement operation.

For a **simultaneous** pass, both contexts are read from the original input.
Output is accumulated separately, so earlier replacements and deletions cannot
feed or bleed later matches in that same pass.

For a **feeding** pass, the context on the already visited side is read from the
output produced so far; the unvisited side is read from the remaining original
input. A replacement can feed or bleed a later match. Deletion can expose an
earlier output segment or word edge. The currently visited token is always an
original input token, and replacement material is never scanned again.

Right-to-left scanning has the symmetric meaning: the already visited side is
the right side. Formally it reverses the word, swaps the rule's left/right tests
and anchors, performs the same structural scan, and reverses the output. Context
test lists are already nearest-first and are not themselves reversed.

The interpreter terminates by recursion on the remaining original input, even
for deletions and feeding rules. Output length never exceeds input length.

## Ordered packages and certificates

A package has a stable ID, explicit version, description, finite inventory,
initial/final stage IDs, and a list of named laws. Each law has a unique ID,
input/output stage IDs and one rule. Stages form a continuous chronological
chain with distinct stage names. A package with no laws is the identity and
has the same initial and final stage. Each complete pass feeds the next law in
the package's list order, regardless of the individual pass's mode.

A certificate identifies the package ID/version, input word, final output, and
one step per law. Each step repeats the law ID, input/output stage IDs and
post-rule word. Missing, extra, reordered, mislabeled or incorrect steps are
rejected, including omission of a pass that changes nothing. A certificate
cannot supply its own alternate grammar or rule order.

The inductive scan relation licenses copying, substitution and deletion under
the above local tests. The pass relation accounts for direction; the cascade
relation composes complete passes. The certificate theorem must connect the
Boolean checker with the inductive relation for the **entire supplied trace**,
not merely assert that some derivation reaches the same final word.

The JSON interface validates inventories, context bounds, rule and stage IDs,
chronology, exact package identity, and all certificate tokens before checking
the trace. Unknown or duplicate JSON fields and unsupported operations are
rejected. Parsing and these packaging validations are executable checks, not a
claim of a verified byte-level parser.

## Regularity and empirical limits

The grammar enforces uniform local application to every matching segment. It
has no lexicon lookup or unchecked whole-word substitution, and the executable
rejects contexts longer than two tokens per side. These restrictions prevent an
arbitrary input/output table from being accepted as a rule operation. They do
not prove that an inventory contains genuine linguistic segments, that chosen
classes are natural classes, or that a short context was not overfit. Those
claims need independent linguistic review and held-out evidence in M5/M6.

The original M0 `Comparative.Rule` accepts any total function for abstract
theorems. M2's accepted packages use only this restricted grammar and do not
deserialize or execute that unrestricted function type. Future insertions,
metathesis, morphology and nondeterminism require a new explicit semantics.
