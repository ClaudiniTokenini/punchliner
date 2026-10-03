"""LLM customer-support agent. Gemini OpenAI-compatible API + prompt-only auth."""

from __future__ import annotations

import inspect
import json
from typing import Any

from openai import OpenAI

from crashtest.llm import DEFAULT_MODEL, gemini_client, gemini_model
from crashtest.prompts import load_prompt
from pack import load_tools_schema
from tools import TOOL_HANDLERS

SYSTEM_PROMPT = load_prompt("target_agent")
_TOOLS = load_tools_schema()

MAX_TOOL_TURNS = 2
MAX_TOKENS = 1024


def _client() -> OpenAI:
    return gemini_client()


def _model_name() -> str:
    return gemini_model() or DEFAULT_MODEL


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
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
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


def _completion_kwargs() -> dict[str, Any]:
    return {
        "temperature": 0.2,
        "max_tokens": MAX_TOKENS,
        "extra_body": {"google": {"thinking_config": {"thinking_budget": 0}}},
    }


def _create(client: OpenAI, **kwargs: Any) -> Any:
    payload = {**kwargs, **_completion_kwargs()}
    try:
        return client.chat.completions.create(**payload)
    except Exception:
        payload.pop("extra_body", None)
        return client.chat.completions.create(**payload)


def handle_message(message: str, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Process one user message through Gemini and return reply + tool calls."""
    history = history or []
    try:
        client = _client()
    except RuntimeError as exc:
        return {
            "role": "assistant",
            "content": f"Target LLM is unavailable: {exc}",
            "system_prompt_note": "prompt-only authorization",
            "tool_calls": [],
        }

    model = _model_name()
    messages = _history_messages(history, message.strip())
    executed: list[dict[str, Any]] = []
    final_text = ""

    try:
        for _ in range(MAX_TOOL_TURNS):
            response = _create(
                client,
                model=model,
                messages=messages,
                tools=_TOOLS,
            )
            choice = response.choices[0].message
            final_text = choice.content or ""
            tool_calls = choice.tool_calls or []
            if not tool_calls:
                break

            messages.append(choice.model_dump(exclude_none=True))
            for tool_call in tool_calls:
                parsed = _parse_args(tool_call.function.arguments)
                recorded = _call_tool(tool_call.function.name, parsed)
                executed.append(recorded)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(recorded["result"], default=str),
                    }
                )
        else:
            response = _create(
                client,
                model=model,
                messages=messages,
            )
            final_text = response.choices[0].message.content or final_text
    except Exception as exc:  # noqa: BLE001 - surface LLM/runtime errors to the caller
        return {
            "role": "assistant",
            "content": (
                f"Target LLM is unavailable: {exc}. "
                "Check GEMINI_API_KEY and GEMINI_MODEL, then restart npm run agent."
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
