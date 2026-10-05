# M1: evidence schema, provenance and import contract

**M1 is delivered: all four acceptance criteria pass.** A separate AI agent completed the independent source-entry review, with exact agreement on all six required entries. The authoritative criterion-by-criterion result is [m1-delivery.json](../reports/m1-delivery.json). This is not human or family-specialist sign-off, and does not establish the historical correctness of the imported analyses.

## Delivered artifacts

| Acceptance criterion | Result | Evidence |
|---|---|---|
| M1-fixtures | 38 valid fixtures accepted; 44 adversarial fixtures rejected for their intended reasons | [Fixture manifest](../data/fixtures/manifest.json), [validation report](../reports/schema-validation.json) |
| M1-lossless | Every valid fixture and all 60 real imported records preserve their complete structure through Lean JSON decoding/encoding | [Typed evidence](../lean/Historical/Evidence.lean), [verification script](../scripts/verify_m1.py) |
| M1-cldf | Two pinned full CLDF datasets validate; 30 records from each are imported and reconciled by upstream ID | [IE-CoR report](../reports/cldf-iecor.json), [Burmish report](../reports/cldf-hillburmish.json), mapping policy below |
| M1-review | Six of 60 core records independently transcribed by a separate AI agent; all six match exactly; no flagged imported readings | [Blinded packet](../reviews/m1-packet.json), [review record](../reviews/m1-independent-review.md), [review report](../reports/m1-review.json) |

The [versioned schema](../schema/v1/README.md) and [migration policy](../schema/MIGRATIONS.md) specify required fields, source/attestation distinctions, dates, normalization and linked alternatives. The validator rejects dangling references, duplicate primary IDs, unrecorded normalization, incompatible cell contents, reconstructed/attested identity confusion and invalid choice bindings. Strict input checks also reject duplicate JSON keys, unknown fields and malformed Unicode input.

The CLI accepts a dossier file or a directory of immediate `.json` files. Its acceptance command works from `lean/`:

```bash
lake exe dossier_check data/pilots --strict
```

It checks both pilots and prints accepted/rejected file counts, record counts and structured diagnostics. `--report FILE` saves that output. `--roundtrip FILE` serializes one accepted dossier for independent comparison. A rejected dossier returns exit code 1; invocation or I/O failure returns 2. The root-relative `data/pilots` path is resolved from `lean/` when necessary.

## Imported data and scope

| Dataset | Exact commit | Source form rows validated | Imported core rows |
|---|---|---:|---:|
| IE-CoR | `700b635a04786427b78841489c46eefbe2843509` | 25,731 | 30 |
| Hill–Gong Burmish | `3d96cfa6b2ed4c59fd13e28ef5ae00db30247bb3` | 4,032 | 30 |

[The selection file](../data/import-selection.json) freezes every selected upstream ID and its selection rationale. The sample is balanced in source order across doculects with segmented forms; it tests representation and import behavior. It is not a cognate-set benchmark or a statistically representative sample. All 60 imported records are the M1 core for review coverage.

Burmish supplies a real Sino-Tibetan import with available CLDF data. This does not replace the planned Kuki-Chin reconstruction case study in M6. Source ProtoBurmish forms receive reconstructed status, a named source analysis and a distinct proto-node. Other source records are treated as reported attestations under the dataset's identities, not independently verified historical facts.

Both sources are CC BY 4.0; [attribution and packaging details](../data/THIRD_PARTY_NOTICES.md) accompany unmodified source-file contents. All snapshot files are hashed in [the manifest](../data/upstream/manifest.json). The upstream Git attribute files are renamed as recorded there to prevent checkout newline conversion from changing the acquired source bytes.

## Reviewed mapping and loss policy

