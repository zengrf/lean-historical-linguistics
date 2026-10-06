# Formal architecture and correctness statements

Status: **design**, except the explicitly identified prototype results and implemented [M1 evidence schema/checker](07-m1-delivery.md), [M2 contextual semantics/certificates](08-m2-delivery.md), [M3 alignment/correspondence checker](09-m3-delivery.md), [M4 bounded reconstruction](10-m4-delivery.md), and [M5 computational pilot](11-m5-delivery.md). M5's independent specialist review is pending; contracts for later modules remain future work.

## 1. The object of verification

Let `Σ` be a finite segment inventory, `H` a declared hypothesis space, `L` a set of language varieties and historical stages, and `D` a finite collection of observations. Initially, a hypothesis contains an ancestral word and a selected, independently versioned forward model. Later it can include morphological structure and alternative laws.

For a deterministic model `F`, define:

```text
Fits(F, D, h) := for every observation (l, w) in D, F(l, h) = w
Recon(P, F, D) := { h in P | Fits(F, D, h) }
```

`P` must be an explicit finite pool or come from a proved finite enumeration with declared bounds. A theorem about `Recon` does not establish that the true ancestor is in `P`. If laws are inferred as part of `h`, their complexity and permitted operations must also be bounded; otherwise the model can encode the observed lexicon as a lookup table.

M4 now proves exact enumeration by alphabet and maximum word length, subject to
an explicit morpheme shape filter, paired with a finite list of whole joint
analyses. It returns every fitting history, with M2 branch certificates and
optional checked M3 evidence links. Known cells match exactly, null rows are
unconstrained, and unknown cells occupy one segment. Incomplete prefixes remain
distinct from complete empty inverse sets. See the
[versioned bounded-search contract](bounded-reconstruction-semantics.md).

For nondeterministic histories, replace equality by membership in the model's licensed output relation. Declare whether alternatives represent real historical variation, uncertainty about the analyst's model, or a lossy observation. These interpretations should not be conflated.

## 2. Data and evidence layers

| Layer | Objects | Required invariant | What remains empirical |
|---|---|---|---|
| Sources | Publication ID, edition, page, dataset release, checksum | Stable identifiers and resolvable references | Reliability and interpretation of the source |
| Observations | Attested spelling, phonetic record, gloss, variety, date interval | Provenance and declared representation | The recorded form and its linguistic analysis |
| Normalization | Original string, tokenizer, segment sequence, mapping version | Original text retained; every transformation recorded | Whether the normalization preserves relevant distinctions |
| Morphology | Word occurrence, morpheme spans, paradigm cell, grammatical features | Spans are valid and non-overlapping where required | Segmentation, function and historical relatedness |
| Comparisons | Proposed cognate links, alignments, correspondence sites | Valid references and structurally valid alignments | Historical inheritance and semantic compatibility |
| Models | Stage inventory, laws, chronology, strata, topology | Well-typed and internally consistent configuration | Which model is linguistically justified |
| Certificates | Intermediate forms, rule applications, membership witnesses | A small checker accepts only licensed derivations | Adequacy of the licensed model |
| Inference | Candidate pools, scores, solver logs | Declared bounds, configuration and reproducibility | Ranking quality and generalization |

Use a **doculect/stage identifier**, not just a label such as “Tibetan.” Different manuscript traditions, written standards and spoken varieties can preserve different evidence. A reconstruction must carry `analysis_id` and `proto_node_id`, not just a leading asterisk in a string.

### Essential distinctions in the schema

- `missing`: no observation available.
- `gap`: an explicit alignment position with no corresponding segment.
- `unknown`: a source records an unresolved reading or sound.
- `alternatives`: a linked set of possible analyses, with an identity for shared choices.
- `attested`: an observation of a written or recorded form, with representation type.
- `reconstructed`: a claim inferred under a named analysis.

Missing evidence must not create a new cognate, while an alignment gap can represent hypothesized insertion or loss. Neither should be encoded as an empty string used for both meanings. Tone, stress, length, aspiration and morphological boundaries need declared tokenization; a Unicode code point is not generally a phonological segment.

CLDF should be the interchange format where applicable, with sidecar tables for historical stages, laws, provenance, alternative analyses and certificates. The CLDF validator remains useful but does not validate the history itself.

## 3. Rule semantics

M2 now implements the [precise versioned contract](rule-semantics.md): single-segment substitution/deletion, at most two explicit context tests per side, word/morpheme boundaries, both scan directions, simultaneous/feeding passes and named chronological stages. The proposals below concerning compilation and broader rule fragments remain future work.

