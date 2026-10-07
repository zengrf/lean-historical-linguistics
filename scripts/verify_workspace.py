"""Run native workspace tests and browser workflows; retain reproducible evidence."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time

from build_pie_corpus import ROOT, encoded
from workspace_server import make_server


def hashes():
    paths = [
        *ROOT.glob("scripts/workspace_*.py"),
        ROOT / "scripts/linguist_notation.py",
        ROOT / "scripts/verify_workspace.py",
        ROOT / "tests/test_workspace.py",
        *ROOT.glob("web/workspace.*"),
        ROOT / "requirements-workspace.txt",
        ROOT / "scripts/lexicon.py",
        ROOT / "scripts/m7_solver.py",
    ]
    paths += [p for p in (ROOT / "lean").rglob("*.lean") if ".lake" not in p.parts]
    return {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths)
    }


def browser_checks(directory, chrome=None):
    from verify_ui import Browser

    checks = []
    with tempfile.TemporaryDirectory(prefix="workspace-test-") as workspace:
        app, server = make_server(workspace)

        def serve():
            try:
                server.run()
            except OSError:
                pass  # The test closes the listening socket during shutdown.

        threading.Thread(target=serve, daemon=True).start()
        b = Browser(chrome)

        def check(name, expression):
            assert b.evaluate(expression), name
            checks.append(name)

        def click(id):
            b.evaluate(f"document.getElementById({json.dumps(id)}).click()")

        def value(id, text, event="change"):
            b.evaluate(
                f"(()=>{{const e=document.getElementById({json.dumps(id)});e.value={json.dumps(text)};e.dispatchEvent(new Event({json.dumps(event)},{{bubbles:true}}));}})()"
            )

        def text(id):
            return f"document.getElementById({json.dumps(id)}).textContent"

        def api(path, body=None):
            return b.evaluate(
                "(async()=>{const s=await (await fetch('/api/workspace/session')).json();const r=await fetch('/api/workspace/"
                + path
                + "',"
                + (
                    json.dumps({})
                    if body is None
                    else "{method:'POST',headers:{'Content-Type':'application/json','X-Workspace-Token':s.token},body:JSON.stringify("
                    + json.dumps(body)
                    + ")}"
                )
                + ");return {status:r.status,body:await r.json()};})()"
            )

        try:
            b.size(1440, 1000)
            b.call("Page.navigate", dict(url=app.launch_url))
            b.wait("document.getElementById('ws-create-dialog')?.open")
            check(
                "launch credential removed from address bar",
                "location.search==='' && !document.cookie.includes('comparative_')",
            )
            value("ws-new-title", "Comparative research · source review")
            click("ws-create")
            b.wait("document.querySelectorAll('#ws-grid tbody tr').length===2")
            check(
                "cognate-set table is the starting view",
                "!document.getElementById('ws-wordlist').hidden && document.getElementById('ws-results').hidden",
            )
            project_id = b.evaluate("document.getElementById('ws-project').value")
            check(
                "daughter columns and source controls are named",
                "document.querySelector('#ws-grid thead').textContent.includes('A') && document.querySelectorAll('.form-cell button[aria-label]').length===4",
            )
            check(
                "original Kiwari fonts and materials loaded",
                "getComputedStyle(document.body).fontFamily.includes('EB Garamond') && getComputedStyle(document.documentElement).getPropertyValue('--tx-washi').includes('data:image/svg')",
            )
            b.evaluate(
                'document.querySelector(\'[data-grid-row="0"][data-grid-column="0"]\').focus()'
            )
            b.call(
                "Input.dispatchKeyEvent",
                dict(
                    type="keyDown", key="Enter", code="Enter", windowsVirtualKeyCode=13
                ),
            )
            check(
                "Enter moves to next cognate set",
                "document.activeElement.dataset.gridRow==='1'",
            )
            b.evaluate(
                "document.querySelector('#ws-grid tbody .form-cell button').click()"
            )
            b.wait("document.getElementById('ws-reading-dialog').open")
            value("ws-reading-original", "<printed reading> & 甲")
            value("ws-reading-witness", "MS A")
            value("ws-reading-locator", "folio 12r, line 3")
            value("ws-reading-alignment", "p a")
            value("ws-reading-certainty", "low")
            value(
                "ws-reading-note",
                "Editorial uncertainty retained separately from the comparison segments.",
            )
            click("ws-add-reading")
            b.evaluate(
                "(()=>{const inputs=document.querySelectorAll('.alternative-reading input');['βa','b a','Edition B','MS B','p. 21','Alternative reading'].forEach((v,i)=>{inputs[i].value=v;inputs[i].dispatchEvent(new Event('change'));});})()"
            )
            click("ws-save-reading")
            b.wait("!document.getElementById('ws-reading-dialog').open")
            check(
                "source notes mark project as unsaved",
                text("ws-save-state") + ".includes('Unsaved')",
            )
            click("ws-save")
            b.wait(text("ws-save-state") + ".includes('Saved revision 2')")
            saved = api("project?id=" + project_id)["body"]
            note = saved["document"]["annotations"]['["one","A"]']
            assert note["original"] == "<printed reading> & 甲" and note[
                "alternatives"
            ][0]["form"] == ["b", "a"]
            checks.append(
                "original reading, witness, locator and alternative preserved in saved revision"
            )
            b.evaluate(
                "document.querySelector('#ws-grid tbody .form-cell button').click()"
            )
            b.wait("document.getElementById('ws-reading-dialog').open")
            b.screenshot(directory / "reading.png")
            b.evaluate("document.querySelector('.alternative-reading button').click()")
            check(
                "alternative choice retains former reading",
                "document.getElementById('ws-reading-form').value==='b a' && document.querySelector('.alternative-reading input').value==='<printed reading> & 甲'",
            )
            # Swap back, retaining the same two source readings.
            b.evaluate("document.querySelector('.alternative-reading button').click()")
            click("ws-save-reading")
            b.wait("!document.getElementById('ws-reading-dialog').open")
            click("ws-save")
            b.wait(text("ws-save-state") + ".includes('Saved revision 3')")
            b.screenshot(directory / "wordlist.png")
            value("ws-title", "Temporary title")
            click("ws-undo")
            check(
                "title edit can be undone",
                "document.getElementById('ws-title').value==='Comparative research · source review'",
            )
            click("ws-redo")
            check(
                "title edit can be redone",
                "document.getElementById('ws-title').value==='Temporary title'",
            )
            click("ws-undo")
            click("ws-save")
            b.wait(text("ws-save-state") + ".includes('Saved revision 4')")
            # Reference form is deliberately kept apart from the reconstruction request.
            b.evaluate("document.querySelector('#ws-grid .set-id button').click()")
            value("ws-row-reference", "b a")
            value("ws-row-split", "test")
            click("ws-save-row")
            b.wait("!document.getElementById('ws-row-dialog').open")
            click("ws-tab-rules")
            check(
                "sound changes use conventional readable notation",
                "document.getElementById('ws-rule-text').value.includes('b > p')",
            )
            value("ws-rule-text", "∅ > p", "input")
            click("ws-apply-rules")
            b.wait("document.querySelector('#ws-message').classList.contains('error')")
            check(
                "unsupported insertion has an actionable error",
                text("ws-message") + ".includes('Insertion')",
            )
            value("ws-rule-text", "b > p\nd > t", "input")
            click("ws-apply-rules")
            b.wait(text("ws-rule-status") + ".includes('Applied')")
            b.screenshot(directory / "sound-changes.png")
            click("ws-tab-results")
            value("ws-shapes", "[p b t d] a", "input")
            click("ws-apply-constraints")
            b.wait(text("ws-message") + ".includes('word shapes applied')")
            click("ws-run")
            b.wait(
                "document.querySelectorAll('#ws-candidates .candidate').length===2",
                timeout=60,
            )
            check(
                "native search returns two protoforms and five model-qualified lexicons",
                text("ws-result-total")
                + ".startsWith('5 allowed') && "
                + text("ws-candidates")
                + ".includes('*b a')",
            )
            b.wait(text("ws-evaluation") + ".includes('Reference-form evaluation')")
            value("ws-max", "3", "input")
            check(
                "editing marks saved results as belonging to a previous state",
                text("ws-result-provenance") + ".includes('unsaved edits')",
            )
            click("ws-undo")
            check(
                "held-out partition evaluation is separately labeled",
                text("ws-evaluation")
                + ".includes('test') && "
                + text("ws-evaluation")
                + ".includes('not search inputs')",
            )
            b.evaluate(
                "document.querySelector('#ws-candidates .candidate').open=true; document.querySelector('#ws-candidates .candidate details').open=true"
            )
            check(
                "native forward traces display rule and successive forms",
                text("ws-candidates")
                + ".includes('b > p') && document.querySelectorAll('#ws-candidates .simple-table tr').length>2",
            )
            b.screenshot(directory / "reconstructions.png")
            value("ws-result-view", "lexicons")
            b.wait(
                "document.querySelector('#ws-candidates h3')?.textContent==='Wordlist 1'"
            )
            check(
                "one model governs both reconstructed entries",
                "document.querySelectorAll('#ws-candidates .candidate').length===2",
            )
            click("ws-result-next")
            b.wait(
                "document.querySelector('#ws-candidates h3')?.textContent==='Wordlist 2'"
            )
            check(
                "whole-wordlist pagination advances without rounding",
                "document.getElementById('ws-result-number').value==='2'",
            )
            for kind in ["project", "edictor", "cldf", "tei"]:
                check(
                    kind + " export available",
                    f"(async()=>{{const r=await fetch('/api/workspace/export?id={project_id}&format={kind}');return r.ok && (await r.blob()).size>20}})()",
                )
            checks.append("exports are retrieved through the authenticated session")
            jobs = api("jobs?id=" + project_id)["body"]["jobs"]
            result = app.jobs.result(jobs[0]["id"])
            assert "_references" not in json.dumps(result["forest"]["request"])
            checks.append(
                "native search input contains no reference reconstruction annotations"
            )
            # Force a small exhausted budget; no complete result is fabricated.
            value("ws-nodes", "1")
            click("ws-run")
            b.wait(text("ws-jobs") + ".includes('incomplete')", timeout=45)
            check(
                "exhausted search is visibly incomplete",
                text("ws-jobs") + ".includes('incomplete')",
            )
            value("ws-nodes", "250000")
            click("ws-tab-history")
            b.wait("document.querySelector('#ws-history-list .revision')")
            check(
                "immutable revision history available",
                "document.querySelectorAll('#ws-history-list .revision').length>=5",
            )
            check(
                "full workspace backup downloadable",
                "(async()=>{const r=await fetch('/api/workspace/backup');return r.ok && (await r.blob()).size>1000})()",
            )
            # Restore revision 1 using the UI; later revisions remain.
            b.evaluate(
                "document.querySelector('#ws-history-list .revision:last-child button').click()"
            )
            b.wait(
                text("ws-message")
                + ".includes('Opened') && document.getElementById('ws-title').value==='Comparative research · source review'"
            )
            current = api("project?id=" + project_id)["body"]
            assert current["revision"] > 5 and current["document"]["annotations"] == {}
            checks.append("restoring creates a new revision and retains later analyses")
            # Exercise real TSV import and script-text rendering.
            click("ws-import")
            value(
                "ws-import-text",
                "ID\tDOCULECT\tCONCEPT\tTOKENS\tCOGID\n1\tA\t<script>window.injected=1</script>\tp a\t1\n2\tB\t<script>window.injected=1</script>\tp a\t1\n",
            )
            click("ws-do-import")
            b.wait(
                "!document.getElementById('ws-import-dialog').open && document.querySelectorAll('#ws-grid tbody tr').length===1"
            )
            check(
                "source markup displays as text",
                "window.injected===undefined && document.querySelector('#ws-grid .gloss').textContent.includes('<script>')",
            )
            # Draft recovery across page reload; edits survive without being published.
            value("ws-notes", "Recoverable browser draft")
            b.call("Page.reload")
            # beforeunload can arrive after the reload command is acknowledged.
            for _ in range(100):
                try:
                    b.call("Page.handleJavaScriptDialog", dict(accept=True))
                    break
                except RuntimeError as error:
                    if "No dialog is showing" not in str(error):
                        raise
                    time.sleep(0.05)
            b.wait("!document.getElementById('ws-recovery').hidden")
            click("ws-recover")
            check(
                "browser draft recovers after reload",
                "document.getElementById('ws-notes').value==='Recoverable browser draft'",
            )
            click("ws-save")
            b.wait(text("ws-save-state") + ".includes('Saved revision 2')")
            # Cross-window conflict: browser must keep its draft.
            imported_id = b.evaluate("document.getElementById('ws-project').value")
            imported = api("project?id=" + imported_id)["body"]
            assert (
                api(
                    "save",
                    dict(
                        id=imported_id,
                        revision=2,
                        title=imported["title"],
                        document=imported["document"],
                        message="Other window",
                    ),
                )["status"]
                == 200
            )
            value("ws-notes", "Preserve this competing draft")
            click("ws-save")
            b.wait(text("ws-message") + ".includes('another window')")
            check(
                "conflicting save preserves current edits",
                "document.getElementById('ws-notes').value==='Preserve this competing draft'",
            )
            check(
                "unsaved draft can still be exported",
                text("ws-save-state")
                + ".includes('Unsaved') && !document.getElementById('ws-export').disabled",
            )
            # Visit initial project after explicitly retaining the conflicting draft.
            b.evaluate("window.confirm=()=>true")
            value("ws-project", project_id)
            b.wait("document.querySelectorAll('#ws-grid tbody tr').length===2")
            b.evaluate(
                "document.getElementById('ws-title').focus();document.getElementById('ws-title').select()"
            )
            b.call("Input.insertText", dict(text="Keyboard saved title"))
            b.call(
                "Input.dispatchKeyEvent",
                dict(
                    type="keyDown",
                    key="s",
                    code="KeyS",
                    modifiers=2,
                    windowsVirtualKeyCode=83,
                ),
            )
            b.wait(text("ws-save-state") + ".startsWith('Saved revision')")
            # Wait for the actual disk revision, not an unchanged initial label.
            deadline = time.monotonic() + 10
            while (
                api("project?id=" + project_id)["body"]["title"]
                != "Keyboard saved title"
                and time.monotonic() < deadline
            ):
                time.sleep(0.05)
            assert (
                api("project?id=" + project_id)["body"]["title"]
                == "Keyboard saved title"
            )
            checks.append("Ctrl-S commits the actively edited field before saving")
            value("ws-title", "Comparative research · source review")
            click("ws-save")
            b.wait(text("ws-save-state") + ".startsWith('Saved revision')")
            b.size(390, 844)
            click("ws-tab-wordlist")
            check(
                "mobile page stays within viewport",
                "document.documentElement.scrollWidth <= innerWidth",
            )
            b.screenshot(directory / "mobile.png")
            b.size(1440, 1000)
            b.evaluate(
                "document.querySelector('input[name=theme][value=night]').click()"
            )
            check(
                "night appearance uses original theme variables",
                "document.documentElement.dataset.time==='night' && getComputedStyle(document.body).color==='rgb(230, 220, 194)'",
            )
            b.screenshot(directory / "night.png")
            b.evaluate("document.getElementById('ws-tab-wordlist').focus()")
            b.call(
                "Input.dispatchKeyEvent",
                dict(
                    type="keyDown",
                    key="ArrowRight",
                    code="ArrowRight",
                    windowsVirtualKeyCode=39,
                ),
            )
            check(
                "tab views support keyboard navigation",
                "document.activeElement.id==='ws-tab-rules' && document.activeElement.getAttribute('aria-selected')==='true'",
            )
            check(
                "legacy research tools remain authenticated and available",
                "(async()=>{const r=await fetch('/legacy');return r.ok && (await r.text()).includes('lex-run')})()",
            )
            errors = [
                e for e in b.events if e.get("method") == "Runtime.exceptionThrown"
            ]
            assert not errors, errors
            checks.append("no uncaught browser exceptions")
        finally:
            b.close()
            server.close()
            app.close()
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/workspace")
    parser.add_argument("--chrome")
    parser.add_argument("--check-report", action="store_true")
    args = parser.parse_args()
    report = args.output / "verification.json"
    if args.check_report:
        retained = json.loads(report.read_text())
        assert (
            retained["passed"] and retained["input_hashes"] == hashes()
        ), "Stale workspace verification evidence"
        for name, digest in retained["screenshots"].items():
            assert (
                hashlib.sha256((args.output / name).read_bytes()).hexdigest() == digest
            ), name
        print(
            "Workspace verification evidence matches current sources and screenshots."
        )
        return
    args.output.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_workspace.py",
            "-v",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    (args.output / "backend-tests.txt").write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "skipped=" not in result.stderr, "Native integration checks must run"
    checks = browser_checks(args.output, args.chrome)
    report.write_bytes(
        encoded(
            dict(
                passed=True,
                backend_tests=int(re.search(r"Ran (\d+) tests", result.stderr)[1]),
                browser_checks=checks,
                screenshots={
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(args.output.glob("*.png"))
                },
                input_hashes=hashes(),
                scope="Private local research workspace; this is automated verification, not a specialist or usability study.",
            )
        )
    )
    print(f"Native workspace tests and {len(checks)} browser checks passed.")


if __name__ == "__main__":
    main()
