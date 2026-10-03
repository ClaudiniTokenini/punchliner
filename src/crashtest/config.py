"""Load and write .crashtest/config.yml and scenarios.yml."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import yaml

from crashtest.schemas import CrashConfig, Scenario

CONFIG_NAME = "config.yml"
SCENARIOS_NAME = "scenarios.yml"
CONTEXT_NAME = "context.yml"


def crashtest_dir(root: Path | None = None) -> Path:
    return (root or Path.cwd()) / ".crashtest"


def config_path(root: Path | None = None) -> Path:
    return crashtest_dir(root) / CONFIG_NAME


def context_path(root: Path | None = None) -> Path:
    return crashtest_dir(root) / CONTEXT_NAME


def scenarios_path(root: Path | None = None) -> Path:
    return crashtest_dir(root) / SCENARIOS_NAME


def template_scenarios() -> str:
    return (Path(__file__).parent / "templates" / SCENARIOS_NAME).read_text(encoding="utf-8")


def dump_config(config: CrashConfig) -> str:
    return yaml.safe_dump(config.model_dump(), sort_keys=False, default_flow_style=False)


def compile_context_summary(seed: str, answers: list[dict], notes: str = "") -> str:
    lines = [seed.strip()]
    if notes.strip():
        lines.append("Must never: " + notes.strip())
    for item in answers:
        flag = "yes" if item.get("yes") else "no"
        lines.append(f"- {item.get('text', item.get('id', 'q'))} {flag}")
    return "\n".join(lines)


def write_context(
    seed: str,
    answers: list[dict],
    root: Path | None = None,
    notes: str = "",
) -> Path:
    directory = crashtest_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "seed": seed.strip(),
        "notes": notes.strip(),
        "answers": answers,
        "summary": compile_context_summary(seed, answers, notes),
    }
    path = context_path(root)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, default_flow_style=False), encoding="utf-8")
    return path


def write_scenarios(scenarios: list[Scenario] | list[dict], root: Path | None = None) -> Path:
    directory = crashtest_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    payload: list[dict] = []
    for item in scenarios:
        if isinstance(item, Scenario):
            payload.append(item.model_dump())
        else:
            payload.append(Scenario.model_validate(item).model_dump())
    path = scenarios_path(root)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    return path


def write_contract(
    config: CrashConfig,
    root: Path | None = None,
    *,
    scenarios: list[Scenario] | list[dict] | None = None,
    force_scenarios: bool = False,
) -> tuple[Path, Path]:
    directory = crashtest_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    cfg = config_path(root)
    scn = scenarios_path(root)
    cfg.write_text(dump_config(config), encoding="utf-8")
    if scenarios is not None:
        write_scenarios(scenarios, root)
    elif force_scenarios or not scn.exists():
        scn.write_text(template_scenarios(), encoding="utf-8")
    return cfg, scn


def load_config(root: Path | None = None) -> CrashConfig:
    path = config_path(root)
    if not path.exists():
        raise FileNotFoundError(str(path))
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return CrashConfig.model_validate(raw)


def load_scenarios(root: Path | None = None) -> list[Scenario]:
    path = scenarios_path(root)
    if not path.exists():
        raise FileNotFoundError(str(path))
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or []
    if isinstance(raw, dict) and "scenarios" in raw:
        raw = raw["scenarios"]
    return [Scenario.model_validate(item) for item in raw]


def new_chat_log(root: Path | None = None) -> Path:
    directory = crashtest_dir(root) / "chat"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.jsonl"
    path.touch()
    return path


def append_chat_turn(path: Path, user: str, payload: dict) -> None:
    line = {
        "ts": datetime.now(UTC).isoformat(),
        "user": user,
        "agent": payload.get("content") or "",
        "tool_calls": payload.get("tool_calls") or [],
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, default=str) + "\n")

