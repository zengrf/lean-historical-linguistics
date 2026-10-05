# Verified comparative reconstruction in Lean

[![Checks](https://github.com/zengrf/lean-historical-linguistics/actions/workflows/ci.yml/badge.svg)](https://github.com/zengrf/lean-historical-linguistics/actions/workflows/ci.yml)

**Yes: Lean can formalize substantial parts of the comparative method and check reconstruction arguments under explicit assumptions.** It can verify derivations, correspondence constraints, bounded candidate reconstruction and ambiguity results. Establishing that a reconstruction describes an actual prehistoric language also requires empirical and philological judgments; a proof assistant does not remove those obligations.

This repository delivers a literature study, a retained research library, an executable proof of concept and a staged research plan for **Proto-Indo-European and Sino-Tibetan / Trans-Himalayan reconstruction**. The proof of concept uses synthetic examples. Source-backed linguistic case studies are specified future deliveries, not completed reconstructions.

**M1 is delivered:** a versioned evidence schema, Lean dossier checker, 38 valid and 44 adversarial fixtures, and reproducible imports of 60 records from pinned Indo-European and Burmish datasets. All four acceptance criteria pass. A separate AI agent independently transcribed the six required source entries; all match exactly. This source-entry review is not human or family-specialist sign-off. See [the review record](reviews/m1-independent-review.md), [delivery report](docs/07-m1-delivery.md) and [criterion-level status](reports/m1-delivery.json).

**M2 is delivered:** a total contextual-rule interpreter with explicit boundaries, both scan directions, simultaneous/feeding passes, substitution and deletion; a certificate checker with kernel-checked soundness and completeness; 25 valid and 88 adversarial fixtures; and 20 independently hand-worked AI review examples. Lean and a separate Python interpreter agree on 9,284 further forward cases. See [M2 delivery](docs/08-m2-delivery.md), [rule semantics](docs/rule-semantics.md) and [acceptance evidence](reports/contextual-rules.json). The packages are synthetic examples, not historically validated sound laws.

**M3 is delivered:** proved alignment preservation and correspondence-partition checking; 140 synthetic sites, including 125 incomplete and 20 conflicting; 49 accepted and 86 rejected fixtures; exact agreement with a Python evaluator on 67,081 column pairs and 6,392 partition proposals. Every site retains its group assignment, support and compatibility diagnostics. Results certify feasibility only. See [M3 delivery](docs/09-m3-delivery.md), [alignment/correspondence semantics](docs/alignment-correspondence-semantics.md) and [per-site evidence](reports/correspondence-sites.json).

## Start reading

| Document | Purpose |
|---|---|
| [Literature review](docs/01-literature-review.md) | Comparative method, prior computational systems, PIE, Sino-Tibetan, formal languages and uncertainty |
| [Formal architecture](docs/02-formal-architecture.md) | Representations, semantics, theorem contracts and the boundary between evidence and proof |
| [Case studies and evaluation](docs/03-case-studies-and-evaluation.md) | Concrete PIE and Kuki-Chin pilots, cross-branch dossiers, leakage controls and review gates |
| [Delivery plan](docs/04-delivery-plan.md) | Ten milestones, quantitative acceptance criteria, dependencies, staffing and decision gates |
| [Prior-art source audit](docs/05-prior-art.md) | Pinned Lean/mathlib/linglib source inspections and reuse opportunities |
| [Research and acquisition method](docs/06-research-method.md) | Reading depth, selection bias, access gaps, version handling and reproducibility |
| [M1 implementation and verification](docs/07-m1-delivery.md) | Evidence schema, CLI, real CLDF imports, tests and independent-review gate |
| [M2 implementation and verification](docs/08-m2-delivery.md) | Contextual rule semantics, proved trace checker, independent examples and adversarial tests |
| [M3 implementation and verification](docs/09-m3-delivery.md) | Row preservation, pairwise compatibility, distinct-unit support and feasible partitions |
| [Annotated bibliography](bibliography/README.md) | 132 source-specific annotations, original links, reading scope and PDF locations |
| [Milestone register](data/milestones.json) | Machine-readable delivery goals; M0–M3 delivered, M4–M9 planned |

## What is retained and checked

- **127 PDFs, representing 122 qualifying distinct works**, retained locally: 5,184 pages and approximately 211 MB. Proposals, reviews/replies and a chapter already contained in a downloaded book do not count toward the 100-work floor. Five unsuccessful acquisitions are documented separately.
- **64 PDFs are included in this public repository** under their recorded redistribution terms. The other 63 are retained in the ignored local library. The manifest and fetcher preserve their original source locations; continued remote availability is not guaranteed.
- **132 annotated references**: 34 focused excerpt readings, 82 excerpt screenings, 10 visual excerpt readings, one decoded-abstract screening, two web-only excerpt readings and three access-gap notes. This is not a claim to have read 5,184 pages cover to cover.
- **79 Lean theorem declarations**: 22 M0 results, five M1 evidence results, 17 M2 contextual-rule results and 35 M3 alignment/correspondence results. The audit permits Lean's standard logical axioms and rejects project axioms, proof placeholders and `native_decide`.

The [full local acquisition audit](reports/library-audit.json) records actual hash and page-count checks. Public CI validates the public PDFs and the acquisition ledger; it cannot verify copies absent from a public checkout. See [verification records](reports/README.md).

## Reproduce the current checks

Use Python 3.12 and a Lean installation managed by [elan](https://github.com/leanprover/elan). The project has no external Lean package dependency.

```bash
git clone https://github.com/zengrf/lean-historical-linguistics.git
cd lean-historical-linguistics
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/verify_library.py
python scripts/check_plan.py
python scripts/build_catalogue.py
git diff --exit-code -- bibliography/README.md bibliography/references.bib library/THIRD_PARTY_NOTICES.md
```

```bash
cd lean
lake build
lake env lean Audit.lean > ../reports/lean-axioms-current.txt
python ../scripts/check_proofs.py ../reports/lean-axioms-current.txt
lake exe dossier_check data/pilots --strict
lake exe verify_dossiers --suite contextual-rules
lake exe correspondence_check --suite correspondence-sites
cd ..
python scripts/verify_m1.py
python -m unittest discover -s tests -v
python scripts/review_m1.py --require-complete
python scripts/verify_m1_delivery.py --require-complete
python scripts/build_m2_fixtures.py --check
python scripts/verify_m2.py --audit reports/lean-axioms-current.txt
python scripts/verify_m2.py --check-report
python scripts/build_m3_fixtures.py --check
python scripts/verify_m3.py --audit reports/lean-axioms-current.txt
python scripts/verify_m3.py --check-report
```

The default toolchain is pinned in [lean-toolchain](lean/lean-toolchain). CI builds Lean **4.19.0 and 4.34.1** independently. The original local build used 4.19.0 because the 4.34.1 binary did not run on the host's macOS 10.15. If you need that compatibility path, replace `lake` with `lake +leanprover/lean4:v4.19.0` in each Lean command. CI results, rather than local compatibility claims, establish the newer-toolchain build status.

To attempt to restore the complete acquired library from its original sources:

```bash
python scripts/fetch_library.py --available --workers 4
python scripts/verify_library.py --local
```

The fetcher skips matching cached PDFs, verifies acquired bytes against the recorded hashes, and fails on changed content or inaccessible sources. It writes a local fetch report without changing the committed acquisition snapshot. `--record` is an explicit maintenance operation for updating that snapshot after review. `--ids ID1 ID2` selects particular sources. Scanned PDFs may have little extracted text; the originals remain the reference.

## Repository layout

```text
bibliography/     Curated source metadata, reading notes, hashes and BibTeX
data/             Milestones, synthetic fixtures, pinned CLDF snapshots and imported pilots
docs/             Literature synthesis, formal design and research protocols
lean/             Compiling proof-of-concept library and theorem audit
library/open/     Unmodified PDFs approved for public redistribution
library/downloads/ Local retained PDFs; ignored by Git
library/text/     Local extracted text; ignored by Git
library/metadata/ Local discovery/fetch records; ignored by Git
reports/          Acquisition and proof verification records
reviews/          Independent source-entry and hand-worked semantics review records
schema/           Versioned evidence format and migration policy
scripts/          Retrieval, catalogue generation and validation
```

Original code and documentation use the [MIT license](LICENSE). Third-party publications retain their own copyright and licenses; consult [the individual notices](library/THIRD_PARTY_NOTICES.md) before reuse. The acquisition and literature cutoff is **5 October 2026 UTC**.

The imported datasets and derived pilot records retain their source licenses; see [dataset attribution](data/THIRD_PARTY_NOTICES.md). The M1 representation pilot is not a verified PIE or Proto-Sino-Tibetan reconstruction.
