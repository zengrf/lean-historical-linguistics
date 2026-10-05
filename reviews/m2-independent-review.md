# M2 independent manual derivation review

Reviewer: `/root/m2_hand_review`, a separate AI agent with fresh task context (`independent_ai_agent`). This is an independent AI derivation review, not human sign-off or family-specialist sign-off.

I read only the supplied packet and its pinned prose semantics. I checked the applicable ancestor, project, docs, and reviews `AGENTS.md` paths; none was present. I did not inspect an interpreter, implementation, Lean source, scripts, data fixtures, expected answers, validation results, or other reports. The read boundary was imposed by instructions on a shared filesystem, not enforced by a technical sandbox.

The exact scope is all 20 cases in `reviews/m2-packet.json`, comprising 22 rule passes under `docs/rule-semantics.md` version 1.0.0. Each output was derived by hand from the prose with one-based original-token positions for each pass. Right-to-left scans were reasoned in visitation order, while result words retain their normal order. All post-rule words, including unchanged stages and the empty-word stage, are present in `m2-responses.json` with position-by-position rationales.

The prose file SHA-256 was verified against the packet before these responses were written:

- Prose file SHA-256: `bd93cd34d4d06ea6a5cf224062514ec7a97fbc370f55653d2ce471ff4da449f8`
- Canonical packet SHA-256: `a5e1d7c7a1d0bd9aa32ecc2d4ad54bbc828f235f9cc3733cab537987c7a610f8`
- Packet hash convention: `SHA256(json.dumps(packet, ensure_ascii=False, sort_keys=True).encode())`, using the default JSON separators.

No specification ambiguity was encountered for these 20 cases. Context lists were read nearest-first; wildcards excluded boundaries; simultaneous contexts used original input; feeding contexts used output on the visited side and original input on the unvisited side; anchors applied after context consumption. These examples do not exercise every possible combination permitted by the prose.

The answers below and their full rationales in the JSON were frozen before any implementation comparison. Python was used only to read the allowed JSON, calculate hashes, serialize the manually entered answers, and check answer structure and pass counts. No rule transformation was executed to obtain or check an answer.

| Case | Post-rule word(s), in pass order |
| --- | --- |
| `unconditional` | `["f", "a", "f", "a"]` |
| `intervocalic` | `["p", "a", "b", "a", "p"]` |
| `word-initial` | `["f", "a", "p"]` |
| `word-final-deletion` | `["t", "a"]` |
| `morpheme-context` | `["p", "+", "b", "a"]` |
| `ltr-simultaneous` | `["b", "b", "a"]` |
| `ltr-feeding` | `["b", "b", "b"]` |
| `rtl-simultaneous` | `["a", "b", "b"]` |
| `rtl-feeding` | `["b", "b", "b"]` |
| `deletion-simultaneous` | `["b", "a"]` |
| `deletion-feeding` | `["b"]` |
| `unvisited-context` | `["b", "b", "p"]` |
| `rtl-word-initial` | `["f", "a", "p"]` |
| `two-token-context` | `["p", "a", "d"]` |
| `boundary-blocks-wildcard` | `["a", "+", "p", "a"]` |
| `ordered-cascade` | `["f", "a"]` → `["v", "a"]` |
| `reversed-cascade` | `["p", "a"]` → `["f", "a"]` |
| `unicode-atoms` | `["a̱", "s", "⁵⁵"]` |
| `edge-exposed-by-deletion` | `["b"]` |
| `empty-word` | `[]` |

These are synthetic semantics derivations. I make no claim of historical validity, genuine linguistic segmenthood, natural classes, valid PIE or Sino-Tibetan analysis, or empirical generalization. I did not review package validation, parser behavior, certificates, Lean proofs, or implementation agreement. A separate AI agent adds a fresh derivation but does not provide human, external, or family-specialist review.
