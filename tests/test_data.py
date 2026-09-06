from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from march_mania.data import authenticate, list_files, run, unpack_file


def test_authentication_exit_becomes_actionable_error(monkeypatch):
    import sys
    from unittest.mock import Mock

    api = Mock()
    api.authenticate.side_effect = SystemExit(1)
    module = SimpleNamespace(KaggleApi=lambda: api)
    monkeypatch.setitem(sys.modules, "kaggle.api.kaggle_api_extended", module)
    with pytest.raises(RuntimeError, match="auth login"):
        authenticate()


class KaggleFixture:
    def __init__(self, raw):
        self.raw = raw
        self.names = sorted(p.name for p in raw.glob("*.csv"))
        self.calls = []
        self.fail = None

    def competition_list_files(self, competition, page_token, page_size):
        start = int(page_token or 0)
        names = self.names[start : start + 3]
        files = [
            SimpleNamespace(
                name=n, total_bytes=(self.raw / n).stat().st_size, creation_date="2026-09-06"
            )
            for n in names
        ]
        return SimpleNamespace(
            files=files, next_page_token=str(start + 3) if start + 3 < len(self.names) else None
        )

    def competition_download_file(self, competition, name, path, force, quiet):
        self.calls.append(name)
        if name == self.fail:
            raise ConnectionError("private request details must not enter logs")
        shutil.copyfile(self.raw / name, Path(path) / name)


def test_paginated_kaggle_download_resumes_completed_files(raw, tmp_path):
    api = KaggleFixture(raw)
    assert len(list_files(api)) == 8
    api.fail = api.names[2]
    output = tmp_path / "download"
    with pytest.raises(RuntimeError, match="interrupted"):
        run(output, api=api)
    assert "private request details" not in (output / "events.jsonl").read_text()
    api.fail = None
    result = run(output, api=api)
    assert result["status"] == "completed"
    assert api.calls.count(api.names[0]) == 1
    assert api.calls.count(api.names[1]) == 1
    assert api.calls.count(api.names[2]) == 2
    manifest = json.loads((output / "data_manifest.json").read_text())
    assert len(manifest["sha256"]) == 8
    before = list(api.calls)
    run(output, api=api)
    assert api.calls == before
    (output / "raw" / api.names[0]).write_text("unexpected edit")
    with pytest.raises(ValueError, match="raw file changed"):
        run(output, api=api)


def test_zip_checks_and_safe_extraction(tmp_path):
    download, target = tmp_path / "download", tmp_path / "target"
    download.mkdir()
    target.mkdir()
    with zipfile.ZipFile(download / "data.zip", "w") as archive:
        archive.writestr("folder/data.csv", "a,b\n1,2\n")
    result = unpack_file(download, "data.csv", 8, target)
    assert result.read_text() == "a,b\n1,2\n"
    with pytest.raises(ValueError, match="size"):
        unpack_file(download, "data.csv", 9, target)
    with zipfile.ZipFile(download / "data.zip", "w") as archive:
        archive.writestr("../other.csv", "a,b\n1,2\n")
    with pytest.raises(ValueError, match="match"):
        unpack_file(download, "data.csv", 8, target)
    assert not (tmp_path / "other.csv").exists()


def test_unsafe_and_duplicate_kaggle_names_rejected(raw):
    api = KaggleFixture(raw)
    api.names = ["../secret.csv"]
    api.competition_list_files = lambda *args, **kwargs: SimpleNamespace(
        files=[SimpleNamespace(name="../secret.csv", total_bytes=1)], next_page_token=None
    )
    with pytest.raises(ValueError, match="Unsafe"):
        list_files(api)
