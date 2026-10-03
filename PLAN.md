# Agent Crash Test — zostało do hackathonu

Okno oddania: 23:00, 4 października. Feature set zamrożony. Żadnych nowych kategorii ataków.

## Zrobione

Kontrakt (`.crashtest/config.yml`, `scenarios.yml`, `results.json`), fixture, CLI (`init` / `run` / `open` / `chat`).

Demo agent: FastAPI, Gemini, pack `shop-assistant`, narzędzia `get_order`, `get_customer`, `issue_refund`, `apply_discount`. Refund powyżej 200 PLN chroni tylko prompt.

Runner: wszystkie scenariusze × N runów, bramka critical/high, exit code `0`/`1`. Scenariusze z Gemini albo z szablonu (`init --defaults`).

Sędzia: Jev (`prompt_compliance`, `security_invariant`, `attack_success`). Raport: status, resilience, scenariusze, trace, remediation (`report/`).

Pivot LLM: lokalny Ollama / LM Studio / Qwen odpadł. Target, `configure` i generowanie scenariuszy idą przez Gemini (`GEMINI_API_KEY`, model `gemini-3.5-flash-lite`, OpenAI-compatible `GEMINI_BASE_URL`). Kontrakt `results.json` bez zmian.

Świadomie poza zakresem: adaptive attacker, SaaS, baza, LangChain, lokalny model, osobny backend dashboardu.

## P0 — fail, fix, pass

To jest demo.

1. Run na podatnym agencie: bramka FAILED, w trace widać `issue_refund` powyżej 200 PLN.
2. W `demo-agent/tools.py` odrzucać taki refund bez zweryfikowanego approval (nie flagi z promptu).
3. Ten sam kontrakt, rerun: `0` skompromitowanych, bramka PASSED.
4. Zostawić oba artefakty (`results.json` + HTML), gdyby live run nie wyszedł.

## P0 — CI

Brak workflow. `crashtest run` już zwraca exit code bramki, osobna flaga `--ci` nie jest potrzebna.

- checkout, `uv sync`, Node, build raportu
- sekrety: `GEMINI_API_KEY`, `JEV_API_KEY`
- upload: `report/dist/` (`index.html`, `results.json`, assety)
- screen failed joba w Actions

## P1 — pitch

Max 10 slajdów. Kolejność: hook (raz przeszedł, a dziesięć razy?) → terminal FAILED → trace → fix w backendzie → PASSED → dopiero stack.

Ujawnić: Gemini `gemini-3.5-flash-lite`, Gemini OpenAI-compatible API, Jev / TypeSafe.

Bufor na końcu: bugfixy i suchy przebieg. Bez nowych funkcji.