The rule language specifies bounded left and right contexts, a target predicate on segments, a replacement or deletion, and an application convention. Each package declares its word/morpheme boundary conventions and the stages at which accent and tone are interpreted.

The reference interpreter is structurally recursive and terminates on finite inputs. For a simultaneous pass it reads the original input to determine each match and emits output into a separate list. For a left-to-right feeding pass, define exactly which produced material is visible. The two application conventions have different semantics.

An ordered cascade feeds the result of one complete pass into the next. A chronology can initially be a list. A later partial-order chronology admits several linear extensions; prove that a proposed schedule satisfies its precedence constraints. Claim schedule independence only after proving the relevant rules commute on a specified domain.

Do not implement arbitrary “repeat until unchanged” without a termination measure or an explicit fuel bound. A fuel-limited result must report exhaustion distinctly from a successful derivation. Insertion rules require a definition that prevents repeatedly matching the same empty boundary.

### Compilation

Prove a reference semantics first. Compile a carefully restricted rule fragment into finite-state transducers only after the semantics are stable:

```text
compiled_correct:
  restricted(rule) →
  ((input, output) ∈ denotes(compile(rule)) ↔ derives(rule, input, output))

cascade_compilation_correct:
  all_restricted(rules) →
  denotes(compileCascade(rules)) = relationalComposition(map denotes rules)
```

These are proposed statements, not existing Lean declarations. The restrictions must be in the type or theorem hypothesis. Arbitrary rational relations cannot be intersected using an acceptor intersection theorem. For multi-branch reconstruction, the initial implementation filters a finite candidate pool. Later symbolic search can intersect regular **preimage languages** when the required closure result has actually been proved.

## 4. Alignment and correspondence contracts

M3 proves that removing gaps from each accepted present row yields exactly the supplied original sequence, and that absent rows remain absent. It rejects all-gap/missing columns, duplicated or omitted segments, and malformed explicit morpheme boundaries. Present empty words remain distinct from absent words. Monotonic alignment is a property of this fragment; bounded metathesis needs an explicit extension. The [versioned semantics](alignment-correspondence-semantics.md) specify the representation and [M3 delivery](09-m3-delivery.md) gives the commands and evidence.

A checked M3 correspondence partition establishes:

1. Every member refers to an existing alignment site.
2. Every pair satisfies the declared compatibility predicate.
3. Missing cells supply no positive evidence.
4. Every required site appears in exactly one group, if a partition is claimed.
5. Support counts are computed from distinct evidence units under the declared policy.

Minimum clique cover is a separate optimization claim. M3 accepts only `feasibility-only` certificates. A claim of optimality would need a lower bound or a complete finite search certificate. Distinct positions or alignments with the same declared evidence unit count once; authenticating whether the unit labels represent independent historical evidence remains a data-review obligation.

## 5. Certificates and the trust boundary

```mermaid
flowchart LR
    A[Attestations and source records] --> B[Versioned linguistic analysis]
    B --> C[Explicit model and candidate pool]
    C --> D[External search: expert, LingPy, solver, neural model]
    D --> E[Candidate and derivation certificate]
    C --> F[Small Lean checker]
    E --> F
    F --> G[Kernel-checked conditional result]
    B --> H[Independent linguistic review and held-out evaluation]
    G --> H
```

The present certificate is simply a list of intermediate words, one per rule. A future compact certificate may store rule IDs and changed positions. It must be connected by a theorem to the reference semantics, so that acceptance establishes the stated derivation relation.

The trusted logical base includes Lean's kernel and any axioms actually reported by `#print axioms`. Standard extensionality/quotient principles can occur; “no project axioms” does not mean “no logical axioms.” Avoid `sorry`, `admit`, unchecked external oracles and `native_decide` in the proof path for this project. The latter restriction keeps this prototype's claimed evidence in kernel-rechecked terms. Ordinary executable benchmarks may use compiled code, but their timing and output are not substitutes for those proofs.

JSON decoding and the Python CLDF importer are executable components outside the kernel proofs. M1 validates decoded objects, retains source bytes and tests serialization. Its theorems concern typed evidence and normalization chains; they do not verify the byte parser or authenticate source readings.

## 6. Theorem backlog and existing results

The current files use `Std`, with no mathlib or linglib dependency.

