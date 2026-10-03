"""Load the ecommerce-support agent pack (prompt, tools, few-shot)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

PACK_ENV = "AGENT_PACK"


def pack_dir() -> Path:
    override = os.environ.get(PACK_ENV)
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parent.parent / "agents" / "ecommerce-support"


def load_profile(root: Path | None = None) -> dict[str, Any]:
    path = (root or pack_dir()) / "PROFILE.yml"
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_tools_schema(root: Path | None = None) -> list[dict[str, Any]]:
    path = (root or pack_dir()) / "tools.json"
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_system_prompt(root: Path | None = None, include_examples: bool = False) -> str:
    root = root or pack_dir()
    system = (root / "SYSTEM.md").read_text(encoding="utf-8").strip()
    if not include_examples:
        return system
    examples_path = root / "examples.jsonl"
    if not examples_path.exists():
        return system
    chunks = ["## Examples"]
    for line in examples_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        example = json.loads(line)
        example_id = example.get("id", "example")
        parts = [f"### {example_id}"]
        for message in example.get("messages", []):
            role = str(message.get("role", "user")).capitalize()
            parts.append(f"{role}: {message.get('content', '')}")
        chunks.append("\n".join(parts))
    return system + "\n\n" + "\n\n".join(chunks)
