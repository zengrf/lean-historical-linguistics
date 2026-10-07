"""Durable local projects, immutable revisions, and analysis job records."""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import uuid

from build_pie_corpus import encoded

DOCUMENT_VERSION = "1.0.0"


class Conflict(ValueError):
    pass


class Missing(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier(value):
    if (
        not isinstance(value, str)
        or len(value) != 32
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError("Invalid project or analysis identifier")
    return value


def validate_document(document):
    if not isinstance(document, dict) or set(document) != {
        "schema_version",
        "request",
        "annotations",
        "classes",
        "project_notes",
    }:
        raise ValueError(
            "Expected a versioned project document with request, annotations, classes and project_notes"
        )
    if document["schema_version"] != DOCUMENT_VERSION:
        raise ValueError("Unsupported project schema version")
    if (
        not isinstance(document["request"], dict)
        or not isinstance(document["annotations"], dict)
        or not isinstance(document["classes"], str)
        or not isinstance(document["project_notes"], str)
    ):
        raise ValueError("Invalid project document fields")
    spec = document["request"]
    for field in ["schema_version", "id", "description"]:
        if not isinstance(spec.get(field), str):
            raise ValueError(f"Project request needs a text {field}")
    if any(type(spec.get(k)) is not int for k in ["min_length", "max_length"]) or (
        spec.get("phonotactics") is not None
        and not isinstance(spec["phonotactics"], list)
    ):
        raise ValueError("Invalid request length bounds or word shapes")
    for field in ["languages", "analyses", "entries", "proto_inventory"]:
        if not isinstance(spec.get(field), list):
            raise ValueError(f"Project request needs a {field} list")
    if (
        len(spec["entries"]) > 10000
        or len(spec["languages"]) > 32
        or len(spec["analyses"]) > 32
    ):
        raise ValueError(
            "Project exceeds the supported row, variety or hypothesis limit"
        )
    for row in spec["entries"]:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("id"), str)
            or not isinstance(row.get("meaning"), str)
            or not isinstance(row.get("reflexes"), list)
        ):
            raise ValueError("Each cognate set needs an identifier, gloss and reflexes")

    def text_fields(obj, fields):
        if not isinstance(obj, dict) or any(
            not isinstance(obj.get(k), str) for k in fields
        ):
            raise ValueError("Missing text fields: " + ", ".join(fields))

    def form(value):
        if value is not None and (
            not isinstance(value, list)
            or any(a is not None and not isinstance(a, str) for a in value)
        ):
            raise ValueError(
                "Segments must be a list of symbols, with null for an unknown segment"
            )

    for language in spec["languages"]:
        text_fields(language, ["id", "label"])
    ids = [l["id"] for l in spec["languages"]]
    if len(ids) != len(set(ids)) or len({e["id"] for e in spec["entries"]}) != len(
        spec["entries"]
    ):
        raise ValueError("Daughter and cognate-set identifiers must be distinct")
    form(spec["proto_inventory"])
    for row in spec["entries"]:
        if [
            r.get("language_id") for r in row["reflexes"] if isinstance(r, dict)
        ] != ids:
            raise ValueError(
                "Each cognate set must contain one reflex per daughter, in order"
            )
        for reflex in row["reflexes"]:
            text_fields(reflex, ["language_id", "source_ref"])
            if "form" not in reflex:
                raise ValueError("Missing reflex form")
            form(reflex["form"])
    for model in spec["analyses"]:
        text_fields(model, ["id", "description", "source_ref"])
        if (
            not isinstance(model.get("branches"), list)
            or [b.get("language_id") for b in model["branches"] if isinstance(b, dict)]
            != ids
        ):
            raise ValueError("Each hypothesis needs one branch per daughter, in order")
        for branch in model["branches"]:
            package = branch.get("package")
            text_fields(
                package,
                ["id", "version", "description", "initial_stage", "final_stage"],
            )
            if not isinstance(package.get("inventory"), list) or not isinstance(
                package.get("laws"), list
            ):
                raise ValueError("Invalid sound-law package")
            form(package["inventory"])
            for law in package["laws"]:
                text_fields(law, ["id", "input_stage", "output_stage"])
                r = law.get("rule")
                text_fields(r, ["direction", "mode"])
                if any(
                    not isinstance(r.get(k), list) for k in ["target", "left", "right"]
                ) or any(
                    type(r.get(k)) is not bool for k in ["left_edge", "right_edge"]
                ):
                    raise ValueError("Invalid sound-change context")
                if r.get("replacement") is not None and not isinstance(
                    r["replacement"], str
                ):
                    raise ValueError("Invalid replacement segment")
    annotations = document["annotations"]
    for field in ["_references", "_splits", "_languages"]:
        if not isinstance(annotations.get(field, {}), dict):
            raise ValueError(f"Invalid {field} annotations")
    if any(
        not isinstance(word, list)
        or len(word) > 64
        or any(not isinstance(a, str) or not a or len(a) > 64 for a in word)
        for word in annotations.get("_references", {}).values()
    ):
        raise ValueError("Reference reconstructions must be lists of known segments")
    if any(
        split not in {"unassigned", "train", "development", "test"}
        for split in annotations.get("_splits", {}).values()
    ):
        raise ValueError("Unknown evaluation partition")
    for key, note in annotations.items():
        if key.startswith("_"):
            continue
        if (
            not isinstance(note, dict)
            or not isinstance(note.get("alternatives", []), list)
            or len(note.get("alternatives", [])) > 100
        ):
            raise ValueError("Invalid reading annotations or too many alternatives")
        if not isinstance(note.get("extra", {}), dict):
            raise ValueError("Raw source columns must be a dictionary")
        for reading in [note] + note.get("alternatives", []):
            if not isinstance(reading, dict) or any(
                not isinstance(reading.get(k, ""), str)
                for k in [
                    "original",
                    "source",
                    "witness",
                    "locator",
                    "note",
                    "alignment",
                    "certainty",
                ]
            ):
                raise ValueError("Reading annotations must contain text fields")
            if "form" in reading:
                form(reading["form"])
    raw = encoded(document)
    if len(raw) > 16_000_000:
        raise ValueError("Project exceeds the 16 MB document limit")
    # Drafts can be saved before the phonological model validates. An analysis
    # must separately pass the native Lean request validator.
    return raw.decode("utf-8"), hashlib.sha256(raw).hexdigest()


