# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tech Stack

**TalentCompass** is a Python web app for AI workforce intelligence and HR advisory, built with:

- **Framework**: Streamlit (v1.35+) — single-page UI with sidebar navigation
- **LLM Integration**: Anthropic Claude API. Model is selectable at runtime (sidebar): `claude-haiku-4-5` (default, fast) or `claude-opus-4-5` (quality).
- **Validation**: pydantic v2 — every Claude JSON response is validated against a schema (`services/schemas.py`) at the API boundary.
- **Data & Visualization**: Plotly (v5.22+), Pandas (v2.2+)
- **PDF Export**: fpdf2 (v2.8+) with custom Deloitte-branded templates
- **Styling**: Custom CSS (Deloitte brand); Cabinet Grotesk via Fontshare. Light theme pinned in `.streamlit/config.toml`.
- **Tests**: pytest (`requirements-dev.txt`); includes byte-deterministic golden-file PDF tests.

## Project Purpose

TalentCompass generates AI-driven workforce assessments and HR advisory:
1. **Role Analysis**: automation potential, task breakdown, AI agent recommendations, reskilling, roadmap, risks — plus **deterministic workforce impact** (FTE freed, payroll savings, severance exposure) and an opt-in **HR management & advisory** layer.
2. **Client Research**: market intelligence (AI potential, trends, competitor moves, Deloitte angle) with **entity disambiguation** to resolve ambiguous company names before research.
3. **Organization Overview**: comparative charts plus an org-wide workforce/financial rollup.
4. **Agent Library**: curated AI-agent templates (built-in + custom) appliable to roles.
5. **Reports & Export**: Deloitte-branded PDFs; JSON session export/import.

LLM outputs are dynamic (no hardcoded scores). Financial figures are computed arithmetic, not LLM estimates.

## Architecture

### Directory Structure

```
talentcompass/
├── app.py                      # Entry point, sidebar (key, model, session I/O), routing
├── .streamlit/config.toml      # Pinned light theme + Deloitte palette
├── services/
│   ├── claude_client.py        # API wrapper: analyze_role, research_company,
│   │                           #   disambiguate_company, analyze_hr_advisory;
│   │                           #   ClaudeClientError, _call/_send/_parse, _validate, model config
│   ├── prompts.py              # System prompts + builders; MARKETS dict (Luxembourg/Belgium)
│   ├── schemas.py              # pydantic v2 models for every Claude response
│   ├── company_context.py      # Company-size bucket inference
│   ├── session_io.py           # Export/import session as JSON (strips api_key)
│   ├── agent_library.py        # AI-agent template library (builtin + custom)
│   ├── template_store.py       # Pluggable persistence: SessionStore | FileStore (DB-ready seam)
│   ├── registry.py             # GLEIF LEI registry lookup for entity disambiguation
│   ├── workforce.py            # Deterministic FTE / payroll / severance maths + rollup
│   └── pdf/                     # PDF package (split from the old pdf_export.py monolith)
│       ├── base.py             #   _DeloittePDF, colours, _safe, _ts, render helpers
│       ├── sections.py         #   _write_role_section, _write_company_section
│       └── builders.py         #   the 5 build_* functions
│   └── pdf_export.py           # Thin re-export shim (back-compat for existing imports)
├── pages/
│   ├── role_analysis.py        # Role Analysis: presets, workforce inputs, agent library, HR advisory
│   ├── client_research.py      # Client Research: market select, Find entity / Research
│   ├── org_overview.py         # Comparative charts + workforce rollup
│   ├── agent_library_page.py   # Browse/create/edit/delete agent templates
│   └── reports_export.py       # Session history, tabbed review, PDF downloads
├── styles/main.css             # Deloitte brand styling
├── assets/fonts/               # DejaVuSans.ttf, DejaVuSans-Bold.ttf for PDF
├── tests/                      # pytest suite + golden PDF checksums
├── requirements.txt
└── requirements-dev.txt        # pytest
```

### Key Design Patterns

**Session State**: `st.session_state` is the single source of truth: `api_key` (never persisted), `model`, `market`, `org_roles` (each tagged `_title`/`_client`/`_dept`, may carry `workforce` + `hr_advisory`), `org_companies`, `last_company_result`, `custom_agent_templates`.

**API Abstraction & Hardening** (`services/claude_client.py`): all calls go through `_call()` → `_send()` (API) + `_parse()` (strip fences + json.loads). On `JSONDecodeError` it retries once; failures raise `ClaudeClientError(message, kind)` with `kind` ∈ `auth|rate_limit|bad_json|api`. Pages catch it and show a friendly `st.error` (no tracebacks). The model is resolved per call via `_resolve_model()` (reads `session_state['model']`, falls back to haiku).

