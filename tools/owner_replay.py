"""Validate and render a private execution's explicitly public aggregate evidence.

This module reads no private prediction, checkpoint, source body or cloud path.
It checks the published accounting and selection rule; hashes identify withheld
evidence and are not a public rerun or proof of upstream publisher authenticity.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
from pathlib import Path

from evidence_contracts import require

ROOT = Path(__file__).resolve().parents[1]
REPLAY = ROOT / "portfolio/owner_replay.json"


def fields(value: dict, expected: str, label: str) -> None:
    require(type(value) is dict and set(value) == set(expected.split()), label + " fields")


def count(value, label: str) -> None:
    require(type(value) is int and value >= 0, "Invalid count: " + label)


def number(value, label: str, maximum: float | None = None) -> None:
    require(
        type(value) in (int, float) and math.isfinite(value) and value >= 0,
        "Invalid number: " + label,
    )
    require(maximum is None or value <= maximum, "Out of range: " + label)


def validate_replay(d: dict) -> dict:
    """Reject disclosure, incompatible denominators and unsupported promotion."""
    fields(
        d,
        "schema_version evidence_type execution reviewed_on status reason provenance "
        "execution_accounting cohort scorecards market coverage decision",
        "Replay",
    )
    require(type(d["schema_version"]) is int and d["schema_version"] == 1, "Replay schema")
    require(d["evidence_type"] == "AUDITABLE_PRIVATE_RUN_AGGREGATES", "Evidence class")
    require(re.fullmatch(r"v[0-9]+", d["execution"]) is not None, "Execution label")
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", d["reviewed_on"]) is not None, "Review date")
    require(d["status"] == "PARTIAL", "Incomplete source closure cannot be success")
    require(d["reason"] == "OWNED_SOURCE_CLOSURE_INCOMPLETE", "Unqualified stop reason")
    p, e, c, m, coverage, decision = (
        d[k]
        for k in ("provenance", "execution_accounting", "cohort", "market", "coverage", "decision")
    )
    fields(
        p,
        "summary_sha256 qualification_sha256 prediction_artifact_sha256 return_parts "
        "manifest_payload_entries logical_files all_uploaded_payloads_verified "
        "raw_source_data_public check_scope",
        "Provenance",
    )
    for key in ("summary_sha256", "qualification_sha256", "prediction_artifact_sha256"):
        require(re.fullmatch(r"[a-f0-9]{64}", p[key]) is not None, "Evidence hash")
    require(p["all_uploaded_payloads_verified"] is True, "Unverified return payloads")
    require(p["raw_source_data_public"] is False, "Private source disclosure")
    require(
        p["check_scope"]
        == (
            "Public checks verify aggregate consistency; "
            "private payloads were authenticated separately."
        ),
        "Public verification scope changed",
    )
    for key in ("manifest_payload_entries", "logical_files"):
        count(p[key], key)
    require(p["logical_files"] <= p["manifest_payload_entries"], "Logical payload count")
    require(type(p["return_parts"]) is list and bool(p["return_parts"]), "Return parts required")
    for ordinal, part in enumerate(p["return_parts"], 1):
        fields(part, "part bytes sha256", "Return part")
        count(part["part"], "part")
        count(part["bytes"], "bytes")
        require(part["part"] == ordinal, "Parts must be unique and consecutive")
        require(0 < part["bytes"] < 150_000_000, "Upload part exceeds strict bound")
        require(re.fullmatch(r"[a-f0-9]{64}", part["sha256"]) is not None, "Part hash")
    require(
        len({x["sha256"] for x in p["return_parts"]}) == len(p["return_parts"]),
        "Duplicate return content",
    )
    fields(
        e,
        "coordinator_seconds start_to_return_status_seconds effective_cpus mean_cpu_cores_used "
        "source_workers research_fits_reused science_fits_reused new_model_fits new_submissions "
        "final_free_disk_bytes old_return_source_bytes_preserved "
        "old_return_allocated_bytes_released "
        "return_bytes bulk_derived_bytes_in_return",
        "Execution",
    )
    for key, value in e.items():
        if key in {"coordinator_seconds", "start_to_return_status_seconds", "mean_cpu_cores_used"}:
            number(value, key)
        else:
            count(value, key)
    require(e["effective_cpus"] > 0 and e["source_workers"] > 0, "Missing execution capacity")
    require(e["mean_cpu_cores_used"] <= e["effective_cpus"], "CPU utilization exceeds capacity")
    require(e["start_to_return_status_seconds"] >= e["coordinator_seconds"], "Runtime intervals")
    require(e["new_model_fits"] == e["new_submissions"] == 0, "Replay cannot claim new training")
    require(e["return_bytes"] == sum(x["bytes"] for x in p["return_parts"]), "Return sum")
    require(e["bulk_derived_bytes_in_return"] <= e["return_bytes"], "Return byte partition")
    # Logical bytes and allocated disk bytes intentionally have no equality rule.
    fields(
        c,
        "unit development_seasons later_seasons development_games later_games total_games arms "
        "prediction_rows identical_arm_populations_verified all_windows_previously_examined "
        "fresh_holdout",
        "Cohort",
    )
    require(c["unit"] == "physical_games", "Prediction rows are not independent games")
    for key in ("development_games", "later_games", "total_games", "arms", "prediction_rows"):
        count(c[key], key)
        require(c[key] > 0, "Empty evaluation population")
    for key in ("development_seasons", "later_seasons"):
        require(type(c[key]) is list and bool(c[key]), "Missing season population")
        require(all(type(x) is int for x in c[key]), "Season must be an integer")
        require(c[key] == sorted(set(c[key])), "Repeated or unordered seasons")
    require(max(c["development_seasons"]) < min(c["later_seasons"]), "Season leakage")
    require(c["development_games"] + c["later_games"] == c["total_games"], "Game denominator")
    require(c["prediction_rows"] == c["total_games"] * c["arms"], "Matched arm denominator")
    require(c["identical_arm_populations_verified"] is True, "Unmatched arm populations")
    require(c["all_windows_previously_examined"] is True, "Consumed windows mislabeled")
    require(c["fresh_holdout"] is False, "A replay does not create a fresh holdout")
    require(type(d["scorecards"]) is list and len(d["scorecards"]) == c["arms"], "Arm count")
    require(len({x["arm"] for x in d["scorecards"]}) == c["arms"], "Duplicated arm identity")
    accepted = []
    for row in d["scorecards"]:
        fields(row, "arm role development_brier later_brier", "Scorecard")
        require(row["role"] in {"accepted", "challenger"}, "Unknown arm role")
        require(
            row["arm"] == "Accepted control" or re.fullmatch(r"Challenger [A-Z]", row["arm"]),
            "Public arm labels must not expose private recipes",
        )
        for key in ("development_brier", "later_brier"):
            number(row[key], key, maximum=1)
        if row["role"] == "accepted":
            accepted.append(row)
    require(len(accepted) == 1 and accepted[0]["arm"] == "Accepted control", "Accepted control")
    require(
        all(
            x["development_brier"] > accepted[0]["development_brier"]
            for x in d["scorecards"]
            if x["role"] == "challenger"
        ),
        "Retained-control rationale contradicts development evidence",
    )
    fields(
        m,
        "selection_records men_selection_records women_selection_records "
        "priced_pregame_selection_records training_admissions unknown_owned_containers "
        "candidate_requests semantic_duplicates unresolved_requests eligible_paid_requests "
        "paid_requests paid_credits source_closure_complete",
        "Market",
    )
    for key, value in m.items():
        if key != "source_closure_complete":
            count(value, key)
    require(
        m["men_selection_records"] + m["women_selection_records"] == m["selection_records"],
        "Market selection partition",
    )
    require(
        m["priced_pregame_selection_records"] <= m["selection_records"], "Priced selection count"
    )
    require(m["source_closure_complete"] is False, "Incomplete inventory mislabeled")
    require(m["unknown_owned_containers"] > 0, "Missing incomplete-inventory evidence")
    require(
        m["semantic_duplicates"] + m["unresolved_requests"] == m["candidate_requests"],
        "Candidate request partition",
    )
    require(
        m["training_admissions"]
        == m["eligible_paid_requests"]
        == m["paid_requests"]
        == m["paid_credits"]
        == 0,
        "Unsupported admission or purchase claim",
    )
    fields(
        coverage,
        "measurement defined_study_seasons required_men_detailed_games "
        "required_women_detailed_games required_study_detail_complete "
        "broader_project_data_complete future_2027_data_complete residuals",
        "Coverage",
    )
    require(
        coverage["measurement"] == "CARRIED_AUTHENTICATED_COVERAGE_NOT_A_NEW_RAW_CENSUS",
        "Carried coverage must stay labeled",
    )
    require(coverage["defined_study_seasons"] == "2013–2025 excluding 2020", "Study scope")
    require(coverage["required_study_detail_complete"] is True, "Study readiness changed")
    require(
        coverage["broader_project_data_complete"] is False
        and coverage["future_2027_data_complete"] is False,
        "Unsupported project completion",
    )
    for key in ("required_men_detailed_games", "required_women_detailed_games"):
        count(coverage[key], key)
    require(type(coverage["residuals"]) is list and bool(coverage["residuals"]), "Coverage gaps")
    for row in coverage["residuals"]:
        fields(row, "family unit have required missing", "Coverage residual")
        require(type(row["family"]) is str and len(row["family"]) <= 80, "Coverage label")
        require(
            row["unit"]
            in {
                "game_rows",
                "tournament_game_rows",
                "team_game_reconciliations",
                "seeded_team_seasons",
            },
            "Coverage unit",
        )
        for key in ("have", "required", "missing"):
            count(row[key], key)
        require(row["have"] + row["missing"] == row["required"], "Coverage denominator")
    require(
        len({r["family"] for r in coverage["residuals"]}) == len(coverage["residuals"]),
        "Duplicate coverage family",
    )
    fields(
        decision, "selected_arm champion_changed new_prospective_score_claimed reason", "Decision"
    )
    require(decision["selected_arm"] == accepted[0]["arm"], "Invalid promotion")
    require(
        decision["champion_changed"] is False
        and decision["new_prospective_score_claimed"] is False,
        "Unsupported scientific claim",
    )
    require(
        decision["reason"]
        == (
            "All three challengers worsen the declared development Brier; "
            "the later window is already exposed."
        ),
        "Decision rationale changed",
    )
    require(c["arms"] == 4, "Decision describes exactly three challengers")
    require(
        re.search(
            r"s3://|arn:aws|/home/|/mnt/|sagemaker-|api[_-]?key|access[_-]?token",
            json.dumps(d),
            re.I,
        )
        is None,
        "Private locator or credential field in aggregate",
    )
    return d


def load_replay(path: Path = REPLAY) -> dict:
    return validate_replay(json.loads(path.read_text()))


def render_replay_panel(d: dict) -> str:
    validate_replay(d)
    e, c = d["execution_accounting"], d["cohort"]
    cards = "".join(
        "<tr><th scope='row'>"
        + html.escape(row["arm"])
        + "</th>"
        + f"<td>{row['development_brier']:.7f}</td><td>{row['later_brier']:.7f}</td></tr>"
        for row in d["scorecards"]
    )
    gaps = "".join(
        f"<tr><th scope='row'>{html.escape(row['family'])}</th>"
        f"<td>{row['have']:,} / {row['required']:,}</td><td>{row['missing']:,}</td>"
        f"<td>{html.escape(row['unit'].replace('_', ' '))}</td></tr>"
        for row in d["coverage"]["residuals"]
    )
    return f"""<section id="owner-replay" class="replay-panel" aria-labelledby="replay-title">
