"""Authored integrity fixtures, not notebook executions or research evidence."""

from __future__ import annotations

import base64
import copy
import io
import json
import stat
import sys
import unittest
import warnings
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from march_mania.publication.evidence_bundle import (  # noqa: E402
    BINDING_SCHEMA,
    MANIFEST,
    NOTEBOOKS,
    REPOSITORY,
    RUNTIME_NOTEBOOK,
    RUNTIME_PNG,
    RUNTIME_RECEIPT,
    SCHEMA,
    SCOPE,
    VALIDATION,
    EvidenceBundleError,
    build_public_bundle,
    canonical,
    definition,
    git_tree,
    pin,
    read_zip,
    sha256,
    strict_json,
    verify_public_bundle,
    verify_runtime,
)

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def fixture_clocks(rows: list[dict]) -> list[dict]:
    """Invent deterministic clocks for test fixtures, never rewrite actual logs."""
    start = datetime(2025, 1, 1, tzinfo=UTC)
    run_start, task_start = 0, 0
    for index, row in enumerate(rows):
        event = row["event"]
        if event == "run_started":
            run_start = index
        if event == "task_started":
            task_start = index
        row["timestamp"] = (start + timedelta(milliseconds=index * 10)).isoformat()
        row["elapsed_seconds"] = round((index - run_start) * 0.01, 3)
        if event == "cell_finished":
            row["cell_elapsed_seconds"] = 0.01
        if event == "task_completed":
            row["task_elapsed_seconds"] = round((index - task_start) * 0.01, 3)
    return rows


def fixture_notebook(cells: int, *, release: bool = False) -> dict:
    result = {"nbformat": 4, "nbformat_minor": 5, "metadata": {}, "cells": []}
    for index in range(cells):
        output = {"output_type": "stream", "name": "stdout", "text": "AUTHORED TEST FIXTURE\n"}
        if release and index == cells - 1:
            output["text"] = "VERIFIED_PUBLIC_REVIEW_COMPLETE\n"
        if release and index == 1:
            output = {
                "output_type": "display_data",
                "metadata": {},
                "data": {
                    "application/vnd.plotly.v1+json": {"data": [], "layout": {}},
                    "image/png": base64.b64encode(PNG).decode(),
                },
            }
        result["cells"].append(
            {
                "cell_type": "code",
                "id": "fixture-" + str(index),
                "metadata": {},
                "source": "print('authored fixture')",
                "execution_count": index + 1,
                "outputs": [output],
            }
        )
    if release:
        result["metadata"]["execution_engine"] = "jupyter_kernel"
    return result


def archive_bytes(
    bodies: dict[str, bytes],
    *,
    comment: bytes = b"",
    duplicate: str | None = None,
    mode: int = stat.S_IFREG | 0o644,
) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.comment = comment
        items = list(sorted(bodies.items()))
        if duplicate is not None:
            items.append((duplicate, bodies[duplicate]))
        for name, body in items:
            entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = mode << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always", UserWarning)
                archive.writestr(entry, body)
    return stream.getvalue()


