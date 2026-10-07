"""Local research interface. Every reconstruction request runs the Lean binaries.

Start after `lake build`: python scripts/serve_ui.py --port 8765.
The server binds only to loopback and serves only the web directory and public PDFs.
"""

import argparse
from copy import deepcopy
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import threading
from urllib.parse import parse_qs, unquote, urlsplit

from build_pie_corpus import ROOT, encoded
from explore_reconstructions import catalogue, SOURCES, select_pool, strict_read, VOICE
from materials import search
from workbench_labels import analysis_label, axis_label, case_labels
import lexicon_api
from m7_solver import IncompleteSearch as LexiconIncomplete
from research import (
    EXAMPLES,
    IncompleteSearch,
    analyze_pool,
    analyze_bounded,
    analyze_paradigm,
    explore_chronology,
)

WEB = ROOT / "web"
EXAMPLE_INFO = {
    "tones": (
        "paradigm",
        "Smooth-syllable tones",
        "VanBik · Kuki-Chin",
        EXAMPLES / "tone-paradigm.json",
    ),
    "stems": (
        "paradigm",
        "ATTACH · linked stems",
        "VanBik · Kuki-Chin",
        EXAMPLES / "stem-paradigm.json",
    ),
    "affixes": (
        "paradigm",
        "Affixes, alternation & tone",
        "Synthetic control",
        EXAMPLES / "affix-control.json",
    ),
    "conflicts": (
        "bounded",
        "Conflicting observations",
        "Synthetic control",
        EXAMPLES / "evidence-control.json",
    ),
    "voice": (
        "bounded",
        "Two voice analyses",
        "Sino-Tibetan · joint alternatives",
        VOICE,
    ),
    "chronology": (
        "chronology",
        "Grimm, Verner & stress",
        "Indo-European · restricted control",
        EXAMPLES / "germanic-chronology.json",
    ),
}
FAMILIES = {
    "pie": "Indo-European",
    "latin": "Latin control",
    "kuki-chin": "Kuki-Chin",
    "tibetan-merger": "Tibetan merger",
}
JOBS = threading.BoundedSemaphore(2)


@lru_cache(maxsize=1)
def public_catalogue():
    return dict(
        examples=[
            dict(key=k, kind=v[0], title=v[1], subtitle=v[2])
            for k, v in EXAMPLE_INFO.items()
        ],
        pools=[
            dict(
                id=d,
                label=label,
                queries=[
                    dict(q, title=case_labels(d, q["case"])["title"])
                    for q in catalogue(d)
                ],
            )
            for d, label in FAMILIES.items()
        ],
        coverage=strict_read(ROOT / "data/materials/coverage.json"),
        limits=dict(histories=1024, axes=16, selected_axes=12, chronology_blocks=6),
        source_readings=strict_read(EXAMPLES / "source-readings.json"),
    )


def describe(request):
    key = request.get("key")
    if key in EXAMPLE_INFO:
        kind, title, subtitle, path = EXAMPLE_INFO[key]
        data = strict_read(path)
        if kind == "chronology":
            return dict(
                kind=kind,
                key=key,
                title=title,
                subtitle=subtitle,
                request=data,
                description=data["description"],
                hypotheses=[],
                axes=[],
            )
        a = data["analyses"][0]
        hypotheses = [
            dict(
                id=a["id"], label=analysis_label(a["id"]), description=a["description"]
            )
            for a in data["analyses"]
        ]
        if kind == "paradigm":
            axes = [
                dict(
                    id=c["id"],
                    label=axis_label(c["id"]),
                    expected=c["expected"],
                    source_ref=c["source_ref"],
                    observed=all(
                        x["cells"][i]["expected"] is not None for x in data["analyses"]
                    ),
                )
                for i, c in enumerate(a["cells"])
            ]
        else:
            axes = [
                dict(
                    id=o["doculect_id"],
                    label=axis_label(o["doculect_id"]),
                    expected=o["form"],
                    source_ref=o["source_ref"],
                    observed=all(
                        x["observations"][i]["form"] is not None
                        for x in data["analyses"]
                    ),
                )
                for i, o in enumerate(a["observations"])
            ]
        return dict(
            kind=kind,
            key=key,
            title=title,
            subtitle=subtitle,
            request=data,
            axes=axes,
            hypotheses=hypotheses,
            description=data.get("source_scope", data.get("description", "")),
            defaults=(
                ["Hakha-Lai"]
                if key == "tones"
                else [a["id"] for a in axes if a["observed"]]
            ),
        )
    if key is not None:
        raise ValueError("Unknown example")
    dataset, case, scope = (
        request["dataset"],
        request["case"],
        request.get("scope", "all-groups"),
    )
    data = select_pool(dataset, case, scope=scope)
    labels = case_labels(dataset, case)
    batch = data.get("batch", data)
    queries = [
        q for q in catalogue(dataset) if q["case"] == case and q["scope"] == scope
    ]
    axes = [
        dict(
            id=b["doculect_id"],
            label=labels["languages"].get(
                b["doculect_id"], axis_label(b["doculect_id"])
            ),
            expected=b["expected"],
            observed=True,
            source_ref=f"{dataset}:{case}:{b['doculect_id']}",
        )
        for b in batch["inverse"][0]["branches"]
    ]
    return dict(
        kind="pool",
        dataset=dataset,
        case=case,
        scope=scope,
        title=labels["title"],
        subtitle=FAMILIES[dataset],
        request=data,
        hypotheses=[
            dict(id=q["hypothesis"], label=analysis_label(q["hypothesis"]))
            for q in queries
        ],
        axes=axes,
        defaults=[a["id"] for a in axes],
        description="Enumerate the declared source pool under selected whole models. Identity and correspondence models are experimental baselines; this is not an unrestricted reconstruction of a language family.",
    )


