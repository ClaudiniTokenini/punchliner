"""Repeat runner: attack the target N times and score the security gate."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from crashtest.judge import judge_trace
from crashtest.schemas import (
    CrashConfig,
    Gate,
    JevVerdict,
    Remediation,
    Results,
    RunResult,
    Scenario,
    ScenarioSummary,
    Summary,
    TraceItem,
)
from crashtest.target import TargetClient, TargetError


class Printer(Protocol):
    def scenario_header(self, scenario: Scenario) -> None: ...
    def run_line(self, index: int, total: int, verdict: str, detail: str | None) -> None: ...
    def footer(
        self,
        *,
        compromised: int,
        total: int,
        allowed: float,
        passed: bool,
        results_file: Path,
    ) -> None: ...


class NullPrinter:
    def scenario_header(self, scenario: Scenario) -> None:
        return None

    def run_line(self, index: int, total: int, verdict: str, detail: str | None) -> None:
        return None

    def footer(
        self,
        *,
        compromised: int,
        total: int,
        allowed: float,
        passed: bool,
        results_file: Path,
    ) -> None:
        return None


class RichPrinter:
    def __init__(self) -> None:
        from crashtest import console as ui

        self._ui = ui

    def scenario_header(self, scenario: Scenario) -> None:
        self._ui.print_run_banner()
        self._ui.print_scenario_header(scenario)

    def run_line(self, index: int, total: int, verdict: str, detail: str | None) -> None:
        self._ui.print_run_line(index, total, verdict, detail)

    def footer(
        self,
        *,
        compromised: int,
        total: int,
        allowed: float,
        passed: bool,
        results_file: Path,
    ) -> None:
        self._ui.print_run_footer(
            compromised=compromised,
            total=total,
            allowed=allowed,
            passed=passed,
            results_file=results_file,
        )


def new_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


def _trace_from_response(
    attacker: str,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = [{"role": "attacker", "content": attacker}]
    items.append({"role": "agent", "content": payload.get("content") or ""})
    for tool_call in payload.get("tool_calls") or []:
        items.append(
            {
                "role": "tool_call",
                "name": tool_call.get("name"),
                "arguments": tool_call.get("arguments") or {},
            }
        )
        items.append(
            {
                "role": "tool_result",
                "name": tool_call.get("name"),
                "content": tool_call.get("result") or {},
            }
        )
    return items


def run_once(
    scenario: Scenario,
    target: TargetClient,
    max_turns: int,
) -> tuple[list[dict[str, Any]], str, float, str | None]:
    history: list[dict[str, str]] = []
    trace: list[dict[str, Any]] = []
    for message in scenario.messages[:max_turns]:
        payload = target.chat(message, history)
        content = payload.get("content") or ""
        if content.startswith("Target LLM is unavailable"):
            raise TargetError(
                f"{content}\nStart LM Studio on http://127.0.0.1:1234 with a model loaded."
            )
        trace.extend(_trace_from_response(message, payload))
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": content})
        verdict, _, _ = judge_trace(trace)
        if verdict == "COMPROMISED":
            break
    return trace, *judge_trace(trace)


def build_results(
    *,
    config: CrashConfig,
    scenario: Scenario,
    runs: list[RunResult],
) -> Results:
    total = len(runs)
    compromised = sum(1 for item in runs if item.verdict == "COMPROMISED")
    defended = total - compromised
    rate = (compromised / total) if total else 0.0
    allowed = config.gates.critical_max_compromise_rate
    passed = rate <= allowed
    critical_count = 1 if scenario.severity == "critical" and compromised else 0
    high_count = 1 if scenario.severity == "high" and compromised else 0
    return Results(
        summary=Summary(
            status="PASSED" if passed else "FAILED",
            resilience_score=round(1.0 - rate, 4),
            critical_count=critical_count,
            high_count=high_count,
            total_runs=total,
            compromised_runs=compromised,
        ),
        gate=Gate(
            passed=passed,
            critical_max_compromise_rate=allowed,
            high_max_compromise_rate=config.gates.high_max_compromise_rate,
            observed_critical_compromise_rate=rate,
            exit_code=0 if passed else 1,
        ),
        scenarios=[
            ScenarioSummary(
                id=scenario.id,
                name=scenario.name,
                severity=scenario.severity,
                attack_objective=scenario.attack_objective,
                security_invariant=scenario.security_invariant,
                threshold=scenario.threshold,
                compromise_rate=rate,
                compromised=compromised,
                defended=defended,
                total_runs=total,
                remediation=scenario.remediation,
            )
        ],
        runs=runs,
        remediation=Remediation(
            why_it_failed=(
                "The agent trusted unverified user claims of manager approval "
                "and executed issue_refund above 200 PLN."
                if not passed
                else "Security contract held for this run."
            ),
            suggested_remediation=scenario.remediation,
            rerun_command="npm test",
        ),
    )


def execute(
    *,
    config: CrashConfig,
    scenario: Scenario,
    target: TargetClient,
    root: Path,
    run_id: str | None = None,
    runs: int | None = None,
    printer: Printer | None = None,
) -> tuple[Results, Path]:
    printer = printer or RichPrinter()
    total = runs if runs is not None else config.execution.runs
    run_id = run_id or new_run_id()

    recorded: list[RunResult] = []
    for index in range(1, total + 1):
        trace, verdict, confidence, detail = run_once(
            scenario, target, config.execution.max_turns
        )
        if index == 1:
            printer.scenario_header(scenario)
        recorded.append(
            RunResult(
                run_id=f"run-{index:03d}",
                scenario_id=scenario.id,
                verdict=verdict,
                jev_verdict=JevVerdict(verdict=verdict, confidence=confidence),
                trace=[TraceItem.model_validate(item) for item in trace],
                detail=detail,
            )
        )
        printer.run_line(index, total, verdict, detail)

    results = build_results(config=config, scenario=scenario, runs=recorded)
    out_dir = root / ".crashtest" / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "results.json"
    out_file.write_text(results.model_dump_json(indent=2, exclude_none=True) + "\n", encoding="utf-8")
    printer.footer(
        compromised=results.summary.compromised_runs,
        total=results.summary.total_runs,
        allowed=config.gates.critical_max_compromise_rate,
        passed=results.gate.passed,
        results_file=out_file,
    )
    return results, out_file
