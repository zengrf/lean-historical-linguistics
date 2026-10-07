"""Exercise the actual browser, API and Lean; capture desktop/mobile previews.

Requires Chrome/Chromium and requirements-ui-test.txt. Starts its own loopback
server unless --url is supplied. Uses Chrome's documented DevTools protocol.
"""

import argparse
import base64
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
from urllib.request import urlopen

import websocket
from build_pie_corpus import ROOT, encoded
from serve_ui import make_server


class Browser:
    def __init__(self, chrome=None):
        self.folder = tempfile.TemporaryDirectory(prefix="comparative-browser-")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        chrome = (
            chrome
            or os.environ.get("CHROME")
            or shutil.which("google-chrome")
            or shutil.which("chromium")
            or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        )
        self.process = subprocess.Popen(
            [
                chrome,
                "--headless",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                "--no-sandbox",
                f"--remote-debugging-port={port}",
                f"--remote-allow-origins=http://127.0.0.1:{port}",
                "--user-data-dir=" + self.folder.name,
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self.id = 0
        self.events = []
        for _ in range(200):
            try:
                pages = json.load(urlopen(f"http://127.0.0.1:{port}/json", timeout=1))
                page = next(p for p in pages if p["type"] == "page")
                break
            except (OSError, StopIteration):
                time.sleep(0.05)
        else:
            raise RuntimeError("Chrome did not expose a page")
        self.ws = websocket.create_connection(
            page["webSocketDebuggerUrl"], origin=f"http://127.0.0.1:{port}", timeout=60
        )
        for command in ["Page.enable", "Runtime.enable", "Log.enable"]:
            self.call(command)

    def call(self, method, params=None):
        self.id += 1
        identifier = self.id
        self.ws.send(
            json.dumps(dict(id=identifier, method=method, params=params or {}))
        )
        while True:
            data = json.loads(self.ws.recv())
            if data.get("id") == identifier:
                if "error" in data:
                    raise RuntimeError(data["error"])
                return data.get("result", {})
            self.events.append(data)

    def evaluate(self, expression):
        out = self.call(
            "Runtime.evaluate",
            dict(expression=expression, awaitPromise=True, returnByValue=True),
        )
        if "exceptionDetails" in out:
            raise AssertionError(out["exceptionDetails"])
        return out.get("result", {}).get("value")

    def wait(self, expression, timeout=45):
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            if self.evaluate("Boolean(" + expression + ")"):
                return
            time.sleep(0.05)
        raise AssertionError(
            "Browser condition not reached: "
            + expression
            + "\n"
            + str(self.evaluate("document.body.innerText"))[:2200]
        )

    def size(self, width, height=1000):
        self.call(
            "Emulation.setDeviceMetricsOverride",
            dict(width=width, height=height, deviceScaleFactor=1, mobile=False),
        )

    def screenshot(self, path):
        self.evaluate("document.activeElement?.blur()")
        size = self.call("Page.getLayoutMetrics")["cssContentSize"]
        raw = self.call(
            "Page.captureScreenshot",
            dict(
                format="png",
                captureBeyondViewport=True,
                clip=dict(
                    x=0, y=0, width=size["width"], height=size["height"], scale=1
                ),
            ),
        )
        path.write_bytes(base64.b64decode(raw["data"]))

    def close(self):
        if hasattr(self, "ws"):
            try:
                self.ws.settimeout(5)
                self.call("Browser.close")
            except (websocket.WebSocketException, OSError):
                # Chrome can close the connection before acknowledging shutdown.
                pass
            self.ws.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        if os.name == "posix":
            # Only this test's session: renderer descendants may briefly outlive
            # the browser and continue writing the temporary profile.
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        for attempt in range(20):
            try:
                self.folder.cleanup()
                break
            except OSError as error:
                if error.errno != errno.ENOTEMPTY or attempt == 19:
                    raise
                time.sleep(0.1)


def verify(url, directory, chrome=None):
    directory.mkdir(parents=True, exist_ok=True)
    b = Browser(chrome)
    checks = []

    def check(name, condition):
        assert b.evaluate(condition), name
        checks.append(name)

    def run():
        b.evaluate("document.getElementById('run').click()")
        b.wait(
            "!document.getElementById('run').disabled && document.getElementById('results').getAttribute('aria-busy')==='false'"
        )

    def case(key):
        b.evaluate(
            "document.getElementById('case').value="
            + json.dumps(key)
            + ";document.getElementById('case').dispatchEvent(new Event('change'))"
        )
        b.wait(
            "state.current?.key==="
            + json.dumps(key)
            + " && !document.getElementById('run').disabled"
        )

    try:
        b.size(1440, 1050)
        b.call("Page.navigate", dict(url=url))
        b.wait(
            "typeof state!=='undefined' && state.current?.key==='tones' && state.chronology && !document.getElementById('run').disabled"
        )
        b.evaluate("document.getElementById('tab-evidence').click()")
        check(
            "source discrepancy and source PDF links",
            "document.querySelectorAll('#reading-note a').length===2 && !document.getElementById('reading-note').hidden",
        )
        b.wait("document.fonts.status==='loaded'")
        check(
            "original Kiwari styles and materials are active",
            "[...document.styleSheets].some(s=>s.href?.endsWith('/vendor/kiwari/slides.css')) && getComputedStyle(document.querySelector('.room'),'::before').backgroundImage.includes('data:image/svg+xml') && getComputedStyle(document.querySelector('.top-rail')).backgroundImage.includes('data:image/svg+xml')",
        )
        check(
            "bundled Garamond fonts are actually loaded",
            "[...document.fonts].some(f=>f.family==='EB Garamond' && f.status==='loaded') && [...document.fonts].some(f=>f.family==='Cormorant Garamond' && f.status==='loaded')",
        )
        check(
            "query explains candidate space and required daughter form",
            "document.getElementById('query-summary').textContent.includes('4 candidate tone categories') && document.getElementById('query-summary').textContent.includes('Hakha Lai')",
        )
        run()
        check(
            "distinct reconstructions group compatible analyses",
            "document.querySelectorAll('.candidate').length===3 && document.querySelector('.result-summary').dataset.forms==='3'",
        )
        check(
            "tone merger retains five source-qualified histories",
            "state.result.result.analysis.survivors.length===5",
        )
        check(
            "withheld Mizo prediction distinguishes candidates",
            "state.result.result.analysis.probes.some(p=>p.distinguished_pairs>0)",
        )
        check(
            "equivalence retains both whole readings",
            "state.result.result.analysis.equivalence_classes.length===1 && state.result.result.histories.length===8",
        )
        b.call(
            "Browser.setDownloadBehavior",
            dict(behavior="allow", downloadPath=b.folder.name),
        )
        b.evaluate("document.getElementById('export').click()")
        downloaded = Path(b.folder.name) / "reconstruction-result.json"
        for _ in range(100):
            if downloaded.exists():
                break
            time.sleep(0.05)
        exported = json.loads(downloaded.read_text())
        assert exported["submitted_request"]["selected"] == ["Hakha-Lai"]
        assert len(exported["result"]["analysis"]["survivors"]) == 5
        checks.append("downloaded exact query and checked result")
        b.evaluate("document.querySelector('.candidate summary').click()")
        b.wait("document.querySelector('.candidate .history-details')")
        b.evaluate(
            "document.querySelector('.candidate .history-details summary').click()"
        )
        b.wait("document.querySelector('.candidate .derivation')")
        check(
            "tone derivation displays actual rules",
            "document.querySelector('.candidate .derivation').innerText.includes('Hakha-Lai-tone-')",
        )
        b.evaluate("document.querySelector('.candidate summary').click()")
        b.screenshot(directory / "desktop.png")
        b.evaluate(
            "document.querySelector('input[name=observation][value=Mizo]').click()"
        )
        check(
            "changed observations invalidate result and export",
            "state.result===null && document.getElementById('export').disabled",
        )
        run()
        check(
            "Mizo removes merger ambiguity but retains model identity",
            "state.result.result.analysis.survivors.length===2 && document.querySelectorAll('.candidate').length===1",
        )
        # Hold a real response until after the user changes a constraint. Older
        # work must neither replace the new query nor leave its button disabled.
        b.evaluate(
            "window.originalFetch=window.fetch;window.fetch=async (...args)=>{const response=await window.originalFetch(...args);if(args[0]==='/api/run') await new Promise(resolve=>window.releaseRun=resolve);return response};window.pendingRun=runEvidence();void 0"
        )
        b.wait("typeof window.releaseRun==='function'")
        b.evaluate(
            "document.querySelector('input[name=observation][value=Mara]').click();window.releaseRun();window.fetch=window.originalFetch"
        )
        b.wait("document.getElementById('results').getAttribute('aria-busy')==='false'")
        # Await the superseded request itself, rather than assuming a delay.
        b.evaluate("window.pendingRun")
        check(
            "changed constraints reject an in-flight result and remain runnable",
            "state.result===null && !document.getElementById('run').disabled && document.getElementById('export').disabled",
        )
        b.evaluate(
            "document.querySelector('input[name=observation][value=Mara]').click()"
        )
        b.evaluate(
            "document.querySelector('input[name=hypothesis][value=table-166-Hakha-2]').click()"
        )
        run()
        check(
            "whole hypothesis selection",
            "state.result.result.analysis.survivors.length===1 && state.result.result.input_request.analyses.length===1",
        )
        case("conflicts")
        run()
        check(
            "both minimal conflicts shown",
            "document.querySelectorAll('.conflict-list li').length===2",
        )
        b.evaluate(
            "document.getElementById('subset-budget').value=0;document.getElementById('subset-budget').dispatchEvent(new Event('change'))"
        )
        run()
        check(
            "budget exhaustion never displayed as complete",
            "state.result.result.complete===false && document.querySelector('.source-note.incomplete')!==null && document.querySelector('.completion').textContent.includes('All allowed forms')",
        )
        b.evaluate(
            "document.getElementById('subset-budget').value=4096;document.querySelector('input[name=observation][value=B]').click()"
        )
        run()
        check(
            "withholding conflicting observation restores p",
            "state.result.result.analysis.survivors.length===1 && document.querySelector('.proto').textContent==='*p'",
        )
        case("affixes")
        run()
        b.evaluate("document.querySelector('.candidate summary').click()")
        b.wait("document.querySelector('.candidate .history-details')")
        b.evaluate(
            "document.querySelector('.candidate .history-details summary').click()"
        )
        b.wait("document.querySelector('.candidate .derivation')")
        check(
            "linked affixes and stem-conditioned tone displayed",
            "document.getElementById('results').innerText.includes('n+pe+s') && document.getElementById('results').innerText.includes('conditioned on stem')",
        )
        # Keyboard tab activation and focus must agree with ARIA state.
        b.evaluate("document.getElementById('tab-evidence').focus()")
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
            "keyboard tabs switch panel and focus",
            "document.activeElement.id==='tab-chronology' && !document.getElementById('panel-chronology').hidden && document.getElementById('panel-evidence').hidden",
        )
        b.evaluate("document.getElementById('run-chronology').click()")
        b.wait("state.chronologyResult!==null")
        check(
            "all six chronology orders computed; one fits",
            "state.chronologyResult.result.orders.length===6 && state.chronologyResult.result.orders.filter(o=>o.agrees_with_observations).length===1",
        )
        b.evaluate(
            "document.querySelectorAll('input[name=precedence]')[0].click();document.querySelectorAll('input[name=precedence]')[2].click();document.getElementById('run-chronology').click()"
        )
        b.wait("state.chronologyResult!==null")
        check(
            "precedence cycle has explicit explanation",
            "state.chronologyResult.result.cyclic && document.getElementById('chronology-results').innerText.includes('cycle')",
        )
        b.evaluate("document.getElementById('tab-materials').click()")
        b.wait("document.querySelectorAll('.material-table tbody tr').length===25")
        check(
            "source catalogue exposes all IE-CoR form rows",
            "document.getElementById('material-status').textContent.includes('25,731')",
        )
        b.evaluate("document.getElementById('next').click()")
        b.wait(
            "document.getElementById('material-status').textContent.includes('26–50')"
        )
        check(
            "source pagination advances without truncating catalogue", "state.page===1"
        )
        b.evaluate(
            "document.getElementById('material-query').value='water';document.getElementById('material-form').requestSubmit()"
        )
        b.wait(
            "document.getElementById('material-results').getAttribute('aria-busy')==='false'"
        )
        check(
            "source search and original row inspection",
            "document.querySelector('.source-record pre').textContent.includes('source_row') && state.materialQuery.q==='water'",
        )
        b.evaluate("document.getElementById('tab-evidence').click()")
        case("conflicts")
        b.evaluate(
            "document.getElementById('subset-budget').value=4096;document.getElementById('subset-budget').dispatchEvent(new Event('change'));document.getElementById('observations-none').click();document.getElementById('max-length').value=2;document.getElementById('max-length').dispatchEvent(new Event('input'))"
        )
        run()
        check(
            "editable word bounds enumerate every short sequence in Lean",
            "state.result.result.histories.length===7 && document.querySelectorAll('.candidate').length===7 && state.result.result.input_request.max_length===2",
        )
        b.evaluate("document.querySelector('input[name=segment][value=b]').click()")
        run()
        check(
            "segment constraint narrows the actual Lean search space",
            "state.result.result.histories.length===3 && state.result.result.input_request.proto_inventory.join('')==='p' && document.querySelectorAll('.candidate').length===3",
        )
        b.evaluate("document.getElementById('reset-constraints').click()")
        check(
            "reset restores observations and original bounds",
            "chosen('observation').length===3 && chosen('segment').length===2 && document.getElementById('max-length').value==='1' && state.result===null",
        )
        run()
        b.evaluate(
            "[...document.querySelectorAll('.conflict-list button')].find(x=>x.textContent==='Uncheck B').click()"
        )
        check(
            "conflict explanation can relax a constraint explicitly",
            "!chosen('observation').includes('B') && state.result===null && document.getElementById('export').disabled",
        )
        run()
        check(
            "relaxing the conflict yields the complete allowed form",
            "document.querySelectorAll('.candidate').length===1 && state.result.result.analysis.survivors.length===1",
        )
        b.evaluate(
            "document.getElementById('max-length').value=10;document.getElementById('max-length').dispatchEvent(new Event('input'))"
        )
        run()
        check(
            "excessive bounds report an error without claiming completeness",
            "state.result===null && document.getElementById('run-status').textContent.includes('1,024') && !document.querySelector('.completion')",
        )
        b.evaluate(
            "document.getElementById('collection').value='pie';document.getElementById('collection').dispatchEvent(new Event('change'));document.getElementById('case-search').value='dog';document.getElementById('case-search').dispatchEvent(new Event('input'))"
        )
        b.wait(
            "state.current?.dataset==='pie' && !document.getElementById('run').disabled"
        )
        check(
            "word search exposes source meanings and language names",
            "document.getElementById('case').options.length>0 && [...document.getElementById('case').options].every(o=>o.textContent.toLowerCase().includes('dog')) && !document.querySelector('#observation-options b').textContent.includes('iecor-form')",
        )
        b.evaluate(
            "document.getElementById('case-search').value='no-match-zzzz';document.getElementById('case-search').dispatchEvent(new Event('input'))"
        )
        check(
            "empty search disables enumeration and clears the active case",
            "state.current===null && document.getElementById('run').disabled",
        )
        b.evaluate(
            "document.getElementById('collection').value='worked';document.getElementById('collection').dispatchEvent(new Event('change'))"
        )
        b.wait(
            "state.current?.key==='tones' && !document.getElementById('run').disabled"
        )
        run()
        for width in [320, 390, 768, 1440]:
            b.size(width)
            check(
                f"no page overflow at {width}px",
                "document.documentElement.scrollWidth<=window.innerWidth",
            )
        for theme in ["dusk", "night", "day"]:
            b.evaluate(
                f"document.querySelector('input[name=theme][value={theme}]').click()"
            )
            check(
                theme + " appearance persists",
                f"document.documentElement.dataset.time==='{theme}' && localStorage.getItem('comparative-theme')==='{theme}'",
            )
        b.call(
            "Emulation.setEmulatedMedia",
            dict(features=[dict(name="prefers-reduced-motion", value="reduce")]),
        )
        check(
            "reduced motion respected",
            "matchMedia('(prefers-reduced-motion:reduce)').matches && getComputedStyle(document.querySelector('.room')).animationName==='none'",
        )
        b.evaluate("document.querySelector('input[name=theme][value=day]').click()")
        case("tones")
        run()
        b.size(390, 900)
        b.screenshot(directory / "mobile.png")
        spec = (ROOT / "data/research/stem-paradigm.json").read_text()
        b.evaluate(
            "importFile(new File(["
            + json.dumps(spec)
            + "], 'stems.json', {type:'application/json'}),'paradigm')"
        )
        run()
        check(
            "imported specification executes and replaces visible case",
            "state.current.imported && document.getElementById('case').value==='vanbik-attach-stems' && state.result.result.analysis.survivors.length===1",
        )
        b.evaluate(
            "document.querySelectorAll('input[name=hypothesis]').forEach(x=>{x.checked=false;x.dispatchEvent(new Event('change'))})"
        )
        run()
        check(
            "no hypothesis is an input error, not an empty reconstruction",
            "document.getElementById('run-status').textContent.includes('at least one') && state.result===null",
        )
        errors = [e for e in b.events if e.get("method") == "Runtime.exceptionThrown"]
        assert not errors, errors
        checks.append("no uncaught browser exceptions")
        paths = [
            "web/index.html",
            "web/app.js",
            "web/style.css",
            "scripts/serve_ui.py",
            "scripts/research.py",
            "scripts/verify_ui.py",
            "scripts/workbench_labels.py",
            "scripts/verify_theme.py",
            "data/pie/corpus.json",
            "data/pie/latin-control-frozen.json",
            "data/kuki-chin/corpus.json",
        ] + [
            str(p.relative_to(ROOT))
            for p in sorted((ROOT / "web/vendor").rglob("*"))
            if p.is_file()
        ]
        report = dict(
            passed=True,
            checks=checks,
            browser=b.call("Browser.getVersion"),
            viewport_widths=[320, 390, 768, 1440],
            screenshots=["desktop.png", "mobile.png"],
            input_hashes={
                p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths
            },
            note="Executed in a real Chrome browser against local HTTP endpoints and compiled Lean binaries. Screenshots require visual review; these checks do not certify complete accessibility.",
        )
        (directory / "verification.json").write_bytes(encoded(report))
        print(
            f"{len(checks)} browser checks passed; screenshots and report: {directory}"
        )
    finally:
        b.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url")
    p.add_argument("--chrome")
    p.add_argument("--output", type=Path, default=ROOT / "reports/ui")
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
