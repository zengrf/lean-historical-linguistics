"""Research data preservation, durable job lifecycle, and local security boundary."""

from copy import deepcopy
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_m7_fixtures import merger, deletion, contextual
from build_pie_corpus import ROOT, encoded
from lexicon import BIN, reconstruct
from linguist_notation import (
    parse_classes,
    parse_rule,
    format_rule,
    compile_branch,
    parse_shapes,
    segmentations,
)
from workspace_store import Store, Conflict, new_document, validate_document
from workspace_jobs import Jobs, prepare_request
from workspace_backup import backup, restore, safe_members, workspace_lock
from workspace_exchange import (
    import_edictor,
    export_edictor,
    cldf_zip,
    import_cldf_zip,
    tei_apparatus,
    cell_key,
    correspondences,
)
from workspace_evaluation import evaluate
from workspace_server import Application
from workspace_engine import identity, STAMP


def settings(spec=None):
    spec = spec or merger()
    return dict(
        analyses=[m["id"] for m in spec["analyses"]],
        languages=[l["id"] for l in spec["languages"]],
        entries=[e["id"] for e in spec["entries"]],
        node_budget=250000,
        time_limit=10,
    )


class NotationTests(unittest.TestCase):
    def test_all_shipped_lexicon_rules_round_trip(self):
        count = 0
        for path in (ROOT / "data/lexicon").glob("*.json"):
            for m in json.loads(path.read_text())["analyses"]:
                for branch in m["branches"]:
                    for law in branch["package"]["laws"]:
                        self.assertEqual(
                            parse_rule(format_rule(law["rule"])), law["rule"]
                        )
                        count += 1
        self.assertGreater(count, 20)

    def test_context_orientation_and_flags(self):
        r = parse_rule("[p t] > b / # a i _ + . #; rtl; feeding")
        self.assertEqual(r["left"], [["i"], ["a"]])
        self.assertEqual(r["right"], ["+", "*"])
        self.assertTrue(r["left_edge"] and r["right_edge"])
        self.assertEqual(r["direction"], "right-to-left")
        self.assertEqual(parse_rule(format_rule(r)), r)

    def test_unsupported_changes_fail_explicitly(self):
        for text in [
            "∅ > p",
            "p t > t p",
            "p > b a",
            "p > b / V V V _",
            "p > b / _ # a",
            "p > b; rtl; ltr",
            "p > b; silently",
            "[p t > b",
            "p > V",
        ]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_rule(text, {"V": ["a", "i"]})

    def test_shapes_and_classes(self):
        c = parse_classes("// comment\nV = a i\nC = p t")
        self.assertEqual(parse_shapes("C V | ∅", c), [[["p", "t"], ["a", "i"]], []])
        self.assertIsNone(parse_shapes("", c))
        for text in ["V = a a", "V = ?", "V a", "V=a\nV=i"]:
            with self.assertRaises(ValueError):
                parse_classes(text)

    def test_segmentation_preserves_ambiguity_and_unicode(self):
        r = segmentations("tɕa", ["tɕ", "t", "ɕ", "a"])
        self.assertEqual(sorted(r["options"]), sorted([["tɕ", "a"], ["t", "ɕ", "a"]]))
        self.assertFalse(r["unique"])
        self.assertEqual(segmentations("ā", ["a", "̄"])["options"], [])

    def test_branch_chronology_rebuilt_without_changing_source(self):
        p = merger()["analyses"][0]["branches"][0]["package"]
        original = deepcopy(p)
        compiled = compile_branch(p, "p > b\nb > ∅ / # _", {}, ["p"])
        self.assertEqual(
            compiled["laws"][1]["input_stage"], compiled["laws"][0]["output_stage"]
        )
        self.assertEqual(p, original)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / "workspace")
        self.document = new_document(merger())
        self.project = self.store.create("Comparative study", self.document)

    def tearDown(self):
        self.tmp.cleanup()

    def test_revisions_survive_restart_and_restore_is_nondestructive(self):
        changed = deepcopy(self.document)
        changed["project_notes"] = "Edited"
        p = self.store.save(self.project["id"], 1, "Study", changed)
        reloaded = Store(self.store.directory)
        self.assertEqual(reloaded.get(p["id"])["document"], changed)
        restored = reloaded.restore(p["id"], 2, 1)
        self.assertEqual(restored["revision"], 3)
        self.assertEqual(restored["document"], self.document)
        self.assertEqual(reloaded.get(p["id"], 2)["document"], changed)
        self.assertEqual(len(reloaded.history(p["id"])), 3)

    def test_concurrent_save_detects_lost_update(self):
        def save_note(note):
            d = deepcopy(self.document)
            d["project_notes"] = note
            try:
                return self.store.save(self.project["id"], 1, "Study", d)["revision"]
            except Conflict:
                return "conflict"

        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(save_note, ["one", "two"]))
        self.assertCountEqual(results, [2, "conflict"])

    def test_drafts_can_have_no_proto_inventory_but_malformed_structure_is_rejected(
        self,
    ):
        d = deepcopy(self.document)
        d["request"]["proto_inventory"] = []
        validate_document(d)
        d["request"]["entries"][0]["reflexes"].pop()
        with self.assertRaises(ValueError):
            validate_document(d)

    def test_newer_schema_is_refused_without_migration(self):
        with sqlite3.connect(self.store.path) as db:
            db.execute("PRAGMA user_version=99")
        with self.assertRaisesRegex(ValueError, "newer"):
            Store(self.store.directory)

    def test_private_database_and_path_validation(self):
        self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)
        for value in ["../secrets", "X" * 32, None]:
            with self.assertRaises(ValueError):
                self.store.get(value)

    def test_terminal_cancellation_cannot_be_overwritten(self):
        job = self.store.add_job(self.project["id"], 1, settings(), "0" * 64)
        self.store.update_job(job["id"], "cancelled", expected={"queued"})
        self.assertFalse(
            self.store.update_job(job["id"], "complete", expected={"running"})
        )
        self.assertEqual(self.store.job(job["id"])["status"], "cancelled")

    def test_interrupted_jobs_are_never_complete_after_restart(self):
        job = self.store.add_job(self.project["id"], 1, settings(), "0" * 64)
        self.store.update_job(job["id"], "running")
        restarted = Jobs(self.store)
        try:
            self.assertEqual(self.store.job(job["id"])["status"], "interrupted")
        finally:
            restarted.close()

    def test_backup_restore_preserves_revisions_and_artifacts(self):
        job = self.store.add_job(self.project["id"], 1, settings(), "0" * 64)
        self.store.update_job(job["id"], "failed", error="Controlled failure")
        directory = self.store.artifact_directory(job["id"])
        directory.mkdir()
        (directory / "input.json").write_bytes(encoded(self.document))
        path = backup(self.store, self.root / "backup.zip")
        restored = Store(restore(path, self.root / "restored"))
        self.assertEqual(
            restored.get(self.project["id"]), self.store.get(self.project["id"])
        )
        self.assertEqual(restored.job(job["id"]), self.store.job(job["id"]))
        self.assertEqual(
            (restored.artifact_directory(job["id"]) / "input.json").read_bytes(),
            encoded(self.document),
        )
        with self.assertRaises(ValueError):
            restore(path, self.store.directory)

    def test_backup_refuses_active_jobs(self):
        self.store.add_job(self.project["id"], 1, settings(), "0" * 64)
        with self.assertRaises(Conflict):
            backup(self.store, self.root / "backup.zip")

    def test_backup_tampering_is_rejected_before_destination_created(self):
        path = backup(self.store, self.root / "backup.zip")
        with zipfile.ZipFile(path) as z:
            content = {n: z.read(n) for n in z.namelist()}
        content["projects.sqlite3"] += b"tamper"
        with zipfile.ZipFile(self.root / "bad.zip", "w") as z:
            for name, data in content.items():
                z.writestr(name, data)
        with self.assertRaisesRegex(ValueError, "integrity"):
            restore(self.root / "bad.zip", self.root / "new")
        self.assertFalse((self.root / "new").exists())

    def test_exclusive_workspace_lock(self):
        with workspace_lock(self.store.directory):
            with self.assertRaises(Conflict):
                with workspace_lock(self.store.directory):
                    pass


