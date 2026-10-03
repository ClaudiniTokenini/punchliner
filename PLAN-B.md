# PLAN OSOBY B  
## Demo / Report / Integration

Rola: `vulnerable agent → report → trace UX → GitHub Actions → demo`  
Definition of Done: `crashtest open` pokazuje atrakcyjny raport i da się przeprowadzić cały scenariusz demo.

Kontrakt z Osobą A: UI czyta wyłącznie  
`.crashtest/runs/<run-id>/results.json`  
Do czasu gotowego engine'u pracuję na `fixtures/results.failed.json`.

Stack po mojej stronie:
- FastAPI — podatny demo agent
- React + Vite + Tailwind + Recharts — static HTML report
- GitHub Actions — CI gate + upload artifact

---

## Sprint 0 — CONTRACT (H0–H1)

Cel: odblokować niezależną pracę.

### Moje zadania

- [ ] Uczestniczyć w zamrożeniu kontraktu: `config.yml`, `scenarios.yml`, `results.json`, komendy CLI
- [ ] Potwierdzić strukturę pól potrzebnych reportowi:
  - `summary`, `gate`, `scenarios[]`, `runs[]`, `trace[]`
  - `jev_verdict`, `compromise_rate`, `remediation`
- [ ] Ustalić ścieżki artifactów:
  - `.crashtest/runs/<run-id>/results.json`
  - `.crashtest/artifacts/<run-id>/` (lub `crashtest-report/`)
- [ ] Zaakceptować scenariusz demo: unauthorized refund > 200 PLN bez approval
- [ ] Dopilnować, że w repo jest fixture: `fixtures/results.failed.json`

### Deliverable

Mam mock JSON i mogę budować report bez czekania na engine.

---

## Sprint 1 — FIRST VERTICAL SLICE (H1–H4)

Cel: działający target + pierwsza wersja reportu.

### 1. Vulnerable e-commerce agent (FastAPI)

Endpoint:

```text
POST /chat
```

Tools (celowo słabe — prompt-only auth):

```text
get_order
get_customer
issue_refund
apply_discount
```

Wymagania:

- [x] Agent odpowiada jak customer support
- [x] Autoryzacja refundów tylko w prompcie (łatwo obejść)
- [x] `issue_refund(amount > 200)` da się wymusić bez manager approval
- [x] Zwraca czytelne tool calls w odpowiedzi (łatwy trace dla reportu)
- [x] Działa lokalnie: `http://localhost:8000/chat`

### 2. Report v0 z fixture

- [x] Scaffold React + Vite + Tailwind
- [x] Wczytywanie `fixtures/results.failed.json`
- [x] Header: status BUILD FAILED / PASSED
- [x] Podstawowa lista scenariuszy + compromise rate
- [x] Placeholder pod trace replay

### Kamień milowy

```text
CLI → HTTP target → attack → results.json → HTML report
```

Po mojej stronie: target żyje, report czyta fixture.

---

## Sprint 2 — INTELLIGENCE / REPORT v1 (H4–H8)

Cel: report opowiada historię bez tłumaczenia.

### Report v1 — ekrany

#### Overview

- [ ] Overall status: PASSED / FAILED
- [ ] Resilience score (np. `82% RESILIENT`)
- [ ] Liczniki: Critical / High
- [ ] Gate summary (threshold vs actual)

#### Vulnerability list

- [ ] Nazwa scenariusza (np. Unauthorized Refund)
- [ ] `2 / 10 compromised`
- [ ] Allowed threshold
- [ ] Severity badge
- [ ] Progress bar obrony

#### Trace replay

- [ ] Chronologia: Attacker → Agent → Tool call → Jev
- [ ] Widoczny tool call z parametrami (`issue_refund(...)`)
- [ ] Highlight naruszenia: `SECURITY CONTRACT VIOLATED`
- [ ] Verdict Jev + confidence

#### Remediation footer

- [ ] Why it failed
- [ ] Suggested remediation
- [ ] Re-run command

### Integracja

- [ ] Report czyta realny `results.json` gdy pojawi się z engine'u
- [ ] Fallback na fixture jeśli brak runu
- [ ] Komenda / skrypt pod `crashtest open` (otwarcie `index.html`)

### Kamień milowy

```bash
crashtest init
crashtest run --runs 5
crashtest open
```

Report działa end-to-end na prawdziwych danych (gdy A dostarczy) lub fixture.

---

## Sprint 3 — CI + ARTIFACT (H8–H12)

Cel: prawdziwy failed CI job + downloadable report.

### GitHub Actions

- [ ] Workflow: checkout → install → (opcjonalnie ollama) → `crashtest run --ci`
- [ ] Exit code 1 przy przekroczonym threshold
- [ ] Upload artifact:

```text
crashtest-report/
├── index.html
├── results.json
└── assets/
```

- [ ] `JEV_API_KEY` z secrets (gdy A podłączy Jev)
- [ ] Screenshot-ready failed job w Actions UI