def fixture_payloads(job: str = "quality") -> tuple[dict[str, bytes], dict]:
    """Tiny self-consistent *invented* receipts exercise refusal paths, not provenance."""
    release = fixture_notebook(5, release=True)
    release_bytes = canonical(release)
    evidence, reproducer = (
        canonical({"scope": "AUTHORED_TEST_FIXTURE"}),
        b"# Fixture, never executed.\n",
    )
    receipt = {
        "status": "PASS",
        "notebook_sha256": sha256(release_bytes),
        "evidence_sha256": sha256(evidence),
        "reproducer_sha256": sha256(reproducer),
        "png_sha256": sha256(PNG),
        "code_cells": 5,
        "plotly_outputs": 1,
        "png_outputs": 1,
        "execution_engine": "jupyter_kernel",
        "model_fits": 0,
        "private_model_reproduced": False,
    }
    source = {
        ".github/workflows/ci.yml": b"# Authored fixture, not actual CI.\n",
        "portfolio/release_evidence.json": evidence,
        "portfolio/reproduce_release.py": reproducer,
        RUNTIME_NOTEBOOK: release_bytes,
        RUNTIME_RECEIPT: canonical(receipt),
        RUNTIME_PNG: PNG,
        "src/example.py": b"# One declared fixture dependency.\n",
    }
    payloads = {
        RUNTIME_RECEIPT: canonical(receipt),
        RUNTIME_NOTEBOOK: release_bytes,
        RUNTIME_PNG: PNG,
    }
    dependencies = {
        "src/example.py": sha256(source["src/example.py"]),
        RUNTIME_RECEIPT: sha256(payloads[RUNTIME_RECEIPT]),
    }
    if job == "quality":
        source[RUNTIME_RECEIPT] = canonical({"scope": "old committed fixture receipt"})
    rows, logs = [], [{"event": "run_started", "notebooks": 6, "publish": True}]
    for position, (name, count) in enumerate(
        zip(NOTEBOOKS, (4, 3, 12, 16, 18, 4), strict=True), start=1
    ):
        value = fixture_notebook(count)
        body = canonical(value)
        unexecuted = copy.deepcopy(value)
        for cell in unexecuted["cells"]:
            cell["execution_count"], cell["outputs"] = None, []
        source["notebooks/" + name] = canonical(unexecuted)
        inputs = {
            "notebook": definition(value),
            "dependencies": dependencies,
            "environment": {"scope": "AUTHORED_TEST_FIXTURE"},
            "execution_mode": "review",
        }
        fingerprint = sha256(json.dumps(inputs, sort_keys=True, allow_nan=False).encode())
        prefix = VALIDATION + f"notebook_runs/{fingerprint}/{PurePosixPath(name).stem}/"
        inputs_raw = canonical(inputs)
        payloads[VALIDATION + name] = payloads[prefix + name] = body
        payloads[prefix + "inputs.json"] = inputs_raw
        # The real TaskStore collector sees these hidden synchronization files;
        # a default GitHub artifact download omits them outside a sealed ZIP.
        payloads[prefix + ".lock"] = b""
        payloads[prefix + "checkpoint.json"] = canonical(
            {
                "fingerprint": fingerprint,
                "outputs": {name: sha256(body), "inputs.json": sha256(inputs_raw)},
            }
        )
        rows.append(
            {
                "notebook": name,
                "fingerprint": fingerprint,
                "sha256": sha256(body),
                "status": "completed",
                "code_cells": count,
            }
        )
        task = PurePosixPath(name).stem
        logs.append({"event": "task_started", "task": task})
        for index in range(count):
            logs.extend(
                [
                    {
                        "event": "cell_started",
                        "notebook": name,
                        "cell": index,
                        "position": position,
                    },
                    {"event": "cell_finished", "notebook": name, "cell": index, "status": "ok"},
                ]
            )
        logs.append({"event": "task_completed", "task": task})
        logs.append(
            {"event": "notebook_completed", "notebook": name, "completed": position, "total": 6}
        )
    logs.extend(
        [
            {"event": "run_completed", "notebooks": 6},
            {"event": "run_started", "notebooks": 6, "publish": True},
        ]
    )
    for position, name in enumerate(NOTEBOOKS, start=1):
        logs.append({"event": "task_reused", "task": PurePosixPath(name).stem})
        logs.append(
            {"event": "notebook_completed", "notebook": name, "completed": position, "total": 6}
        )
    logs.append({"event": "run_completed", "notebooks": 6})
    payloads[VALIDATION + "notebooks.jsonl"] = b"".join(
        canonical(row) for row in fixture_clocks(logs)
    )
    payloads[VALIDATION + "notebook_execution.json"] = canonical(
        {"status": "completed", "notebooks": rows}
    )
    identity = {
        "repository": REPOSITORY,
        "source_commit": "a" * 40,
        "source_tree": git_tree(source, dict.fromkeys(source, "100644")),
        "reviewed_head_commit": "b" * 40,
        "workflow_run_id": 1,
        "run_attempt": 1,
        "workflow_name": "Research quality",
        "workflow_path": ".github/workflows/ci.yml",
        "event": "pull_request",
        "job": job,
    }
    source_zip = archive_bytes(source, comment=identity["source_commit"].encode())
    payloads[VALIDATION + "source.zip"] = source_zip
    payloads[VALIDATION + "source.sha256"] = (
        sha256(source_zip) + "  outputs/validation/source.zip\n"
    ).encode()
    payloads[VALIDATION + "source_commit.txt"] = (identity["source_commit"] + "\n").encode()
    if job == "quality":
        payloads[VALIDATION + "quality.json"] = canonical(
            {
                "checks": [
                    {"check": key, "status": "passed"}
                    for key in ("compile", "lint", "format", "types", "tests")
                ]
            }
        )
        payloads[VALIDATION + "junit.xml"] = (
            b'<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0">'
            b'<testcase classname="AuthoredFixture" name="contract"/></testsuite></testsuites>'
        )
    return payloads, identity


