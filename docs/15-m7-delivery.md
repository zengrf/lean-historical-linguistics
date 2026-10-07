# M7: reconstruction from daughter-language reflexes

M7 implements generative reconstruction of a bounded protolexicon. The input is
a table of proposed cognate sets, daughter-language forms, selected sound-law
models, and constraints on protoforms. The system constructs the complete
inverse language for each row, checks its representation in Lean, and enumerates
the compatible protolexicons. It does not require a list of candidate protoforms.

The [primary browser view](../web/index.html) is **Reconstruct a lexicon**. It
uses the existing original Kiwari assets. The earlier source-pool and paradigm
operations remain in their own tab. [Desktop](../reports/m7-ui/desktop.png) and
[mobile](../reports/m7-ui/mobile-night.png) previews come from actual browser runs.

## The reconstruction problem

Let \(\Sigma\) be the selected proto-segment alphabet, \(B\) the maximum
word length, and \(H\) the finite list of whole sound-law models. Each model
provides an ordered rule package for every daughter language. For cognate row
\(i\), define

\[
R_{h,i}=\{w\in\Sigma^{\le B}: |w|\ge b,\; P(w),\;
  \forall d,\ O_{i,d}\text{ matches }\operatorname{run}(h_d,w)\}.
\]

Here \(b\) is the minimum length and \(P\) the optional word-shape constraint.
The complete solution is the disjoint union of model-qualified assignments:

\[
\coprod_{h\in H}\{h\}\times\prod_i R_{h,i}.
\]

The same model applies to every row. A model with an empty inverse set for any
row contributes no full protolexicon. The system never combines one model's
first word with another model's second word. Counts distinguish models; equal
word lists under different models are different analyses.

This is a phonological reconstruction of the **supplied lexicon under the
specified hypotheses**. Cognacy, tokenization, historical applicability of the
rules and the suitability of the alphabet are input assumptions. An allowed
alphabet is not a claim that all its phonemes were present in the actual
protolanguage. The system does not infer unattested lexical items, discover all
possible sound laws, or prove a complete historical PIE or Sino-Tibetan grammar.
Morphology, analogy, loans, topology inference and productive tone systems are
outside this M7 input language. Existing separate paradigm operations remain
available. M5 and M6 still await their family-specialist assessments.

## What Lean proves and checks

M7 adds 28 theorem declarations; the repository audit now covers 185.

| Module | Result |
| --- | --- |
| [Compile.lean](../lean/Historical/Compile.lean) | For unconditional left-to-right M2 rule sequences, the compiled segment images give exactly the original interpreter's word output. Substitution, deletion and either pass convention are supported. |
| [Inverse.lean](../lean/Historical/Inverse.lean) | Consuming a prefix of the observed forms and the word-shape templates gives exactly the residual inverse problem. Enumeration includes every and only fitting bounded word. |
| [SearchGraph.lean](../lean/Historical/SearchGraph.lean) | A faithful graph recognizes exactly the specified transition system. The checker verifies every alphabet transition, including the absence of a transition, and every accepting state. |
| [Protolexicon.lean](../lean/Historical/Protolexicon.lean) | The reference prefix search is exact. Products of row languages give precisely the assignments permitted by one model; union over whole models preserves that requirement. |
| [LexiconInput.lean](../lean/Historical/LexiconInput.lean) | `compiled_request_complete` and `reference_request_complete` connect correctly bound graphs to the original M2 interpreter and the request's reflexes, alphabet, bounds and templates. |

The external Python solver supplies graph states, edges and accepting flags.
The native Lean executable recomputes their meanings. It also checks model and
row coverage, initial-state bindings, unique edge labels, and the topological
order of edges. Removing a possible branch, changing an observation, or rebinding
a graph to a different model cannot produce an accepted completeness claim.
Graph sharing preserves residual constraints; different reference machines
cannot share a trie unless their observation tuples agree.

The compiled fragment is deliberately restricted. A package containing a
context, an edge condition, or a right-to-left pass uses the original M2
interpreter in a bounded prefix trie. Nothing in that package is silently
discarded. This fallback is exact but may exceed the resource budget.

The mathematical results are kernel checked. Strict JSON parsing, the
request-to-graph bindings, native execution, integer counts, pagination, Python
orchestration and the browser are also tested infrastructure; their entire
implementation is not proved in Lean. In particular, the count recurrence and
indexing routines have exhaustive comparison tests, rather than a separate
formal cardinality proof. Native counts are computed from the checked graph
and independently compared with Python counts. Every displayed protoform also
receives a fresh native forward derivation and certificate check.

