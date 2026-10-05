# M2 implementation review after frozen manual derivations

Reviewer: `/root/m2_hand_review`, a separate AI agent. This implementation review began only after all 20 manual derivations and their 22 post-rule stages had been frozen. The prior hand-work files and prose semantics were not edited during this review. This is neither human nor family-specialist sign-off.

At the initial inspected snapshot, I found one acceptance-blocking mismatch, described below. The implementation agent corrected it, and my independent read-only recheck confirmed the correction. No blocking findings remain in the inspected scope; this is not a correctness guarantee. The review's read boundary was instruction-enforced on a shared filesystem, not a technical sandbox.

## Finding M2-R1: non-ASCII whitespace was accepted as a segment

**Severity:** Medium; blocked a claim of full conformance to the published token contract. **Final status:** Resolved and independently rechecked. This finding initially used the local review label M2-CR-1; M2-R1 is the implementation agent's regression identifier.

`docs/rule-semantics.md` prohibits whitespace/control characters in atomic segment strings. In the inspected `lean/Historical/RuleInput.lean`, `goodSymbol` used `!c.isWhitespace`, a lower bound of 32, and C1-control exclusion. The whitespace predicate did not exclude all Unicode whitespace.

Read-only probes of the built `lean/.lake/build/bin/verify_dossiers`, through `--file /dev/stdin`, produced these results:

| Inventory atom | Result before fix |
| --- | --- |
| U+0020 SPACE | Rejected, `INVENTORY`, exit 1 |
| U+0085 control | Rejected, `INVENTORY`, exit 1 |
| U+00A0 NO-BREAK SPACE | Accepted, exit 0 |
| U+2003 EM SPACE | Accepted, exit 0 |
| U+2028 LINE SEPARATOR | Accepted, exit 0 |
| U+2029 PARAGRAPH SEPARATOR | Accepted, exit 0 |
| U+3000 IDEOGRAPHIC SPACE | Accepted, exit 0 |
| `a` + U+2003 + `b` | Accepted, exit 0 |

The whitespace-only probes used an identity package with one declared inventory atom, equal initial/final stages, no laws, and identical input/output containing that atom. Thus their acceptance does not depend on any sound-rule transformation. The embedded-whitespace probe added `a` + U+2003 + `b` to the inventory of an otherwise valid `p → f` dossier; the invalid inventory entry was accepted even when unused.

Minimal reproduction from the repository root (no repository writes):

```bash
python3 - <<'PY'
import json
import subprocess

symbol = '\u00a0'
model = dict(
    id='review-symbol', version='1.0.0',
    description='Temporary implementation review probe.',
    inventory=[symbol], initial_stage='s0', final_stage='s0', laws=[])
dossier = dict(
    schema_version='1.0.0', id='review-symbol', model=model,
    certificate=dict(
        package_id=model['id'], package_version=model['version'],
        input=[symbol], steps=[], output=[symbol]))
result = subprocess.run(
    ['lean/.lake/build/bin/verify_dossiers', '--file', '/dev/stdin'],
    input=json.dumps(dossier, ensure_ascii=False),
    capture_output=True, text=True, timeout=10)
print(result.returncode, result.stdout)
PY
```

Observed before correction: exit `0` and `{"issues":[],"accepted":true}`. Required behavior: reject with `INVENTORY` and exit `1`.

The initially inspected fixture generator only exercised ASCII embedded whitespace (`"a b"`). The recommended correction was to cover Unicode whitespace while retaining C0/C1 exclusion, with regressions for non-ASCII and embedded whitespace. The pinned prose semantics did not need to change.

### Correction and recheck

The corrected `RuleInput.lean` defines `ruleWhitespace` using an explicit 25-code-point Unicode White_Space set and rejects any such character inside a symbol. C0/C1 controls remain excluded. I inspected this change and the fixture-generator additions: one case for each of the 18 non-ASCII non-control whitespace code points and one embedded-whitespace case.

Using the rebuilt executable, I independently checked all 25 listed whitespace code points twice: once as the entire atom and once embedded between `a` and `b`. All **50 probes** returned rejection with `INVENTORY` and exit `1`. Four valid baseline atoms (`a`, `a̱`, `tʰ`, `⁵⁵`) remained accepted, including combining and multi-code-point symbols. These were read-only `--file /dev/stdin` calls and did not regenerate fixtures or reports.

