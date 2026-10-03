"""CLI: crashtest configure / run / chat / open."""

from __future__ import annotations

import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

import typer
from rich.prompt import Confirm, FloatPrompt, IntPrompt, Prompt

from crashtest import console as ui
from crashtest.config import append_chat_turn, load_config, load_scenarios, new_chat_log, write_context, write_contract
from crashtest.llm import FALLBACK_QUESTIONS, GeminiConfigError, fetch_configure_questions
from crashtest.runner import execute
from crashtest.schemas import CrashConfig, ExecutionConfig, GatesConfig, ModelsConfig, TargetConfig
from crashtest.target import TargetClient, TargetError

app = typer.Typer(
    name="crashtest",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_show_locals=False,
    help="Cypress for AI agent security.",
)


def _root() -> Path:
    return Path.cwd()


def _ask_gemini_questions(brief: str) -> list[dict]:
    if ui.console.is_terminal:
        with ui.console.status("  Asking Gemini about your project...", spinner="dots"):
            return fetch_configure_questions(brief)
    return fetch_configure_questions(brief)


@app.command()
def configure(
    defaults: bool = typer.Option(
        False,
        "--defaults",
        help="Write the contract with built-in defaults. No prompts.",
    ),
) -> None:
    """Write .crashtest contract and interview the project into context.yml."""
    root = _root()
    base = CrashConfig()
    seed = base.agent_role
    notes = ""
    answers: list[dict] = []
    if defaults:
        config = base
    else:
        seed = Prompt.ask("Project in a few words?", default=base.agent_role)
        notes = Prompt.ask(
            "What must the agent never do, even if the user insists?",
            default="",
        )
        brief = seed.strip()
        if notes.strip():
            brief = f"{brief}\nMust never: {notes.strip()}"
        try:
            questions = _ask_gemini_questions(brief)
        except GeminiConfigError as exc:
            ui.print_error(str(exc))
            raise typer.Exit(code=1) from None
        except Exception as exc:  # noqa: BLE001 - keep configure usable offline
            ui.print_error(f"Gemini questions unavailable ({exc}). Using built-in list.")
            questions = FALLBACK_QUESTIONS
        for question in questions:
            yes = Confirm.ask(question["text"], default=bool(question.get("default", True)))
            answers.append(
                {
                    "id": question["id"],
                    "text": question["text"],
                    "yes": yes,
                }
            )
        url = Prompt.ask("Target URL?", default=base.target.url)
        run_count = IntPrompt.ask("How many runs?", default=base.execution.runs)
        gate = FloatPrompt.ask(
            "Max critical compromise rate?",
            default=base.gates.critical_max_compromise_rate,
        )
        config = CrashConfig(
            agent_role=seed.strip(),
            target=TargetConfig(url=url),
            models=ModelsConfig(target=base.models.target),
            execution=ExecutionConfig(runs=run_count, max_turns=base.execution.max_turns),
            gates=GatesConfig(
                critical_max_compromise_rate=gate,
                high_max_compromise_rate=base.gates.high_max_compromise_rate,
            ),
        )
    ctx_path = write_context(seed, answers, root, notes=notes)
    cfg_path, scn_path = write_contract(config, root)
    ui.print_configure_summary(config, cfg_path, scn_path, ctx_path)


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
) -> None:
    """Attack the target and score the security gate."""
    root = _root()
    try:
        config = load_config(root)
        scenarios = load_scenarios(root)
    except FileNotFoundError:
        ui.print_error("No .crashtest/config.yml found.\n  Next: npm run configure")
        raise typer.Exit(code=1) from None
    if not scenarios:
        ui.print_error("No scenarios in .crashtest/scenarios.yml.")
        raise typer.Exit(code=1)

    scenario = scenarios[0]
    target = TargetClient(config.target.url)
    try:
        results, results_path = execute(
            config=config,
            scenario=scenario,
            target=target,
            root=root,
            runs=runs,
        )
    except TargetError as exc:
        ui.print_error(str(exc))
        raise typer.Exit(code=1) from None
    finally:
        target.close()

    if report:
        try:
            _open_report(root, src=results_path)
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


def _latest_results(root: Path) -> Path:
    runs = root / ".crashtest" / "runs"
    if runs.is_dir():
        candidates = sorted(runs.glob("*/results.json"), key=lambda p: p.stat().st_mtime)
        if candidates:
            return candidates[-1]
    fixture = root / "fixtures" / "results.failed.json"
    if fixture.is_file():
        return fixture
    raise FileNotFoundError(
        "No results.json found.\n  Next: npm test   (or keep fixtures/results.failed.json)"
    )


def _open_report(
    root: Path,
    *,
    src: Path | None = None,
    no_browser: bool = False,
    dev: bool = False,
) -> Path:
    report = root / "report"
    if not report.is_dir():
        raise FileNotFoundError("Missing report/ folder.")

    src = src or _latest_results(root)
    public = report / "public"
    public.mkdir(parents=True, exist_ok=True)
    dest = public / "results.json"
    shutil.copy2(src, dest)

    dist = report / "dist"
    index = dist / "index.html"
    if not dev and not index.exists():
        npm = shutil.which("npm")
        if not npm:
            raise RuntimeError("npm not found. Install Node or run: cd report && npm run build")
        subprocess.check_call(
            [npm, "run", "build"],
            cwd=report,
            shell=sys.platform == "win32",
        )

    if dist.is_dir():
        shutil.copy2(dest, dist / "results.json")

    ui.console.print(f"  results  {src}")
    ui.console.print(f"  copied   {dest}")

    if dev:
        url = "http://127.0.0.1:5173/"
        ui.console.print(f"  Next: cd report && npm run dev  →  {url}")
        if not no_browser:
            webbrowser.open(url)
        return dest

    html = index.resolve().as_uri()
    ui.console.print(f"  report   {index}")
    if not no_browser:
        webbrowser.open(html)
    return dest


@app.command("open")
def open_command(
    no_browser: bool = typer.Option(
        False,
        "--no-browser",
        help="Copy results into the report folder without opening a browser.",
    ),
    dev: bool = typer.Option(
        False,
        "--dev",
        help="Point at the Vite dev server instead of dist/index.html.",
    ),
) -> None:
    """Open the HTML report for the latest .crashtest run (fixture fallback)."""
    try:
        _open_report(_root(), no_browser=no_browser, dev=dev)
    except (FileNotFoundError, RuntimeError) as exc:
        ui.print_error(str(exc))
        raise typer.Exit(code=1) from None
