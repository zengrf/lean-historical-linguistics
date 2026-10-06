# M6: Kuki-Chin and cross-branch comparisons

M6 is **computationally checked, linguistically unreviewed**. The engineering artifacts are implemented. The original `M6-core` and `M6-signoff` requirements remain open until an independent human specialist assesses the 50 core sets and 30 cross-branch dossiers. The [evaluation report](../reports/sino-tibetan-evaluation.json) records each criterion separately.

## Source sample and scope

The [Kuki-Chin corpus](../data/kuki-chin/corpus.json) contains 100 sets and 580 reflex records, including a designated core of 50 sets and 298 records. Selection proceeds through VanBik's initial-consonant subsections in printed order. Eligible sets carry a PKC reconstruction and at least three distinct source varieties in at least two of his Peripheral, Central and Maraic groups. Repeated source rows remain visible.

The PDF, entry number, page, extracted spelling and exact variety label accompany every record. Source discussion and possible-loan flags point back to the complete entry. Broken punctuation, uncertain glyphs, stem alternations, optional segments and allofams are retained. PDF extraction is not independent transcription review.

The [30 cross-branch dossiers](../data/cross-branch/dossiers.json) cover *sr*, Tibetan *wa* and syllable fusion, Tibetan morphophonology, Old Chinese prefixes and suffixes. They distinguish written evidence, scholarly transcription and reconstruction. They preserve unresolved comparisons, a rejected etymology and grammatical comparisons whose lexical roots are not cognate. The source pages and attribution limits are recorded beside each claim.

The terminology pass preceded implementation in commit `1e95645`. It followed the repository's primary sources; [terminology readings](../bibliography/terminology-readings.json) and the [editorial record](../reports/editorial-review.json) identify its scope. M6's source arguments and selected pages are recorded in the cross-branch source register.

## Formal and executable contract

[SourceScope.lean](../lean/Historical/SourceScope.lean) indexes sound-change paths by source-qualified endpoints. It proves composition, associativity and preservation of candidate filtering when two paths have identical predictions. The shared [Batch.lean](../lean/Historical/Batch.lean) retains M5's execution semantics. The project now has 137 audited theorem declarations, including four new scope/path results.

`sino_tibetan_check` strictly decodes the batch, validates package endpoints and rejects inverse queries that mix source ancestors or attach an observation to another variety. Source labels are declarations supplied by the encoder; the checker does not authenticate publications or establish their historical truth.

The lexical experiment compares an identity baseline and a training-only substitution/deletion baseline. Tokens are transcription graphemes. Tone marks remain in the evidence and normalization record but are excluded from this segmental score. Unmarked tone never becomes a zero tone. Named stem cells must correspond; all required cells must match for a multi-cell record to count as exact.

Source-defined exercises separately reproduce initial correspondences, relative chronology and specified morphological effects. They include the broad versus restricted *sr* condition, early *wa > o* before later nominal fusion, pre-Tibetan mergers and possible sources of Chinese final *s*. A projection can fit while a complete lexical history remains unexplained. Some dossiers are documentary because the required philology or morphology is not supplied by the current rule language.

The two whole-paradigm analyses of Chinese transitive/intransitive voicing yield two distinct candidates in a six-hypothesis bounded onset test. The result preserves their observational equivalence on the supplied p/b contrast. It does not choose the historically correct derivational direction.

## Evaluation and sensitivity

Commit `2ed6130` freezes the corpus, source dossiers, family splits and study design before fitted models appear. Family grouping runs across all parsed chapter-4 entries, conservatively joining shared stems, compound components, explicit cross-references and repeated spellings. Unrecorded relations still require specialist checking.

All 580 reflex records remain in the outcome table. The report distinguishes unsupported records, mismatches and exact transcription matches, with both conditional accuracy and total-source coverage. Inverse search is complete within declared pools of published reference forms, including held-out labels. This is retrospective closed-set retrieval, not blind discovery.

