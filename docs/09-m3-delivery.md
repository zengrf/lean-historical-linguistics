# M3: alignment and correspondence verification

**M3 is delivered; all four acceptance criteria pass.** The implementation checks
monotonic alignments, derives their sound correspondence sites, and verifies
proposed partitions under the [versioned semantics](alignment-correspondence-semantics.md).
It makes **feasibility-only** claims. All fixtures are synthetic.

| Criterion | Delivered evidence |
| --- | --- |
| M3-alignment | Inductive gap-insertion relation; equivalence to exact row recovery; preservation of absence, width, original material and explicit morpheme boundaries |
| M3-patterns | Pairwise compatibility and shared observed segments; no support from missing, unknown or gap-only overlap; distinct declared unit counts; every required site assigned exactly once |
| M3-sites | 140 counted sites, including 125 incomplete and 20 conflicting; every site's assignment, support, pair witnesses and outcome retained; 49 accepted and 86 rejected fixtures overall |
| M3-optimality | Feasibility-only profile; minimum, optimal, maximal and score claims rejected; different feasible partitions of identical observations accepted |

[correspondence-sites.json](../reports/correspondence-sites.json) records the
criterion results, all 135 fixture outcomes, all site diagnostics, finite
reference comparisons and input hashes. Negative examples pass the test only
when the checker rejects them with their intended error code. The counted suite
has 100 accepted and 40 rejected sites; rejected proposals remain visible.

## Formal contracts

[Alignment.lean](../lean/Historical/Alignment.lean) has nine theorems.
`removeGaps_iff` connects exact recovery to an inductive `GapInsertion` relation
whose constructors only copy original cells or insert gaps. `checkRow_iff` and
`checkAlignment_iff` connect executable acceptance to that relation and the
documented shape constraints. General preservation results establish exact row
recovery, preservation of absent rows and material in every accepted column.
Unknown readings, explicit boundaries, order and multiplicity are retained.

[Correspondence.lean](../lean/Historical/Correspondence.lean) has 23 theorems.
`compatible_iff` connects the executable predicate to equal axis lengths,
agreement at every position and at least one shared observed segment.
`checkGroup_iff` and `checkPartition_iff` establish equivalence to `ValidGroup`
and `FeasiblePartition`; their consequences expose pairwise compatibility,
computed support and exactly-once membership. Distinct-unit membership and
nonduplication are proved. Missing-only, unknown-only and gap-only positive
support are ruled out for arbitrary lengths. Concrete counterexamples disprove
transitivity and reject a merge of a compatible chain.

[CorrespondenceInput.lean](../lean/Historical/CorrespondenceInput.lean) has three
theorems. `dataAccepted_iff` and `dossierAccepted_iff` connect the actual CLI
acceptance functions to checked alignments, empty metadata/registry diagnostics
and a feasible partition. `accepted_data_recovers_row` bridges the typed input
rows to exact recovery. Site cells are derived from referenced alignment columns;
the input has no field for a separate, potentially inconsistent copy of them.

M3 adds 35 theorems, bringing the project total to 79. The audit covers every
declaration and rejects proof placeholders, project axioms and `native_decide`.
The local audit reports only Lean's standard `propext`, `Quot.sound` and
`Classical.choice` dependencies. These proofs are conditional on the defined
representations and predicates; they do not prove historical cognacy, correct
source transcription or independence of the declared evidence-unit labels.

## Alignment and grouping input

A [complete dossier](../data/correspondence/valid/boundaries.json) supplies:

- `alignment_data`: schema `1.0.0`, document metadata, ordered doculect axis and
  alignments; each alignment gives its ID, evidence unit, width and source-labeled
  original/aligned rows;
- `sites`: IDs referring to every segment-bearing `(alignment_id, column_index)`
  exactly once, using zero-based indices;
- `groups`: IDs, site memberships and claimed counts of distinct evidence units;
- `support_policy: "distinct-evidence-units-v1"` and `claim: "feasibility-only"`.

Cells reuse M1's tagged `kind`/`value` encoding. A null original and aligned row
means an absent word. A present empty original is `[]` and may align to gaps.
Present rows cannot contain missing-data cells. Explicit `boundary("+")` tokens
separate nonempty original spans, occupy boundary columns, and survive recovery.
This profile does not accept interval span fields or metathesis.

