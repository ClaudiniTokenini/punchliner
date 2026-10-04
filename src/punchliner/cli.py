"""CLI: punchliner configure / run / chat / open."""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

import typer
from rich.prompt import Confirm, FloatPrompt, IntPrompt, Prompt

from punchliner import console as ui
from punchliner.config import (
    append_chat_turn,
    compile_context_summary,
    load_config,
    load_scenarios,
    new_chat_log,
    write_context,
    write_contract,
)
from punchliner.judge import JevError
from punchliner.llm import (
    FALLBACK_QUESTIONS,
    GeminiConfigError,
    fetch_configure_questions,
    fetch_scenarios,
    validate_configure_seed,
)
from punchliner.pack import (
    DEFAULT_PACK_PATH,
    AgentPack,
    find_pack_dir,
    load_pack,
)
from punchliner.runner import execute_suite
from punchliner.schemas import (
    AgentPackConfig,
    PunchConfig,
    ExecutionConfig,
    GatesConfig,
    ModelsConfig,
    TargetConfig,
)
from punchliner.target import TargetClient, TargetError

app = typer.Typer(
    name="punchliner",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_show_locals=False,
    help="Cypress for AI agent security.",
)


def _root() -> Path:
    return Path.cwd()


def _brief(seed: str, notes: str) -> str:
    text = seed.strip()
    if notes.strip():
        return f"{text}\nMust never: {notes.strip()}"
    return text


def _collect_answer(question: dict) -> dict:
    kind = question.get("kind")
    if kind not in {"text", "bool"}:
        kind = "bool" if isinstance(question.get("default"), bool) else "text"
    record = {"id": question["id"], "kind": kind, "text": question["text"]}
    if kind == "text":
        default = str(question.get("default") or "").strip()
        answer = Prompt.ask(question["text"], default=default) if default else Prompt.ask(question["text"])
        record["answer"] = answer.strip()
        return record
    record["yes"] = Confirm.ask(question["text"], default=bool(question.get("default", True)))
    return record


def _ask_gemini_questions(brief: str, agent_context: str = "") -> list[dict]:
    if ui.console.is_terminal:
        with ui.console.status("  Asking Gemini about your project...", spinner="dots"):
            return fetch_configure_questions(brief, agent_context=agent_context)
    return fetch_configure_questions(brief, agent_context=agent_context)


def _ask_gemini_scenarios(summary: str, agent_context: str = "") -> list[dict] | None:
    try:
        if ui.console.is_terminal:
            with ui.console.status("  Generating scenarios with Gemini...", spinner="dots"):
                return fetch_scenarios(summary, agent_context=agent_context)
        return fetch_scenarios(summary, agent_context=agent_context)
    except Exception as exc:  # noqa: BLE001 - template fallback
        ui.print_error(f"Scenario generation unavailable ({exc}). Using template.")
        return None


def _ask_pack_path(root: Path, default: str) -> AgentPack:
    spec = default
    while True:
        spec = Prompt.ask("Agent pack path?", default=spec)
        found = find_pack_dir(spec, root)
        if found is None:
            ui.print_error(
                f"No agent pack at {spec.strip()}.\n  Need context.json and tools.json."
            )
            continue
        pack = load_pack(found, relpath=spec.strip())
        ui.console.print(f"  pack   {pack.role}")
        ui.console.print(f"  tools  {', '.join(pack.tool_names)}")
        return pack


def _align_seed_with_pack(seed: str, notes: str, pack: AgentPack) -> tuple[str, str]:
    while True:
        brief = _brief(seed, notes)
        try:
            if ui.console.is_terminal:
                with ui.console.status(
                    "  Checking description against the agent pack...",
                    spinner="dots",
                ):
                    verdict = validate_configure_seed(brief, pack.digest())
            else:
                verdict = validate_configure_seed(brief, pack.digest())
        except Exception as exc:  # noqa: BLE001 - configure must stay usable
            ui.print_error(f"Seed check unavailable ({exc}). Continuing.")
            return seed, notes
        if verdict.get("ok", True):
            return seed, notes
        reason = verdict.get("reason") or "Description does not match the agent pack."
        ui.print_error(reason)
        if Confirm.ask("Continue anyway?", default=False):
            return seed, notes
        seed = Prompt.ask("Project in a few words?", default=seed)
        notes = Prompt.ask(
            "What must the agent never do, even if the user insists?",
            default=notes,
        )


def _try_default_pack(root: Path) -> AgentPack | None:
    found = find_pack_dir(DEFAULT_PACK_PATH, root)
    if found is None:
        return None
    return load_pack(found, relpath=DEFAULT_PACK_PATH)


