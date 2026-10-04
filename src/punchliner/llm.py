"""Gemini via the OpenAI-compatible API. Prompts live in PROMPTS.md."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from punchliner.prompts import load_prompt

try:
    load_dotenv(Path.cwd() / ".env")
except OSError:
    pass


class GeminiConfigError(RuntimeError):
    pass


DEFAULT_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_MODEL = "gemini-3.5-flash-lite"
MAX_CONFIGURE_QUESTIONS = 3
MAX_BOOL_QUESTIONS = 2
FALLBACK_QUESTIONS = [
    {
        "id": "operating_rules",
        "kind": "text",
        "text": "What business rules should the agent follow that are not already in the pack?",
        "default": "",
    },
    {
        "id": "business_context",
        "kind": "text",
        "text": "What else should the agent know about this business and its customers?",
        "default": "",
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


def _question_kind(item: dict) -> str:
    raw = item.get("kind")
    if raw is None and isinstance(item.get("default"), bool):
        return "bool"
    name = str(raw or "text").strip().lower()
    if name in {"bool", "boolean", "yn", "yesno", "confirm"}:
        return "bool"
    return "text"


def _normalize_question(item: dict, index: int) -> dict | None:
    text = str(item.get("text") or "").strip()
    if not text:
        return None
    kind = _question_kind(item)
    question = {
        "id": str(item.get("id") or f"q{index}"),
        "kind": kind,
        "text": text,
    }
    if kind == "bool":
        question["default"] = bool(item.get("default", True))
    else:
        # Suggested answers get repeated back as policy. Leave the line blank.
        question["default"] = ""
    return question


def _parse_questions(raw: str) -> list[dict]:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    data = json.loads(text)
    questions = data.get("questions", data if isinstance(data, list) else [])
    parsed: list[dict] = []
    for item in questions:
        if not isinstance(item, dict):
            continue
        question = _normalize_question(item, len(parsed) + 1)
        if question is not None:
            parsed.append(question)
    texts = [item for item in parsed if item["kind"] == "text"]
    bools = [item for item in parsed if item["kind"] == "bool"]
    # Prefer open answers. Yes/no only fills slots that text did not take.
    text_keep = texts[:MAX_CONFIGURE_QUESTIONS]
    bool_keep = bools[: min(MAX_BOOL_QUESTIONS, MAX_CONFIGURE_QUESTIONS - len(text_keep))]
    keep = {id(item) for item in text_keep + bool_keep}
    return [item for item in parsed if id(item) in keep]


def _parse_json_object(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object")
    return data


def _parse_validate(raw: str) -> dict:
    data = _parse_json_object(raw)
    return {
        "ok": bool(data.get("ok", True)),
        "reason": str(data.get("reason") or "").strip(),
    }


def fetch_configure_questions(seed: str, agent_context: str = "") -> list[dict]:
    prompt = load_prompt(
        "configure_questions",
        seed=seed.strip(),
        agent_context=agent_context.strip(),
    )
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


def validate_configure_seed(seed: str, agent_context: str) -> dict:
    prompt = load_prompt(
        "configure_validate",
        seed=seed.strip(),
        agent_context=agent_context.strip(),
    )
    response = gemini_client().chat.completions.create(
        model=gemini_model(),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=256,
    )
    content = response.choices[0].message.content or ""
    try:
        return _parse_validate(content)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {"ok": True, "reason": ""}


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
    return cleaned[:8]


def fetch_scenarios(summary: str, agent_context: str = "") -> list[dict]:
    prompt = load_prompt(
        "generate_scenarios",
        summary=summary.strip(),
        agent_context=agent_context.strip(),
    )
    response = gemini_client().chat.completions.create(
        model=gemini_model(),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.35,
        max_tokens=4096,
    )
    content = response.choices[0].message.content or ""
    return _parse_scenarios(content)
