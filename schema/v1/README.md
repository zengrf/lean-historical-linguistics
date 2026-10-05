# Evidence dossier 1.0.0

[dossier.schema.json](dossier.schema.json) describes the closed interchange structure. [Evidence.lean](../../lean/Historical/Evidence.lean) supplies typed structures and distinct cell constructors; [Validation.lean](../../lean/Historical/Validation.lean) checks semantic consistency. The command-line reader is [DossierCheck.lean](../../lean/DossierCheck.lean).

## Required objects

| Object | Required information |
|---|---|
| Dossier | Exact schema version, stable ID, description, source/doculect/meaning/analysis/method/choice registries and records |
| Source | ID, title, URL or URN, version, license, publication/dataset/synthetic kind, optional SHA-256 |
| Doculect | ID, name, family, historical stage, attested/proto kind, optional ordered date interval |
| Meaning | ID and source-derived label; a record may reference several meanings |
| Analysis | ID, description, cited sources and a source-defined proto-node ID |
| Record | Stable ID, doculect, meanings, representation, attestation, evidence state, citations, readings, uncertainty and optional import origin |
| Reading | Original text, normalized display, explicit cells, versioned normalization history and shared-choice bindings |
| Import origin | Dataset ID, table, original upstream row ID, mapped ID/original column names and **all** raw form columns |

IDs use nonempty ASCII letters/digits plus `._:-`. They are unique within registries. Record IDs and dossier IDs must also be unique across a directory checked in one invocation. Imported record IDs are namespaced by dataset. A future selection change must not renumber an existing upstream record.

Dates use astronomical years, including year zero, with `earliest <= latest`. An unknown date is `null`. Stage labels must still be explicit; unknown dates must not be fabricated from a modern language label.

## Source text, normalization and cells

Every reading stores its exact `original` string independently of its `normalized` display. A nonempty history links the two through input/output steps with declared method ID/version and a reason. Identity steps are explicit and cannot change text. The validator checks continuity; it does **not** prove that an arbitrary editorial or upstream transformation is linguistically justified.

The cells render the normalized display in order:

- `segment` carries a nonempty source-defined token. A token may include combining marks, length or tone; it need not be one code point.
- `boundary` carries explicit boundary text, such as `+`.
- `gap` has `value: null` and renders nothing. It is an alignment position, not a missing observation.
- `missing` has `value: null`. A missing observation has empty original/display strings and exactly one missing cell.
- `unknown` carries an unresolved source reading and requires an uncertainty flag and note. It can occur inside an otherwise present form.

No implicit Unicode normalization occurs during parsing or serialization. Literal UTF-8 supports supplementary characters, Tibetan/Chinese scripts and combining marks. For compatibility with Lean 4.19, UTF-16 surrogate escape sequences are rejected with `UNICODE_ESCAPE`; use the equivalent literal UTF-8 character. Ordinary escapes remain supported. Invalid UTF-8, duplicate JSON object keys, unknown fields and omitted explicit optional fields fail.

Losslessness means recovery of the original **string and source data**, not inversion of a lossy normalization from its output alone. JSON whitespace and object key ordering can change; string code points and the separately retained upstream file bytes do not.

## Variants and linked alternatives

Each reading is a complete joint hypothesis. For example, two readings `pat` and `pid` do not create the unlisted hybrids `pad` and `pit`. A choice group declares named options. Bindings on readings can refer to the same group across different records, preserving correlations. A reading cannot bind one group twice or reference an undeclared option.

M1 preserves and validates these references. It does not enumerate globally compatible combinations or prove their linguistic interpretation; that belongs to reconstruction work in M4.

Reconstructed records require a proto doculect, a declared analysis and that analysis's proto-node. Attested records cannot silently carry reconstructed identity. This is a distinction between encoded source claims, not independent authentication of the source.

## Validation and migration

From `lean/`, run `lake exe dossier_check data/pilots --strict`. The CLI also accepts explicit files, directories, `--report FILE` and `--roundtrip FILE` for one accepted dossier. Exit codes are 0 for all accepted, 1 for rejected dossiers and 2 for invocation/I/O failures. Directory scanning covers immediate `.json` files, not nested directories.

The [migration policy](../MIGRATIONS.md) governs future changes. See the [M1 delivery report](../../docs/07-m1-delivery.md) for import scope, tests and remaining review requirements.
