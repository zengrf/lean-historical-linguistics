# Local workspace verification

The screenshots are captures of the running application, with synthetic
comparison data and explicitly illustrative manuscript annotations. They are
not source attestations. The interface uses the original Kiwari package.

| View | Screenshot |
| --- | --- |
| Comparative wordlist | [wordlist.png](wordlist.png) |
| Printed reading, witness and alternatives | [reading.png](reading.png) |
| Ordered sound changes | [sound-changes.png](sound-changes.png) |
| Selected constraints, all allowed forms and checked derivations | [reconstructions.png](reconstructions.png) |
| Mobile wordlist | [mobile.png](mobile.png) |
| Night appearance | [night.png](night.png) |

[verification.json](verification.json) contains 35 backend tests, 38 browser
checks and the hashes of the actual inputs and captures. The backend output is
retained in [backend-tests.txt](backend-tests.txt). Tests run against the built
native Lean executable; they do not substitute a mocked reconstruction result.
The full repository unit suite also passed: 176 tests.

Reproduce with `python scripts/verify_workspace.py` after `./workbench setup`
and installation of `requirements-ui-test.txt`. CI repeats the workflow with
Lean 4.19.0 and 4.34.1. `--check-report` verifies the retained input and screenshot
hashes. See the [operating guide](../../docs/17-research-workspace.md) for the
private deployment boundary and the [release gates](../../docs/18-production-readiness.md)
for unresolved scientific, usability and distribution requirements.
