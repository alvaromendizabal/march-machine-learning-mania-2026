from __future__ import annotations

import json

import pandas as pd
import pytest
from test_feature_store import settings

from march_mania.data_review import inventory_file, run, split_review
from march_mania.features import read_official
from march_mania.runtime import digest


def test_inventory_reads_latin1_and_counts_missing_values(tmp_path):
    path = tmp_path / "names.csv"
    path.write_bytes("Season,Name\n2016,Jos\xe9\n2017,\n".encode("latin1"))
    record = inventory_file(path)
    assert record["rows"] == 2 and record["missing_cells"] == 1
    assert record["first_season"] == 2016 and record["last_season"] == 2017
    assert record["sha256"] == digest(path)


@pytest.mark.parametrize(
    "name", ["MTeamCoaches.csv", "MTeamConferences.csv", "WTeamConferences.csv"]
)
def test_inventory_recognizes_official_context_inputs(tmp_path, name):
    path = tmp_path / name
    path.write_text("Season,TeamID\n2026,1101\n")
    assert inventory_file(path)["feature_source"]


def test_raw_audit_records_provenance_and_resumes_without_rereading(raw, tmp_path, monkeypatch):
    manifest = {
        "sha256": {p.name: digest(p) for p in raw.glob("*.csv")},
        "source": "synthetic test fixture",
        "retrieved_at": "2026-01-01T00:00:00+00:00",
    }
    (raw.parent / "data_manifest.json").write_text(json.dumps(manifest))
    output = tmp_path / "review"
    first = run(raw, output, settings())
    assert first["download_hashes_verified"] and first["files"] == 8

    def unexpected(*args):
        pytest.fail("Completed task should have been reused")

    monkeypatch.setattr("march_mania.data_review.inventory_file", unexpected)
    monkeypatch.setattr("march_mania.data_review.season_review", unexpected)
    assert run(raw, output, settings())["fingerprint"] == first["fingerprint"]
    root = output / first["fingerprint"]
    splits = pd.read_csv(root / "splits.csv")
    assert (splits.training_max_season < splits.validation_season).all()
    events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
    assert sum(e["event"] == "task_reused" for e in events) == 9
    path = raw / "MRegularSeasonCompactResults.csv"
    path.write_text(path.read_text() + "\n")
    with pytest.raises(ValueError, match="checksum"):
        run(raw, output, settings())


def test_split_guard_and_no_future_label_dependence(raw):
    data = read_official(raw)[0]
    config = settings()
    config["validation_seasons"] = [2016]
    original = split_review(data, config)
    for tables in data.values():
        labels = tables["NCAATourneyCompactResults"]
        labels.loc[labels.Season == 2017, ["WScore", "LScore"]] = [200, 1]
    pd.testing.assert_frame_equal(original, split_review(data, config))
    labels = data["M"]["NCAATourneyCompactResults"]
    labels.loc[labels.Season == 2016, "DayNum"] = 132
    with pytest.raises(ValueError, match="precedes"):
        split_review(data, config)


def test_missing_raw_has_clear_next_action(tmp_path):
    with pytest.raises(FileNotFoundError, match="march-data"):
        run(tmp_path / "raw", tmp_path / "review", settings())
