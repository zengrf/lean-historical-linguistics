# M3 alignment and correspondence fixtures

All examples in this directory are **synthetic**. They are authored contract
tests, not transcriptions or evidence of historical cognacy. Source references
begin with `synthetic:`. The code/data license is the repository's MIT license.

The [manifest](manifest.json) declares the expected acceptance, rejection code,
input kind and rationale for each of 135 fixtures. `scripts/build_m3_fixtures.py`
reproduces the bytes deterministically; `--check` rejects missing, changed or
extra fixture files. Expectations are authored separately from Lean execution.

Only 60 dossiers under `sites/` count toward the 100-site acceptance floor:

| Category | Dossiers | Sites | Expected result |
| --- | ---: | ---: | --- |
| Shared observed segments | 30 | 60 | Accept |
| Two columns per evidence unit | 10 | 40 | Accept; duplicate positions do not inflate support |
| Shared segment plus an observed conflict | 10 | 20 | Reject conflicting groups |
| Disjoint observations, with missing or gap overlap | 10 | 20 | Reject unsupported groups |

All 140 counted sites have a valid alignment, a complete registry and one
proposed assignment. Of these, 125 contain missing or unknown cells and 20
participate in an observed conflict. The 40 rejected sites retain their proposed
groups and diagnostics in the report; they are never counted as valid groups.
Counts use `(fixture path, site ID)` identities. Structural mutation tests in
`valid/` and `invalid/` are additional checks and do not raise these totals.

See [the semantics](../../docs/alignment-correspondence-semantics.md) and
[delivery guide](../../docs/09-m3-delivery.md) for the JSON contract and commands.
[correspondence-sites.json](../../reports/correspondence-sites.json) records each
fixture's outcome and, for every derived site, its cells, coordinates, unit,
group assignment, computed support, pairwise shared-segment witnesses,
conflicts and checker result. Null rows are absent observations; present empty
rows and alignment gaps remain distinct.

The only supported claim is **feasibility-only**. Two differently sized feasible
partitions of identical observations are explicit fixtures. No count here is a
minimum-cover certificate or an empirical sample size of independent etymologies.
