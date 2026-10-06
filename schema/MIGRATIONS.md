# Schema version and migration policy

The first evidence schema is **1.0.0**. M0 contained no earlier evidence schema, so version 1.0.0 requires no migration from M0.

The reader requires an exact `schema_version` and explicit values or `null` for every declared field. Unknown fields and versions fail. This prevents an older reader from silently discarding a new interpretation of source data. The JSON Schema and Lean decoder are separate checks; cross-reference and normalization-history constraints live in the Lean validator.

Before accepting another version:

1. Add an immutable schema directory and a version-specific decoder. Never change the meaning of a published 1.0.0 field in place.
2. Publish an explicit migration function with source and target versions. It must preserve source snapshots, original strings, stable IDs, uncertainty and provenance, or reject a record it cannot translate faithfully.
3. Log migration ID/version, input/output artifact hashes and any changed interpretation. Retain the input artifact. Renaming an ID requires a published old-to-new mapping.
4. Add old-version and new-version fixtures, rejection cases and lossless round-trip tests for the retained source layer. Revalidate all references and linked choices after migration.
5. Have the semantic change reviewed before adopting the new format. Reopen affected independent-review gates when source readings or relevant interpretations change.

Use a major version for changed meanings or required representations, a minor version for explicit additions requiring an updated reader, and a patch version for compatible corrections. Even a minor addition is not silently accepted by the exact-version reader. Documentation-only corrections that do not change the contract need no schema version change.

Unicode normalization, tokenization and editorial decisions have their own method IDs and versions. A change to one of these methods creates a new analysis while retaining the original form. The initial importer identifies itself through its committed code, pinned source snapshots and reproducible import report.