def constrained_bounds(request, bounds, hypotheses):
    """Change only the finite proto-word space; branch models remain intact."""
    if not isinstance(bounds, dict) or set(bounds) != {"proto_inventory", "max_length"}:
        raise ValueError("Provide allowed segments and a maximum length")
    inventory, length = bounds["proto_inventory"], bounds["max_length"]
    if (
        not isinstance(inventory, list)
        or not inventory
        or not all(isinstance(x, str) for x in inventory)
        or len(set(inventory)) != len(inventory)
        or set(inventory) - set(request["proto_inventory"])
    ):
        raise ValueError("Select at least one segment from this model's inventory")
    if type(length) is not int or not 0 <= length <= 16:
        raise ValueError("Maximum length must be an integer from 0 to 16")
    alphabet = len(inventory) + int(request["allow_morphemes"])
    size = sum(alphabet**i for i in range(length + 1))
    histories = size * (
        len(hypotheses) if hypotheses is not None else len(request["analyses"])
    )
    if histories > 1024:
        raise ValueError(
            f"These bounds require {histories:,} form–analysis combinations; reduce them to at most 1,024"
        )
    spec = deepcopy(request)
    spec.update(
        proto_inventory=inventory,
        max_length=length,
        candidate_budget=max(request["candidate_budget"], histories),
    )
    return spec


def run_request(body):
    allowed = {
        "key",
        "kind",
        "dataset",
        "case",
        "scope",
        "request",
        "hypotheses",
        "selected",
        "subset_budget",
        "constraints",
        "choices",
        "bounds",
    }
    if not isinstance(body, dict) or set(body) - allowed:
        raise ValueError("Unknown request fields")
    kind = body.get("kind")
    if kind not in {"pool", "bounded", "paradigm", "chronology"}:
        raise ValueError("Unknown analysis kind")
    if "bounds" in body and kind != "bounded":
        raise ValueError("Word bounds apply only to bounded reconstruction")
    if kind != "chronology" and "hypotheses" in body and not body["hypotheses"]:
        raise ValueError("Select at least one allowed analysis")
    kwargs = dict(
        selected=body.get("selected"), subset_budget=body.get("subset_budget", 4096)
    )
    for key in ["selected", "hypotheses", "choices"]:
        if key in body and (
            not isinstance(body[key], list)
            or not all(isinstance(x, str) for x in body[key])
        ):
            raise ValueError(key + " must be an array of identifiers")
    if kind == "pool":
        if body.get("request") is not None:
            raise ValueError(
                "Use a registered pool, or import a bounded/paradigm specification"
            )
        return analyze_pool(
            body["dataset"],
            body["case"],
            body.get("hypotheses", ()),
            body.get("scope", "all-groups"),
            **kwargs,
        )
    if "request" in body:
        request = body["request"]
    else:
        info = EXAMPLE_INFO[body["key"]]
        if info[0] != kind:
            raise ValueError("Example and analysis kind differ")
        request = strict_read(info[3])
    if kind == "chronology":
        return explore_chronology(request, body.get("constraints"))
    if kind == "paradigm":
        return analyze_paradigm(request, body.get("hypotheses", ()), **kwargs)
    if "bounds" in body:
        request = constrained_bounds(request, body["bounds"], body.get("hypotheses"))
    return analyze_bounded(
        request, body.get("hypotheses", ()), body.get("choices", ()), **kwargs
    )


@lru_cache(maxsize=8)
def material_records(dataset, query, language, concept, set_id):
    if dataset not in {"iecor", "sagartst", "hillburmish", "vanbik2009"}:
        raise ValueError("Unknown source")
    if dataset == "hillburmish" and set_id:
        raise ValueError(
            "Burmish cognacy is embedded in source columns; no separate cognate-set table"
        )
    return list(
        search(dataset, query, language or None, concept or None, set_id or None)
    )


