"""Terminal-only public-solution reproduction workflow."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

from march_mania.public_solutions import first_place_2026 as first

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/public_solutions/first_place_2026"
REPORTS = ROOT / "reports/public_solutions/first_place_2026"
TOOLS = ROOT / ".tools/public_solutions/first_place_2026"
MANIFEST = ROOT / "research/public_solutions/first_place_2026/source_manifest.json"

PINNED_RAW = (
    "https://raw.githubusercontent.com/"
    "harrisonhoran/kaggle-march-mania-2026-1st-place/"
    f"{first.REFERENCE_COMMIT}/"
)

WINNER_ENV = {
    "numpy": "2.2.4",
    "pandas": "2.2.3",
    "scikit-learn": "1.8.0",
    "scipy": "1.15.2",
    "xgboost": "3.2.0",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def package_version(name: str) -> str:
    candidates = [name]
    if name == "xgboost":
        candidates.append("xgboost-cpu")
    for candidate in candidates:
        try:
            return importlib.metadata.version(candidate)
        except importlib.metadata.PackageNotFoundError:
            pass
    return "missing"


def _find_under(root: Path, filename: str) -> Path | None:
    matches = [p for p in root.rglob(filename) if p.is_file()]
    if not matches:
        return None
    matches.sort(key=lambda p: (len(p.parts), str(p)))
    return matches[0]


def _run(command: list[str], cwd: Path | None = None) -> None:
    print("RUN", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def _kaggle_cli() -> list[str]:
    """Return the current environment's Kaggle CLI command."""
    executable = shutil.which("kaggle")
    if executable:
        return [executable]
    return [sys.executable, "-m", "kaggle"]


def _copy_existing_official(target: Path) -> list[str]:
    copied = []
    for filename in first.OFFICIAL_FILES:
        if (target / filename).is_file():
            continue
        source = _find_under(ROOT / "data", filename)
        if source is None or target in source.parents:
            continue
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target / filename)
        copied.append(filename)
    return copied


def _extract_all_zips(directory: Path) -> None:
    for archive in sorted(directory.glob("*.zip")):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(directory)


