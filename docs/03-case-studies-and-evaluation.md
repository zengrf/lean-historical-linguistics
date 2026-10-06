# Case studies and evaluation protocol

Status: the acceptance protocol below remains in force. M5 now has a [source-backed computational pilot](11-m5-delivery.md), including frozen evaluation, explicit failures and a separate Latin control. Its independent PIE-specialist review is pending; it is not linguistically validated. M6 remains planned. The earlier formal-contract fixtures remain synthetic.

M1 now imports 60 real Indo-European/Burmish records for representation and provenance testing. These are not the M5/M6 reconstruction benchmarks; see [M1 scope and status](07-m1-delivery.md).

## 1. Three different evaluation questions

| Question | Evidence | Success does not establish |
|---|---|---|
| Is the checker correct for its semantics? | General Lean theorems; axiom audit | Historical correctness of the semantics or inputs |
| Does the system reproduce a published analysis? | A source-backed dossier with exact assumptions | That the published analysis is uniquely right |
| Does the analysis generalize or discriminate alternatives? | Frozen held-out observations; expert review; sensitivity analysis | Certainty about unobserved prehistoric reality |

Record the denominator for every metric. Count cognate sets, roots, word occurrences, segments and languages separately. Report rejected imports, excluded forms, missing evidence and unresolved cases. Scores must include the counts and reasons for exclusions.

## 2. A research dossier

Every pilot dossier must include:

1. Bibliographic source and exact page/table/entry, plus data license and release hash.
2. Original forms, normalized forms, normalization rules, variety/stage IDs and dates or explicit unknowns.
3. Attestation status, source uncertainty, glosses, morphology and candidate cognate links.
4. A named reconstruction system and inventory, including unresolved phonetic interpretation.
5. A scoped rule cascade and relative chronology, including analogical/borrowing explanations when invoked.
6. Expected intermediate and final forms, surviving alternatives and unexplained observations.
7. A certificate and the exact theorem connecting its acceptance to the model.
8. Split membership, independent reviewer decisions and disagreements.

Keep conflicting editorial judgments as parallel records. Reviewer agreement is evidence about the annotation process, not a theorem about the past.

## 3. Synthetic and attested-ancestor controls

### Synthetic histories

Generate small histories using the **reference semantics**, freeze their seeds and keep their latent ancestors. Vary mergers, deletions, missing forms, contexts and rule order. Include a deliberately different generator to test whether evaluation merely rewards the system's own inductive bias.

Adversarial cases must include an incorrect intermediate step, omitted rule, extra rule, reversed chronology, unsupported segment, wrong language ID, malformed alignment, a merger-induced ambiguity, missing-versus-gap confusion, coindexed alternatives and an empty-data case. Report when absent observations leave the candidate set unconstrained.

### Attested ancestors

Use a pinned Romance dataset or a small source-backed Latin-to-daughter cascade as an external control. Split by etymological root and paradigm family, not random individual inflections. Retain the distinction between learned borrowings, inherited forms and the selected historical Latin variety. Withholding written Latin provides a useful test target but is not an exact simulation of reconstructing PIE or Sino-Tibetan.

The first release should provide a sound-law baseline and a simple alignment/correspondence baseline. Neural or LLM experiments are optional after these are reproducible.

## 4. PIE pilot

### Stage A: 20 reviewed comparative sets

Select 20 sets across at least three branches and 60 source-backed reflex records. Begin with relatively secure inherited material; preserve documented problematic cases separately. Each set must have at least two independent daughter branches represented. Record any published reconstructed protoform as a claim rather than as an attested observation.

Use a restricted Germanic chronology dossier drawn from Ringe's discussion in the Olander volume and relevant source works. Verner-type conditioning requires inherited accent at the correct stage. An implementation of Grimm's Law must state the conditioning environments, consonant series and target stage; `p → f` alone is insufficient.

For laryngeals, compare source-defined treatment of initial laryngeals in Anatolian. The pilot is allowed to return ambiguity about phonetic realization. Attribute each interpretation to its source.

### Stage B: 200 sets / at least 600 reflex records

Increase coverage only after Stage A's schema and rule semantics stabilize. Use at least five branches where the chosen evidence supports this. Preserve morphology, loans, alternative cognacy and disputed forms. A source-backed IE-CoR import may help select sets, but its cognacy annotations do not automatically supply the required protoforms or chronological sound laws.

Include three morphology dossiers: a source-defined nominal ablaut paradigm, one analogical change, and competing hi-conjugation analyses. The last may remain a comparison of unresolved predictions rather than a single accepted reconstruction.

### Pass criteria

- All included records have source locators and explicit attestation/reconstruction status.
- Every claim of successful derivation has an accepted certificate.
- Every mismatch is retained and classified, including “unresolved.”
- Every source-supported derivation within the implemented fragment is reproduced, or a documented transcription/specification disagreement blocks release.
- At least two alternative analysis packages can be run on the same frozen evidence without changing it.
- A specialist independent of the encoding reviews the 20-set core and all disputed dossiers before the pilot is labeled linguistically validated.