The 69 lexical families divide into 41 training, 14 development and 14 test families. They contain 359, 144 and 77 reflex records respectively. Of the 580 records, 297 support the specified segmental comparison and 283 remain unsupported. There are 579 distinct set/variety/form triples: one identical source row is repeated and remains visible.

| Baseline and split | Exact / supported reflexes | All source reflexes | Reference recalled / full-coverage inverse queries |
| --- | --- | --- | --- |
| Identity, train | 51 / 184 | 359 | 3 / 46 |
| Correspondence, train | 76 / 184 | 359 | 4 / 46 |
| Identity, development | 16 / 60 | 144 | 1 / 15 |
| Correspondence, development | 19 / 60 | 144 | 0 / 15 |
| Identity, test | 16 / 53 | 77 | 0 / 13 |
| Correspondence, test | 15 / 53 | 77 | 0 / 13 |

The learned baseline does not improve test accuracy. Its 15 exact matches cover 19.5% of all test records; 24 test records remain unsupported. Neither model recovers the reference in the 13 full-coverage test inverse queries. These failures delimit the present transcription and morphology model; they are not evidence against the comparative method.

Sensitivity checks remove observations while keeping the ancestor and rules fixed; every previously compatible candidate must remain. Coverage under VanBik's and Button's differently scoped groups is reported separately, including the provisional identification of Falam/Zahao with Button's Zahau. These coverage comparisons do not convert one author's protoforms into another author's reconstruction.

A polytomy and a tree with a TB node allow different placements of a proposed shared change. Rebracketing with unchanged composed branch functions leaves predictions unchanged, as the Lean theorems establish. The implementation does not estimate the Sino-Tibetan tree. Additional comparative and philological evidence is needed to distinguish the unresolved source accounts.

Removing observations changes one of the 50 paired inverse results. All original candidates remain compatible. The separate merger control retains both `ndz` and `dz`, and the voice-paradigm control retains both complete analyses. The source-fragment batch has 40 matching projections and six intentionally retained counterexamples across 46 forward jobs; these counts are engineering checks, not an etymological accuracy score.

## Verification and review

The full verifier compares every Lean forward trace and complete inverse set with the separate Python interpreter. It also checks M1 round trips, all 50 M3 display alignments, the joint-paradigm enumeration, strict-input counterexamples, split provenance, benchmark bounds and artifact hashes. A fresh-process benchmark checks 1,000 certificates with the largest lexical package against the 60-second and 2-GiB limits.

The checked artifacts contain **740 forward certificates, 199 finite-pool queries and four branch certificates for the two joint-paradigm candidates**. All agree with the Python interpreter. The 14 executable rejection cases include changed source levels, incorrect varieties, missing scopes, duplicate keys and unbound paradigm choices. The repository's 80 Python tests include 13 M6 tests for normalization, leakage, missing outcomes, lost ambiguity and corrupted traces.

The recorded local benchmark checks 1,000 five-token certificates with 22 rules each in approximately **1.79 seconds and 47 MiB** on Darwin x86_64. CI measures its own runners separately.

```bash
python scripts/build_kuki_corpus.py --check
python scripts/build_sino_tibetan_sources.py --check
python scripts/build_m6_experiment.py --check
cd lean
lake build
lake env lean Audit.lean > ../reports/lean-axioms-current.txt
cd ..
python scripts/verify_m6.py --audit reports/lean-axioms-current.txt
python scripts/verify_m6.py --check-report
python scripts/review_sino_tibetan.py
python -m unittest discover -s tests -v
```

The compatibility toolchain is `lake +leanprover/lean4:v4.19.0`; CI also runs the pinned 4.34.1 version. `--check-report` checks saved results and hashes without claiming a fresh Lean execution.

The [review packet](../reviews/sino-tibetan-packet.json) binds all source inputs and execution records. [Specialist sign-off](../reviews/sino-tibetan-signoff.md) is pending. Both `python scripts/verify_m6.py --require-complete` and `python scripts/review_sino_tibetan.py --require-complete` fail while that requirement remains unmet. An unresolved historical question can be an accepted research result; an absent review or an unresolved objection to release cannot pass the gate.
