"""Load and write .crashtest/config.yml and scenarios.yml."""

from __future__ import annotations

from pathlib import Path

import yaml

from crashtest.schemas import CrashConfig, Scenario

CONFIG_NAME = "config.yml"
SCENARIOS_NAME = "scenarios.yml"


def crashtest_dir(root: Path | None = None) -> Path:
    return (root or Path.cwd()) / ".crashtest"


def config_path(root: Path | None = None) -> Path:
    return crashtest_dir(root) / CONFIG_NAME


def scenarios_path(root: Path | None = None) -> Path:
    return crashtest_dir(root) / SCENARIOS_NAME


def template_scenarios() -> str:
    return (Path(__file__).parent / "templates" / SCENARIOS_NAME).read_text(encoding="utf-8")


def dump_config(config: CrashConfig) -> str:
    return yaml.safe_dump(config.model_dump(), sort_keys=False, default_flow_style=False)


def write_contract(config: CrashConfig, root: Path | None = None) -> tuple[Path, Path]:
    directory = crashtest_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    cfg = config_path(root)
    scn = scenarios_path(root)
    cfg.write_text(dump_config(config), encoding="utf-8")
    if not scn.exists():
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