Missing and unknown cells provide neither conflict nor positive support.
Observed gaps conflict with segments. Equal gaps do not constitute a shared
sound. A group is checked at every pair of distinct sites, since compatibility
is not transitive. Singleton groups are feasible with support one; they establish
no recurrence. Several sites from one declared etymon do not increase support.
The checker cannot authenticate the historical independence of different labels.

The observed-sound compatibility criterion follows
[List (2019), PDF pp. 8–9](https://aclanthology.org/J19-1004/). The explicit
unknown-reading policy is this project's conservative extension. Full semantics,
source boundaries and assumptions are stated in the linked specification.

The strict shared JSON parser rejects duplicate/unknown keys and omitted explicit
fields. Literal supplementary UTF-8 and BMP escapes are supported; surrogate
escapes are rejected consistently across toolchains. Segment values obey M2's
atomic-symbol constraints. No Unicode normalization occurs in this checker.

## Executable, reports and verification

From `lean/`:

```bash
lake build
lake exe correspondence_check --suite correspondence-sites
lake exe correspondence_check --file data/correspondence/valid/boundaries.json
lake exe correspondence_check --alignment data/correspondence/valid/standalone-boundaries.json
lake exe correspondence_check --suite correspondence-sites --report /tmp/correspondence-suite.json
```

File checks return 0 for acceptance, 1 for rejection and 2 for invocation/I/O
failure. The suite returns success only if every expected result/rejection code
matches and the separate total/incomplete/conflicting site floors pass. Paths
work from the repository root and `lean/`. Saved CLI reports equal stdout JSON.

Each `fixtures[].result.sites[]` entry in the saved acceptance report records
the derived cells, alignment coordinate, evidence unit, group assignments and
occurrence count, claimed/computed support, pairwise compatibility, shared-sound
doculect witnesses, conflicting sites, site acceptance and document acceptance.
`site_accepted` checks that site's assigned groups and the input; another group's
failure can still reject the document. `pairwise_compatible` alone is insufficient
for acceptance because support, registry and coverage must also pass.
Recovered rows are recorded even for rejected proposals. Stable error codes and
paths are saved; full CLI error messages may vary across Lean parser versions.

[The Python evaluator](../scripts/reference_correspondence.py) independently
computes the specification using position maps, sets and counters. It checks all
125 typed fixtures, every emitted site field, and recovery of 916 rows in accepted
alignments, including alignments whose grouping proposal is rejected.
Ten byte/shape-invalid fixtures are rejected before semantic evaluation.
This is a second implementation written in this task, not an independent human
or separate-agent review.

The verifier also compares:

- **67,081 column pairs**: all 259 sequences of lengths zero through three over
  two segments, a gap, missing data, an unknown reading and a boundary; conflict,
  shared-segment positions, compatibility and symmetry all agree;
- **6,392 partition proposals**: eight three-site contexts, every ordered list of
  zero through three nonempty subsets, and variants with incorrect support.
  These include non-transitivity, duplicate units, missing/unknown data,
  gap conflicts, boundaries and differing axis lengths.

The `--matrix FILE` interface takes `{ "columns": [...] }`; `--partitions FILE`
takes `{ "sites": [...], "proposals": [...] }` with typed core sites
`{ "id": "...", "evidence_unit": "...", "cells": [...] }` and lists of groups.
Both emit `scope: "typed-core-evaluation"`. They expose core functions for finite
comparisons and do not certify source ingestion, alignment validity or optimality.
Use `--file` for full dossier acceptance. Exhaustive tests over these small
domains supplement the general proofs; they are not bounded inverse reconstruction
(M4) or optimization certificates (M7).

To reproduce the complete delivery:

```bash
cd lean
lake build
lake env lean Audit.lean > ../reports/lean-axioms-current.txt
cd ..
python scripts/check_proofs.py reports/lean-axioms-current.txt
python scripts/build_m3_fixtures.py --check
python scripts/verify_m3.py --audit reports/lean-axioms-current.txt
python scripts/verify_m3.py --check-report
python -m unittest discover -s tests -v
python scripts/check_plan.py
```

On the original macOS host use `lake +leanprover/lean4:v4.19.0`. CI builds and
audits both 4.19.0 and 4.34.1, runs M1/M2 regressions and all M3 comparisons, and
rejects generated-report drift. `--check-report` verifies hashes, saved site
evidence, thresholds and artifact paths; only the full run executes Lean.
Byte parsing, file I/O, metadata and empirical source interpretation remain
outside the kernel proof claim. M1's real datasets remain available for the later
source-reviewed case studies; synthetic M3 acceptance is not that review.