class ExchangeTests(unittest.TestCase):
    TSV = "ID\tDOCULECT\tCONCEPT\tTOKENS\tCOGID\tVALUE\tSOURCE\tWITNESS\tLOCATOR\tCUSTOM\n1\t漢語\twater\t? a\t17\t甲\tBook\tMS A\t12r:3\tretained\n2\tB\twater\t∅\t17\t∅\tBook\tMS B\t8\talso retained\n3\tB\tfire\t\t18\t\tBook\tMS B\t9\tmissing\n"

    def test_edictor_unicode_source_columns_and_unknown_empty_missing(self):
        doc = import_edictor(self.TSV)["document"]
        exported = export_edictor(doc)
        self.assertIn("CUSTOM", exported)
        self.assertIn("retained", exported)
        imported = import_edictor(exported)["document"]
        self.assertEqual(
            [r["form"] for e in imported["request"]["entries"] for r in e["reflexes"]],
            [[None, "a"], [], None, None],
        )
        note = imported["annotations"][cell_key("set-1", "language-1")]
        self.assertEqual(
            (note["original"], note["witness"], note["locator"]),
            ("甲", "MS A", "12r:3"),
        )

    def test_duplicate_and_partial_cognacy_are_not_silently_selected(self):
        for text in [
            self.TSV + "4\tB\twater\ta\t17\ta\tBook\tX\t1\tx\n",
            self.TSV.replace("COGID", "COGIDS"),
            self.TSV.replace("\n2\t", "\n1\t"),
        ]:
            with self.assertRaises(ValueError):
                import_edictor(text)

    def test_cldf_export_validates_and_import_distinguishes_empty(self):
        doc = import_edictor(self.TSV)["document"]
        data = cldf_zip(doc)
        result = import_cldf_zip(data)["document"]
        self.assertEqual(
            [r["form"] for e in result["request"]["entries"] for r in e["reflexes"]],
            [[None, "a"], []],
        )
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertEqual(json.loads(archive.read("project.json")), doc)

    def test_zip_traversal_duplicate_and_remote_dependencies_rejected(self):
        for name in ["../outside", "/absolute", "dir\\escape", "file:file"]:
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, "w") as z:
                z.writestr(name, "bad")
            with self.assertRaises(ValueError):
                import_cldf_zip(stream.getvalue())
        data = cldf_zip(new_document(merger()))
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            content = {n: z.read(n) for n in z.namelist()}
        metadata = next(n for n in content if "metadata" in n)
        m = json.loads(content[metadata])
        m["tables"][0]["url"] = "https://example.invalid/forms.csv"
        content[metadata] = encoded(m)
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as z:
            for name, value in content.items():
                z.writestr(name, value)
        with self.assertRaisesRegex(ValueError, "local files"):
            import_cldf_zip(stream.getvalue())

    def test_tei_preserves_readings_witnesses_and_escapes_markup(self):
        doc = new_document(merger())
        doc["annotations"][cell_key("one", "A")] = dict(
            original="<甲 & 乙>",
            witness="MS A",
            certainty="low",
            alternatives=[
                dict(original="丙", form=["b", "a"], witness="MS B", source="Edition")
            ],
        )
        xml = tei_apparatus(doc)
        root = ET.fromstring(xml)
        ns = {"t": "http://www.tei-c.org/ns/1.0"}
        readings = root.findall(".//t:rdg", ns)
        self.assertEqual(readings[0].text, "<甲 & 乙>")
        self.assertEqual(readings[0].attrib["cert"], "low")
        self.assertEqual(readings[1].text, "丙")
        self.assertFalse(root.findall(".//t:lem", ns))

    def test_correspondences_require_explicit_consistent_alignments(self):
        doc = new_document(merger())
        for language in ["A", "B"]:
            doc["annotations"][cell_key("one", language)] = {"alignment": "p a"}
        result = correspondences(doc)
        self.assertEqual(
            result["columns"],
            [
                {"segments": ["p", "p"], "count": 1},
                {"segments": ["a", "a"], "count": 1},
            ],
        )
        self.assertEqual(result["skipped"], ["two"])
        doc["annotations"][cell_key("one", "A")]["alignment"] = "b a"
        with self.assertRaises(ValueError):
            correspondences(doc)


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = Application(self.tmp.name)
        self.app.configure(8765)

    def tearDown(self):
        self.app.close()
        self.tmp.cleanup()

    def call(self, path, body=None, **overrides):
        data = encoded(body) if isinstance(body, dict) else body or b""
        env = dict(
            REQUEST_METHOD="POST" if body is not None else "GET",
            PATH_INFO=path,
            QUERY_STRING="",
            HTTP_HOST="127.0.0.1:8765",
            HTTP_ORIGIN="http://127.0.0.1:8765",
            HTTP_COOKIE=f"{self.app.cookie_name}={self.app.launch_token}",
            HTTP_X_WORKSPACE_TOKEN=self.app.csrf,
            CONTENT_TYPE="application/json",
            CONTENT_LENGTH=str(len(data)),
        )
        env["wsgi.input"] = io.BytesIO(data)
        env.update(overrides)
        status = []

        def start(code, headers):
            status.extend([int(code.split()[0]), dict(headers)])

        result = b"".join(self.app(env, start))
        return status[0], status[1], result

    def test_authentication_launch_redirect_and_headers(self):
        self.assertEqual(self.call("/", HTTP_COOKIE="")[0], 403)
        code, headers, _ = self.call(
            "/", HTTP_COOKIE="", QUERY_STRING="access=" + self.app.launch_token
        )
        self.assertEqual(code, 303)
        self.assertEqual(headers["Location"], "/")
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", headers["Set-Cookie"])
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_dns_rebinding_cross_origin_and_csrf_rejected(self):
        for override in [
            dict(HTTP_HOST="attacker.example:8765"),
            dict(HTTP_ORIGIN="https://attacker.example"),
            dict(HTTP_X_WORKSPACE_TOKEN="bad"),
            dict(HTTP_SEC_FETCH_SITE="cross-site"),
        ]:
            self.assertEqual(self.call("/api/workspace/create", {}, **override)[0], 403)

    def test_strict_json_body_limits_and_static_traversal(self):
        for body in [b'{"x":1,"x":2}', b'{"x":NaN}', b"\xff"]:
            self.assertEqual(self.call("/api/workspace/create", body)[0], 400)
        self.assertEqual(
            self.call("/api/workspace/create", b"{}", CONTENT_LENGTH="16000001")[0], 400
        )
        self.assertEqual(self.call("/../scripts/workspace_server.py")[0], 404)
        self.assertEqual(self.call("/projects.sqlite3")[0], 404)

    def test_project_source_markup_is_data_not_executable_html(self):
        doc = new_document(merger())
        doc["project_notes"] = "<script>alert(1)</script>"
        status, headers, raw = self.call(
            "/api/workspace/create", dict(title="Study", document=doc)
        )
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers["Content-Type"])
        self.assertEqual(
            json.loads(raw)["document"]["project_notes"], doc["project_notes"]
        )

    def test_malformed_cldf_reports_client_error(self):
        self.assertEqual(
            self.call(
                "/api/workspace/import",
                dict(
                    format="cldf",
                    text=base64.b64encode(b"notzip").decode(),
                    title="X",
                    source="X",
                ),
            )[0],
            400,
        )


