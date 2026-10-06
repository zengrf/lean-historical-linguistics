# Retained publication library

The library is indexed in the [annotated catalogue](../bibliography/README.md), backed by [metadata](../bibliography/sources.json) and the [acquisition ledger](../bibliography/downloads.json).

- `open/`: 64 unmodified PDFs included in public Git under the [individual permissions](THIRD_PARTY_NOTICES.md).
- `downloads/`: 63 additional acquired PDFs retained locally and ignored by Git.
- `text/`: local extraction output, including per-page text. Scans and unusual fonts may extract incompletely.
- `metadata/`: local discovery records, fetch reports and supporting inspection artifacts.

The 127 PDFs contain 122 qualifying distinct works under the conservative count described in the [research method](../docs/06-research-method.md). The current collection occupies approximately 211 MB, excluding text and working files. The public subset is smaller.

To verify the originating local collection, run `python scripts/verify_library.py --local` from the repository root after installing its Python requirements. To attempt restoration from a fresh clone, first run `python scripts/fetch_library.py --available`. Source access can change; the fetcher reports failures and hash mismatches.

No blanket license applies to these publications. The repository's MIT license covers its original code and documentation only.
