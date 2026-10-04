"""Live report open must not rebuild a frozen HTML artifact."""

from pathlib import Path

from punchliner.cli import _open_report


def test_open_starts_vite_when_port_is_free(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "report").mkdir()
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
    monkeypatch.setattr("punchliner.cli._wait_for_report", lambda _proc: None)
    held: list[Proc] = []
    monkeypatch.setattr("punchliner.cli._hold_server", lambda proc: held.append(proc))

    url = _open_report(tmp_path, no_browser=True)

    assert started
    assert held
    assert url.startswith("http://127.0.0.1:5173")
