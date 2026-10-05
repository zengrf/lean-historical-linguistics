# Alignment and correspondence semantics, version 1.0.0

M3 checks monotonic alignments and feasible partitions of their segment-bearing
columns. The initial suite is synthetic. Acceptance does not establish cognacy,
historical sound laws, correct segmentation, or an optimal number of groups.

## Rows, gaps and absence

Cells reuse M1's tagged types: `segment`, `boundary`, `unknown`, `missing` and
`gap`. Strings are atomic Unicode values and are never normalized by M3.
Present original rows contain segments, explicit `+` morpheme boundaries, or
unknown readings; they cannot contain alignment gaps or missing-data cells.
A present aligned row may additionally contain gaps. Removing exactly those
gaps must recover the entire original row in order, with multiplicity and all
unknown/boundary values intact. Reordering, substitution, duplication and
omission are rejected.

An absent reflex is represented by **null at the row level**, in both original
and aligned fields. Column extraction gives a `missing` cell at every position
of that absent row. This avoids assigning an invented segment count to an
absent word. A present empty word is `[]`, distinct from an absent word; it can
be aligned with an explicit sequence of gaps. A present row cannot silently
become absent or vice versa. Unknown readings remain explicit cells rather
than being erased or imputed.

All alignments use the document's same ordered, unique doculect axis. Every
alignment has at least two rows and a positive width. Every present aligned
row has that width. Each column must contain some original material: columns
consisting solely of gaps and missing data are rejected. Boundary columns may
contain `boundary("+")`, gaps or missing data, but cannot mix boundaries with
segments or unknown readings. Boundaries in original rows must occur between
non-boundary cells; leading, trailing and adjacent boundaries are rejected.
This profile uses explicit boundary tokens, not interval-based morpheme spans;
undeclared span fields are rejected instead of being silently interpreted.

## Sites and compatibility

Every column containing at least one observed segment is a required site.
The site registry must contain exactly one reference to each such
`(alignment_id, column_index)` pair, using zero-based indices. Boundary-only and
unknown-only columns remain in the alignment, but are not promoted to sound
correspondence sites. A document with no required segment sites is rejected.
Site cells are derived from checked alignments, never supplied independently
by a grouping certificate.

Two cells agree unless both carry observed values that conflict. A `missing`
cell or an `unknown` reading provides no conflicting or supporting observation.
Otherwise agreement is exact equality of tagged cells: in particular a gap
conflicts with a segment, and distinct observed segments conflict.

Two sites are compatible precisely when their ordered axes have equal length,
all corresponding cells agree, and at least one position contains the same
observed segment in both sites. Equal gaps, boundaries, missing data and unknown
readings never supply that positive evidence. This follows the observed-sound
and no-conflict criterion in [List (2019), PDF pp. 8–9](https://aclanthology.org/J19-1004/);
treating explicit unknown readings as unavailable is this project's additional
conservative policy, not a claim that the source defined that representation.

For example, `[p,t]` is compatible with `[p,missing]`, which is compatible with
`[p,k]`, while `[p,t]` conflicts with `[p,k]`. Therefore a connected component,
representative match or union-find merge is not a valid group certificate.
The checker tests every pair of distinct site IDs in each proposed group.

## Support and partition certificates

Each alignment declares an `evidence_unit` identifying its etymon/root family.
All sites extracted from that alignment inherit the same unit. A group's
support is the number of distinct declared evidence units among its members
with observed segments. Several positions in one alignment, repeated sources
or several alignments with the same declared unit do not increase this count.
The certificate's claimed support must equal that computed count.

Each group must be nonempty, have distinct member IDs referring to existing
sites, contain only sites with observed segments, and be a pairwise-compatible
clique. Singleton groups are permitted with support one; they carry no evidence
of recurrence. Group and site IDs must be unique. Every required site must be
assigned exactly once, with no omitted, repeated or unknown references.

Support counts and shared-segment witnesses are distinct diagnostics: a pair
can share a segment and still conflict at another observed position. Its group
must then be rejected even when it has several distinct evidence units.
The checker verifies the declared unit policy; it cannot authenticate that
two declared units are historically independent. That is a future data-review
obligation, not a theorem about arbitrary labels.

The only accepted claim is `feasibility-only`. Minimum, optimal, maximal and
score-based claims are rejected. No optimizer or heuristic is in the acceptance
path. A checked feasible partition need not be unique or use the fewest groups.

## Source and parser boundaries

Each row has a nonempty source reference, including for absent observations.
For synthetic fixtures these explicitly identify constructed data. A checked
alignment recovers the supplied original; it does not authenticate its external
source or create an empirical M1-to-M3 transcription policy. The raw M1 sources,
normalizations, linked alternatives and provenance remain separate and intact.

The strict JSON profile rejects duplicate keys, undeclared fields and omitted
explicit fields. Cells retain M1's `kind`/`value` encoding; null rows denote
absence, whereas a `gap` cell denotes an alignment operation. Segment symbols
use M2's atomic-symbol restrictions, including Unicode whitespace rejection.
Unknown reading strings must be nonempty; they remain unavailable for positive
support regardless of their spelling. Literal UTF-8 is required for supplementary
Unicode characters, consistent with the supported Lean parser versions.

The formal contracts relate typed checker acceptance to row recovery and a
feasible correspondence partition. JSON decoding, metadata validation and file
I/O are executable boundaries, not claims of verified byte-level parsing or
independent linguistic validation.
