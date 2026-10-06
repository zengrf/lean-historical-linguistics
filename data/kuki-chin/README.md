# Kuki-Chin study

The frozen sample contains **100 sets and 580 reflex records** from VanBik (2009), chapter 4. It covers 34 initial-consonant subsections. The 50-set core contains 298 reflex records. These are source cognacy claims awaiting specialist assessment.

`corpus.json` preserves PDF-extracted forms, glosses, exact source aliases, page and entry locators, discussion flags and source reconstruction levels. `selection.json` records the round-robin sample and extraction omissions. `splits.json` groups related roots, compound components, explicit cross-references and repeated source spellings before assigning train/development/test splits. The input freeze is commit `2ed6130`; the fitted models did not exist at that commit.

`experiment.json` records every sampled row, its normalization, tone marks, stem-cell analysis or exclusion reason. The two baselines compare transcription graphemes with tone excluded. They do not provide full phonemic analyses or chronological sound changes. Form I and Form II must match by label; an invariant reflex can apply to both, but an unlabelled form cannot freely select either. Unsupported compounds, allofams and optional material remain in the denominator.

`lexical-input.json` supplies scoped Lean jobs. Inverse queries are complete only within the specified finite pools, which include held-out reference labels. Restricting observations to Northern varieties does not change a PKC ancestor into a PNC ancestor.

`source-fragments.json` states the projection, source and uncertainty of each separate published-analysis exercise. `diagnostic-input.json` includes deliberately unsuccessful controls. `morphology.json` preserves complete competing paradigms. The bounded onset comparison in `joint-analysis-input.json` retains both analyses of the transitive/intransitive voicing contrast.

`evidence.json` and `cross-evidence.json` use the M1 interchange format. The 50 `alignments/` files use reversible `Uxxxxxx` Unicode scalar identifiers to retain spaces, combining marks and stem labels through M3. These are display alignments, not independently justified phonological alignments. Removing gaps and decoding the identifiers must recover the source strings exactly.

Run the commands in [M6 delivery](../../docs/12-m6-delivery.md). Source PDF attribution is in [the data notices](../THIRD_PARTY_NOTICES.md). The [specialist packet](../../reviews/sino-tibetan-packet.json) remains pending.
