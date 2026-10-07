"""Exercise the primary reflex-table UI against native Lean in a real browser."""

import argparse
import hashlib
import json
from pathlib import Path
import threading

from build_pie_corpus import ROOT, encoded
from serve_ui import make_server
from verify_ui import Browser


def verify(url, directory, chrome=None):
    directory.mkdir(parents=True, exist_ok=True)
    b = Browser(chrome)
    checks = []

    def check(name, expression):
        assert b.evaluate(expression), name
        checks.append(name)

    def run():
        b.evaluate("document.getElementById('lex-run').click()")
        b.wait(
            "!document.getElementById('lex-run').disabled && document.getElementById('lex-status').textContent.startsWith('Complete.')",
            timeout=90,
        )

    def example(key):
        b.evaluate(
            "document.getElementById('lex-example').value="
            + json.dumps(key)
            + ";document.getElementById('lex-example').dispatchEvent(new Event('change'))"
        )
        b.wait(
            "!document.getElementById('lex-run').disabled && document.getElementById('lex-status').textContent.startsWith('Ready.')"
        )

    try:
        b.size(1440, 1050)
        b.call("Page.navigate", dict(url=url))
        b.wait(
            "document.getElementById('lex-status')?.textContent.startsWith('Ready.')"
        )
        check(
            "reflex reconstruction is the primary view",
            "!document.getElementById('panel-lexicon').hidden && document.getElementById('panel-evidence').hidden",
        )
        check(
            "reflex input distinguishes missing, unknown and empty",
            "document.getElementById('lex-table-details').textContent.replace(/\\s+/g,' ').includes('Blank = missing word; ? = one unknown segment; ∅ = an observed empty form')",
        )
        run()
        check(
            "enumerates model-qualified whole lexicons",
            "document.getElementById('lex-total').textContent==='5 allowed protolexicons'",
        )
        check(
            "both local roots displayed",
            "document.querySelectorAll('.lex-derivation').length===2 && document.getElementById('lex-candidates').textContent.includes('*ba') && document.getElementById('lex-candidates').textContent.includes('*pa')",
        )
        b.evaluate(
            "document.querySelector('.lex-derivation').open=true; document.querySelector('.lex-derivation details').open=true"
        )
        check(
            "derivation comes from the native rule trace",
            "document.getElementById('lex-candidates').textContent.includes('mergers-A-law-0')",
        )
        b.screenshot(directory / "desktop.png")
        b.evaluate(
            "document.getElementById('lex-view').value='lexicons'; document.getElementById('lex-view').dispatchEvent(new Event('change'))"
        )
        b.wait(
            "document.querySelector('.lex-whole') && !document.getElementById('lex-go').disabled"
        )
        check(
            "whole lexicon has one model and both rows",
            "document.querySelector('.lex-whole').textContent.includes('mergers · lexicon 0') && document.querySelectorAll('.lex-whole tr').length===3",
        )
        b.evaluate("document.getElementById('lex-next').click()")
        b.wait(
            "document.querySelector('.lex-whole h4')?.textContent.endsWith('lexicon 1')"
        )
        check(
            "pagination advances whole lexicons",
            "document.getElementById('lex-offset').value==='1'",
        )
        b.evaluate(
            "document.getElementById('lex-max').value='1';document.getElementById('lex-max').dispatchEvent(new Event('input'))"
        )
        check(
            "edits invalidate complete results",
            "document.getElementById('lex-results').hidden && document.getElementById('lex-export').disabled",
        )
        example("conflict")
        run()
        check(
            "global conflict is not independent wordwise model mixing",
            "document.getElementById('lex-total').textContent==='0 allowed protolexicons' && document.getElementById('lex-model-summary').textContent.includes('No full lexicon')",
        )
        example("merger")
        b.evaluate(
            "document.getElementById('lex-table').value='id\\tmeaning\\tA\\tB\\ncustom\\tImported word\\tp a\\tp a\\n';document.getElementById('lex-table').dispatchEvent(new Event('input'))"
        )
        run()
        check(
            "pasted TSV is actually used",
            "document.getElementById('lex-total').textContent==='3 allowed protolexicons' && document.getElementById('lex-entry').textContent.includes('Imported word')",
        )
        b.evaluate(
            "document.querySelector('input[name=lex-model][value=identity]').click()"
        )
        run()
        check(
            "model selection constrains the complete search",
            "document.getElementById('lex-total').textContent==='2 allowed protolexicons'",
        )
        b.evaluate(
            "document.getElementById('lex-shapes').value='[[[\"b\"],[\"a\"]]]';document.getElementById('lex-shapes').dispatchEvent(new Event('input'))"
        )
        run()
        check(
            "slot constraints change the inverse set",
            "document.getElementById('lex-total').textContent==='1 allowed protolexicons'",
        )
        b.call(
            "Browser.setDownloadBehavior",
            dict(behavior="allow", downloadPath=b.folder.name),
        )
        b.evaluate("document.getElementById('lex-export').click()")
        import time

        path = Path(b.folder.name) / "checked-protolexicons.json"
        for _ in range(200):
            if path.exists():
                break
            time.sleep(0.05)
        downloaded = json.loads(path.read_text())
        assert (
            downloaded["summary"]["complete"]
            and downloaded["forest"]["request"]["entries"][0]["id"] == "custom"
        )
        checks.append("downloads the checked graph and exact request")
        example("merger")
        b.evaluate(
            "document.getElementById('lex-budget').value='1';document.getElementById('lex-budget').dispatchEvent(new Event('input'));document.getElementById('lex-run').click()"
        )
        b.wait(
            "!document.getElementById('lex-run').disabled && document.getElementById('lex-status').classList.contains('error')"
        )
        check(
            "budget exhaustion cannot appear as a complete empty set",
            "document.getElementById('lex-results').hidden && document.getElementById('lex-status').textContent.includes('completeness is not established')",
        )
        b.evaluate("document.getElementById('lex-budget').value='250000'")
        example("pie")
        run()
        b.evaluate(
            "document.getElementById('lex-view').value='words';document.getElementById('lex-view').dispatchEvent(new Event('change'))"
        )
        b.wait(
            "document.querySelector('.lex-derivation') && !document.getElementById('lex-go').disabled"
        )
        check(
            "PIE example is generative and fitted-model scope is visible",
            "document.getElementById('lex-candidates').textContent.includes('*koḱs') && document.getElementById('lex-description').textContent.includes('fitted correspondence baseline')",
        )
        example("kuki")
        run()
        check(
            "Kuki-Chin ambiguity retained",
            "document.getElementById('lex-total').textContent==='2 allowed protolexicons'",
        )
        b.size(390, 900)
        b.evaluate("document.querySelector('input[name=theme][value=night]').click()")
        check(
            "mobile has no page-level horizontal overflow",
            "document.documentElement.scrollWidth<=window.innerWidth",
        )
        check(
            "original Kiwari theme is used",
            "document.documentElement.dataset.time==='night' && [...document.styleSheets].some(s=>s.href?.endsWith('/vendor/kiwari/slides.css'))",
        )
        b.screenshot(directory / "mobile-night.png")
        errors = [e for e in b.events if e.get("method") == "Runtime.exceptionThrown"]
        assert not errors, errors
        checks.append("no uncaught browser exceptions")
        names = [
            "web/index.html",
            "web/style.css",
            "web/lexicon.js",
            "scripts/lexicon_api.py",
            "scripts/verify_m7_ui.py",
        ]
        report = dict(
            passed=True,
            checks=checks,
            input_hashes={
                n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in names
            },
        )
        (directory / "checks.json").write_bytes(encoded(report))
        print(f"M7 browser: {len(checks)} checks passed.")
        return report
    finally:
        b.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url")
    p.add_argument("--chrome")
    p.add_argument("--output", type=Path, default=ROOT / "reports/m7-ui")
    args = p.parse_args()
    server = None
    try:
        if not args.url:
            server = make_server(0)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            args.url = f"http://127.0.0.1:{server.server_port}"
        verify(args.url, args.output, args.chrome)
    finally:
        if server:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
