# Can the comparative method be formalized in Lean?

**Yes: a useful, substantial part can be formalized.** The strongest initial project is a system for checking reconstruction arguments, exposing assumptions and computing the remaining alternatives. It should grow into a library of verified comparative procedures. It should not promise a proof that a particular reconstruction was the language actually spoken by a prehistoric population.

This distinction is productive rather than merely cautionary. It identifies concrete mathematical questions: Does a sound-law cascade derive the claimed reflex? Does an alignment faithfully account for its input? Is a proposed correspondence group internally compatible? Does finite reconstruction return exactly the compatible candidates in its declared search space? Can two different hypotheses be distinguished by the available observations?

Research cutoff: **5 October 2026 UTC** (the session began on 4 October in Los Angeles). [The catalogue](../bibliography/README.md) contains source links, acquisition status, annotations and reading scope. This is a substantial targeted review, not a claim to have read every page of every downloaded book. Page references below use **PDF page numbers**, which can differ from printed pagination.

## 1. What is being formalized?

### The method is an iterative investigation

Rankin's account moves from candidate comparisons through recurring correspondences, distributional analysis, reconstruction and the interpretation of phonetic values. It also considers morphology, meaning and syntax. Complementary correspondence distributions can motivate a common proto-segment; typology can help interpret that segment. Neither step is equivalent to selecting the most frequent modern sound. See [Rankin 2003](https://lx.berkeley.edu/sites/default/files/rankin_comparative_method.pdf), PDF pp. 1–5, 10, 17, 23, 26.

