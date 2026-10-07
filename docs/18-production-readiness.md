# Production release requirements

The implemented application is a **local research release candidate**. It has
durable projects, explicit philological annotations, a familiar comparative
table, conventional sound-law editing, checked bounded reconstruction,
interchange, resource limits, recovery and automated browser tests. It is not
yet an independently validated system for reconstructing unrestricted PIE or
Proto-Sino-Tibetan from raw multilingual wordlists.

The release target is a single researcher using a private macOS or Linux
workspace. A public or institutional multiuser deployment requires a different
operational boundary. No claim of user acceptance, penetration testing, or
specialist approval is inferred from automated tests.

## Obstacles addressed in this revision

| Obstacle | Delivered change | Verifiable acceptance evidence |
| --- | --- | --- |
| JSON-first experimental UI | Editable cognate-set table, variety and set editors, readable ordered sound changes, explicit hypothesis/observation/word-shape controls | `verify_workspace.py`: real browser workflow, keyboard navigation, mobile layout, original Kiwari assets |
| Loss of philological evidence | Printed reading, comparison segmentation, witness, locator, certainty, editorial notes, alignments and retained alternatives | TSV/CLDF round trips, escaped TEI export, browser variant swap and revision checks |
| Ephemeral projects and results | SQLite revisions, optimistic save conflicts, browser draft recovery, immutable job inputs, saved certificates | Concurrent-write, restart, restore, snapshot and tamper tests |
| Contextual search exhausts tiny budgets | Proved conservative prefix pruning followed by exact terminal checking | [19 new Lean results](16-contextual-pruning.md); [96 brute-force comparisons and a 1,000-row contextual benchmark](../reports/contextual-pruning.json) |
| Long jobs block research work | Two isolated processes, persistent queue, bounded search, cancellation and parent monitoring | Running and queued cancellation, incomplete-result and restart tests |
| Accidental public exposure | Loopback-only Waitress application, private launch session, Host/Origin/CSRF checks, CSP, private data directory | Negative HTTP tests; researcher data outside public Git |
| Irrecoverable local storage | Hash-checked backup of revisions and artifacts; tested restore into an empty directory | Database integrity and byte-preservation checks; refusal of overwrite and corrupt archives |
| Stale executable mistaken for current proof implementation | Recorded build toolchain, Lean source hashes and executable hash; refusal after changes | Stale-build test; `./workbench doctor`; setup build in both CI toolchains |
| Circular evaluation against supplied protoforms | Reference forms and partitions kept outside search requests; post-search native evaluation | Tests compare requests with/without references and retain out-of-scope denominators |
| Difficult installation and repeatability | One setup command, pinned dependencies and checked installer, recorded engine build, macOS launcher | Local setup/doctor run and CI installation/build workflow |

The contextual scale control completed 1,000 synthetic cognate sets with 2,000
branch certificates in 2.422 seconds, using 8,000 graph states and a conservative
277.2 MiB peak-memory bound on the recorded machine. It had one complete
wordlist. This is a controlled performance test, not a measure of historical
accuracy. Ambiguous contextual histories can still exhaust the declared budget.

## Requirements before broader production claims

Each gate has a concrete acceptance condition. These are outstanding work, not
silent exceptions to a production-ready label.

| Gate | Remaining obstacle | Required delivery and acceptance |
| --- | --- | --- |
| G1: PIE historical validity | Existing correspondence baseline has poor held-out agreement; fuller law systems, transcription and cognacy need adjudication | Resolve all discrepancies in the [20-set review packet](../reviews/pie-signoff.md); version each source-qualified rule history; freeze a new development/test protocol before tuning; publish exact-match, reference recovery, ambiguity and unsupported counts with every excluded record. A PIE specialist signs a dated review with unresolved disagreements retained. |
| G2: Sino-Tibetan historical validity | Proto-Kuki-Chin does not stand for Proto-Sino-Tibetan; branch topology, reconstruction level, morphology and tone remain disputed | Review the [Kuki-Chin and cross-branch packet](../reviews/sino-tibetan-signoff.md); state the source and level of every hypothesis; supply distinct, nonconflated branch models; evaluate held-out lexical families under each model. Relevant specialists sign the data and phonological analyses. |
| G3: broader phonological models | Generative M7 supports single-segment replacement/deletion; it excludes insertion, metathesis, a general phonological feature algebra and productive linked paradigms | Specify each new process and its interaction with direction, feeding and boundaries; prove a sound forward interpreter and sound/complete bounded inverse checker; compare every small-domain inverse set against an independent enumerator; add source-worked examples and adversarial certificates. M6 tone/morphology panels alone do not satisfy this M7 integration gate. |
| G4: hypothesis formation | Cognacy, segmentation and a finite set of ordered branch histories must currently be supplied | Any proposed cognate clustering, alignment or law induction must be labeled as a proposal, cite its evidence, preserve alternatives, and pass the existing exact checker after explicit selection. Evaluate on frozen source-disjoint data. Do not claim to infer all sound-law systems or all possible family trees. |
| G5: expert usability and accessibility | Automated browser checks do not show that philologists can complete their own work unaided | Execute the [researcher acceptance protocol](../reviews/workspace-acceptance.md) with at least five relevant researchers, including PIE and Sino-Tibetan experience; retain task completion, intervention, error and correction records. Resolve every data-loss or scope-misinterpretation issue; complete a keyboard and screen-reader audit. |
| G6: institutional / multiuser service | Loopback authentication has no accounts, roles, audit identities, TLS deployment or shared storage policy | Before permitting remote binds: implement authentication and authorization per project, authenticated workers, encrypted transport, account recovery, cross-user isolation tests, migration rehearsal, retention policy, operator metrics, backup restore drill and a deployment-specific security review. Current server cannot be safely repurposed by changing its bind address. |
| G7: distribution and long-running operations | Source installation is tested; a signed desktop package, Windows-native support, upgrade service and sustained production load are not | Package and sign per supported OS; reproduce clean-machine installation with no development tools exposed to users; run an eight-hour realistic mixed workload and crash/disk-full recovery trials; publish p95 latency, memory and resource-limit behavior. Windows users currently need Linux/WSL. |
| G8: interchange completeness | Partial cognacy and competing CLDF judgments need explicit import decisions; TEI export is limited and not schema-validated as a full edition | Add reviewed partial-cognacy/morpheme adapters with loss reports; validate the selected TEI customization against its schema; preserve bibliography and source identity across tool round trips. Maintain full project and original-source archives as the current lossless records. |
| G9: scientific scale and evaluation | Synthetic throughput does not bound realistic contextual ambiguity; exact arithmetic and pagination are tested executable code, not a separate proved cardinality theorem | Benchmark independently reviewed real datasets at 100, 1,000 and 10,000 sets, with ambiguity/deletion/context strata and several model counts; report completion and exhaustion rates, all bounds, peak memory and checking costs. Define acceptable resource ceilings before measurement. Prove count/unranking correspondence if claiming those operations are theorem-certified. |

G1, G2 and G5 require independent human work. No specialist or user study was
fabricated, and no third party was contacted by this implementation. G3/G4/G8
are research and format extensions with semantic choices that need review, not
ordinary deployment fixes. The current application supports a narrower useful
workflow while keeping those boundaries visible.

## Release decision

The current acceptance record consists of the Lean audit, exact inverse-set
comparisons, contextual benchmark, native workspace tests, real-browser evidence,
and exact-commit CI runs. A local release may be used to inspect consequences of
explicit hypotheses, provided the source interpretation and historical claims
remain subject to review. A general-purpose historical reconstruction production
release requires the relevant gates above to be closed with linked evidence.
