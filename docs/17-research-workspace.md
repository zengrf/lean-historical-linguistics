# Local research workspace

The workbench is a private, persistent application for explicit comparative
analyses. Its principal view is a cognate-set table. Researchers record source
readings, edit sound-law hypotheses, select observations and word constraints,
and enumerate the reconstructions allowed by those assumptions.

This release is a candidate for supervised local research use. Automated checks
do not constitute a historical-linguistic assessment or a usability study. The
[release requirements](18-production-readiness.md) distinguish those gates.

## Install and open

Use Python 3.12 on macOS or Linux. From this repository:

```bash
./workbench setup
./workbench
```

Setup creates `.venv`, installs the pinned Python dependencies, installs elan
4.2.4 under `.tools/elan` when needed, checks the downloaded installer's SHA-256,
and builds the Lean executables. It leaves shell startup files unchanged. Lean
4.34.1 is the default; macOS 10 uses the tested 4.19.0 compatibility build. The
installer digests come from the [official elan release](https://github.com/leanprover/elan/releases/tag/v4.2.4).
An existing toolchain manager can be used with
`./workbench setup --use-installed-elan`. `WORKBENCH_PYTHON` selects the Python
used for setup. This is source installation, not a signed desktop distribution.

On macOS, `Workbench.command` opens the installed application by double-click.
For a terminal without an automatically opened browser:

```bash
./workbench serve --port 8765
./workbench doctor
```

Open the private launch link printed in that terminal. The link establishes an
HttpOnly, SameSite browser session; its credential is then removed from the
address bar. Restarting the application invalidates that session. The server
binds only to `127.0.0.1`. It uses Waitress, checks the Host and Origin headers,
requires a session token for workspace changes, and sets a restrictive content
security policy. It is not a shared multiuser server. Keep the launch link and
workspace backups private. Another process running as the same OS user is
outside this boundary.

The default data directory is `~/Library/Application Support/ComparativeReconstruction`
on macOS and `~/.local/share/comparative-reconstruction` on Linux. `--workspace`
selects another directory. Research data stay outside the public Git repository.
Stop the terminal process with Ctrl-C after saving.

## A comparative study

1. Create a project from a labeled example, or import a wordlist with explicit
   cognate membership. The PIE example is a fitted baseline; the Kuki-Chin
   example has the source scope stated in its description. Synthetic examples
   are identified as such.
2. In **Wordlist**, enter one proposed cognate set per row and one daughter
   variety per column. Enter segments separated by spaces. `?` means one
   unknown segment, `∅` an observed zero, and a blank cell no phonological
   observation. These three states have different search consequences.
3. Open **⋯** to record the printed reading, source, witness or edition, locator,
   certainty, alignment and editorial note. Alternative readings remain
   explicit. **Use for comparison** swaps the selected reading while retaining
   the former reading. Segmentation proposals use the declared inventory and
   require an explicit choice; they do not normalize the source transcription.
4. In **Sound changes**, edit one ordered branch history at a time. For example,
   `p > b / V _ V` or `h > ∅ / # _`. Define `V = a e i o u` separately. `#`
   denotes a word boundary, `+` a morphological boundary in the rule language,
   and `.` any segment. `[p t k]` is an explicit segment class. The normal pass
   convention is simultaneous, left to right. Per-rule `; rtl` and `; feeding`
   flags preserve the other checked conventions. Unsupported processes are
   rejected with an explanation.
5. In **Reconstructions**, select hypotheses, daughter observations and cognate
   sets. Apply the proto-segment inventory, length bounds and optional word
   shapes, such as `C V | C V C`. Enumerating saves a revision and submits its
   exact request to a bounded background worker. Further editing does not
   change the submitted analysis.
6. Inspect individual protoforms or whole reconstructed wordlists. A whole
   wordlist uses one shared sound-law model. Counts are model-qualified: the
   same wordlist supported by two hypotheses is counted twice. Each displayed
   form is also checked by native forward derivation. Download the checked
   search to retain its complete forest, request and hashes.

Enter advances down a daughter column; Ctrl plus arrow keys navigate cells.
Escape leaves the current cell's saved draft value. Tabs support arrow-key,
Home and End navigation. Ctrl/Cmd-S saves a revision. Large tables display 50
rows at a time; filtering does not silently change the selected reconstruction
scope. On narrow displays the comparison table scrolls horizontally.

The editing conventions draw on the [EDICTOR wordlist interface](https://edictor.org/)
and [LingPy's wordlist formats](https://lingpy.org/tutorial/formats.html). The
application retains the existing, licensed Kiwari CSS, fonts and textures from
the persona website package; see `web/vendor/kiwari/` and its manifest.

The M7 generative search currently proposes segment-only protoforms. A project
can retain `+` boundary annotations and M2 boundary-conditioned histories, but
the workspace refuses to enumerate them as M7 input. Select explicit compared
morphological units or use the separate morphology analysis; a boundary-bearing
input must not be mistaken for evidence that no historical reconstruction exists.

## Sources, alignments and evaluation

Certainty of a manuscript reading is editorial metadata. It does not silently
change a phonological observation into an unknown segment. Supplied alignments
are checked by deleting gap symbols and comparing the result with the selected
segments. The correspondence view summarizes columns of those alignments;
it neither discovers cognacy nor establishes a sound law.

Opening a cognate-set identifier allows a reference reconstruction and a
training, development or test partition to be recorded. These fields remain in
annotations, outside the native search request. Evaluation occurs after search,
and reports all reference forms, the number within the declared alphabet and
bounds, recovery, and recovery as the unique candidate. Candidate counts are
retained per row. An out-of-scope reference remains in the denominator. The
partition is a researcher declaration: the software cannot establish that a
model was developed without exposure to test data. The original M5/M6 frozen
evaluations remain unchanged.

## Data exchange

| Format | Import / export | Preservation and limits |
| --- | --- | --- |
| Complete project JSON | Both | Versioned request, alternative readings, source annotations, classes, reference forms and notes. Does not contain revision history or saved analyses. |
| EDICTOR / LingPy TSV | Both | Explicit `ID`, `DOCULECT`, `CONCEPT`, `TOKENS`, `COGID`; printed reading, sources, witness, locator, certainty, note, alignment and extra columns. A single selected reading is exported per cell; use project JSON to preserve alternatives. |
| Wide cognate-set TSV | Export | Compact comparison table; use the project file to retain source and editorial metadata. |
| CLDF Wordlist ZIP | Both | Official `pycldf` writer and validator; explicit full-word cognacy, language and parameter tables. Source columns retained on import. Export includes `project.json` for complete project recovery. |
| TEI reading apparatus | Export | Printed readings, witness identifiers, selected/alternative distinctions, certainty and editorial notes. This limited XML export is tested for well-formedness and data retention; it is not a validated complete TEI edition or an inferred stemma. |
| Checked search JSON | Export | Complete native-checked graph forest, frozen request, counts and certificate hash. |
| Workspace backup ZIP | Export / command-line restore | All revisions, job records and retained analysis artifacts, with a file-hash manifest. |

CLDF handling follows the [CLDF Wordlist module](https://github.com/cldf/cldf/blob/master/modules/Wordlist/README.md).
Partial cognacy, multiple cognate judgments for one form, and multiple readings
in one cognate-set/language cell require an explicit analysis decision before
import. The importer rejects them instead of selecting a judgment. It rejects
external file dependencies, path traversal and oversized archives. Missing
observations are retained in exported `project.json`; CLDF tables omit them.
Observed zero is explicitly tagged `Observation_Status=empty`, with `Form=∅`
and empty `Segments`. CLDF import reads the tables as a new wordlist; it does not
silently privilege an accompanying project file over edited CSV tables. Retain
the original CLDF archive for bibliographies and tables outside this adapter's
scope. The TEI vocabulary follows the [critical-apparatus guidelines](https://tei-c.org/release/doc/tei-p5-doc/en/html/TC.html).

## Durability and operation

SQLite transactions retain immutable revisions. A save based on an obsolete
revision is rejected, preserving the browser draft for export and comparison.
Undo/redo is available in the current window; **History & backups** restores an
older revision by creating a new revision. Browser drafts are a convenience,
not a substitute for a saved revision. Storage quota failures are displayed.

Completed analyses bind the project revision, engine hash, frozen request and
graph hash. Changing a native executable or Lean source invalidates the build
record; rebuild with `./workbench setup`. Previously saved results can still be
exported. Re-run them before browsing with a different native executable.

Two isolated workers run concurrently; up to 16 analyses may be active or
queued. Cancellation terminates the worker process group, including its native
checker. A worker monitors its application parent. An interrupted process is
recorded as interrupted at restart, never complete. Resource exhaustion is
reported as incomplete or failed, without a completeness claim.

| Limit | Current value |
| --- | --- |
| Native request | 1–10,000 sets, 1–32 daughter varieties, 1–32 global hypotheses |
| Protoforms | 1–64 inventory symbols; length 0–64; up to 256 explicit slot templates |
| Sound laws | Up to 128 per branch; replacement or deletion of one segment; up to two context positions on each side |
| Workspace document / HTTP JSON | 16 MB |
| Browser file import | 11 MB; CLDF expansion at most 64 MB / 256 archive entries |
| Search | At most 250,000 graph states and 60 seconds of graph construction |
| Total job deadline | Search limit plus 125 seconds for checks and evaluation |
| Native certificate | At most 128 MiB |
| Linux worker hard limits | 3 GiB address space, 256 MiB per file; macOS uses time, graph and artifact limits without an address-space cap |
| Native worker runtime | One Lean task thread; 64 MiB thread stack reservation on Lean 4.34, so default virtual stack reservations do not exhaust the Linux address-space limit |
| Stored analysis admission limit | 2 GiB; pending jobs can add artifacts before the next admission check |
| Browser backup download | 64 MB compressed; command-line backup supports larger workspaces |

Save first, finish or cancel active analyses, then download a backup. To restore:

```bash
./workbench restore /path/to/comparative-workspace.zip /path/to/new-workspace
./workbench open --workspace /path/to/new-workspace
```

Restore verifies every file hash and SQLite integrity and refuses to overwrite a
nonempty directory. For a larger backup, close the application first:

```bash
./workbench backup /path/to/workspace /path/to/new-backup.zip
```

The workspace lock prevents two application processes from sharing the same
database. The schema is versioned; newer schemas are refused. Back up before an
upgrade and keep the matching repository revision. A future schema change must
ship a tested migration and restore procedure; there is no silent downgrade.

The server reports request IDs for unexpected failures without exposing source
text in HTTP errors. Worker diagnostics are retained with the analysis. There
is no telemetry, remote collaboration, automatic cloud backup or public hosting
in this release. Ordinary OS backup and access controls apply.

## Reproduce the application checks

```bash
source .venv/bin/activate
python -m pip install -r requirements-ui-test.txt
python scripts/verify_workspace.py
python scripts/verify_workspace.py --check-report
```

The verifier runs the backend suite, real browser interactions and native Lean
analyses, then hashes the tested sources and screenshots. CI repeats these
workflows with both supported Lean versions. See
[retained evidence](../reports/workspace/verification.json),
[wordlist](../reports/workspace/wordlist.png),
[reading apparatus](../reports/workspace/reading.png), and
[reconstruction results](../reports/workspace/reconstructions.png).
