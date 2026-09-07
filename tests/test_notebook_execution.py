from __future__ import annotations

import json
import time

import nbformat
import pytest
from filelock import FileLock, Timeout

from march_mania.publication.notebooks import (
    NOTEBOOKS,
    definition,
    dependency_hashes,
    execute_notebooks,
    validate_execution,
)


class Client:
    calls = 0
    fail = False

    def __init__(self, notebook, **kwargs):
        self.notebook = notebook
        self.kwargs = kwargs

    def execute(self):
        type(self).calls += 1
        time.sleep(0.02)
        if self.fail:
            raise RuntimeError("deliberate execution failure")
        for cell in self.notebook.cells:
            if cell.cell_type == "code":
                cell.execution_count = 1
                cell.outputs = [nbformat.v4.new_output("stream", name="stdout", text="verified\n")]
        return self.notebook


@pytest.fixture
def project(tmp_path):
    Client.calls = 0
    Client.fail = False
    (tmp_path / "notebooks").mkdir()
    for name in NOTEBOOKS[:2]:
        book = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("print(1)")])
        nbformat.write(book, tmp_path / "notebooks" / name)
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports/metric.csv").write_text("brier\n0.2\n")
    return tmp_path


def run(root, **kwargs):
    return execute_notebooks(
        root,
        names=(NOTEBOOKS[0],),
        kernel_name="python3",
        heartbeat_seconds=0.005,
        client_factory=Client,
        **kwargs,
    )


def test_resume_does_not_execute_again_and_can_publish(project):
    first = run(project)
    second = run(project, publish=True)
    assert Client.calls == 1
    assert first["notebooks"] == second["notebooks"]
    validate_execution(nbformat.read(project / "notebooks" / NOTEBOOKS[0], as_version=4))
    log = (project / "outputs/validation/notebooks.jsonl").read_text()
    assert '"event": "heartbeat"' in log and '"event": "task_reused"' in log
    assert '"timestamp"' in log and '"elapsed_seconds"' in log


def test_changed_input_and_source_invalidate_cache(project):
    run(project, publish=True)
    (project / "reports/metric.csv").write_text("brier\n0.1\n")
    run(project)
    assert Client.calls == 2
    path = project / "notebooks" / NOTEBOOKS[0]
    book = nbformat.read(path, as_version=4)
    book.cells[0].source = "print(2)"
    nbformat.write(book, path)
    run(project)
    assert Client.calls == 3


def test_corrupt_cached_outputs_are_reexecuted(project):
    run(project)
    cached = next((project / "outputs/validation/notebook_runs").rglob(NOTEBOOKS[0]))
    cached.write_text("corrupt")
    run(project)
    assert Client.calls == 2


def test_failure_never_overwrites_canonical_notebook_and_is_resumable(project):
    original = (project / "notebooks" / NOTEBOOKS[0]).read_bytes()
    Client.fail = True
    with pytest.raises(RuntimeError, match="deliberate"):
        run(project, publish=True)
    assert (project / "notebooks" / NOTEBOOKS[0]).read_bytes() == original
    assert not list((project / "outputs/validation/notebook_runs").rglob("checkpoint.json"))
    report = json.loads((project / "outputs/validation/notebook_execution.json").read_text())
    assert report["status"] == "failed"
    Client.fail = False
    run(project, publish=True)
    assert Client.calls == 2


def test_definition_excludes_only_execution_state():
    book = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("1")])
    before = definition(book)
    book.cells[0].execution_count = 1
    book.cells[0].metadata.execution = {"start": "time"}
    book.metadata.language_info = {"name": "python", "version": "3.12"}
    assert definition(book) == before
    book.cells[0].metadata.tags = ["skip-execution"]
    assert definition(book) != before


