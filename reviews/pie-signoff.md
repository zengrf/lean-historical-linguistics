# M5 independent PIE specialist sign-off

**Status: pending. No specialist sign-off has been received.**

The current result is **computationally checked, linguistically unreviewed**.
No person or institution is represented as endorsing it. The primary AI
implementation session performed the encoding and its engineering checks;
those checks are not independent family-specialist review.

The [packet](pie-packet.json) requires assessment of all 20 core sets, eight
source-backed onset diagnostics and three morphology dossiers. It includes
source locators, retained failures and global questions about scope, chronology,
secondary attribution and leakage. The [response file](pie-responses.json)
contains only a pending marker. The [delivery report](../docs/11-m5-delivery.md)
and [evaluation](../reports/pie-evaluation.json) keep M5-core and M5-signoff open.

An actual response must identify the reviewer and relevant family expertise,
attest independence from the original encoding, name the packet SHA-256, and
supply a dated assessment of every required item with a rationale and source
locators. `decision` is `approve` or `unresolved-objection` per item; unresolved
release objections keep linguistic validation open. A JSON attestation is a
recording mechanism, not cryptographic proof of a person's identity.

Run `python scripts/review_pie.py --prepare` only when preparing a changed
packet for review. It does not create approval or overwrite a response.
`python scripts/review_pie.py --require-complete` checks the actual response and
returns a nonzero exit status while independent review remains pending.