def unverified_bundle(
    payloads: dict[str, bytes],
    identity: dict,
    *,
    manifest=None,
    duplicate: str | None = None,
    mode: int = stat.S_IFREG | 0o644,
) -> tuple[bytes, dict]:
    """Intentionally allow corrupt fixtures so the independent verifier can reject them."""
    manifest = (
        manifest
        if manifest is not None
        else {
            "schema": SCHEMA,
            "scope": SCOPE,
            "identity": identity,
            "members": [{"name": name, **pin(body)} for name, body in sorted(payloads.items())],
        }
    )
    raw = archive_bytes({**payloads, MANIFEST: canonical(manifest)}, duplicate=duplicate, mode=mode)
    return raw, {"schema": BINDING_SCHEMA, "bytes": len(raw), "sha256": sha256(raw), **identity}


class EvidenceBundleTests(unittest.TestCase):
    def setUp(self):
        self.payloads, self.identity = fixture_payloads()

    def verify(self):
        raw, binding = unverified_bundle(self.payloads, self.identity)
        return verify_public_bundle(raw, binding)

    def reject(self, contract: str):
        with self.assertRaisesRegex(EvidenceBundleError, contract):
            self.verify()

    def replace_book(self, mutate):
        receipt_path = VALIDATION + "notebook_execution.json"
        receipt = strict_json(self.payloads[receipt_path])
        row = receipt["notebooks"][0]
        name, fingerprint = row["notebook"], row["fingerprint"]
        prefix = VALIDATION + f"notebook_runs/{fingerprint}/{PurePosixPath(name).stem}/"
        value = strict_json(self.payloads[VALIDATION + name])
        mutate(value)
        body = canonical(value)
        self.payloads[VALIDATION + name] = self.payloads[prefix + name] = body
        row["sha256"] = sha256(body)
        self.payloads[receipt_path] = canonical(receipt)
        checkpoint = strict_json(self.payloads[prefix + "checkpoint.json"])
        checkpoint["outputs"][name] = sha256(body)
        self.payloads[prefix + "checkpoint.json"] = canonical(checkpoint)

    def event_rows(self):
        return [
            strict_json(line) for line in self.payloads[VALIDATION + "notebooks.jsonl"].splitlines()
        ]

    def test_complete_quality_fixture_with_measured_counts(self):
        result = self.verify()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["canonical_notebooks"]["cold_code_cells"], 57)
        self.assertEqual(result["canonical_notebooks"]["dependency_associations"], 12)
        self.assertEqual(result["canonical_notebooks"]["runtime_dependency_associations"], 6)
        self.assertEqual(result["verified_result"]["nested_pins_verified"], 4)
        self.assertEqual(result["retained_empty_task_locks"], 6)
        self.assertEqual(result["notebooks_executed_by_verifier"], 0)
        lifecycle = result["canonical_notebooks"]["event_lifecycle"]
        self.assertEqual(lifecycle["events"], 148)
        self.assertEqual(lifecycle["closed_ordered_runs"], 2)

    def test_lifecycle_rejects_reversed_log_with_unchanged_event_counts(self):
        self.payloads[VALIDATION + "notebooks.jsonl"] = b"".join(
            canonical(row) for row in reversed(self.event_rows())
        )
        self.reject("ordered lifecycle transition")

    def test_lifecycle_rejects_warm_reuse_before_cold_completion(self):
        rows = self.event_rows()
        reused = [row for row in rows if row["event"] == "task_reused"]
        rows = [row for row in rows if row["event"] != "task_reused"]
        rows[1:1] = reused
        self.payloads[VALIDATION + "notebooks.jsonl"] = b"".join(canonical(row) for row in rows)
        self.reject("ordered lifecycle transition")

    def test_publication_scope_is_committed_not_fresh_execution(self):
        payloads, identity = fixture_payloads("notebook-publication")
        raw, binding = build_public_bundle(payloads, identity)
        result = verify_public_bundle(raw, binding)
        self.assertIn("not newly executed", result["verified_result"]["origin"])
        self.assertIsNone(result["quality"])

    def test_deterministic_seal(self):
        self.assertEqual(
            build_public_bundle(self.payloads, self.identity),
            build_public_bundle(self.payloads, self.identity),
        )

    def test_verifier_never_opens_files(self):
        raw, binding = build_public_bundle(self.payloads, self.identity)
        with patch("builtins.open", side_effect=AssertionError("No filesystem access")):
            self.assertEqual(verify_public_bundle(raw, binding)["status"], "PASS")

    def test_external_sha_required(self):
        raw, binding = build_public_bundle(self.payloads, self.identity)
        binding["sha256"] = "0" * 64
        with self.assertRaisesRegex(EvidenceBundleError, "external bundle"):
            verify_public_bundle(raw, binding)

    def test_external_exact_size_not_boolean(self):
        raw, binding = build_public_bundle(self.payloads, self.identity)
        for value in (True, len(raw) - 1):
            binding["bytes"] = value
            with self.assertRaisesRegex(EvidenceBundleError, "external bundle"):
                verify_public_bundle(raw, binding)

    def test_external_unknown_field_rejected(self):
        raw, binding = build_public_bundle(self.payloads, self.identity)
        binding["trust_me"] = True
        with self.assertRaisesRegex(EvidenceBundleError, "closed external"):
            verify_public_bundle(raw, binding)

    def test_different_run_head_tree_and_attempt_rejected(self):
        raw, binding = build_public_bundle(self.payloads, self.identity)
        for key, value in (
            ("workflow_run_id", 2),
            ("run_attempt", 2),
            ("reviewed_head_commit", "c" * 40),
            ("source_tree", "c" * 40),
        ):
            changed = {**binding, key: value}
            with (
                self.subTest(key=key),
                self.assertRaisesRegex(EvidenceBundleError, "externally bound"),
            ):
                verify_public_bundle(raw, changed)

    def test_bool_run_identifier_rejected(self):
        self.identity["workflow_run_id"] = True
        self.reject("positive exact CI")

    def test_other_project_rejected(self):
        self.identity["repository"] = "example/unrelated"
        self.reject("independent project")

    def test_push_must_bind_same_source_head(self):
        self.identity["event"] = "push"
        self.reject("push source/head")

    def test_wrong_workflow_rejected(self):
        self.identity["workflow_path"] = ".github/workflows/other.yml"
        self.reject("exact workflow")

    def test_unsafe_names_rejected(self):
        for name in (
            "../outside",
            "/absolute",
            "a//b",
            "a\\b",
            "a/./b",
            "a:b",
            "trailing ",
            "bad\x00name",
            "folder/NUL.txt",
            "folder/COM1",
            "a" * 256,
        ):
            changed = dict(self.payloads)
            changed[name] = b"fixture"
            with self.subTest(name=name), self.assertRaises(EvidenceBundleError):
                verify_public_bundle(*unverified_bundle(changed, self.identity))

    def test_duplicate_names_rejected(self):
        raw, binding = unverified_bundle(self.payloads, self.identity, duplicate=RUNTIME_NOTEBOOK)
        with self.assertRaisesRegex(EvidenceBundleError, "unique ZIP"):
            verify_public_bundle(raw, binding)

    def test_symlink_modes_rejected(self):
        raw, binding = unverified_bundle(self.payloads, self.identity, mode=stat.S_IFLNK | 0o777)
        with self.assertRaisesRegex(EvidenceBundleError, "safe regular ZIP"):
            verify_public_bundle(raw, binding)

    def test_unlisted_payload_rejected(self):
        manifest = {
            "schema": SCHEMA,
            "scope": SCOPE,
            "identity": self.identity,
            "members": [
                {"name": name, **pin(body)} for name, body in sorted(self.payloads.items())
            ],
        }
        self.payloads[VALIDATION + "unlisted.json"] = b"{}"
        raw, binding = unverified_bundle(self.payloads, self.identity, manifest=manifest)
        with self.assertRaisesRegex(EvidenceBundleError, "manifest payload closure"):
            verify_public_bundle(raw, binding)

    def test_manifest_wrong_member_pin_rejected(self):
        manifest = {
            "schema": SCHEMA,
            "scope": SCOPE,
            "identity": self.identity,
            "members": [
                {"name": name, **pin(body)} for name, body in sorted(self.payloads.items())
            ],
        }
        manifest["members"][0]["crc32"] = "00000000"
        raw, binding = unverified_bundle(self.payloads, self.identity, manifest=manifest)
        with self.assertRaisesRegex(EvidenceBundleError, "member byte/CRC/SHA"):
            verify_public_bundle(raw, binding)

    def test_unknown_runtime_payload_rejected(self):
        self.payloads["other/evidence.json"] = b"{}"
        self.reject("registered public runtime")

    def test_unknown_validation_payload_rejected_even_when_manifest_closed(self):
        self.payloads[VALIDATION + "unrelated_private_payload.json"] = b"{}"
        self.reject("finite registered validation")

    def test_no_task_locks_is_not_fabricated_as_retained(self):
        self.payloads = {
            name: body for name, body in self.payloads.items() if not name.endswith("/.lock")
        }
        self.assertEqual(self.verify()["retained_empty_task_locks"], 0)

    def test_nonempty_registered_task_lock_rejected(self):
        name = next(name for name in self.payloads if name.endswith("/.lock"))
        self.payloads[name] = b"Unexpected content is not a synchronization lock."
        self.reject("canonical task locks must be empty")

    def test_unregistered_task_lock_rejected(self):
        self.payloads[VALIDATION + "notebook_runs/" + "f" * 64 + "/unregistered/.lock"] = b""
        self.reject("finite registered validation")

    def test_other_hidden_file_in_registered_task_rejected(self):
        name = next(name for name in self.payloads if name.endswith("/.lock"))
        self.payloads[name.removesuffix(".lock") + ".other"] = b""
        self.reject("finite registered validation")

    def test_missing_runtime_notebook_rejected(self):
        del self.payloads[RUNTIME_NOTEBOOK]
        self.reject("registered public runtime")

    def test_runtime_notebook_replaced_rejected(self):
        self.payloads[RUNTIME_NOTEBOOK] += b" "
        self.reject("nested receipt body")

    def test_runtime_png_replaced_rejected(self):
        self.payloads[RUNTIME_PNG] += b"x"
        self.reject("nested receipt body")

    def test_resealed_five_cell_notebook_cannot_replace_reviewed_code(self):
        source, _, _ = read_zip(self.payloads[VALIDATION + "source.zip"], source=True)
        value = strict_json(self.payloads[RUNTIME_NOTEBOOK])
        value["cells"][0]["source"] = "print('unreviewed code')"
        self.payloads[RUNTIME_NOTEBOOK] = canonical(value)
        receipt = strict_json(self.payloads[RUNTIME_RECEIPT])
        receipt["notebook_sha256"] = sha256(self.payloads[RUNTIME_NOTEBOOK])
        self.payloads[RUNTIME_RECEIPT] = canonical(receipt)
        with self.assertRaisesRegex(EvidenceBundleError, "source matches reviewed"):
            verify_runtime(self.payloads, source, "quality")

    def test_missing_checkpoint_body_rejected(self):
        path = next(name for name in self.payloads if name.endswith("/inputs.json"))
        del self.payloads[path]
        self.reject("required body or field")

    def test_checkpoint_input_pin_rejected(self):
        path = next(name for name in self.payloads if name.endswith("/inputs.json"))
        self.payloads[path] += b" "
        self.reject("checkpoint output bodies")

    def test_missing_notebook_execution_rejected(self):
        del self.payloads[VALIDATION + "notebook_execution.json"]
        self.reject("required body or field")

    def test_incomplete_notebook_receipt_rejected(self):
        path = VALIDATION + "notebook_execution.json"
        value = strict_json(self.payloads[path])
        value["status"] = "running"
        self.payloads[path] = canonical(value)
        self.reject("completed canonical")

    def test_unexecuted_cell_rejected_even_after_rehash(self):
        self.replace_book(lambda value: value["cells"][0].update(execution_count=None))
        self.reject("executed code counts")

    def test_boolean_execution_count_rejected(self):
        self.replace_book(lambda value: value["cells"][0].update(execution_count=True))
        self.reject("executed code counts")

    def test_warning_output_rejected_even_after_rehash(self):
        self.replace_book(
            lambda value: value["cells"][0]["outputs"][0].update(text="UserWarning: fixture")
        )
        self.reject("notebook warning")

    def test_error_output_rejected_even_after_rehash(self):
        self.replace_book(lambda value: value["cells"][0]["outputs"][0].update(output_type="error"))
        self.reject("unknown notebook output")

    def test_changed_source_definition_rejected(self):
        self.replace_book(lambda value: value["cells"][0].update(source="print('different')"))
        self.reject("definition matches checkpoint")

    def test_duplicate_cold_cell_event_rejected(self):
        path = VALIDATION + "notebooks.jsonl"
        self.payloads[path] += canonical(
            {"event": "cell_started", "notebook": NOTEBOOKS[0], "cell": 0}
        )
        self.reject("cold notebook cell")

    def test_missing_warm_task_rejected(self):
        path = VALIDATION + "notebooks.jsonl"
        self.payloads[path] = b"\n".join(
            line
            for line in self.payloads[path].splitlines()
            if not (b"task_reused" in line and NOTEBOOKS[0].removesuffix(".ipynb").encode() in line)
        )
        self.reject("warm task")

    def test_hidden_failure_event_rejected(self):
        self.payloads[VALIDATION + "notebooks.jsonl"] += canonical({"event": "run_failed"})
        self.reject("hidden notebook failure")

    def test_source_archive_hash_receipt_rejected(self):
        self.payloads[VALIDATION + "source.sha256"] = (
            b"0" * 64 + b"  outputs/validation/source.zip\n"
        )
        self.reject("source archive SHA")

    def test_source_commit_body_rejected(self):
        self.payloads[VALIDATION + "source_commit.txt"] = b"b" * 40 + b"\n"
        self.reject("checked source commit")

    def test_source_git_tree_reconstructed_not_trusted(self):
        self.identity["source_tree"] = "c" * 40
        self.reject("reconstructed reviewed Git tree")

    def test_failed_quality_gate_rejected(self):
        path = VALIDATION + "quality.json"
        value = strict_json(self.payloads[path])
        value["checks"][0]["status"] = "failed"
        self.payloads[path] = canonical(value)
        self.reject("quality gates")

    def test_skipped_junit_rejected(self):
        path = VALIDATION + "junit.xml"
        self.payloads[path] = self.payloads[path].replace(
            b'name="contract"/>', b'name="contract"><skipped/></testcase>'
        )
        self.reject("skipped pytest")

    def test_junit_count_mismatch_rejected(self):
        path = VALIDATION + "junit.xml"
        self.payloads[path] = self.payloads[path].replace(b'tests="1"', b'tests="2"')
        self.reject("suite count closure")

    def test_junit_entities_rejected(self):
        self.payloads[VALIDATION + "junit.xml"] = b'<!DOCTYPE x [<!ENTITY y "fixture">]>'
        self.reject("without entity declarations")

    def test_duplicate_json_keys_and_nonfinite_rejected(self):
        for value in (
            b'{"key":1,"key":2}',
            b'{"key":NaN}',
            b'{"key":Infinity}',
            b'{"key":1e309}',
            b'{"key":-1e999}',
            b"not JSON",
            b'"\xff"',
        ):
            with self.subTest(value=value), self.assertRaises(EvidenceBundleError):
                strict_json(value)

    def test_original_zip_null_name_is_rejected(self):
        raw = archive_bytes({"unsafeXname": b"fixture"})
        raw = raw.replace(b"unsafeXname", b"unsafe\x00name")
        with self.assertRaisesRegex(EvidenceBundleError, "original ZIP name"):
            read_zip(raw)

    def test_zip_crc_corruption_is_rejected(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_STORED) as archive:
            entry = zipfile.ZipInfo("fixture.txt")
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(entry, b"KNOWN_FIXTURE_BODY")
        raw = stream.getvalue().replace(b"KNOWN_FIXTURE_BODY", b"WRONG_FIXTURE_BODY")
        with self.assertRaisesRegex(EvidenceBundleError, "complete bounded ZIP"):
            read_zip(raw)

    def test_git_dos_directories_and_files_are_read_without_extraction(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_STORED) as archive:
            directory = zipfile.ZipInfo("folder/")
            directory.create_system, directory.external_attr = 0, 16
            archive.writestr(directory, b"")
            file = zipfile.ZipInfo("folder/file.txt")
            file.create_system, file.external_attr = 0, 1
            archive.writestr(file, b"fixture")
        raw = bytearray(stream.getvalue())
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            offset = archive.start_dir
        first_length = 46 + len("folder/")
        # Explicit DOS regular external attributes are zero in native git archive.
        raw[offset + first_length + 38 : offset + first_length + 42] = b"\x00" * 4
        bodies, modes, _ = read_zip(bytes(raw), source=True)
        self.assertEqual(bodies, {"folder/file.txt": b"fixture"})
        self.assertEqual(modes, {"folder/file.txt": "100644"})

    def test_unbacked_dependency_rejected_even_when_source_root_is_rebound(self):
        source, modes, _ = read_zip(self.payloads[VALIDATION + "source.zip"], source=True)
        source["src/example.py"] = b"# changed after declared dependency was frozen\n"
        raw = archive_bytes(source, comment=self.identity["source_commit"].encode())
        self.payloads[VALIDATION + "source.zip"] = raw
        self.payloads[VALIDATION + "source.sha256"] = (
            sha256(raw) + "  outputs/validation/source.zip\n"
        ).encode()
        self.identity["source_tree"] = git_tree(source, modes)
        self.reject("missing or mismatched declared dependency")

    def test_malformed_zip_rejected(self):
        raw = b"not a ZIP"
        binding = {
            "schema": BINDING_SCHEMA,
            "bytes": len(raw),
            "sha256": sha256(raw),
            **self.identity,
        }
        with self.assertRaisesRegex(EvidenceBundleError, "bounded ZIP"):
            verify_public_bundle(raw, binding)


if __name__ == "__main__":
    unittest.main()