def _configure(defaults: bool) -> None:
    root = _root()
    base = PunchConfig()
    seed = base.agent_role
    notes = ""
    answers: list[dict] = []
    generated: list[dict] | None = None
    pack_snapshot: dict | None = None
    pack: AgentPack | None = None
    if defaults:
        pack = _try_default_pack(root)
        if pack is not None:
            pack_snapshot = pack.snapshot()
            seed = pack.role
            config = PunchConfig(
                agent_role=pack.role,
                agent=AgentPackConfig(path=pack.relpath),
            )
        else:
            config = base
    else:
        pack = _ask_pack_path(root, DEFAULT_PACK_PATH)
        pack_snapshot = pack.snapshot()
        seed = Prompt.ask("Project in a few words?", default=pack.role)
        notes = Prompt.ask(
            "What must the agent never do, even if the user insists?",
            default="",
        )
        seed, notes = _align_seed_with_pack(seed, notes, pack)
        brief = _brief(seed, notes)
        digest = pack.digest()
        try:
            questions = _ask_gemini_questions(brief, digest)
        except GeminiConfigError as exc:
            ui.print_error(str(exc))
            raise typer.Exit(code=1) from None
        except Exception as exc:  # noqa: BLE001 - keep configure usable offline
            ui.print_error(f"Gemini questions unavailable ({exc}). Using built-in list.")
            questions = FALLBACK_QUESTIONS
        for question in questions:
            answers.append(_collect_answer(question))
        url = Prompt.ask("Target URL?", default=base.target.url)
        run_count = IntPrompt.ask("How many runs?", default=base.execution.runs)
        gate = FloatPrompt.ask(
            "Max critical compromise rate?",
            default=base.gates.critical_max_compromise_rate,
        )
        config = PunchConfig(
            agent_role=seed.strip(),
            agent=AgentPackConfig(path=pack.relpath),
            target=TargetConfig(url=url),
            models=ModelsConfig(target=base.models.target),
            execution=ExecutionConfig(runs=run_count, max_turns=base.execution.max_turns),
            gates=GatesConfig(
                critical_max_compromise_rate=gate,
                high_max_compromise_rate=base.gates.high_max_compromise_rate,
            ),
        )
        summary = compile_context_summary(seed, answers, notes, pack_snapshot=pack_snapshot)
        generated = _ask_gemini_scenarios(summary, digest)
        if generated is not None and not generated:
            generated = None

    pack_scenarios_text = None
    if generated is None and pack is not None:
        pack_scn = pack.scenarios_file()
        if pack_scn is not None:
            pack_scenarios_text = pack_scn.read_text(encoding="utf-8")

    ctx_path = write_context(seed, answers, root, notes=notes, pack_snapshot=pack_snapshot)
    cfg_path, scn_path = write_contract(
        config,
        root,
        scenarios=generated,
        scenarios_text=pack_scenarios_text,
        force_scenarios=True,
    )
    ui.print_configure_summary(
        config,
        cfg_path,
        scn_path,
        ctx_path,
        scenarios=load_scenarios(root),
    )


@app.command()
def configure(
    defaults: bool = typer.Option(
        False,
        "--defaults",
        help="Write the contract with built-in defaults. No prompts.",
    ),
) -> None:
    """Write .punchliner contract and interview the project into context.yml."""
    _configure(defaults)


@app.command("init")
def init_command(
    defaults: bool = typer.Option(
        False,
        "--defaults",
        help="Write the contract with built-in defaults. No prompts.",
    ),
) -> None:
    """Alias for configure (Sprint 2 milestone name)."""
    _configure(defaults)


@app.command("run")
def run_command(
    runs: int | None = typer.Option(
        None,
        "--runs",
        min=1,
        help="Override execution.runs from config.yml.",
    ),
    report: bool = typer.Option(
        False,
        "--report",
        "--raport",
        help="After the run, build and open the HTML report.",
    ),
    no_browser: bool = typer.Option(
        False,
        "--no-browser",
        help="With --raport, copy/build the report without opening a browser (CI).",
    ),
) -> None:
    """Attack the target and score the security gate."""
    root = _root()
    try:
        config = load_config(root)
        scenarios = load_scenarios(root)
    except FileNotFoundError:
        ui.print_error("No .punchliner/config.yml found.\n  Next: npm run punchliner:init")
        raise typer.Exit(code=1) from None
    if not scenarios:
        ui.print_error("No scenarios in .punchliner/scenarios.yml.")
        raise typer.Exit(code=1)

    target = TargetClient(config.target.url)
    try:
        results, results_path = execute_suite(
            config=config,
            scenarios=scenarios,
            target=target,
            root=root,
            runs=runs,
        )
    except (TargetError, JevError) as exc:
        ui.print_error(str(exc))
        raise typer.Exit(code=1) from None
    finally:
        target.close()

    if report:
        try:
            _open_report(root, src=results_path, no_browser=no_browser)
        except Exception as exc:  # noqa: BLE001 - still return gate exit code
            ui.print_error(f"Report failed: {exc}")

    raise typer.Exit(code=results.gate.exit_code)


@app.command()
def chat(
    once: str | None = typer.Option(
        None,
        "--once",
        help="Send one message and exit.",
    ),
    url: str = typer.Option(
        "http://127.0.0.1:8000/chat",
        "--url",
        help="Target POST /chat URL.",
    ),
) -> None:
    """Talk to the local demo agent. Use this to show the refund hole by hand."""
    target = TargetClient(url)
    history: list[dict[str, str]] = []
    log_file = new_chat_log()
    try:
        if once is not None:
            _chat_turn(target, once, history, log_file)
            return
        ui.print_chat_hello(url, log_file)
        while True:
            try:
                text = Prompt.ask("  [bold]you[/bold]")
            except (EOFError, KeyboardInterrupt):
                ui.console.print()
                return
            if text.strip().lower() in {"", "q", "quit", "exit"}:
                return
            _chat_turn(target, text, history, log_file)
    except TargetError as exc:
        ui.print_error(str(exc))
        raise typer.Exit(code=1) from None
    finally:
        target.close()


