"""Live report open must not rebuild a frozen HTML artifact."""

from pathlib import Path

from crashtest.cli import _open_report


def test_open_does_not_build_when_server_is_up(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "report").mkdir()
    src = tmp_path / ".crashtest" / "runs" / "20261003-120000" / "results.json"
    src.parent.mkdir(parents=True)
    src.write_text("{}", encoding="utf-8")
    calls: list[object] = []
    monkeypatch.setattr("crashtest.cli._port_open", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        "crashtest.cli.subprocess.Popen",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    monkeypatch.setattr("crashtest.cli.webbrowser.open", lambda *_args, **_kwargs: None)

    url = _open_report(tmp_path, src=src, no_browser=True)

    assert calls == []
    assert url == "http://127.0.0.1:5173/?run=20261003-120000"


def test_open_starts_vite_when_port_is_free(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "report").mkdir()
    started: list[tuple[list[str], Path]] = []

    class Proc:
        def poll(self) -> None:
            return None

        def wait(self, timeout: float | None = None) -> int:
            return 0

        def terminate(self) -> None:
            return None

    def fake_popen(args: list[str], **kwargs: object) -> Proc:
        started.append((args, kwargs["cwd"]))
        return Proc()

    monkeypatch.setattr("crashtest.cli._port_open", lambda *_args, **_kwargs: False)
    monkeypatch.setattr("crashtest.cli.shutil.which", lambda _name: "/usr/bin/npm")
    monkeypatch.setattr("crashtest.cli.subprocess.Popen", fake_popen)
    monkeypatch.setattr("crashtest.cli._wait_for_report", lambda _proc: None)
    held: list[Proc] = []
    monkeypatch.setattr("crashtest.cli._hold_server", lambda proc: held.append(proc))

    url = _open_report(tmp_path, no_browser=True)

    assert started == [(["/usr/bin/npm", "run", "dev"], tmp_path / "report")]
    assert held
    assert url == "http://127.0.0.1:5173/"
