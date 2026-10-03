# Update: Gemini zamiast lokalnego LLM

**Data:** 2026-10-03

Lokalny target (LM Studio / Ollama / Qwen) został zastąpiony **Google Gemini** przez OpenAI-compatible API.

| Było (wizja) | Jest |
|--------------|------|
| Ollama + Qwen3 / LM Studio | Gemini `gemini-3.5-flash-lite` |
| LiteLLM → lokalny inference | `openai` SDK → `GEMINI_BASE_URL` |
| lokalny model na maszynie jury | klucz API w `.env` / CI secrets |

Dokumenty zaktualizowane: `README.md`, `PLAN.md`, `PLAN-B.md`, `SPRINT-1.md`, `SPRINT-2.md`, `.env.example`.

Kod źródłowy już był na Gemini (`src/crashtest/llm.py`, `demo-agent/agent.py`).
