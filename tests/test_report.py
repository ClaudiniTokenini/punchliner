"""Live report open must not rebuild a frozen HTML artifact."""

from pathlib import Path

from punchliner.cli import _open_report


def _write_run(tmp_path: Path, run_id: str = "20261004-044004") -> Path:
    src = tmp_path / ".punchliner" / "runs" / run_id / "results.json"
    src.parent.mkdir(parents=True)
    src.write_text("{}", encoding="utf-8")
    return src


def test_open_starts_vite_on_latest_run(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "report").mkdir()
    _write_run(tmp_path)
    started: list[object] = []

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

    monkeypatch.setattr("punchliner.cli._port_open", lambda *_args, **_kwargs: False)
    monkeypatch.setattr("punchliner.cli.shutil.which", lambda _name: "/usr/bin/npm")
    monkeypatch.setattr("punchliner.cli.subprocess.Popen", fake_popen)
    monkeypatch.setattr("punchliner.cli._wait_for_report", lambda _proc, port=5173: None)
    held: list[Proc] = []
    monkeypatch.setattr("punchliner.cli._hold_server", lambda proc: held.append(proc))

    url = _open_report(tmp_path, no_browser=True)

    assert started
    assert held
    assert "run=20261004-044004" in url


def test_open_skips_stale_server_without_the_run(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "report").mkdir()
    _write_run(tmp_path)
    started: list[object] = []

    class Proc:
        def poll(self) -> None:
            return None

        def wait(self, timeout: float | None = None) -> int:
            return 0

        def terminate(self) -> None:
            return None

    monkeypatch.setattr("punchliner.cli._port_open", lambda _host, port: port == 5173)
    monkeypatch.setattr("punchliner.cli._api_run_ids", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("punchliner.cli.shutil.which", lambda _name: "/usr/bin/npm")
    monkeypatch.setattr(
        "punchliner.cli.subprocess.Popen",
        lambda args, **kwargs: started.append(args) or Proc(),
    )
    monkeypatch.setattr("punchliner.cli._wait_for_report", lambda _proc, port=5173: None)
    monkeypatch.setattr("punchliner.cli._hold_server", lambda _proc: None)

    url = _open_report(tmp_path, no_browser=True)

    assert started
    assert "--port" in started[0]
    assert "5174" in started[0]
    assert "5174" in url
    assert "run=20261004-044004" in url
