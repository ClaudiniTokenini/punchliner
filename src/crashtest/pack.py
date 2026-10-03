"""Load a visible agent pack (context.json, tools.json, db/)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PACK_ENV = "AGENT_PACK"
DEFAULT_PACK_PATH = "demo-agent/shop-assistant"
CONTEXT_NAME = "context.json"
TOOLS_NAME = "tools.json"


class PackError(FileNotFoundError):
    pass


@dataclass
class AgentPack:
    path: Path
    relpath: str
    name: str
    role: str
    prompt_id: str
    authorization: str
    refund_limit_pln: float | None
    tool_names: list[str]
    tools_schema: list[dict[str, Any]]
    context: dict[str, Any]
    orders: dict[str, Any]
    customers: dict[str, Any]

    def digest(self) -> str:
        lines = [
            f"path: {self.relpath}",
            f"name: {self.name}",
            f"role: {self.role}",
            f"prompt_id: {self.prompt_id}",
            f"authorization: {self.authorization}",
        ]
        if self.refund_limit_pln is not None:
            lines.append(f"refund_limit_pln: {self.refund_limit_pln}")
        if self.tool_names:
            lines.append("tools: " + ", ".join(self.tool_names))
        if self.orders:
            lines.append("orders: " + ", ".join(str(key) for key in self.orders))
        if self.customers:
            lines.append("customers: " + ", ".join(str(key) for key in self.customers))
        return "\n".join(lines)

    def snapshot(self) -> dict[str, Any]:
        return {
            "path": self.relpath,
            "name": self.name,
            "role": self.role,
            "prompt_id": self.prompt_id,
            "authorization": self.authorization,
            "refund_limit_pln": self.refund_limit_pln,
            "tools": list(self.tool_names),
            "orders": [str(key) for key in self.orders],
        }


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def is_pack_dir(path: Path) -> bool:
    return path.is_dir() and (path / CONTEXT_NAME).is_file() and (path / TOOLS_NAME).is_file()


def find_pack_dir(spec: str, root: Path | None = None) -> Path | None:
    raw = spec.strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    bases = [root or Path.cwd(), repo_root()]
    candidates: list[Path] = []
    if path.is_absolute():
        candidates.append(path)
    else:
        for base in bases:
            candidates.append((base / path).resolve())
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if is_pack_dir(candidate):
            return candidate
    return None


def _configured_path(root: Path) -> str | None:
    path = root / ".crashtest" / "config.yml"
    if not path.is_file():
        return None
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    agent = raw.get("agent") or {}
    if not isinstance(agent, dict):
        return None
    value = agent.get("path")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def resolve_pack_path(configured: str | None = None, *, root: Path | None = None) -> Path:
    cwd = root or Path.cwd()
    specs: list[str] = []
    env = os.environ.get(PACK_ENV, "").strip()
    if env:
        specs.append(env)
    if configured and configured.strip():
        specs.append(configured.strip())
    else:
        from_config = _configured_path(cwd)
        if from_config:
            specs.append(from_config)
    specs.append(DEFAULT_PACK_PATH)
    for spec in specs:
        found = find_pack_dir(spec, cwd)
        if found is not None:
            return found
    raise PackError(
        f"Agent pack not found ({DEFAULT_PACK_PATH}). "
        "Need a folder with context.json and tools.json."
    )


def _load_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_pack(path: Path, relpath: str | None = None) -> AgentPack:
    if not is_pack_dir(path):
        raise PackError(f"No agent pack at {path}. Need context.json and tools.json.")
    context = _load_json(path / CONTEXT_NAME, {})
    if not isinstance(context, dict):
        raise PackError(f"Invalid {CONTEXT_NAME} in {path}.")
    tools_schema = _load_json(path / TOOLS_NAME, [])
    if not isinstance(tools_schema, list):
        raise PackError(f"Invalid {TOOLS_NAME} in {path}.")
    orders = _load_json(path / "db" / "orders.json", {})
    customers = _load_json(path / "db" / "customers.json", {})
    if not isinstance(orders, dict):
        orders = {}
    if not isinstance(customers, dict):
        customers = {}
    named = context.get("tools") or []
    tool_names = [str(item) for item in named] if isinstance(named, list) else []
    if not tool_names:
        tool_names = [
            str((item.get("function") or {}).get("name"))
            for item in tools_schema
            if isinstance(item, dict) and (item.get("function") or {}).get("name")
        ]
    limit = context.get("refund_limit_pln")
    try:
        refund_limit = float(limit) if limit is not None else None
    except (TypeError, ValueError):
        refund_limit = None
    display = relpath.strip() if relpath else str(path)
    return AgentPack(
        path=path.resolve(),
        relpath=display,
        name=str(context.get("name") or path.name),
        role=str(context.get("role") or path.name),
        prompt_id=str(context.get("prompt_id") or "target_agent"),
        authorization=str(context.get("authorization") or "prompt-only"),
        refund_limit_pln=refund_limit,
        tool_names=tool_names,
        tools_schema=tools_schema,
        context=context,
        orders=orders,
        customers=customers,
    )


def load_active_pack(*, root: Path | None = None) -> AgentPack:
    cwd = root or Path.cwd()
    path = resolve_pack_path(root=cwd)
    relpath = os.environ.get(PACK_ENV, "").strip() or _configured_path(cwd) or DEFAULT_PACK_PATH
    return load_pack(path, relpath=relpath)
