# Dataset attribution and retention

The original project code and synthetic fixtures use MIT. The source datasets and their derived pilot records retain **CC BY 4.0** attribution requirements; they are not relicensed under MIT.

## IE-CoR

Heggarty, Paul; Anderson, Cormac; Scarborough, Matthew. *Indo-European Cognate Relationships database*. The snapshot metadata cites IE-CoR version 1.1 (2024); its provenance and repository release labels differ. The snapshot is identified by its commit and file hashes; the discrepancy between version labels remains unresolved.

- [Pinned repository](https://github.com/lexibank/iecor/tree/700b635a04786427b78841489c46eefbe2843509)
- [Retained original license](upstream/iecor/LICENSE), [upstream README and contributors](upstream/iecor/README.md)
- Commit: `700b635a04786427b78841489c46eefbe2843509`
- [Derived pilot](pilots/iecor.json): 30 selected records; original values and all raw form columns preserved, representations wrapped in the project's evidence schema.
- [M5 derived PIE pilot](pie/README.md): 200 source cognate sets and 843 distinct form rows, plus a separate 20-set Latin/Romance control. Original records, cognacy notes, licenses and exact source locators remain attached. Added selection, normalization, models and splits are explicitly identified; specialist linguistic review is pending. These derivatives retain CC BY 4.0 attribution.
- [M6 Kuki-Chin corpus](kuki-chin/README.md): lexical forms, glosses and source claims from Kenneth VanBik (2009), *Proto-Kuki-Chin*, STEDT Monograph 8, with exact PDF pages and entry numbers. The source PDF remains unmodified under STEDT's academic noncommercial redistribution permission. This extraction is separately labelled and has not received specialist review.
- [M6 cross-branch comparisons](cross-branch/README.md): selected lexical facts and original summaries of arguments from Guillaume Jacques's papers and Sagart and Baxter (2012), with page locators, source URLs and PDF hashes. Button (2011), *Proto Northern Chin*, supplies the distinct reconstruction scope and tone notation. Local research PDFs without established redistribution permission remain outside Git. Source papers retain their copyrights; the generated analyses do not imply their authors' endorsement.

## Hill–Gong Burmish data

Nathan W. Hill and Xun Gong, with Johann-Mattis List as maintainer. *Proto-Burmish Reconstruction*, as identified in the pinned dataset's README and metadata.

- [Pinned repository](https://github.com/lexibank/hillburmish/tree/3d96cfa6b2ed4c59fd13e28ef5ae00db30247bb3)
- [Retained original license](upstream/hillburmish/LICENSE), [upstream README and contributors](upstream/hillburmish/README.md)
- Commit: `3d96cfa6b2ed4c59fd13e28ef5ae00db30247bb3`
- [Derived pilot](pilots/hillburmish.json): 30 selected records, including explicit treatment of the source's ProtoBurmish node as reconstructed.

Both datasets grant [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The retained upstream files are unmodified. Derived pilot JSON adds identifiers, provenance and representation metadata; it concatenates the original segment tokens for display and records that operation explicitly. The selection is not a new historical reconstruction or validation of the source analyses.

Packaging exception: upstream `.gitattributes` files are retained as `.gitattributes.upstream`, with the original path recorded in the manifest. Their contents are unchanged. This prevents their CRLF checkout settings from changing the LF source bytes that were acquired and hashed. Repository attributes disable newline conversion in the snapshot directories.

[manifest.json](upstream/manifest.json) lists every retained upstream file's checksum and size. [Import reports](../reports/README.md) list columns and tables that remain uninterpreted. Other parties' notices remain in the original source files.

## Sagart–Jacques–Lai–List Sino-Tibetan data

Laurent Sagart, Guillaume Jacques, Yunfan Lai and Johann-Mattis List (2019).
*Sino-Tibetan Database of Lexical Cognates*. Jena: Max Planck Institute for the
Science of Human History. The retained Lexibank derivative is pinned to
[`c6df5f38eeef9cf40dbb939e6515f8bf8cd04246`](https://github.com/lexibank/sagartst/tree/c6df5f38eeef9cf40dbb939e6515f8bf8cd04246).

The [upstream README](upstream/sagartst/README.md),
[contributors](upstream/sagartst/CONTRIBUTORS.md),
[CC BY 4.0 license](upstream/sagartst/LICENSE), CLDF tables and source bibliography
are retained unmodified. [materials/sources.json](materials/sources.json) records
every retained file's checksum and size. As in the older snapshots,
`.gitattributes` is renamed `.gitattributes.upstream` to preserve source bytes.
The catalogue adds counts, joins and source-qualified identifiers; it makes no
new cognacy judgments or claims of author endorsement. Forms from this source
are not deduplicated against Burmish or Kuki-Chin records from other sources.