Jäger and List distinguish computational problems that are often bundled together under the comparative method. Proposed cognates inform correspondences, and correspondences inform cognacy judgments. This makes revision an ordinary part of the method, not evidence of a circular proof when hypotheses and their successive evidence are recorded. See [Jäger & List 2016](https://lingulist.de/documents/papers/jaeger-list-2016-computational-elaborations-comparative-method.pdf), introduction.

**Design consequence:** use a versioned argument graph. An observation, a proposed cognacy judgment, a normalization decision, a sound law and a reconstructed form are different objects. Keep the dependencies between them. A revision creates a new analysis against which the existing evidence can be checked again.

### Cognacy needs an explicit unit and diagnostic

Meelen, Hill and Fellner distinguish stronger and weaker kinds of cognacy, together with similarity in meaning and function. Their workflow separates potential comparisons from accepted comparisons relative to a developing correspondence system. They also discuss a colexification-based semantic measure. This is especially relevant because a binary whole-word label hides root sharing, changed morphology and semantic divergence. See [*What are cognates?*](https://journals.ed.ac.uk/pihph/article/view/7405), PDF pp. 2, 7–12, 20, 25.

**Design consequence:** a statement of cognacy must specify its units, historical depth and evidence. Preserve morpheme occurrences and their position within words. Record semantic evidence without making a numerical semantic score the definition of inherited meaning. Identical modern glosses are neither necessary nor sufficient for common ancestry.

### Regularity, analogy and phonetic plausibility

Garrett distinguishes phonologization from other sources of changed phonological form. Garrett and Johnson discuss production and perception biases; these motivate directional expectations, not exceptionless restrictions on every possible history. Garrett and Blevins show why a synchronic morphophonological pattern may have an analogical history. See [Garrett's sound-change chapter](https://linguistics.berkeley.edu/~garrett/garrett-soundchangechapter.pdf), [Garrett & Johnson](https://linguistics.berkeley.edu/~kjohnson/papers/Garrett-Johnson_2012.pdf), and [Garrett & Blevins](https://linguistics.berkeley.edu/~garrett/FsKiparsky.pdf).

**Design consequence:** regular sound change is a scoped claim about a stage, variety, environment and lexical stratum. A failure may indicate an erroneous transcription, wrong cognate, omitted condition, loan, analogy or genuinely unresolved history. It must not automatically produce a word-specific exception that makes the theory fit. Analogical explanations need their own model forms and paradigm relations.

Matisoff explicitly objects to confusing elaborate notation with explanation in [*Proto-Languages and Proto-Sprachgefühl*](https://stedt.berkeley.edu/pdf/JAM/matisoff1982proto.pdf), PDF pp. 3–4. His discussion of competing complex protoforms and the historical level of conditioning material, pp. 31–32, also matters. A theorem prover does not answer that criticism merely by checking more notation. The response must be independently constrained laws, inspectable evidence, prediction and intelligible counterexamples.

## 2. Computational reconstruction has a long history

### Direct prior art: the Reconstruction Engine

[Lowe & Mazaudon 1994](https://aclanthology.org/J94-3004/) already describe bidirectional reconstruction with explicit sound correspondences, contextual restrictions, a syllable canon and semantic processing, illustrated with Tamang. Their system computes possible ancestors, groups supporting reflexes, generates expected daughters and retains a residue. Its treatment of imprecision and user-supplied semantic groupings is directly relevant (PDF pp. 1–2, 6, 10, 12, 20, 25–29).

This rules out a novelty claim such as “the first implementation of the comparative method.” The proposed contribution is **machine-checked contracts for selected operations**, an explicit connection from those contracts to source evidence, and systematic handling of competing analyses.

### Alignments, cognate detection and correspondence patterns

The pair-HMM tradition models alignment and word similarity ([W05-0606](https://aclanthology.org/W05-0606/)); context-sensitive etymological models add phonetic features and imputation ([W12-0215](https://aclanthology.org/W12-0215/)). [LexStat](https://aclanthology.org/W12-0216/) estimates language-specific scoring schemes. [List's monograph](https://doi.org/10.5281/zenodo.11879) explains why scoring, pairwise alignment and multiple alignment must be distinguished. An algorithm can optimize its declared score without finding the linguistically correct alignment.

[Partial cognate detection](https://aclanthology.org/P16-2097/) matters particularly for morphologically complex comparisons: two words may share only one component. [Dictionary-based discovery](https://aclanthology.org/D17-1267/) adds semantic evidence. [Global reranking](https://aclanthology.org/P17-1181/) and [supervised link prediction](https://aclanthology.org/2024.eacl-long.58/) impose additional structure. These are candidate-producing methods, not interchangeable definitions of cognacy.

[List 2019](https://aclanthology.org/J19-1004/), especially PDF pp. 8–9, models compatibility of incomplete alignment sites and searches for a clique cover. Two sites need shared non-gap evidence and no conflicting observed cells. Missing data make compatibility non-transitive. Therefore connected components or naïve union-find can merge incompatible sites. The Lean prototype includes a counterexample with three columns that share one observed sound but disagree elsewhere. Future work should verify clique membership and coverage separately from any claim of minimum cover size.

[Trimming](https://aclanthology.org/2023.sigtyp-1.6/) and [fast supervised reconstruction](https://aclanthology.org/2022.lchange-1.9/) provide transparent baselines. Preserve the discarded material: higher regularity after trimming is not evidence that every removed segment was historically irrelevant.

### Probabilistic and neural inference

The progression from [stochastic diachronic edits](https://aclanthology.org/D07-1093/) through [markedness-aware reconstruction](https://aclanthology.org/N09-1008/) to [large-scale Austronesian reconstruction](https://doi.org/10.1073/pnas.1204678110) demonstrates that useful automatic inference is possible. It also exposes assumptions about supplied cognate sets, trees, alignment and change processes. Approximate inference must not be advertised as exhaustive search.

[Ab Antiquo](https://aclanthology.org/2021.naacl-main.353/) evaluates supervised reconstruction of an attested ancestor and discusses phonological error patterns. [Unsupervised neural reconstruction](https://aclanthology.org/2023.acl-long.91/) incorporates monotonic alignment and other inductive biases. [Cognate Transformer](https://aclanthology.org/2023.emnlp-main.423/) uses aligned inputs and pretraining, with limitations involving data scarcity and metathesis. These provide strong baselines, but benchmark agreement is not historical identification.

[Reflex reranking](https://aclanthology.org/2024.lrec-main.762/) and [semisupervised bidirectional reconstruction](https://aclanthology.org/2024.acl-long.788/) support forward derivation as a useful constraint. The latter paper explicitly observes that incorrect protoforms can still yield accurate daughter predictions and that correspondence between neural reasoning and linguistic reasoning is not established (PDF p. 10). This is an empirical counterpart of the formal inverse ambiguity in our prototype.

[Sound-law induction as programming by examples](https://aclanthology.org/2025.acl-long.1432/) is especially compatible with proof-carrying proposals. Its generated Python programs and small evaluation set do not constitute verified linguistic rules. Translate accepted proposals into a restricted rule language; do not execute arbitrary generated programs as the trusted checker. The [2026 Chinese dialect study](https://aclanthology.org/2026.acl-long.831/) extends ancestor-informed rule and pronunciation tasks, but its Middle Chinese/dialect setting is not evidence for a reconstructed Sino-Tibetan root.

## 3. PIE: strong traditions, multiple analytical layers

### What provides a useful first case?

Start with **restricted, source-backed derivations**, not a universal PIE grammar. Three complementary dossiers are proposed:

1. **Germanic relative chronology:** a source-defined subset of Grimm-type developments, Verner's conditioning and subsequent stress relocation. Preserve the source's exact conditions. This demonstrates feeding, bleeding and the need for stage-indexed accent.
2. **Anatolian laryngeal reflexes:** show why an inventory distinction, a phonetic interpretation and a written reflex are separate claims. Retain competing treatments where syllabification or analogy matters.
3. **Morphology:** compare a small nominal ablaut paradigm and, later, alternative accounts of Hittite hi-conjugation. A root string alone cannot encode a paradigm.

The [Olander volume](https://www.cambridge.org/core/product/4B44B5ACF0D3BBA89B9408050F112A52) supplies multiple scholarly perspectives. Clackson's methodology chapter discusses shared innovations, retentions and false positives from contact or parallel change. Ringe's chapter sets out chronology and the limitations of cladistics. Its numerical illustration for the Germanic subgroup must not be imported as a calibrated probability: that would require justifying the event probabilities and their dependencies, independently of checking arithmetic.

Kloekhorst's work supplies explicit, testable disputes: [initial laryngeals](https://www.kloekhorst.nl/Publications.html), nominal ablaut, thorn clusters, the Anatolian stop system and a proposed pre-PIE final-vowel law. The bibliography links individual PDFs. Their coexistence argues for named analysis packages rather than a global constant called `thePIE`. A shared reconstructed distinction does not require agreement about its precise phonetic realization or its chronological level.

### Existing executable PIE reconstructions

[PIE Lexicon](https://aclanthology.org/W17-0234/) uses foma to implement ordered sound laws and generate forms in many languages. It is direct implementation prior art. Its reported fit and its Glottal Fricative Theory should be assessed as claims within a particular system. Successful derivation of encoded examples does not entail that its proto-inventory is uniquely determined. A Lean version would add value only through well-defined semantics, independent checking, evidence provenance and discriminating evaluation.

### Data, phylogeny and historical interpretation

[IE-CoR](https://doi.org/10.1038/s41597-025-05445-3) is a strong source for reviewed cognate relationships, morphological complexity and contact annotations. Its discussion of “fire” and “name” illustrates that agreement on cognacy need not imply agreement on a precise protoform. The paper also has inconsistent lexeme totals between its abstract and body: compute statistics from a pinned release rather than copying a convenient number.

[Ringe, Warnow & Taylor](https://www.cs.rice.edu/~nakhleh/CPHL/RWT02.pdf), [Nakhleh, Ringe & Warnow](https://www.cs.rice.edu/~nakhleh/Papers/81.2nakhleh.pdf), and [Erdem et al.](https://www.cs.rice.edu/~nakhleh/Papers/padl03.pdf) show that formal character models, networks and constraint solving already contribute to Indo-European phylogeny. These reconstruct a different object from phonological word forms.

[Chang et al.](https://linguistics.berkeley.edu/~garrett/ChangEtAl-2015.pdf) and [Heggarty et al.](https://doi.org/10.1126/science.abg0818) illustrate the consequences of ancestry constraints, sampled ancestors and data coding for dated trees. The plan does not attempt to settle homeland questions by formalizing one selected analysis. That would require a separately scoped evidential synthesis, not just a proof assistant.

## 4. Sino-Tibetan / Trans-Himalayan: preserve disagreement

### Naming a proto-language already embeds assumptions

[Benedict 1972](https://stedt.berkeley.edu/pubs.html) distinguishes Chinese, Karen and Tibeto-Burman in its taxonomy (PDF pp. 14, 18). Matisoff's numeral study explicitly revises aspects of that organization. Therefore “Proto-Tibeto-Burman,” “Proto-Sino-Tibetan” and “Proto-Trans-Himalayan” must not be silently treated as interchangeable identifiers. Define a proto-node by a source, a set of descendant varieties and an explicit topology hypothesis.

The full Benedict and Matisoff 1978 PDFs are retained, but only selected introductory scanned pages were visually examined. Matisoff's 2003 HPTB remains an access gap in this session; its publisher description and the downloaded critical reviews do not license a claim to have read that book directly.

### Testable disagreements, not a single imposed doctrine

[Sagart's HPTB review](https://shs.hal.science/halshs-00094374) asks for explicit correspondences and distinguishes useful results from untested comparisons. [Jacques's review of Hill](https://shs.hal.science/halshs-03507197) emphasizes philology, contact, analogy and unresolved questions. [Fellner & Hill's methodological response](https://www.tara.tcd.ie/bitstreams/c18faf5a-558b-4783-b832-7d38a4f6b205/download) challenges the transfer of assumptions between research traditions; only its web-accessible introductory material was examined here.

The appropriate formal target is a comparison of **specified analyses on specified evidence**. Allofamic variation can be represented as an explicit hypothesis with constraints and a cost; it must not act as an unlimited escape hatch. Conversely, a strict deterministic sound model must not force every unexplained form to be rejected as non-cognate. Retain an unresolved category and permit later revision.

### Work upward from a tractable subgroup

[VanBik's Proto-Kuki-Chin](https://stedt.berkeley.edu/pubs.html) distinguishes reconstructions at several levels and supplies abundant comparative material. [Button's Proto Northern Chin](https://stedt.berkeley.edu/pubs.html) adds a different reconstruction and external comparisons. [Namkung's inventories](https://stedt.berkeley.edu/pubs.html) are useful for understanding transcription conventions. Together they support a bounded pilot without pretending to reconstruct the entire family at once.

The initial pilot should use **Kuki-Chin**. A second pilot can use **Burmish**, including the public data underlying [uncertainty-aware reconstruction](https://aclanthology.org/2023.lchange-1.3/), once exact dataset versions and permissions are checked. Do not require agreement between these independent subgroup projects as a precondition for verifying their internal derivations.

### Cross-branch tests need richer representations

Selected dossiers can then cross branch boundaries:

| Dossier | Relevant evidence | Representation required |
|---|---|---|
| Tibetan *wa* and later *-wa* | [Jacques 2009](https://shs.hal.science/halshs-00408281) | Historical stages; coalescence; evidence for secondary origins |
| Tibetan stem alternations | [Jacques 2012](https://crlao.cnrs.fr/wp-content/uploads/2025/02/jacques_2012_tibetan_internal_reconstruction_libre.pdf) | Whole paradigms; hypothetical prefixes; linked alternatives |
| *sr-* correspondences | [Jacques 2015](https://shs.hal.science/halshs-01287468) | Source-backed etymologies, explicit exclusions, branch-specific laws |
| Old Chinese *s-* | [Sagart & Baxter](https://hal.science/hal-00781153) | Competing voicing rules and derivational functions |
| Departing tone and suffixes | [Jacques 2016](https://shs.hal.science/halshs-01566036) | Several historical suffixes sharing a later reflex |
| Tangut and Khaling alternations | [Tangut](https://shs.hal.science/halshs-00351738), [Khaling](https://shs.hal.science/halshs-01486954) | Morphological boundaries, tone, coda loss and syllable reduction |

Old Chinese requires particular care. [The phonology sketch](https://hal.science/hal-03892358) distinguishes rhyme, script, Middle Chinese, dialect and loanword evidence. The [250-concept list](https://hal.science/hal-03099839) retains multiple lexical candidates and uses a particular Baxter-Sagart reconstruction. Written attestation, Middle Chinese transcription and an Old Chinese reconstruction must therefore be different data types, with linked evidence rather than implicit identity.

[Sagart et al.'s dated phylogeny](https://doi.org/10.1073/pnas.1817972116) is relevant to topology and data selection, but it does not provide a completed root phonology. A proof conditional on its tree remains conditional on that tree.

## 5. Formal-language theory and proof engineering

### Restrict the rule language before proving algorithms

[Kaplan & Kay](https://aclanthology.org/J94-3001/) supply a foundational finite-state treatment of restricted rewriting and two-level constraints. [Mohri 1997](https://aclanthology.org/J97-2003/) distinguishes sequential behavior and the conditions needed for transformations such as determinization. [Chandlee's dissertation](https://udspace.udel.edu/server/api/core/bitstreams/2552d413-efdd-4b50-ad95-b362c0482ff4/content) provides a more restrictive locality perspective.

The mathematical distinctions matter:

- Applying a rule simultaneously to the original input differs from scanning and feeding its output back into the same rule.
- A finite list of terminating passes is different from arbitrary rewrite closure.
- A deterministic forward function can have many inverse candidates.
- Deletion can make an inverse set infinite unless the hypothesis space is bounded or represented symbolically.
- Regular **languages** are closed under intersection; arbitrary rational two-tape **relations** are not. Do not transfer acceptor theorems to transducers without checking their hypotheses.
- Weighted algorithms need semiring assumptions, epsilon-path accounting and, for infinite sums, convergence conditions. See [Mohri's algorithms chapter](https://www.cs.brandeis.edu/~cs136a/CS136a_docs/Mohri_WeightedAutomataAlgorithms_Handbook.pdf) and [Mohri & Riley](https://cs.nyu.edu/~mohri/pub/wdisj.pdf).

The first complete implementation should consequently handle bounded contexts, a declared application direction, substitution and deletion, and a finite candidate pool. Insertion, bounded metathesis, copying and probabilistic paths are later milestones with separate contracts.

### Existing mechanized work reduces, but does not eliminate, the burden

[Doczkal, Kaiser & Smolka](https://www.ps.uni-saarland.de/~doczkal/regular/ConstructiveRegularLanguages.pdf), [Paulson](https://www.cl.cam.ac.uk/~lp15/papers/Formath/automata.pdf), and [Braibant & Pous](https://arxiv.org/abs/1105.4537) demonstrate proof architectures for regular languages, automata and reflective decision procedures in other systems. They provide designs and theorem statements, not directly importable Lean proofs.

Current Lean source inspection found useful automata definitions in mathlib and phonological rewrite/transduction infrastructure in **linglib**. The [pinned prior-art audit](05-prior-art.md) records exact commits, files and limits of the inspection. Neither dependency is imported into the small current prototype. Reuse should follow a semantic comparison and a successful build at a chosen commit.

[Lean 4's system paper](https://lean-lang.org/papers/lean4.pdf) supports a separation between executable definitions and checked proofs. [Mathlib](https://arxiv.org/abs/1910.09336), [library maintenance](https://arxiv.org/abs/2004.03673), [instance-parameter design](https://arxiv.org/abs/2202.01629), and [recent maintenance work](https://arxiv.org/abs/2508.21593) motivate pinning, linting and explicit interfaces. Empirical hypotheses should be visible parameters, not silently selected global instances.

## 6. Uncertainty and identifiability are central results

Fix a forward model `F` and observations `D`. Reconstruction should initially return the set of hypotheses in a declared pool that fit `D`. If distinct ancestors have the same observable consequences, no checker over those consequences can distinguish them. The existing Lean example exhibits exactly this after a merger.

This is not the claim that all reconstruction is futile. A new language, a dated spelling, an informative paradigm or a different independently justified model may distinguish previous alternatives. The crucial discipline is to state what changed. The proved monotonicity result applies only when the model and candidate universe remain fixed while observations are added.

[List, Hill, Forkel & Blum](https://aclanthology.org/2023.lchange-1.3/) explicitly warn that separate choices at multiple positions imply a Cartesian product. Thus “either *pat* or *pid*” is not faithfully represented by independent vowel and final-consonant alternatives, which also admit *pad* and *pit*. Our prototype gives a finite counterexample. Store joint hypotheses or coindexed constraints, and distinguish ensemble stability from posterior probability.

[Evans & Warnow](https://www.stat.berkeley.edu/~evans/668.pdf) show non-identifiability in a particular rates-across-sites setting. The lesson is to formulate identifiability obligations for each statistical model, not to generalize that result into an impossibility theorem about every linguistic date.

## 7. What this review supports—and what remains open

The literature supports a feasible first research program: a verified derivation and reconstruction core, source-rich comparative dossiers, and an interface for expert revision and untrusted automated proposals. It supports rigorous conditional results and useful negative results about ambiguity. It does not support a promised complete automatic reconstruction of PIE or Proto-Sino-Tibetan.

The immediate gaps are substantive: specialist validation of pilot etymologies; direct access to HPTB and Hill's 2019 monograph; fuller engagement with general textbooks by Campbell, Fox, Hock, and with PIE handbooks and dictionaries; broader Chinese-, Tibetan-, German- and French-language coverage; and deeper study of analogy, borrowing, semantic change and syntax before formalizing those modules. The retained French and Chinese papers improve coverage but do not erase the collection's English/open-access and author-availability biases.

The [architecture](02-formal-architecture.md), [case-study and evaluation protocol](03-case-studies-and-evaluation.md) and [milestones](04-delivery-plan.md) turn these findings into a bounded, falsifiable program. A successful project makes errors and disagreements easier to locate. It need not declare a single victorious proto-language to be scientifically valuable.
