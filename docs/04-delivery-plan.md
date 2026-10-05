# Delivery plan with verifiable goals

This is a research-and-engineering plan, not a promise that a complete prehistoric language will be recovered. **M0–M4 are delivered; M5–M9 are planned.** Separate AI reviewers completed M1's source-entry gate and M2's independent hand-worked examples; specialist review of historical analyses remains part of the later case studies. The machine-readable register is [milestones.json](../data/milestones.json). M1–M4's checkers and verification commands now exist; commands named for later modules remain acceptance-interface specifications.

## 1. Intended research contribution

Deliver a Lean library and accompanying comparative datasets that support:

1. Verified execution of a restricted sound-law language and independent checking of derivation certificates.
2. Validated alignments and correspondence-group certificates.
3. Sound and complete reconstruction **relative to an explicit finite hypothesis space**.
4. Explicit alternative analyses, counterexamples and identifiability limits.
5. Source-backed PIE and Sino-Tibetan subgroup dossiers, with independently reviewed empirical claims.
6. Reproducible interfaces for expert, statistical, constraint-based and neural proposal systems.

The first publishable result could be the semantics and certificate checker plus two carefully delimited comparative dossiers. The full program should not be held hostage to solving all of PIE morphology or a unified Proto-Sino-Tibetan phonology.

## 2. Milestones

| ID | Delivery and dependencies | Acceptance evidence | Planned effort |
|---|---|---|---|
| **M0** | Literature corpus, synthesis, proof-of-concept and public repository | At least 100 distinct qualifying retained works; checksums; annotated catalogue; general theorem and counterexample build; public CI | Delivered |
| **M1** | Data contract and provenance; depends on M0 | Schema, 38 valid / 44 adversarial fixtures, lossless source retention, CLDF adapter and 60 real imported records. Six source entries independently checked by a separate AI agent, with exact agreement. | Delivered; original estimate 3–5 engineer-weeks + review |
| **M2** | Restricted contextual rule semantics and trace checker; depends on M1 | Total interpreter; explicit pass conventions; 17 new theorems including checker soundness/completeness; 25 valid / 88 adversarial fixtures; 20 independently hand-worked AI examples; 9,284 further comparisons | Delivered; original estimate 5–8 engineer-weeks |
| **M3** | Alignment and correspondence verification; depends on M1–M2 | 35 new theorems; feasible partition checker; 140 synthetic sites, including 125 incomplete / 20 conflicting; 135 fixtures; 67,081 pair and 6,392 partition comparisons | Delivered; original estimate 4–6 engineer-weeks |
| **M4** | Bounded inverse reconstruction and alternatives; depends on M2–M3 | 48 new theorems; explicit finite models/word bounds; 1,936 exact inverse sets across 16 cascades; linked alternatives and incomplete searches retained; 82 fixtures | Delivered; original estimate 4–7 engineer-weeks |
| **M5** | PIE case study; depends on M1–M4 | 20-set reviewed core expanding to 200 sets / 600 reflex records; named rule packages; chronology and morphology dossiers; frozen evaluation and independent sign-off | 6–10 engineer-weeks + 6–10 specialist-weeks |
| **M6** | Sino-Tibetan subgroup and cross-branch study; depends on M1–M4 | 50-set reviewed Kuki-Chin core expanding to 100 sets / 300 reflex records; 30 cross-branch dossiers; competing analyses and unresolved outcomes preserved | 8–12 engineer-weeks + 8–12 specialist-weeks |
| **M7** | Verified optimization and external proposers; depends on M2–M6 | Proved compilation for a restricted fragment; one deterministic baseline and one external proposer; all reported accepted outputs carry certificates; benchmark logs | 6–10 engineer-weeks |
| **M8** | Morphology, analogy and contact extension; depends on M5–M7 | Paradigm-aware derivations; typed borrowing/analogy witnesses; 20 reviewed cases; failure to establish a unique history explicitly represented | 6–10 engineer-weeks + specialist review |
| **M9** | Research release and optional probability module; depends on M7–M8 | Clean-environment reproduction; artifact archive; paper with precise claims; uncertainty evaluation. Optional finite rational posterior theorem if pursued | 4–8 engineer-weeks |

Effort estimates are planning ranges, not measured productivity or cost quotations. Some data work can proceed alongside proof work; one person cannot simply add nominal parallelism to shorten the schedule.

## 3. What “done” means for each milestone

### M0: current delivery

- The download ledger records bytes, page counts, canonical/source URLs and SHA-256 hashes. A local audit reopens PDFs and verifies their bytes.
- The count excludes failed acquisitions, the research proposal, reviews/reply, and the chapter already included in a downloaded book. Repeated files or versions do not raise the threshold.
- Source-specific reading notes identify focused passages, abstract/conclusion screening, visual inspection or access gaps. There is no claim that 100 books were read cover to cover.
- The Lean prototype proves general properties and synthetic counterexamples. The theorem audit names the logical dependencies.
- GitHub contains the code, study, manifests and explicitly redistributable PDFs. Other retained copies remain in the ignored local research library; the fetcher can attempt their original URLs.

