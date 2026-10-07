"""Bounded process queue; request snapshots and terminal states are durable."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

from build_pie_corpus import ROOT, encoded
from lexicon import BIN, constrain, native, page
from explore_reconstructions import strict_read
from workspace_store import Conflict
from workspace_engine import identity


def prepare_request(document, settings):
    expected = {"analyses", "languages", "entries", "node_budget", "time_limit"}
    if not isinstance(settings, dict) or set(settings) != expected:
        raise ValueError(
            "Select hypotheses, daughter languages, cognate sets and search limits"
        )
    if (
        type(settings["node_budget"]) is not int
        or not 1 <= settings["node_budget"] <= 250000
    ):
        raise ValueError("The search node budget must be 1–250000")
    if (
        type(settings["time_limit"]) not in (int, float)
        or not 0 < settings["time_limit"] <= 60
    ):
        raise ValueError(
            "The search time budget must be greater than zero and at most 60 seconds"
        )
    spec = document["request"]
    if any(
        not isinstance(settings[k], list) or not settings[k]
        for k in ["analyses", "languages"]
    ):
        raise ValueError("Select at least one hypothesis and one daughter variety")
    native("--validate", spec)
    chosen = settings["entries"]
    known = {entry["id"] for entry in spec["entries"]}
    if (
        not isinstance(chosen, list)
        or not chosen
        or any(not isinstance(x, str) for x in chosen)
        or len(set(chosen)) != len(chosen)
        or not set(chosen) <= known
    ):
        raise ValueError("Select at least one distinct, existing cognate set")
    result = constrain(spec, settings["analyses"], settings["languages"])
    result["entries"] = [entry for entry in result["entries"] if entry["id"] in chosen]
    boundary_rows = [
        row["id"]
        for row in result["entries"]
        if any("+" in (r["form"] or []) for r in row["reflexes"])
    ]
    boundary_rules = any(
        "+" in law["rule"][side]
        for model in result["analyses"]
        for branch in model["branches"]
        for law in branch["package"]["laws"]
        for side in ["left", "right"]
    )
    if boundary_rows or boundary_rules:
        raise ValueError(
            "M7 searches segment-only protoforms and cannot generate morphological boundary atoms. Select explicit compared morphological units, or use the separate morphology analysis. Boundary-bearing sets: "
            + ", ".join(boundary_rows[:10])
        )
    return result


class Jobs:
    def __init__(self, store, workers=2):
        self.store = store
        self.store.recover_jobs()
        self.executor = ThreadPoolExecutor(
            max_workers=workers, thread_name_prefix="reconstruction"
        )
        self.lock = threading.RLock()
        self.active = {}
        self.closed = False

    def submit(self, project_id, revision, settings):
        project = self.store.get(project_id, revision)
        request = prepare_request(project["document"], settings)
        fingerprint = identity()["binary_sha256"]
        with self.lock:
            if self.closed:
                raise Conflict("The application is shutting down")
            for existing in self.store.jobs(project_id):
                if (
                    existing["revision"] == revision
                    and existing["settings"] == settings
                    and existing["status"] in {"queued", "running"}
                ):
                    return existing
            if (
                sum(
                    p.stat().st_size
                    for p in self.store.artifacts.rglob("*")
                    if p.is_file()
                )
                > 2 * 1024**3
            ):
                raise Conflict(
                    "Stored analyses have reached 2 GiB. Export and archive this workspace before starting more analyses."
                )
            job = self.store.add_job(project_id, revision, settings, fingerprint)
            directory = self.store.artifact_directory(job["id"])
            directory.mkdir(mode=0o700)
            (directory / "input.json").write_bytes(
                encoded(
                    dict(
                        request=request,
                        limits={k: settings[k] for k in ["node_budget", "time_limit"]},
                        engine_sha256=fingerprint,
                        parent_pid=os.getpid(),
                        evaluation_annotations={
                            k: project["document"]["annotations"].get(k, {})
                            for k in ["_references", "_splits"]
                        },
                    )
                )
            )
            self.executor.submit(self._run, job["id"])
        return job

    @staticmethod
    def stop(process):
        if process.poll() is not None:
            return
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGTERM)
            else:
                process.terminate()
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait(timeout=5)
        except ProcessLookupError:
            pass

    def _run(self, key):
        process = None
        directory = self.store.artifact_directory(key)
        try:
            with self.lock:
                if self.closed or not self.store.update_job(
                    key, "running", expected={"queued"}
                ):
                    return
                log = open(directory / "worker.log", "wb")
                try:
                    process = subprocess.Popen(
                        [
                            sys.executable,
                            str(ROOT / "scripts/workspace_worker.py"),
                            str(directory),
                        ],
                        stdin=subprocess.DEVNULL,
                        stdout=log,
                        stderr=log,
                        start_new_session=True,
                    )
                finally:
                    log.close()
                self.active[key] = process
            deadline = (
                time.monotonic() + self.store.job(key)["settings"]["time_limit"] + 125
            )
            while process.poll() is None:
                if time.monotonic() >= deadline:
                    self.stop(process)
                    self.store.update_job(
                        key,
                        "incomplete",
                        error="The total job time budget was exhausted; completeness is not established",
                        expected={"running"},
                    )
                    return
                time.sleep(0.05)
            if self.store.job(key)["status"] != "running":
                return
            outcome_path = directory / "outcome.json"
            if process.returncode or not outcome_path.is_file():
                raise ValueError("The analysis worker stopped without a checked result")
            outcome = strict_read(outcome_path)
            if outcome["status"] == "complete":
                # Final artifact sizes are bounded even if an external solver
                # produced an unexpectedly large file.
                if (directory / "forest.json").stat().st_size > 134217728:
                    raise ValueError(
                        "The checked search exceeds the 128 MiB artifact limit"
                    )
            self.store.update_job(
                key,
                outcome["status"],
                summary=outcome["summary"],
                error=outcome["error"],
                expected={"running"},
            )
        except Exception as error:
            self.store.update_job(
                key, "failed", error=str(error)[:2000], expected={"running", "queued"}
            )
        finally:
            with self.lock:
                self.active.pop(key, None)

    def cancel(self, key):
        with self.lock:
            changed = self.store.update_job(
                key,
                "cancelled",
                error="Cancelled by the researcher; no completeness claim",
                expected={"queued", "running"},
            )
            if changed and key in self.active:
                self.stop(self.active[key])
        return self.store.job(key)

    def result(self, key):
        job = self.store.job(key)
        if job["status"] != "complete":
            raise ValueError("This analysis has no complete checked result")
        directory = self.store.artifact_directory(key)
        result = dict(
            forest=strict_read(directory / "forest.json"),
            summary=strict_read(directory / "summary.json"),
        )
        if (
            result["summary"] != job["summary"]
            or hashlib.sha256(encoded(result["forest"])).hexdigest()
            != job["summary"]["certificate_sha256"]
        ):
            raise ValueError("Saved certificate integrity check failed")
        return result

    def describe(self, key):
        job = self.store.job(key)
        if job["status"] != "complete":
            raise ValueError("This analysis has no complete checked result")
        request = strict_read(self.store.artifact_directory(key) / "input.json")[
            "request"
        ]
        if (
            hashlib.sha256(encoded(request)).hexdigest()
            != job["summary"]["request_sha256"]
        ):
            raise ValueError("Saved request integrity check failed")
        return dict(request=request, summary=job["summary"])

    def browse(self, key, analysis_id, entry_id=None, offset="0", limit=20):
        if (
            hashlib.sha256(BIN.read_bytes()).hexdigest()
            != self.store.job(key)["engine_sha256"]
        ):
            raise ValueError(
                "This result was checked by a different native build. Download it for archival use or run the analysis again with the current engine."
            )
        return page(
            self.result(key), analysis_id, entry_id=entry_id, offset=offset, limit=limit
        )

    def evaluation(self, key):
        job = self.store.job(key)
        if job["status"] != "complete":
            raise ValueError("Reference evaluation requires a complete analysis")
        path = self.store.artifact_directory(key) / "evaluation.json"
        if not path.is_file():
            return dict(totals=[], rows=[])
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != job["summary"].get("evaluation_sha256"):
            raise ValueError("Evaluation integrity check failed")
        return json.loads(data)

    def close(self):
        with self.lock:
            self.closed = True
            for key, process in list(self.active.items()):
                self.store.update_job(
                    key,
                    "interrupted",
                    error="Application stopped before completion",
                    expected={"running"},
                )
                self.stop(process)
        self.executor.shutdown(wait=True, cancel_futures=True)
        self.store.recover_jobs()
