"""Load named sections from PROMPTS.md (paid-API prompt source of truth)."""

from __future__ import annotations

import os
from pathlib import Path


def prompts_path() -> Path:
    override = os.environ.get("CRASHTEST_PROMPTS")
    if override:
        return Path(override).expanduser().resolve()
    packaged = Path(__file__).with_name("PROMPTS.md")
    repo = Path(__file__).resolve().parents[2] / "PROMPTS.md"
    for candidate in (Path.cwd() / "PROMPTS.md", repo, packaged):
        if candidate.exists():
            return candidate
    raise FileNotFoundError("PROMPTS.md not found. Keep it at the repo root.")


def load_prompt(name: str, **placeholders: str) -> str:
    text = prompts_path().read_text(encoding="utf-8")
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
            continue
        if current is None:
            continue
        sections[current].append(line)
    if name not in sections:
        raise KeyError(f"Prompt section {name!r} missing in PROMPTS.md")
    body = "\n".join(sections[name]).strip()
    for key, value in placeholders.items():
        body = body.replace("{" + key + "}", value)
    return body
