# Bounded reconstruction semantics, version 1.0.0

M4 enumerates ancestral words under explicitly supplied, finite joint analyses.
A completed result contains every fitting history in the declared space. Its
completeness is relative to that inventory, length bound, models, observations
and interpretation of uncertainty. It does not establish that the true history
lies in the space, infer unrestricted sound laws, or rank a preferred ancestor.

## Hypothesis space

The query declares an ordered `proto_inventory` of distinct atomic segment
strings and `max_length`. `allow_morphemes` optionally adds M2's `+` boundary
atom. Length counts all atoms, including explicit boundaries. Enumeration covers
lengths zero through the bound; the empty word is included. Leading, trailing
and adjacent morpheme boundaries are filtered out. Unicode strings retain exact
values; no normalization or codepoint-level tokenization occurs.

`analyses` is an explicit list of complete joint alternatives. Each has a unique
ID, a proto-node/stage ID, one named M2 package per declared doculect, a complete
observation tuple, and one binding for every declared choice group. Only listed
tuples are licensed: neither readings, package branches nor bindings are
recombined. A candidate consists of an entire named analysis and a protoform.
Identical protoforms under different analyses remain distinct histories.

The declared `analysis_bound` and `max_rules_per_branch` bound these finite
choices. Each branch is a validated M2 package, uses the analysis's proto node
as its initial stage, and includes the proto inventory. Package identity/version
cannot denote conflicting definitions in one query. The M2 restrictions on rule
grammar, chronological stages, inventories and contexts continue to apply.

The executable profile supports at most 15 proto segment symbols, 16 atoms of
length, 16 joint analyses, eight doculects and 16 rules per branch. These limits
are validation boundaries of this implementation; the general enumeration and
correctness theorems do not assume those constants. At least two distinct
doculects and one analysis are required. An empty proto inventory is permitted
and still contains the empty word (plus well-formed boundary words if enabled).

## Observations and the M3 bridge

An observation is an original, unaligned sequence of M1 cells or a null row.
Null means unavailable evidence and constrains no output; `[]` requires an empty
output. Known segments and `+` boundaries must match exactly. An explicit unknown
reading occupies **exactly one segment** position; it does not match a boundary,
zero tokens or several tokens. This is an explicit M4 mask policy. Uncertain
lengths or correlated readings must be represented as separate joint analyses.
Gap/missing cells inside present forms are rejected. Unknown spellings and source
references are retained, not interpreted as observed segment identities.

Every analysis can optionally attach an M3 correspondence dossier and target
alignment ID. The entire dossier must pass M3 and the selected alignment must
exist. Observation doculects, source references and original forms must exactly
match that alignment's rows. M3's preservation theorem then connects these
originals to the aligned rows after removing gaps. The bridge does not invent
proto-segment identities from a correspondence group or validate cognacy.
Directly supplied observations remain explicitly sourced input assumptions.

For a history to fit, every branch observation must be matched by the output of
that history's M2 cascade. The formal relation uses M2's inductive `Derives`
relation, not an unproved external predictor. Each returned history serializes
its analysis ID, proto node, complete choice bindings, protoform, branch outputs
and all intermediate M2 certificate steps. Acceptance is Boolean feasibility;
there are no scores, thresholds, tie-breaking or automatic merging of histories.

## Ambiguity and stronger evidence

Histories are observationally equivalent on a selected doculect axis when their
predicted outputs agree there, even if their protoforms or models differ. They
fit exactly the same observations on that axis. This is observational
indistinguishability relative to the declared models, not historical identity.

Adding observations can only remove candidates when the model, word space and
interpretation of cells are held fixed. Changing the inventory, bounds, model
choices or linked alternatives is a different comparison. Partial results under
a resource limit are not subject to a completed-result monotonicity claim.

## Completion and resource limits

The executable distinguishes `complete`, `incomplete` and `invalid` results.
Only a complete empty result asserts `no_candidate_in_scope: true`. This means
no fitting history in the declared finite space; it never means that no ancestor
exists outside those bounds.

Before enumeration, the raw sequence-count upper bound is computed. A space
exceeding 20,000 raw hypotheses returns `incomplete` with reason `space-limit`
without allocating it. Within that ceiling, `candidate_budget` limits the
number of hypotheses examined. An optional `time_limit_ms` is a cooperative
deadline checked between candidate evaluations; zero yields an immediate
incomplete result. A running cascade or JSON I/O is not interrupted mid-step,
so this is not a hard wall-clock guarantee. Budget/deadline exhaustion always
preserves `complete: false`, even when no candidate has been found.

Partial candidates are sound and refer to an examined prefix of the fixed
enumeration. Relative completeness is claimed only after the entire space is
examined. The CLI reports examined count, scope size when enumerated, raw upper
bound, completion reason and all retained candidates. An external process kill
or I/O failure is an operational failure, never a completed empty search.

## Trust boundaries

Strict JSON decoding, validation, the resource-control driver, source references
and serialization are executable infrastructure. Formal theorems cover finite
enumeration, mask matching, the M2 derivation bridge, candidate soundness and
relative completeness, completed prefixes, joint alternatives, monotonicity and
observational equivalence. A separate Python enumerator and interpreter provide
finite cross-checks; they are test infrastructure rather than proof assumptions
or independent specialist review. The M4 delivery suite is synthetic.
