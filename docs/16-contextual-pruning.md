# Verified pruning for contextual sound changes

Contextual packages now use a pruned prefix search. For each original segment,
the rule cascade computes a finite set containing every output that the segment
could contribute. Unconditional left-to-right rules retain their exact effect;
other rules retain both copying and any target-compatible replacement or
deletion. Context, word edges, pass convention and direction are fully applied
by the original interpreter when a complete word is tested.

This approximation can reject a prefix if none of its possible outputs matches
the beginning of an observed reflex. It never supplies an accepted historical
derivation. [Pruning.lean](../lean/Historical/Pruning.lean) proves that every
actual derivation is included in the approximation, including right-to-left and
feeding passes. It then proves that every prefix of a fitting word has a
nonempty residual set. The generic pruned-machine theorem and
`LexiconInput.pruned_request_complete` connect the checked graph to exactly the
same reconstruction predicate as the original exhaustive reference search.

This adds 19 theorem declarations; the complete audit now covers 204. The
unpruned reference mode remains available for independent comparison and old
certificates remain accepted. The optimized unconditional fragment continues
to use its more compact residual graph.

Run:

```bash
python scripts/verify_m7.py --check
python scripts/verify_pruning.py --output /tmp/contextual-pruning.json
```

The [pruning report](../reports/contextual-pruning.json) includes 96 further
exact inverse sets under reproducibly generated contextual cascades, agreement
with the independent exhaustive interpreter, and rejection of omitted edges
and false accepting states. The formerly exhausted length-12 example now has
four graph states and a complete result. A 1,000-row synthetic contextual
benchmark has 2,000 daughter reflexes and independently checked branch
certificates; it permits one complete protolexicon. Measurements and source
hashes are retained in the report.

This is a conservative pruning algorithm, not general finite-state sound-law
compilation. Deletion, missing evidence and permissive alternatives can still
leave a large search. Existing time, memory and certificate bounds still apply;
an exhausted search is incomplete, never a complete empty result. Synthetic
scaling results do not establish performance for a complete historical grammar.
