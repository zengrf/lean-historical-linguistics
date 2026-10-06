# M4: bounded inverse reconstruction and ambiguity

**M4 is delivered; all four acceptance criteria pass.** The implementation
enumerates a declared finite protoform space, executes named M2 branch models,
returns every fitting joint history, and preserves ambiguity. It can bind
observations to checked M3 alignments. The
[semantics](bounded-reconstruction-semantics.md) specify all bounds, masks and
completion states; [the acceptance report](../reports/exhaustive-small-domain.json)
records the exact inverse sets and source hashes.

| Criterion | Delivered evidence |
| --- | --- |
| M4-enumeration | Exact-length and bounded-length enumeration theorems, cardinality formulas, explicit morpheme shape filter and finite named joint analyses |
| M4-correctness | Soundness and relative completeness through M2's inductive derivation relation; sound partial prefixes and a proved completion condition |
| M4-ambiguity | Equivalence on selected doculects, fixed-model observation monotonicity/refinement, merger ambiguity and joint alternatives with preserved dependencies |
| M4-reference | All 1,936 inverse sets match Python over 121 words and 16 cascades: 234,256 membership decisions; resource limits and timeouts remain incomplete |

All M4 data are **synthetic**. The result establishes mathematical correctness
relative to specified models and bounds. Empirical PIE and Sino-Tibetan
reconstruction and independent specialist review remain M5/M6 deliveries.

## Formal implementation

[Reconstruction.lean](../lean/Historical/Reconstruction.lean) proves membership in
`wordsExact` and `wordsUpTo` equivalent to the declared alphabet and length
conditions, and proves their sequence counts. `protoWords` additionally filters
malformed explicit morpheme boundaries; `mem_space` characterizes the exact
product of these words with the supplied **whole** joint scenarios.

Cell/sequence matching has an inductive specification. Known segments and
boundaries match exactly. Unknown readings match one segment. Null forms are
unconstrained, while present empty forms require empty outputs. `fits_iff`
connects executable acceptance to `Fits`, whose observations require M2's
`Derives` relation for the chosen branch package. `reconstruction_correct`,
`candidate_sound` and `candidate_complete` therefore establish soundness and
relative completeness beyond the finite test domain.

`prefix_results_sound` and `prefix_results_in_space` apply even before search
finishes. `prefixComplete_iff` and `completed_search_correct` establish when the
whole result is justified. `completed_empty_iff` rules out fitting histories
only in the declared complete space. A counterexample demonstrates why an empty
unexamined prefix cannot support that conclusion. Canonical certificates are
connected to M2's already-proved trace checker.

[Identifiability.lean](../lean/Historical/Identifiability.lean) defines equivalence
of predictions on a selected doculect axis, including across different models.
`equivalent_fits` and `equivalent_membership` show that such histories cannot be
distinguished by those observations. `reconstruction_mono` holds with a fixed
alphabet, bound and model. `reconstruction_refinement` also covers filling absent
forms or otherwise strengthening masks, provided the stated refinement relation
holds. The executable counterexamples retain both ancestors of a merger and
reject hybrids assembled from incompatible linked reading tuples.

[ReconstructionInput.lean](../lean/Historical/ReconstructionInput.lean) supplies
strict interchange types, package/choice/bound validation, the M3 bridge,
resource handling and certificate serialization. `checked_candidate_correct`
ties validated typed inputs to the proved reconstruction relation.
`m3_projection_recovers` connects projected source observations to M3's row
recovery theorem. Attaching an M3 dossier requires its full acceptance and exact
agreement of original forms, source references and doculects at the named target
alignment. This bridge does not infer proto sounds from correspondence classes.

M4 added **48 Lean theorem declarations**, bringing the project total at M4 delivery to **127**; the current audit also includes later milestones.
Every declaration appears in `Audit.lean`. The audit rejects project axioms,
proof placeholders and `native_decide`; reported dependencies are Lean's
standard `propext`, `Quot.sound` and `Classical.choice`. The JSON parser, metadata
validation, I/O and time-control driver remain executable trust boundaries.

## Joint alternatives and serialized results

A [complete query](../data/reconstruction/complete/joint-model-alternatives.json)
declares the proto inventory, maximum length, optional morpheme atom, doculect
axis, finite analysis bound, rule-count bound and execution limits. Each named
analysis contains a proto node, complete choice bindings, one M2 package per
doculect, and the whole observation tuple. Only those listed tuples are used.
The checker does not take a product of choices at individual positions or across
branch packages. M1 remains the evidence/provenance representation; this M4
profile makes its additional analysis decisions explicit.

