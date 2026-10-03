"""Rich output in the style of a test runner."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.text import Text

from crashtest.schemas import CrashConfig, Scenario

console = Console(highlight=False)


def print_configure_summary(
    config: CrashConfig,
    config_file: Path,
    scenarios_file: Path,
    context_file: Path | None = None,
    scenarios: list[Scenario] | None = None,
) -> None:
    console.print()
    console.print("  [bold]Agent Crash Test[/bold]")
    console.print()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim", min_width=10)
    table.add_column()
    table.add_row("agent", config.agent_role)
    table.add_row("pack", config.agent.path)
    table.add_row("target", config.target.url)
    table.add_row("model", config.models.target)
    table.add_row("runs", str(config.execution.runs))
    table.add_row(
        "gate",
        f"critical compromise rate = {config.gates.critical_max_compromise_rate:.0%}",
    )
    console.print(table)
    if scenarios:
        console.print()
        console.print(f"  [bold]{len(scenarios)} scenarios[/bold]")
        for item in scenarios:
            line = Text("    - ")
            line.append(item.name, style="bold")
            line.append("  ")
            line.append(item.severity, style="red" if item.severity == "critical" else "yellow")
            console.print(line)
    console.print()
    console.print(f"  wrote     {config_file}")
    console.print(f"  wrote     {scenarios_file}")
    if context_file is not None:
        console.print(f"  wrote     {context_file}")
    console.print()
    console.print("  Next: [bold]npm test[/bold]   or   [bold]npm run test:report[/bold]")
    console.print()


def print_run_banner() -> None:
    console.print()
    console.print("  [bold]> crashtest run[/bold]")
    console.print()


def print_scenario_header(scenario: Scenario) -> None:
    line = Text()
    line.append("  ")
    line.append(scenario.name, style="bold")
    line.append("    ")
    line.append(scenario.severity, style="red" if scenario.severity == "critical" else "yellow")
    line.append("    ")
    line.append(scenario.attack_objective[:60], style="dim")
    console.print(line)
    console.print()


def print_run_line(index: int, total: int, verdict: str, detail: str | None) -> None:
    width = max(len(str(total)), 1)
    if verdict == "COMPROMISED":
        mark = Text("✗", style="bold red")
        label = Text("COMPROMISED", style="bold red")
    elif verdict == "INCONCLUSIVE":
        mark = Text("?", style="bold yellow")
        label = Text("INCONCLUSIVE", style="bold yellow")
    else:
        mark = Text("✓", style="bold green")
        label = Text("BLOCKED", style="bold green")
    row = Text("  ")
    row.append_text(mark)
    row.append(f"  {index:>{width}}  ")
    row.append_text(label)
    if detail:
        row.append("    ")
        row.append(detail, style="dim")
    console.print(row)


def print_run_footer(
    *,
    compromised: int,
    total: int,
    allowed: float,
    passed: bool,
    results_file: Path,
) -> None:
    rate = (compromised / total) if total else 0.0
    console.print()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim", min_width=10)
    table.add_column()
    table.add_row(
        "rate",
        f"{compromised} / {total} compromised    {rate:.0%}",
    )
    table.add_row("allowed", f"{allowed:.0%}")
    console.print(table)
    console.print()
    if passed:
        console.print("  [bold green]GATE PASSED[/bold green]")
    else:
        console.print("  [bold red]GATE FAILED[/bold red]")
    console.print()
    console.print(f"  results  {results_file}")
    console.print()


def print_error(message: str) -> None:
    console.print()
    console.print(f"  [red]{message}[/red]")
    console.print()


def print_chat_hello(url: str, log_file: Path | None = None) -> None:
    console.print()
    console.print("  [bold]Target agent[/bold]  (customer support, prompt-only auth)")
    console.print(f"  [dim]{url}[/dim]")
    console.print("  [dim]empty line or q to quit. Try a 499 PLN refund on order 4812.[/dim]")
    if log_file is not None:
        console.print(f"  [dim]log  {log_file}[/dim]")
    console.print()


def print_chat_reply(content: str, tool_calls: list[dict]) -> None:
    console.print(f"  [bold]agent[/bold]  {content}")
    for tool_call in tool_calls:
        name = str(tool_call.get("name", "?"))
        arguments = tool_call.get("arguments") or {}
        compact = ", ".join(f"{key}={value}" for key, value in arguments.items())
        hot = {
            "issue_refund",
            "update_salary",
            "export_payroll",
            "create_deploy",
            "rotate_api_key",
            "open_firewall",
        }
        style = "bold red" if name in hot else "dim"
        console.print(f"  [{style}]tool   {name}({compact})[/{style}]")
    console.print()
