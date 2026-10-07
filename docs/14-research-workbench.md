# Evidence analysis and the research workbench

The primary view now supports [M7 generative protolexicon reconstruction](15-m7-delivery.md) from reflex tables. This document describes the separate source-pool, paradigm and evidence-analysis operations.

The workbench adds five operations to the existing finite reconstruction
engines: minimal conflicting evidence, discriminating predictions,
observational equivalence, chronology enumeration, and linked morphology and
tone. Each operation is available through the command line and the local
browser interface. [Research.lean](../lean/Historical/Research.lean) and
[Paradigm.lean](../lean/Historical/Paradigm.lean) contain 20 new theorems;
[the native verifier](../scripts/verify_research.py) compares the executable
results with an independent Python interpreter.

## Open the interface

From a prepared checkout, build the Lean executables and start the server:

```bash
cd lean
lake build
cd ..
python scripts/serve_ui.py --port 8765
```

Open <http://127.0.0.1:8765>. See the [repository setup](../README.md#reproduce-the-current-checks)
for Python dependencies and the Lean 4.19 compatibility command.
The server uses Python's standard library, serves only on loopback, and requires
no frontend build tool or external font service. Reconstruction requests run
the compiled Lean programs and compare their outputs with Python. A missing
binary produces an error, never a substitute result.

