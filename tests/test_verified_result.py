"""Public evidence checks reject inconsistent claims and mutable release artifacts."""

from __future__ import annotations

import copy
import importlib.util
import json
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verified_release", ROOT / "portfolio/reproduce_release.py"
)
assert SPEC is not None and SPEC.loader is not None
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


@pytest.fixture
def public_bundle(tmp_path):
    evidence = json.loads((ROOT / release.EVIDENCE).read_text())
    for entry in evidence["provenance"]["source_documents"]:
        destination = tmp_path / entry["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / entry["path"]).read_bytes())
    destination = tmp_path / release.EVIDENCE
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(evidence))
    return tmp_path, evidence


def test_comparisons_use_separate_references_and_preserve_coverage(public_bundle):
    root, evidence = public_bundle
    result = release.validate(evidence, root)
    assert Decimal(result["absolute_brier_reduction"]) == Decimal("0.0030359")
    assert result["relative_brier_reduction_percent_display"] == "2.7663"
    matched = result["matched_reconstruction"]
    assert matched["evaluation_games"] == 126
    assert matched["relative_brier_reduction_percent_display"] == "2.9137"
    assert matched["reference_method_brier"] != result["reference_brier"]
    assert result["historical_coverage"]["games"] == 566
    assert result["private_model_reproduced"] is False
    assert result["fresh_generalization_test"] is False


def test_source_content_tampering_is_detected(public_bundle):
    root, evidence = public_bundle
    path = root / evidence["provenance"]["source_documents"][0]["path"]
    path.write_text(path.read_text() + " ")
    with pytest.raises(release.EvidenceError, match="checksum mismatch"):
        release.validate(evidence, root)


def test_updated_hash_does_not_hide_disagreeing_receipt(public_bundle):
    root, evidence = public_bundle
    document = evidence["provenance"]["source_documents"][0]
    path = root / document["path"]
    receipt = json.loads(path.read_text())
    receipt["private_score"] = "0.09"
    path.write_text(json.dumps(receipt))
    document["sha256"] = release.digest(path)
    with pytest.raises(release.EvidenceError, match="receipt disagrees"):
        release.validate(evidence, root)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-0.1", "1.1", 0.1067095])
def test_invalid_or_inexact_score_rejected(public_bundle, value):
    root, evidence = public_bundle
    evidence["scored"]["accepted"]["score"] = value
    with pytest.raises(release.EvidenceError):
        release.validate(evidence, root)


def test_lost_historical_games_rejected(public_bundle):
    root, evidence = public_bundle
    evidence["historical"]["legacy_ineligible"] -= 1
    with pytest.raises(release.EvidenceError, match="loses or duplicates"):
        release.validate(evidence, root)


def test_group_scores_must_reconcile_to_matched_result(public_bundle):
    root, evidence = public_bundle
    evidence["matched_reconstruction"]["project_men_brier"] = "0.01"
    with pytest.raises(release.EvidenceError, match="game-weighted"):
        release.validate(evidence, root)


@pytest.mark.parametrize(
    "field", ["original_rank_claim", "private_training_reproduced", "2027_prospectively_validated"]
)
def test_unsupported_public_claims_rejected(public_bundle, field):
    root, evidence = public_bundle
    evidence["disclosure"][field] = True
    with pytest.raises(release.EvidenceError, match="Unsupported disclosure"):
        release.validate(evidence, root)


def test_consumed_outcomes_cannot_be_labeled_fresh_holdout(public_bundle):
    root, evidence = public_bundle
    evidence["historical"]["consumed"] = False
    with pytest.raises(release.EvidenceError, match="untouched holdout"):
        release.validate(evidence, root)


def test_private_path_and_symlink_escape_rejected(public_bundle, tmp_path):
    root, evidence = public_bundle
    escaped = copy.deepcopy(evidence)
    escaped["provenance"]["source_documents"][0]["path"] = "../private_predictions.csv"
    with pytest.raises(release.EvidenceError, match="stay within"):
        release.validate(escaped, root)
    secret = tmp_path.parent / f"{tmp_path.name}_private.json"
    secret.write_text("{}")
    link = root / "escape.json"
    link.symlink_to(secret)
    escaped["provenance"]["source_documents"][0]["path"] = "escape.json"
    with pytest.raises(release.EvidenceError, match="escapes"):
        release.validate(escaped, root)


def test_report_restart_is_deterministic_and_tamper_evident(public_bundle):
    root, _ = public_bundle
    first = release.write_report(root)
    original_report = (root / release.REPORT).read_bytes()
    original_svg = (root / release.SVG).read_bytes()
    assert release.write_report(root) == first
    assert (root / release.REPORT).read_bytes() == original_report
    assert (root / release.SVG).read_bytes() == original_svg
    assert release.check_report(root) == first
    (root / release.SVG).write_text("<svg>misleading replacement</svg>")
    with pytest.raises(release.EvidenceError, match="figure differs"):
        release.check_report(root)


def test_report_checks_current_evidence_after_change(public_bundle):
    root, evidence = public_bundle
    release.write_report(root)
    evidence["as_of_utc"] = "2026-10-09"
    (root / release.EVIDENCE).write_text(json.dumps(evidence))
    with pytest.raises(release.EvidenceError, match="report differs"):
        release.check_report(root)
