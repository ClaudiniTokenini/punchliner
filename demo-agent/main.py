from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from crashtest.llm import GeminiConfigError, gemini_client

from agent import PACK, SYSTEM_PROMPT, handle_message
from tools import REFUNDS


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        gemini_client()
    except GeminiConfigError as exc:
        sys.stderr.write(f"\n{exc}\n\n")
        sys.stderr.flush()
        raise SystemExit(1) from exc
    yield


app = FastAPI(
    title="Vulnerable E-commerce Agent",
    description="Demo target for Agent Crash Test - prompt-only authorization.",
    version="0.1.0",
    lifespan=lifespan,
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str | None = None
    messages: list[ChatMessage] = Field(default_factory=list)


class ToolCallOut(BaseModel):
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]


class ChatResponse(BaseModel):
    role: str
    content: str
    tool_calls: list[ToolCallOut] = Field(default_factory=list)
    system_prompt_note: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/policy")
def policy() -> dict[str, Any]:
    return {
        "authorization": PACK.authorization,
        "refund_limit_pln": PACK.refund_limit_pln,
        "system_prompt": SYSTEM_PROMPT,
        "pack": PACK.relpath,
        "tools": PACK.tool_names,
        "warning": "Do not use in production. Intentionally vulnerable.",
    }


@app.get("/debug/refunds")
def debug_refunds() -> dict[str, Any]:
    return {"refunds": REFUNDS}


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    if body.message:
        user_text = body.message
        history = [m.model_dump() for m in body.messages]
    elif body.messages:
        history = [m.model_dump() for m in body.messages]
        user_text = next(
            (m.content for m in reversed(body.messages) if m.role in {"user", "attacker"}),
            "",
        )
    else:
        return ChatResponse(
            role="assistant",
            content="Send a message to continue.",
            meta={"endpoint": "http://localhost:8000/chat"},
        )

    result = handle_message(user_text, history)
    return ChatResponse(
        role=result["role"],
        content=result["content"],
        tool_calls=[ToolCallOut(**tc) for tc in result.get("tool_calls", [])],
        system_prompt_note=result.get("system_prompt_note"),
        meta={
            "endpoint": "http://localhost:8000/chat",
            "tools": PACK.tool_names,
            "pack": PACK.relpath,
        },
    )
