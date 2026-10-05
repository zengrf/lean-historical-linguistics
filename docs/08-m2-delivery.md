# M2: contextual sound laws and derivation certificates

**M2 is delivered; all four acceptance criteria pass.** It implements the [versioned rule semantics](rule-semantics.md), a total Lean
interpreter, a theorem-backed certificate checker, and strict JSON tooling.
[contextual-rules.json](../reports/contextual-rules.json) records all four
acceptance criteria and the exact source hashes used for verification.

## Deliverables and verification

| Criterion | Delivered evidence |
| --- | --- |
| M2-semantics | Atomic segments, explicit morpheme/word boundaries, bounded contexts, both directions, simultaneous/feeding passes, replacement/deletion and ordered stages; 20 independently hand-worked examples covering 22 passes |
| M2-checker | 17 new Lean theorems, including equivalence between Boolean acceptance and the entire inductively licensed trace; all 44 project theorem declarations audited |
| M2-adversarial | 25 valid and 88 adversarial fixtures, each with a named expected outcome and rejection reason |
| M2-no-memorization | Restricted typed grammar, finite declared inventory and two-token context bounds; no callback, lexical lookup, word-specific exception or whole-word replacement operation |

The [rule packages](../data/rule-packages/contextual-examples.json) and all fixtures
are synthetic. They establish representation and execution behavior, not
historical sound laws or reconstructions of a real proto-language.

The interpreter uses structural recursion on the original input. During feeding
passes, produced material can condition subsequent original tokens but is not
itself revisited. A deletion consumes one original token. This supplies a total
interpreter without fuel, convergence assumptions or fixed-point iteration.

## Formal contracts

[Rules.lean](../lean/Historical/Rules.lean) defines local tests, the three `Emits`
inference rules, an inductive `Scan` relation, and direction-sensitive `Pass`.
`scan_eq_iff` and `pass_iff_apply` connect them to the executable functions.
Additional theorems establish deterministic passes, non-increasing output
length and copying of morpheme boundaries at each visited position.

[Certificates.lean](../lean/Historical/Certificates.lean) defines named laws,
stage-labeled intermediate words, ordered cascades and `LicensedTrace`.
`checkTrace_iff` states that the Boolean checker accepts **exactly** the supplied
traces licensed by the inductive semantics, including law IDs and stage labels.
`checkTrace_sound` and `checkTrace_complete` expose the two directions.
`derivation_iff_certificate` connects cascade derivability to existence of an
accepted certificate; `canonical_trace_accepted` provides one constructively.

[RuleInput.lean](../lean/Historical/RuleInput.lean) adds finite inventories,
package identity/version, chronological stage continuity, context bounds and
strict interchange types. `checkDossier_iff` ties the same Boolean used by the
CLI to both empty validation diagnostics and `LicensedTrace`. Diagnostics explain
rejections; they are not a second acceptance algorithm.

Theorems hold for typed rules and words. The scan proofs allow arbitrary finite
context lengths; the accepted JSON profile additionally enforces at most two
tokens per side. They do not establish natural classes, historical regularity,
correct segmentation or the empirical justification of any supplied package.

## Independent examples and additional comparisons

The separate AI task `/root/m2_hand_review` received only the pinned prose
semantics and the [input-only packet](../reviews/m2-packet.json). Before seeing or
executing any implementation, it manually worked all 20 cases and froze each
intermediate word with a position-by-position rationale. The
[responses](../reviews/m2-responses.json) and
[review note](../reviews/m2-independent-review.md) retain its method and hashes.
The verifier compares every stage and final word directly with Lean execution.

This is independent AI hand-work, not human or family-specialist sign-off.
The workspace read boundary was enforced by instruction, not a sandbox.
Reviewer identity and independence are attestations; shared AI failure modes
remain possible. Changed prose semantics or example inputs invalidate the
review hashes and require renewed review.

