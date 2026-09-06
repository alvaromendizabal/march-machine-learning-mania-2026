from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path


def test_official_zip_ingestion_is_repeatable_and_rejects_conflicts(raw, tmp_path):
    archive = tmp_path / "official.zip"
    with zipfile.ZipFile(archive, "w") as zip_file:
        for path in raw.glob("*.csv"):
            zip_file.write(path, "nested/" + path.name)
    output = tmp_path / "extracted"
    argv = [sys.executable, "scripts/inspect_data.py", str(archive), "--destination", str(output)]
    for _ in range(2):
        result = subprocess.run(argv, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr
    assert len(list(output.glob("*.csv"))) == 8
    (output / "MNCAATourneySeeds.csv").write_text("different")
    result = subprocess.run(argv, capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert "immutable" in result.stderr


def test_preflight_failure_names_missing_files(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "march_mania.research", "--raw", str(tmp_path), "--preflight"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "MRegularSeasonCompactResults.csv" in result.stderr
    assert not (tmp_path / "manifest.json").exists()


def test_notebook_schema_and_code_are_valid():
    import nbformat

    notebook = nbformat.read(Path("notebooks/05_feature_research.ipynb"), as_version=4)
    nbformat.validate(notebook)
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type == "code":
            compile(cell.source, f"cell-{index}", "exec")