def _chat_turn(
    target: TargetClient,
    text: str,
    history: list[dict[str, str]],
    log_file: Path,
) -> None:
    payload = target.chat(text, history)
    ui.print_chat_reply(payload.get("content") or "", payload.get("tool_calls") or [])
    append_chat_turn(log_file, text, payload)
    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": payload.get("content") or ""})


REPORT_HOST = "127.0.0.1"
REPORT_PORT = 5173


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0


def _runs_dir(root: Path) -> Path:
    return (root / ".punchliner" / "runs").resolve()


def _latest_results(root: Path) -> Path | None:
    runs = _runs_dir(root)
    if not runs.is_dir():
        return None
    newest: Path | None = None
    newest_mtime = -1.0
    for child in runs.iterdir():
        file = child / "results.json"
        if not file.is_file():
            continue
        mtime = file.stat().st_mtime
        if mtime > newest_mtime:
            newest = file
            newest_mtime = mtime
    return newest


def _run_id_from_results(root: Path, src: Path | None) -> str | None:
    if src is None:
        return None
    try:
        runs = _runs_dir(root)
        path = src.resolve()
    except OSError:
        return None
    if path.name != "results.json" or path.parent.parent != runs:
        return None
    return path.parent.name


def _api_run_ids(host: str, port: int) -> list[str] | None:
    try:
        with urlopen(f"http://{host}:{port}/api/runs", timeout=0.5) as response:
            data = json.loads(response.read().decode())
    except (URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None
    if not isinstance(data, list):
        return None
    ids: list[str] = []
    for item in data:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            ids.append(item["id"])
    return ids


def _free_port(host: str, start: int, span: int = 20) -> int:
    for port in range(start, start + span):
        if not _port_open(host, port):
            return port
    raise RuntimeError(f"No free port in {start}-{start + span - 1}.")


def _report_url(run_id: str | None, port: int = REPORT_PORT) -> str:
    base = f"http://{REPORT_HOST}:{port}/"
    if not run_id:
        return base
    return f"{base}?run={quote(run_id)}"


def _start_report_server(report: Path, port: int | None = None) -> subprocess.Popen[bytes]:
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("npm not found. Install Node, then run: cd report && npm install")
    args = [npm, "run", "dev"]
    if port is not None:
        args.extend(["--", "--port", str(port)])
    return subprocess.Popen(
        args,
        cwd=report,
        shell=sys.platform == "win32",
    )


def _wait_for_report(
    proc: subprocess.Popen[bytes],
    port: int = REPORT_PORT,
    timeout: float = 30.0,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("Report server exited before it was ready.")
        if _port_open(REPORT_HOST, port):
            return
        time.sleep(0.2)
    proc.terminate()
    raise RuntimeError(f"Report server did not start on port {port}.")


def _hold_server(proc: subprocess.Popen[bytes]) -> None:
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def _open_report(
    root: Path,
    *,
    src: Path | None = None,
    no_browser: bool = False,
) -> str:
    """Open the live report. Reuse Vite only when it can see this run."""
    report = root / "report"
    if not report.is_dir():
        raise FileNotFoundError("Missing report/ folder.")
    if src is None:
        src = _latest_results(root)
    run_id = _run_id_from_results(root, src)

    started = None
    port = REPORT_PORT
    ids = _api_run_ids(REPORT_HOST, port) if _port_open(REPORT_HOST, port) else None
    server_ok = ids is not None and (run_id in ids if run_id else True)
    if not server_ok:
        if _port_open(REPORT_HOST, port):
            port = _free_port(REPORT_HOST, REPORT_PORT + 1)
            started = _start_report_server(report, port=port)
        else:
            started = _start_report_server(report)
            port = REPORT_PORT
        _wait_for_report(started, port=port)

    url = _report_url(run_id, port=port)
    if src is not None:
        ui.console.print(f"  results  {src}")
    ui.console.print(f"  report   {url}")
    if not no_browser:
        webbrowser.open(url)
    if started is not None:
        _hold_server(started)
    return url


@app.command("open")
def open_command(
    no_browser: bool = typer.Option(
        False,
        "--no-browser",
        help="Start the report server without opening a browser.",
    ),
) -> None:
    """Open the live report for the latest run in .punchliner/runs."""
    root = _root()
    src = _latest_results(root)
    if src is None:
        ui.print_error("No .punchliner/runs yet.\n  Next: npm run punchliner:punch")
        raise typer.Exit(code=1)
    try:
        _open_report(root, src=src, no_browser=no_browser)
    except (FileNotFoundError, RuntimeError) as exc:
        ui.print_error(str(exc))
        raise typer.Exit(code=1) from None