The interface loads the original styles, textures and bundled Garamond fonts
from [Kiwari](https://github.com/zengrf/kiwari-slides/tree/a0be327572f2fec8a6080bb74e1334442db57927),
the reusable toolkit for the personal website's aesthetic. The 11 upstream
files in `web/vendor/kiwari` are unmodified and pinned to commit
`a0be327572f2fec8a6080bb74e1334442db57927`. The source URL and SHA-256 hashes
are in [upstream.json](../web/vendor/kiwari/upstream.json); MIT and font OFL
licenses are retained. `python scripts/verify_theme.py` checks the complete
file inventory, hashes, font paths and stylesheet imports. The app loads the
upstream CSS directly, with no separate copy of its palette or textures.
[style.css](../web/style.css) adapts the slide dimensions to a scrolling
application and lays out the controls; the original paper, timber, lattice,
font families and `data-time` day/dusk/night colors come from the toolkit.
Layouts accommodate narrow screens; tabs support arrow keys, Home and End.

In **Reconstruct**, use the three numbered steps:

1. **Choose the material.** Search by meaning or example name, then select a
   word or worked example. Pool titles and daughter-language labels come from
   the retained sources; original IDs remain in requests and exports.
2. **Set the constraints.** Allowed analyses are alternatives (OR). Required
   daughter forms are joint requirements (AND), evaluated under the same
   analysis. Unchecked forms impose no constraint. Require all/none and reset
   controls make these choices explicit. The candidate space is visible:
   inspect every member of a source pool, or set allowed proto-segments and
   maximum token length for a bounded model. The latter includes the empty
   word and every shorter sequence; a morpheme boundary counts as one token.
3. **Enumerate all allowed reconstructions.** The query summary states what
   will be tested. Results list each distinct proto-form once, with all its
   compatible analyses and their derivations beneath it. Equality for this
   display uses exact structured proto-forms, not their rendered spelling.
   Counts also report form–analysis combinations, so distinct analyses remain
   identifiable. Unchanged rule passes remain in full certificates.

For example, the default tone query requires Hakha Lai F and permits both
source readings: it returns **three tonal reconstructions** represented by
five form–analysis combinations. Requiring Mizo R leaves **one tonal
reconstruction**, still permitted by both analyses. These results enumerate
source-specific tonal categories, not complete proto-language words.

Every successful reconstruction query exhausts its specified finite candidate
space. Conflict diagnosis is a separate subset search: a curtailed diagnostic
budget does not make an already exhaustive empty reconstruction result
partial. Its possibly incomplete conflict list is labeled separately. A
conflict's **Uncheck** control changes that requirement and clears the old
result; it does not silently run a modified query. Prediction comparisons and
the evidence matrix are available below the primary result list.

Bounded controls may select a subset of the model's proto-segment inventory
and a maximum length from 0 to 16. The server rejects an empty inventory,
unsupported segments and more than 1,024 form–analysis combinations before
execution. It changes only the input word space and runtime candidate budget;
branch rule packages stay intact. The effective specification goes through
the existing native enumerator and independent interpreter. Original bounds
are restored by reset.

Changing a constraint clears the prior result and disables its export;
superseded requests cannot populate results for newer selections. Export
contains the submitted query, effective input specification, complete
histories and checked result. **Advanced** offers the diagnostic budget and
JSON import/export; duplicate keys and non-JSON constants are rejected.
These browser checks are a starting point for accessibility review, not a
claim of complete accessibility certification.

In **Chronology**, choose precedences between the declared rule blocks.
Every permitted order is evaluated on the declared probes. In **Source
materials**, search and paginate the 48,694 retained source form records and
inspect their original fields, cognacy judgments, source locators and loan
annotations where the source supplies them. The retained snapshots have wider
coverage than the executable models; see [the coverage table](13-materials-and-exploration.md).

## The finite question

A *history* is a pair of a declared whole analysis and a candidate input.
Two analyses remain distinct even when they share an input or predict the
same reflexes. Observation axes may be daughter reflexes or cells of a linked
paradigm. Source-qualified ancestor nodes and the existing scoped pool checks
are retained. The expanded material catalogue does not infer cognacy or
silently supply sound changes.

The evidence layer accepts at most 1,024 histories, 16 axes and 12 selected
observations. It requires a nonempty history universe; an incompatible model
selection is an input error. For bounded reconstruction, the underlying M4
enumeration must finish before the evidence analysis begins. Exhausting that
enumeration or timing out yields an incomplete result. The richer evidence
analysis has a smaller profile than the original M4 engine, whose independent
20,000-combination interface remains available.

### Minimal conflicting evidence

For a set of selected observations, the engine finds the histories agreeing
with every observation. If none survive, it enumerates subsets of the selected
observations and returns each inconsistent subset for which every single
deletion is satisfiable. Agreement is monotone under removal of observations,
so every proper subset is satisfiable as well. Minimality is by inclusion,
not by minimum cardinality.

`minimalConflict_iff` connects the Boolean check to its proposition;
`minimal_conflict_proper_subset` proves the proper-subset consequence.
`mem_subsets` and `full_conflict_enumeration_correct` establish complete
enumeration of minimal conflicts as sublists of the ordered selected axes.
The maximum subset space is 4,096. A smaller subset budget yields sound
reported conflicts but an incomplete list. The complete survivor set is still
reported; an incomplete conflict list is not presented as proof that no
conflict exists. If a history already satisfies all observations, monotonicity
excludes every inconsistent subset without enumeration.

### Predictions and equivalence

The engine groups surviving histories by identical predictions on the selected
axes. `equivalent_refl`, `equivalent_symm` and `equivalent_trans` prove the
equivalence relation; `class_members_correct` characterizes membership in a
computed class. A known segmental observation with unobserved tone projects
away tone when computing equivalence. M4's unknown segment positions are
likewise projected away. The empty selected domain yields one class containing
all histories.

For each withheld or unobserved axis, the engine partitions the same survivors
by the full predicted output. It reports the number of unordered history pairs
with different predictions. The interface sorts probes by that count and
explicitly identifies nondiscriminating probes. Counts depend on the declared
analysis inventory; they are not probabilities or information gain under a
prior. Every underlying output comes from a checked forward derivation.
Existing withheld observations and prospective unobserved axes remain
distinguishable in the exported metadata.

### Chronology

The chronology input declares at most six named blocks, with at most 64 sound
rule passes in total and 1–16 probe words. Internal order within a block stays
fixed. The enumerator generates every permutation satisfying the supplied
earlier/later constraints. `order_enumeration_correct` characterizes its
outputs and `order_respects_constraints` proves the precedence condition.
The validator requires distinct known block IDs. A cycle, including a
self-edge, gives an explicit `cyclic: true` result with no orders. Malformed
rule blocks are still rejected even if a cycle prevents their use.

Each order produces a restaged rule package and checked derivations for every
probe. An order may satisfy the precedence constraints yet fail the observed
reflexes; both facts are reported. No precedence is inferred from a desired
answer. The source-inspired Germanic control permits all six orders of the
Grimm fragment, Verner fragment and initial-stress block. Only
Grimm → Verner → stress matches both accent-marked VCV observations. This
inherits the restricted Ringe fragment from [M5](11-m5-delivery.md), not a
complete PIE-to-Germanic sound history.

### Morphology and tone

A finite paradigm shares one input stem and optional tonal category across
all its cells. Each cell declares these operations, in order:

1. An exact lexical allomorph map, if the input has a listed allomorph.
2. An ordered stem-level sound package.
3. Prefix and suffix concatenation, with explicit morpheme boundaries.
4. An ordered word-level sound package.
5. Sequential tone-category rules, whose segmental conditioning is explicitly
   evaluated on either the stem before affixation or the final surface word.

Tone rules test optional initial and final segment classes, ignoring morpheme
boundaries for those tests. They change source-specific category labels;
they do not equate a label with universal pitch, infer tone association or
model arbitrary autosegmental spreading. Rules may feed later tone rules.
An unknown input tone stays unknown. An expected `tone: null` imposes no tonal
constraint; an expected cell of `null` imposes no segmental or tonal constraint.
An observed empty segment string remains an actual empty-string constraint.

`tone_derivation_iff` and `realization_correct` connect the executable
operations with relational derivations. `realization_deterministic` proves
determinacy. `agrees_iff` handles partially observed forms, and
`paradigm_reconstruction_correct` proves soundness and completeness within the
declared root pool. Generated certificates retain allomorph input, affixes,
stem and surface traces, tone rules and conditioning stages. Each is compared
with the independent interpreter. The parser, UI, orchestration and all their
connections are tested infrastructure; they are not covered by one end-to-end
software correctness theorem.

The native paradigm profile permits 256 distinct inputs, 16 whole analyses,
16 cells per analysis, 256 exact allomorph entries per cell and 32 tone rules
per cell. Input and declared allomorph words are at most 100 tokens; affixes
together are at most 100 tokens. The evidence interface additionally imposes
its 1,024-history bound. The segmental packages retain M2's own validation
rules. These are finite, explicit paradigms rather than a learned productive
grammar of either family.

## Worked sources and controls

The [source reading record](../data/research/source-readings.json) identifies
the VanBik PDF hash and examined pages. Tables 164 and 166 were also inspected
as rendered pages. The models are separately attributed and generated in
[build_research_examples.py](../scripts/build_research_examples.py).

| Case | Source and interpretation | Verified outcome |
| --- | --- | --- |
| Smooth nominal tones | VanBik Table 164, printed p. 454 / PDF p. 482; WATER [243], PDF p. 485; conflicting Table 166 reading, printed p. 465 / PDF p. 493 | Hakha Lai alone leaves five history/reading pairs in one class; Mizo distinguishes eight of their ten unordered pairs |
| ATTACH [2] | VanBik printed p. 65 / PDF p. 93: PKC Form I `*ɓeel`, Form II `*ɓelʔ`, Mizo paired stems and Hakha Lai invariant stem | One shared root satisfies all four displayed cells; the alternative root fails Form I |
| Affixes, alternation and tone | Explicitly synthetic singular/plural control | Prefixation, suffixation, vowel alternation, devoicing and pre-devoicing tonal conditioning compose; the negative root is rejected |
| Conflicting observations | Explicitly synthetic identity branches: A=`p`, B=`b`, C=`p` | Exactly {A,B} and {B,C} are minimal conflicts; withholding B restores `p` |
| Two voice analyses | Existing M6 whole analyses from Sagart–Baxter | Both analysis identities and their different candidate onsets survive; selecting one keeps its entire paradigm |
| Grimm, Verner and stress | Existing M5 source-inspired VCV controls | All six orders checked; one matches both observations; a precedence cycle yields no order |

VanBik Table 164 gives Hakha Lai **L** for PKC tone 2; Table 166 prints **F**,
although the latter page's entry [7] gives L. The second analysis changes only
that printed Hakha correspondence and retains Table 164 for the other
branches. It is an explicit hybrid reading for comparison, not an assertion
that Table 166 supplies an alternative complete system. No emendation or
specialist adjudication is claimed. The example uses four daughter varieties,
excludes Khumi's conditioned variants, and projects away segments.

The ATTACH example stipulates lexical allomorphy from that entry; it does not
infer a productive alternation. Mizo `h` is a source-spelling projection of the
displayed stem. Tones are omitted there. VanBik's discussion on PDF p. 38
precludes identifying Form I/II generally with tense or transitivity. Verbal
tone behavior, sandhi, polysyllabic association and full morphology remain
outside these controls. M5/M6 specialist reviews remain pending.

## Command-line use

```bash
python scripts/research.py pool --dataset tibetan-merger --case merged-affricate-pool
python scripts/research.py paradigm --input data/research/tone-paradigm.json \
  --observe Hakha-Lai --report /tmp/tones.json
python scripts/research.py paradigm --input data/research/stem-paradigm.json
python scripts/research.py bounded --input data/research/evidence-control.json
python scripts/research.py bounded --input data/research/evidence-control.json --observe A --observe C
python scripts/research.py chronology --input data/research/germanic-chronology.json
```

Repeat `--hypothesis ID` to select whole analyses. Repeat `--observe ID` to
choose constraining observations. Omitting `--observe` selects every available
observed axis. The browser/API also accepts an empty selected list. For
chronology, edit `constraints` in a copy of the source input or use the
checkboxes. `--subset-budget N` bounds conflict enumeration. Exit codes are
0 for complete results, 2 for invalid requests or execution errors, and 3
for incomplete enumeration. The native `research_check` executable accepts
`--matrix`, `--paradigm` or `--chronology` with a JSON path; native validation
failures return 1 and invocation/I/O failures return 2.

## Delivery checks

| Deliverable | Acceptance evidence |
| --- | --- |
| Minimal conflicts | Proper-subset and enumeration theorems; all 256 three-history/two-axis matrices across selected domains; two-conflict worked control; incomplete-budget control |
| Discriminating predictions | Exact Lean/Python derivation comparison; tone example with pair counts 8, 6, 6; nondiscriminating and missing-tone tests |
| Equivalence classes | Equivalence and membership theorems; history identities retained; empty-domain and unobserved-component tests |
| Chronology | Enumeration and precedence theorems; all 874 permutations across sizes 0–6; source-inspired derivations, counterfeeding order and cycle controls |
| Morphology and tone | Five semantic theorems; source-worked tones and lexical stems; synthetic affixation, stage conditioning and missing-tone controls |
| Constraint interface | OR across selected whole analyses; AND across required forms; editable bounded word space executed in Lean; distinct proto-forms retain all compatible histories; explicit conflict relaxation; changed inputs invalidate results |
| Theme reuse | Eleven byte-for-byte Kiwari files, source commit and SHA-256 manifest, MIT/OFL licenses; browser checks confirm original texture CSS and actual local font loading |
| Interface and reproducibility | Real-browser operations against Lean, JSON import/export, source search/pagination, keyboard tabs, four responsive widths and theme checks; saved screenshots and input hashes |

```bash
python scripts/verify_theme.py
python scripts/build_research_examples.py --check
python -m unittest discover -s tests -p test_research.py -v
python scripts/verify_research.py --check
python -m pip install -r requirements-ui-test.txt
python scripts/verify_ui.py --output /tmp/research-ui
```

The [native report](../reports/research-workbench.json) records all execution
digests, theorems and input hashes, including 20 integration runs and 23
rejected inputs. The [browser report](../reports/ui/verification.json) records
the actual local browser version, executed checks and screenshot paths.
[Desktop](../reports/ui/desktop.png) and [mobile](../reports/ui/mobile.png)
previews were visually inspected. CI repeats native and browser checks under
Lean 4.19.0 and 4.34.1. Broader milestone regression checks and the complete theorem
dependency audit remain required.

Selecting alternative loan/cognacy/segmentation judgments in a dedicated
editor, proving safe pruning, and resuming larger searches remain future work.
Current imports can express supplied whole alternatives; they do not infer
those judgments or expand the finite search profile.