@unittest.skipUnless(
    BIN.is_file(), "Build lexicon_check for native workspace integration"
)
class NativeJobTests(unittest.TestCase):
    # Reuse the same isolated storage fixture without rerunning StoreTests.
    def setUp(self):
        StoreTests.setUp(self)
        self.jobs = Jobs(self.store)

    def tearDown(self):
        self.jobs.close()
        StoreTests.tearDown(self)

    def wait_job(self, key):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            job = self.store.job(key)
            if job["status"] not in {"running", "queued"}:
                return job
            time.sleep(0.03)
        self.fail("Native job did not finish")

    def test_native_job_frozen_revision_evaluation_and_integrity(self):
        doc = deepcopy(self.document)
        doc["annotations"] = {
            "_references": {"one": ["b", "a"]},
            "_splits": {"one": "test"},
        }
        p = self.store.save(self.project["id"], 1, "Study", doc)
        job = self.jobs.submit(p["id"], 2, settings())
        doc["request"]["entries"][0]["reflexes"][0]["form"] = ["b", "a"]
        self.store.save(p["id"], 2, "Later", doc)
        finished = self.wait_job(job["id"])
        self.assertEqual(finished["status"], "complete", finished["error"])
        self.assertEqual(finished["revision"], 2)
        self.assertEqual(finished["summary"]["lexicon_count"], "5")
        self.assertNotIn("summary", self.store.jobs(p["id"])[0])
        self.assertNotIn("forest", self.jobs.describe(job["id"]))
        self.assertEqual(
            self.jobs.describe(job["id"])["request"]["entries"][0]["reflexes"][0][
                "form"
            ],
            ["p", "a"],
        )
        self.assertEqual(
            self.jobs.browse(job["id"], "mergers", "one", limit=2)["count"], "2"
        )
        self.assertEqual(self.jobs.evaluation(job["id"])["totals"][0]["recovered"], 1)
        path = self.store.artifact_directory(job["id"]) / "forest.json"
        forest = json.loads(path.read_text())
        forest["request"]["description"] = "tampered"
        path.write_bytes(encoded(forest))
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.jobs.result(job["id"])

    def test_budget_exhaustion_has_no_complete_result(self):
        limits = settings()
        limits["node_budget"] = 1
        job = self.jobs.submit(self.project["id"], 1, limits)
        self.assertEqual(self.wait_job(job["id"])["status"], "incomplete")
        with self.assertRaises(ValueError):
            self.jobs.result(job["id"])

    def test_cancelled_queued_job_never_starts(self):
        with patch.object(self.jobs.executor, "submit"):
            job = self.jobs.submit(self.project["id"], 1, settings())
            duplicate = self.jobs.submit(self.project["id"], 1, settings())
            self.assertEqual(duplicate["id"], job["id"])
            self.jobs.cancel(job["id"])
            self.jobs._run(job["id"])
            self.assertEqual(self.store.job(job["id"])["status"], "cancelled")

    def test_references_do_not_change_search_request(self):
        first = prepare_request(self.document, settings())
        d = deepcopy(self.document)
        d["annotations"] = {
            "_references": {"one": ["unavailable"]},
            "_splits": {"one": "test"},
        }
        self.assertEqual(first, prepare_request(d, settings()))
        result = reconstruct(first)
        scores = evaluate(first, d["annotations"], result["summary"])
        self.assertEqual(scores["totals"][0]["in_scope"], 0)
        self.assertEqual(scores["totals"][0]["recovered"], 0)

    def test_stale_native_build_is_rejected(self):
        stamp = json.loads(STAMP.read_text())
        stamp["binary_sha256"] = "0" * 64
        path = self.root / "stale-build.json"
        path.write_bytes(encoded(stamp))
        with patch("workspace_engine.STAMP", path), self.assertRaisesRegex(
            ValueError, "changed"
        ):
            identity()

    def test_morphological_boundaries_are_reported_as_unsupported(self):
        document = deepcopy(self.document)
        document["request"]["entries"][0]["reflexes"][0]["form"] = ["p", "+", "a"]
        with self.assertRaisesRegex(ValueError, "morphological boundary"):
            prepare_request(document, settings())
        selected = settings()
        selected["languages"] = ["B"]
        self.assertIsNone(
            prepare_request(document, selected)["entries"][0]["reflexes"][0]["form"]
        )

    def test_running_worker_is_cancelled_with_its_process_group(self):
        spec = contextual()
        spec["max_length"] = 64
        for row in spec["entries"]:
            for reflex in row["reflexes"]:
                reflex["form"] = None
        project = self.store.create("Cancellation control", new_document(spec))
        job = self.jobs.submit(project["id"], 1, settings(spec))
        deadline = time.monotonic() + 5
        while job["id"] not in self.jobs.active and time.monotonic() < deadline:
            time.sleep(0.01)
        process = self.jobs.active[job["id"]]
        self.assertIsNone(process.poll())
        self.jobs.cancel(job["id"])
        self.assertIsNotNone(process.poll())
        self.assertEqual(self.wait_job(job["id"])["status"], "cancelled")
        with self.assertRaises(ValueError):
            self.jobs.result(job["id"])


if __name__ == "__main__":
    unittest.main()
