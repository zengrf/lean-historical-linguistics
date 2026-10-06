# M5: source-backed Indo-European pilot

**The computational implementation is complete; M5 remains `in_review`.**
Its independent family-specialist review is not supplied by the implementation.
The release label is **computationally checked, linguistically unreviewed**.
The original five acceptance conditions remain unchanged.

| Criterion | Current evidence and status |
| --- | --- |
| M5-core | 20 source-backed comparative sets, 161 reflexes, exact locators, normalization/uncertainty, all baseline attempts and failures; independent review pending |
| M5-scale | 200 cognate sets and 843 distinct source form rows, spanning ten branches; passes the numerical and provenance checks |
| M5-analyses | Executable scoped Germanic chronology and alternative Anatolian laryngeal treatments; three explicit morphology dossiers; differences and unresolved interpretations preserved |
| M5-evaluation | Frozen lexical-family splits, deterministic baselines, separate Latin control, exact inverse sets, complete denominators and leakage disclosures |
| M5-signoff | Pending: no independent PIE specialist has supplied an assessment |

The [evaluation report](../reports/pie-evaluation.json) records each gate
separately. `--require-complete` intentionally exits nonzero while review is
pending. Passing CI establishes computational checks and honest gate reporting;
it does not confer linguistic validation.

## Corpus and provenance

The [data directory](../data/pie/README.md) contains a deterministic sample from
the existing pinned IE-CoR snapshot. The 20 named core sets include dog, five,
four, name, new, star, three, two, eat, fire, foot, water, wind, earth, hand,
bone, blood, knee, horn and heart. Each core set has at least two independent
first-level branches; their union spans ten branches. The broader sample uses
the first eligible source set IDs after reserving that core, without consulting
model output.

Each record retains all original form columns, its cognacy judgment, source
cognate-set reconstruction and notes, gloss/meaning data, exact language/variety,
source locators, uncertainty and available segmentations. Dates remain explicitly
unknown where the import cannot justify them. Source-marked hypothetical forms
are excluded from the attested reflex count and retained in the exclusion ledger.
The 843 reflex memberships are also 843 distinct form rows; repeated membership
cannot inflate the count. Loan relationships and unselected rows remain visible.

The source `forms.csv` rows have no bibliography entries in this snapshot.
Provenance therefore points to pinned dataset rows. The set-level source
bibliography and justification are preserved as separate claims. This does not
assert that every underlying dictionary entry has been independently inspected.

M1 validates a lossless orthographic evidence projection with explicit identity
normalization. Its code-point cells represent spelling, not inferred phonemes.
The experimental phonemic view uses the upstream `Phonemic_Segments` column;
the separate phonetic `Segments` column is never silently substituted. Twenty
source-backed core alignments use a unit-edit baseline and M3 validates row
preservation and singleton correspondence-group feasibility. Neither validation
proves cognacy or phonological homology.

## Frozen evaluation and its limits

Commit `83adff4` freezes the source selection and splits before lexical model
construction. Verification checks Git ancestry, byte identity with those
commits and the absence of fitted model artifacts there; a full clone is
required and CI fetches the history. Grouping uses transitive links over the entire upstream dataset:
supersets, proposed cognacy, normalized root alternatives, shared form IDs, and
identical spellings within a doculect. Possible homonyms are conservatively kept
together. The 119 families split into 71 train, 24 development and 24 test
families: 132/34/34 cognate sets and 561/149/133 reflex records. Unknown family
relationships remain a specialist-review question.

The no-change baseline is compared with a correspondence baseline fitted only
on train pairs with one parsable source protoform. Unit-edit alignment supplies
one-token substitution/deletion counts per doculect. Insertions are recorded as
unsupported by this compiler. Temporary atoms prevent accidental feeding between
substitutions. There is no per-item historical lookup table. Development/test
forms never fit the mappings, and a mutation test checks that changing held-out
transcriptions leaves the fitted mappings unchanged.