Each returned candidate records `analysis_id`, `proto_node_id`, `choice_bindings`
and `protoform`, plus every branch's package ID/version, input, complete labeled
trace, output and certificate/observation checks. Equal protoforms under different
analyses remain different histories. `history_count` and
`distinct_protoform_count` are separate. There is no preferred winner or score.

Known observed cells must belong to the corresponding package inventory.
Proto symbols must belong to every branch's inventory. Package ID/version pairs
cannot denote conflicting definitions. All branches begin at their analysis's
proto node. Choice groups/options, source references, axes and nullable fields
must be explicit. Undeclared JSON fields, duplicate keys, malformed UTF-8 and
unsupported surrogate escapes fail before search.

## Complete, incomplete and invalid

The executable accepts at most 15 proto symbols, maximum length 16, 16 joint
analyses, eight doculects and 16 rules per branch. These operational profile limits
do not restrict the general theorem statements. Within the profile, a raw-space
upper bound over 20,000 hypotheses returns `incomplete` with reason `space-limit`
before allocating the space. The proto shape filter may reduce the actual scope;
the preflight ceiling is deliberately conservative.

`candidate_budget` limits evaluations. `time_limit_ms` is null or a cooperative
deadline (at most 60,000 ms), checked between candidate evaluations. Zero yields
an immediate incomplete response. The driver counts completed decisions, then
recomputes the recorded prefix through the proved checker and checks its count.
Final verification/serialization may run past the cooperative deadline. For a
hard process deadline use the optional Python wrapper below.

Only `status: "complete"` with no retained candidates sets
`no_candidate_in_scope: true`. Budget exhaustion, deadlines, oversized spaces,
invalid inputs and operational failures never make this claim. A completed empty
set means no fitting ancestor **within the declared space**, not no ancestor
anywhere. Incomplete results retain sound prefix candidates without claiming
that the remaining space has been checked.

## Verification and commands

From `lean/`:

```bash
lake build
lake exe reconstruct --suite bounded-reconstruction
lake exe reconstruct --file data/reconstruction/complete/merger.json
lake exe reconstruct --file data/reconstruction/complete/m3-bridge.json
lake exe reconstruct --file data/reconstruction/incomplete/empty-prefix.json
```

The last command intentionally exits **3**. Exit codes are 0 for a complete
search (including a completed empty set), 1 for invalid input, 2 for invocation
or I/O failure, and 3 for incomplete search. `--report FILE` saves the same JSON
as stdout. `--batch FILE` takes `{ "queries": [...] }`, checks each full query,
and preserves every result. Batch exit status prioritizes invalid over incomplete;
each query still carries its own status.

From the repository root, a process deadline can be imposed with:

```bash
python scripts/run_reconstruction.py data/reconstruction/complete/merger.json --timeout 30
```

If the process times out before returning JSON, the wrapper reports `incomplete`
with reason `process-timeout`, unknown input-validation/examined status, and no
negative reconstruction claim. Unexpected exits or malformed output become
operational errors. The test suite exercises an actual controlled process timeout.

The [82 authored fixtures](../data/reconstruction/manifest.json) include 25 complete
searches, six incomplete searches and 51 invalid inputs. Every status, exact
candidate list and expected rejection reason agrees. Each returned branch
certificate is compared to the separate M2 Python interpreter.

The exhaustive reference uses `itertools.product` to enumerate all 121 words of
length zero through four over `{a,b,c}`. For each of 16 cascades it runs each
protoform forward once and builds an inverse index. Lean independently filters
its proved enumeration for **every one of the 121 possible observed words**.
All 1,936 inverse sets and every returned certificate agree. The cascades cover
identity, merger, deletion, both directions and pass modes, chronology, and edge
conditions. A further 121 comparisons fill a missing second observation under
the same model/space; every result is the expected subset. This is a separate
algorithm and code path, not a separate human or agent review.

Full reproduction after installing the root Python requirements:

```bash
cd lean
lake build
lake env lean Audit.lean > ../reports/lean-axioms-current.txt
cd ..
python scripts/check_proofs.py reports/lean-axioms-current.txt
python scripts/build_m4_fixtures.py --check
python scripts/verify_m4.py --audit reports/lean-axioms-current.txt
python scripts/verify_m4.py --check-report
python -m unittest discover -s tests -v
python scripts/check_plan.py
```

The original macOS host uses `lake +leanprover/lean4:v4.19.0`. CI builds and audits
both 4.19.0 and 4.34.1, reruns all M1–M4 acceptance checks, and rejects generated
report drift. `--check-report` verifies saved inverse sets, hashes, thresholds and
delivered artifact paths; the full command is needed to execute Lean again.
