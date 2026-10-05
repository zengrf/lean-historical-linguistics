# Verification records

`library-audit.json` is the saved **full local** acquisition audit, produced with:

```bash
python scripts/verify_library.py --local --output reports/library-audit.json
```

It records the time, count decisions, source coverage, access gaps and actual checks of all 127 retained PDF files. It attests to the files checked at that time. It does not establish exhaustive literature coverage or cover-to-cover reading. A public clone contains 64 PDFs; its ordinary audit therefore has a different on-disk count.

`lean-axioms-local.txt` records `#print axioms` for all 22 theorem declarations after a successful local build with **Lean 4.19.0 on macOS 10.15 x86_64**. Its reported dependencies are `propext` and `Quot.sound`. There are no project axioms or proof placeholders in the audited source.

The local host could not run the Lean 4.34.1 binary because its system C++ library lacks a required symbol. [GitHub Actions](https://github.com/zengrf/lean-historical-linguistics/actions/workflows/ci.yml) independently builds the source on Linux with both 4.19.0 and the pinned 4.34.1, then checks each generated theorem audit. Consult the run for the commit being evaluated; a committed old report alone does not validate changed source.

The plan validator checks the machine-readable register's structure and delivered artifact paths. The library verifier checks PDF identity and metadata consistency. Neither substitutes for the future linguistic review and empirical evaluation specified in the delivery plan.