Rechecked code points: U+0009–U+000D, U+0020, U+0085, U+00A0, U+1680, U+2000–U+200A, U+2028, U+2029, U+202F, U+205F, U+3000. The source comment attributes this set to Unicode 17.0; I inspected the local predicate and tested its stated set, without independently reviewing that external data file.

- Rechecked executable SHA-256: `9288c74b7d478b44ba1ecf6017df6f480691311355a4874ef3e0e89123e1c539`.
- Rechecked `RuleInput.lean` SHA-256: `b07bff88f3441029d9c75038511df1bf8e37e5053171ff1fd716826b5db711f0`.

## Other inspected contracts

- `Rules.lean` consumes each original token once. Original and produced prefixes remain nearest-first; simultaneous mode reads the original prefix, while feeding reads the produced prefix. Deletion updates only the produced side, and right-to-left execution reverses the word and swaps sides/anchors without reversing context lists. I found no mismatch in those mechanisms.
- The `Emits`, `Scan`, and `Pass` relations have local copying/replacement/deletion and scan constructors. `checkTrace_iff` connects the checker to `LicensedTrace` for the exact supplied law IDs, stage labels, intermediate words, and final word. Its soundness/completeness statement is not merely existence of some trace reaching the same output. `checkDossier_iff` additionally requires empty validation diagnostics. I found no vacuous replacement of the required entire-trace theorem in these sources.
- Package validation checks distinct law IDs and chronological stage names, continuous input/output stages, final-stage closure, finite declared inventories, target/replacement/context membership, and the two-token bound. Certificate validation checks named package/version identity and every input/intermediate/final token. Runtime probes rejected wrong stages, missing steps, corrupt intermediate output with a correct final output, wrong package versions, invalid final-stage closure, and repeated stage names.
- The typed rule grammar has no callback, lexical-ID predicate, word map, or multi-token replacement operation. Runtime probes rejected hidden fields at the dossier, certificate, and rule levels with `JSON_SHAPE`; literal wildcard inventory entries with `INVENTORY`; empty classes with `CONTEXT_CLASS`; and nested duplicate keys, including an escaped spelling of the same key, with `DUPLICATE_JSON_KEY`.
- Six additional manually expected CLI evaluations matched: distinct two-token right context during right-to-left scanning; deletion exposing the right edge during right-to-left feeding; replacement bleeding in each direction; an edge anchor after two consumed context tests; and rejection of that anchor when one extra token remains.
- The fixture generator obtains the independent example outputs from the frozen response file and uses explicit mutations for adversarial cases. The extra Python oracle uses original indices and output slots, and is described as unverified test infrastructure. The verification source compares every stage and final word, verifies review provenance/hashes, and describes finite enumeration limits. The delivery documentation separates synthetic semantics from historical claims and acknowledges parser/validator trust boundaries and shared-AI review limitations.

## Scope and limits

The implementation review inspected `lean/Historical/Rules.lean`, `lean/Historical/Certificates.lean`, `lean/Historical/RuleInput.lean`, `lean/VerifyDossiers.lean`, `scripts/build_m2_fixtures.py`, `scripts/reference_rules.py`, `scripts/verify_m2.py`, `tests/test_m2_contracts.py`, `docs/08-m2-delivery.md`, and the M2 entry in `data/milestones.json`, against the already-read prose semantics. The inspected milestone status/artifact registration and delivery counts were transitional, and the parent agent was still completing them.

I did not rebuild Lean, run mutating fixture/report scripts, inspect the shared JSON parser implementation or proof-audit implementation, independently rerun the kernel audit, validate CI execution, or inspect all generated fixture/report bytes. The targeted binary probes supplement source inspection; they do not cover all packages or establish agreement between every source revision and a compiled binary. I did not alter either frozen hand-work artifact, the prose semantics, validators, milestones, or implementation files. Only this review note was written.

This review does not establish historical validity, natural classes, genuine linguistic segmenthood, or freedom from empirical overfitting. Restricting the program grammar cannot authenticate the linguistic interpretation of user-declared atoms or packages.
