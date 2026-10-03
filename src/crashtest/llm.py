"""Gemini via the OpenAI-compatible API. Prompts live in PROMPTS.md."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from crashtest.prompts import load_prompt

try:
    load_dotenv(Path.cwd() / ".env")
except OSError:
    pass


class GeminiConfigError(RuntimeError):
    pass


DEFAULT_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_MODEL = "gemini-3.5-flash-lite"
FALLBACK_QUESTIONS = [
    {
        "id": "can_refund",
        "text": "Can the agent issue refunds or move money?",
        "default": True,
    },
    {
        "id": "prompt_only_auth",
        "text": "Is authorization only in the prompt (no backend check)?",
        "default": True,
    },
    {
        "id": "critical_over_limit",
        "text": "Is an action above a money limit without approval a critical failure?",
        "default": True,
    },
]


def gemini_model() -> str:
    return os.environ.get("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def gemini_client() -> OpenAI:
    try:
        load_dotenv(Path.cwd() / ".env")
    except OSError:
        pass
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise GeminiConfigError(
            "GEMINI_API_KEY is missing.\n"
            "  Copy .env.example to .env and set GEMINI_API_KEY."
        )
    base_url = os.environ.get("GEMINI_BASE_URL", DEFAULT_BASE).strip() or DEFAULT_BASE
    return OpenAI(base_url=base_url, api_key=api_key, timeout=60.0)


def _parse_questions(raw: str) -> list[dict]:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    data = json.loads(text)
    questions = data.get("questions", data if isinstance(data, list) else [])
    cleaned: list[dict] = []
    for item in questions:
        if not isinstance(item, dict) or not item.get("text"):
            continue
        cleaned.append(
            {
                "id": str(item.get("id") or f"q{len(cleaned) + 1}"),
                "text": str(item["text"]).strip(),
                "default": bool(item.get("default", True)),
            }
        )
    return cleaned[:3]


def fetch_configure_questions(seed: str) -> list[dict]:
    prompt = load_prompt("configure_questions", seed=seed.strip())
    response = gemini_client().chat.completions.create(
        model=gemini_model(),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1024,
    )
    content = response.choices[0].message.content or ""
    try:
        questions = _parse_questions(content)
    except (json.JSONDecodeError, TypeError, ValueError):
        return FALLBACK_QUESTIONS
    return questions


def _parse_scenarios(raw: str) -> list[dict]:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    data = json.loads(text)
    items = data.get("scenarios", data if isinstance(data, list) else [])
    cleaned: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        messages = item.get("messages") or []
        if not item.get("id") or not item.get("name") or not messages:
            continue
        cleaned.append(
            {
                "id": str(item["id"]).strip(),
                "name": str(item["name"]).strip(),
                "severity": str(item.get("severity") or "critical").strip(),
                "attack_objective": str(item.get("attack_objective") or "").strip(),
                "security_invariant": str(item.get("security_invariant") or "").strip(),
                "threshold": float(item.get("threshold", 0.0)),
                "messages": [str(m) for m in messages if str(m).strip()],
                "remediation": str(item.get("remediation") or "").strip(),
            }
        )
    return cleaned[:5]


def fetch_scenarios(summary: str) -> list[dict]:
    prompt = load_prompt("generate_scenarios", summary=summary.strip())
    response = gemini_client().chat.completions.create(
        model=gemini_model(),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2048,
    )
    content = response.choices[0].message.content or ""
    return _parse_scenarios(content)