def browse(query):
    records = material_records(
        query.get("dataset", "iecor"),
        query.get("q", ""),
        query.get("language", ""),
        query.get("concept", ""),
        query.get("set", ""),
    )
    offset = int(query.get("offset", 0))
    limit = int(query.get("limit", 25))
    if offset < 0 or not 1 <= limit <= 100:
        raise ValueError("Invalid page (1–100 records)")
    page = records[offset : offset + limit]
    return dict(
        total=len(records),
        offset=offset,
        returned=len(page),
        has_more=offset + len(page) < len(records),
        records=page,
    )


def strict_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("Duplicate JSON key: " + key)
            out[key] = value
        return out

    def constant(value):
        raise ValueError("Invalid JSON constant: " + value)

    return json.loads(
        raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant
    )


class Handler(BaseHTTPRequestHandler):
    server_version = "ComparativeWorkbench/1.0"

    def trusted(self):
        hosts = {
            f"127.0.0.1:{self.server.server_port}",
            f"localhost:{self.server.server_port}",
        }
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        return host in hosts and (
            not origin or origin in {"http://" + h for h in hosts}
        )

    def send(self, status, data, content_type="application/json; charset=utf-8"):
        raw = encoded(data) if isinstance(data, (dict, list)) else data
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'self'; font-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        )
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if not self.trusted():
            return self.send(403, dict(error="Use the local server origin"))
        url = urlsplit(self.path)
        path = unquote(url.path)
        query = {k: v[-1] for k, v in parse_qs(url.query).items()}
        try:
            if path == "/api/catalogue":
                return self.send(200, public_catalogue())
            if path == "/api/lexicon/example":
                return self.send(200, lexicon_api.example(query.get("key", "merger")))
            if path == "/api/case":
                return self.send(200, describe(query))
            if path == "/api/materials":
                return self.send(200, browse(query))
            if path.startswith("/sources/"):
                name = path.removeprefix("/sources/")
                if Path(name).name != name or not name.endswith(".pdf"):
                    raise ValueError("Unknown public source")
                file = ROOT / "library/open" / name
            else:
                file = (
                    WEB / ("index.html" if path == "/" else path.lstrip("/"))
                ).resolve()
                if not file.is_relative_to(WEB.resolve()):
                    raise ValueError("Unknown resource")
            if not file.is_file():
                return self.send(404, dict(error="Resource not found"))
            return self.send(
                200,
                file.read_bytes(),
                mimetypes.guess_type(file.name)[0] or "application/octet-stream",
            )
        except (ValueError, KeyError, TypeError, UnicodeError) as error:
            self.send(400, dict(error=str(error), complete=False))

    def do_POST(self):
        if not self.trusted():
            return self.send(403, dict(error="Use the local server origin"))
        if self.path not in {
            "/api/run",
            "/api/import",
            "/api/lexicon/import",
            "/api/lexicon/run",
            "/api/lexicon/page",
            "/api/lexicon/export",
            "/api/lexicon/table",
        }:
            return self.send(404, dict(error="Unknown endpoint"))
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.send(415, dict(error="Send application/json"))
        acquired = False
        try:
            size = int(self.headers.get("Content-Length", "0"))
            body_limit = (
                16_000_000 if self.path.startswith("/api/lexicon/") else 2_000_000
            )
            if not 0 < size <= body_limit:
                raise ValueError(f"Request must be 1–{body_limit} bytes")
            body = strict_json(self.rfile.read(size))
            if self.path in {"/api/import", "/api/lexicon/import"}:
                if (
                    not isinstance(body, dict)
                    or set(body) != {"text"}
                    or not isinstance(body["text"], str)
                ):
                    raise ValueError("Provide the unmodified JSON text")
                imported = strict_json(body["text"].encode("utf-8"))
                if not isinstance(imported, dict):
                    raise ValueError("Specification must be a JSON object")
                return self.send(200, dict(request=imported))
            acquired = JOBS.acquire(blocking=False)
            if not acquired:
                return self.send(
                    429,
                    dict(
                        error="Two analyses are already running; try again shortly",
                        complete=False,
                    ),
                )
            if self.path.startswith("/api/lexicon/"):
                self.send(200, lexicon_api.execute(self.path.rsplit("/", 1)[-1], body))
            else:
                result = run_request(body)
                self.send(200, dict(submitted_request=body, result=result))
        except (IncompleteSearch, LexiconIncomplete) as error:
            self.send(200, dict(status="incomplete", complete=False, error=str(error)))
        except (
            ValueError,
            KeyError,
            TypeError,
            IndexError,
            AttributeError,
            UnicodeError,
        ) as error:
            self.send(400, dict(status="error", complete=False, error=str(error)))
        except OSError as error:
            self.send(
                503,
                dict(
                    status="unavailable",
                    complete=False,
                    error="Build the Lean executables before running an analysis. "
                    + str(error),
                ),
            )
        finally:
            if acquired:
                JOBS.release()

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)


def make_server(port=8765):
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args()
    server = make_server(args.port)
    print(f"Comparative workbench: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
