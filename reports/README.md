# Verification records

[m7-verification.json](m7-verification.json) records generative reconstruction
from daughter reflexes: 1,488 exact inverse sets, complete graph checking,
global model consistency, rejected malformed graphs and corrupted forward
certificates. [m7-benchmark-local.json](m7-benchmark-local.json) measures 1,000
distinct cognate rows and 3,000 branch certificates, including generation and
native checking. [m7-ui/checks.json](m7-ui/checks.json) records 19 browser checks
for reflex import, selectable constraints, indexed whole-lexicon enumeration
and export. See [M7 delivery](../docs/15-m7-delivery.md) for the 28 new theorem
statements, runtime profile, supported compiler fragment and empirical limits.

[research-workbench.json](research-workbench.json) records the five new
operations: 256 exhaustive matrix comparisons, 874 chronology permutations,
20 integration executions and 23 rejected requests, with source hashes and
20 new theorem names. [ui/verification.json](ui/verification.json) records 43
real-browser checks against the API and compiled Lean, including downloaded
query/result JSON, distinct reconstructed forms, editable native word bounds,
explicit conflict relaxation, original Kiwari CSS/font loading, imported
specifications, keyboard tabs, source pagination,
four responsive widths and day/dusk/night settings. Its desktop and mobile
screenshots were visually inspected. See the [workbench guide](../docs/14-research-workbench.md)
for precise claims and reproduction commands.

[materials-and-exploration.json](materials-and-exploration.json) records the
expanded source catalogue and ten hypothesis-selection executions in Lean,
including comparison with the independent Python interpreter. The accompanying
15 tests check all 41,942 retained CLDF form rows, the expanded VanBik entries,
selection of all 509 registered pool queries, linked analyses, withheld
observations, ambiguity and incomplete searches. See the
[coverage and usage guide](../docs/13-materials-and-exploration.md).

`library-audit.json` is the saved **full local** acquisition audit, produced with:

```bash
python scripts/verify_library.py --local --output reports/library-audit.json
```

It records the time, count decisions, source coverage, access gaps and actual checks of all 127 retained PDF files. It attests to the files checked at that time. It does not establish exhaustive literature coverage or cover-to-cover reading. A public clone contains 64 PDFs; its ordinary audit therefore has a different on-disk count.

`lean-axioms-local.txt` records `#print axioms` for all 185 theorem declarations after a successful local build with **Lean 4.19.0 on macOS 10.15 x86_64**. Its reported dependencies are `propext`, `Quot.sound` and `Classical.choice`. There are no project axioms or proof placeholders in the audited source.

The local host could not run the Lean 4.34.1 binary because its system C++ library lacks a required symbol. [GitHub Actions](https://github.com/zengrf/lean-historical-linguistics/actions/workflows/ci.yml) independently builds the source on Linux with both 4.19.0 and the pinned 4.34.1, then checks each generated theorem audit. Consult the run for the commit being evaluated; a committed old report alone does not validate changed source.

The plan validator checks the machine-readable register's structure and delivered artifact paths. The library verifier checks PDF identity and metadata consistency. Neither substitutes for the future linguistic review and empirical evaluation specified in the delivery plan.

M1 reports are separate from the literature acquisition audit:

- [schema-validation.json](schema-validation.json): 38 valid / 44 adversarial cases, 60 imported records, source reconciliation, structural round trips and input hashes.
- [cldf-iecor.json](cldf-iecor.json) and [cldf-hillburmish.json](cldf-hillburmish.json): pinned imports, row/ID counts, field mappings and uninterpreted data.
- [m1-review.json](m1-review.json): six of 60 originals independently transcribed by a separate AI agent; all match exactly. The report records reviewer type, independence attestation and a canonical JSON response hash. See the [review method and limitations](../reviews/m1-independent-review.md); this is not human or family-specialist sign-off.
- [m1-delivery.json](m1-delivery.json): all four criteria pass, with `all_deliverables_accepted: true` and the accepted artifact paths.

CI now runs both `python scripts/review_m1.py --require-complete` and `python scripts/verify_m1_delivery.py --require-complete`. A missing, stale or incomplete review fails acceptance; changed source readings require renewed independent review.

[contextual-rules.json](contextual-rules.json) records M2's four accepted criteria,
25 valid / 88 adversarial fixtures, exact agreement on 20 independently hand-worked
AI examples, 9,284 further forward comparisons, the 17 new theorem names and
source hashes. [M2's delivery document](../docs/08-m2-delivery.md) states the proof
and empirical limits. `python scripts/verify_m2.py --audit PATH` reruns the
executable checks and audits a freshly emitted Lean theorem report;
`--check-report` checks freshness, review attestations and delivered paths only.
Both Lean CI jobs run the full verification and reject report drift.

[correspondence-sites.json](correspondence-sites.json) records M3's four accepted
criteria, all 135 fixture outcomes and their site/row diagnostics, 140 counted
synthetic sites (125 incomplete, 20 conflicting), 67,081 pair comparisons and
6,392 partition comparisons. It records 35 new theorems and exact input hashes.
The complete report preserves rejected group proposals and states feasibility
only; no minimum cover or historical reconstruction is claimed. See
[M3 delivery](../docs/09-m3-delivery.md) for interpretation and reproduction.
`python scripts/verify_m3.py --audit PATH` executes the full checks;
`--check-report` validates saved evidence, thresholds, hashes and delivered paths.
Both Lean CI jobs rerun M3 and compare the report byte for byte.

[exhaustive-small-domain.json](exhaustive-small-domain.json) records M4's four
accepted criteria, 48 new theorems, 82 authored fixture results (25 complete,
six incomplete, 51 invalid), exact candidate sets for all 1,936 bounded inverse
queries over 16 cascades, and 121 observation-refinement checks. Candidate
certificates and choice bindings are checked against the Python reference.
Timeouts and empty prefixes remain incomplete. See
[M4 delivery](../docs/10-m4-delivery.md) for assumptions, completion semantics and
the M3 bridge. `python scripts/verify_m4.py --audit PATH` runs the complete checks;
`--check-report` verifies saved inverse sets, hashes and delivered paths.
Both Lean CI jobs rerun the full verifier and reject report drift.

[pie-evaluation.json](pie-evaluation.json) records M5's baseline
results, all reflex-level failures, source-analysis comparisons, Latin control,
evaluation splits, possible data leakage and acceptance criteria. The three
`pie-*-execution.json` files retain all 1,308 complete forward certificates and
310 inverse results. [pie-benchmark-local.json](pie-benchmark-local.json) records
the local 1,000-certificate performance measurement. [pie-review.json](pie-review.json)
explicitly records pending independent specialist review; M5 is **in review**.
See [M5 delivery](../docs/11-m5-delivery.md) for reproduction and limitations.
`verify_m5.py --require-complete` cannot pass without actual specialist sign-off.

[sino-tibetan-evaluation.json](sino-tibetan-evaluation.json) records M6's 100-set,
580-reflex Kuki-Chin study and 30 cross-branch dossiers. It retains every
unsupported result, mismatch, scoped inverse set and alternative analysis.
The three `sino-tibetan-*-execution.json` files contain 740 forward certificates,
199 finite-pool results and a bounded comparison of two whole paradigms.
[sino-tibetan-benchmark-local.json](sino-tibetan-benchmark-local.json) records
the 1,000-certificate measurement. The [specialist status](sino-tibetan-review.json)
remains pending. See [M6 delivery](../docs/12-m6-delivery.md);
`verify_m6.py --require-complete` enforces the outstanding review requirement.
