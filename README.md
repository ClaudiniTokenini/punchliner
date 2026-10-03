# Agent Crash Test

Cypress for AI agent security. Ten sam scenariusz, wiele runów, próg kompromitacji.

Wymagania: Python 3.12, [uv](https://docs.astral.sh/uv/), klucz Gemini w `.env`.

```bash
uv sync
cp .env.example .env   # wstaw GEMINI_API_KEY
npm run agent
```

Model: `gemini-3.5-flash-lite` (env `GEMINI_MODEL`). Prompty do API są w `PROMPTS.md`.

W drugim terminalu reczny czat z odbiorca:

```bash
npm run chat
```

Kontekst projektu (opis + pytania y/n, bez generowania scenariuszy):

```bash
npm run configure
npm test
```

`npm test` atakuje `POST /chat` i zapisuje `.crashtest/runs/<id>/results.json`. Exit `1` gdy rate > próg.

Demo sklep: zamowienia sa slownikiem w pamieci (`demo-agent/tools.py`), nie SQLite ani CSV. Zamowienie `4812` = 499 PLN (powyzej limitu 200 PLN).

```text
  2 / 5 compromised    40%
  GATE FAILED
```

Raport UI: `cd report && npm install && npm run dev`.
