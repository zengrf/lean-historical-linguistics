# Prior art and dependency audit

Inspected on 5 October 2026 UTC. Source inspection is not a full code audit or an executed dependency build. Neither mathlib nor linglib is a dependency of the current prototype.

## linglib

Repository: [hawkrobe/linglib](https://github.com/hawkrobe/linglib), Apache-2.0. Inspected commit: [`a66829edd6d6eb9407ae763d203f231d5e5502ea`](https://github.com/hawkrobe/linglib/tree/a66829edd6d6eb9407ae763d203f231d5e5502ea).

The inspected tree contains substantial formal linguistics, including phonology, feature systems and subregular transduction. This is material prior art for a Lean formalization of sound change. The inspection does **not** justify claiming that this repository contains no related historical-linguistic work elsewhere in its large tree.

| File at pinned commit | Inspected functionality | Implication |
|---|---|---|
| [LocalRewrite.lean](https://github.com/hawkrobe/linglib/blob/a66829edd6d6eb9407ae763d203f231d5e5502ea/Linglib/Phonology/Subregular/LocalRewrite.lean) | Context elements, feature changes, deletion, replacement/copying, simultaneous single passes and cascades; locality/subsequential results with conditions | Strong candidate for reuse after comparing semantics and supported effects |
| [Transduction.lean](https://github.com/hawkrobe/linglib/blob/a66829edd6d6eb9407ae763d203f231d5e5502ea/Linglib/Phonology/Subregular/Transduction.lean) | Logical transduction using ordered copies of input positions, emission and locality results | Provides a broader representation, but reordering/metathesis needs careful treatment |
| [Segmental/Basic.lean](https://github.com/hawkrobe/linglib/blob/a66829edd6d6eb9407ae763d203f231d5e5502ea/Linglib/Phonology/Segmental/Basic.lean) | Partial feature bundles and natural-class machinery | Compare with the intended inventories rather than inventing a parallel feature hierarchy |
| [Latin/Phonology.lean](https://github.com/hawkrobe/linglib/blob/a66829edd6d6eb9407ae763d203f231d5e5502ea/Linglib/Fragments/Latin/Phonology.lean) | A particular finite Latin fragment | Not automatically a complete inventory for Latin, much less PIE |

`LocalRewrite` reads the original input within a pass. The inspected effects do not supply a general insertion, metathesis or coalescence engine. Its left-input-local result requires an appropriate absence of right context; the subsequential result handles bounded lookahead under its stated assumptions. Reusing a theorem requires retaining those assumptions.

The pinned toolchain was Lean 4.34.0. The README's dependency example and current toolchain did not use the same version. Pin the actual commit and verify builds instead of copying an illustrative dependency string.

**Next action at M1/M2:** build this commit in a clean environment, compare 20 reference rules, decide between a small dependency, upstream contribution or a documented adapter, and record licensing/attribution if code is reused. No source code has been copied into this project.

## mathlib

Repository: [leanprover-community/mathlib4](https://github.com/leanprover-community/mathlib4), inspected commit [`7d6757bc18680044fc0ff6efc8ee20494b408556`](https://github.com/leanprover-community/mathlib4/tree/7d6757bc18680044fc0ff6efc8ee20494b408556).

Source files inspected:

- [DFA.lean](https://github.com/leanprover-community/mathlib4/blob/7d6757bc18680044fc0ff6efc8ee20494b408556/Mathlib/Computability/DFA.lean): evaluation, accepted languages, reindexing and Boolean constructions.
- [NFA.lean](https://github.com/leanprover-community/mathlib4/blob/7d6757bc18680044fc0ff6efc8ee20494b408556/Mathlib/Computability/NFA.lean): nondeterministic transitions, evaluation, path witnesses and acceptance.
- [EpsilonNFA.lean](https://github.com/leanprover-community/mathlib4/blob/7d6757bc18680044fc0ff6efc8ee20494b408556/Mathlib/Computability/EpsilonNFA.lean): epsilon closure, paths and correctness of conversion to an NFA.
- [RegularExpressions.lean](https://github.com/leanprover-community/mathlib4/blob/7d6757bc18680044fc0ff6efc8ee20494b408556/Mathlib/Computability/RegularExpressions.lean): language interpretation, derivatives and executable matching with correctness results.

These are useful foundations for acceptors and regular preimage languages. They do not, merely by existing, establish a ready-made verified weighted two-tape sound-law compiler. A full transducer/library search and a dependency build remain part of M2/M7.

## Historical-linguistic implementations

| Work | Existing contribution | Proposed additional contribution here |
|---|---|---|
| [Reconstruction Engine, 1994](https://aclanthology.org/J94-3004/) | Bidirectional comparison/reconstruction, contextual correspondences and semantic processing | Kernel-checked contracts and typed evidence links |
| [PIE Lexicon, 2017](https://aclanthology.org/W17-0234/) | Executable finite-state PIE-to-daughter laws | Verified semantics, alternative analyses and independent evaluation |
| [DiaSim, 2020](https://aclanthology.org/2020.lt4hala-1.5/) | Debuggable forward sound-change cascades | Proof-connected diagnostics and certificates |
| [LingPy, 2013](https://aclanthology.org/P13-4003/) and [EDICTOR 3, 2024](https://aclanthology.org/2024.lchange-1.1/) | Comparison algorithms and expert editing workflows | Interchange and certificate checking; avoid replacing mature interfaces without need |
| [Uncertainty representation, 2023](https://aclanthology.org/2023.lchange-1.3/) | Fuzzy reconstructions and stability-based inference | Joint alternatives with precise semantics and proofs of scope |
| [Sound-law PBE, 2025](https://aclanthology.org/2025.acl-long.1432/) | LLM-generated sound-change programs | Restricted semantics and independently checked proposals |

No claim of being the first formalization, first computational comparative method, or first Lean phonology library is made. Any eventual novelty claim requires a refreshed search and comparison at publication time.
