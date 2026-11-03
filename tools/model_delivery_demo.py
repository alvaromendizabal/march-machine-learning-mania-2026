"""Export and reload the frozen PUBLIC SYNTHETIC models; never fit a new model.

`demo` reconstructs public feature rows and verifies detached inference against
the committed predictions. `predict` reads only a pinned JSON model and an
explicit labels-free request. There is no HTTP service or deployment claim.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from march_mania.public_reference import (  # noqa: E402
    DISCLOSURE,
    FEATURE_NAMES,
    MAX_MODEL_BYTES,
    MAX_REQUEST_BYTES,
    MODEL_SCHEMA,
    REQUEST_SCHEMA,
    SCOPE,
    canonical,
    decode_json,
    exact_keys,
    load_model,
    pin,
    predict_bytes,
    require,
)

SOURCE = ROOT / "examples/temporal_model_demo"
REFERENCE_PAYLOADS = {
    "synthetic_fixture.json",
    "synthetic_fits.json",
    "predictions.json",
    "evaluation.json",
    "calibration.svg",
}


def read_bounded(path: Path, maximum: int) -> bytes:
    require(
        path.is_file() and not path.is_symlink(), "A regular, nonsymlink input file is required"
    )
    with path.open("rb") as handle:
        raw = handle.read(maximum + 1)
    require(0 < len(raw) <= maximum, "Input file byte bound")
    return raw


def write_new(path: Path, raw: bytes) -> None:
    """Never overwrite an input, symlink, existing result, or unrelated file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)


def load_public_reference() -> tuple[dict[str, bytes], dict[str, Any]]:
    manifest = decode_json(read_bounded(SOURCE / "manifest.json", 65_536), 65_536)
    require(
        isinstance(manifest, dict) and manifest.get("schema_version") == 1,
        "Reference manifest schema",
    )
    require(
        manifest.get("evidence_scope") == SCOPE and manifest.get("owner_research_fits") == 0,
        "Reference evidence scope",
    )
    require(set(manifest.get("payloads", {})) == REFERENCE_PAYLOADS, "Reference payload closure")
    generator = read_bounded(ROOT / "tools/temporal_model_demo.py", 1_048_576)
    require(pin(generator) == manifest["generator_pin"], "Reference generator hash changed")
    files = {}
    for name in sorted(REFERENCE_PAYLOADS):
        raw = read_bounded(SOURCE / name, 1_048_576)
        require(pin(raw) == manifest["payloads"][name], "Reference artifact pin changed")
        files[name] = raw
    return files, manifest


def export_model(fit: dict[str, Any], manifest: dict[str, Any]) -> bytes:
    """Translate one fixed public fit receipt into a narrowly typed serving model."""
    exact_keys(
        fit,
        {
            "evaluation_season",
            "evidence_scope",
            "model",
            "feature_names",
            "coefficients",
            "intercept",
            "scaler",
            "fit_completed_at_utc",
            "fit_time_is_authored_fixture_clock_not_wall_clock",
            "training_seasons",
            "latest_training_label_available_at_utc",
            "physical_training_ids",
            "training_input_pin",
            "optimizer",
        },
        "public fit receipt",
    )
    require(
        fit["evidence_scope"] == SCOPE
        and fit["model"] == "ACTUALLY_FITTED_SYNTHETIC_L2_LOGISTIC_REGRESSION"
        and fit["feature_names"] == list(FEATURE_NAMES),
        "Public fit identity",
    )
    scaler = fit["scaler"]
    require(
        scaler["fitted_on"] == "TRAINING_SYMMETRIC_PAIRS_ONLY"
        and scaler["physical_training_games"] == len(fit["physical_training_ids"])
        and scaler["augmented_training_rows"] == 2 * len(fit["physical_training_ids"])
        and scaler["weight_per_augmented_row"] == 0.5,
        "Training population contract",
    )
    value = {
        "schema": MODEL_SCHEMA,
        "evidence_scope": SCOPE,
        "disclosure": DISCLOSURE,
        "model": {
            "family": "L2_LOGISTIC_ZERO_INTERCEPT",
            "feature_names": fit["feature_names"],
            "coefficients": fit["coefficients"],
            "intercept": fit["intercept"],
            "scaler": {name: scaler[name] for name in ("mean", "scale")},
        },
        "lineage": {
            "evaluation_season": fit["evaluation_season"],
            "training_seasons": fit["training_seasons"],
            "physical_training_ids": sorted(fit["physical_training_ids"]),
            "physical_training_games": len(fit["physical_training_ids"]),
            "fit_completed_at_utc": fit["fit_completed_at_utc"],
            "fit_clock_is_authored_not_wall_clock": fit[
                "fit_time_is_authored_fixture_clock_not_wall_clock"
            ],
            "latest_training_label_available_at_utc": fit["latest_training_label_available_at_utc"],
            "training_input_pin": fit["training_input_pin"],
            "public_generator_pin": manifest["generator_pin"],
            "public_fits_pin": manifest["payloads"]["synthetic_fits.json"],
        },
    }
    raw = canonical(value)
    load_model(raw, pin(raw)["sha256"])
    return raw


