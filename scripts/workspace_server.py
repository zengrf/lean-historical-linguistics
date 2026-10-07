"""Authenticated loopback research application served by Waitress.

Projects stay in a private local workspace, outside the public repository.
Open the launch link printed by this command. It establishes a private browser
session and removes the credential from the address bar by redirecting.
"""

import argparse
import base64
from http.cookies import SimpleCookie
import hashlib
import hmac
import json
import logging
import mimetypes
from pathlib import Path
import secrets
import sys
import threading
import tempfile
import signal
import csv
import zipfile
from urllib.parse import parse_qs, urlsplit
import webbrowser

from build_pie_corpus import ROOT, encoded
from lexicon import BIN, native, to_tsv, read_tsv
from lexicon_api import example, EXAMPLES
from linguist_notation import parse_classes, compile_branch, parse_shapes, segmentations
from serve_ui import strict_json, public_catalogue, describe, browse, run_request, JOBS
from workspace_store import Store, Conflict, Missing, new_document, validate_document
from workspace_jobs import Jobs
from workspace_exchange import (
    import_edictor,
    export_edictor,
    cldf_zip,
    import_cldf_zip,
    tei_apparatus,
    correspondences,
)
from workspace_backup import backup, workspace_lock
from m7_solver import IncompleteSearch
from workspace_engine import readiness

LOG = logging.getLogger("comparative.workspace")
WEB = ROOT / "web"


def require(body, keys):
    if not isinstance(body, dict) or set(body) != set(keys):
        raise ValueError("Expected fields: " + ", ".join(keys))


