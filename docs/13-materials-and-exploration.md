# Comparative materials and hypothesis exploration

The catalogue exposes **every row in three pinned CLDF datasets**, plus every
parseable entry in VanBik's initial-consonant chapter. The explorer selects
existing hypotheses and asks Lean to enumerate their reconstructions within a
declared finite space. The enlarged catalogue does not automatically supply
sound-change rules for its new records.

## Source coverage

| Source | Coverage in the catalogue | Source judgments retained |
| --- | --- | --- |
| [IE-CoR](../data/upstream/iecor/README.md) | 25,731 forms; 160 varieties; 170 concepts | 25,741 cognate memberships; 4,981 cognate sets; published root forms and reconstruction levels; comments, uncertainty and 1,036 loan-event rows |
| [Sagart, Jacques, Lai and List](../data/upstream/sagartst/README.md) | 12,179 forms; 50 varieties; 250 concepts | 12,179 cognate memberships in 5,120 sets; loans, sources, transcription and subgroup labels |
| [Hill–Gong Burmish](../data/upstream/hillburmish/README.md) | 4,032 forms; nine source varieties/nodes; 819 concepts | Original cognacy and partial-cognacy columns, loan flags, segmentation, sources and ProtoBurmish forms |
| [VanBik 2009](../library/open/vanbik2009.pdf) | 1,344 parsed entries; 6,711 reflex records; 12 varieties | 1,161 PKC, 126 PCC and 57 PNC entries; original forms, glosses, source pages, stem labels, allofamy markers and discussion flags |

These are **48,653 source form records**, not 48,653 distinct lexemes. Varieties,
forms and analyses overlap between datasets; source-qualified IDs keep their
provenance separate. Burmish has no separate CLDF cognate table in this snapshot:
its embedded cognacy columns remain available without inventing a new set table.
Sagart's 5,120 set identifiers are cognacy judgments, not 5,120 reconstructed
Proto-Sino-Tibetan words. The catalogue assigns no blanket phonetic-attestation
status: ProtoBurmish is reconstructed, and Old Chinese and Tangut pronunciation
transcriptions require their source analyses.

The [coverage report](../data/materials/coverage.json) lists every variety and its
record count. IE-CoR's source labels cover Albanian, Anatolian, Armenian,
Balto-Slavic, Celtic, Germanic, Hellenic, Indo-Iranic, Italic and Tocharian.
The broader Sino-Tibetan source includes Sinitic, Tibetan, Burmish, Loloish,
Kiranti, rGyalrong, Qiangic, Tangut, Tani, Jingpho, Nungic, Chin/Mizo,
Tibeto-Kinauri and other source labels. These labels are preserved as source
metadata; they do not establish a preferred higher-level subgrouping.

