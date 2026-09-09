"""Post-result provenance, temporal alignment and saved-prediction transformations."""

from __future__ import annotations

import io
import json
import shutil
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from march_mania.publication import refinement
from march_mania.runtime import atomic_json, digest

ROOT = Path(__file__).resolve().parents[1]


def test_real_scores_cover_the_complete_matrix_and_preserve_lineage():
    scores = refinement.score_table(ROOT)
    assert len(scores) == 50
    assert scores.sha256.nunique() == 50
    assert scores.rows.eq(132133).all()
    matrix = scores.pivot(index="men_stream", columns="women_stream", values="private_brier")
    assert matrix.shape == (10, 5)
    assert matrix.idxmin(axis=1).eq("w_logistic").all()
    # With independent male/female streams, crossed-pair Brier differences are additive.
    # Screenshot rounding permits a small residual, but transcription errors do not.
    changes = matrix.subtract(matrix.w_logistic, axis=0)
    assert (changes.max() - changes.min()).max() <= 2.1e-7


def test_publication_recomputes_the_real_historical_evidence():
    summary = refinement.review(ROOT)
    assert summary["observed_submissions"] == 50
    assert summary["historical_games_per_candidate"] == 649
    assert summary["new_adjustments"] == 8
    annual = pd.read_csv(ROOT / refinement.REPORT / "metrics_by_season.csv")
    assert set(annual.Season) == {2016, 2017, 2018, 2019, 2021}
    assert annual.groupby("candidate_id").size().eq(5).all()


@pytest.mark.parametrize("change", ["score", "duplicate", "unknown", "future", "duplicate_variant"])
def test_stale_scores_or_invalid_protocol_cannot_be_reviewed(tmp_path, change):
    if change in {"future", "duplicate_variant"}:
        config = json.loads((ROOT / refinement.CONFIG).read_text())
        if change == "future":
            config["development_seasons"][-1] = 2026
        else:
            config["variants"][1] = config["variants"][0]
        with pytest.raises(ValueError):
            refinement.validate_config(config)
        return
    folder = tmp_path / "reports/prediction_production"
    shutil.copytree(ROOT / "reports/prediction_production", folder)
    scores = pd.read_csv(tmp_path / refinement.SCORES)
    if change == "score":
        scores.loc[0, "private_brier"] += 0.01
    elif change == "duplicate":
        scores.loc[0, "candidate_id"] = scores.loc[1, "candidate_id"]
    else:
        scores.loc[0, "candidate_id"] = "missing_model"
    scores.to_csv(tmp_path / refinement.SCORES, index=False)
    if change != "score":
        metadata = (tmp_path / refinement.SCORES).with_suffix(".json")
        record = json.loads(metadata.read_text())
        record["scores_sha256"] = digest(tmp_path / refinement.SCORES)
        atomic_json(metadata, record)
    with pytest.raises(ValueError):
        refinement.score_table(tmp_path)


def test_all_adjustments_preserve_complementarity_bounds_and_neutral_predictions():
    config = json.loads((ROOT / refinement.CONFIG).read_text())
    refinement.validate_config(config)
    anchor = np.array([0.0, 0.01, 0.3, 0.5, 0.8, 0.99, 1.0])
    partner = np.array([0.0, 0.2, 0.1, 0.5, 0.7, 0.9, 1.0])
    for variant in config["variants"]:
        result = refinement.transform(anchor, partner, variant)
        reverse = refinement.transform(1 - anchor, 1 - partner, variant)
        assert np.isfinite(result).all()
        assert ((result >= 0) & (result <= 1)).all()
        np.testing.assert_allclose(result + reverse, 1, atol=2e-15, rtol=0)
        assert result[3] == 0.5
    with pytest.raises(ValueError, match="probability"):
        refinement.transform(np.array([np.nan]), np.array([0.4]), config["variants"][0])


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    config = json.loads((ROOT / refinement.CONFIG).read_text())
    arrays = {
        "m_pooled_xgboost": [0.17, 0.81],
        "m_rank_logistic": [0.41, 0.65],
        "m_pooled_hist": [0.12, 0.73],
    }
    source = tmp_path / "source.zip"
    records = []
    with zipfile.ZipFile(source, "w") as archive:
        for stream, values in arrays.items():
            name = stream + "__w_logistic"
            data = (
                "ID,Pred\n"
                f"2026_1101_1102,{values[0]}\n2026_1102_1103,{values[1]}\n"
                "2026_3101_3102,0.12345678901234567\n2026_3102_3103,0.9876543210987654\n"
            )
            archive.writestr(name + ".csv", data)
            import hashlib

            records.append(
                {"candidate_id": name, "sha256": hashlib.sha256(data.encode()).hexdigest()}
            )
    config["source_archive_sha256"] = digest(source)
    atomic_json(tmp_path / refinement.CONFIG, config)
    atomic_json(
        (tmp_path / refinement.SCORES).with_suffix(".json"), {"production_fingerprint": "a" * 64}
    )
    pd.DataFrame(records).to_csv(
        tmp_path / "reports/prediction_production/submission_manifest.csv", index=False
    )
    monkeypatch.setattr(refinement, "review", lambda root: {"inputs": {}})
    return tmp_path, source, config


def test_generation_preserves_women_aligns_ids_and_reuses_exact_bytes(inputs, monkeypatch):
    root, source, config = inputs
    first = refinement.generate(root, source)
    bundle = root / first["archive"]
    with zipfile.ZipFile(bundle) as archive, zipfile.ZipFile(source) as original:
        assert len(archive.namelist()) == 10
        baseline = original.read("m_pooled_xgboost__w_logistic.csv")
        for variant in config["variants"]:
            data = archive.read(variant["candidate_id"] + ".csv")
            assert data.splitlines()[-2:] == baseline.splitlines()[-2:]
            frame = pd.read_csv(io.BytesIO(data), float_precision="round_trip")
            assert frame.shape == (4, 2)
    monkeypatch.setattr(
        refinement, "transform", lambda *a: pytest.fail("unnecessary recomputation")
    )
    assert refinement.generate(root, source) == first


def test_changed_archive_is_rejected_before_generation(inputs):
    root, source, _ = inputs
    source.write_bytes(source.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="Source ZIP"):
        refinement.generate(root, source)
    assert not (root / "submissions").exists()
