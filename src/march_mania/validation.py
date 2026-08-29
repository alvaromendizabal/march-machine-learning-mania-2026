from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

RESULT_TABLES = [
    "MRegularSeasonCompactResults",
    "WRegularSeasonCompactResults",
    "MNCAATourneyCompactResults",
    "WNCAATourneyCompactResults",
    "MRegularSeasonDetailedResults",
    "WRegularSeasonDetailedResults",
    "MNCAATourneyDetailedResults",
    "WNCAATourneyDetailedResults",
]

REQUIRED_CORE_TABLES = [
    "MTeams",
    "WTeams",
    "MSeasons",
    "WSeasons",
    "MRegularSeasonCompactResults",
    "WRegularSeasonCompactResults",
    "MNCAATourneyCompactResults",
    "WNCAATourneyCompactResults",
    "MRegularSeasonDetailedResults",
    "WRegularSeasonDetailedResults",
    "MNCAATourneyDetailedResults",
    "WNCAATourneyDetailedResults",
    "MNCAATourneySeeds",
    "WNCAATourneySeeds",
]


def run_raw_data_audit(
    tables: Mapping[str, pd.DataFrame], target_season: int = 2026
) -> pd.DataFrame:
    records: list[dict[str, object]] = []

    def record(check: str, passed: bool, severity: str, details: str) -> None:
        records.append(
            {"Check": check, "Passed": bool(passed), "Severity": severity, "Details": details}
        )

    missing = [name for name in REQUIRED_CORE_TABLES if name not in tables]
    record(
        "Required core tables are present",
        not missing,
        "ERROR",
        "All required tables found" if not missing else f"Missing: {missing}",
    )

    if "MTeams" in tables and "WTeams" in tables:
        men = set(tables["MTeams"]["TeamID"])
        women = set(tables["WTeams"]["TeamID"])
        record("Men/women TeamIDs do not overlap", men.isdisjoint(women), "ERROR", f"Overlap count: {len(men & women)}")
        record("Men TeamIDs are below 3000", all(team < 3000 for team in men), "ERROR", f"Teams checked: {len(men)}")
        record("Women TeamIDs are at least 3000", all(team >= 3000 for team in women), "ERROR", f"Teams checked: {len(women)}")

    for name in RESULT_TABLES:
        if name not in tables:
            continue
        df = tables[name]
        keys = ["Season", "DayNum", "WTeamID", "LTeamID"]
        duplicate_count = int(df.duplicated(keys).sum())
        record(f"{name}: unique game keys", duplicate_count == 0, "ERROR", f"Duplicate rows: {duplicate_count}")
        same_team_count = int((df["WTeamID"] == df["LTeamID"]).sum())
        record(f"{name}: teams differ", same_team_count == 0, "ERROR", f"Invalid rows: {same_team_count}")
        score_order_count = int((df["WScore"] <= df["LScore"]).sum())
        record(f"{name}: winner score exceeds loser score", score_order_count == 0, "ERROR", f"Invalid rows: {score_order_count}")

        if "RegularSeason" in name:
            bad_day = int((df["DayNum"] > 132).sum())
            record(f"{name}: regular-season DayNum <= 132", bad_day == 0, "ERROR", f"Rows above 132: {bad_day}")

        if "NCAATourney" in name:
            target_rows = int((df["Season"] == target_season).sum())
            record(
                f"{name}: target-season outcomes excluded from modeling inputs",
                target_rows == 0,
                "WARNING",
                f"Rows for {target_season}: {target_rows}. Never use these as features or training labels when replaying the {target_season} forecast.",
            )

        if "Detailed" in name:
            bad_attempts = 0
            for prefix in ("W", "L"):
                for made, attempted in (("FGM", "FGA"), ("FGM3", "FGA3"), ("FTM", "FTA")):
                    bad_attempts += int((df[f"{prefix}{made}"] > df[f"{prefix}{attempted}"]).sum())
            record(f"{name}: made shots do not exceed attempts", bad_attempts == 0, "ERROR", f"Violations: {bad_attempts}")

            w_rebuilt = 2 * df["WFGM"] + df["WFGM3"] + df["WFTM"]
            l_rebuilt = 2 * df["LFGM"] + df["LFGM3"] + df["LFTM"]
            point_mismatch = int(((w_rebuilt != df["WScore"]) | (l_rebuilt != df["LScore"])).sum())
            record(f"{name}: box-score points reconcile", point_mismatch == 0, "WARNING", f"Rows with mismatch: {point_mismatch}")

            # Audit signal only; do not automatically remove flagged games.
            w_poss = df["WFGA"] - df["WOR"] + df["WTO"] + 0.475 * df["WFTA"]
            l_poss = df["LFGA"] - df["LOR"] + df["LTO"] + 0.475 * df["LFTA"]
            poss_gap = np.abs(w_poss - l_poss)
            suspicious = int((poss_gap > 7).sum())
            record(
                f"{name}: estimated possession gap audit",
                suspicious == 0,
                "WARNING",
                f"Rows with absolute gap > 7: {suspicious}; inspect rather than dropping automatically.",
            )

    for gender in ("M", "W"):
        compact_name = f"{gender}RegularSeasonCompactResults"
        detailed_name = f"{gender}RegularSeasonDetailedResults"
        if compact_name not in tables or detailed_name not in tables:
            continue
        compact = tables[compact_name]
        detailed = tables[detailed_name]
        start = 2003 if gender == "M" else 2010
        compact_keys = compact.loc[compact["Season"] >= start, ["Season", "DayNum", "WTeamID", "LTeamID"]]
        detailed_keys = detailed.loc[detailed["Season"] >= start, ["Season", "DayNum", "WTeamID", "LTeamID"]]
        merged = compact_keys.merge(detailed_keys.drop_duplicates(), how="left", indicator=True)
        missing_detail = int((merged["_merge"] == "left_only").sum())
        severity = "WARNING" if gender == "W" else "ERROR"
        record(
            f"{gender}: compact games have detailed rows from documented start",
            missing_detail == 0,
            severity,
            f"Missing detailed rows: {missing_detail} (limited early women's gaps are documented).",
        )

    for name in ("SampleSubmissionStage1", "SampleSubmissionStage2"):
        if name not in tables:
            continue
        df = tables[name]
        parts = df["ID"].astype(str).str.split("_", expand=True)
        parse_ok = parts.shape[1] == 3
        record(f"{name}: IDs have three components", parse_ok, "ERROR", f"Rows: {len(df)}")
        if parse_ok:
            t1 = pd.to_numeric(parts[1], errors="coerce")
            t2 = pd.to_numeric(parts[2], errors="coerce")
            bad_order = int((t1 >= t2).sum())
            mixed_gender = int((((t1 < 3000) & (t2 >= 3000)) | ((t1 >= 3000) & (t2 < 3000))).sum())
            record(f"{name}: lower TeamID is first", bad_order == 0, "ERROR", f"Violations: {bad_order}")
            record(f"{name}: matchups do not mix genders", mixed_gender == 0, "ERROR", f"Violations: {mixed_gender}")

    return pd.DataFrame(records)
