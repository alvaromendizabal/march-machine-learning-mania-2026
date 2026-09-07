"""Synthetic tests only: season leakage, actual fitting, corruption, and replay."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from march_mania.modeling import candidates, columns_for
from march_mania.publication import inference
from march_mania.publication.artifacts import (
    restore_archive,
    restore_tasks,
    safe_path,
    verified_write,
)
from march_mania.runtime import EventLog, TaskStore, digest, fingerprint


@pytest.fixture
def settings() -> dict:
    path = Path(__file__).resolve().parents[1] / "configs/inference.json"
    return {**json.loads(path.read_text()), "threads": 1, "chunk_size": 3}


@pytest.fixture
def inputs(settings: dict) -> tuple:
    rng = np.random.default_rng(2026)
    history, games, matchups = [], [], []
    for gender, base in [("M", 1100), ("W", 3100)]:
        cs = [c for c in candidates(gender) if c.family == settings["families"][gender]]
        names = sorted({column for c in cs for column in columns_for(c)})
        for season in range(2013, 2027):
            if season == 2020:
                continue
            for i in range(6):
                row = {
                    "Gender": gender,
                    "Season": season,
                    "DayNum": 136 + i,
                    "ID": f"{season}_{base + i}_{base + i + 10}",
                    "y": i % 2,
                    **{name: float(rng.normal()) for name in names},
                }
                games.append(row)
                if season == 2026:
                    row = {key: value for key, value in row.items() if key not in {"y", "DayNum"}}
                    if i % 2:
                        row["diff_seed"] = np.nan
                    matchups.append(row)
                if season in settings["selection_seasons"]:
                    for c in cs:
                        history.append(
                            {
                                "Gender": gender,
                                "Season": season,
                                "ID": row["ID"],
                                "y": i % 2,
                                "route": gender,
                                "family": c.family,
                                "candidate": c.name,
                                "p": 0.2 + 0.6 * (i % 2),
                            }
                        )
    matrix = pd.DataFrame(games)
    requested = pd.DataFrame(matchups)
    sample = pd.DataFrame({"ID": requested.ID, "Pred": 0.5})
    return pd.DataFrame(history), matrix, requested, sample


def test_freeze_ignores_future_targets(settings: dict, inputs: tuple) -> None:
    history = inputs[0]
    future = history.assign(Season=2026, p=0.99, y=1 - history.y)
    assert inference.freeze_recipe(history, settings) == inference.freeze_recipe(
        pd.concat([history, future]), settings
    )
    recipe = inference.freeze_recipe(history, settings)
    for gender in ("M", "W"):
        assert all("seed" not in c for c in recipe["genders"][gender]["features"]["seed_free"])


@pytest.mark.parametrize(
    "field,value",
    [
        ("selection_seasons", [2022]),
        ("prediction_season", 2027),
        ("benchmark_seasons", [2026]),
        ("calibration", "temperature"),
        ("families", {"M": "xgboost", "W": "logistic"}),
        ("chunk_size", 0),
        ("threads", True),
        ("protocol", "untouched"),
    ],
)
def test_invalid_config(settings: dict, field: str, value: object) -> None:
    with pytest.raises(ValueError):
        inference.validate_config({**settings, field: value})


def test_duplicate_and_missing_selection(settings: dict, inputs: tuple) -> None:
    with pytest.raises(ValueError, match="Duplicate"):
        inference.freeze_recipe(pd.concat([inputs[0], inputs[0]]), settings)
    with pytest.raises(ValueError, match="Missing"):
        inference.freeze_recipe(inputs[0].loc[inputs[0].Season != 2021], settings)


def test_training_cutoff_and_identity(inputs: tuple) -> None:
    frame = inputs[1]
    with pytest.raises(ValueError, match="boundary"):
        inference.validate_games(frame, 2025)
    valid = frame.loc[frame.Season < 2026]
    with pytest.raises(ValueError, match="Duplicate"):
        inference.validate_games(pd.concat([valid, valid]), 2025)
    with pytest.raises(ValueError, match="identity"):
        inference.validate_games(valid.assign(ID=[f"invalid_{i}" for i in range(len(valid))]), 2025)


def test_matchup_contract(inputs: tuple) -> None:
    _, _, matrix, sample = inputs
    inference.validate_matchups(matrix, sample)
    with pytest.raises(ValueError, match="label-free"):
        inference.validate_matchups(matrix.assign(y=1), sample)
    with pytest.raises(ValueError, match="exactly"):
        inference.validate_matchups(matrix.iloc[::-1], sample)
    with pytest.raises(ValueError, match="Both"):
        inference.validate_matchups(matrix.assign(Gender="M"), sample)


def test_actual_fit_resume_and_future_outcome_isolation(
    tmp_path: Path, settings: dict, inputs: tuple, monkeypatch: pytest.MonkeyPatch
) -> None:
    history, frame, matrix, sample = inputs
    recipe = inference.freeze_recipe(history, settings)
    key = fingerprint(settings)
    store = TaskStore(tmp_path, key, EventLog(tmp_path / "events.jsonl"))
    first = inference.execute(frame, matrix, sample, recipe, tmp_path, store, settings)
    assert first["rows"] == len(sample) and first["final_model_fits"] == 4
    submission = tmp_path / "publication/submission.csv"
    before = digest(submission)
    audits = json.loads((tmp_path / "publication/fit_audits.json").read_text())
    assert all(a["training_max_season"] == 2025 for a in audits)
    original = inference.fit_model

    def forbid(*args, **kwargs):
        raise AssertionError("Completed fits must not rerun")

    monkeypatch.setattr(inference, "fit_model", forbid)
    altered = frame.copy()
    altered.loc[altered.Season == 2026, "y"] = -99
    inference.execute(altered, matrix, sample, recipe, tmp_path, store, settings)
    assert digest(submission) == before
    monkeypatch.setattr(inference, "fit_model", original)
    # A fresh independent run must also ignore all 2026 labels, not just reuse cached fits.
    fresh = tmp_path / "independent"
    inference.execute(
        altered,
        matrix,
        sample,
        recipe,
        fresh,
        TaskStore(fresh, key, EventLog(fresh / "events.jsonl")),
        settings,
    )
    assert digest(fresh / "publication/submission.csv") == before
    # Corrupt only a prediction chunk: repair that ordinary artifact, not completed fits.
    monkeypatch.setattr(inference, "fit_model", forbid)
    chunk = next(tmp_path.glob("predict_*/predictions.csv"))
    chunk.write_text("corrupted")
    inference.execute(frame, matrix, sample, recipe, tmp_path, store, settings)
    assert digest(submission) == before


def test_failed_fit_has_no_success_checkpoint(
    tmp_path: Path, settings: dict, inputs: tuple, monkeypatch: pytest.MonkeyPatch
) -> None:
    history, frame, matrix, sample = inputs

    def fail(*args, **kwargs):
        raise RuntimeError("Simulated interruption")

    monkeypatch.setattr(inference, "fit_model", fail)
    with pytest.raises(RuntimeError, match="interruption"):
        inference.execute(
            frame,
            matrix,
            sample,
            inference.freeze_recipe(history, settings),
            tmp_path,
            TaskStore(tmp_path, "test", EventLog(tmp_path / "events.jsonl")),
            settings,
        )
    assert not list(tmp_path.rglob("checkpoint.json"))
    assert not (tmp_path / "publication/submission.csv").exists()


@pytest.mark.parametrize("name", ["../outside", "/etc/passwd", "x/../../outside", "x\\outside", ""])
def test_safe_paths(tmp_path: Path, name: str) -> None:
    with pytest.raises(ValueError):
        safe_path(tmp_path, name)


def test_archive_restore_and_corruption(tmp_path: Path) -> None:
    contents = b"a,b\n1,2\n"
    sha = hashlib.sha256(contents).hexdigest()
    archive = tmp_path / "inputs.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("run/table.csv", contents)
        z.writestr(
            "archive_manifest.json", json.dumps({"schema": 1, "sha256": {"run/table.csv": sha}})
        )
    destination = tmp_path / "restored"
    restore_archive(archive, destination, digest(archive))
    restore_archive(archive, destination, digest(archive))
    assert (destination / "run/table.csv").read_bytes() == contents
    with pytest.raises(ValueError, match="recorded"):
        restore_archive(archive, destination, "0" * 64)
    with pytest.raises(ValueError, match="mismatch"):
        verified_write(destination / "run/table.csv", b"bad", sha)
    assert (destination / "run/table.csv").read_bytes() == contents


def test_remote_resume_commits_last(tmp_path: Path) -> None:
    payload = b"verified model bytes"
    sha = hashlib.sha256(payload).hexdigest()
    cp = json.dumps({"fingerprint": "abc", "outputs": {"model.joblib": sha}}).encode()
    objects = {"project/abc/fit/checkpoint.json": cp, "project/abc/fit/model.joblib": payload}

    class Client:
        def get_paginator(self, name):
            return self

        def paginate(self, **kwargs):
            return [{"Contents": [{"Key": key} for key in objects]}]

        def get_object(self, Bucket, Key):
            value = objects[Key]
            return {
                "Body": io.BytesIO(value),
                "Metadata": {"sha256": hashlib.sha256(value).hexdigest()},
            }

    mirror = SimpleNamespace(client=Client(), bucket="private", prefix="project/abc")
    log = EventLog(tmp_path / "events.jsonl")
    assert restore_tasks(mirror, tmp_path, "abc", log) == 1
    assert (tmp_path / "fit/model.joblib").read_bytes() == payload
    assert restore_tasks(mirror, tmp_path, "abc", log) == 1
    with pytest.raises(ValueError, match="incompatible"):
        restore_tasks(mirror, tmp_path, "changed", log)
    objects["project/abc/fit/model.joblib"] = b"corrupt"
    (tmp_path / "fit/model.joblib").unlink()
    (tmp_path / "fit/checkpoint.json").unlink()
    with pytest.raises(ValueError, match="mismatch"):
        restore_tasks(mirror, tmp_path, "abc", log)
    assert not (tmp_path / "fit/checkpoint.json").exists()