**Schema Validation** (`services/schemas.py`): `_validate(data, Model)` runs `Model.model_validate(...).model_dump()` after parsing; a `ValidationError` raises `ClaudeClientError(kind="bad_json")` directly (NOT routed through the JSON retry — it is valid JSON of the wrong shape). All models use `extra="allow"` so unknown keys survive and `_title`/`_dept`/`_client` tags round-trip.

**Deterministic vs LLM split**: `services/workforce.py` computes FTE/payroll/severance with plain arithmetic on consultant inputs — defensible and reproducible. The LLM only supplies qualitative content (automation_score, advisory). Keep this separation: never present a computed figure as an LLM guess or vice versa.

**Pluggable persistence** (`services/template_store.py`): `get_store(state)` returns `SessionStore` (default) or `FileStore` (env `TC_TEMPLATE_STORE=file`). `agent_library` reads/writes only through this interface — a future `DBStore` slots in without UI changes.

**Entity disambiguation** (`disambiguate_company`): tries the GLEIF registry (`services/registry.py`) first (authoritative, `source="registry"`); on miss/offline/disabled falls back to an LLM candidate listing (`source="llm"`). Fail-safe — any registry error returns to the LLM path.

**Module Reloading** (`app.py::_reload_modules`): reloads submodules each rerun so code edits apply without a restart. **Gated behind `TC_DEV=1`** — a no-op in normal runs. Set `TC_DEV=1` while iterating locally; Python changes otherwise need a server restart.

**Presets**: `role_analysis.py` PRESETS dict for quick form fill; analysis is always live.

## Commands

```bash
pip install -r requirements.txt           # runtime deps
pip install -r requirements-dev.txt       # pytest
streamlit run app.py                       # http://localhost:8501
pytest -q                                  # run the test suite
```

### Environment flags

- `TC_DEV=1` — enable hot module reload (dev only).
- `TC_TEMPLATE_STORE=file` (+ optional `TC_TEMPLATE_PATH`) — persist custom agent templates to disk instead of session.
- `TC_USE_REGISTRY=0` — disable GLEIF registry lookup (LLM-only disambiguation).
- `GEMINI_API_KEY`/`GOOGLE_API_KEY` — only used by the graphify tooling, not the app.

### Workflow Notes

- **Tests exist now**: `pytest` must stay green. PDF golden tests assert byte-identical output — they freeze `_ts` and the fpdf creation date in `tests/conftest.py`. New PDF sections must be guarded by their data key (e.g. `if r.get("workforce")`) so fixtures without that key stay byte-identical.
- **API key**: all Claude calls need a valid `sk-ant-...` key pasted in the sidebar at runtime.

## Important Architectural Constraints

1. **JSON-only + schema-validated**: prompts demand raw JSON; `_call()` parses it and `_validate()` checks it against a pydantic model. Missing required fields (e.g. `automation_score`) surface a friendly error.
2. **Market profiles**: `prompts.py::MARKETS` parametrizes market context. Luxembourg is the complete, default profile and its prompt output is kept **byte-identical** to the original `COMPANY_SYSTEM` (a test asserts this — do not regress it). Belgium is a beta skeleton.
3. **Session persistence**: results live in the browser session; `services/session_io.py` exports/imports them as JSON (never including the api_key). Custom agent templates can additionally persist to disk via `FileStore`.
4. **No API key storage**: keys are never written to disk, env, or server. Session export strips them by allow-list (only `org_roles`/`org_companies`/`custom_agent_templates` are serialised).
5. **Computed figures are not LLM output**: workforce/financial numbers come from `services/workforce.py` arithmetic.

## CSS & Branding

- Colors: Deloitte green `#86BC25`, black `#1A1A1A`, greys. Light theme pinned in `.streamlit/config.toml`.
- Typography: Cabinet Grotesk (Fontshare) for headings. Note `main.css` restores the Material Symbols icon font on icon elements so the `[data-baseweb] *` font override doesn't render icons as ligature text.
- Deloitte logo: base64 data URI in sidebar; also in PDF headers.

## PDF Export Details

- Package `services/pdf/` (`base.py`, `sections.py`, `builders.py`); `services/pdf_export.py` is a re-export shim.
- `_safe()` normalizes Unicode for DejaVu; characters that fail UTF-8 round-trip are dropped.
- Builders: `build_single_role_pdf`, `build_roles_pdf`, `build_single_company_pdf`, `build_companies_pdf`, `build_combined_pdf`. Role PDFs include guarded workforce + HR-advisory blocks.

## Known Gaps & Future Improvements

- `template_store.py` has the seam for a real per-user/project DB (`DBStore`), not yet implemented (needs identity/infra).
- GLEIF disambiguation live call should be smoke-tested with network access; its candidates are authoritative but `category` is coarse.
- Belgium market profile is beta (real regulators/players, placeholder trends).
- Project orchestration / work-order history lives in `ORCHESTRATION.md`.