def fetch_inputs() -> dict:
    """Fetch all first-place inputs without browser/UI interaction."""
    spec = json.loads(MANIFEST.read_text(encoding="utf-8"))
    official = CACHE / "official"
    nishaan = CACHE / "nishaan"
    external = CACHE / "external"
    reference = CACHE / "reference"
    for directory in (official, nishaan, external, reference, REPORTS):
        directory.mkdir(parents=True, exist_ok=True)

    reused = _copy_existing_official(official)
    missing = [f for f in first.OFFICIAL_FILES if not (official / f).is_file()]
    if missing:
        _run(
            [
                *_kaggle_cli(),
                "competitions",
                "download",
                "-c",
                spec["kaggle_competition"],
                "-p",
                str(official),
                "--force",
            ]
        )
        _extract_all_zips(official)
        for filename in missing:
            if (official / filename).is_file():
                continue
            nested = _find_under(official, filename)
            if nested is not None:
                shutil.copy2(nested, official / filename)

    still_missing = [f for f in first.OFFICIAL_FILES if not (official / f).is_file()]
    if still_missing:
        raise FileNotFoundError(f"Missing official files after terminal fetch: {still_missing}")

    ap_path = nishaan / spec["nishaan_required_file"]
    if not ap_path.is_file():
        existing = _find_under(ROOT / "data", spec["nishaan_required_file"])
        if existing is not None and nishaan not in existing.parents:
            shutil.copy2(existing, ap_path)
        else:
            _run(
                [
                    *_kaggle_cli(),
                    "datasets",
                    "download",
                    "-d",
                    spec["kaggle_dataset"],
                    "-p",
                    str(nishaan),
                    "--unzip",
                    "--force",
                ]
            )
            if not ap_path.is_file():
                nested = _find_under(nishaan, spec["nishaan_required_file"])
                if nested is not None:
                    shutil.copy2(nested, ap_path)
    if not ap_path.is_file():
        raise FileNotFoundError(ap_path)

    for asset in spec["github_assets"]:
        destination = CACHE / asset["relative_path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.is_file():
            url = PINNED_RAW + asset["source_path"]
            print("DOWNLOAD", url, "->", destination, flush=True)
            urllib.request.urlretrieve(url, destination)

    files = []
    for path in sorted(p for p in CACHE.rglob("*") if p.is_file() and p.suffix != ".zip"):
        files.append(
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    receipt = {
        "status": "inputs_materialized",
        "reference_commit": first.REFERENCE_COMMIT,
        "cache_root": str(CACHE),
        "reused_official_files": reused,
        "files": files,
        "known_2026_outcomes_used": False,
    }
    (REPORTS / "input_manifest.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, indent=2))
    return receipt


def setup_exact_environment() -> dict:
    """Create isolated winner-version environment without modifying project .venv."""
    env = TOOLS / ".venv"
    python = env / "bin/python"
    requirements = ROOT / "research/public_solutions/first_place_requirements.txt"
    TOOLS.mkdir(parents=True, exist_ok=True)
    if not python.is_file():
        _run(["uv", "venv", str(env), "--python", "3.12"])
    _run(["uv", "pip", "install", "--python", str(python), "-r", str(requirements)])
    cmd = [
        str(python),
        "-c",
        (
            "import json,numpy,pandas,scipy,sklearn,xgboost;"
            "print(json.dumps({'numpy':numpy.__version__,'pandas':pandas.__version__,"
            "'scipy':scipy.__version__,'scikit-learn':sklearn.__version__,"
            "'xgboost':xgboost.__version__}))"
        ),
    ]
    output = subprocess.check_output(cmd, text=True).strip()
    versions = json.loads(output)
    receipt = {
        "status": "exact_environment_ready",
        "python": str(python),
        "versions": versions,
        "expected": WINNER_ENV,
        "exact_match": {k: versions.get(k) == v for k, v in WINNER_ENV.items()},
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "environment.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, indent=2))
    return receipt


def build_features() -> dict:
    """Build the literal published feature matrices; no model fitting."""
    official = CACHE / "official"
    ap = CACHE / "nishaan/AP Poll Data.csv"
    injury = CACHE / "external/college-basketball-injury-report_20260318_all.csv"
    bpr = CACHE / "external/miya_player_bpr_v2.csv"
    bundle = first.build_reference_features(official, ap, injury, bpr)

    derived = CACHE / "derived"
    derived.mkdir(parents=True, exist_ok=True)
    bundle.tournament.to_csv(
        derived / "tournament_features.csv.gz",
        index=False,
        compression={"method": "gzip", "mtime": 0},
    )
    bundle.submission.to_csv(
        derived / "submission_features.csv.gz",
        index=False,
        compression={"method": "gzip", "mtime": 0},
    )
    bundle.team_seasons.to_csv(
        derived / "team_seasons.csv.gz", index=False, compression={"method": "gzip", "mtime": 0}
    )

    REPORTS.mkdir(parents=True, exist_ok=True)
    bundle.coverage.to_csv(REPORTS / "feature_coverage.csv", index=False)

    required = []
    for gender, flag, features in (
        ("men", 1, first.MEN_FEATURES),
        ("women", 0, first.WOMEN_FEATURES),
    ):
        hist = bundle.tournament.loc[bundle.tournament["men_women"].eq(flag)]
        current = bundle.submission.loc[bundle.submission["men_women"].eq(flag)]
        required.append(
            {
                "gender": gender,
                "historical_rows": int(len(hist)),
                "submission_rows": int(len(current)),
                "historical_complete_rows": int(hist[list(features)].notna().all(axis=1).sum()),
                "submission_complete_rows": int(current[list(features)].notna().all(axis=1).sum()),
            }
        )

    receipt = {
        "status": "first_place_features_built",
        "reference_commit": first.REFERENCE_COMMIT,
        "historical_max_season": int(bundle.tournament["Season"].max()),
        "known_2026_outcomes_used": False,
        "men_features": list(first.MEN_FEATURES),
        "women_features": list(first.WOMEN_FEATURES),
        "coverage_summary": required,
        "derived_paths": {
            "tournament": str(derived / "tournament_features.csv.gz"),
            "submission": str(derived / "submission_features.csv.gz"),
            "team_seasons": str(derived / "team_seasons.csv.gz"),
            "coverage": str(REPORTS / "feature_coverage.csv"),
        },
        "derived_sha256": {
            name: sha256(Path(path))
            for name, path in {
                "tournament": derived / "tournament_features.csv.gz",
                "submission": derived / "submission_features.csv.gz",
                "team_seasons": derived / "team_seasons.csv.gz",
            }.items()
        },
    }
    (REPORTS / "feature_build.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, indent=2))
    return receipt


def preflight() -> dict:
    actual = {name: package_version(name) for name in WINNER_ENV}
    payload = {
        "status": "preflight_complete",
        "project_root": str(ROOT),
        "cache_root": str(CACHE),
        "report_root": str(REPORTS),
        "exact_environment_root": str(TOOLS / ".venv"),
        "reference_commit": first.REFERENCE_COMMIT,
        "project_environment_versions": actual,
        "winner_exact_environment": WINNER_ENV,
        "project_exact_match": {k: actual[k] == v for k, v in WINNER_ENV.items()},
        "known_2026_outcomes_used": False,
    }
    print(json.dumps(payload, indent=2))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "preflight",
            "fetch-first-place-inputs",
            "setup-first-place-env",
            "build-first-place-features",
        ],
    )
    args = parser.parse_args()
    if args.command == "preflight":
        preflight()
    elif args.command == "fetch-first-place-inputs":
        fetch_inputs()
    elif args.command == "setup-first-place-env":
        setup_exact_environment()
    elif args.command == "build-first-place-features":
        build_features()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