No numerical accuracy threshold is specified. Failed reproduction may reveal omitted conditioning or transcription errors. Acceptance requires a complete account of the results and an explanation of failures.

## 5. Sino-Tibetan / Trans-Himalayan pilot

### Stage A: Proto-Kuki-Chin, 50 comparative sets

Choose 50 sets and at least 150 reflex records from VanBik, with exact page/entry references, after checking consistency of subgroup level and transcription. Annotate whether a protoform belongs to Kuki-Chin, Central Chin, Northern Chin or another level. Use Button as a comparison source where appropriate, preserving its different scope and assumptions.

Begin with subgroup reconstruction. The coverage targets specify the sample size; individual comparisons may admit several reconstructions.

### Stage B: 100 subgroup sets and 30 cross-branch dossiers

Expand to 100 subgroup sets / at least 300 reflex records. Add a Burmish dataset only after pinning its source and reviewing its own transcription/label conventions. Keep its results separate from Kuki-Chin summary statistics.

Build 30 small cross-branch dossiers covering the following themes where sufficient evidence exists: *sr-* correspondences, Tibetan *wa* and secondary syllable fusion, Tibetan stem alternations, Old Chinese prefix voicing, departing-tone derivation and tone/coda interactions. At least 10 should retain competing analyses or explicitly unresolved outcomes. If the available published material does not support the target count, report the shortfall and identify the unsupported comparisons.

Old Chinese records must distinguish written character evidence, rhyme/phonetic-series evidence, Middle Chinese transcription, and the selected Old Chinese reconstruction. A phonological value from Baxter-Sagart is an analysis-layer value, even when the corresponding written word is ancient.

### Pass criteria

- The same provenance and certificate standards as the PIE pilot.
- No silent equivalence between PTB and PST/Trans-Himalayan nodes.
- Tone, missing values, unknown readings and gaps round-trip through the import/export path.
- Alternative prefix and suffix analyses preserve linked choices across a paradigm.
- Comparison reports identify evidence that discriminates models and evidence that does not.
- A Sino-Tibetan specialist reviews the 50-set core and cross-branch dossiers before linguistic validation is claimed.

## 6. Splits and leakage controls

Store a split manifest before fitting or tuning. Group all reflexes, variants, compounds sharing the tested root where relevant, and paradigm cells of a lexical family into one split. Publish the grouping rule. Use approximately 60/20/20 train/development/test proportions only when sample size makes all partitions meaningful; otherwise use nested, grouped cross-validation and publish its folds.

Keep family transfer separate from within-family prediction. A held-out language tests a different generalization problem from a held-out cognate set. Data used to devise or edit rules cannot also be presented as a blind historical prediction test. Pseudo-prospective withholding of a once-unknown language is illustrative unless the analysis genuinely avoids later knowledge; a modern model already informed by Hittite cannot recreate the original laryngeal discovery experiment just by masking a column.

For LLM proposals, document potential training-data contamination. Include unseen synthetic histories with known structure and preserve the full generation/checking log. Report whether prior exposure to the evaluation data can be excluded.

## 7. Metrics and baselines

| Component | Metrics | Baselines / comparisons |
|---|---|---|
| Imports | Valid/invalid counts; lost distinctions; coverage | Original source and independent transcription sample |
| Alignment | Structural validity; declared objective; expert agreement | Simple edit alignment; LingPy-style alignment |
| Cognacy | Precision/recall and clustering measures; partial-cognacy errors | LexStat; reviewed source annotations |
| Forward derivation | Exact reflex accuracy; normalized edit distance; failure types | Published cascade; no-change baseline |
| Reconstruction | Candidate-set recall relative to reference analyses; size; top-k agreement; ambiguity rate | Finite enumeration; correspondence-based model |
| Model comparison | Shared fits; discriminating observations; assumption changes | Competing published systems |
| Phylogeny, if included | Topological comparison and sensitivity to coding/priors | Cognate-based and correspondence-based inputs separately |
| Engineering | Build time; checker latency; memory; certificate size | Reference interpreter versus verified optimization |

Report both coverage and informativeness: an empty candidate set rejects the tested hypotheses, while a large set may provide little discrimination. Evaluate feature distance only with a fixed, documented feature system and handle ambiguous reference forms as sets.

Statistical uncertainty should resample at the unit actually independent enough for the claim—usually sets or lexical families, not individual segment tokens. Report paired differences and intervals where justified. Small pilot results are descriptive; they should not be used to claim universal superiority.

## 8. Reproducibility and release acceptance

Archive configurations, code commits, source and dataset hashes, rule-package versions, split files, random seeds, certificates, predictions and error tables. A clean checkout must rebuild every claimed theorem and reproduce deterministic pilot outputs. Performance measurements require a declared machine and timeout.

The first pilot performance target is an engineering budget: on a documented ordinary laptop, check 1,000 bounded certificates in under 60 seconds with peak memory under 2 GB. If this fails, publish the result and optimize before increasing scope; it is not a scientific accuracy threshold.

CI establishes that the specified proof and software checks pass. Specialist review separately assesses the linguistic evidence and analyses.
