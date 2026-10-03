"""LLM customer-support agent with prompt-only authorization via LM Studio."""

from __future__ import annotations

import inspect
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from pack import load_profile, load_system_prompt, load_tools_schema, pack_dir
from tools import TOOL_HANDLERS

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SYSTEM_PROMPT = (pack_dir() / "SYSTEM.md").read_text(encoding="utf-8").strip()
_MODEL_PROMPT = load_system_prompt()
_PROFILE = load_profile()
_TOOLS = load_tools_schema()

MAX_TOOL_TURNS = 2
OPENAI_TIMEOUT = 60.0
MAX_TOKENS = 256
_RESOLVED_MODEL: str | None = None


def _client() -> OpenAI:
    base_url = os.environ.get("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
    api_key = os.environ.get("LM_STUDIO_API_KEY", "lm-studio")
    return OpenAI(base_url=base_url, api_key=api_key, timeout=OPENAI_TIMEOUT)


def _model_name(client: OpenAI) -> str:
    global _RESOLVED_MODEL
    if _RESOLVED_MODEL:
        return _RESOLVED_MODEL
    env = os.environ.get("LM_STUDIO_MODEL", "").strip()
    if env:
        _RESOLVED_MODEL = env
        return env
    try:
        ids = [item.id for item in client.models.list().data]
        chat_ids = [item_id for item_id in ids if "embed" not in item_id.lower()]
        for item_id in chat_ids:
            if "9b" in item_id.lower():
                _RESOLVED_MODEL = item_id
                return item_id
        if chat_ids:
            _RESOLVED_MODEL = chat_ids[0]
            return chat_ids[0]
    except Exception:
        pass
    _RESOLVED_MODEL = str(_PROFILE.get("model", "qwen/qwen3.5-9b"))
    return _RESOLVED_MODEL


def _parse_args(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return {"name": name, "arguments": arguments, "result": {"error": "unknown_tool"}}
    params = inspect.signature(handler).parameters
    filtered = {key: value for key, value in arguments.items() if key in params}
    try:
        result = handler(**filtered)
    except TypeError as exc:
        result = {"error": "invalid_arguments", "detail": str(exc)}
    return {"name": name, "arguments": arguments, "result": result}


def _history_messages(history: list[dict[str, Any]], user_text: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": _MODEL_PROMPT}]
    for item in history:
        role = item.get("role")
        content = item.get("content")
        if not isinstance(content, str) or not content:
            continue
        if role in {"user", "attacker"}:
            messages.append({"role": "user", "content": content})
        elif role in {"assistant", "agent"}:
            messages.append({"role": "assistant", "content": content})
    if not messages or messages[-1].get("content") != user_text or messages[-1].get("role") != "user":
        messages.append({"role": "user", "content": user_text})
    return messages


def handle_message(message: str, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Process one user message through LM Studio and return reply + tool calls."""
    history = history or []
    client = _client()
    model = _model_name(client)
    messages = _history_messages(history, message.strip())
    executed: list[dict[str, Any]] = []
    final_text = ""

    try:
        for _ in range(MAX_TOOL_TURNS):
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=_TOOLS,
                temperature=0.2,
                max_tokens=MAX_TOKENS,
                extra_body={
                    "enable_thinking": False,
                    "chat_template_kwargs": {"enable_thinking": False},
                },
            )
            choice = response.choices[0].message
            final_text = choice.content or ""
            tool_calls = choice.tool_calls or []
            if not tool_calls:
                break

            assistant_tool_calls = []
            for tool_call in tool_calls:
                assistant_tool_calls.append(
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments or "{}",
                        },
                    }
                )
                parsed = _parse_args(tool_call.function.arguments)
                executed.append(_call_tool(tool_call.function.name, parsed))

            messages.append(
                {
                    "role": "assistant",
                    "content": final_text or None,
                    "tool_calls": assistant_tool_calls,
                }
            )
            for tool_call, recorded in zip(tool_calls, executed[-len(tool_calls) :], strict=True):
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(recorded["result"], default=str),
                    }
                )
        else:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2,
                max_tokens=MAX_TOKENS,
                extra_body={
                    "enable_thinking": False,
                    "chat_template_kwargs": {"enable_thinking": False},
                },
            )
            final_text = response.choices[0].message.content or final_text
    except Exception as exc:  # noqa: BLE001 - surface LLM/runtime errors to the caller
        return {
            "role": "assistant",
            "content": (
                f"Target LLM is unavailable: {exc}. "
                "Load qwen/qwen3.5-9b in LM Studio (thinking off, model actually in RAM) "
                "and restart npm run agent."
            ),
            "system_prompt_note": "prompt-only authorization",
            "tool_calls": executed,
        }

    return {
        "role": "assistant",
        "content": final_text or "Done.",
        "system_prompt_note": "prompt-only authorization",
        "tool_calls": executed,
    }