These choices follow the separation between rule semantics and finite-state
execution in [Kaplan and Kay (1994)](https://aclanthology.org/J94-3001/) and the
finite-state language-processing setting of
[Mohri (1997)](https://aclanthology.org/J97-2003/). This implementation is a
homomorphism compiler with a reference fallback; it is not a formalization of
those papers' general transducer compilation algorithms. Both works are already
in the retained research library.

## Input contract

[merger.json](../data/lexicon/merger.json) is a complete small request.
[LexiconInput.lean](../lean/Historical/LexiconInput.lean) defines the exact
interchange structures. Every field is required, including explicit nullable
fields; duplicate keys, unknown fields, omitted nulls and invalid UTF-8 are
rejected. A `pool` or `reference` field is not accepted.

| Field | Meaning |
| --- | --- |
| `schema_version`, `id`, `description` | Version `1.0.0`, stable identifier and description of the request's scope. |
| `languages` | Ordered daughter-language identifiers and labels. |
| `proto_inventory` | Distinct atomic segments. `kʷ` can be one segment; spaces separate tokens. Morpheme boundaries are not members of this alphabet. |
| `min_length`, `max_length` | Inclusive bounds on protoform length, measured in segments. |
| `phonotactics` | `null` for unrestricted shape, or a union of slot templates. `[[["p","b"],["a"]]]` permits `pa` or `ba`. `[]` permits no words; `[[]]` permits the empty word. Overlapping templates do not duplicate words. |
| `analyses` | Whole models with IDs, descriptions, source references and one ordered M2 `package` per daughter. All branch lists follow `languages`. |
| `entries` | Cognate-set IDs, meanings and one reflex per daughter, with source references. All reflex lists follow `languages`. |

A reflex `form: null` is a completely missing observation. `form: []` is an
observed empty output. `form: [null,"a"]` requires exactly two segments with
the second equal to `a`. Unknown cells do not match a morpheme boundary. A
literal `+` in an observed form is a boundary, not an unknown segment. Since
M7 generates boundary-free protoforms and M2 has no insertion, such a boundary
cannot be generated by the current model and will yield an empty inverse set.

The TSV header is `id`, `meaning`, then the daughter-language IDs in order.
Within a cell, tokens are separated by spaces. A blank cell is a missing word,
`?` is one unknown segment, and `∅` is an observed empty form. TSV imports retain
the supplied source reference plus row number; imported JSON retains individual
reflex references. Changing table text replaces the edited table's row
provenance with the stated import source. Original requests are retained in the
downloaded certificate.

The runtime profile allows 10,000 rows, 32 languages, 32 selected models, 64
proto-segments, a maximum length of 64, 256 slot templates, and at most 128 laws
per branch package. Each package has at most 256 symbols, including intermediate
ones. The default graph budget is 250,000 nodes and the search time budget is
60 seconds. A separate native-check process has a 60-second limit and a
128 MiB certificate input limit. These are acceptance ceilings, not promises
that every combination will finish. UI request bodies may be up to 16 MB.

An exhausted budget returns `complete: false`. It does not return a supposedly
complete empty answer. A successful empty search has `complete: true` and a
zero solution count.

## Running and enumerating

After the repository's Python setup:

```bash
cd lean
lake build
lake env lean Audit.lean > ../reports/lean-axioms-current.txt
cd ..
python scripts/check_proofs.py reports/lean-axioms-current.txt
python scripts/serve_ui.py --port 8765
```

Open <http://127.0.0.1:8765>. Choose an example or import a request, paste/import
the reflex table, select global models and daughter languages, and set the
alphabet, length bounds and optional templates. Unchecking a daughter removes
its observations; it does not create a new model. The results show which models
reconstruct every row and identify rows that exclude a model. Browse individual
row languages or whole protolexicons, inspect the derivations, or download the
complete factored search certificate. The local UI retains the four most recent
searches; download a result to keep it after eviction or server restart.

The CLI exposes the same operations:

```bash
python scripts/lexicon.py solve data/lexicon/merger.json --output /tmp/mergers
python scripts/lexicon.py words /tmp/mergers --model mergers --entry one
python scripts/lexicon.py lexicons /tmp/mergers --model mergers --offset 0 --limit 4
python scripts/lexicon.py solve data/lexicon/contextual.json --output /tmp/contextual
```

`solve` saves `forest.json` and `summary.json`. CLI browsing rechecks the saved
forest in Lean. Word order is deterministic prefix order using the declared
alphabet, with the empty continuation first. Protolexicons use mixed-radix
indexing in request row order, with the last row varying fastest. Offsets and
counts are decimal strings, so they do not lose precision in JavaScript.
At most 100 words or 10,000 reconstructed row words are materialized per page.

An external proposer can submit the same graphs or forward certificates:

```bash
lean/.lake/build/bin/lexicon_check --validate data/lexicon/merger.json
lean/.lake/build/bin/lexicon_check --check /tmp/mergers/forest.json
```

`--derive` takes `{request, proposals}`, where each proposal contains
`analysis_id`, `entry_id` and `word`. It returns native forward certificates and
acceptance results. `--check-proposals` takes `{request, proposals}` with each
element `{proposal, certificates}`; the certificates must identify the request's
exact packages and contain every rule pass. Generation success, certificate
acceptance and historical reference agreement are separate quantities in the
verification report. No statistical or neural score can bypass these checks.

## Examples and empirical scope

| Example | Result and interpretation |
| --- | --- |
| [Two mergers](../data/lexicon/merger.json) | A/B reflexes `pa`, `ta`. The merger model permits `{pa,ba} × {ta,da}`: four protolexicons. Identity permits one more model-qualified assignment. |
| [Global conflict](../data/lexicon/conflict.json) | Each word has candidates under some model, but neither model fits both rows. There are zero whole protolexicons. |
| [Deletion](../data/lexicon/deletion.json) | Bounded insertion of historically lost `h` in possible ancestors; unknown, empty and missing daughter forms remain distinct. Fifty whole assignments under the supplied bounds. The sound-law language itself still performs only substitution/deletion. |
| [Contextual change](../data/lexicon/contextual.json) | Intervocalic voicing uses the reference interpreter; one compatible protolexicon. |
| [Kuki-Chin ARM](../data/lexicon/kuki.json) | VanBik 2009, PDF p.93, entry 1: Mizo and Thado Kuki `báan`, projected to `b a a n` with tone omitted. With `b` and `ɓ` allowed and a stipulated merger, both `baan` and `ɓaan` survive. No source protoform is supplied. This does not decide the historical onset system. |
| [Indo-European LEG](../data/lexicon/pie.json) | Retained IE-CoR Old Irish `k o s`, Middle Welsh `k o ɨ s`, Neapolitan `k ɔ ʃː ə`. The existing M5 fitted correspondence packages, a 23-symbol alphabet and length ≤6 yield `k o ḱ s`. This conditional result is generated without a root pool; the packages remain fitted baselines with incomplete morphology and chronology. |
| [1,000 distinct rows](../data/lexicon/scaling.json) | Three synthetic daughters, eight proto-segments, four mergers, length six. Each row has 64 roots; one shared model permits `64^1000 = 2^6000` protolexicons in a 2,341-node graph. |

The example builder reads daughter-language source rows and existing rule
packages. It does not select candidates from source reconstructions. In the PIE
example, training provenance belongs to the reused M5 packages: removing the
candidate pool does not remove the fitted model's dependence on its training
material. Neither worked source example is an independent accuracy evaluation.

## Delivery evidence

All seven M7 criteria are represented in the
[milestone register](../data/milestones.json), including the four original
optimization/proposer criteria and the reflex-input, whole-lexicon and browser
requirements added for this implementation.

```bash
python scripts/build_m7_fixtures.py --check
python -m unittest discover -s tests -p test_m7.py -v
python scripts/verify_m7.py --check
python scripts/benchmark_m7.py --lean-version v4.19.0 --output /tmp/m7-benchmark.json
python scripts/verify_m7_ui.py --output /tmp/m7-ui
python scripts/verify_m7.py --check-report
```

The [native verification report](../reports/m7-verification.json) records 1,488
exact inverse-set comparisons across 12 cascades and all 121 words of length at
most four over three symbols, plus missing/unknown/boundary observations. It
separates generated proposals from accepted certificates, rejects 29 malformed
graph/parser cases and seven corrupted forward certificates, and exercises
complete empty results, whole-model conflicts, compiler/reference agreement and
incomplete searches. The independent baseline enumerates words first and uses
the existing Python forward interpreter; it does not use residual states.

The [local benchmark](../reports/m7-benchmark-local.json) documents the available host,
software, bounds, elapsed time and memory. It checks 1,000 distinct cognate rows
and 3,000 branch certificates against the original target of at least 1,000
certificates under 60 seconds and 2 GiB. The host is an iMac13,2 with an Intel
Core i5-3470 and 16 GiB RAM. This is an ordinary 2012 desktop, not a laptop.
The register now names ordinary development hardware to match the available
measurement; the original laptop-specific measurement has not been made. The
word-count, time and memory targets are unchanged. It also measures a smaller exhaustive
reference search before the symbolic search. Memory is a conservative sum of
the Python peak and largest sequential child peak. The 19
[browser checks](../reports/m7-ui/checks.json) exercise the actual API and native
Lean executable. Both Lean 4.19.0 and 4.34.1 run the native M7 checks and benchmark
in CI; the complete theorem audit is part of the repository's Lean jobs.

These engineering checks do not close the open linguistic review gates for M5
or M6. The delivery claim is verified bounded enumeration under explicit
phonological assumptions.