The Sagart dataset is pinned to
[`c6df5f38eeef9cf40dbb939e6515f8bf8cd04246`](https://github.com/lexibank/sagartst/tree/c6df5f38eeef9cf40dbb939e6515f8bf8cd04246).
Its original tables, bibliography, metadata, contributors and CC BY 4.0 license
are retained with [file hashes](../data/materials/sources.json). IE-CoR and
Burmish retain their [existing pins](../data/upstream/manifest.json).
The catalogue reads the original CSV strings without normalizing them. The
VanBik expansion reuses the M6 extractor, preserves its ten omission records,
and does not promote unreviewed PDF extraction to verified transcription.

## Browse the material

Commands below run from the repository root after installing `requirements.txt`.

```bash
python scripts/materials.py coverage
python scripts/materials.py search --dataset iecor --set 21
python scripts/materials.py table --dataset iecor --table cognatesets --id 21
python scripts/materials.py table --dataset iecor --table loans --limit 0
python scripts/materials.py search --dataset sagartst --language Japhug --text hand
python scripts/materials.py search --dataset hillburmish --language ProtoBurmish
python scripts/materials.py search --dataset vanbik2009 --set 1
```

Search returns the exact form row, language and concept metadata, cognate
memberships, and available root/loan records. VanBik results include the entry's
reconstruction level and extraction notes. `--limit 0` returns every match;
otherwise the output explicitly reports truncation and the total match count.
The `table` command exposes other source tables without interpreting their
columns. Identifiers are specific to their source; matching an ID across
datasets does not establish identity or cognacy.

## Select hypotheses and enumerate reconstructions

Two kinds of completeness are available:

1. **Declared-pool enumeration:** check every form in a finite, explicitly listed
   pool against the selected sound-change packages and observed reflexes.
2. **Bounded word enumeration:** check every permitted word over a declared
   inventory up to a length bound, for every selected whole analysis.

Neither enumerates every historically conceivable proto-language. Both retain
multiple solutions. An empty result is conclusive only inside the declared
space after successful exhaustion. Budget limits, deadlines and process errors
do not establish absence. No probability or historical preference is implied by
the number of surviving candidates.

Build the executables with `cd lean && lake build`, then return to the repository
root. The macOS compatibility command is documented in the main README.

### Published candidate pools

There are **509 registered queries**: 270 PIE, 40 Latin control, 198 Kuki-Chin,
and one source-inspired Tibetan merger control. Every query is selectable;
their original source and modeling limitations remain in force.

```bash
python scripts/explore_reconstructions.py list --dataset pie
python scripts/explore_reconstructions.py pool --dataset pie --case set-21 \
  --hypothesis identity --hypothesis correspondence --report /tmp/pie-21.json
python scripts/explore_reconstructions.py pool --dataset kuki-chin \
  --case vb-1-unmarked --hypothesis correspondence --scope northern-only
python scripts/explore_reconstructions.py pool --dataset tibetan-merger \
  --case merged-affricate-pool --explain '["p"]'
```

`identity` and `correspondence` are the existing experimental baselines. They
are not complete PIE or Kuki-Chin sound histories. The published-root pools
include reference forms; recovering a member is not independent discovery of
that form. Cases without an executable model are searchable in the material
catalogue but are not silently assigned these models.

The merger example returns both `ndz` and `dz`: the two modeled daughter
reflexes cannot distinguish them. `--explain '["p"]'` asks Lean to derive a
specific proposal through each branch. Its checked traces show which observed
outputs fail to match. A proposal outside the pool can be explained if it uses
the package's valid symbols, but that does not add it to the pool. Explanation
results explicitly report pool membership and observation agreement.

Selecting multiple hypotheses reports their candidates separately, the union
with hypothesis membership, and the intersection. Comparison stays within one
named case and observation scope. Source-qualified M6 nodes are validated by
the Lean wrapper; PKC and different authors' PNC nodes remain distinct.

### Whole joint analyses and bounded enumeration

The default example is the source-inspired Old Chinese voice-paradigm onset
control from M6. It compares the complete N-anticausative and s-devoicing
analyses. The observation axes are **two paradigm cells**, not two daughter
languages; the result concerns basic onset projections, not full word histories.

```bash
python scripts/explore_reconstructions.py list
python scripts/explore_reconstructions.py bounded
python scripts/explore_reconstructions.py bounded \
  --choose voice-analysis=N-anticausative --report /tmp/voice-N.json
python scripts/explore_reconstructions.py bounded \
  --choose voice-analysis=s-devoicing --save-request /tmp/voice-s-input.json
python scripts/explore_reconstructions.py bounded --budget 0
```

Both analyses together return `(N-anticausative, p)` and `(s-devoicing, b)`.
Selecting one retains its entire linked paradigm. Choices are OR within a
group and AND across groups, restricted to the joint analyses actually declared
in the specification. Incompatible choices produce an input-selection error,
not a claim that no reconstruction exists. `--analysis ID` selects named whole
analyses directly.

`--spec PATH` accepts another M4 specification. Its explicit inventory, length
bound, observations, ordered rules, alternative analyses and evidence references
define the question. See [bounded reconstruction semantics](bounded-reconstruction-semantics.md).
The current profile permits at most 20,000 raw word/analysis combinations; a
larger space is reported as incomplete. The search is not pruned or resumable.
No default inventory is inferred from an arbitrary source spelling.

### Sensitivity and reproducibility

`pool --omit-doculect ID` withholds an observation for a sensitivity analysis;
the report names every withheld axis. At least two observations must remain in
the current pool interface. This does not classify an item as a loan or revoke
its source judgment. For PIE pools, observation IDs denote individual source
form rows, so inspect the selected request to identify the axis being withheld.

Every run returns the exact selected request, its SHA-256 hash, the original
input hash and the Lean result. `--save-request` exports a directly executable
Lean input; `--report` saves the complete result. Lean output is checked against
the independent Python interpreter. Bounded searches with positive cooperative
deadlines retain Lean's incomplete-prefix result; they are not compared against
a deterministic Python prefix. Exit codes are 0 for complete results, 1 for a
Lean-invalid bounded specification, 2 for errors and 3 for incomplete searches.

## Linguistic coverage and remaining work

The retained library and literature review supply the broader theoretical
material. Structured data coverage, executable linguistic models and specialist
assessment are separate deliverables:

| Area | Available material | Remaining formal/empirical work |
| --- | --- | --- |
| IE vocabulary and branches | Complete pinned IE-CoR source tables; branch and source metadata | Wider semantic coverage beyond the 170-concept source, additional attestations and specialist reconciliation of disputed cognacy |
| PIE phonology and chronology | M5 Ringe chronology fragment; Kloekhorst Hittite onset projections; recorded alternative attribution | Full daughter-specific sound histories, accent/ablaut, syllabification and interactions with morphology |
| PIE morphology | M5 source-backed dispute records and joint evidence representation | Productive inflectional/derivational analyses and conditioning by morphological environment |
| Sino-Tibetan vocabulary | Complete pinned Sagart and Burmish datasets; expanded VanBik chapter 4 | More language varieties and lexical domains; source-specific transcription review and reconciliation |
| Kuki-Chin rhymes, tones and stem alternation | Complete retained VanBik/Button books; extracted source strings and M6 parsing diagnostics | Structured transcription of VanBik chapters 5–6, Button comparisons, phonological alignment and executable tone/stem models |
| Cross-branch reconstruction | Thirty M6 dossiers with source pages, alternatives, topology assumptions and discriminating evidence | More lexical families and explicit branch histories; no automatic promotion of PKC, PNC or PTB reconstructions to PST |
| Reconstruction search | Pool and bounded enumeration; joint analyses; checked derivations | Larger search spaces, compositional morphology, chronology alternatives and a reviewed inventory of historical hypothesis packages |

The new catalogue is comprehensive **for the pinned CLDF snapshots**. It is not
a complete inventory of either family, a full transcription of every retained
book, or a comprehensive executable reconstruction of PIE/PST. The M5/M6
corpora, splits and review requirements remain frozen and unchanged. Their
specialist signoffs remain pending.

## Useful next features and acceptance criteria

These are proposed extensions, not delivered features. They follow from the
comparative method's attention to recurrent correspondences, conditioning,
shared innovations, morphological structure and source criticism; see the
repository's [primary-source terminology readings](../bibliography/terminology-readings.json)
and [literature review](01-literature-review.md).

| Feature | Research use | Verifiable delivery goal |
| --- | --- | --- |
| Minimal conflicting evidence | Explain why a hypothesis yields no candidate | Return inclusion-minimal sets of observations inconsistent within the declared space; verify inconsistency and that removing any one observation restores a candidate |
| Discriminating observations | Decide which additional attestation or variety would distinguish surviving reconstructions | Partition candidates by predicted held-out reflex; independently verify every prediction and report when no available observation distinguishes them |
| Observational equivalence | Avoid treating undistinguishable analyses as a unique historical answer | Retain all analysis identities while grouping those with identical predictions on a declared domain; prove the equivalence relation and test its computed classes |
| Chronology constraints | Compare competing orders of sound changes | Enumerate all orders satisfying a supplied partial order; reject cycles; certify each derivation and distinguish counterfeeding/feeding outcomes |
| Alternative cognacy, loans and segmentation | Test how source disputes affect reconstruction | Bind alternatives as whole analyses, retain attribution and loan status, and show candidate differences without silently relabeling evidence |
| Morphology and tone | Model paradigms and conditioned changes beyond segment replacement/deletion | Add explicit semantics, soundness proofs and source-worked controls before evaluating stem alternation, tone correspondences or affix histories |
| Larger and resumable search | Explore useful bounds without confusing interruption with exhaustion | Prove pruning preserves every solution; bind checkpoints to input hashes; make resumed results exactly equal uninterrupted enumeration |
| Review interface | Inspect sources, assumptions and derivations together | Link each displayed claim to a source locator and each output to its certificate; export the exact query and preserve unresolved alternatives |

The first three offer the most immediate research value after enumeration:
they explain failure, guide evidence collection, and expose the limits of
identification. A graphical interface can then present these operations without
changing the underlying scientific claims.

## Verification

```bash
python scripts/build_materials.py --check
python -m unittest discover -s tests -p test_explorer.py -v
python scripts/verify_explorer.py --check
```

The tests check retention of every CLDF form row, reconstruction-level handling,
selection of all 509 registered queries, whole-paradigm dependencies, unknown
choices, ambiguity, withheld observations, duplicate JSON keys, timeouts and
tampered candidate lists. The [verification report](../reports/materials-and-exploration.json)
records CLDF validation, source hashes and ten Lean executions checked against
the independent interpreter. The dedicated workflow repeats extraction and
execution under Lean 4.19.0 and 4.34.1.
