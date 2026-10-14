"""Offline, synthetic-only forecast and evaluation example (Python stdlib).

This authored teaching fixture is independent of the private research forecast.
No network, credentials, training data or third-party packages are required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "examples" / "public_reproduction"
SEED = 20261014
SCOPE = "SYNTHETIC_ONLY"
LOG_EPSILON = 1e-15


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact_keys(record: dict, keys: set[str], context: str) -> None:
    require(isinstance(record, dict) and set(record) == keys, f"Invalid {context} fields")


def utc(value: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), "Timestamp must use explicit UTC Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid UTC timestamp") from exc
    require(parsed.utcoffset() == timedelta(0), "Timestamp must be UTC")
    return parsed


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def uniform(seed: int, key: str) -> float:
    """A platform-independent deterministic value strictly inside (0, 1)."""
    value = int.from_bytes(hashlib.sha256(f"{seed}:{key}".encode()).digest()[:6], "big")
    return (value + 0.5) / 2**48


def win_probability(rating_a: float, rating_b: float) -> float:
    """An illustrative, unfitted logistic rating rule, not the research model."""
    for rating in (rating_a, rating_b):
        require(type(rating) in (int, float) and math.isfinite(rating), "Invalid rating")
        require(500 <= rating <= 2500, "Rating outside fixture range [500, 2500]")
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def make_fixture(seed: int = SEED) -> dict:
    """Author four synthetic seasons; dates and labels describe no NCAA games."""
    teams = [f"FICTIONAL_{index:02d}" for index in range(1, 9)]
    cutoffs, observations, games, labels = {}, [], [], []
    for season, rounds in zip(range(2023, 2027), range(4, 8), strict=True):
        cutoffs[str(season)] = f"{season}-03-16T23:59:59Z"
        strengths = {
            team: round(1300 + 400 * uniform(seed, f"{season}:{team}:strength"), 6)
            for team in teams
        }
        for team in teams:
            for day in (14, 16, 18):
                noise = 100 * (uniform(seed, f"{season}:{team}:{day}:noise") - 0.5)
                # The post-cutoff observation is deliberately influential but excluded.
                rating = strengths[team] + noise + (450 if day == 18 else 0)
                observations.append(
                    {
                        "season": season,
                        "team": team,
                        "observed_at_utc": f"{season}-03-{day:02d}T12:00:00Z",
                        "rating": round(rating, 6),
                    }
                )
        rotation = list(teams)
        for round_index in range(rounds):
            for match_index in range(4):
                a, b = rotation[match_index], rotation[-match_index - 1]
                identity = f"synthetic-{season}-r{round_index + 1}-g{match_index + 1}"
                if uniform(seed, identity + ":orientation") < 0.5:
                    a, b = b, a
                games.append(
                    {
                        "game_id": identity,
                        "season": season,
                        "started_at_utc": f"{season}-03-{18 + round_index:02d}T17:00:00Z",
                        "team_a": a,
                        "team_b": b,
                    }
                )
                # Labels use the latent authored strengths, independent of observed ratings.
                latent = 1 / (1 + 10 ** ((strengths[b] - strengths[a]) / 500))
                labels.append(
                    {
                        "game_id": identity,
                        "outcome_a": int(uniform(seed, identity + ":outcome") < latent),
                    }
                )
            rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
    return {
        "schema_version": 1,
        "evidence_scope": SCOPE,
        "seed": seed,
        "description": "Authored fictional teams, ratings and outcomes; no NCAA evidence.",
        "cutoffs_utc": cutoffs,
        "observations": observations,
        "games": games,
        "labels": labels,
    }


def validate_games(games: list, cutoffs: dict) -> None:
    require(isinstance(games, list) and bool(games), "Games must be a nonempty list")
    require(isinstance(cutoffs, dict) and bool(cutoffs), "Missing season cutoffs")
    for season, cutoff in cutoffs.items():
        require(isinstance(season, str) and season.isdigit(), "Invalid cutoff season")
        require(utc(cutoff).year == int(season), "Cutoff year must match season")
    ids, physical_games = set(), set()
    for game in games:
        exact_keys(game, {"game_id", "season", "started_at_utc", "team_a", "team_b"}, "game")
        require(isinstance(game["game_id"], str) and bool(game["game_id"]), "Invalid game ID")
        require(game["game_id"] not in ids, "Duplicate game ID")
        ids.add(game["game_id"])
        require(type(game["season"]) is int, "Season must be an integer")
        season = str(game["season"])
        require(season in cutoffs, "Missing season cutoff")
        start = utc(game["started_at_utc"])
        require(start.year == game["season"], "Game year must match season")
        require(start > utc(cutoffs[season]), "Game must occur strictly after forecast cutoff")
        a, b = game["team_a"], game["team_b"]
        require(all(isinstance(t, str) and t for t in (a, b)) and a != b, "Invalid team pair")
        physical = (game["season"], start, *sorted((a, b)))
        require(physical not in physical_games, "Duplicate physical game, including swapped teams")
        physical_games.add(physical)


def predict(games: list, observations: list, cutoffs: dict) -> tuple[list, dict]:
    """Predict from identity-only requests; this interface cannot receive labels."""
    validate_games(games, cutoffs)
    require(isinstance(observations, list) and bool(observations), "Missing observations")
    selected, seen = {}, set()
    excluded = 0
    for observation in observations:
        exact_keys(observation, {"season", "team", "observed_at_utc", "rating"}, "observation")
        season, team = observation["season"], observation["team"]
        require(type(season) is int and str(season) in cutoffs, "Unknown observation season")
        require(isinstance(team, str) and bool(team), "Invalid observation team")
        stamp = utc(observation["observed_at_utc"])
        require(stamp.year == season, "Observation year must match season")
        win_probability(observation["rating"], 1500)  # Validate even excluded observations.
        identity = (season, team, stamp)
        require(identity not in seen, "Duplicate source snapshot")
        seen.add(identity)
        if stamp > utc(cutoffs[str(season)]):
            excluded += 1
            continue
        key = (season, team)
        if key not in selected or stamp > utc(selected[key]["observed_at_utc"]):
            selected[key] = observation
    forecasts = []
    for game in games:
        keys = [(game["season"], game[field]) for field in ("team_a", "team_b")]
        require(
            all(key in selected for key in keys), "Missing eligible pre-cutoff team observation"
        )
        a, b = (selected[key] for key in keys)
        forecasts.append({**game, "probability_a": win_probability(a["rating"], b["rating"])})
    audit = {
        "forecast_cutoffs_utc": cutoffs,
        "selection_rule": "Latest observation at or before that season's fixed forecast cutoff",
        "source_observations": len(observations),
        "excluded_post_cutoff_observations": excluded,
        "selected_team_season_observations": len(selected),
        "selected_observations": [selected[key] for key in sorted(selected)],
        "prediction_inputs_contain_labels": False,
    }
    return forecasts, audit


def evaluate(forecasts: list, labels: list, cutoffs: dict) -> dict:
    require(isinstance(forecasts, list) and bool(forecasts), "Missing forecasts")
    game_keys = {"game_id", "season", "started_at_utc", "team_a", "team_b"}
    for row in forecasts:
        exact_keys(row, game_keys | {"probability_a"}, "forecast")
        p = row["probability_a"]
        require(
            type(p) in (int, float) and math.isfinite(p) and 0 <= p <= 1,
            "Probability must be finite and in [0, 1]",
        )
    validate_games([{key: row[key] for key in game_keys} for row in forecasts], cutoffs)
    require(isinstance(labels, list) and bool(labels), "Missing labels")
    outcomes = {}
    for label in labels:
        exact_keys(label, {"game_id", "outcome_a"}, "label")
        require(isinstance(label["game_id"], str), "Invalid label ID")
        require(label["game_id"] not in outcomes, "Duplicate outcome label")
        require(type(label["outcome_a"]) is int and label["outcome_a"] in (0, 1), "Nonbinary label")
        outcomes[label["game_id"]] = label["outcome_a"]
    require(set(outcomes) == {row["game_id"] for row in forecasts}, "Forecast/label IDs differ")
    rows = [(row["probability_a"], outcomes[row["game_id"]], row["season"]) for row in forecasts]

    def metrics(group: list) -> dict:
        count = len(group)
        brier = math.fsum((p - y) ** 2 for p, y, _ in group) / count
        losses = []
        for p, y, _ in group:
            bounded = max(LOG_EPSILON, min(1 - LOG_EPSILON, p))
            losses.append(-math.log(bounded) if y else -math.log1p(-bounded))
        positives = [p for p, y, _ in group if y]
        negatives = [p for p, y, _ in group if not y]
        auc = None
        if positives and negatives:
            concordant = math.fsum(
                float(pos > neg) + 0.5 * float(pos == neg) for pos in positives for neg in negatives
            )
            auc = concordant / (len(positives) * len(negatives))
        return {
            "physical_games": count,
            "brier": brier,
            "log_loss": math.fsum(losses) / count,
            "roc_auc": auc,
            "mean_prediction": math.fsum(p for p, _, _ in group) / count,
            "observed_team_a_win_rate": sum(y for _, y, _ in group) / count,
        }

    seasons = {
        str(year): metrics([row for row in rows if row[2] == year])
        for year in sorted({row[2] for row in rows})
    }
    bins = []
    ece = 0.0
    for index in range(5):
        members = [row for row in rows if min(int(row[0] * 5), 4) == index]
        mean_p = math.fsum(row[0] for row in members) / len(members) if members else None
        rate = sum(row[1] for row in members) / len(members) if members else None
        if members:
            ece += len(members) / len(rows) * abs(mean_p - rate)
        bins.append(
            {
                "lower_inclusive": index / 5,
                "upper": (index + 1) / 5,
                "upper_inclusive": index == 4,
                "count": len(members),
                "mean_prediction": mean_p,
                "observed_win_rate": rate,
            }
        )
    return {
        "schema_version": 1,
        "evidence_scope": SCOPE,
        "interpretation": "Synthetic diagnostic only; not NCAA accuracy or calibration evidence.",
        "pooled_game_weighted": metrics(rows),
        "per_season": seasons,
        "unweighted_mean_season_brier": (
            math.fsum(v["brier"] for v in seasons.values()) / len(seasons)
        ),
        "reference_50_percent_brier": 0.25,
        "log_loss_probability_clip": LOG_EPSILON,
        "reliability": {
            "bins": bins,
            "expected_calibration_error": ece,
            "caution": "Small authored sample; bin diagnostics are not a calibration guarantee.",
        },
        "auc_convention": (
            "Pairwise positive-versus-negative ranking; ties count one half; null if undefined"
        ),
    }


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
    require(
        type(fixture["schema_version"]) is int and fixture["schema_version"] == 1,
        "Unsupported fixture schema",
    )
    require(fixture["evidence_scope"] == SCOPE, "Only explicitly synthetic fixtures are accepted")
    require(type(fixture["seed"]) is int, "Fixture seed must be an integer")
    require(
        isinstance(fixture["description"], str) and bool(fixture["description"]),
        "Missing fixture description",
    )
    forecasts, audit = predict(fixture["games"], fixture["observations"], fixture["cutoffs_utc"])
    scores = evaluate(forecasts, fixture["labels"], fixture["cutoffs_utc"])
    files = {
        "synthetic_fixture.json": canonical(fixture),
        "predictions.json": canonical({"evidence_scope": SCOPE, "forecasts": forecasts}),
        "evaluation.json": canonical(scores),
    }
    provenance = {
        "schema_version": 1,
        "evidence_scope": SCOPE,
        "fixture_seed": fixture["seed"],
        "generator": "tools/reproduce_public.py",
        "generator_sha256": digest(Path(__file__).read_bytes()),
        "model": "Unfitted logistic rating example with fixed scale 400",
        "model_fits": 0,
        "network_requests": 0,
        "private_artifacts_read": 0,
        "source_audit": audit,
        "artifacts": {
            name: {"sha256": digest(raw), "bytes": len(raw)} for name, raw in files.items()
        },
        "scope_limit": (
            "Reproduces only this authored example, not a private model or a Kaggle score."
        ),
    }
    files["provenance.json"] = canonical(provenance)
    return files


def read_fixture(path: Path) -> dict:
    def no_duplicates(pairs: list) -> dict:
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate JSON object key")
            result[key] = value
        return result

    def no_constant(value: str) -> None:
        raise ValueError(f"Nonfinite JSON constant: {value}")

    return json.loads(path.read_text(), object_pairs_hook=no_duplicates, parse_constant=no_constant)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Compare all artifact bytes; write nothing"
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--fixture", type=Path, help="Use a strict synthetic fixture JSON")
    args = parser.parse_args(argv)
    started = time.monotonic()
    try:
        fixture = read_fixture(args.fixture) if args.fixture else make_fixture()
        files = reproduce(fixture)
        if args.check:
            for name, expected in files.items():
                path = args.output_dir / name
                require(
                    path.is_file() and path.read_bytes() == expected, f"Artifact mismatch: {name}"
                )
        else:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            for name, raw in files.items():
                (args.output_dir / name).write_bytes(raw)
        result = {
            "status": "PASS",
            "mode": "check" if args.check else "generate",
            "evidence_scope": SCOPE,
            "physical_games": len(fixture["games"]),
            "artifact_files": sorted(files),
        }
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1
    finally:
        stamp = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        print(
            f"[{stamp}] public reproduction elapsed={time.monotonic() - started:.3f}s",
            file=sys.stderr,
        )


if __name__ == "__main__":
    raise SystemExit(main())