def build_demo_files() -> tuple[dict[str, bytes], dict[str, Any]]:
    files, manifest = load_public_reference()
    spec = importlib.util.spec_from_file_location(
        "public_temporal_feature_producer", ROOT / "tools/temporal_model_demo.py"
    )
    require(spec is not None and spec.loader is not None, "Public feature producer unavailable")
    generator = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(generator)  # type: ignore[union-attr]
    fixture = decode_json(files["synthetic_fixture.json"], 1_048_576)
    features, unused = generator.build_features(
        fixture["games"], fixture["observations"], fixture["cutoffs_utc"]
    )
    fits = decode_json(files["synthetic_fits.json"], 1_048_576)
    reference = decode_json(files["predictions.json"], 1_048_576)
    require(fits["evidence_scope"] == reference["evidence_scope"] == SCOPE, "Reference scope")
    require(
        [fit["evaluation_season"] for fit in fits["fits"]] == [2024, 2025, 2026],
        "Exactly the three existing frozen folds are required",
    )
    produced, folds, differences = {}, [], []
    for fit in fits["fits"]:
        season = fit["evaluation_season"]
        model_raw = export_model(fit, manifest)
        model_pin = pin(model_raw)
        request = {
            "schema": REQUEST_SCHEMA,
            "evidence_scope": SCOPE,
            "rows": [row for row in features if row["season"] == season],
        }
        request_raw = canonical(request)
        response_raw = predict_bytes(model_raw, model_pin["sha256"], request_raw)
        response = decode_json(response_raw, 1_048_576)
        expected = [row for row in reference["forecasts"] if row["season"] == season]
        require(
            canonical(response["predictions"]) == canonical(expected),
            "Detached model predictions differ from the frozen public reference",
        )
        differences.extend(
            abs(a["pred"] - b["pred"])
            for a, b in zip(response["predictions"], expected, strict=True)
        )
        for name, raw in (
            ("model.json", model_raw),
            ("request.json", request_raw),
            ("response.json", response_raw),
        ):
            produced[f"folds/{season}/{name}"] = raw
        folds.append(
            {
                "evaluation_season": season,
                "predictions_checked": len(expected),
                "model_pin": model_pin,
                "request_pin": pin(request_raw),
                "response_pin": pin(response_raw),
                "exact_prediction_parity": True,
            }
        )
    return produced, {
        "schema": "march.synthetic.delivery.receipt.v1",
        "status": "PASS",
        "scope": SCOPE,
        "model_count": len(folds),
        "predictions_checked": len(differences),
        "exact_prediction_parity": True,
        "maximum_absolute_probability_difference": max(differences),
        "new_model_fits": 0,
        "network_requests": 0,
        "private_inputs_read": 0,
        "inference_loaded_training_module": False,
        "producer_imports_public_generator_for_features_only": True,
        "producer_fits_or_rescores_models": False,
        "delivery_source_pin": pin(Path(__file__).read_bytes()),
        "inference_source_pin": pin((ROOT / "src/march_mania/public_reference.py").read_bytes()),
        "fit_clock_scope": "AUTHORED_FIXTURE_CLOCKS_NOT_HISTORICAL_AVAILABILITY_PROOF",
        "hash_scope": "CONTENT_IDENTITY_NOT_AUTHORSHIP_OR_HISTORICAL_TIMESTAMP",
        "service_scope": "OFFLINE_BATCH_REFERENCE_NOT_DEPLOYED_PRODUCTION_SERVICE",
        "folds": folds,
    }


