"""Fail-closed, data-only delivery for the authored synthetic logistic example.

This module neither trains nor opens files, imports the trainer, loads pickle,
uses network services, or implements the private competition inference system.
An expected SHA verifies content identity, not authorship or a historical clock.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, cast

SCOPE = "SYNTHETIC_ONLY"
MODEL_SCHEMA = "march.synthetic.logistic.delivery.v1"
REQUEST_SCHEMA = "march.synthetic.inference.batch.v1"
RESPONSE_SCHEMA = "march.synthetic.inference.result.v1"
FEATURE_NAMES = ("rating_difference", "form_difference", "rest_days_difference")
FEATURE_LIMITS = (2000.0, 6.0, 14.0)
MAX_MODEL_BYTES = 524_288
MAX_REQUEST_BYTES = 1_048_576
MAX_BATCH_ROWS = 512
MAX_TRAINING_GAMES = 2048
DISCLOSURE = "PUBLIC_SYNTHETIC_REFERENCE_NOT_COMPETITION_MODEL"
MODEL_KEYS = {"schema", "evidence_scope", "disclosure", "model", "lineage"}
PARAMETER_KEYS = {"family", "feature_names", "coefficients", "intercept", "scaler"}
LINEAGE_KEYS = {
    "evaluation_season",
    "training_seasons",
    "physical_training_ids",
    "physical_training_games",
    "fit_completed_at_utc",
    "fit_clock_is_authored_not_wall_clock",
    "latest_training_label_available_at_utc",
    "training_input_pin",
    "public_generator_pin",
    "public_fits_pin",
}
GAME_KEYS = {"scope", "id", "season", "started_at_utc", "team_a", "team_b"}
ROW_KEYS = GAME_KEYS | {"forecast_at_utc", "feature_available_at_utc", "features"}
ID_PATTERN = re.compile(r"synthetic_([0-9]{4})_r[0-9]{2}_g[0-9]{2}\Z")
TEAM_PATTERN = re.compile(r"FICTIONAL_(?:0[1-9]|1[0-2])\Z")
UTC_PATTERN = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z\Z"
)
SHA_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def pin(raw: bytes) -> dict[str, Any]:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def exact_keys(value: object, keys: set[str], name: str) -> dict[str, Any]:
    require(type(value) is dict and set(value) == keys, "Invalid " + name + " fields")
    return value  # type: ignore[return-value]


def literal(value: object, expected: object, name: str) -> None:
    require(type(value) is type(expected) and value == expected, "Invalid " + name)


def number(value: object, name: str, lower: float, upper: float) -> float:
    require(type(value) in (int, float), "Invalid numeric " + name)
    try:
        result = float(value)  # type: ignore[arg-type]
    except (OverflowError, ValueError) as exc:
        raise ValueError("Invalid numeric " + name) from exc
    require(math.isfinite(result) and lower <= result <= upper, "Out-of-range " + name)
    return result


def integer(value: object, name: str, lower: int, upper: int) -> int:
    require(type(value) is int and lower <= value <= upper, "Invalid integer " + name)  # type: ignore[operator]
    return value  # type: ignore[return-value]


def utc(value: object, name: str) -> datetime:
    require(isinstance(value, str) and UTC_PATTERN.fullmatch(value) is not None, "Invalid " + name)
    try:
        return datetime.fromisoformat(cast(str, value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid " + name) from exc


def identifier(value: object) -> str:
    require(
        isinstance(value, str) and ID_PATTERN.fullmatch(value) is not None, "Invalid synthetic ID"
    )
    return value  # type: ignore[return-value]


def sha256_text(value: object) -> str:
    require(isinstance(value, str) and SHA_PATTERN.fullmatch(value) is not None, "Invalid SHA-256")
    return value  # type: ignore[return-value]


def validate_pin(value: object, name: str) -> None:
    item = exact_keys(value, {"bytes", "sha256"}, name)
    integer(item["bytes"], name + " byte count", 1, 16_777_216)
    sha256_text(item["sha256"])


def decode_json(raw: bytes, maximum_bytes: int) -> Any:
    require(type(raw) is bytes and 0 < len(raw) <= maximum_bytes, "JSON byte bound")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, value in items:
            require(name not in result, "Duplicate JSON key")
            result[name] = value
        return result

    def constant(unused: str) -> None:
        raise ValueError("Nonfinite JSON constant")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("Invalid complete UTF-8 JSON document") from exc


@dataclass(frozen=True)
class ReferenceModel:
    """Only immutable, fully validated serving values cross the load boundary."""

    artifact_sha256: str
    coefficients: tuple[float, ...]
    scale: tuple[float, ...]
    evaluation_season: int
    training_seasons: tuple[int, ...]
    physical_training_ids: frozenset[str]
    fit_completed_at: datetime


def load_model(raw: bytes, expected_sha256: str) -> ReferenceModel:
    """Verify caller-supplied content identity, then all closed model contracts."""
    expected = sha256_text(expected_sha256)
    require(type(raw) is bytes and 0 < len(raw) <= MAX_MODEL_BYTES, "Model byte bound")
    require(
        hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected), "Model SHA-256 mismatch"
    )
    bundle = exact_keys(decode_json(raw, MAX_MODEL_BYTES), MODEL_KEYS, "model bundle")
    literal(bundle["schema"], MODEL_SCHEMA, "model schema version")
    literal(bundle["evidence_scope"], SCOPE, "model evidence scope")
    literal(bundle["disclosure"], DISCLOSURE, "model disclosure")
    params = exact_keys(bundle["model"], PARAMETER_KEYS, "model parameters")
    literal(params["family"], "L2_LOGISTIC_ZERO_INTERCEPT", "model family")
    require(
        type(params["feature_names"]) is list and params["feature_names"] == list(FEATURE_NAMES),
        "Feature name/order contract",
    )
    number(params["intercept"], "intercept", 0, 0)
    require(
        type(params["coefficients"]) is list and len(params["coefficients"]) == 3,
        "Coefficient shape",
    )
    coefficients = tuple(number(v, "coefficient", -100, 100) for v in params["coefficients"])
    scaler = exact_keys(params["scaler"], {"mean", "scale"}, "scaler")
    require(type(scaler["mean"]) is list and len(scaler["mean"]) == 3, "Scaler mean shape")
    for value in scaler["mean"]:
        number(value, "symmetric scaler mean", 0, 0)
    require(type(scaler["scale"]) is list and len(scaler["scale"]) == 3, "Scaler SD shape")
    scales = tuple(number(v, "scaler SD", 1e-12, 10_000) for v in scaler["scale"])
    lineage = exact_keys(bundle["lineage"], LINEAGE_KEYS, "model lineage")
    evaluation = integer(lineage["evaluation_season"], "evaluation season", 1900, 2100)
    training = lineage["training_seasons"]
    require(type(training) is list and 0 < len(training) <= 100, "Training season list")
    years = [integer(v, "training season", 1900, evaluation - 1) for v in training]
    require(years == sorted(set(years)), "Training seasons must be unique and sorted")
    identities = lineage["physical_training_ids"]
    count = integer(lineage["physical_training_games"], "training games", 1, MAX_TRAINING_GAMES)
    require(type(identities) is list and len(identities) == count, "Training ID/count contract")
    ids = [identifier(value) for value in identities]
    require(ids == sorted(set(ids)), "Training IDs must be unique and sorted")
    require(all(int(value.split("_")[1]) in years for value in ids), "Training ID season conflict")
    require(
        {int(value.split("_")[1]) for value in ids} == set(years), "Unrepresented training season"
    )
    fitted = utc(lineage["fit_completed_at_utc"], "fit clock")
    available = utc(lineage["latest_training_label_available_at_utc"], "training label clock")
    require(
        fitted.year == evaluation and available.year in years and available < fitted,
        "Training label/fit/evaluation chronology",
    )
    literal(lineage["fit_clock_is_authored_not_wall_clock"], True, "authored clock disclosure")
    for name in ("training_input_pin", "public_generator_pin", "public_fits_pin"):
        validate_pin(lineage[name], name)
    return ReferenceModel(
        expected, coefficients, scales, evaluation, tuple(years), frozenset(ids), fitted
    )


def validate_request(raw: bytes, model: ReferenceModel) -> list[dict[str, Any]]:
    request = exact_keys(
        decode_json(raw, MAX_REQUEST_BYTES),
        {"schema", "evidence_scope", "rows"},
        "request; evaluation labels and extra metadata are forbidden",
    )
    literal(request["schema"], REQUEST_SCHEMA, "request schema version")
    literal(request["evidence_scope"], SCOPE, "request evidence scope")
    rows = request["rows"]
    require(type(rows) is list and 0 < len(rows) <= MAX_BATCH_ROWS, "Inference batch row bound")
    seen_ids, seen_games = set(), set()
    for value in rows:
        row = exact_keys(value, ROW_KEYS, "feature row; labels are forbidden")
        literal(row["scope"], SCOPE, "row scope")
        identity = identifier(row["id"])
        require(
            identity not in seen_ids and identity not in model.physical_training_ids,
            "Duplicate or training game ID",
        )
        seen_ids.add(identity)
        season = integer(row["season"], "inference season", 1900, 2100)
        require(
            season == model.evaluation_season == int(identity.split("_")[1]),
            "Inference season does not match pinned model",
        )
        a, b = row["team_a"], row["team_b"]
        require(
            all(isinstance(t, str) and TEAM_PATTERN.fullmatch(t) is not None for t in (a, b))
            and a != b,
            "Invalid fictional team pair",
        )
        start = utc(row["started_at_utc"], "game clock")
        forecast = utc(row["forecast_at_utc"], "forecast clock")
        available = utc(row["feature_available_at_utc"], "feature availability clock")
        require(
            start.year == forecast.year == available.year == season, "Row clock/season conflict"
        )
        require(
            model.fit_completed_at < forecast and available <= forecast,
            "Model or feature unavailable at forecast",
        )
        require(start - forecast >= timedelta(hours=1), "Forecast must precede game by at least 1h")
        physical = (season, start, *sorted((a, b)))
        require(physical not in seen_games, "Duplicate physical game, including swapped teams")
        seen_games.add(physical)
        require(type(row["features"]) is list and len(row["features"]) == 3, "Feature vector shape")
        for feature, limit in zip(row["features"], FEATURE_LIMITS, strict=True):
            number(feature, "authored feature range", -limit, limit)
    return rows


def predict_bytes(model_raw: bytes, expected_sha256: str, request_raw: bytes) -> bytes:
    """All-or-nothing, labels-free inference from exact data-only model bytes."""
    model = load_model(model_raw, expected_sha256)
    rows = validate_request(request_raw, model)
    predictions = []
    for row in rows:
        logit = math.fsum(
            float(value) / scale * coefficient
            for value, scale, coefficient in zip(
                row["features"], model.scale, model.coefficients, strict=True
            )
        )
        if logit >= 0:
            probability = 1 / (1 + math.exp(-logit))
        else:
            exp_value = math.exp(logit)
            probability = exp_value / (1 + exp_value)
        predictions.append({key: row[key] for key in GAME_KEYS} | {"pred": probability})
    return canonical(
        {
            "schema": RESPONSE_SCHEMA,
            "evidence_scope": SCOPE,
            "model_sha256": model.artifact_sha256,
            "request_sha256": hashlib.sha256(request_raw).hexdigest(),
            "evaluation_season": model.evaluation_season,
            "physical_games": len(predictions),
            "new_model_fits": 0,
            "prediction_kind": "LOADED_SYNTHETIC_REFERENCE_NOT_REAL_GAME_FORECAST",
            "predictions": predictions,
        }
    )
