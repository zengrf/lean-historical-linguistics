# Verified comparative reconstruction in Lean

[![Checks](https://github.com/zengrf/lean-historical-linguistics/actions/workflows/ci.yml/badge.svg)](https://github.com/zengrf/lean-historical-linguistics/actions/workflows/ci.yml)

This project formalizes parts of the comparative method in Lean: the application
of ordered sound changes, the checking of alignments and correspondence
patterns, and reconstruction within a finite hypothesis space. It also contains
comparative data, a literature review and a retained research library for
Indo-European and Sino-Tibetan studies.

A checked derivation establishes a consequence of the specified rules. The
linguistic justification of those rules, the cognacy judgments and the source
readings requires separate assessment. See the [terminology and notation](docs/terminology.md)
and [formal architecture](docs/02-formal-architecture.md) for these distinctions.

## Current results

| Milestone | Implementation and evidence | Status |
| --- | --- | --- |
| [M0: literature and prototype](docs/06-research-method.md) | 132 references; 122 qualifying retained works; general proofs and counterexamples | Delivered |
| [M1: evidence](docs/07-m1-delivery.md) | Versioned schema; 60 CLDF imports; 38 valid and 44 invalid fixtures; six independently transcribed source entries | Delivered |
| [M2: sound changes](docs/08-m2-delivery.md) | Contextual rules and derivation certificates; 20 independently worked examples; 9,284 comparisons with a Python interpreter | Delivered |
| [M3: alignments and correspondences](docs/09-m3-delivery.md) | Row preservation and feasible correspondence partitions; 140 synthetic sites; 67,081 pair and 6,392 partition comparisons | Delivered |
| [M4: reconstruction](docs/10-m4-delivery.md) | Soundness and relative completeness for bounded search; 1,936 inverse sets; joint alternatives and incomplete searches | Delivered |
| [M5: Indo-European](docs/11-m5-delivery.md) | 200 IE-CoR cognate sets, 843 reflexes, a 20-set review sample, published analyses and a Latin control | Computational checks passed; specialist review pending |
| [M6: Kuki-Chin and cross-branch comparison](docs/12-m6-delivery.md) | 100 VanBik sets, 580 reflex records, a 50-set review core and 30 cross-branch dossiers; source-qualified paths and competing analyses | Computational checks passed; specialist review pending |

M1's source-entry review and M2's worked derivations were completed by separate
AI agents. They assess transcription and rule application. M5 requires a PIE
specialist's assessment of the linguistic analyses; its [review record](reviews/pie-signoff.md)
is pending. M6's [Sino-Tibetan specialist review](reviews/sino-tibetan-signoff.md)
is also pending. The M2–M4 test cases are synthetic.

The M5 correspondence baseline reproduces 1 of 79 supported test reflexes;
54 further test reflexes are unsupported by its transcription or rule model.
The report retains every mismatch and unsupported record, together with 1,308
forward certificates and 310 inverse results. It measures agreement with
published reference forms within a declared candidate pool.

## Documentation

The [expanded materials and hypothesis explorer](docs/13-materials-and-exploration.md)
provide access to 48,694 source form records: complete retained IE-CoR, Sagart
Sino-Tibetan and Burmish datasets, plus all 1,355 numbered VanBik entries. Select among
509 existing candidate-pool queries or supply a bounded reconstruction
specification; compare hypotheses, inspect checked derivations and test the
effect of withholding observations. This source coverage exceeds the executable
model coverage. Completeness always refers to the declared pool or bounded
word/analysis space.

| Document | Contents |
| --- | --- |
| [Literature review](docs/01-literature-review.md) | Comparative method, computational reconstruction, PIE, Sino-Tibetan and formal foundations |
| [Terminology](docs/terminology.md) | Definitions, notation and differences between source reconstruction systems |
| [Formal architecture](docs/02-formal-architecture.md) | Representations, semantics and theorem statements |
| [Case studies and evaluation](docs/03-case-studies-and-evaluation.md) | PIE and Kuki-Chin protocols, evaluation splits and review requirements |
| [Delivery plan](docs/04-delivery-plan.md) | Milestones, acceptance criteria and dependencies |
| [Prior art](docs/05-prior-art.md) | Pinned inspections of Lean libraries and related computational systems |
| [Research method](docs/06-research-method.md) | Source selection, reading scope, acquisition and access gaps |
| [Annotated bibliography](bibliography/README.md) | Source annotations, links and PDF locations |
| [Milestone register](data/milestones.json) | Machine-readable criteria and status |
| [Materials and hypothesis exploration](docs/13-materials-and-exploration.md) | Full source catalogue, hypothesis selection, enumeration, explanations, coverage gaps and proposed features |

## Library and proofs

- **127 PDFs, representing 122 qualifying distinct works**, retained locally: 5,184 pages and approximately 211 MB. Proposals, reviews/replies and a chapter already contained in a downloaded book do not count toward the 100-work floor. Five unsuccessful acquisitions are documented separately.
- **64 PDFs are included in this public repository** under their recorded redistribution terms. The other 63 are retained in the ignored local library. The manifest and fetcher preserve their original source locations; continued remote availability is not guaranteed.
- **132 annotated references**: 34 focused excerpt readings, 82 excerpt screenings, 10 visual excerpt readings, one decoded-abstract screening, two web-only excerpt readings and three access-gap notes. The reading notes identify the examined pages.
- **137 Lean theorem declarations**: 22 M0 results, five M1 evidence results, 17 M2 contextual-rule results, 35 M3 alignment/correspondence results, 48 M4 reconstruction/ambiguity results, six M5 case-study results and four M6 path/scope results. The audit permits Lean's standard logical axioms and rejects project axioms, proof placeholders and `native_decide`.

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
lake exe reconstruct --suite bounded-reconstruction
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
python scripts/build_m4_fixtures.py --check
python scripts/verify_m4.py --audit reports/lean-axioms-current.txt
python scripts/verify_m4.py --check-report
python scripts/verify_m5.py --audit reports/lean-axioms-current.txt
python scripts/verify_m5.py --check-report
python scripts/review_pie.py
python scripts/verify_m6.py --audit reports/lean-axioms-current.txt
python scripts/verify_m6.py --check-report
python scripts/review_sino_tibetan.py
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
lean/             Lean definitions, proofs, executables and dependency audit
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

The imported datasets and derived pilot records retain their source licenses; see [dataset attribution](data/THIRD_PARTY_NOTICES.md). M1 checks the representation and retention of these source records.
