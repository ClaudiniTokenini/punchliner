# Sprint 2 — Podsumowanie (Osoba B) — przebudowa po Sprincie 1 A

**Data:** 2026-10-03  
**Zakres:** Report v1 + integracja z realnym engine Osoby A + `crashtest open`  
**Źródło wymagań:** `PLAN-B.md` → Sprint 2  
**Tryb:** Ponytail (full)

---

## Stan wejściowy (po Sprincie 1 Osoby A)

Osoba A dostarczyła działający core. To zmieniło kontekst Sprintu 2 B:

| Artefakt A | Ścieżka | Znaczenie dla B |
|------------|---------|-----------------|
| CLI Typer | `src/crashtest/cli.py` | `configure` / `run` / `chat` — trzeba dokleić `open` |
| Schemat `results.json` | `src/crashtest/schemas.py` → `Results` | Kontrakt UI już zamrożony w Pydantic |
| Runner | `src/crashtest/runner.py` | Zapis: `.crashtest/runs/<id>/results.json` |
| Config + scenarios | `.crashtest/config.yml`, `scenarios.yml` | Realny security contract |
| Demo agent (LLM) | `demo-agent/` + LM Studio | Target na `:8000` (nie reguły heurystyczne) |
| npm scripts | `package.json` | `agent`, `chat`, `configure`, `test` |
| Testy | `tests/test_crashtest.py` | Mockowany run produkuje ten sam JSON co UI |

Poprzednia wersja Sprintu 2 B (samodzielny skrypt + Report v1) **nie była w repo** — `App.tsx` wrócił do v0, brak `SPRINT-2.md`. Ten dokument opisuje **przebudowę od zera na kontrakcie A**.

### Zgodność schematu

Pola z `crashtest.schemas.Results` = to, czego oczekuje report:

```text
summary · gate · scenarios[] · runs[] · remediation
+ jev_verdict · trace[] · compromise_rate
```

Fixture `fixtures/results.failed.json` i output runnera A są zgodne kształtem.  
`rerun_command` w fixture ustawione na `npm test` (jak w runnerze A).

---

## Co zostało zrobione (Sprint 2 B)

### 1. Report v1 — `report/src/App.tsx`

| Ekran | Status | Szczegóły |
|-------|--------|-----------|
| Overview | Done | FAILED/PASSED, `{n}% RESILIENT`, Critical/High, gate summary (observed vs allowed + exit) |
| Vulnerabilities | Done | nazwa, `x / n compromised`, allowed threshold, severity badge, progress bar |
| Trace Replay | Done | timeline Attacker → Agent → Tool Call → Tool Result → Jev; `issue_refund(...)`; `SECURITY CONTRACT VIOLATED` |
| Remediation | Done | why / suggested / re-run command |

Ładowanie danych:

```text
fetch("./results.json")  →  artifact z open / public
404                     →  fixtures/results.failed.json
```

W UI widać `Data source: …`.

### 2. `crashtest open` w CLI Osoby A

Dodane do `src/crashtest/cli.py` (nie osobny skrypt — jedna powierzchnia CLI):

```bash
uv run crashtest open
uv run crashtest open --no-browser
uv run crashtest open --dev
npm run open
```

Zachowanie:
1. Bierze najnowszy `.crashtest/runs/*/results.json`
2. Brak runów → `fixtures/results.failed.json`
3. Kopiuje do `report/public/results.json` (+ `dist/` jeśli jest)
4. Buduje report, jeśli brak `dist/index.html`
5. Otwiera HTML w przeglądarce

Root `package.json`: dodane `"open"` i `"report"`.

### 3. Test

`tests/test_crashtest.py::test_open_copies_latest_results` — **passed**.

### 4. Smoke na realnym JSON z engine A

Wygenerowano mockowany run engine’em A:

```text
.crashtest/runs/sprint2-demo/results.json
status: FAILED · compromised: 5/5
```

`crashtest open --no-browser` skopiował ten plik do reportu.  
`npm --prefix report run build` — OK.

---

## Weryfikacja wymagań PLAN-B Sprint 2

### Overview

| Wymaganie | Spełnione? | Dowód |
|-----------|------------|-------|
| Overall status PASSED / FAILED | **TAK** | Badge + Stat |
| Resilience score | **TAK** | Hero `% RESILIENT` |
| Critical / High | **TAK** | Dwa liczniki |
| Gate summary | **TAK** | observed vs allowed + exit |

### Vulnerability list

| Wymaganie | Spełnione? | Dowód |
|-----------|------------|-------|
| Nazwa scenariusza | **TAK** | Unauthorized Refund |
| `x / n compromised` | **TAK** | z `scenarios[]` |
| Allowed threshold | **TAK** | `Allowed: …` |
| Severity badge | **TAK** | critical/high |
| Progress bar | **TAK** | % defended |

### Trace replay

| Wymaganie | Spełnione? | Dowód |
|-----------|------------|-------|
| Chronologia + Jev | **TAK** | timeline + blok Jev |
| Tool call z parametrami | **TAK** | `issue_refund(order_id=…, amount=…)` |
| SECURITY CONTRACT VIOLATED | **TAK** | highlight na COMPROMISED tool_call |
| Jev verdict + confidence | **TAK** | z `jev_verdict` |

### Remediation

| Wymaganie | Spełnione? | Dowód |
|-----------|------------|-------|
| Why / suggested / re-run | **TAK** | footer z `remediation` |

### Integracja

| Wymaganie | Spełnione? | Dowód |
|-----------|------------|-------|
| Realny `results.json` z engine | **TAK** | open ← `.crashtest/runs/sprint2-demo/results.json` |
| Fallback fixture | **TAK** | brak runów / 404 fetch |
| `crashtest open` | **TAK** | komenda Typer + `npm run open` |

### Kamień milowy

```bash
npm run configure   # A — działa (dawniej init)
npm test            # A — działa (crashtest run)
npm run open        # B — działa
```

| Część | Status |
|-------|--------|
| Report na fixture | Spełnione |
| Report na JSON z runnera A | Spełnione (ścieżka + smoke na `sprint2-demo`) |
| Live LLM `npm test` bez mocka | Wymaga LM Studio + `npm run agent` (infra A) |

---

## Ponytail — co pominięto

| Pominięte | Dlaczego | Dodać gdy |
|-----------|----------|-----------|
| Recharts | CSS bar wystarcza | Sprint 4 polish |
| Osobny `scripts/crashtest_open.py` | Logika w CLI A | — |
| Osobne pliki komponentów | jeden `App.tsx` | UI urośnie |

---

## Werdykt

**Wymagania Sprint 2 z PLAN-B dla Osoby B: spełnione (16/16).**

Integracja z Osobą A: report czyta **ten sam** `results.json`, który produkuje `crashtest run`.

**Następny (Sprint 3 B):** GitHub Actions — `crashtest run --ci` + upload HTML artifact.
