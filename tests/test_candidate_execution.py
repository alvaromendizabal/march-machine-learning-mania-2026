"""Real wide-matrix chunks, interrupted artifacts, and verified official context restoration."""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from march_mania import matchup_artifacts
from march_mania.advanced_features import advanced_snapshot
from march_mania.features import read_official
from march_mania.publication import workflow
from march_mania.runtime import EventLog, TaskStore


def test_wide_chunks_equal_direct_features_and_resume(raw, tmp_path, monkeypatch):
    data = read_official(raw)[0]
    teams = pd.concat([advanced_snapshot(t, g, 2016) for g, t in data.items()], ignore_index=True)
    pairs = pd.DataFrame(
        {
            "Gender": ["M", "W", "M"],
            "Season": [2016] * 3,
            "Team1ID": [1001, 3001, 1003],
            "Team2ID": [1002, 3002, 1006],
        }
    )
    direct = matchup_artifacts.pair_features(teams, pairs)
    sample = pd.DataFrame({"ID": direct.ID, "Pred": 0.5})
    store = TaskStore(tmp_path, "wide-matrix", EventLog(tmp_path / "events.jsonl"))
    output = tmp_path / "features.parquet"
    matchup_artifacts.write_submission_features(teams, pairs, sample, output, store, chunk_size=1)
    result = pd.read_parquet(output)
    pd.testing.assert_frame_equal(result.drop(columns="route"), direct)
    times = {p: p.stat().st_mtime_ns for p in tmp_path.glob("submission_*/features.parquet")}

    def forbid(*args):
        raise AssertionError("Verified feature chunks must not be generated again")

    monkeypatch.setattr(matchup_artifacts, "pair_features", forbid)
    matchup_artifacts.write_submission_features(teams, pairs, sample, output, store, chunk_size=1)
    assert times == {p: p.stat().st_mtime_ns for p in times}
    with pytest.raises(ValueError, match="Positive"):
        matchup_artifacts.write_submission_features(teams, pairs, sample, output, store, 0)
    with pytest.raises(ValueError, match="Duplicate"):
        matchup_artifacts.write_submission_features(
            teams, pairs, sample.assign(ID="x"), output, store
        )


def test_context_restore_is_checksum_checked_and_does_not_overwrite(raw, monkeypatch):
    target = raw / "MTeamCoaches.csv"
    log = EventLog(raw.parent / "events.jsonl")

    def download(bucket, key, destination, ExtraArgs):
        assert "VersionId" in ExtraArgs and key.endswith("MTeamCoaches.csv")
        from pathlib import Path

        Path(destination).write_bytes(b"incorrect remote bytes")

    monkeypatch.setattr(
        workflow,
        "Mirror",
        lambda _: SimpleNamespace(
            bucket="private",
            prefix="official-context",
            client=SimpleNamespace(download_file=download),
        ),
    )
    with pytest.raises(ValueError, match="checksum"):
        workflow.restore_coach_context(raw, log)
    assert not target.exists() and not (raw / ".MTeamCoaches.csv.tmp").exists()
    target.write_bytes(b"existing user source")
    workflow.restore_coach_context(raw, log)
    assert target.read_bytes() == b"existing user source"
