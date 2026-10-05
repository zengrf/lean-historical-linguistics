# M1 independent source-entry review

Completed on 2026-10-05 UTC by the independent AI agent task `/root/m1_source_review`, recorded as `codex-independent-ai-agent:/root/m1_source_review`. This identifies the actual reviewing agent task; it is not an authenticated human identity or a human attestation.

The scope was the six `Value` cells listed in `reviews/m1-packet.json`: three from hillburmish and three from iecor. This is the packet's minimum sample of six out of 60 core records, not a review of all 60. The entries are finalized in `reviews/m1-responses.json`. No source ambiguity was found, so every `resolution` is `null`.

## Independence and method

This agent started with fresh task context, did not participate in the import or encoding, and was not supplied expected imported values. Before finalizing the transcription, it read only the review packet, the blank response template, and the two packet-pinned upstream CSVs, while checking for applicable `AGENTS.md` files (none were found at the checked ancestor and source/review paths). It did not consult `data/pilots`, importer code, validation scripts or reports, or expected answers. The workspace was shared: this read boundary was enforced by instruction, not by a separate filesystem sandbox.

For each dataset, the reviewer calculated the local CSV's SHA256, separately fetched the exact commit-pinned raw GitHub CSV using `curl` with normal certificate verification, and checked both hashes and complete byte equality. An initial Python HTTPS attempt failed because that Python installation could not find its certificate issuer; the successful retry did not disable TLS verification. The source files were decoded as UTF-8 and read using Python's standard CSV reader. Each requested `ID` matched exactly one row. The reviewer displayed and inspected the full raw CSV row, its requested `Value` cell, the escaped string, and every Unicode code point, then wrote the six entries from those source observations. It did not substitute `Form`, phonetic fields, or inferred forms for `Value`.

## Source provenance

Both local snapshots and independently fetched bytes exactly match the packet's source hashes.

| Dataset | Commit | SHA256 | Bytes |
| --- | --- | --- | ---: |
| hillburmish | `3d96cfa6b2ed4c59fd13e28ef5ae00db30247bb3` | `7a6906044fb9337c894498e3936040dec86f34198f2ee1bd1ca282fb0f3e421f` | 479039 |
| iecor | `700b635a04786427b78841489c46eefbe2843509` | `055ce127b4033d6b96f5589228bf9a63b20564a0c0d19e5b9e97fe80b1a77202` | 2650749 |

The fetched sources were the [pinned hillburmish CSV](https://raw.githubusercontent.com/lexibank/hillburmish/3d96cfa6b2ed4c59fd13e28ef5ae00db30247bb3/cldf/forms.csv) and [pinned iecor CSV](https://raw.githubusercontent.com/lexibank/iecor/700b635a04786427b78841489c46eefbe2843509/cldf/forms.csv). Their local counterparts were `data/upstream/hillburmish/cldf/forms.csv` and `data/upstream/iecor/cldf/forms.csv`.

The response preserves the supplied packet hash, `aae16253a527d0738397c7e92806c4c680ec16f07e118b388e759be2bbb5d3b5`. It was independently reproduced as SHA256 of UTF-8 `json.dumps(packet, sort_keys=True, ensure_ascii=False)` with default separators and no trailing newline. This is a logical JSON serialization hash. The packet file's raw-byte SHA256 is separately recorded as `b2a72fae3d2a858d601e80935167a13c73c61e1b9e758795aabf8b777609e9bd`; the difference is serialization, not a source discrepancy.

## Transcription and Unicode checks

Line numbers below are physical lines in the pinned CSV, including its header. All six rows occupy a single physical line.

| Record ID | Source line | Exact `Value` | Unicode code points |
| --- | ---: | --- | --- |
| `hillburmish:Atsi-1193_accomplishsucceed-1` | 11 | `pa̱n⁵⁵` | `U+0070 U+0061 U+0331 U+006E U+2075 U+2075` |
| `hillburmish:Lashi-1666_achehead-1` | 21 | `nɔː³¹` | `U+006E U+0254 U+02D0 U+00B3 U+00B9` |
| `hillburmish:Rangoon-1366_afraidbe-1` | 24 | `tɕɑuʔ⁴` | `U+0074 U+0255 U+0251 U+0075 U+0294 U+2074` |
| `iecor:18-4-1` | 914 | `popel` | `U+0070 U+006F U+0070 U+0065 U+006C` |
| `iecor:23-6-1` | 1439 | `bak` | `U+0062 U+0061 U+006B` |
| `iecor:10-4-1` | 385 | `chāi` | `U+0063 U+0068 U+0101 U+0069` |

The Atsi form contains a combining macron below (`U+0331`) after `a`; it was retained as a combining character. The Lashi form contains the IPA open `ɔ` and triangular colon `ː`, plus superscript three and one. The Rangoon form contains `ɕ`, `ɑ`, `ʔ`, and superscript four. The iecor form `chāi` uses precomposed `ā` (`U+0101`). All six source values are unchanged by an NFC comparison, but no normalization was applied to the submitted strings. There were no missing or duplicate requested IDs, unexpected surrounding whitespace, or ambiguous cell boundaries in this sample.

## Limits

This is independent AI source-entry review. It provides neither human nor language-family-specialist sign-off, and makes no assessment of cognacy, phonological interpretation, source scholarship, or historical-linguistic claims. The provenance checks establish byte agreement with the pinned public CSVs, not independent correctness of their linguistic contents. The reviewer did not examine imported outputs or determine milestone status, and did not change validators or milestone declarations.