Reproduce the current checks using [the README](../README.md). A public checkout's audit checks the public files and the structure of the acquisition ledger; it cannot attest to private files it does not contain. `--local` checks the full retained collection.

### M1: representation is a deliverable

Create a schema version and a migration policy. Every imported record must have a stable ID, source, original form, representation type and attestation status. No source is silently normalized into a preferred reconstruction. Twenty deliberately invalid cases must be rejected for the intended reason; the valid set must include tone, combining characters, multiple meanings, multiple variants and linked alternatives.

Implemented acceptance command, run from `lean/`: `lake exe dossier_check data/pilots --strict`. It prints counts and fails on broken source references, duplicate primary IDs and unrecorded normalizations. Independent double-entry checking must cover at least 10% of imported core forms and all records whose OCR or glyph interpretation is uncertain. A separate AI reviewer completed the six-entry sample (10% of 60), with exact Unicode agreement and no discrepancies; there are no flagged imported readings. See [M1 delivery and verification](07-m1-delivery.md) and the [review's method and limits](../reviews/m1-independent-review.md).

### M2: prove the specified semantics

Publish a small grammar for the rule language. State the semantics of matching, word boundaries, context, pass direction, rule order and deletion. Include examples that distinguish simultaneous from feeding application. Prove that the checker accepts exactly the traces licensed by the semantics. Report the trusted axioms of every public theorem.

Implemented acceptance commands: `lake build Historical.Rules Historical.Certificates` and `lake exe verify_dossiers --suite contextual-rules`. The restricted grammar rejects unchecked word-specific substitutions, hidden lexical lookups and arbitrary callbacks. See the [published semantics](rule-semantics.md), [M2 delivery and verification](08-m2-delivery.md), and [criterion-level evidence](../reports/contextual-rules.json). Independent AI hand-work checks all 20 examples against the prose semantics; it does not provide historical or family-specialist validation.

### M3: verify structure before optimizing

Prove row preservation when removing alignment gaps. Verify correspondence groups pairwise, with no positive support from missing cells. Give counterexamples for treating compatibility as transitive. A minimum-cover claim is optional; if made, add a checked optimality certificate. The first 100-site suite must include at least 20 incomplete and 10 conflicting sites.

Acceptance artifact: a report listing every site's assigned group, support and compatibility outcome, with a theorem-backed validity result. A heuristic score alone fails this milestone.

Implemented commands: `lake exe correspondence_check --suite correspondence-sites` and `python scripts/verify_m3.py --audit PATH` after a fresh build/audit. The [M3 delivery](09-m3-delivery.md) and [per-site report](../reports/correspondence-sites.json) document all four passing criteria. The implementation accepts feasibility-only claims and rejects unsupported optimality. Distinct evidence-unit labels prevent repeated positions from inflating support; their historical independence is an empirical assumption. The current suite is synthetic and does not replace M5/M6 review.

### M4: finish the bounded inverse problem

Declare inventory size, maximum protoform length and any bound on rule/model choices. Prove enumeration covers precisely the declared space. Prove each returned candidate fits and each fitting in-scope candidate is returned. Prove that observationally equivalent hypotheses cannot be distinguished by the selected observations. Return alternatives, not an arbitrary selected winner.

Check the algorithm against exhaustive enumeration on all words of length at most four over a three-symbol alphabet for at least ten small cascades. This finite comparison detects implementation mistakes; the general Lean theorems establish the contract beyond that test domain. A timeout must be reported as incomplete search, never as “no ancestor.”

Implemented commands: `lake exe reconstruct --suite bounded-reconstruction` and
`python scripts/verify_m4.py --audit PATH` after a fresh build/audit. All 1,936
inverse sets agree over 121 words and 16 cascades, with 234,256 membership
decisions and 121 fixed-model observation-refinement checks. The 82 authored
fixtures cover complete, incomplete and invalid queries. See [M4 delivery](10-m4-delivery.md)
and [exact inverse-set evidence](../reports/exhaustive-small-domain.json).
Completeness remains relative to the declared finite space and supplied models;
these synthetic checks do not close the empirical M5/M6 gates.

### M5 and M6: validated linguistic dossiers

Follow the detailed [case-study protocol](03-case-studies-and-evaluation.md). Deliver the small independently reviewed core before scaling. Store all failures and disagreement records. Require a reviewer with the relevant family expertise who did not perform the original encoding. If specialist review is unavailable, label the release **computationally checked, linguistically unreviewed**; do not mark this gate passed.

The evidence must include multiple source-defined analysis packages. A successful outcome may show that two theories fit the same data, or that the selected sources do not support a proposed law. Those are legitimate results. Inventing extra etymologies or dropping contradictions to meet a numerical target is not.

### M7: optimize behind a fixed contract

Benchmark the reference interpreter before optimization. A finite-state compiler must come with a semantics-preservation theorem for a precisely stated fragment. An external proposer can be a solver or a statistical/neural system; its outputs are inputs to the verified checker. Candidate-generation success, certificate acceptance and reference-analysis agreement must be separate columns in the report.

Target: 1,000 bounded certificates checked in under 60 seconds and under 2 GB peak memory on a documented ordinary laptop. If the target fails, publish the profile and limit supported batch size until addressed. Do not introduce unsound shortcuts to meet the time limit.

### M8: explain apparent exceptions

Add morphemes, paradigm cells and typed historical mechanisms. An analogy witness must specify the model and affected paradigm relation; a borrowing witness must specify donor/recipient stages and the adaptation analysis. Twenty reviewed cases must include at least five competing explanations. Keep phonological failure visible when an alternative mechanism is proposed.

Arbitrary syntax and unrestricted semantic reconstruction remain outside the committed core. A later syntax project requires a separate definition of comparable units and suitable evidence; grammar-tree transformations alone do not supply that foundation.

### M9: independent reproduction and publication

Produce a tagged release with an artifact manifest, frozen data/rule/split versions and one-command reproduction. Have a second environment and a second person reproduce the main theorem and case-study results. Prepare a paper that distinguishes mathematical correctness, empirical reproduction, prediction and methodological interpretation.

An optional finite rational probability module may prove posterior normalization and calculation for a small model. It must separately assess calibration and sensitivity. Infinite weighted models, global historical identifiability and proof of a homeland are not promised deliverables.

## 4. First twelve weeks

| Weeks | Focus | Reviewable endpoint |
|---|---|---|
| 1–2 | Resolve source/data permissions; choose exact inventories, varieties and two small dossiers | A signed-off scope note, 10 PIE sets and 10 Kuki-Chin sets transcribed with sources |
| 3–4 | Schema, normalization and CLDF adapter | M1 fixtures, validation report and reviewed mappings |
| 5–6 | Restricted interpreter and chronology | Executable examples with all intermediate stages |
| 7–8 | Certificate reflection and adversarial tests | M2 theorem audit and failure diagnostics |
| 9–10 | Alignment validity and correspondence groups | First M3 site report; no unsupported transitive grouping |
| 11–12 | Bounded candidate reconstruction on the small dossiers | A vertical-slice release with explicit ambiguity and a plan adjustment based on observed effort |

This schedule targets a vertical slice, not completed 200-set and 100-set pilots. A single developer unfamiliar with Lean or historical linguistics should lengthen it substantially.

## 5. Staffing and cost model

A realistic starting team is one full-time Lean engineer/researcher, a PIE specialist and a Sino-Tibetan specialist each contributing roughly one day per week, and limited data-engineering support. For that team, **12–18 months** is a reasonable planning envelope for M1–M9's core; novel transducer proofs, difficult morphology or unavailable specialist time can extend it. One person developing both disciplinary expertise and infrastructure should plan for a longer research project.

Budget primarily for time. The core checker and small pilots should run on a laptop. GPU work is optional and should be budgeted only after deterministic baselines establish a reason for it. Use local salary/day rates to price roughly 46–76 engineer-weeks plus specialist and annotation time; no fabricated dollar estimate is needed.

## 6. Decision gates and failure handling

| Risk or observation | Gate / response |
|---|---|
| Too many source forms cannot be normalized faithfully | Stop scaling; repair representation or narrow the pilot |
| A rule semantics cannot express an essential case | Document the counterexample and add a separately specified extension |
| All hypotheses fit because the rule language memorizes words | Restrict the model class and require held-out tests |
| Too few hypotheses survive because a preferred theory was hard-coded | Compare named alternatives and audit exclusions |
| A transducer optimization is hard to verify | Retain the reference checker and defer optimization |
| A tree assumption drives a cross-branch reconstruction | Run sensitivity across defensible topologies; retain conditional conclusions |
| Morphological segmentation controls a result | Preserve rival segmentations and expose their different predictions |
| Experts disagree | Publish both annotations and the concrete disagreement |
| A paper or dataset cannot be acquired or redistributed | Record the gap; retain lawful local copies and public metadata; substitute an appropriate source only with explicit rationale |
| Current dependencies break | Use pinned releases and an explicit migration branch |

## 7. Research questions worth publishing even with negative answers

- How much of a published sound-law account can be expressed without hidden lexical exceptions?
- Which reconstruction distinctions are identifiable from a fixed set of daughter observations?
- How much ambiguity is introduced by missing data, alignment choice or correlated protoform alternatives?
- Which disagreements are empirical, and which merely use different equivalent notations?
- Can a certificate interface expose mistakes in existing reconstruction pipelines without recreating their search algorithms?
- Does an explicit representation of morphology and borrowing reduce apparent sound-law exceptions on independently reviewed cases?

The project succeeds by making these questions answerable with inspectable evidence, not by maximizing the number of theorem names or forcing a single reconstruction.