def new_document(request):
    return dict(
        schema_version=DOCUMENT_VERSION,
        request=request,
        annotations={},
        classes="V = a e i o u\nC = p b t d k g m n s l r",
        project_notes="",
    )


class Store:
    def __init__(self, directory):
        self.directory = Path(directory).expanduser().resolve()
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.directory / "projects.sqlite3"
        self.artifacts = self.directory / "analyses"
        self.artifacts.mkdir(exist_ok=True, mode=0o700)
        with self.connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError(
                    f"Workspace schema {version} is newer than this application"
                )
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL,
                    revision INTEGER NOT NULL, created TEXT NOT NULL,
                    updated TEXT NOT NULL, archived INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS revisions (
                    project_id TEXT NOT NULL REFERENCES projects(id),
                    revision INTEGER NOT NULL, created TEXT NOT NULL,
                    message TEXT NOT NULL, document TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    PRIMARY KEY(project_id, revision)
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created TEXT NOT NULL, updated TEXT NOT NULL,
                    settings TEXT NOT NULL, summary TEXT,
                    error TEXT, engine_sha256 TEXT NOT NULL,
                    FOREIGN KEY(project_id,revision) REFERENCES revisions(project_id,revision)
                );
                CREATE INDEX IF NOT EXISTS jobs_project ON jobs(project_id,created);
                PRAGMA user_version=1;
            """
            )
        os.chmod(self.path, 0o600)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        try:
            with db:
                yield db
        finally:
            db.close()

    def list_projects(self):
        with self.connection() as db:
            return [
                dict(row)
                for row in db.execute("SELECT * FROM projects ORDER BY updated DESC")
            ]

    def create(self, title, document):
        title = self.title(title)
        text, sha = validate_document(document)
        key, stamp = uuid.uuid4().hex, now()
        with self.connection() as db:
            db.execute(
                "INSERT INTO projects VALUES (?,?,?,?,?,0)",
                (key, title, 1, stamp, stamp),
            )
            db.execute(
                "INSERT INTO revisions VALUES (?,?,?,?,?,?)",
                (key, 1, stamp, "Project created", text, sha),
            )
        return self.get(key)

    @staticmethod
    def title(value):
        if not isinstance(value, str) or not value.strip() or len(value) > 200:
            raise ValueError("Use a project title of 1–200 characters")
        return value.strip()

    def get(self, key, revision=None):
        identifier(key)
        with self.connection() as db:
            project = db.execute("SELECT * FROM projects WHERE id=?", (key,)).fetchone()
            if project is None:
                raise Missing("Project not found")
            if revision is not None and (type(revision) is not int or revision < 1):
                raise ValueError("Revision must be a positive integer")
            row = db.execute(
                "SELECT * FROM revisions WHERE project_id=? AND revision=?",
                (key, project["revision"] if revision is None else revision),
            ).fetchone()
            if row is None:
                raise Missing("Revision not found")
            return dict(project) | dict(
                document=json.loads(row["document"]),
                document_revision=row["revision"],
                document_sha256=row["sha256"],
            )

    def save(self, key, revision, title, document, message="Saved changes"):
        identifier(key)
        title = self.title(title)
        if (
            type(revision) is not int
            or revision < 1
            or not isinstance(message, str)
            or len(message) > 1000
        ):
            raise ValueError("Invalid revision or change description")
        text, sha = validate_document(document)
        stamp = now()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT revision FROM projects WHERE id=?", (key,)
            ).fetchone()
            if row is None:
                raise Missing("Project not found")
            if row[0] != revision:
                raise Conflict(
                    "This project changed in another window. Export your draft, then reload the latest revision."
                )
            next_revision = revision + 1
            db.execute(
                "INSERT INTO revisions VALUES (?,?,?,?,?,?)",
                (key, next_revision, stamp, message, text, sha),
            )
            db.execute(
                "UPDATE projects SET title=?,revision=?,updated=? WHERE id=?",
                (title, next_revision, stamp, key),
            )
        return self.get(key)

    def history(self, key):
        identifier(key)
        self.get(key)
        with self.connection() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT revision,created,message,sha256 FROM revisions WHERE project_id=? ORDER BY revision DESC",
                    (key,),
                )
            ]

    def restore(self, key, current_revision, old_revision):
        old = self.get(key, old_revision)
        current = self.get(key)
        return self.save(
            key,
            current_revision,
            current["title"],
            old["document"],
            f"Restored revision {old_revision}; later revisions retained",
        )

    def add_job(self, key, revision, settings, engine_sha256):
        self.get(key, revision)
        identifier(key)
        job_id, stamp = uuid.uuid4().hex, now()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if (
                db.execute(
                    "SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running')"
                ).fetchone()[0]
                >= 16
            ):
                raise Conflict(
                    "The analysis queue is full; wait for a job or cancel one"
                )
            db.execute(
                "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    job_id,
                    key,
                    revision,
                    "queued",
                    stamp,
                    stamp,
                    json.dumps(settings),
                    None,
                    None,
                    engine_sha256,
                ),
            )
        return self.job(job_id)

    def job(self, key):
        identifier(key)
        with self.connection() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (key,)).fetchone()
        if row is None:
            raise Missing("Analysis not found")
        result = dict(row)
        for field in ["settings", "summary"]:
            result[field] = json.loads(result[field]) if result[field] else None
        return result

    def jobs(self, project_id):
        identifier(project_id)
        with self.connection() as db:
            rows = db.execute(
                "SELECT id,project_id,revision,status,created,updated,settings,error,engine_sha256 FROM jobs WHERE project_id=? ORDER BY created DESC LIMIT 100",
                (project_id,),
            ).fetchall()
        return [dict(row) | dict(settings=json.loads(row["settings"])) for row in rows]

    def update_job(self, key, status, *, summary=None, error=None, expected=None):
        identifier(key)
        if status not in {
            "queued",
            "running",
            "complete",
            "incomplete",
            "failed",
            "cancelled",
            "interrupted",
        }:
            raise ValueError("Invalid analysis status")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status FROM jobs WHERE id=?", (key,)).fetchone()
            if row is None:
                raise Missing("Analysis not found")
            if expected is not None and row[0] not in expected:
                return False
            db.execute(
                "UPDATE jobs SET status=?,updated=?,summary=?,error=? WHERE id=?",
                (
                    status,
                    now(),
                    json.dumps(summary) if summary is not None else None,
                    error,
                    key,
                ),
            )
        return True

    def recover_jobs(self):
        with self.connection() as db:
            db.execute(
                "UPDATE jobs SET status='interrupted',updated=?,error=? WHERE status IN ('queued','running')",
                (
                    now(),
                    "The application stopped before this analysis finished. Run it again; no complete result was recorded.",
                ),
            )

    def artifact_directory(self, key):
        return self.artifacts / identifier(key)

    def backup(self, destination):
        destination = Path(destination)
        if destination.resolve() == self.path:
            raise ValueError("Choose a different backup path")
        if destination.exists():
            raise ValueError("Backup destination already exists")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as source:
            target = sqlite3.connect(destination)
            try:
                source.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("Backup integrity check failed")
            finally:
                target.close()
        os.chmod(destination, 0o600)
        return destination
