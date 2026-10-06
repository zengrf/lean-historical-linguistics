# Source-backed Indo-European pilot (M5)

Status: **computationally checked, linguistically unreviewed**. Independent
family-specialist review is pending. See [delivery and results](../../docs/11-m5-delivery.md).

The corpus contains **200 source cognate sets / 843 distinct source form rows**
across ten first-level IE-CoR branches. The 20-set review core contains 161
reflexes. These are source claims, not 200 verified PIE derivations.

| Artifact | Role |
| --- | --- |
| [selection.json](selection.json) | Deterministic selection, omitted rows and source-marked reconstructions excluded from the reflex count |
| [splits.json](splits.json) | 119 conservatively linked lexical families, frozen before model fitting |
| [corpus.json](corpus.json) | Every selected raw form, judgment, cognate-set record, language metadata and exact source locator |
| [evidence.json](evidence.json) | M1-checked identity projection of source orthography; character cells are not inferred phones |
| [experiment.json](experiment.json) | Explicit normalization, training pairs, learned mappings, candidate pool and every supported/unsupported reflex |
| [lexical-input.json](lexical-input.json) | Executable no-change and train-only correspondence baselines |
| [source-analyses.json](source-analyses.json) | Source locators, chronology constraints and declared projection/conditioning limits |
| [diagnostic-input.json](diagnostic-input.json) | Ten synthetic chronology controls and eight source-backed onset projections under two models each |
| [morphology.json](morphology.json) | Nominal ablaut, a separately typed analogical operation, and unresolved hi-conjugation alternatives |
| [alignments](alignments) | Twenty edit-alignment dossiers checked by M3; validity does not establish homology |
| [latin-control-frozen.json](latin-control-frozen.json) | Separate 20-set attested-Latin control with 60 Romance daughter records |
| [latin-control-design.json](latin-control-design.json) | Latin-control training pairs and declared closed-set retrieval scope |
| [latin-control-input.json](latin-control-input.json) | Executable Latin/Romance baseline/control queries |

All IE-CoR source and derived data retain **CC BY 4.0**; see the
[attribution notice](../THIRD_PARTY_NOTICES.md). Original upstream files are
unchanged at commit `700b635a04786427b78841489c46eefbe2843509`. IE-CoR's
individual `forms.csv` bibliography fields are empty in this snapshot. Each
form therefore cites its exact pinned dataset row; cognate-set bibliographic
citations are retained separately and are not misrepresented as a checked
dictionary citation for each spelling.

`Phonemic_Segments` and the source's phonetic `Segments` are retained separately.
Missing segmentations remain missing. Published protoforms are explicitly
reconstruction claims. Ambiguous notation that the baseline cannot parse stays
unsupported; it is neither guessed nor discarded from the denominator.

Run `python scripts/build_pie_corpus.py --check`,
`python scripts/build_pie_experiment.py --check`, and
`python scripts/build_pie_controls.py --check` from the root to verify generated
bytes. Changing frozen inputs requires a separately versioned study. The
[review packet](../../reviews/pie-packet.json) binds the core and disputed
dossiers to source and execution hashes.