<div class="eyebrow">Latest private run · public aggregates · {html.escape(d["reviewed_on"])}</div>
<h2 id="replay-title">Completed work should survive the next run.</h2>
<p><strong>{html.escape(d["execution"])}: {html.escape(d["status"])}.</strong>
Research and science replay completed. Owned market-source reconciliation remains open.
The public checks below validate aggregate consistency; private bodies stay private.</p>
<div class="grid"><article><span>Verified fit reuse</span>
<strong>{e["research_fits_reused"] + e["science_fits_reused"]}</strong>
<span>{e["new_model_fits"]} new fits; {e["new_submissions"]} new submissions.</span></article>
<article><span>Matched research games</span><strong>{c["total_games"]}</strong>
<span>{c["arms"]} arms; {c["prediction_rows"]:,} probability rows.</span></article>
<article><span>Free disk after packaging</span>
<strong>{e["final_free_disk_bytes"] / 1e9:.2f} GB</strong>
<span>Historical run measurement; current free space is not established.</span></article></div>
<h3>A negative result is a model-selection result.</h3>
<p>The accepted control remains selected. Every challenger worsens the declared development
Brier. The later window was already examined; it cannot support a fresh-holdout claim.</p>
<div class="replay-table"><table><caption>Lower Brier is better.
Every arm uses the same physical-game population.</caption>
<thead><tr><th>Public arm label</th><th>Development · {c["development_games"]} games</th>
<th>Exposed later · {c["later_games"]} games</th></tr></thead><tbody>{cards}</tbody></table></div>
<p>Challenger labels omit private recipes. Aggregate scores do not reproduce private training.
No paired uncertainty can be recomputed publicly without per-game errors, so this table makes
no significance or prospective-superiority claim.</p>
<details><summary>Inspect remaining data gaps and runtime accounting</summary>
<p>The defined 2013–2025 study has its required detailed inputs. Broader source coverage remains
incomplete. The following carried counts are not a fresh raw-table census.</p>
<div class="replay-table"><table><thead><tr><th>Evidence family</th><th>Have / required</th>
<th>Missing</th><th>Unit</th></tr></thead><tbody>{gaps}</tbody></table></div>
<p>Market inventory: {d["market"]["selection_records"]:,} selection records;
{d["market"]["training_admissions"]} model admissions. Quote selections are not distinct games.
{d["market"]["unknown_owned_containers"]:,} owned containers remain unresolved.</p>
<p>Core work: {e["coordinator_seconds"]:.2f} seconds; recorded start through return status:
{e["start_to_return_status_seconds"]:.2f} seconds. Mean CPU use:
{e["mean_cpu_cores_used"]:.3f} of {e["effective_cpus"]} effective cores.
This is an observation, not proof of the fastest configuration.</p>
<p>The uploaded return contained {e["bulk_derived_bytes_in_return"] / 1e6:.2f} MB of bulk derived
copies in {e["return_bytes"] / 1e6:.2f} MB total. That evidence exposed an actionable packaging
defect. It does not authorize deleting unique project data.</p></details></section>"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.parse_args()
    d = load_replay()
    print(
        json.dumps(
            {"status": "PASS", "execution": d["execution"], "scope": d["provenance"]["check_scope"]}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