@pytest.mark.parametrize("kind", ["unexecuted", "error", "warning"])
def test_no_incomplete_or_warning_outputs_are_publishable(kind):
    cell = nbformat.v4.new_code_cell("1", execution_count=1)
    if kind == "unexecuted":
        cell.execution_count = None
    elif kind == "error":
        cell.outputs = [
            nbformat.v4.new_output("error", ename="ValueError", evalue="bad", traceback=[])
        ]
    else:
        cell.outputs = [nbformat.v4.new_output("stream", name="stderr", text="UserWarning: bad\n")]
    with pytest.raises(ValueError):
        validate_execution(nbformat.v4.new_notebook(cells=[cell]))


def test_dependency_hashes_ignore_logs_but_detect_local_table_changes(project):
    before = dependency_hashes(project)
    (project / "reports/events.jsonl").write_text("event\n")
    assert dependency_hashes(project) == before
    local = project / "outputs/feature_store"
    local.mkdir(parents=True)
    (local / "data.csv").write_text("changed\n")
    assert dependency_hashes(project) != before


def test_duplicate_names_and_concurrent_publication_are_rejected(project):
    with pytest.raises(ValueError, match="unique canonical"):
        execute_notebooks(project, names=(NOTEBOOKS[0], NOTEBOOKS[0]))
    destination = project / "outputs/validation"
    with FileLock(str(destination / "publication.lock")):
        with pytest.raises(Timeout):
            run(project)


def test_real_kernel_records_cell_progress_and_reuses_completed_notebook(project):
    first = execute_notebooks(project, names=(NOTEBOOKS[0],), kernel_name="python3", publish=True)
    second = run(project)
    assert first["notebooks"] == second["notebooks"]
    assert Client.calls == 0
    log = (project / "outputs/validation/notebooks.jsonl").read_text()
    assert '"event": "cell_started"' in log and '"event": "cell_finished"' in log
    assert '"cell_elapsed_seconds"' in log


def test_interruption_of_second_notebook_preserves_first_checkpoint(project):
    path = project / "notebooks" / NOTEBOOKS[1]
    book = nbformat.read(path, as_version=4)
    book.cells[0].source = "print(2)"
    nbformat.write(book, path)

    class InterruptedClient(Client):
        interrupt = True
        calls = 0

        def execute(self):
            if self.interrupt and self.notebook.cells[0].source == "print(2)":
                type(self).calls += 1
                raise RuntimeError("second notebook interrupted")
            return super().execute()

    arguments = {
        "names": NOTEBOOKS[:2],
        "kernel_name": "python3",
        "client_factory": InterruptedClient,
        "publish": True,
    }
    with pytest.raises(RuntimeError, match="interrupted"):
        execute_notebooks(project, **arguments)
    assert InterruptedClient.calls == 2
    InterruptedClient.interrupt = False
    result = execute_notebooks(project, **arguments)
    assert InterruptedClient.calls == 3
    assert len(result["notebooks"]) == 2


def test_failed_mirror_retries_upload_without_reexecuting(project, monkeypatch):
    import march_mania.publication.notebooks as module

    class Mirror:
        fail = True

        def __init__(self, uri):
            self.uri = uri

        def upload(self, path, key):
            if self.fail:
                raise OSError("replication interrupted")

    monkeypatch.setattr(module, "Mirror", Mirror)
    with pytest.raises(OSError, match="replication"):
        run(project, s3="s3://example/notebooks")
    assert Client.calls == 1
    Mirror.fail = False
    run(project, s3="s3://example/notebooks")
    assert Client.calls == 1


def test_new_submission_bytes_invalidate_notebook_evidence(project):
    before = dependency_hashes(project)
    folder = project / "submissions"
    folder.mkdir()
    path = folder / "submission.csv"
    path.write_text("ID,Pred\n2026_1101_1102,0.5\n")
    restored = dependency_hashes(project)
    assert restored != before
    path.write_text("ID,Pred\n2026_1101_1102,0.6\n")
    assert dependency_hashes(project) != restored
