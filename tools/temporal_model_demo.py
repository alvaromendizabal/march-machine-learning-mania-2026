"""Train and audit a small temporal probability model on authored fictional data.

This standard-library teaching example is deliberately independent of the private
competition implementation. It performs real numerical fitting, but every input,
outcome, fitted coefficient and score is SYNTHETIC_ONLY, never NCAA evidence.
The older tools/reproduce_public.py example remains an unfitted rating baseline.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "examples" / "temporal_model_demo"
SCOPE = "SYNTHETIC_ONLY"
SEED = 2026
FEATURE_NAMES = ("rating_difference", "form_difference", "rest_days_difference")
GAME_KEYS = {"scope", "id", "season", "started_at_utc", "team_a", "team_b"}
FEATURE_KEYS = GAME_KEYS | {"forecast_at_utc", "feature_available_at_utc", "features"}
LABEL_KEYS = {"scope", "id", "outcome_a", "available_at_utc"}
OBSERVATION_KEYS = {"season", "team", "published_at_utc", "rating", "form", "rest_days"}
LOG_EPSILON = 1e-15
PROTOCOL = {
    "model": "L2 logistic regression with zero intercept and symmetric training augmentation",
    "evaluation_seasons": [2024, 2025, 2026],
    "iterations": 250,
    "learning_rate": 0.12,
    "l2_penalty": 0.04,
    "calibration_bins": 5,
    "selection": "Fixed teaching configuration; no evaluation-season tuning or search",
    "training": "Expanding earlier seasons; labels available strictly before fit time",
    "scaling": "Mean and population SD fitted on symmetric training pairs only",
    "mirrors": "Original and team-swapped rows each weight one half; one physical-game unit",
    "scope": SCOPE,
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def pin(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def exact_keys(value: dict, keys: set[str], name: str) -> None:
    require(isinstance(value, dict) and set(value) == keys, f"Invalid {name} fields")


def utc(value: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), "Timestamp requires explicit UTC Z")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid UTC timestamp") from exc
    require(stamp.tzinfo is not None and stamp.utcoffset() == timedelta(0), "Non-UTC timestamp")
    return stamp


def stamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def numeric(value: object, name: str) -> float:
    require(type(value) in (int, float) and math.isfinite(value), f"Nonfinite or invalid {name}")
    return float(value)


def uniform(seed: int, key: str) -> float:
    value = int.from_bytes(hashlib.sha256(f"{seed}:{key}".encode()).digest()[:6], "big")
    return (value + 0.5) / 2**48


def sigmoid(value: float) -> float:
    require(math.isfinite(value), "Nonfinite model logit")
    if value >= 0:
        return 1 / (1 + math.exp(-value))
    exponent = math.exp(value)
    return exponent / (1 + exponent)


def make_fixture(seed: int = SEED) -> dict:
    """Create six round-robin seasons; these dates and teams describe no real games."""
    require(type(seed) is int and 0 <= seed < 2**32, "Seed must be an unsigned integer")
    teams = [f"FICTIONAL_{i:02d}" for i in range(1, 13)]
    observations, games, labels, cutoffs = [], [], [], {}
    for season in range(2021, 2027):
        cutoffs[str(season)] = f"{season}-03-17T00:00:00Z"
        latent = {
            team: {
                "strength": 2 * uniform(seed, f"{season}:{team}:strength") - 1,
                "form": 2 * uniform(seed, f"{season}:{team}:form") - 1,
                "rest_days": 2 + 4 * uniform(seed, f"{season}:{team}:rest"),
            }
            for team in teams
        }
        for team in teams:
            for day in (14, 16, 18):
                state = latent[team]
                noise = uniform(seed, f"{season}:{team}:{day}:noise") - 0.5
                observations.append(
                    {
                        "season": season,
                        "team": team,
                        "published_at_utc": f"{season}-03-{day:02d}T12:00:00Z",
                        "rating": round(1500 + 250 * state["strength"] + 45 * noise, 8),
                        "form": round(state["form"] + 0.15 * noise, 8),
                        "rest_days": round(state["rest_days"] + 0.2 * noise, 8),
                    }
                )
        rotation = list(teams)
        for round_index in range(11):
            for pair in range(6):
                a, b = rotation[pair], rotation[-pair - 1]
                identity = f"synthetic_{season}_r{round_index + 1:02d}_g{pair + 1:02d}"
                if uniform(seed, identity + ":orientation") < 0.5:
                    a, b = b, a
                start = f"{season}-03-{18 + round_index:02d}T17:00:00Z"
                games.append(
                    {
                        "scope": SCOPE,
                        "id": identity,
                        "season": season,
                        "started_at_utc": start,
                        "team_a": a,
                        "team_b": b,
                    }
                )
                difference = {
                    key: latent[a][key] - latent[b][key]
                    for key in ("strength", "form", "rest_days")
                }
                # Transparent authored generator, unrelated to any private feature recipe.
                probability = sigmoid(
                    1.5 * difference["strength"]
                    + 0.55 * difference["form"]
                    + 0.12 * difference["rest_days"]
                )
                labels.append(
                    {
                        "scope": SCOPE,
                        "id": identity,
                        "outcome_a": int(uniform(seed, identity + ":outcome") < probability),
                        "available_at_utc": stamp(utc(start) + timedelta(hours=3)),
                    }
                )
            rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
    return {
        "schema_version": 1,
        "evidence_scope": SCOPE,
        "seed": seed,
        "description": "Authored fictional observations and labels; not NCAA data or results.",
        "cutoffs_utc": cutoffs,
        "observations": observations,
        "games": games,
        "labels": labels,
    }


def validate_games(games: list[dict], cutoffs: dict[str, str]) -> None:
    require(isinstance(games, list) and bool(games), "Missing games")
    require(isinstance(cutoffs, dict) and bool(cutoffs), "Missing cutoffs")
    for season, value in cutoffs.items():
        require(isinstance(season, str) and season.isdigit(), "Invalid cutoff season")
        require(utc(value).year == int(season), "Cutoff year differs from season")
    ids, physical = set(), set()
    for game in games:
        exact_keys(game, GAME_KEYS, "game")
        require(game["scope"] == SCOPE, "Only explicitly synthetic rows are allowed")
        require(isinstance(game["id"], str) and game["id"].startswith("synthetic_"), "Invalid ID")
        require(game["id"] not in ids, "Duplicate game ID")
        ids.add(game["id"])
        year = game["season"]
        require(type(year) is int and str(year) in cutoffs, "Unknown integer season")
        a, b = game["team_a"], game["team_b"]
        require(
            all(isinstance(t, str) and t.startswith("FICTIONAL_") for t in (a, b)) and a != b,
            "Invalid fictional team pair",
        )
        start, cutoff = utc(game["started_at_utc"]), utc(cutoffs[str(year)])
        require(start.year == year, "Game year differs from season")
        require(start - cutoff >= timedelta(hours=1), "Forecast cutoff must precede game by 1h")
        identity = (year, start, *sorted((a, b)))
        require(identity not in physical, "Duplicate physical game, including team swaps")
        physical.add(identity)


def build_features(games: list[dict], observations: list[dict], cutoffs: dict) -> tuple[list, dict]:
    """Build pre-cutoff differences; this function has no labels argument."""
    validate_games(games, cutoffs)
    require(isinstance(observations, list) and bool(observations), "Missing observations")
    selected, seen, excluded = {}, set(), 0
    for observation in observations:
        exact_keys(observation, OBSERVATION_KEYS, "observation")
        year, team = observation["season"], observation["team"]
        require(type(year) is int and str(year) in cutoffs, "Unknown observation season")
        require(isinstance(team, str) and team.startswith("FICTIONAL_"), "Unknown fictional team")
        observed = utc(observation["published_at_utc"])
        require(observed.year == year, "Observation year differs from season")
        for key, lower, upper in (("rating", 500, 2500), ("form", -3, 3), ("rest_days", 0, 14)):
            value = numeric(observation[key], key)
            require(lower <= value <= upper, "Observation outside authored feature range")
        identity = (year, team, observed)
        require(identity not in seen, "Duplicate or conflicting source snapshot")
        seen.add(identity)
        if observed > utc(cutoffs[str(year)]):
            excluded += 1
            continue
        key = (year, team)
        if key not in selected or observed > utc(selected[key]["published_at_utc"]):
            selected[key] = observation
    features = []
    for game in games:
        keys = [(game["season"], game[field]) for field in ("team_a", "team_b")]
        require(all(key in selected for key in keys), "Missing eligible pre-cutoff observation")
        a, b = (selected[key] for key in keys)
        features.append(
            {
                **game,
                "forecast_at_utc": cutoffs[str(game["season"])],
                "feature_available_at_utc": max(
                    a["published_at_utc"], b["published_at_utc"], key=utc
                ),
                "features": [a[field] - b[field] for field in ("rating", "form", "rest_days")],
            }
        )
    return features, {
        "source_observations": len(observations),
        "excluded_post_cutoff_observations": excluded,
        "selected_team_season_observations": len(selected),
        "feature_names": list(FEATURE_NAMES),
        "labels_received_by_feature_builder": False,
        "latest_eligible_snapshot_rule": True,
    }


def validate_feature_rows(rows: list[dict]) -> None:
    require(isinstance(rows, list) and bool(rows), "Missing feature rows")
    cutoffs = {}
    for row in rows:
        exact_keys(row, FEATURE_KEYS, "feature row; evaluation labels are forbidden")
        year = str(row["season"])
        require(year not in cutoffs or cutoffs[year] == row["forecast_at_utc"], "Cutoff conflict")
        cutoffs[year] = row["forecast_at_utc"]
        require(
            utc(row["feature_available_at_utc"]) <= utc(row["forecast_at_utc"]),
            "Post-cutoff feature rejected",
        )
        require(utc(row["feature_available_at_utc"]).year == row["season"], "Feature year conflict")
        require(isinstance(row["features"], list) and len(row["features"]) == 3, "Feature shape")
        for value in row["features"]:
            require(abs(numeric(value, "feature")) <= 10_000, "Feature magnitude bound")
    validate_games([{key: row[key] for key in GAME_KEYS} for row in rows], cutoffs)


def validate_labels(labels: list[dict], rows: list[dict]) -> dict[str, dict]:
    require(isinstance(labels, list) and bool(labels), "Missing labels")
    games = {row["id"]: row for row in rows}
    result = {}
    for label in labels:
        exact_keys(label, LABEL_KEYS, "label")
        identity = label["id"]
        require(isinstance(identity, str) and identity in games, "Extra or invalid label ID")
        require(identity not in result, "Duplicate label ID")
        require(label["scope"] == SCOPE, "Only synthetic labels are allowed")
        require(type(label["outcome_a"]) is int and label["outcome_a"] in (0, 1), "Binary label")
        require(
            utc(label["available_at_utc"]) > utc(games[identity]["started_at_utc"]),
            "Label must become available after its game",
        )
        result[identity] = label
    require(set(result) == set(games), "Exact feature/label ID closure required")
    return result


def fit_scaler(training: list[dict]) -> dict:
    """Fit on (x, -x) pairs with half weight per row; no evaluation data is accepted."""
    validate_feature_rows(training)
    means = [0.0] * len(FEATURE_NAMES)
    scales = []
    for index in range(len(FEATURE_NAMES)):
        variance = math.fsum(row["features"][index] ** 2 for row in training) / len(training)
        scales.append(math.sqrt(variance) if variance else 1.0)
    return {
        "mean": means,
        "scale": scales,
        "population_variance": True,
        "fitted_on": "TRAINING_SYMMETRIC_PAIRS_ONLY",
        "physical_training_games": len(training),
        "augmented_training_rows": 2 * len(training),
        "weight_per_augmented_row": 0.5,
        "effective_training_game_weight": float(len(training)),
    }


def transform(vector: list[float], scaler: dict) -> list[float]:
    require(len(vector) == len(scaler["mean"]) == len(scaler["scale"]) == 3, "Scaler shape")
    result = []
    for value, mean, scale in zip(vector, scaler["mean"], scaler["scale"], strict=True):
        number, center, denominator = (
            numeric(value, "feature"),
            numeric(mean, "scaler mean"),
            numeric(scale, "scaler SD"),
        )
        require(denominator > 0, "Scaler SD must be positive")
        result.append((number - center) / denominator)
    return result


def logistic_objective(pairs: list[tuple], coefficients: list[float], penalty: float) -> float:
    total_weight = math.fsum(weight for _, _, weight in pairs)
    loss = (
        math.fsum(
            weight * (max(z, 0) - y * z + math.log1p(math.exp(-abs(z))))
            for x, y, weight in pairs
            for z in [math.fsum(a * b for a, b in zip(x, coefficients, strict=True))]
        )
        / total_weight
    )
    return loss + penalty * math.fsum(value**2 for value in coefficients) / 2


def fit_model(training: list[dict], labels: list[dict], *, forecast_at_utc: str) -> dict:
    """Perform a fixed, actual L2 logistic fit using earlier, already-available labels."""
    validate_feature_rows(training)
    outcomes = validate_labels(labels, training)
    fitted_at = utc(forecast_at_utc) - timedelta(hours=1)
    for row in training:
        require(row["season"] < fitted_at.year, "Training season must precede evaluation season")
        require(
            utc(outcomes[row["id"]]["available_at_utc"]) < fitted_at,
            "Training label unavailable at fit time",
        )
        require(utc(row["feature_available_at_utc"]) < fitted_at, "Training feature unavailable")
    scaler = fit_scaler(training)
    pairs = []
    for row in training:
        vector = transform(row["features"], scaler)
        y = outcomes[row["id"]]["outcome_a"]
        pairs.extend(((vector, y, 0.5), ([-v for v in vector], 1 - y, 0.5)))
    coefficients = [0.0] * len(FEATURE_NAMES)
    penalty = PROTOCOL["l2_penalty"]
    before = logistic_objective(pairs, coefficients, penalty)
    for _ in range(PROTOCOL["iterations"]):
        terms = [[] for _ in coefficients]
        for vector, y, weight in pairs:
            predicted = sigmoid(math.fsum(x * w for x, w in zip(vector, coefficients, strict=True)))
            for index, value in enumerate(vector):
                terms[index].append(weight * (predicted - y) * value)
        gradients = [
            math.fsum(values) / len(training) + penalty * coefficients[index]
            for index, values in enumerate(terms)
        ]
        coefficients = [
            weight - PROTOCOL["learning_rate"] * gradient
            for weight, gradient in zip(coefficients, gradients, strict=True)
        ]
    after = logistic_objective(pairs, coefficients, penalty)
    require(math.isfinite(after) and after <= before + 1e-12, "Numerical optimizer loss regression")
    training_payload = [{"features": row["features"], **outcomes[row["id"]]} for row in training]
    return {
        "evidence_scope": SCOPE,
        "model": "ACTUALLY_FITTED_SYNTHETIC_L2_LOGISTIC_REGRESSION",
        "feature_names": list(FEATURE_NAMES),
        "coefficients": coefficients,
        "intercept": 0.0,
        "scaler": scaler,
        "fit_completed_at_utc": stamp(fitted_at),
        "fit_time_is_authored_fixture_clock_not_wall_clock": True,
        "training_seasons": sorted({row["season"] for row in training}),
        "latest_training_label_available_at_utc": max(
            (value["available_at_utc"] for value in outcomes.values()), key=utc
        ),
        "physical_training_ids": [row["id"] for row in training],
        "training_input_pin": pin(canonical(training_payload)),
        "optimizer": {
            "iterations_completed": PROTOCOL["iterations"],
            "training_objective_initial": before,
            "training_objective_final": after,
            "learning_rate": PROTOCOL["learning_rate"],
            "l2_penalty": penalty,
            "early_stopping_or_evaluation_tuning": False,
        },
    }


def predict(model: dict, rows: list[dict]) -> list[dict]:
    """Inference accepts validated feature rows only, never evaluation labels."""
    validate_feature_rows(rows)
    require(model["evidence_scope"] == SCOPE and model["intercept"] == 0.0, "Model scope")
    require(model["feature_names"] == list(FEATURE_NAMES), "Model feature schema")
    require(len(model["coefficients"]) == 3, "Coefficient shape")
    require(model["scaler"]["mean"] == [0.0, 0.0, 0.0], "Symmetric centering contract")
    for value in model["coefficients"]:
        numeric(value, "coefficient")
    forecasts = []
    for row in rows:
        require(row["season"] > max(model["training_seasons"]), "Evaluation/training overlap")
        require(row["id"] not in model["physical_training_ids"], "Training ID in evaluation")
        require(
            utc(model["fit_completed_at_utc"]) < utc(row["forecast_at_utc"]),
            "Model not fitted before forecast",
        )
        vector = transform(row["features"], model["scaler"])
        probability = sigmoid(
            math.fsum(x * weight for x, weight in zip(vector, model["coefficients"], strict=True))
        )
        forecasts.append({key: row[key] for key in GAME_KEYS} | {"pred": probability})
    return forecasts


def score(forecasts: list[dict], labels: list[dict], cutoffs: dict) -> dict:
    require(isinstance(forecasts, list) and bool(forecasts), "Missing forecasts")
    for forecast in forecasts:
        exact_keys(forecast, GAME_KEYS | {"pred"}, "forecast")
        probability = numeric(forecast["pred"], "probability")
        require(0 <= probability <= 1, "Probability outside [0, 1]")
    games = [{key: row[key] for key in GAME_KEYS} for row in forecasts]
    validate_games(games, cutoffs)
    outcomes = validate_labels(labels, games)
    pairs = [(row["pred"], outcomes[row["id"]]["outcome_a"], row["season"]) for row in forecasts]

    def metrics(group: list[tuple]) -> dict:
        count = len(group)
        losses = []
        for p, y, _ in group:
            q = max(LOG_EPSILON, min(1 - LOG_EPSILON, p))
            losses.append(-math.log(q) if y else -math.log1p(-q))
        positive = [p for p, y, _ in group if y]
        negative = [p for p, y, _ in group if not y]
        auc = None
        if positive and negative:
            auc = math.fsum(float(a > b) + 0.5 * float(a == b) for a in positive for b in negative)
            auc /= len(positive) * len(negative)
        return {
            "physical_games": count,
            "brier": math.fsum((p - y) ** 2 for p, y, _ in group) / count,
            "log_loss": math.fsum(losses) / count,
            "accuracy_ties_half_credit": math.fsum(
                0.5 if p == 0.5 else float((p > 0.5) == bool(y)) for p, y, _ in group
            )
            / count,
            "roc_auc": auc,
        }

    per_season = {
        str(year): metrics([row for row in pairs if row[2] == year])
        for year in sorted({row[2] for row in pairs})
    }
    bins, ece = [], 0.0
    for index in range(PROTOCOL["calibration_bins"]):
        members = [row for row in pairs if min(int(row[0] * 5), 4) == index]
        mean = math.fsum(row[0] for row in members) / len(members) if members else None
        observed = math.fsum(row[1] for row in members) / len(members) if members else None
        if members:
            ece += len(members) / len(pairs) * abs(mean - observed)
        bins.append(
            {
                "lower": index / 5,
                "upper": (index + 1) / 5,
                "count": len(members),
                "mean_prediction": mean,
                "observed_frequency": observed,
            }
        )
    return {
        "evidence_scope": SCOPE,
        "pooled_game_weighted": metrics(pairs),
        "per_season": per_season,
        "unweighted_mean_season_brier": math.fsum(value["brier"] for value in per_season.values())
        / len(per_season),
        "reliability": {"bins": bins, "expected_calibration_error": ece},
        "log_loss_probability_clip": LOG_EPSILON,
        "interpretation": "Synthetic out-of-season diagnostics, not NCAA performance evidence.",
    }


def calibration_svg(evaluation: dict) -> bytes:
    """Accessible deterministic static fallback; no third-party rendering dependency."""
    bins = evaluation["reliability"]["bins"]
    caption = "Authored fictional data only. Each game was predicted by an earlier-season fit."
    elements = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="760" height="430" '
        'viewBox="0 0 760 430" role="img" aria-labelledby="title desc">',
        '<title id="title">Synthetic temporal model reliability</title>',
        f'<desc id="desc">{html.escape(caption)} Circles show five reliability bins.</desc>',
        '<rect width="760" height="430" rx="14" fill="#f8fafc"/>',
        '<g font-family="system-ui, sans-serif" fill="#14283f">',
        '<text x="46" y="36" font-size="22" font-weight="700">'
        "Does confidence match frequency?</text>",
        '<text x="46" y="60" font-size="12" fill="#526477">'
        "SYNTHETIC ONLY · three expanding-window folds</text>",
    ]
    for tick in range(6):
        value = tick / 5
        x, y = 84 + 570 * value, 350 - 250 * value
        elements.extend(
            [
                f'<path d="M84 {y:.1f}H654" stroke="#dbe4ec"/>',
                f'<text x="66" y="{y + 4:.1f}" text-anchor="end" font-size="11">{value:.1f}</text>',
                f'<text x="{x:.1f}" y="371" text-anchor="middle" font-size="11">{value:.1f}</text>',
            ]
        )
    elements.append('<path d="M84 350L654 100" stroke="#697e93" stroke-dasharray="5 5"/>')
    points = []
    for item in bins:
        if item["count"]:
            x = 84 + 570 * item["mean_prediction"]
            y = 350 - 250 * item["observed_frequency"]
            points.append(f"{x:.2f},{y:.2f}")
    elements.append(
        f'<polyline points="{" ".join(points)}" fill="none" stroke="#087e8b" stroke-width="3"/>'
    )
    for item in bins:
        if item["count"]:
            x = 84 + 570 * item["mean_prediction"]
            y = 350 - 250 * item["observed_frequency"]
            elements.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="6" fill="#087e8b" stroke="#fff" '
                f'stroke-width="2"><title>n={item["count"]}; mean probability '
                f"{item['mean_prediction']:.3f}; observed "
                f"{item['observed_frequency']:.3f}</title></circle>"
            )
    elements.extend(
        [
            '<text x="369" y="397" text-anchor="middle" font-size="12">'
            "Predicted probability</text>",
            '<text transform="translate(23 225) rotate(-90)" text-anchor="middle" '
            'font-size="12">Observed frequency</text>',
            '<text x="46" y="420" font-size="10" fill="#526477">'
            "Small synthetic sample; this is not a calibration guarantee "
            "or a competition score.</text>",
            "</g></svg>\n",
        ]
    )
    return "\n".join(elements).encode()


def reproduce(fixture: dict) -> dict[str, bytes]:
    exact_keys(
        fixture,
        {
            "schema_version",
            "evidence_scope",
            "seed",
            "description",
            "cutoffs_utc",
            "observations",
            "games",
            "labels",
        },
        "fixture",
    )
    require(type(fixture["schema_version"]) is int and fixture["schema_version"] == 1, "Schema")
    require(fixture["evidence_scope"] == SCOPE, "Only explicitly synthetic fixtures accepted")
    require(type(fixture["seed"]) is int and 0 <= fixture["seed"] < 2**32, "Fixture seed")
    require(isinstance(fixture["description"], str) and fixture["description"], "Description")
    # The teaching protocol is fixed before fitting; this is not a prospective real-data seal.
    protocol_pin = pin(canonical(PROTOCOL))
    features, feature_audit = build_features(
        fixture["games"], fixture["observations"], fixture["cutoffs_utc"]
    )
    labels = validate_labels(fixture["labels"], features)
    forecasts, models, folds = [], [], []
    for season in PROTOCOL["evaluation_seasons"]:
        training = [row for row in features if row["season"] < season]
        evaluation = [row for row in features if row["season"] == season]
        require(
            bool(training) and bool(evaluation), "Every registered fold needs train and evaluation"
        )
        model = fit_model(
            training,
            [labels[row["id"]] for row in training],
            forecast_at_utc=fixture["cutoffs_utc"][str(season)],
        )
        predictions = predict(model, evaluation)
        forecasts.extend(predictions)
        models.append({"evaluation_season": season, **model})
        folds.append(
            {
                "evaluation_season": season,
                "training_seasons": model["training_seasons"],
                "physical_training_games": len(training),
                "physical_evaluation_games": len(evaluation),
                "train_evaluation_ID_intersection": 0,
                "training_labels_available_before_fit": True,
                "scaler_fit_on_training_only": True,
                "predictions_frozen_before_evaluation": True,
                "prediction_pin": pin(canonical(predictions)),
                "training_input_pin": model["training_input_pin"],
            }
        )
    # Predictions are serialized before evaluation labels enter the scoring function.
    forecast_bytes = canonical({"evidence_scope": SCOPE, "forecasts": forecasts})
    evaluation_labels = [labels[row["id"]] for row in forecasts]
    evaluation = score(forecasts, evaluation_labels, fixture["cutoffs_utc"])
    reference = score(
        [{**row, "pred": 0.5} for row in forecasts], evaluation_labels, fixture["cutoffs_utc"]
    )
    evaluation.update(
        {
            "schema_version": 1,
            "forecast_pin_before_scoring": pin(forecast_bytes),
            "teaching_protocol": PROTOCOL,
            "protocol_pin_before_fitting": protocol_pin,
            "folds": folds,
            "feature_audit": feature_audit,
            "synthetic_model_fits": len(models),
            "owner_research_fits": 0,
            "private_artifacts_read": 0,
            "network_requests": 0,
            "reference_50_percent": reference["pooled_game_weighted"],
            "scope_limit": (
                "Reproduces this authored example only, not private research or Kaggle scores."
            ),
        }
    )
    files = {
        "synthetic_fixture.json": canonical(fixture),
        "predictions.json": forecast_bytes,
        "evaluation.json": canonical(evaluation),
        "synthetic_fits.json": canonical({"evidence_scope": SCOPE, "fits": models}),
        "calibration.svg": calibration_svg(evaluation),
    }
    files["manifest.json"] = canonical(
        {
            "schema_version": 1,
            "evidence_scope": SCOPE,
            "generator": "tools/temporal_model_demo.py",
            "generator_pin": pin(Path(__file__).read_bytes()),
            "artifact_closure": "Exactly the five named payloads; manifest excludes its own hash",
            "payloads": {name: pin(raw) for name, raw in files.items()},
            "protocol_pin": protocol_pin,
            "synthetic_model_fits": len(models),
            "owner_research_fits": 0,
        }
    )
    return files


def run_demo(out_dir: Path | None = None, seed: int = SEED, *, check: bool = False) -> dict:
    """Return the evaluation; optionally generate or byte-check the six public artifacts."""
    files = reproduce(make_fixture(seed))
    if check:
        require(out_dir is not None, "Check requires output directory")
        for name, expected in files.items():
            path = Path(out_dir) / name
            require(path.is_file() and path.read_bytes() == expected, "Artifact mismatch: " + name)
    elif out_dir is not None:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        for name, raw in files.items():
            (Path(out_dir) / name).write_bytes(raw)
    return json.loads(files["evaluation.json"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", "--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--check", action="store_true", help="Verify bytes without writing")
    args = parser.parse_args(argv)
    try:
        evaluation = run_demo(args.out_dir, args.seed, check=args.check)
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "evidence_scope": SCOPE,
                    "mode": "check" if args.check else "generate",
                    "synthetic_model_fits": evaluation["synthetic_model_fits"],
                    **evaluation["pooled_game_weighted"],
                },
                sort_keys=True,
            )
        )
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
