# Terminology and notation

The terminology in this repository follows the primary works listed below.
Where authors differ in their classifications or reconstructions, the data
retain the author's name, reconstruction system and language varieties.

| Term | Use in this repository | Reference |
| --- | --- | --- |
| Comparative method | Comparison of related languages through recurrent sound correspondences, reconstruction and the assessment of innovations | Rankin (2003), pp.183–192; Jäger and List (2016), §§1–2 |
| Comparanda | Forms proposed for comparison, before the relevant cognacy judgment has been established | Meelen, Hill and Fellner (2022), §3 |
| Cognate set | Forms or morphemes assigned a common inherited source under a specified analysis | Meelen, Hill and Fellner (2022), §§3–5 |
| Sound correspondence | A relation among sounds in compared forms; recurrent correspondences are evidence for reconstruction | Rankin (2003), §5; Jäger and List (2016), §2 |
| Sound change | A proposed historical development, with a direction, conditioning environment and language stage | Rankin (2003), §§2, 5; Lowe and Mazaudon (1994), §1 |
| Reflex | The descendant form or sound under the cited historical analysis | Rankin (2003), §5 |
| Protoform | A reconstructed form attributed to a named proto-language and analysis | VanBik (2009), pp.57–65 |
| Internal reconstruction | Reconstruction from alternations within a language | Rankin (2003), §5; Jacques (2012), *An Internal Reconstruction of Tibetan Stem Alternations* |
| Alignment | An arrangement of sequences in rows, with corresponding elements in columns and gaps where required | Jäger and List (2016), §2.1 |
| Correspondence pattern | A pattern inferred from compatible alignment columns under the stated compatibility criterion | List (2019), pp.144–145 (PDF pp.8–9) |
| Ordered rules / rule cascade | A sequence of rules in which each rule applies to the output of its predecessor | Kaplan and Kay (1994), pp.331–333 |
| Derivation | A sequence of forms licensed by the specified rules | Kaplan and Kay (1994), §2 |
| Certificate | Data supplied to a checker; here, usually the intermediate forms of a derivation | Repository implementation term; see [rule semantics](rule-semantics.md) |
| Soundness | Every accepted certificate or returned candidate satisfies the specified relation | State the relation and assumptions in the theorem |
| Relative completeness | Every candidate satisfying that relation within the declared search space is returned | State the inventory, bounds, models and observations |
| Observational equivalence | Two hypotheses have the same predicted observations under the stated models | See [bounded reconstruction](bounded-reconstruction-semantics.md) |
| Sensitivity analysis | Comparison of results after changing a specified assumption, input or analysis | Report the changed assumption and the affected results |

`dossier`, `package`, `site` and `doculect` also occur in the file formats. A
dossier is the repository's record of a comparison and its evidence. A rule
package stores an ordered list of rules and its metadata. A site is an
alignment column, following List (2019:144). A doculect identifies a particular documented variety or
historical stage. These labels describe data structures; they add no claim of
historical relatedness.

## Reconstruction levels and transcription

VanBik's Proto-Kuki-Chin, Proto-Central-Chin, Proto-Northern-Chin and Proto-Maraic
are distinct reconstruction levels. His Proto-Kuki-Chin comparisons require
evidence from at least two of his three principal subgroups: Peripheral,
Central and Maraic (2009:58). His reconstruction of tone is provisional (p.57).

Button's Northern Chin includes Mizo and Zahau alongside Thado, Zo, Tedim and
Sizang (2011:12–14). It therefore differs in coverage from VanBik's Northern
Chin. Button's tone categories I–III are historical categories, distinct from
the phonetic pitch contours of individual languages (pp.27–30). A missing tone
mark is interpreted only under the cited transcription convention.

Proto-Tibeto-Burman, Proto-Sino-Tibetan and Proto-Trans-Himalayan retain the
classification and reconstruction assumptions of each source. A shared name
alone does not establish identical descendant sets or phonological systems.
Old Chinese spelling, Middle Chinese transcription and an Old Chinese
reconstruction occupy separate fields. An asterisk marks reconstruction, not
written attestation.

## Writing and attribution

Describe the linguistic problem, give the compared forms or theorem, then state
the result and its limits. Name the author of a reconstruction or disputed
analysis. Use ordinary terms such as *published analysis*, *comparative data*,
*sound correspondences*, *derivation* and *acceptance criterion*. Numerical
results should identify their denominator and the treatment of missing data.

Distinguish a publication's result from the proposed use of that result in Lean.
State proof assumptions next to the theorem and empirical limitations next to
the affected result. Keep milestone status and reproduction commands in the
delivery documents. Historical review records and frozen experimental inputs
retain their original wording and hashes.

## Sources examined for this revision

The [reading record](../bibliography/terminology-readings.json) lists the retained
PDFs, hashes and pages examined. The readings concern selected sections, not
complete books.

- [Rankin, *The Comparative Method*](https://lx.berkeley.edu/sites/default/files/rankin_comparative_method.pdf).
- [Jäger and List, *Statistical and computational elaborations of the classical comparative method*](https://lingulist.de/documents/papers/jaeger-list-2016-computational-elaborations-comparative-method.pdf).
- [Meelen, Hill and Fellner, *What are cognates?*](https://journals.ed.ac.uk/pihph/article/view/7405).
- [Lowe and Mazaudon, *The Reconstruction Engine*](https://aclanthology.org/J94-3004/).
- [Kaplan and Kay, *Regular Models of Phonological Rule Systems*](https://aclanthology.org/J94-3001/).
- [List, *Automatic Inference of Sound Correspondence Patterns Across Multiple Languages*](https://aclanthology.org/J19-1004/).
- [List, Hill, Forkel and Blum, *Representing and Computing Uncertainty in Phonological Reconstruction*](https://aclanthology.org/2023.lchange-1.3/).
- [VanBik, *Proto-Kuki-Chin*](../library/open/vanbik2009.pdf), and [Button, *Proto Northern Chin*](../library/open/button2011.pdf).
- [de Moura and Ullrich, *The Lean 4 Theorem Prover and Programming Language*](https://lean-lang.org/papers/lean4.pdf).
