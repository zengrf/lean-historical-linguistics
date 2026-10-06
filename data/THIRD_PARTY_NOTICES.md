# Dataset attribution and retention

The original project code and synthetic fixtures use MIT. The source datasets and their derived pilot records retain **CC BY 4.0** attribution requirements; they are not relicensed under MIT.

## IE-CoR

Heggarty, Paul; Anderson, Cormac; Scarborough, Matthew. *Indo-European Cognate Relationships database*. The snapshot metadata cites IE-CoR version 1.1 (2024); its provenance and repository release labels differ. The snapshot is identified by its commit and file hashes; the discrepancy between version labels remains unresolved.

- [Pinned repository](https://github.com/lexibank/iecor/tree/700b635a04786427b78841489c46eefbe2843509)
- [Retained original license](upstream/iecor/LICENSE), [upstream README and contributors](upstream/iecor/README.md)
- Commit: `700b635a04786427b78841489c46eefbe2843509`
- [Derived pilot](pilots/iecor.json): 30 selected records; original values and all raw form columns preserved, representations wrapped in the project's evidence schema.
- [M5 derived PIE pilot](pie/README.md): 200 source cognate sets and 843 distinct form rows, plus a separate 20-set Latin/Romance control. Original records, cognacy notes, licenses and exact source locators remain attached. Added selection, normalization, models and splits are explicitly identified; specialist linguistic review is pending. These derivatives retain CC BY 4.0 attribution.

## Hill–Gong Burmish data

Nathan W. Hill and Xun Gong, with Johann-Mattis List as maintainer. *Proto-Burmish Reconstruction*, as identified in the pinned dataset's README and metadata.

- [Pinned repository](https://github.com/lexibank/hillburmish/tree/3d96cfa6b2ed4c59fd13e28ef5ae00db30247bb3)
- [Retained original license](upstream/hillburmish/LICENSE), [upstream README and contributors](upstream/hillburmish/README.md)
- Commit: `3d96cfa6b2ed4c59fd13e28ef5ae00db30247bb3`
- [Derived pilot](pilots/hillburmish.json): 30 selected records, including explicit treatment of the source's ProtoBurmish node as reconstructed.

Both datasets grant [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The retained upstream files are unmodified. Derived pilot JSON adds identifiers, provenance and representation metadata; it concatenates the original segment tokens for display and records that operation explicitly. The selection is not a new historical reconstruction or validation of the source analyses.

Packaging exception: upstream `.gitattributes` files are retained as `.gitattributes.upstream`, with the original path recorded in the manifest. Their contents are unchanged. This prevents their CRLF checkout settings from changing the LF source bytes that were acquired and hashed. Repository attributes disable newline conversion in the snapshot directories.

[manifest.json](upstream/manifest.json) lists every retained upstream file's checksum and size. [Import reports](../reports/README.md) list columns and tables that remain uninterpreted. Other parties' notices remain in the original source files.