def fresh_process_check(files: dict[str, bytes]) -> dict[str, Any]:
    """Run inference with trainer, source fixtures, labels and site packages absent."""
    with tempfile.TemporaryDirectory(prefix="march-public-inference-") as name:
        root = Path(name)
        for source, target in (
            (Path(__file__), root / "tools/model_delivery_demo.py"),
            (
                ROOT / "src/march_mania/public_reference.py",
                root / "src/march_mania/public_reference.py",
            ),
            (ROOT / "src/march_mania/__init__.py", root / "src/march_mania/__init__.py"),
        ):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        require(
            not (root / "tools/temporal_model_demo.py").exists()
            and not (root / "examples").exists(),
            "Isolation fixture includes training inputs",
        )
        predicted = 0
        for season in (2024, 2025, 2026):
            prefix = f"folds/{season}/"
            for field in ("model.json", "request.json"):
                write_new(root / prefix / field, files[prefix + field])
            model_pin = pin(files[prefix + "model.json"])
            command = [
                sys.executable,
                "-I",
                "-S",
                str(root / "tools/model_delivery_demo.py"),
                "predict",
                "--model",
                str(root / prefix / "model.json"),
                "--expected-sha256",
                model_pin["sha256"],
                "--request",
                str(root / prefix / "request.json"),
                "--output",
                str(root / prefix / "response.json"),
            ]
            result = subprocess.run(
                command,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=20,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            require(result.returncode == 0, "Isolated inference subprocess failed")
            require(
                (root / prefix / "response.json").read_bytes() == files[prefix + "response.json"],
                "Fresh-process inference bytes differ",
            )
            child = json.loads(result.stdout)
            require(
                child["status"] == "PASS" and child["new_model_fits"] == 0,
                "Unexpected subprocess receipt",
            )
            require(
                child["runtime_contract"]
                == {
                    "trainer_imported": False,
                    "third_party_model_packages_imported": False,
                    "python_isolated": True,
                    "python_no_site": True,
                },
                "Fresh inference process imported training or third-party runtime",
            )
            predicted += child["physical_games"]
        return {
            "status": "PASS",
            "isolated_processes": 3,
            "predictions_checked": predicted,
            "site_packages_enabled": False,
            "trainer_or_fixtures_present": False,
            "exact_response_bytes_match": True,
            "new_model_fits": 0,
        }


def run_demo(output: Path | None = None) -> dict[str, Any]:
    files, receipt = build_demo_files()
    receipt["fresh_process_test"] = fresh_process_check(files)
    files["receipt.json"] = canonical(receipt)
    files["manifest.json"] = canonical(
        {
            "schema": "march.synthetic.delivery.files.v1",
            "evidence_scope": SCOPE,
            "payloads": {name: pin(raw) for name, raw in sorted(files.items())},
            "closure": "Exactly the ten named payloads; manifest excludes its own hash",
        }
    )
    if output is not None:
        if output.exists() or output.is_symlink():
            # An identical run is a read-only verification, never a silent refresh.
            require(output.is_dir() and not output.is_symlink(), "Unsafe output directory")
            actual: set[str] = set()
            for path in output.rglob("*"):
                require(not path.is_symlink(), "Symlink in existing demo output")
                if not path.is_dir():
                    require(path.is_file(), "Nonregular existing demo output")
                    actual.add(path.relative_to(output).as_posix())
            require(actual == set(files), "Existing demo output has incomplete or extra payloads")
            for name, raw in files.items():
                require(
                    read_bounded(output / name, len(raw)) == raw,
                    "Existing demo bytes differ; choose a new output directory",
                )
        else:
            output.mkdir(parents=True, exist_ok=False)
            for name, raw in files.items():
                write_new(output / name, raw)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser(
        "demo", help="Verify all frozen synthetic models without refitting"
    )
    demo.add_argument("--out-dir", type=Path, default=ROOT / "outputs/model-delivery")
    predict = subparsers.add_parser(
        "predict", help="Labels-free inference from a pinned JSON model"
    )
    predict.add_argument("--model", type=Path, required=True)
    predict.add_argument("--expected-sha256", required=True)
    predict.add_argument("--request", type=Path, required=True)
    predict.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            receipt = run_demo(args.out_dir)
        else:
            raw = predict_bytes(
                read_bounded(args.model, MAX_MODEL_BYTES),
                args.expected_sha256,
                read_bounded(args.request, MAX_REQUEST_BYTES),
            )
            write_new(args.output, raw)
            result = decode_json(raw, MAX_REQUEST_BYTES)
            receipt = {
                "status": "PASS",
                "scope": SCOPE,
                "physical_games": result["physical_games"],
                "new_model_fits": 0,
                "model_sha256": result["model_sha256"],
                "response_pin": pin(raw),
                "runtime_contract": {
                    "trainer_imported": any(
                        name in sys.modules
                        for name in ("temporal_model_demo", "public_temporal_feature_producer")
                    ),
                    "third_party_model_packages_imported": any(
                        name in sys.modules
                        for name in ("numpy", "pandas", "sklearn", "torch", "tensorflow")
                    ),
                    "python_isolated": bool(sys.flags.isolated),
                    "python_no_site": bool(sys.flags.no_site),
                },
            }
        print(json.dumps(receipt, sort_keys=True))
        return 0
    except (ValueError, OSError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        # Input data, local paths and exceptions from subprocesses are not reflected.
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error_type": type(exc).__name__,
                    "output_not_authoritative": True,
                }
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
