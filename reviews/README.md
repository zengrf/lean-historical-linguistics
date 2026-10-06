# Independent review records

| Milestone | Review | Status |
| --- | --- | --- |
| M1 | Independent transcription of six source entries by a separate AI agent | Complete; six exact matches |
| M2 | Twenty synthetic derivations worked by a separate AI agent before implementation comparison | Complete; all intermediate forms agree |
| M5 | PIE specialist assessment of the comparative data and analyses | [Pending](pie-signoff.md) |

The M1 and M2 reviews concern transcription and formal rule application. Family
specialists separately assess the linguistic analyses in M5 and M6.

## M1 double-entry transcription

**Completed on 2026-10-05 UTC:** the separate AI agent `codex-independent-ai-agent:/root/m1_source_review` independently transcribed all six required source cells. It started with fresh context, did not participate in import/encoding and did not consult imported values or validation code. All six originals agree exactly with the imports. The [response](m1-responses.json), [reviewer's method and limitations](m1-independent-review.md), and [reconciliation report](../reports/m1-review.json) are retained.

The reviewer fetched the sources at the pinned commits and checked their hashes.
The task instructions restricted access to expected answers on the shared
filesystem; there was no technical access restriction. Automated import checks
and the separate transcription review are recorded independently.

[m1-packet.json](m1-packet.json) identifies six source rows: three Indo-European and three Burmish. This is 10% of the 60 imported core records. The current import uses digital CSV data, with no OCR and no question-mark/replacement-glyph flags. Any flagged imported readings are automatically added to the required packet.

CI requires both review and delivery acceptance to pass:

```bash
python scripts/review_m1.py --require-complete
python scripts/verify_m1_delivery.py --require-complete
```

For a new or changed source packet, an independent reviewer should:

1. Open the exact pinned source file/row listed in the packet. Consult the source CSV rather than `data/pilots` or a generated expected answer.
2. Transcribe the requested original-value column into [m1-response-template.json](m1-response-template.json), recording the actual reviewer identity, reviewer type and independence attestation. Do not consult earlier responses or review notes for the same cells before finalizing the new entries.
3. Save the completed response as `reviews/m1-responses.json`, preserving the packet hash and documenting the source-only review method. The importer and validator must not generate the review response.
4. Run `python scripts/review_m1.py --require-complete`. Resolve discrepancies against the source, or add the upstream row ID and a nonempty reason to that dataset's optional `uncertainty_overrides` object in `data/import-selection.json`. Reimport to preserve the original value while flagging the concern; record `resolution: {"status": "flagged", "reason": "..."}` in the review response. Regenerate the packet, review any newly required records, update its hash in the response, and rerun all checks.
5. Once the review passes, change M1's status to `delivered`, remove the pending-review note, regenerate `reports/m1-delivery.json`, and run `python scripts/verify_m1_delivery.py --require-complete`.

Changing a pinned source or the review sample invalidates the packet hash. Reviewer identity, type and independence are explicit attestations; the script can check coverage and exact transcription agreement, but cannot authenticate reviewers. The report also records a SHA256 of the complete response's canonical JSON serialization (`ensure_ascii=False`, `sort_keys=True`, Python's default separators, UTF-8, no trailing newline). It is not the raw file hash. This M1 check concerns source entry. M5/M6 will require a separate family-specialist review of the linguistic analyses.

## M2 independent hand-worked derivations

The [M2 packet](m2-packet.json) pins the prose semantics and supplies 20 synthetic
inputs and rule sequences without expected outputs. A fresh AI reviewer manually
derived all 22 passes before seeing or executing the implementation. The
[response](m2-responses.json) records every intermediate word and a positional
rationale; the [review note](m2-independent-review.md) records method and limits.
All stages agree with Lean execution and the separate Python test oracle.

`python scripts/verify_m2.py --audit reports/lean-axioms-current.txt` checks the
packet/semantics hashes, independence attestations, complete coverage and exact
stage agreement. Changed semantics or inputs reopen the review. This is AI
semantics review, not human or family-specialist sign-off.

A later [M2 code review](m2-code-review.md), performed after the hand-worked
answers were frozen, found and independently rechecked a Unicode whitespace
validation fix. Its scope and limitations are recorded separately.
