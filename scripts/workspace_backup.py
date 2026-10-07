"""Portable, hash-checked workspace backups. Restore only into an empty directory."""

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import tempfile
import zipfile

from workspace_store import Store, Conflict


def safe_members(archive, *, maximum=3 * 1024**3, count=100000):
    members = archive.infolist()
    names = [item.filename for item in members]
    if len(names) > count or len(set(names)) != len(names):
        raise ValueError("Archive has too many files or duplicate paths")
    if sum(item.file_size for item in members) > maximum:
        raise ValueError("Archive expands beyond the permitted size")
    for item in members:
        name = PurePosixPath(item.filename)
        if (
            name.is_absolute()
            or ".." in name.parts
            or "\\" in item.filename
            or not name.parts
            or ":" in name.parts[0]
            or (item.external_attr >> 16) & 0o170000 == 0o120000
        ):
            raise ValueError("Unsafe archive path or symbolic link")
    return members


@contextmanager
def workspace_lock(directory):
    import fcntl

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with open(directory / "application.lock", "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Conflict(
                "This workspace is open. Use its backup button, or close it before running this command."
            )
        yield


def backup(store, destination):
    """Caller holds the application job lock or the exclusive workspace lock."""
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Backup destination already exists")
    with tempfile.TemporaryDirectory(prefix="comparative-backup-") as temporary:
        database = store.backup(Path(temporary) / "projects.sqlite3")
        with sqlite3.connect(database) as db:
            if db.execute(
                "SELECT COUNT(*) FROM jobs WHERE status IN ('running','queued')"
            ).fetchone()[0]:
                raise Conflict(
                    "Finish or cancel active analyses before making a full workspace backup"
                )
            ids = [row[0] for row in db.execute("SELECT id FROM jobs")]
        files = {"projects.sqlite3": database}
        for key in ids:
            for path in store.artifact_directory(key).glob("*"):
                if path.is_file() and not path.is_symlink():
                    files[f"analyses/{key}/{path.name}"] = path
        manifest = {"format": "comparative-workspace-1", "sha256": {}}
        # Hash in bounded memory; large search forests need not fit in RAM.
        for name, path in files.items():
            with path.open("rb") as stream:
                manifest["sha256"][name] = hashlib.file_digest(
                    stream, "sha256"
                ).hexdigest()
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary_zip = Path(temporary) / "backup.zip"
        with zipfile.ZipFile(temporary_zip, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, path in sorted(files.items()):
                archive.write(path, name)
            archive.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
        with destination.open("xb") as output, temporary_zip.open("rb") as source:
            shutil.copyfileobj(source, output)
        destination.chmod(0o600)
    return destination


def restore(source, destination):
    destination = Path(destination).expanduser().resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Restore requires a new or empty workspace directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".comparative-restore-", dir=destination.parent
    ) as temporary:
        root = Path(temporary) / "workspace"
        root.mkdir(mode=0o700)
        with zipfile.ZipFile(source) as archive:
            members = safe_members(archive)
            manifest = json.loads(archive.read("manifest.json"))
            if manifest.get("format") != "comparative-workspace-1":
                raise ValueError("Unsupported backup format")
            expected = manifest["sha256"]
            if (
                set(expected) != {item.filename for item in members} - {"manifest.json"}
                or "projects.sqlite3" not in expected
            ):
                raise ValueError("Backup manifest does not match the archive")
            for name, sha in expected.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                digest = hashlib.sha256()
                with archive.open(name) as input_file, path.open("xb") as output:
                    while block := input_file.read(1024 * 1024):
                        digest.update(block)
                        output.write(block)
                path.chmod(0o600)
                if digest.hexdigest() != sha:
                    raise ValueError(f"Backup integrity check failed: {name}")
        with sqlite3.connect(
            f"file:{root / 'projects.sqlite3'}?mode=ro", uri=True
        ) as db:
            db.execute("PRAGMA trusted_schema=OFF")
            if (
                db.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
                or db.execute("PRAGMA foreign_key_check").fetchall()
            ):
                raise ValueError("Backup database integrity check failed")
            if db.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('trigger','view')"
            ).fetchall():
                raise ValueError("Unexpected executable objects in backup database")
        recovered = Store(root)
        for item in recovered.list_projects():
            recovered.get(item["id"])
        recovered.recover_jobs()
        if destination.exists():
            destination.rmdir()
        root.replace(destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("backup", "restore"):
        p = sub.add_parser(name)
        p.add_argument("source", type=Path)
        p.add_argument("destination", type=Path)
    args = parser.parse_args()
    if args.command == "backup":
        with workspace_lock(args.source):
            path = backup(Store(args.source), args.destination)
    else:
        path = restore(args.source, args.destination)
    print(path)


if __name__ == "__main__":
    main()
