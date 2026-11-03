"""Read-only public CI evidence verification; hashes are not authorship attestations.

Only bytes and an independently obtained binding enter this module. It never
extracts an archive, opens a file, contacts a service, imports a trainer, runs a
notebook, fits a model or scores predictions. The companion CLI collects public
CI outputs; the verifier refuses missing bodies rather than trusting a receipt.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import math
import re
import stat
import xml.etree.ElementTree as ET
import zipfile
import zlib
from collections import Counter
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Any

REPOSITORY = "alvaromendizabal/march-machine-learning-mania-2026"
SCHEMA = "MARCH_PUBLIC_CI_BUNDLE_V1"
BINDING_SCHEMA = "MARCH_PUBLIC_CI_EXTERNAL_BINDING_V1"
SCOPE = "Public CI source, native notebook outputs and validation evidence; no private model replay"
MANIFEST = "bundle_manifest.json"
VALIDATION = "outputs/validation/"
RUNTIME_RECEIPT = "reports/verified_result/notebook_execution.json"
RUNTIME_NOTEBOOK = "portfolio/verified_result.ipynb"
RUNTIME_PNG = "reports/verified_result/score_comparison.png"
RUNTIME_PATHS = (RUNTIME_RECEIPT, RUNTIME_NOTEBOOK, RUNTIME_PNG)
VALIDATION_FILES = frozenset(
    (
        "source.zip",
        "source.sha256",
        "source_commit.txt",
        "notebook_execution.json",
        "notebooks.jsonl",
        "model_notebook.jsonl",
        "publication.lock",
        "quality.json",
        "junit.xml",
        "coverage.xml",
        "portfolio.jsonl",
        "refinement.jsonl",
        "release.jsonl",
    )
)
NOTEBOOKS = (
    "00_data_audit_and_preparation.ipynb",
    "01_split_protocol_and_pre_tournament_snapshots.ipynb",
    "02_feature_store_and_diagnostics.ipynb",
    "03_model_comparison_and_diagnostics.ipynb",
    "04_locked_benchmark_and_final_submission.ipynb",
    "05_feature_research.ipynb",
)
IDENTITY_KEYS = frozenset(
    (
        "repository",
        "source_commit",
        "source_tree",
        "reviewed_head_commit",
        "workflow_run_id",
        "run_attempt",
        "workflow_name",
        "workflow_path",
        "event",
        "job",
    )
)
MAX_BUNDLE_BYTES = 40_000_000
MAX_MEMBER_BYTES = 50_000_000
MAX_DECODED_BYTES = 250_000_000
MAX_MEMBERS = 10_000


class EvidenceBundleError(ValueError):
    """A public body, identity, boundary or receipt failed a named contract."""


def require(condition: bool, contract: str) -> None:
    if not condition:
        raise EvidenceBundleError(contract)


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def pin(body: bytes) -> dict[str, Any]:
    return {"bytes": len(body), "sha256": sha256(body), "crc32": f"{zlib.crc32(body):08x}"}


def canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def strict_json(body: bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, value in items:
            require(name not in result, "unique JSON object keys")
            result[name] = value
        return result

    def constant(_: str) -> None:
        raise EvidenceBundleError("finite JSON numbers")

    def finite_float(token: str) -> float:
        value = float(token)
        require(math.isfinite(value), "finite JSON numbers")
        return value

    try:
        return json.loads(
            body, object_pairs_hook=pairs, parse_constant=constant, parse_float=finite_float
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise EvidenceBundleError("complete bounded UTF-8 JSON") from error


def safe_name(name: Any, *, directory: bool = False) -> str:
    require(type(name) is str and bool(name), "nonempty text member name")
    value = name[:-1] if directory and name.endswith("/") else name
    path = PurePosixPath(value)
    require(
        bool(value)
        and str(path) == value
        and not path.is_absolute()
        and "\\" not in value
        and ":" not in value
        and all(ord(char) >= 32 and ord(char) != 127 for char in value)
        and all(
            part not in ("", ".", "..") and part.rstrip(" .") == part for part in value.split("/")
        ),
        "safe normalized relative member name",
    )
    reserved = {"CON", "PRN", "AUX", "NUL"} | {
        prefix + str(index) for prefix in ("COM", "LPT") for index in range(1, 10)
    }
    require(
        len(value.encode("utf-8")) <= 1024
        and all(
            len(part.encode("utf-8")) <= 255 and part.split(".")[0].upper() not in reserved
            for part in value.split("/")
        ),
        "portable bounded member name",
    )
    return value


def read_zip(raw: bytes, *, source: bool = False) -> tuple[dict[str, bytes], dict[str, str], bytes]:
    """Validate every entry before using any content; never call extract()."""
    require(type(raw) is bytes and len(raw) <= MAX_MEMBER_BYTES, "bounded archive bytes")
    bodies: dict[str, bytes] = {}
    modes: dict[str, str] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            require(0 < len(entries) <= MAX_MEMBERS, "bounded nonempty member inventory")
            require(len({entry.filename for entry in entries}) == len(entries), "unique ZIP names")
            require(
                len({entry.filename.casefold() for entry in entries}) == len(entries),
                "portable unique ZIP names",
            )
            require(
                sum(entry.file_size for entry in entries) <= MAX_DECODED_BYTES,
                "bounded decoded inventory",
            )
            for entry in entries:
                require(entry.orig_filename == entry.filename, "unchanged original ZIP name")
                name = safe_name(entry.filename, directory=source and entry.is_dir())
                require(not entry.flag_bits & 1, "unencrypted ZIP member")
                require(
                    entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                    "supported ZIP compression",
                )
                require(entry.file_size <= MAX_MEMBER_BYTES, "bounded member bytes")
                mode = entry.external_attr >> 16
                if source and entry.is_dir():
                    require(
                        entry.file_size == 0
                        and (
                            (entry.create_system == 0 and entry.external_attr == 16)
                            or (entry.create_system == 3 and stat.S_ISDIR(mode))
                        ),
                        "regular Git archive directory",
                    )
                    require(archive.read(entry) == b"", "empty Git archive directory")
                    continue
                require(not entry.is_dir(), "regular payload, not directory")
                if source and entry.create_system == 0:
                    require(entry.external_attr == 0, "regular DOS Git archive member")
                    modes[name] = "100644"
                else:
                    require(
                        entry.create_system == 3
                        and stat.S_ISREG(mode)
                        and stat.S_IMODE(mode) in (0o644, 0o755),
                        "explicit safe regular ZIP mode",
                    )
                    modes[name] = "100755" if mode & 0o111 else "100644"
                body = archive.read(entry)
                require(
                    len(body) == entry.file_size and zlib.crc32(body) == entry.CRC,
                    "member length and CRC",
                )
                bodies[name] = body
            require(archive.testzip() is None, "complete ZIP CRC check")
            return bodies, modes, archive.comment
    except (zipfile.BadZipFile, RuntimeError, OSError, EOFError) as error:
        raise EvidenceBundleError("readable complete bounded ZIP") from error


def git_tree(bodies: Mapping[str, bytes], modes: Mapping[str, str]) -> str:
    """Reconstruct the root Git object from the complete archive, not a claimed hash."""
    root: dict[str, Any] = {}
    for path, body in bodies.items():
        parts = safe_name(path).split("/")
        current = root
        for part in parts[:-1]:
            child = current.setdefault(part, {})
            require(isinstance(child, dict), "no Git file/directory path collision")
            current = child
        require(parts[-1] not in current, "unique Git tree path")
        oid = hashlib.sha1(f"blob {len(body)}\0".encode() + body).digest()
        current[parts[-1]] = (modes[path], oid)

    def tree(node: dict[str, Any]) -> bytes:
        result = bytearray()
        for name, item in sorted(
            node.items(),
            key=lambda pair: (pair[0] + ("/" if isinstance(pair[1], dict) else "")).encode(),
        ):
            mode, oid = ("40000", tree(item)) if isinstance(item, dict) else item
            result.extend(mode.encode() + b" " + name.encode() + b"\0" + oid)
        return hashlib.sha1(f"tree {len(result)}\0".encode() + result).digest()

    return tree(root).hex()


def validate_identity(identity: Any) -> None:
    require(type(identity) is dict and set(identity) == IDENTITY_KEYS, "closed CI identity schema")
    require(identity["repository"] == REPOSITORY, "independent project identity")
    for key in ("source_commit", "source_tree", "reviewed_head_commit"):
        require(
            type(identity[key]) is str and re.fullmatch(r"[0-9a-f]{40}", identity[key]) is not None,
            "Git SHA grammar",
        )
    for key in ("workflow_run_id", "run_attempt"):
        require(
            type(identity[key]) is int and identity[key] > 0, "positive exact CI identity count"
        )
    require(
        identity["workflow_name"] == "Research quality"
        and identity["workflow_path"] == ".github/workflows/ci.yml",
        "exact workflow identity",
    )
    require(
        identity["event"] in ("pull_request", "push")
        and identity["job"] in ("quality", "notebook-publication"),
        "registered CI job and event",
    )
    if identity["event"] == "push":
        require(
            identity["source_commit"] == identity["reviewed_head_commit"],
            "push source/head identity",
        )


def notebook(raw: bytes) -> dict[str, Any]:
    value = strict_json(raw)
    require(
        type(value) is dict
        and value.get("nbformat") == 4
        and type(value.get("metadata")) is dict
        and type(value.get("cells")) is list,
        "native notebook v4 shape",
    )
    require(len(value["cells"]) <= 10_000, "bounded notebook cells")
    for cell in value["cells"]:
        require(
            type(cell) is dict
            and cell.get("cell_type") in ("code", "markdown", "raw")
            and type(cell.get("metadata")) is dict,
            "native cell shape",
        )
        source = cell.get("source")
        if isinstance(source, list):
            require(all(type(item) is str for item in source), "text source lines")
            cell["source"] = "".join(source)
        else:
            require(type(source) is str, "text cell source")
    return value


def definition(value: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    result["metadata"] = {
        key: item
        for key, item in result["metadata"].items()
        if key not in {"language_info", "widgets"}
    }
    for cell in result["cells"]:
        cell.pop("execution_count", None)
        cell.pop("outputs", None)
        cell["metadata"].pop("execution", None)
    return result


def execution_state(value: Mapping[str, Any]) -> list[dict[str, Any]]:
    codes = [cell for cell in value["cells"] if cell["cell_type"] == "code"]
    require(
        bool(codes) and all(type(cell.get("execution_count")) is int for cell in codes),
        "executed code counts, not booleans",
    )
    require(
        [cell["execution_count"] for cell in codes] == list(range(1, len(codes) + 1)),
        "sequential code execution state",
    )
    for cell in codes:
        require(type(cell.get("outputs")) is list, "native code outputs")
        for output in cell["outputs"]:
            require(
                type(output) is dict
                and output.get("output_type") in ("stream", "display_data", "execute_result"),
                "no error or unknown notebook output",
            )
            if output["output_type"] == "stream":
                text = output.get("text", "")
                text = "".join(text) if isinstance(text, list) else text
                require(
                    type(text) is str and not re.search(r"\b[A-Za-z]*Warning:", text),
                    "no unresolved notebook warning",
                )
    return codes


def verify_notebooks(payloads: Mapping[str, bytes], source: Mapping[str, bytes]) -> dict[str, Any]:
    receipt = strict_json(payloads[VALIDATION + "notebook_execution.json"])
    require(receipt.get("status") == "completed", "completed canonical notebook receipt")
    rows = receipt.get("notebooks")
    require(
        type(rows) is list and [row.get("notebook") for row in rows] == list(NOTEBOOKS),
        "six exact ordered canonical notebooks",
    )
    results: list[dict[str, Any]] = []
    all_dependencies: dict[str, str] = {}
    cells_expected: set[tuple[str, int]] = set()
    total_source, total_runtime = 0, 0
    for row in rows:
        require(row.get("status") == "completed", "completed notebook row")
        name, fingerprint = row["notebook"], row.get("fingerprint")
        require(
            type(fingerprint) is str and re.fullmatch(r"[0-9a-f]{64}", fingerprint) is not None,
            "notebook fingerprint grammar",
        )
        body = payloads[VALIDATION + name]
        require(sha256(body) == row.get("sha256"), "canonical notebook receipt body SHA")
        prefix = VALIDATION + f"notebook_runs/{fingerprint}/{PurePosixPath(name).stem}/"
        require(payloads[prefix + name] == body, "checkpoint native notebook equality")
        checkpoint = strict_json(payloads[prefix + "checkpoint.json"])
        require(
            checkpoint.get("fingerprint") == fingerprint
            and type(checkpoint.get("outputs")) is dict
            and set(checkpoint["outputs"]) == {name, "inputs.json"},
            "checkpoint fingerprint and output closure",
        )
        for path, expected in checkpoint["outputs"].items():
            require(sha256(payloads[prefix + path]) == expected, "all checkpoint output bodies")
        inputs = strict_json(payloads[prefix + "inputs.json"])
        require(
            sha256(json.dumps(inputs, sort_keys=True, allow_nan=False).encode()) == fingerprint,
            "recomputed input fingerprint",
        )
        value = notebook(body)
        require(
            definition(value) == inputs.get("notebook"),
            "executed notebook definition matches checkpoint",
        )
        require(
            definition(value) == definition(notebook(source["notebooks/" + name])),
            "executed definition matches reviewed source",
        )
        codes = execution_state(value)
        require(
            type(row.get("code_cells")) is int and row["code_cells"] == len(codes),
            "exact code-cell count",
        )
        cells_expected.update(
            (name, index)
            for index, cell in enumerate(value["cells"])
            if cell["cell_type"] == "code"
        )
        dependencies = inputs.get("dependencies")
        require(type(dependencies) is dict and bool(dependencies), "nonempty declared dependencies")
        source_count = runtime_count = 0
        for path, expected in dependencies.items():
            safe_name(path)
            require(
                type(expected) is str and re.fullmatch(r"[0-9a-f]{64}", expected) is not None,
                "dependency SHA grammar",
            )
            if path in source and sha256(source[path]) == expected:
                source_count += 1
            elif path in payloads and sha256(payloads[path]) == expected:
                runtime_count += 1
            else:
                raise EvidenceBundleError("missing or mismatched declared dependency body: " + path)
        if all_dependencies:
            require(dependencies == all_dependencies, "no cross-notebook dependency drift")
        all_dependencies = dependencies
        total_source += source_count
        total_runtime += runtime_count
        results.append(
            {
                "notebook": name,
                "sha256": sha256(body),
                "fingerprint": fingerprint,
                "code_cells": len(codes),
                "source_dependency_bodies": source_count,
                "runtime_dependency_bodies": runtime_count,
            }
        )
    logs = [strict_json(line) for line in payloads[VALIDATION + "notebooks.jsonl"].splitlines()]
    events = Counter(row.get("event") for row in logs)
    for event in ("cell_started", "cell_finished"):
        pairs = [
            (row.get("notebook"), row.get("cell")) for row in logs if row.get("event") == event
        ]
        require(
            len(pairs) == len(set(pairs)) and set(pairs) == cells_expected,
            "exact cold notebook cell event identities",
        )
    require(
        all(row.get("status") == "ok" for row in logs if row.get("event") == "cell_finished"),
        "all cold cell events successful",
    )
    for event in ("task_started", "task_completed", "task_reused"):
        tasks = [row.get("task") for row in logs if row.get("event") == event]
        require(
            len(tasks) == 6 and set(tasks) == {PurePosixPath(name).stem for name in NOTEBOOKS},
            "cold and warm task identity closure",
        )
    require(
        events["run_started"] == events["run_completed"] == 2,
        "one cold execution and one warm reuse",
    )
    require(
        not any(events[key] for key in ("run_failed", "task_failed", "checkpoint_invalid")),
        "no hidden notebook failure",
    )
    return {
        "notebooks": results,
        "cold_notebooks": 6,
        "cold_code_cells": len(cells_expected),
        "warm_reused_notebooks": 6,
        "distinct_dependency_paths": len(all_dependencies),
        "dependency_associations": total_source + total_runtime,
        "source_dependency_associations": total_source,
        "runtime_dependency_associations": total_runtime,
        "missing_declared_dependency_bodies": 0,
        "event_counts": dict(events),
    }


def verify_runtime(
    payloads: Mapping[str, bytes], source: Mapping[str, bytes], job: str
) -> dict[str, Any]:
    receipt = strict_json(payloads[RUNTIME_RECEIPT])
    require(
        receipt.get("status") == "PASS"
        and type(receipt.get("model_fits")) is int
        and receipt["model_fits"] == 0
        and receipt.get("private_model_reproduced") is False,
        "zero-fit public release receipt scope",
    )
    fields = {
        "notebook_sha256": (RUNTIME_NOTEBOOK, payloads),
        "png_sha256": (RUNTIME_PNG, payloads),
        "evidence_sha256": ("portfolio/release_evidence.json", source),
        "reproducer_sha256": ("portfolio/reproduce_release.py", source),
    }
    require(
        {key for key in receipt if key.endswith("_sha256")} == set(fields),
        "four exact nested receipt pins",
    )
    for field, (path, collection) in fields.items():
        require(sha256(collection[path]) == receipt[field], "nested receipt body: " + field)
    value = notebook(payloads[RUNTIME_NOTEBOOK])
    reviewed = notebook(source[RUNTIME_NOTEBOOK])
    require(
        [(cell["cell_type"], cell["source"]) for cell in value["cells"]]
        == [(cell["cell_type"], cell["source"]) for cell in reviewed["cells"]],
        "five-cell notebook source matches reviewed code and narrative",
    )
    codes = execution_state(value)
    require(
        len(codes) == receipt.get("code_cells") == 5, "five-cell release notebook execution state"
    )
    outputs = [output for cell in codes for output in cell["outputs"]]
    require("VERIFIED_PUBLIC_REVIEW_COMPLETE" in str(outputs), "release notebook completion marker")
    plots = [
        output for output in outputs if "application/vnd.plotly.v1+json" in output.get("data", {})
    ]
    images = [output for output in outputs if "image/png" in output.get("data", {})]
    require(
        len(plots) == receipt.get("plotly_outputs") == 1
        and len(images) == receipt.get("png_outputs") == 1,
        "retained Plotly and PNG pair",
    )
    image = images[0]["data"]["image/png"]
    image = "".join(image) if isinstance(image, list) else image
    try:
        require(
            base64.b64decode(image, validate=True) == payloads[RUNTIME_PNG],
            "native embedded and standalone PNG equality",
        )
    except (ValueError, TypeError) as error:
        raise EvidenceBundleError("valid native PNG base64") from error
    engine = value["metadata"].get("execution_engine")
    require(
        engine == receipt.get("execution_engine")
        and engine in ("jupyter_kernel", "ipython_in_process"),
        "declared execution engine equality",
    )
    if job == "quality":
        require(engine == "jupyter_kernel", "quality job requires real kernel receipt")
    else:
        require(
            all(payloads[path] == source[path] for path in RUNTIME_PATHS),
            "publication job retains exact committed release inputs",
        )
    return {
        "code_cells": 5,
        "nested_pins_verified": 4,
        "missing_nested_bodies": 0,
        "execution_engine": engine,
        "png_matches_embedded_output": True,
        "cell_sources_match_reviewed_notebook": True,
        "origin": "quality job regenerated output"
        if job == "quality"
        else "committed source input, not newly executed",
        "model_fits": 0,
        "notebook_sha256": receipt["notebook_sha256"],
    }


def verify_quality(payloads: Mapping[str, bytes]) -> dict[str, Any]:
    quality = strict_json(payloads[VALIDATION + "quality.json"])
    require(
        [row.get("check") for row in quality.get("checks", [])]
        == ["compile", "lint", "format", "types", "tests"]
        and all(row.get("status") == "passed" for row in quality["checks"]),
        "five quality gates passed",
    )
    raw = payloads[VALIDATION + "junit.xml"]
    require(
        b"<!DOCTYPE" not in raw.upper() and b"<!ENTITY" not in raw.upper(),
        "JUnit without entity declarations",
    )
    try:
        junit = ET.fromstring(raw)
    except ET.ParseError as error:
        raise EvidenceBundleError("parseable JUnit") from error
    suites, cases = junit.findall("testsuite"), junit.findall(".//testcase")
    require(len(suites) == 1 and bool(cases), "one nonempty actual pytest suite")
    counts = {
        "tests": len(cases),
        "failures": len(junit.findall(".//failure")),
        "errors": len(junit.findall(".//error")),
        "skipped": len(junit.findall(".//skipped")),
    }
    require(
        counts["failures"] == counts["errors"] == counts["skipped"] == 0,
        "no failed errored or skipped pytest case",
    )
    require(
        all(suites[0].get(key) == str(value) for key, value in counts.items()),
        "JUnit suite count closure",
    )
    require(
        len({(case.get("classname"), case.get("name")) for case in cases}) == len(cases),
        "unique actual pytest case identities",
    )
    return {
        "gates_passed": 5,
        "junit": counts,
        "coverage_scope": (
            "selected modules only; coverage.xml retained, "
            "not reinterpreted as whole-project coverage"
        ),
    }


def verify_public_bundle(
    bundle_bytes: bytes, external_binding: Mapping[str, Any]
) -> dict[str, Any]:
    """Verify exact externally bound bytes without trusting the manifest as authority."""
    require(
        type(bundle_bytes) is bytes and len(bundle_bytes) < MAX_BUNDLE_BYTES, "bundle below 40 MB"
    )
    binding = dict(external_binding)
    require(
        set(binding) == IDENTITY_KEYS | {"schema", "bytes", "sha256"}
        and binding.get("schema") == BINDING_SCHEMA,
        "closed external binding schema",
    )
    require(
        type(binding["bytes"]) is int
        and binding["bytes"] == len(bundle_bytes)
        and binding["sha256"] == sha256(bundle_bytes),
        "external bundle byte/SHA pin",
    )
    identity = {key: binding[key] for key in IDENTITY_KEYS}
    validate_identity(identity)
    payloads, _, _ = read_zip(bundle_bytes)
    try:
        manifest = strict_json(payloads.pop(MANIFEST))
        require(
            type(manifest) is dict
            and set(manifest) == {"schema", "scope", "identity", "members"}
            and manifest["schema"] == SCHEMA
            and manifest["scope"] == SCOPE,
            "closed public manifest schema and scope",
        )
        require(manifest["identity"] == identity, "externally bound CI run/head/tree identity")
        rows = manifest["members"]
        require(
            type(rows) is list and [row.get("name") for row in rows] == sorted(payloads),
            "exact sorted manifest payload closure",
        )
        for row in rows:
            require(
                type(row) is dict and set(row) == {"name", "bytes", "sha256", "crc32"},
                "closed manifest member schema",
            )
            require(
                type(row["bytes"]) is int
                and row == {"name": row["name"], **pin(payloads[row["name"]])},
                "every manifest member byte/CRC/SHA",
            )
        require(
            set(payloads) - {name for name in payloads if name.startswith(VALIDATION)}
            == set(RUNTIME_PATHS),
            "only registered public runtime bodies",
        )
        commit = identity["source_commit"]
        require(
            payloads[VALIDATION + "source_commit.txt"] == (commit + "\n").encode(),
            "exact checked source commit",
        )
        source_raw = payloads[VALIDATION + "source.zip"]
        require(
            payloads[VALIDATION + "source.sha256"]
            == (sha256(source_raw) + "  outputs/validation/source.zip\n").encode(),
            "source archive SHA receipt",
        )
        source, modes, comment = read_zip(source_raw, source=True)
        require(comment == commit.encode(), "Git archive source commit comment")
        require(
            git_tree(source, modes) == identity["source_tree"],
            "complete reconstructed reviewed Git tree",
        )
        require(identity["workflow_path"] in source, "workflow body retained in reviewed tree")
        canonical_report = verify_notebooks(payloads, source)
        allowed = set(RUNTIME_PATHS) | {VALIDATION + name for name in VALIDATION_FILES}
        for row in canonical_report["notebooks"]:
            name, fingerprint = row["notebook"], row["fingerprint"]
            prefix = VALIDATION + f"notebook_runs/{fingerprint}/{PurePosixPath(name).stem}/"
            allowed.update(
                {
                    VALIDATION + name,
                    prefix + name,
                    prefix + "inputs.json",
                    prefix + "checkpoint.json",
                }
            )
        require(set(payloads) <= allowed, "finite registered validation payload paths")
        runtime_report = verify_runtime(payloads, source, identity["job"])
        quality_report = verify_quality(payloads) if identity["job"] == "quality" else None
    except (KeyError, TypeError, AttributeError, IndexError) as error:
        raise EvidenceBundleError(
            "required body or field missing/invalid: " + type(error).__name__
        ) from error
    return {
        "schema": "MARCH_PUBLIC_CI_VERIFICATION_V1",
        "status": "PASS",
        "binding": binding,
        "payload_members": len(payloads),
        "payload_decoded_bytes": sum(map(len, payloads.values())),
        "safe_unique_regular_members": True,
        "exact_manifest_closure": True,
        "all_member_crc_bytes_sha_verified": True,
        "source_files": len(source),
        "source_sha256": sha256(source_raw),
        "source_tree_reconstructed": identity["source_tree"],
        "canonical_notebooks": canonical_report,
        "verified_result": runtime_report,
        "quality": quality_report,
        "notebooks_executed_by_verifier": 0,
        "model_fits_by_verifier": 0,
        "scoring_by_verifier": 0,
        "network_calls_by_verifier": 0,
        "limits": [
            "Expected bindings must come from independently trusted CI/API evidence; "
            "this is not a signature or authorship proof.",
            "Native outputs and exact declared dependencies are checked; "
            "cell code is not executed by this verifier.",
            "Public synthetic and aggregate evidence does not reproduce "
            "the private competitive pipeline.",
        ],
    }


def build_public_bundle(
    payloads: Mapping[str, bytes], identity: Mapping[str, Any]
) -> tuple[bytes, dict[str, Any]]:
    """Seal collected public outputs, then verify the exact final bytes before release."""
    validate_identity(dict(identity))
    require(MANIFEST not in payloads and bool(payloads), "no self-manifest input")
    manifest = {
        "schema": SCHEMA,
        "scope": SCOPE,
        "identity": dict(identity),
        "members": [
            {"name": safe_name(name), **pin(body)} for name, body in sorted(payloads.items())
        ],
    }
    bodies = {**payloads, MANIFEST: canonical(manifest)}
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, body in sorted(bodies.items()):
            require(type(body) is bytes, "byte-only bundle payload")
            entry = zipfile.ZipInfo(safe_name(name), date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, body)
    raw = stream.getvalue()
    binding = {"schema": BINDING_SCHEMA, "bytes": len(raw), "sha256": sha256(raw), **identity}
    verify_public_bundle(raw, binding)
    return raw, binding
