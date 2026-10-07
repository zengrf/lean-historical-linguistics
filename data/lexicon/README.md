# Reflex-only reconstruction inputs

Each JSON file supplies daughter-language forms, global sound-law models and
protoform constraints. It contains no candidate protoform pool. Corresponding
TSV files can be pasted into the **Reconstruct a lexicon** view.

See [the M7 input contract and examples](../../docs/15-m7-delivery.md).
Regenerate with `python scripts/build_m7_fixtures.py`; use `--check` to compare
retained bytes. `scaling.json` has 1,000 distinct synthetic cognate rows.

`pie.json` uses retained IE-CoR daughter forms (CC BY 4.0) and existing M5 fitted
rule packages. `kuki.json` projects the Mizo and Thado Kuki ARM reflexes from
VanBik 2009, PDF p.93, entry 1, with tone omitted. Their descriptions state the
restricted model scope. Neither is a complete family grammar or independent
accuracy evaluation. Other examples are synthetic controls.
