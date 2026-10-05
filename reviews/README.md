# M1 independent double-entry review

The importer and automated source comparisons were implemented by Codex. They are not an independent second transcription. **No independent reviewer response has been recorded yet.**

[m1-packet.json](m1-packet.json) identifies six source rows: three Indo-European and three Burmish. This is 10% of the 60 imported core records. The current import uses digital CSV data, with no OCR and no question-mark/replacement-glyph flags. Any flagged imported readings are automatically added to the required packet.

An independent reviewer should:

1. Open the exact pinned source file/row listed in the packet. Consult the source CSV rather than `data/pilots` or a generated expected answer.
2. Transcribe the requested original-value column into [m1-response-template.json](m1-response-template.json), recording the actual reviewer identity and independence attestation.
3. Save the completed response as `reviews/m1-responses.json`, preserving the packet hash. No response is generated automatically.
4. Run `python scripts/review_m1.py --require-complete`. Resolve discrepancies against the source, or add the upstream row ID and a nonempty reason to that dataset's optional `uncertainty_overrides` object in `data/import-selection.json`. Reimport to preserve the original value while flagging the concern; record `resolution: {"status": "flagged", "reason": "..."}` in the review response. Regenerate the packet, review any newly required records, update its hash in the response, and rerun all checks.
5. Once the review passes, change M1's status to `delivered`, remove the pending-review note, regenerate `reports/m1-delivery.json`, and run `python scripts/verify_m1_delivery.py --require-complete`.

Changing a pinned source or the review sample invalidates the packet hash. Reviewer identity and independence are explicit attestations; the script can check coverage and transcription agreement, but cannot authenticate a person. This M1 check concerns source entry. M5/M6 will require a separate family-specialist review of the linguistic analyses.
