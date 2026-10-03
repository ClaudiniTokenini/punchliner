"""Standalone reports must not retain an earlier run's embedded artifact."""

import os
from pathlib import Path

from crashtest.cli import _open_report


def report_workspace(root: Path) -> tuple[Path, Path]:
    source = root / "results.json"
    source.write_text('{"run": 1}', encoding="utf-8")
    os.utime(source, (1, 1))
    dist = root / "report" / "dist"
    dist.mkdir(parents=True)
    (dist / "results.json").write_text(source.read_text(), encoding="utf-8")
    index = dist / "index.html"
    index.write_text("<html></html>", encoding="utf-8")
    os.utime(index, (10, 10))
    return source, index


def test_unchanged_report_does_not_rebuild(tmp_path: Path, monkeypatch) -> None:
    source, _ = report_workspace(tmp_path)
    calls = []
    monkeypatch.setattr("crashtest.cli.subprocess.check_call", lambda *args, **kwargs: calls.append(args))
    _open_report(tmp_path, src=source, no_browser=True)
    assert not calls


def test_report_rebuilds_when_source_changes(tmp_path: Path, monkeypatch) -> None:
    source, _ = report_workspace(tmp_path)
    app = tmp_path / "report" / "src" / "App.tsx"
    app.parent.mkdir()
    app.write_text("export default function App() {}", encoding="utf-8")
    calls = []
    monkeypatch.setattr("crashtest.cli.shutil.which", lambda _: "/usr/bin/npm")
    monkeypatch.setattr("crashtest.cli.subprocess.check_call", lambda *args, **kwargs: calls.append(args))
    _open_report(tmp_path, src=source, no_browser=True)
    assert calls == [(["/usr/bin/npm", "run", "build"],)]


def test_report_rebuilds_for_different_artifact_even_with_older_timestamp(tmp_path: Path, monkeypatch) -> None:
    source, _ = report_workspace(tmp_path)
    source.write_text('{"run": 2}', encoding="utf-8")
    os.utime(source, (1, 1))
    calls = []
    monkeypatch.setattr("crashtest.cli.shutil.which", lambda _: "/usr/bin/npm")
    monkeypatch.setattr("crashtest.cli.subprocess.check_call", lambda *args, **kwargs: calls.append(args))
    _open_report(tmp_path, src=source, no_browser=True)
    assert calls == [(["/usr/bin/npm", "run", "build"],)]
    assert (tmp_path / "report" / "dist" / "results.json").read_text() == '{"run": 2}'
