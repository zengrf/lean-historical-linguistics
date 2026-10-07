"""Run M7 examples and capture their real browser results for a performance review."""

import argparse
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import threading
import time

from build_pie_corpus import ROOT, encoded
from lexicon import constrain, page, reconstruct
from m7_solver import IncompleteSearch
from serve_ui import make_server
from verify_ui import Browser


def request(key):
    return json.loads((ROOT / "data/lexicon" / (key + ".json")).read_text())


def measure(spec, *, repetitions=3, **options):
    runs = []
    result = None
    for _ in range(repetitions):
        start = time.perf_counter()
        try:
            result = reconstruct(spec, **options)
            outcome = dict(complete=True, summary=result["summary"])
        except IncompleteSearch as error:
            outcome = dict(complete=False, reason=str(error))
        runs.append(dict(seconds=time.perf_counter() - start, **outcome))
    return (
        dict(
            runs=runs,
            median_seconds=statistics.median(run["seconds"] for run in runs),
            options=options,
        ),
        result,
    )


def capture(url, directory):
    b = Browser()
    records = {}
    try:
        b.size(1440, 1260)
        b.call("Page.navigate", dict(url=url))
        b.wait(
            "document.getElementById('lex-status')?.textContent.startsWith('Ready.')"
        )
        b.wait("document.fonts.status==='loaded'")
        for key in ["merger", "pie", "kuki"]:
            b.evaluate(
                "document.getElementById('lex-example').value="
                + json.dumps(key)
                + ";document.getElementById('lex-example').dispatchEvent(new Event('change'))"
            )
            b.wait(
                "!document.getElementById('lex-run').disabled && document.getElementById('lex-status').textContent.startsWith('Ready.')"
            )
            b.evaluate("document.getElementById('lex-run').click()")
            b.wait(
                "!document.getElementById('lex-run').disabled && document.getElementById('lex-status').textContent.startsWith('Complete.')",
                timeout=90,
            )
            b.wait(
                "!document.getElementById('lex-go').disabled && document.querySelector('.lex-derivation, .lex-whole')"
            )
            view = "lexicons" if key == "merger" else "words"
            b.evaluate(
                "document.getElementById('lex-view').value="
                + json.dumps(view)
                + ";document.getElementById('lex-view').dispatchEvent(new Event('change'))"
            )
            b.wait(
                "!document.getElementById('lex-go').disabled && document.querySelector('.lex-derivation, .lex-whole')"
            )
            if key == "merger":
                b.evaluate(
                    "document.getElementById('lex-offset').value='3';document.getElementById('lex-go').click()"
                )
                b.wait(
                    "!document.getElementById('lex-go').disabled && document.querySelector('.lex-whole h4')?.textContent.endsWith('lexicon 3')"
                )
            else:
                b.evaluate(
                    "document.querySelectorAll('.lex-derivation').forEach(d=>d.open=true)"
                )
            # Collapse the input using the existing control, then capture the
            # workbench region. No stylesheet or displayed result is changed.
            b.evaluate(
                "document.getElementById('lex-table-details').open=false;document.activeElement?.blur()"
            )
            b.evaluate(
                "document.querySelector('#panel-lexicon .workbench').scrollIntoView({block:'start'})"
            )
            b.evaluate(
                "new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))"
            )
            raw = b.call(
                "Page.captureScreenshot",
                dict(format="png", captureBeyondViewport=False),
            )
            (directory / (key + ".png")).write_bytes(base64.b64decode(raw["data"]))
            records[key] = b.evaluate(
                "({total:document.getElementById('lex-total').textContent,scope:document.getElementById('lex-scope').textContent,candidates:document.getElementById('lex-candidates').innerText})"
            )
        errors = [
            event
            for event in b.events
            if event.get("method") == "Runtime.exceptionThrown"
        ]
        assert not errors, errors
        return records
    finally:
        b.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/m7-examples")
    parser.add_argument("--lean-version", required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = dict(
        code_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        timing_scope="Native request validation, graph generation, native completeness checking and independent count comparison; word-page derivations are outside these small-case timings.",
        examples={},
        contextual_scaling={},
    )
    for key in ["merger", "pie", "kuki", "conflict", "deletion", "contextual"]:
        measured, result = measure(request(key))
        measured["first_pages"] = {
            model["analysis_id"]: page(result, model["analysis_id"], limit=4)
            for model in result["summary"]["models"]
            if model["lexicon_count"] != "0"
        }
        report["examples"][key] = measured
        print(
            key,
            measured["median_seconds"],
            result["summary"]["lexicon_count"],
            flush=True,
        )
    narrowed = constrain(request("merger"), analyses=["mergers"])
    narrowed["proto_inventory"] = ["p", "t", "a"]
    measured, result = measure(narrowed)
    measured["request"] = narrowed
    measured["first_pages"] = {"mergers": page(result, "mergers", limit=4)}
    report["examples"]["merger_narrowed"] = measured
    for bound in [3, 6, 8, 12]:
        spec = deepcopy(request("contextual"))
        spec["max_length"] = bound
        measured, _ = measure(spec, repetitions=1, time_limit=5)
        measured["possible_words_before_reflex_constraints"] = sum(
            3**n for n in range(bound + 1)
        )
        report["contextual_scaling"][str(bound)] = measured
        print(
            "contextual",
            bound,
            measured["runs"][0]["complete"],
            measured["median_seconds"],
            flush=True,
        )
    server = make_server(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        report["browser"] = capture(
            f"http://127.0.0.1:{server.server_port}", args.output
        )
    finally:
        server.shutdown()
        server.server_close()
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/benchmark_m7.py"),
            "--lean-version",
            args.lean_version,
            "--output",
            str(args.output / "benchmark.json"),
        ],
        cwd=ROOT,
        check=True,
    )
    sources = [
        "scripts/capture_m7_examples.py",
        "scripts/lexicon.py",
        "scripts/m7_solver.py",
        "web/lexicon.js",
    ]
    sources += [
        "data/lexicon/" + key + ".json"
        for key in [
            "merger",
            "pie",
            "kuki",
            "conflict",
            "deletion",
            "contextual",
            "scaling",
        ]
    ]
    report["input_hashes"] = {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in sources
    }
    (args.output / "examples.json").write_bytes(encoded(report))
    print("Wrote measurements and actual browser screenshots to", args.output)


if __name__ == "__main__":
    main()