After freezing those answers, the same separate agent performed a
[code review](../reviews/m2-code-review.md). It found one mismatch in Unicode
whitespace validation. The fix added an explicit whitespace predicate and 19
regression fixtures; the reviewer independently rechecked 50 whitespace
rejections and four valid Unicode baselines. No blocking findings remained in
its inspected scope. This later implementation inspection did not alter or
supply answers to the earlier hand-worked review.

An additional [Python reference](../scripts/reference_rules.py) uses original
indices and mutable output slots, rather than Lean's recursive prefix scan and
reversal for right-to-left execution. The verifier enumerates words of length
zero through four over `{a,b,c}` and `{a,b,+}`, deduplicates the overlap, and
compares every intermediate and final word for 44 single-pass/cascade packages.
This gives 211 distinct words per package and 9,284 comparisons. It also checks
length and boundary retention. This is a finite forward-execution test, not the
bounded inverse reconstruction promised by M4.

## JSON and command-line interface

A [complete example](../data/contextual-rules/valid/ltr-feeding.json) supplies:

- `schema_version` and a stable dossier `id`;
- `model`: ID/version/description, segment inventory, initial/final stages and ordered laws;
- `certificate`: exact package ID/version, input, every post-law step and final output.

Words are arrays of strings; `+` denotes an explicit morpheme boundary. Contexts
use arrays for segment classes, `*` for one segment and `+` for a boundary.
`replacement: null` means deletion. All fields, including nulls, must be explicit.
Duplicate and unknown JSON fields, malformed UTF-8, unsupported modes/directions,
undeclared tokens, broken stage chains and missing/extra steps are rejected.
Segment symbols reject C0/C1 controls and the pinned
[Unicode 17.0 White_Space property](https://www.unicode.org/Public/17.0.0/ucd/PropList.txt),
including embedded non-ASCII spaces. Regression fixtures cover each non-ASCII
separator after an independent code review identified the narrower standard
library predicate as insufficient.
Supplementary characters must be literal UTF-8 for parser compatibility; BMP
escapes and JSON key reordering are accepted. Unicode normalization is never
performed by the interpreter.

From `lean/`:

```bash
lake build Historical.Rules Historical.Certificates
lake build
lake exe verify_dossiers --suite contextual-rules
lake exe verify_dossiers --file data/contextual-rules/valid/ltr-feeding.json
lake exe verify_dossiers --suite contextual-rules --report /tmp/contextual-suite.json
```

`--suite` succeeds only if every fixture has its expected outcome/reason and the
minimum counts are met. Individual `--file` checking returns 0 for acceptance
and 1 for rejection; invocation/I/O failures return 2. The suite's root-relative
paths work from either the repository root or `lean/`.

`--evaluate FILE` accepts an object with `model` and a nonempty list `inputs`.
It validates the package and input inventory, then emits canonical steps and
outputs for each word. This provides trace generation for testing or proposals;
it does not infer a model or authenticate that a package is historically valid.

The parser is shared with M1 and rejects hidden fields before typed decoding is
accepted. Parsing, packaging validators and file I/O remain executable trust
boundaries; this delivery does not claim a verified byte-level JSON parser.
M1's real evidence dossiers retain their originals and metadata separately.
M2 does not silently project uncertain/missing evidence into rule tokens or
claim to implement the empirical evidence-to-analysis decisions in M5/M6.

## Reproduction and CI

Install the root Python requirements and build Lean first:

```bash
cd lean
lake build
lake env lean Audit.lean > ../reports/lean-axioms-current.txt
cd ..
python scripts/check_proofs.py reports/lean-axioms-current.txt
python scripts/build_m2_fixtures.py --check
python scripts/verify_m2.py --audit reports/lean-axioms-current.txt
python scripts/verify_m2.py --check-report
python -m unittest discover -s tests -v
python scripts/check_plan.py
```

On the original macOS host, replace `lake` with
`lake +leanprover/lean4:v4.19.0`. CI builds and audits both 4.19.0 and 4.34.1,
runs all M1 regressions and the complete M2 acceptance suite, and rejects stale
generated reports. `--check-report` alone checks hashes, review provenance and
delivered paths; it does not rerun Lean. The report never substitutes for a
current build and kernel audit.
