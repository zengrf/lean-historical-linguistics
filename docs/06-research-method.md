# Research method, acquisition record and limits

This study combines a targeted literature search, source-specific reading notes, inspection of relevant proof-assistant code and a small mechanized feasibility test. The cutoff is **5 October 2026 UTC**. It is a substantial planning review, not an exhaustive systematic review or a replacement for specialist philological assessment.

## 1. Questions that determined source selection

The search covered six connected areas:

1. Comparative-method theory: regular correspondences, cognacy, internal reconstruction, analogy, contact, semantic comparison and morphological evidence.
2. Computational practice: alignment, cognate detection, correspondence patterns, reconstruction engines, sound-law induction, neural proposals, uncertainty and evaluation.
3. Indo-European: sound laws, relative chronology, laryngeals, ablaut, Anatolian, executable PIE models, cognate datasets and phylogenetic assumptions.
4. Sino-Tibetan / Trans-Himalayan: competing historical classifications, Tibeto-Burman traditions, Old Chinese, Tibetan and subgroup reconstruction, especially Kuki-Chin.
5. Formal foundations: rewriting, finite-state transduction, subregular functions, weighted automata, constraint solving and identifiability.
6. Mechanization: Lean's kernel and library design, mechanized automata in Lean/Coq/Isabelle, reusable linguistic definitions and maintenance practices.

Searches used combinations of these subjects, named foundational systems and citation-following. ACL Anthology collection metadata supported computational discovery; author sites, HAL, university repositories, STEDT, publishers and arXiv supplied other sources. The discovery script is supporting machinery, not an automatic relevance or quality judgment. The curated [source catalogue](../bibliography/sources.json) is authoritative.

Every retained item was selected for an identifiable use in the formal design, linguistic case studies or research evaluation. There is no claim that all papers share one definition of reconstruction or that a phylogenetic method already reconstructs proto-word forms.

## 2. Acquisition and conservative counting

The final snapshot has **132 references, 127 successfully retained PDFs, and 122 qualifying distinct works**. It records **5,184 PDF pages and 211,275,019 bytes**. Counts refer to files and curated work identities, not search hits.

Each successful download has a recorded source URL, resolved URL, byte count, SHA-256 digest and PDF page count. The full local verifier reopens and hashes the actual retained files. All 127 acquired files have different hashes. Identity checks also exclude the separately acquired Anatolian chapter already contained in the downloaded Olander volume: different bytes do not automatically imply a distinct work.

The count additionally excludes List's research proposal, two reviews and a short reply. They remain useful supporting material and are explicitly labeled. Failed downloads, landing pages, tables of contents and repository metadata do not contribute to the floor. The retained books and dissertations are counted once each, rather than treating every chapter as a separate acquired work.

The collection includes full monographs or dissertations by Benedict, Matisoff, VanBik, Button, Namkung, List and Chandlee, and the Olander edited volume. Their presence in the collection does not imply that every page was read.

Coverage tags overlap. Among qualifying acquired works, the current tags include 62 computational, 27 Sino-Tibetan, 18 formal, 17 Indo-European and 17 theory entries, with additional data, morphology, syntax and comparative-method tags. These are navigation aids, not mutually exclusive discipline totals or evidence of exhaustive coverage.

## 3. Reading depth and traceability

[Reading notes](../bibliography/reading-notes.json) record the scope, examined PDF pages, findings, proposed formalization use and a caution for every reference. The current tiers are:

| Tier | Entries | Interpretation |
|---|---:|---|
| Focused excerpts | 34 | Selected substantive sections examined to resolve a methodological or design question |
| Screened excerpts | 82 | Opening/abstract material and selected closing passages where available; a relevance assessment rather than a full critical reading |
| Visual excerpts | 10 | Selected rendered pages inspected because scans or font encoding limited text extraction |
| Screened decoded abstract | 1 | A damaged extracted abstract decoded for limited screening; conclusions kept correspondingly narrow |
| Web excerpts only | 2 | Introductory passages available through web retrieval, without a retained complete PDF |
| Access gap | 3 | Bibliographic or publisher-level information; no claim of direct substantive reading |

These counts sum to 132, including the five acquisition gaps. PDF page numbers include covers and repository wrappers. They can differ substantially from printed pages. Some files have incomplete or corrupted extracted text; `text_characters` is an extraction diagnostic, not a reading or quality measure.

The synthesis gives particular weight to comparative-method accounts; Lowe and Mazaudon's Reconstruction Engine; Meelen, Hill and Fellner on cognacy; alignment/correspondence and uncertainty papers; source-defined PIE disputes; Kuki-Chin monographs; Sino-Tibetan methodological disagreements; and formal-language and proof-assistant foundations. It does not turn a screened result into a claim that its full derivation has been independently reproduced.

Findings in the catalogue are paraphrases. A proposed Lean representation or delivery consequence is this study's analysis, not necessarily the source author's proposal. The [prior-art audit](05-prior-art.md) likewise distinguishes inspected source definitions from software that has actually been built and checked here.

