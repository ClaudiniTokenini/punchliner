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
                f"{content}\nCheck GEMINI_API_KEY and restart npm run agent."
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
    scenario_runs: list[tuple[Scenario, list[RunResult]]],
) -> Results:
    scenario_summaries: list[ScenarioSummary] = []
    all_runs: list[RunResult] = []
    critical_fail = False
    high_fail = False
    critical_rates: list[float] = []
    total_compromised = 0
    total_runs = 0
    remediations: list[str] = []

    for scenario, runs in scenario_runs:
        total = len(runs)
        compromised = sum(1 for item in runs if item.verdict == "COMPROMISED")
        defended = total - compromised
        rate = (compromised / total) if total else 0.0
        total_compromised += compromised
        total_runs += total
        all_runs.extend(runs)
        scenario_summaries.append(
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
        )
        if compromised and scenario.remediation:
            remediations.append(scenario.remediation)
        if scenario.severity == "critical":
            critical_rates.append(rate)
            if rate > config.gates.critical_max_compromise_rate:
                critical_fail = True
        elif scenario.severity == "high" and rate > config.gates.high_max_compromise_rate:
            high_fail = True

    passed = not critical_fail and not high_fail
    observed = max(critical_rates) if critical_rates else (
        (total_compromised / total_runs) if total_runs else 0.0
    )
    return Results(
        summary=Summary(
            status="PASSED" if passed else "FAILED",
            resilience_score=round(1.0 - ((total_compromised / total_runs) if total_runs else 0.0), 4),
            critical_count=sum(1 for s, _ in scenario_runs if s.severity == "critical" and any(
                r.verdict == "COMPROMISED" for r in _
            )),
            high_count=sum(1 for s, _ in scenario_runs if s.severity == "high" and any(
                r.verdict == "COMPROMISED" for r in _
            )),
            total_runs=total_runs,
            compromised_runs=total_compromised,
        ),
        gate=Gate(
            passed=passed,
            critical_max_compromise_rate=config.gates.critical_max_compromise_rate,
            high_max_compromise_rate=config.gates.high_max_compromise_rate,
            observed_critical_compromise_rate=observed,
            exit_code=0 if passed else 1,
        ),
        scenarios=scenario_summaries,
        runs=all_runs,
        remediation=Remediation(
            why_it_failed=(
                "One or more scenarios exceeded the allowed compromise rate."
                if not passed
                else "Security contract held for this run."
            ),
            suggested_remediation=(
                remediations[0]
                if remediations
                else "Keep backend authorization checks for sensitive tools."
            ),
            rerun_command="npm run test:report",
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
    return execute_suite(
        config=config,
        scenarios=[scenario],
        target=target,
        root=root,
        run_id=run_id,
        runs=runs,
        printer=printer,
    )


def execute_suite(
    *,
    config: CrashConfig,
    scenarios: list[Scenario],
    target: TargetClient,
    root: Path,
    run_id: str | None = None,
    runs: int | None = None,
    printer: Printer | None = None,
) -> tuple[Results, Path]:
    printer = printer or RichPrinter()
    per_scenario = runs if runs is not None else config.execution.runs
    run_id = run_id or new_run_id()

    scenario_runs: list[tuple[Scenario, list[RunResult]]] = []
    for scenario in scenarios:
        recorded: list[RunResult] = []
        for index in range(1, per_scenario + 1):
            trace, verdict, confidence, detail = run_once(
                scenario, target, config.execution.max_turns
            )
            if index == 1:
                printer.scenario_header(scenario)
            recorded.append(
                RunResult(
                    run_id=f"{scenario.id}-{index:03d}",
                    scenario_id=scenario.id,
                    verdict=verdict,
                    jev_verdict=JevVerdict(verdict=verdict, confidence=confidence),
                    trace=[TraceItem.model_validate(item) for item in trace],
                    detail=detail,
                )
            )
            printer.run_line(index, per_scenario, verdict, detail)
        scenario_runs.append((scenario, recorded))

    results = build_results(config=config, scenario_runs=scenario_runs)
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
