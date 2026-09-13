"""Complete score preservation and rejection of changed observation provenance."""

import json
import shutil
from pathlib import Path

import pytest

from march_mania.publication import scoreboard
from march_mania.runtime import digest

ROOT = Path(__file__).resolve().parents[1]


def test_complete_current_scores_and_legacy_history_remain_distinct():
    table = scoreboard.scores(ROOT)
    assert len(table) == 58
    assert table.sha256.nunique() == 58
    assert table.iloc[0].candidate_id == "m_pooled_xgboost_t090__w_logistic"
    assert table.iloc[0].private_brier == pytest.approx(0.1225463)
    assert table.groupby("batch").size().to_dict() == {"original_50": 50, "refinement_8": 8}


@pytest.mark.parametrize("change", ["unrecorded_score", "duplicate", "missing", "wrong_source"])
def test_changed_or_incomplete_observations_are_rejected(tmp_path, change):
    for name in (
        "reports/prediction_production",
        "reports/prediction_refinement",
        scoreboard.REPORT,
    ):
        shutil.copytree(ROOT / name, tmp_path / name)
    path = tmp_path / scoreboard.REPORT / "refinement_scores.csv"
    lines = path.read_text().splitlines()
    if change == "unrecorded_score":
        lines[-1] = lines[-1].replace("0.1225463", "0.0225463")
    elif change == "duplicate":
        lines[-1] = lines[-2]
    elif change == "missing":
        lines = lines[:-1]
    else:
        lines[-1] = lines[-1].replace("d3d2763e", "unknown")
    path.write_text("\n".join(lines) + "\n")
    if change != "unrecorded_score":
        provenance = path.with_name("provenance.json")
        record = json.loads(provenance.read_text())
        record["scores_sha256"] = digest(path)
        provenance.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        scoreboard.scores(tmp_path)