## 4. Gaps and priorities for the next reading cycle

Five attempted acquisitions remain incomplete:

| Catalogue ID | Missing retained work | Session limitation |
|---|---|---|
| `matisoff2003` | *Handbook of Proto-Tibeto-Burman* | Institutional PDF endpoint returned an access error |
| `koskenniemi1983` | *Two-Level Morphology* | Repository endpoint could not be resolved |
| `nipkow2013` | Verified MSO decision-procedure paper | Retrieval timed out |
| `fellner-hill2023` | Sino-Tibetan methodological response | Repository download denied; limited web excerpts were readable |
| `lai2022` | Tibetan lenition manuscript | Repository download denied; limited web excerpts were readable |

The recorded errors are historical observations, not claims that these works are generally unavailable. No paywall or authentication control was bypassed. Matisoff 2003 was not silently substituted with a review while counted as the book.

Priority additions for the next cycle include Nathan Hill's [*The Historical Phonology of Tibetan, Burmese, and Chinese*](https://doi.org/10.1017/9781316550939), Baxter and Sagart's *Old Chinese: A New Reconstruction*, comprehensive historical-linguistics textbooks by Campbell, Hock and Fox, and PIE textbooks and grammars by Fortson and Ringe. They are reading priorities, **not extra acquired or directly studied books in the present count**. These should deepen coverage of phonological interpretation, morphology, semantic change, philology and branches underrepresented in the current library.

The current selection favors sources with accessible electronic copies and the authors/repositories discoverable in this session. English predominates; French and Chinese material is present but coverage of non-English traditions is incomplete. Major gaps remain in archaeology, population genetics, sociolinguistic models of transmission, full syntax reconstruction and many individual Sino-Tibetan branches. Those areas should be added when a precise research claim depends on them, rather than being implied by a general claim to cover all relevant literature.

## 5. Versions and bibliographic corrections

The catalogue separates a stable local ID from the displayed bibliographic year. Where an author manuscript, proof or repository deposit differs from the eventual publication, a `version_note` records the distinction. An ID containing a year is not itself a claim about the final publication date.

Title/author checks against the files corrected several initial search-result mismatches. Examples include the intended pair-HMM and LexStat papers, Kloekhorst chapter identity, the authorship of the Khaling chapter and the IE-CoR author name. The IE-CoR paper's inconsistent lexeme totals are retained as a caution: future dataset statistics should be computed from a pinned release. A full-volume PDF and a separately acquired chapter are linked using `included_in`.

Some preliminary or author-hosted manuscripts still lack fully reconciled final-publication metadata. The corresponding version notes identify the uncertainty. The generated BibTeX preserves the available metadata without inventing journal, volume or page fields.

## 6. Public distribution and local retention

**64 PDFs are public; 63 additional acquired PDFs are retained locally.** Public availability of a PDF is not treated as permission to mirror it. Each public entry has a `rights_basis`, and [the notices](../library/THIRD_PARTY_NOTICES.md) preserve the source-specific license and attribution. The PDFs themselves are unmodified.

ACL ownership and the [Anthology copyright policy](https://aclanthology.org/faq/copyright/) were checked, while explicit article notices and third-party publisher ownership take precedence over a blanket assumption. Four ELRA PDFs state CC-BY-NC without a version; the catalogue does not invent one. STEDT's specific no-charge, unmodified academic redistribution permission applies only to the appropriate monographs. Other author-hosted and institutional PDFs remain local unless permission was established.

The public Git repository therefore contains the study, original code, complete acquisition/reading metadata and the permitted PDF subset. The full collection exists at `library/open/` plus `library/downloads/` on the originating workspace. A fresh clone requires source retrieval to restore the latter, and external availability may change.

## 7. Reproduction and maintenance

Follow [the root README](../README.md) for current commands. The two audit modes are deliberately distinct:

- `python scripts/verify_library.py` validates metadata, count decisions and the public files. Any additional local files that happen to be present are also checked.
- `python scripts/verify_library.py --local` additionally requires all successfully acquired PDFs to exist with their recorded hashes.

`fetch_library.py --available` attempts only the 127 previously successful acquisitions. The default fetch report goes to ignored local metadata. Existing matching files are reused. Changed bytes are reported as a version mismatch rather than silently overwriting the recorded artifact. Review a changed source and its rights, then explicitly update metadata and regenerate the catalogue if adopting it.

`check_plan.py` checks dependency consistency, acceptance-record structure and the existence of artifacts marked delivered. It does not execute future acceptance commands or certify that planned milestones are complete. Lean builds and `check_proofs.py` establish the current proof prototype's status; empirical linguistic correctness remains outside those checks.

The honest delivery is thus a reproducible, substantially researched starting point with tested formal contracts and explicit evidence gaps. Full case-study encoding, external specialist review and deeper reading are part of the subsequent milestones.
