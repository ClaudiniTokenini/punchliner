"""CLI: crashtest configure / crashtest run."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.prompt import FloatPrompt, IntPrompt, Prompt

from crashtest import console as ui
from crashtest.config import load_config, load_scenarios, write_contract
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


@app.command()
def configure(
    defaults: bool = typer.Option(
        False,
        "--defaults",
        help="Write the contract with built-in defaults. No prompts.",
    ),
) -> None:
    """Write .crashtest/config.yml with a simple security contract."""
    base = CrashConfig()
    if defaults:
        config = base
    else:
        role = Prompt.ask("What does the agent do?", default=base.agent_role)
        url = Prompt.ask("Target URL?", default=base.target.url)
        model = Prompt.ask("LM Studio model?", default=base.models.target)
        run_count = IntPrompt.ask("How many runs?", default=base.execution.runs)
        gate = FloatPrompt.ask(
            "Max critical compromise rate?",
            default=base.gates.critical_max_compromise_rate,
        )
        config = CrashConfig(
            agent_role=role,
            target=TargetConfig(url=url),
            models=ModelsConfig(target=model),
            execution=ExecutionConfig(runs=run_count, max_turns=base.execution.max_turns),
            gates=GatesConfig(
                critical_max_compromise_rate=gate,
                high_max_compromise_rate=base.gates.high_max_compromise_rate,
            ),
        )
    cfg_path, scn_path = write_contract(config, _root())
    ui.print_configure_summary(config, cfg_path, scn_path)


@app.command("run")
def run_command(
    runs: int | None = typer.Option(
        None,
        "--runs",
        min=1,
        help="Override execution.runs from config.yml.",
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
        results, _ = execute(
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
    try:
        if once is not None:
            _chat_turn(target, once, history)
            return
        ui.print_chat_hello(url)
        while True:
            try:
                text = Prompt.ask("  [bold]you[/bold]")
            except (EOFError, KeyboardInterrupt):
                ui.console.print()
                return
            if text.strip().lower() in {"", "q", "quit", "exit"}:
                return
            _chat_turn(target, text, history)
    except TargetError as exc:
        ui.print_error(str(exc))
        raise typer.Exit(code=1) from None
    finally:
        target.close()


def _chat_turn(target: TargetClient, text: str, history: list[dict[str, str]]) -> None:
    payload = target.chat(text, history)
    ui.print_chat_reply(payload.get("content") or "", payload.get("tool_calls") or [])
    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": payload.get("content") or ""})