class Application:
    def __init__(self, directory):
        self.store = Store(directory)
        self.jobs = Jobs(self.store)
        self.launch_token = secrets.token_urlsafe(32)
        self.csrf = secrets.token_urlsafe(32)
        self.port = None
        self.synchronous = threading.BoundedSemaphore(2)

    def configure(self, port):
        self.port = int(port)
        self.cookie_name = f"comparative_{self.port}"
        self.hosts = {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}
        self.origins = {"http://" + host for host in self.hosts}
        self.launch_url = f"http://127.0.0.1:{self.port}/?access={self.launch_token}"

    def __call__(self, env, start_response):
        request_id = secrets.token_hex(6)
        status, mime, extra = 200, "application/json; charset=utf-8", []
        try:
            if env.get("HTTP_HOST") not in self.hosts:
                raise PermissionError("Use the application's local launch address")
            path = env.get("PATH_INFO", "/")
            parsed = parse_qs(env.get("QUERY_STRING", ""), keep_blank_values=True)
            if any(len(values) != 1 for values in parsed.values()):
                raise ValueError("Duplicate query parameter")
            query = {key: values[0] for key, values in parsed.items()}
            cookie = SimpleCookie()
            try:
                cookie.load(env.get("HTTP_COOKIE", ""))
            except Exception:
                raise PermissionError("Invalid browser session")
            credential = cookie.get(self.cookie_name)
            authenticated = credential is not None and hmac.compare_digest(
                credential.value, self.launch_token
            )
            if (
                path == "/"
                and env["REQUEST_METHOD"] == "GET"
                and hmac.compare_digest(query.get("access", ""), self.launch_token)
            ):
                status, result, mime = 303, b"", "text/plain"
                extra = [
                    ("Location", "/"),
                    (
                        "Set-Cookie",
                        f"{self.cookie_name}={self.launch_token}; Path=/; HttpOnly; SameSite=Strict",
                    ),
                ]
            else:
                if not authenticated:
                    raise PermissionError(
                        "Open the private launch link printed by workspace_server.py on this computer"
                    )
                if env.get("HTTP_SEC_FETCH_SITE") == "cross-site":
                    raise PermissionError(
                        "Cross-site workspace requests are not allowed"
                    )
                method = env["REQUEST_METHOD"]
                if method == "POST":
                    if env.get("HTTP_ORIGIN") not in self.origins or (
                        path.startswith("/api/workspace/")
                        and not hmac.compare_digest(
                            env.get("HTTP_X_WORKSPACE_TOKEN", ""), self.csrf
                        )
                    ):
                        raise PermissionError(
                            "The workspace session has changed; reload this page"
                        )
                    if env.get("CONTENT_TYPE", "").split(";")[0] != "application/json":
                        raise ValueError("Send application/json")
                    size = int(env.get("CONTENT_LENGTH") or 0)
                    if not 0 < size <= 16_000_000:
                        raise ValueError("Request must be 1–16000000 bytes")
                    body = strict_json(env["wsgi.input"].read(size))
                    result = self.post(path, body)
                elif method == "GET":
                    result, mime, extra = self.get(path, query)
                else:
                    status, result = 405, dict(error="Use GET or POST")
        except PermissionError as error:
            status, result = 403, dict(error=str(error))
        except Conflict as error:
            status, result = 409, dict(error=str(error))
        except Missing as error:
            status, result = 404, dict(error=str(error))
        except IncompleteSearch as error:
            status, result = 400, dict(
                error=str(error), complete=False, status="incomplete"
            )
        except (
            ValueError,
            TypeError,
            KeyError,
            IndexError,
            UnicodeError,
            csv.Error,
            zipfile.BadZipFile,
        ) as error:
            status, result = 400, dict(error=str(error))
        except OSError:
            LOG.exception("Local I/O failure, request %s", request_id)
            status, result = 503, dict(
                error="A required local file or executable is unavailable. Check workspace diagnostics."
            )
        except Exception:
            LOG.exception("Unexpected error, request %s", request_id)
            status, result = 500, dict(
                error=f"The operation failed. Your saved revisions are retained. Diagnostic reference: {request_id}"
            )
        if not isinstance(result, bytes):
            result = encoded(result)
            mime = "application/json; charset=utf-8"
        phrases = {
            200: "OK",
            303: "See Other",
            400: "Bad Request",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            409: "Conflict",
            500: "Internal Server Error",
            503: "Service Unavailable",
        }
        headers = [
            ("Content-Type", mime),
            ("Content-Length", str(len(result))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
            ("Referrer-Policy", "no-referrer"),
            ("X-Request-ID", request_id),
            (
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
            ),
        ] + extra
        start_response(f"{status} {phrases[status]}", headers)
        return [result]

    def get(self, path, query):
        result, mime, headers = None, "application/json; charset=utf-8", []
        if path == "/api/workspace/session":
            result = dict(
                token=self.csrf,
                examples=EXAMPLES,
                checker_ready=readiness()["ready"],
                workspace=str(self.store.directory),
                project_schema="1.0.0",
                deployment="private local research workspace",
            )
        elif path == "/api/workspace/projects":
            result = dict(projects=self.store.list_projects())
        elif path == "/api/workspace/project":
            result = self.store.get(
                query["id"], int(query["revision"]) if "revision" in query else None
            )
        elif path == "/api/workspace/history":
            result = dict(revisions=self.store.history(query["id"]))
        elif path == "/api/workspace/jobs":
            result = dict(jobs=self.store.jobs(query["id"]))
        elif path == "/api/workspace/job":
            result = self.store.job(query["id"])
        elif path == "/api/workspace/result":
            result = self.jobs.describe(query["id"])
        elif path == "/api/workspace/evaluation":
            result = self.jobs.evaluation(query["id"])
        elif path == "/api/workspace/backup":
            if not self.synchronous.acquire(blocking=False):
                raise Conflict("Another export is in progress; try again shortly")
            try:
                with self.jobs.lock, tempfile.TemporaryDirectory(
                    prefix="comparative-download-"
                ) as directory:
                    file = backup(self.store, Path(directory) / "workspace.zip")
                    if file.stat().st_size > 64_000_000:
                        raise ValueError(
                            "This backup exceeds the 64 MB browser download limit. Close the application and use workspace_backup.py backup for a full-size backup."
                        )
                    result, mime = file.read_bytes(), "application/zip"
                    headers.append(
                        (
                            "Content-Disposition",
                            'attachment; filename="comparative-workspace.zip"',
                        )
                    )
            finally:
                self.synchronous.release()
        elif path == "/api/workspace/example":
            result = dict(
                document=new_document(example(query.get("key", "merger"))["request"])
            )
        elif path == "/api/workspace/export":
            kind = query.get("format", "project")
            if kind == "result":
                result = self.jobs.result(query["id"])
            else:
                project = self.store.get(query["id"])
                document = project["document"]
                if kind == "project":
                    result = document
                elif kind == "edictor":
                    result, mime = (
                        export_edictor(document).encode("utf-8"),
                        "text/tab-separated-values; charset=utf-8",
                    )
                elif kind == "wide":
                    result, mime = (
                        to_tsv(document["request"]).encode("utf-8"),
                        "text/tab-separated-values; charset=utf-8",
                    )
                elif kind == "cldf":
                    result, mime = cldf_zip(document), "application/zip"
                elif kind == "tei":
                    result, mime = (
                        tei_apparatus(document),
                        "application/xml; charset=utf-8",
                    )
                else:
                    raise ValueError("Unknown export format")
            suffix = (
                "zip"
                if kind == "cldf"
                else (
                    "tsv"
                    if kind in {"wide", "edictor"}
                    else "xml" if kind == "tei" else "json"
                )
            )
            headers.append(
                (
                    "Content-Disposition",
                    f'attachment; filename="comparative-{kind}.{suffix}"',
                )
            )
        elif path == "/api/catalogue":
            result = public_catalogue()
        elif path == "/api/case":
            result = describe(query)
        elif path == "/api/materials":
            result = browse(query)
        elif path == "/api/lexicon/example":
            result = example(query.get("key", "merger"))
        else:
            if path.startswith("/sources/"):
                name = path.removeprefix("/sources/")
                if Path(name).name != name or not name.endswith(".pdf"):
                    raise Missing("Unknown public source")
                file = ROOT / "library/open" / name
            else:
                name = (
                    "workspace.html"
                    if path == "/"
                    else "index.html" if path == "/legacy" else path.lstrip("/")
                )
                file = (WEB / name).resolve()
                if not file.is_relative_to(WEB.resolve()):
                    raise Missing("Resource not found")
            if not file.is_file():
                raise Missing("Resource not found")
            result, mime = (
                file.read_bytes(),
                mimetypes.guess_type(file.name)[0] or "application/octet-stream",
            )
        return result, mime, headers

    def post(self, path, body):
        if path in {"/api/import", "/api/lexicon/import"}:
            require(body, ["text"])
            return dict(request=strict_json(body["text"].encode("utf-8")))
        if path == "/api/run" or path.startswith("/api/lexicon/"):
            if not JOBS.acquire(blocking=False):
                raise Conflict("Two additional analyses are running; try again shortly")
            try:
                if path == "/api/run":
                    return dict(submitted_request=body, result=run_request(body))
                import lexicon_api

                return lexicon_api.execute(path.rsplit("/", 1)[-1], body)
            finally:
                JOBS.release()
        if path == "/api/workspace/create":
            require(body, ["title", "document"])
            return self.store.create(body["title"], body["document"])
        if path == "/api/workspace/save":
            require(body, ["id", "revision", "title", "document", "message"])
            return self.store.save(
                body["id"],
                body["revision"],
                body["title"],
                body["document"],
                body["message"],
            )
        if path == "/api/workspace/restore":
            require(body, ["id", "revision", "restore_revision"])
            return self.store.restore(
                body["id"], body["revision"], body["restore_revision"]
            )
        if path == "/api/workspace/run":
            require(body, ["id", "revision", "settings"])
            return self.jobs.submit(body["id"], body["revision"], body["settings"])
        if path == "/api/workspace/cancel":
            require(body, ["id"])
            return self.jobs.cancel(body["id"])
        if path == "/api/workspace/page":
            require(body, ["id", "analysis_id", "entry_id", "offset", "limit"])
            if not self.synchronous.acquire(blocking=False):
                raise Conflict("Two result pages are being checked; try again shortly")
            try:
                return self.jobs.browse(
                    body["id"],
                    body["analysis_id"],
                    body["entry_id"],
                    body["offset"],
                    body["limit"],
                )
            finally:
                self.synchronous.release()
        if path == "/api/workspace/check":
            require(body, ["document"])
            validate_document(body["document"])
            return native("--validate", body["document"]["request"])
        if path == "/api/workspace/import":
            require(body, ["format", "text", "title", "source"])
            if body["format"] == "edictor":
                return import_edictor(body["text"], body["title"], body["source"])
            if body["format"] == "cldf":
                return import_cldf_zip(
                    base64.b64decode(body["text"], validate=True),
                    body["title"],
                    body["source"],
                )
            if body["format"] == "project":
                document = strict_json(body["text"].encode("utf-8"))
                validate_document(document)
                return dict(document=document, warnings=[])
            if body["format"] == "request":
                spec = strict_json(body["text"].encode("utf-8"))
                native("--validate", spec)
                return dict(document=new_document(spec), warnings=[])
            raise ValueError(
                "Choose project JSON, a reconstruction request, or an EDICTOR wordlist"
            )
        if path == "/api/workspace/correspondences":
            require(body, ["document"])
            validate_document(body["document"])
            return correspondences(body["document"])
        if path == "/api/workspace/notation":
            require(
                body,
                [
                    "request",
                    "analysis_id",
                    "language_id",
                    "rules",
                    "classes",
                    "direction",
                    "mode",
                ],
            )
            spec = json.loads(json.dumps(body["request"]))
            classes = parse_classes(body["classes"])
            analysis = next(
                (a for a in spec["analyses"] if a["id"] == body["analysis_id"]), None
            )
            if analysis is None:
                raise ValueError("Unknown hypothesis")
            branch = next(
                (
                    b
                    for b in analysis["branches"]
                    if b["language_id"] == body["language_id"]
                ),
                None,
            )
            if branch is None:
                raise ValueError("Unknown daughter language")
            branch["package"] = compile_branch(
                branch["package"],
                body["rules"],
                classes,
                spec["proto_inventory"],
                direction=body["direction"],
                mode=body["mode"],
            )
            return dict(request=spec)
        if path == "/api/workspace/shapes":
            require(body, ["text", "classes"])
            return dict(
                phonotactics=parse_shapes(body["text"], parse_classes(body["classes"]))
            )
        if path == "/api/workspace/segment":
            require(body, ["value", "inventory"])
            return segmentations(body["value"], body["inventory"])
        raise Missing("Unknown workspace operation")

    def close(self):
        self.jobs.close()


def default_directory():
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/ComparativeReconstruction"
    return Path.home() / ".local/share/comparative-reconstruction"


def make_server(directory, port=0):
    from waitress import create_server

    app = Application(directory)
    server = create_server(
        app,
        host="127.0.0.1",
        port=port,
        threads=8,
        max_request_body_size=16_000_000,
        channel_timeout=30,
        connection_limit=32,
        expose_tracebacks=False,
    )
    app.configure(server.effective_port)
    return app, server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=default_directory())
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--open", action="store_true", help="Open the private launch link in a browser"
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    args.workspace.mkdir(parents=True, exist_ok=True, mode=0o700)
    with workspace_lock(args.workspace):
        app, server = make_server(args.workspace, args.port)
        print("Private workspace:", app.store.directory, flush=True)
        print("Open this local launch link:", app.launch_url, flush=True)
        if args.open:
            webbrowser.open(app.launch_url)

        def shutdown(signum, frame):
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, shutdown)
        try:
            server.run()
        except KeyboardInterrupt:
            pass
        finally:
            server.close()
            app.close()


if __name__ == "__main__":
    main()