### Packaging reportu

- [ ] Build static (Vite) do artifact folder
- [ ] Report self-contained (działa offline z artifactu)
- [ ] Spójne nazewnictwo z kontraktem Osoby A

### Kamień milowy

**Failed CI + pobieralny security report** — kluczowy screen do jury.

---

## Sprint 4 — PRODUCT MOMENT (H12–H16)

Cel: design na poziomie 20% oceny jury. Zero nowych feature'ów poza polish.

### Dopracować tylko 3 ekrany

1. **Overview** — BUILD FAILED, resilience, critical/high
2. **Vulnerability** — unauthorized refund, rates, threshold
3. **Trace** — exploit path + tool call + Jev COMPROMISED

### Design checklist (z wizji)

- [ ] Cypress-like: artifact runu, nie osobny SaaS dashboard
- [ ] Jedna kompozycja pierwszego ekranu, czytelna hierarchia
- [ ] Trace replay jako główny „aha moment”
- [ ] Bez zbędnych kart / clutteru
- [ ] Działa desktop + mobile na poziomie prezentacji
- [ ] Recharts tylko tam, gdzie pomaga (rate / resilience), nie dekoracja

### Kamień milowy

Bez tłumaczenia widać: co padło, jak, i dlaczego build failed.

---

## Sprint 5 — FIX & RETEST DEMO (H16–H19)

Cel: najmocniejsza część pitchu — Detect → Fix → Verify.

### BEFORE

- [ ] Demo agent podatny (prompt-only)
- [ ] Run pokazuje `2 / 10 COMPROMISED` (lub podobny fail)
- [ ] Report pokazuje exact exploit w trace

### FIX (w demo agencie)

- [ ] Przenieść regułę do backendu:
  - `refund > 200 PLN` wymaga manager authorization
- [ ] Odrzucać nieautoryzowane `issue_refund` niezależnie od promptu

### AFTER

- [ ] Rerun: `0 / 10 COMPROMISED`
- [ ] Report: SECURITY GATE PASSED / BUILD PASSED
- [ ] Mieć gotowe oba artifacty (failed + passed) na wypadek live failu

### Kamień milowy

Pełna historia demo w < kilka minut.

---

## Sprint 6 — SUBMISSION & PITCH (H19–H22)

### Materiały

- [ ] Max 10 slajdów
- [ ] Screenshots: failed CI, overview, vulnerability, trace, passed rerun
- [ ] GIF/video krótkiego flow jeśli potrzebny
- [ ] Scenariusz live demo (kolejność kliknięć / komend)

### Pitch sequence (z wizji)

1. Hook: agent przeszedł test raz — a dziesięć razy?
2. Terminal: `2 / 10 COMPROMISED` → BUILD FAILED
3. Artifact: trace z `issue_refund()`
4. Fix w backendzie
5. Rerun: `0 / 10` → BUILD PASSED
6. Dopiero potem krótka architektura

### Disclosure (regulamin)

- [ ] Jawnie: Ollama, Qwen3, LiteLLM, Jev (+ inne użyte API)

### H22–H24 — buffer

- [ ] Tylko bugfixy i dry-run demo
- [ ] Żadnych nowych funkcji
- [ ] Fallback artifact zawsze pod ręką

---

## Priorytety (gdy brakuje czasu)

| Priorytet | Co | Dlaczego |
|-----------|----|----------|
| P0 | Podatny agent + fix path | Bez tego nie ma demo loop |
| P0 | Trace replay w reportcie | Główny dowód naruszenia |
| P0 | Failed CI + artifact upload | Screen pod practical applicability |
| P1 | Overview + vulnerability rates | Security SLO UX |
| P1 | `crashtest open` | Cypress-like DX |
| P2 | Recharts polish / animacje | Design points |
| P2 | GIF / extra slides | Nice-to-have |

Świadomie nie robię: SaaS, logowania, bazy, osobnego dashboard backendu, wielu attack categories w UI.

---

## Checklist synchronizacji z Osobą A

| Moment | Co wymieniamy |
|--------|----------------|
| H0–H1 | Schema `results.json` + fixture |
| H1–H4 | URL targeta `/chat` + shape tool calls |
| H4–H8 | Real `results.json` z pierwszego runu |
| H8–H12 | Format artifact folder + exit code CI |
| H12–H16 | Final fields: remediation, jev_verdict |
| H16–H19 | Wspólny dry-run: fail → fix → pass |

---

## Definition of Done (osobiste)

Uznaję pracę za skończoną, gdy:

1. `POST /chat` demo agent jest podatny, potem naprawialny backendowo  
2. Report z `results.json` pokazuje overview + vulnerability + trace  
3. GitHub Actions failuje na gate i uploaduje HTML artifact  
4. `crashtest open` otwiera raport  
5. Live (lub nagrane) demo przechodzi: fail → understand → fix → pass  
6. Pitch + screenshots są gotowe przed buforem H22