The adapter discovers columns using [CLDF property URLs](https://cldf.clld.org/v1.0/terms.html), not assumptions about names such as `ID` or `Value`. It uses pycldf to validate the complete dataset and parse declared separators/nulls. This initial profile reads physical, comma-delimited UTF-8 CSV columns. It rejects missing mappings, repeated selected IDs, unknown selected rows and selected rows lacking the original/Form/Segments values required by this profile. Those cases need an explicit adapter extension; they are not silently skipped.

| Source information | Evidence representation |
|---|---|
| Dataset repository, commit, license and form-table checksum | Dataset source record plus complete snapshot manifest |
| Form ID | Stable dataset-prefixed record ID and unmodified upstream row ID |
| Language/parameter references | Declared doculect and meaning IDs; exact source labels retained |
| Original `Value` | Exact `reading.original` and the original raw column |
| `Form` | Explicit first normalization step, with source-row provenance |
| `Segments` | Explicit second step and source token cells; concatenation is a display convention |
| Boundary tokens | Distinct boundary cells |
| Source question marks/replacement glyphs | Unresolved cells/uncertainty flags and review requirement |
| All form columns, including uninterpreted ones | Ordered `raw_columns` list, preserving every cell as text |
| Other table fields and tables | Retained in the immutable snapshot; not promoted to evidence semantics |

Upstream transcription conventions are preserved. For example, a segment token containing a grapheme/sound alias such as `ṅ/ŋ` stays intact. It is not split into independently selectable proto-segments. The record's `mixed` representation label acknowledges that source strings, transcription conventions and segment tokens can differ.

Every mapped change from original text to normalized display has a versioned method and reason. The Lean theorem about normalization chains proves their input/output continuity. It does not prove that an upstream transcription is correct. Tokenization and linguistic interpretation are still source claims.

An unresolved source-reading concern can be retained using a reasoned `uncertainty_overrides` entry in the selection file. Reimporting flags the record without changing its original source value. The override appears in the import report and expands the independent-review packet as necessary.

The importer retains cognacy, loan, native-script, commentary and other custom fields in raw columns, while explicitly listing them as not semantically interpreted. Additional cognate/clade/loan/author tables remain in the snapshot. This is an intentional semantic boundary: M1 does not turn their contents into verified inheritance or sound-law judgments.

IE-CoR's selected rows have empty row-level source-reference fields. They receive exact dataset-row citations; dictionary-level references are not invented. Burmish's original source-reference strings remain in raw columns and the source bibliography remains in the snapshot. Resolving those citations into a richer publication graph is future data enrichment, not hidden behind a generic “source complete” claim.

This mapping/loss policy was reviewed during implementation against both snapshots and adversarial adapter tests. The separate source-entry review described below checks the required transcription sample. No unsupported semantic field is claimed to have been imported losslessly into a richer meaning; its original bytes remain recoverable.

## Proof and parser boundaries

Five M1 theorems bring the audited project total to 27:

- Recorded normalization replay agrees with an inductive chain relation.
- Renormalization retains the original source string.
- Renormalization retains linked-choice bindings.
- A missing observation is distinct from an alignment gap.
- Every typed cell survives JSON encoding/decoding.

The complete dossier round trips are executable tests, not a general theorem about every possible dossier. The executable checker is written in Lean, but there is no claim of a verified UTF-8/JSON parser or a theorem proving every validation branch correct. Source checksums identify artifacts; they do not establish their truth.

Original strings are retained rather than reconstructed by inverting normalization. Tests include combining marks, supplementary characters, tone, stress, length, Tibetan/Chinese scripts, multiple meanings, variants, coindexed alternatives, dates, missing evidence, gaps and uncertain readings. The supporting Python JSON Schema checker and source-rebuild checks provide an independently implemented comparison of structure and retained source data, but not an independent human transcription.

## Reproduce the engineering checks

Install the root Python requirements and build the Lean project first. On the original macOS host use the documented `+leanprover/lean4:v4.19.0` override; CI checks both supported toolchains.

```bash
cd lean
lake build
lake exe dossier_check data/pilots --strict
lake env lean Audit.lean > ../reports/lean-axioms-current.txt
cd ..
python scripts/check_proofs.py reports/lean-axioms-current.txt
python scripts/import_cldf.py --check
python scripts/verify_m1.py
python -m unittest discover -s tests -v
python scripts/review_m1.py --require-complete
python scripts/verify_m1_delivery.py --require-complete
python scripts/check_plan.py
```

The saved engineering report records hashes of its inputs and implementation. The delivery verifier rejects a stale report or missing artifact. Generated schemas/fixtures/imports are rebuilt in CI and compared against the committed versions. Upstream validation uses vendored snapshots and needs no network after dependencies are installed.

## Completed independent source-entry review

On 2026-10-05 UTC, the separate AI agent `codex-independent-ai-agent:/root/m1_source_review` completed the fixed six-row packet: three IE-CoR and three Burmish entries. It started with fresh context, had not participated in the encoding, and consulted the packet and source CSVs without viewing imported values, importer code or validation reports. It separately fetched the commit-pinned public CSVs and verified byte equality and SHA256 hashes against the local snapshots. It inspected each source row and every Unicode code point before finalizing the entries.

The [submitted response](../reviews/m1-responses.json) and [reviewer's record](../reviews/m1-independent-review.md) preserve its identity, method, source hashes and limitations. Subsequent reconciliation found exact Unicode agreement on all six originals, including combining marks, IPA symbols, vowel length and superscript tones. Coverage is 6/60 (10%); there are no flagged imported readings or unresolved discrepancies. The reviewer made no changes to imports or validators.

Independence here means a separate agent and source-entry procedure without access to expected answers in its task context. The shared filesystem boundary was enforced by instruction, not a sandbox, and shared AI failure modes remain possible. This is not an independent human or family-specialist review. The M5/M6 linguistic review requirements remain in force.

Both acceptance commands now pass, and CI requires them:

```bash
python scripts/review_m1.py --require-complete
python scripts/verify_m1_delivery.py --require-complete
```

The review checker requires the current packet hash, reviewer identity, independence attestation, sufficient coverage, and resolved or explicitly flagged discrepancies. It also records reviewer type and a canonical JSON response hash, so the saved report identifies the exact response assessed. It cannot authenticate reviewer identity or independence. Changing a source or the sample requires a new review; missing, stale or incomplete review evidence fails CI. The delivery report now records `all_deliverables_accepted: true`.