The root tokenizer records its losses: it removes reconstruction stars and
morphological hyphens, maps a small declared set of notation aliases, and drops
lexical accent for this baseline only. Length and other supported distinctions
remain. Unknown laryngeals and optional/opaque notation are unsupported; a
partly parsable alternative list is rejected as a whole. The full original
notation remains in the corpus. These lexical models cannot implement Verner's
conditioning; the separate chronology controls retain accent explicitly.

Inverse evaluation searches a declared pool of the parsable published reference
forms, including held-out labels. This is **closed-set reference retrieval**,
not generation of unknown ancestors. Observations from the daughters are tested
jointly against each complete candidate. There is no hybrid made by choosing a
different ancestor for each branch. Source variants are retained as individual
observations, so a deterministic model unable to explain variation can return an
empty set. Empty means empty within that model and pool.

The frozen corpus supplies the shared symbol inventory. Public sources and AI
training may already contain these etymologies. Accordingly this is a
retrospective grouped evaluation, not a blind reconstruction or simulated
discovery of Hittite. Family transfer is not claimed.

## Results, including failures

There are **1,152 lexical forward attempts** (including explicit source
protoform alternatives) and **270 lexical inverse queries**. Of 843 reflexes,
541 can be evaluated by this restricted baseline; 193 have unsupported proto
notation and 109 lack supported phonemic segmentation.

| Model / split | Exact / supported reflexes | All reflexes | Recalled references / inverse queries |
| --- | ---: | ---: | ---: |
| No-change, all | 0 / 541 | 843 | 0 / 135 |
| Correspondence, train | 29 / 365 | 561 | 2 / 93 |
| Correspondence, development | 0 / 97 | 149 | 0 / 22 |
| Correspondence, test | 1 / 79 | 133 | 0 / 20 |

These are low-coverage baselines. Source roots are often stems while reflexes
are inflected lexemes; many sound changes and morphology are unmodeled. All
302 unsupported records and all mismatches remain in the report. Exact baseline
matches carry checked execution certificates but are **not** labeled validated
historical derivations. Conditional accuracy, all-record coverage, normalized
edit distance, candidate sizes, ambiguity and failure categories have separate
denominators. Results are descriptive; no universal superiority or statistical
independence is asserted.

The separate Latin/Romance control was frozen in `c268e77` before fitting its
own models. It has 20 source-attested Latin targets, 60 Romance daughter forms,
120 forward attempts and 40 inverse queries. Latin is omitted from the inverse
observation branches. The declared candidate pool still contains the 20 Latin
labels, so this is also closed-set recovery. Source variety, possible borrowing,
and the distinction between literary Latin and spoken ancestors remain explicit.
The control design explicitly joins the source's separate loan table and retains
form-level loan fields. An absent loan flag does not prove inheritance; learned
versus inherited status remains unreviewed. This control is not counted toward
the 200 PIE sets, and overlap in lexical
families does not become independent family-transfer evidence.

## Source-defined chronology and competing analyses

The [source-analysis ledger](../data/pie/source-analyses.json) gives PDF hashes,
page locators, reading scope, control types and package limitations.

Ringe's chronology in the Olander volume, pp.55–56, supplies ordered Germanic
changes and obstruent blocking. The executable fragment handles stop-series
changes, Verner voicing in explicit vowel–consonant–vowel contexts, and stress
relocation within declared control shapes. Here the immediately preceding
unaccented vowel is the last preceding nucleus, and voiced neighbours are
explicit. Arbitrary cluster traversal, later hardening, unstressed vowel raising
and complete word histories remain outside scope. Ten synthetic controls test
this fragment; a reversed stress/Verner order changes predictions. It is an
intentional negative control, not an attributed alternative historical theory.