| Contract | Current status | Location / remaining work |
|---|---|---|
| Execution of appended cascades equals sequential execution | **Proved** | `Comparative.run_append` |
| Inductive derivation agrees with executable cascade | **Proved** | `Comparative.derives_iff_run` |
| Accepted trace implies a licensed derivation | **Proved** | `Comparative.checkTrace_sound` |
| Canonical trace is accepted | **Proved** | `Comparative.checkTrace_complete` |
| Added observations only eliminate candidates under a fixed model | **Proved** | `Comparative.fits_mono` |
| Observationally equivalent ancestors satisfy the same observations | **Proved** | `Comparative.fits_of_equivalent` |
| Filter membership exactly matches pool membership and acceptance | **Proved** | `Comparative.mem_reconstruct_iff` |
| Reconstruction correctness relative to a reflected predicate and finite pool | **Proved, conditional** | `Comparative.reconstruction_correct` |
| Strengthening an acceptance predicate cannot enlarge output | **Proved** | `Comparative.reconstruct_mono` |
| Corrupted, missing-step and extra-step traces are rejected | **Proved examples** | `Comparative.Examples` |
| A merger leaves distinct ancestors observationally identical | **Proved example** | `Comparative.Examples.merger_ambiguity` |
| Missing-data compatibility need not be transitive | **Proved example** | `Comparative.Patterns.compatible_is_not_transitive` |
| Missing data differ from gaps and cannot alone supply support | **Proved examples** | `Comparative.Patterns` |
| Independent positional alternatives can overgenerate | **Proved example** | `Comparative.Patterns.independent_choices_overgenerate` |
| Context-sensitive rule interpreter and certificate correctness | **Proved** | `Historical.Rules`, `Historical.Certificates`, `Historical.RuleInput.checkDossier_iff`; M2 |
| Restricted rule compiler correctness | Planned | M7 |
| Alignment validity and feasible correspondence-partition checker correctness | **Proved** | `Historical.Alignment`, `Historical.Correspondence`, `Historical.CorrespondenceInput.dossierAccepted_iff`; M3 |
| Exhaustive enumeration by inventory/length and candidate soundness/completeness | **Proved** | `Historical.Reconstruction.mem_wordsUpTo`, `mem_space`, `reconstruction_correct`; M4 |
| Specialist assessment of PIE and Sino-Tibetan etymologies | Pending | M5 and M6; an empirical requirement, separate from the theorem inventory |
| Observational equivalence and fixed-model monotonicity/refinement | **Proved** | `Historical.Identifiability.equivalent_fits`, `equivalent_membership`, `reconstruction_refinement`; M4 |
| Probabilistic inference correctness and calibration | Planned, optional | M9 |

There are **22 M0 theorem declarations**, five M1 evidence results, 17 M2 results, 35 M3 results, 48 M4 results and six M5 case-study results, for **133 audited declarations** in total. The M0 abstract `Comparative.Rule` remains any total word-to-word function for generic theorems. M2 uses a distinct data-only `Historical.Rules.Rule` grammar; its accepted packages enforce local context bounds, a finite declared inventory and chronological stage continuity. M3 verifies alignment preservation and feasible correspondence partitions. M4 proves bounded inverse reconstruction through the M2 semantics and preserves joint alternatives. M5 checks supplied reference-pool retrieval and forward certificates for an empirical baseline pilot. M1 retains sourced evidence independently. These conditional results do not establish historical plausibility.

## 7. Uncertainty, scores and explanations

Keep three different outputs:

1. **Logical compatibility:** a predicate or checked certificate under explicit assumptions.
2. **Search/ranking score:** edit cost, description length, likelihood or another named objective.
3. **Empirical uncertainty:** sensitivity to coding, data, rules and competing analyses; calibrated probabilities only where justified.

Do not store arbitrary confidence numbers next to proof terms as though the latter verified the numbers. A future finite rational Bayesian model can prove normalization and exact posterior calculations; it still cannot prove that its priors and likelihood represent historical reality. Infinite weighted paths require additional mathematics and are outside the first release.

Explanations should name the source observations, rule order, intermediate forms, unmatched observations and surviving alternatives. A diagnostic that produces a small conflicting subset is more useful than an opaque Boolean failure. Minimality of the conflict set is itself optional and separately provable.

## 8. Suggested module organization after the prototype

```text
Historical/Source/          identifiers, page references, editions
Historical/Observation/     scripts, segments, missingness, stages
Historical/Morphology/      morpheme occurrences and paradigms
Historical/Rules/           reference semantics, contexts, chronology
Historical/Certificates/    trace checker and reflection theorems
Historical/Alignment/       validity and selected optimization algorithms
Historical/Correspondence/  compatibility graphs and checked covers
Historical/Reconstruction/  finite pools, bounds, equivalence, ambiguity
Historical/Import/          validated interchange and generated fixtures
Historical/CaseStudies/     individually sourced analysis packages
Historical/Probability/     optional later finite models
```

This is a proposed module organization. Upstream general results where practical, and keep empirical datasets and domain-specific assumptions separate from general theorem libraries.