Eight source-backed Hittite diagnostics compare Kloekhorst's 2006 conditioned
initial-laryngeal treatment with a retention account attributed to Melchert as
reported in that paper. The original Melchert PDF was unavailable at its linked
location, so this mediated attribution is explicit and included in the review
packet. The same evidence is used for both models. Cases include tentative
etymologies and distinct reconstruction choices. Tests project written-onset
retention; `R` abstracts resonant identity, and some vowel quantity/epenthesis
lies outside the projection. They do not certify full words or settle precise
laryngeal phonetics. The primary source's scanned page images were inspected.

The [morphology dossiers](../data/pie/morphology.json) preserve three separate
problems: the competing strong/weak reconstructions of 'water'; consonantal
*u̯* introduced into its weak stem by an explicitly **analogical** operation;
and competing inherited ablaut/reduplication accounts for the hi-conjugation.
Analogy is not smuggled into a regular sound rule. Source-reported Schindler and
Jasanoff positions remain attributed as such. Morphological comparison can
remain unresolved; no string certificate is claimed to prove the analysis.

## Formal implementation and verification

[CaseStudy.lean](../lean/Historical/CaseStudy.lean) adds six results: exact
finite-pool retrieval, soundness, relative completeness, fixed-model observation
monotonicity, empty-pool-result characterization, and accepted forward traces.
They use M4's inductive observation semantics and M2's licensed trace relation.
All **133 project theorem declarations** appear in the dependency audit; project
axioms, proof placeholders and `native_decide` are rejected.

[PieCheck.lean](../lean/PieCheck.lean) supplies strict JSON input, package/stage
validation, bounded batch execution, full traces, exact-match indicators and
complete finite-pool candidate sets. Metadata, tokenization, scientific scope,
training and I/O remain executable trust boundaries. Every one of the **1,308
forward certificates and 310 inverse sets** is compared against the separate
Python interpreter. Ten invalid executable inputs and fourteen Python failure
tests exercise leakage, missing outcomes, corrupted certificates and review
misclassification. The repository has 67 Python tests in total.

The [local benchmark](../reports/pie-benchmark-local.json) measures 1,000
three-token certificates with 31 rules each in a fresh process, including parsing,
validation and serialization: approximately 0.25 seconds and 51 MiB peak resident
memory on the recorded Darwin x86_64 host. This meets the declared 60-second /
2-GiB budget for that workload. CI measures its own runner separately.

From the repository root, after installing the Python requirements and building:

```bash
python scripts/build_pie_corpus.py --check
python scripts/build_pie_experiment.py --check
python scripts/build_pie_controls.py --check
lean/.lake/build/bin/pie_check --batch data/pie/diagnostic-input.json
python scripts/review_pie.py
python scripts/verify_m5.py --audit reports/lean-axioms-current.txt
python scripts/verify_m5.py --check-report
python scripts/benchmark_pie.py --output /tmp/pie-benchmark.json
python -m unittest discover -s tests -v
```

Generate the fresh audit with `lake env lean Audit.lean` from `lean/` as in
earlier milestones. The local compatibility host uses Lean 4.19.0; CI builds
both 4.19.0 and 4.34.1 and rejects deterministic report drift.

## Independent review still required

The [review packet](../reviews/pie-packet.json) binds all 20 core sets, eight
source-backed diagnostics and three morphology dossiers to exact input and
execution hashes. It asks for source checking, assessment of normalization and
scope, objections and global leakage/attribution review. The
[sign-off record](../reviews/pie-signoff.md) is explicitly pending.

The original [case-study protocol](03-case-studies-and-evaluation.md) requires:
“A specialist independent of the encoding reviews the 20-set core and all
disputed dossiers before the pilot is labeled linguistically validated.”
The reviewer must assess the concrete artifacts, record unresolved objections,
and bind their response to the packet. An AI review or the encoder's own checks
cannot supply this requirement. After any relevant change, stale sign-off is
rejected. `python scripts/verify_m5.py --check-report --require-complete` fails
until the actual independent assessment closes the remaining gates.
