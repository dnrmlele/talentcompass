# TalentCompass Upgrade Orchestration

Coordinator: Fable 5 session (this file is the single source of truth).
Workers: Opus 4.8 coding sessions — paste one work order per session.
Graph basis: `graphify-out/graph.json` (87 nodes, 161 edges, 10 communities).

## Status Board

| WO | Title | Wave | Status | Depends on | Files touched |
|----|-------|------|--------|-----------|---------------|
| WO-01 | Harden API layer | 1 | DONE | — | services/claude_client.py, pages/role_analysis.py, pages/client_research.py |
| WO-04 | Unit test suite (pure functions) | 1 | DONE | — | tests/ (new), requirements-dev.txt (new) |
| WO-02 | Schema validation | 2 | DONE | WO-01 | services/schemas.py (new), services/claude_client.py, requirements.txt |
| WO-03 | Model config in sidebar | 2 | DONE | WO-02 | services/claude_client.py, app.py |
| WO-05 | Split PDF monolith | 3 | DONE | WO-04 | services/pdf/* (new), services/pdf_export.py (shim), tests/conftest.py |
| WO-06 | Session save/load | 4 | DONE | WO-02 | services/session_io.py (new), app.py |
| WO-07 | Gate module-reload dev hack | 4 | DONE | WO-06 | app.py, README.md |
| WO-08 | Market parametrization | 4 | DONE | WO-02 | services/prompts.py, pages/client_research.py |
| WO-09 | Agent template library (slice 1) | 5 | DONE | WO-02, WO-06 | services/agent_library.py (new), pages/role_analysis.py, services/session_io.py, app.py, tests/test_agent_library.py (new) |
| WO-10 | Company entity disambiguation | 5 | DONE | WO-02, WO-08 | services/claude_client.py, services/prompts.py, services/schemas.py, pages/client_research.py, tests/test_disambiguation.py (new) |
| WO-10b | Registry-grounded candidates (GLEIF) | 6 | DONE | WO-10 | services/registry.py (new), services/claude_client.py, services/schemas.py, pages/client_research.py, tests/test_registry.py (new) |
| WO-11 | Agent Library page | 6 | DONE | WO-09 | pages/agent_library_page.py (new), app.py |
| WO-12 | Pluggable template persistence | 6 | DONE | WO-09 | services/template_store.py (new), services/agent_library.py, tests/test_template_store.py (new) |

Status values: READY / IN PROGRESS / REVIEW / DONE / BLOCKED.
Rule: two work orders that touch the same file never run in parallel. Waves encode this.

## Wave plan

- Wave 1 (parallel): WO-01, WO-04 — no file overlap.
- Wave 2 (parallel): WO-02, WO-03 — both touch `claude_client.py`; run WO-02 first, then WO-03 (small).
- Wave 3: WO-05 alone (large refactor, golden files from WO-04 protect it).
- Wave 4: WO-06 → WO-07 (both touch app.py, sequential), WO-08 parallel with either.

---

## WO-01 — Harden API layer

**Objective:** Make `_call()` in `services/claude_client.py` survive malformed Claude output and API errors instead of crashing the Streamlit UI.

**Context:** This is a Streamlit app (TalentCompass). All Claude API calls go through `_call()` (services/claude_client.py:10). It currently does a bare `json.loads` on the stripped response with no try/except, no retry, and constructs a new `anthropic.Anthropic` client on every call. Callers are `analyze_role()` (line 24) and `research_company()` (line 29), consumed by `pages/role_analysis.py` and `pages/client_research.py`.

**Tasks:**
1. Wrap the JSON parse in try/except. On `json.JSONDecodeError`, retry the API call exactly once with an appended user instruction: "Your previous reply was not valid JSON. Return ONLY the JSON object, no markdown, no commentary."
2. Catch `anthropic.APIError` (and subclasses like `AuthenticationError`, `RateLimitError`) and raise a single custom exception `ClaudeClientError(message: str, kind: str)` defined in the same module, where `kind` is one of: `"auth"`, `"rate_limit"`, `"bad_json"`, `"api"`.
3. In `pages/role_analysis.py` and `pages/client_research.py`, catch `ClaudeClientError` around the analyze/research calls and show `st.error()` with a friendly message per kind. Do not show tracebacks.
4. Do not change the public signatures of `analyze_role()` or `research_company()`.
5. Do not add new dependencies.

**Acceptance criteria:**
- Simulated malformed JSON response (mock) triggers exactly one retry, then `ClaudeClientError(kind="bad_json")` if still invalid.
- Invalid API key shows a friendly `st.error` in the UI, no traceback.
- Valid responses behave exactly as before (same dict returned).
- `python -c "from services.claude_client import analyze_role, research_company, ClaudeClientError"` succeeds.

**On completion:** update this file — set WO-01 status to REVIEW, note any deviations under "Worker notes" below.

---

## WO-04 — Unit test suite (pure functions)

**Objective:** Add pytest coverage for the pure, no-API parts of the codebase, plus golden-file PDF tests that will protect the later PDF refactor (WO-05).

**Context:** TalentCompass has zero tests. Pure targets: `services/prompts.py` (role_prompt at line 5, company_prompt at line 72), `services/company_context.py` (inferred_size_to_company_size at line 6), `services/pdf_export.py` (`_safe()` text normalizer, and 5 builders: build_single_role_pdf, build_roles_pdf, build_single_company_pdf, build_companies_pdf, build_combined_pdf). Do NOT test `services/claude_client.py` in this work order — it is being modified in parallel by another session.

**Tasks:**
1. Create `tests/` package and `requirements-dev.txt` containing `pytest>=8`.
2. `tests/test_prompts.py`: assert role_prompt/company_prompt embed the given job title, description, company name; assert system prompts demand JSON-only output.
3. `tests/test_company_context.py`: cover each size bucket plus unknown/empty input fallback.
4. `tests/test_pdf_safe.py`: `_safe()` handles em dashes, curly quotes, ellipses, and non-BMP characters without raising.
5. `tests/test_pdf_builders.py`: build each of the 5 PDFs from a small fixture dict (mimic real analyze_role/research_company output shape — see prompt schemas in services/prompts.py). Assert output is non-empty bytes starting with `%PDF`. Save each output's SHA256 to `tests/golden/checksums.json` and assert against it (regeneration flag via env var `UPDATE_GOLDEN=1`).
6. Do not modify any production code. If a function is untestable without modification, note it in "Worker notes" instead of changing it.

**Acceptance criteria:**
- `pytest` exits 0 from repo root.
- At least: 4 prompt tests, 4 company_context tests, 4 _safe tests, 5 builder tests.
- `tests/golden/checksums.json` exists and the golden assertion passes on a second run.

**On completion:** update this file — set WO-04 status to REVIEW.

---

## WO-02 — Schema validation (blocked until WO-01 done)

**Objective:** Validate Claude's JSON against typed schemas at the API boundary so the UI never KeyErrors on missing/odd fields.

**Context:** Role analysis JSON shape: automation_score, tasks[], ai_agents[], roadmap[], risks[], stats. Company research JSON shape: company_profile, ai_potential_score, industry_ai_trends[], competitor_moves[], key_ai_opportunities[], risks_and_barriers[]. Exact field names: read them from `services/prompts.py` prompt text — the prompts specify the schema Claude must return.

**Tasks:**
1. New `services/schemas.py` with pydantic v2 models `RoleAnalysis` and `CompanyResearch` mirroring the prompt schemas. All nested list-item fields Optional-with-default where the prompt does not guarantee them.
2. Add `pydantic>=2` to requirements.txt.
3. In `services/claude_client.py`, validate parsed dict through the model and return `model.model_dump()` (keep dict return type — do not change callers' access patterns).
4. Validation failure raises `ClaudeClientError(kind="bad_json")` (from WO-01).
5. Update pages only if a field access provably mismatches the schema.

**Acceptance criteria:**
- Missing optional field → defaults applied, UI renders.
- Missing required field (e.g. automation_score) → friendly error, no traceback.
- Existing tests (WO-04) still pass.

---

## WO-03 — Model config (blocked until WO-02 done)

**Objective:** Remove hardcoded model string (services/claude_client.py:13). Sidebar selectbox: "claude-haiku-4-5 (fast)" default, "claude-opus-4-5 (quality)". Store in `st.session_state["model"]`; `_call()` reads it with haiku fallback. Show one-line cost hint near the selector.

**Files:** services/claude_client.py, app.py.

**Acceptance criteria:** switching model changes the model param actually sent (verify via mock); no code edit needed to switch; default behavior identical to today.

---

## WO-05 — Split PDF monolith (blocked until WO-04 done)

**Objective:** Break `services/pdf_export.py` into `services/pdf/base.py` (_DeloittePDF, _safe, _h, _subh, _body, bullets, fonts/logo path helpers), `services/pdf/sections.py` (_write_role_section, _write_company_section), `services/pdf/builders.py` (5 build_* functions). Keep `services/pdf_export.py` as a thin re-export shim so existing imports keep working.

**Acceptance criteria:** golden checksums from WO-04 unchanged (byte-identical PDFs); `from services.pdf_export import build_combined_pdf` still works; pytest green.

---

## WO-06 — Session save/load (blocked until WO-02 done)

**Objective:** Sidebar "Export session" → JSON download of org_roles + org_companies (+ schema version field, never the API key). "Import session" file-uploader → validate via services/schemas.py → restore state.

**Files:** services/session_io.py (new), app.py, pages/reports_export.py.

**Acceptance criteria:** analyze → export → hard refresh → import → org overview charts and PDF exports identical; importing a file with an api_key field strips it; invalid file → friendly error.

---

## WO-07 — Gate module-reload hack (blocked until WO-06 done)

**Objective:** `_reload_modules()` (app.py:8) runs `importlib.reload` on every rerender. Gate behind `TC_DEV=1` env var; skip entirely otherwise. Add a README note for contributors.

**Acceptance criteria:** without TC_DEV no reload calls happen (assert via monkeypatched importlib in a test); with TC_DEV=1 behavior identical to today.

---

## WO-08 — Market parametrization (blocked until WO-02 done)

**Objective:** Extract Luxembourg specifics from COMPANY_SYSTEM in services/prompts.py into a MARKETS dict (regulators, competitor names, trends per market). Luxembourg = default and only complete profile; add one skeleton second market (Belgium) labeled "beta". Market dropdown in pages/client_research.py feeds company_prompt.

**Acceptance criteria:** Luxembourg output prompt text byte-identical to today's COMPANY_SYSTEM; selecting Belgium produces a coherent prompt with Belgian regulator placeholders; prompt tests updated and green.

---

## Worker notes

(Workers append findings, deviations, and follow-ups here. Coordinator triages.)

### WO-01 (Opus 4.8, 2026-06-12) — REVIEW

**Done:**
- `_call()` hardened: split into `_send()` (API) + `_parse()` (strip fences + json.loads). On first `JSONDecodeError`, retries once — appends the prior assistant reply + the exact retry instruction string. Second failure → `ClaudeClientError(kind="bad_json")`.
- `ClaudeClientError(message, kind)` defined in same module. `anthropic.AuthenticationError` → `"auth"`, `RateLimitError` → `"rate_limit"`, `APIError` (catch-all base, ordered last) → `"api"`. Both the initial and retry sends are wrapped.
- Public signatures of `analyze_role`/`research_company` unchanged. No new deps.
- Both pages now catch `ClaudeClientError` and `st.error()` a friendly per-kind message via local `_ERROR_MESSAGES` map. No tracebacks shown.

**Verification:** Stub-injected `anthropic` (module not installed in this env) — confirmed all 6 paths: valid no-retry, bad→good single retry, bad×2→bad_json (exactly 2 API calls), auth, rate_limit, api. Retry message asserts the appended instruction. ALL PASS.

**Deviations:**
- D1: Status board "Files touched" for WO-01 listed only `services/claude_client.py`, but Task 3 explicitly requires editing `pages/role_analysis.py` and `pages/client_research.py`. Followed the task body (authoritative) and edited all three. Updated the board's Files-touched cell to match. No other WO in Wave 1 (WO-04) touches these pages, so no parallel-conflict risk.
- D2: Could not run the literal acceptance command `python -c "from services.claude_client import ..."` — `anthropic` is not installed in this environment (no venv; system Python 3.13). Import logic is sound; the only failure is the missing third-party module. Reviewer should run `pip install -r requirements.txt` then re-run the import check.

**Follow-up for WO-02:** the retry appends the bad assistant turn into history; if WO-02 adds schema validation inside `_call()`, a schema failure should likely NOT trigger the JSON retry (it's valid JSON, wrong shape) — current code only retries on `JSONDecodeError`, so WO-02 raising `bad_json` directly is compatible.

### WO-02 (Fable coordinator session, 2026-06-12) — REVIEW

**Done:**
- New `services/schemas.py`: pydantic v2 models `RoleAnalysis` + `CompanyResearch` mirroring the exact JSON in `services/prompts.py`. All models inherit `_Base` with `model_config = ConfigDict(extra="allow")` so keys Claude returns beyond the schema are preserved through `model_dump()` (no data loss). Only `automation_score` (role) and `ai_potential_score` (company) are required; every other field Optional-with-default (lists → `[]`, sub-objects → empty model) per "Optional unless the prompt guarantees them".
- `services/claude_client.py`: added `_validate(data, model_cls)` helper. `analyze_role`/`research_company` now return `_validate(_call(...), Model)`. Public signatures unchanged.
- `requirements.txt`: added `pydantic>=2`.

**Carry-over honored (from WO-01 note):** `_validate` runs AFTER `_call()` finished its `json.JSONDecodeError` retry. A pydantic `ValidationError` is valid-JSON/wrong-shape → raised DIRECTLY as `ClaudeClientError(kind="bad_json")`, never re-routed through the API JSON retry. Confirmed in code + smoke test.

**Verification (smoke, py -3.13):** role defaults applied on `{automation_score:80}`; missing `automation_score`/`ai_potential_score` → `ValidationError`; extra key survives `model_dump`; lax coercion `score:"85"`→85; `_validate` wrong-shape → `ClaudeClientError(kind="bad_json")`; WO-01 imports intact. ALL PASS. Full pytest: **24 passed** (WO-04 suite untouched/green). black-formatted both files.

**Deviations:**
- D3: Board "Files touched" for WO-02 listed the two `pages/` files as possible edits. Verdict: NO page edits needed. The only bracket access on the result dict is `result["_title"]/["_dept"]/["_client"]` in `pages/role_analysis.py:202-204` — those are WRITES tagging the returned (plain, mutable) dict, not reads, so `model_dump()` returning a normal dict keeps them working. Updated the board's Files-touched cell to drop the two pages and add `requirements.txt` (actually touched).
- D4 (advisory, no action): list-of-string fields (`reskilling.develop`, `roadmap[].items`, `risk.items`, `strategy.quick_wins`) typed `list[str]`. If Claude ever emits a non-string item, pydantic lax will reject (→ bad_json). Acceptable — matches prompt contract; pages already `str(x)` defensively if it ever loosens. Flag for WO-03/later if false-positives appear in practice.

**For WO-03 (next, sequential — same file `services/claude_client.py`):** the hardcoded model string is at `services/claude_client.py` inside `_send()` (`model="claude-haiku-4-5"`), not at the old line 13 — WO-01 refactored `_call` into `_send`/`_parse`. Point WO-03 at `_send()`.

### WO-03 (Fable coordinator session, 2026-06-12) — DONE

**Done:**
- `services/claude_client.py`: added `_DEFAULT_MODEL = "claude-haiku-4-5"` + `_resolve_model()` (lazy, defensive `st.session_state.get("model")` read; falls back to default outside a Streamlit run). Threaded an optional `model` param through `_call` → both `_send` calls; `_send` uses `model or _resolve_model()`. `analyze_role`/`research_company` pass no model, so they resolve from session_state — exactly the sidebar path. Hardcoded string removed from `_send`.
- `app.py`: sidebar "Model" selectbox after the API-key block. Labels "claude-haiku-4-5 (fast)" (default, index 0) / "claude-opus-4-5 (quality)" → mapped to ids → `st.session_state["model"]`. One-line cost-hint caption.

**Verification (mock anthropic, py -3.13):** explicit `model=` → `messages.create(model="claude-opus-4-5")`; session_state model → opus sent via `analyze_role`; unset session_state → haiku fallback; default constant correct. Full pytest **24 passed**. black-formatted both files.

**Deviations:**
- D5: Spec said "_send reads it [session_state]". Implemented the read inside `_resolve_model()` (called by `_send`) rather than literally inlining `st.session_state` in `_send`, so the client degrades gracefully (falls back to haiku) when called with no Streamlit runtime — required for the mock-based acceptance test and any non-UI use. Behaviour matches spec intent: sidebar choice flows to the API call, haiku when unset.
- D6 (interaction note for WO-07): app.py reloads `services.claude_client` every render via `_reload_modules`, and sets `session_state["model"]` every render — no staleness. When WO-07 gates the reload hack, no change to model logic is needed.

### WO-05 (Fable coordinator session, 2026-06-12) — DONE

**Done:**
- New `services/pdf/` package: `base.py` (`_DeloittePDF`, colours, `_FONT_DIR`, `_root`, `_logo_path`, `_safe`, `_ts`, `_h`, `_subh`, `_body`, `_bullets`), `sections.py` (`_write_role_section`, `_write_company_section`), `builders.py` (5 `build_*`), plus `__init__.py`.
- `services/pdf_export.py` reduced to a re-export shim: `_safe`, `_ts`, `_DeloittePDF`, and the 5 builders. Existing imports unchanged — `pages/reports_export.py` and `app.py` untouched, NO page edits needed.
- Goldens GREEN without regeneration across two runs → PDF bytes byte-identical → refactor is behavior-preserving.

**Critical correctness — path depth:** `base.py` sits one level deeper than the old module, so `_FONT_DIR` and `_root()` use `parent.parent.parent` (was `parent.parent`) to resolve to the SAME repo root. Fonts + logo are embedded in the PDF bytes; a wrong depth would have silently changed output / broken font load. Verified via goldens.

**Deviations:**
- D7 (the pre-flagged one): builders resolve `_ts` / `_DeloittePDF` in the `services.pdf.builders` namespace, so the WO-04 freeze fixture's patch targets in `tests/conftest.py` were moved from `services.pdf_export.*` to `services.pdf.builders.*`. This is the allowed extra-file edit. Without it the creation_date freeze would not reach the builders and goldens would flap. conftest now imports `services.pdf.builders as pdf_builders` and patches there.
- D8 (advisory): black re-wrapped long f-string `multi_cell` calls in the new modules — formatting only, f-string contents identical, goldens confirm byte output unchanged.

**Wave-4 readiness:** WO-06 (session io) and WO-08 (markets) both depend only on WO-02 (DONE) → both READY. They touch disjoint files (WO-06: session_io.py/app.py/reports_export.py; WO-08: prompts.py/client_research.py) → may run in PARALLEL. WO-07 still BLOCKED on WO-06 (both edit app.py → sequential after WO-06).

### WO-06 (Fable coordinator session, 2026-06-12) — DONE

**Done:**
- New `services/session_io.py`: `export_session(state)→bytes` (JSON of `org_roles` + `org_companies` + `app`/`version` tags; pulls ONLY those two keys, so `api_key` and `model` are never serialised). `import_session(raw)→{org_roles, org_companies}` validates every record through `services.schemas` (RoleAnalysis/CompanyResearch), fills defaults, preserves `_title/_dept/_client` UI tags (extra="allow"), and strips any `api_key` from records. `SessionImportError` carries friendly messages; raised on bad UTF-8, bad JSON, non-dict, missing/over-range `version`, non-list collections, or schema `ValidationError`.
- `app.py`: sidebar "Session" block — `st.download_button` (Export) + `st.file_uploader` (Import). Import guarded by a sha256 digest in `st.session_state["_imported_digest"]` so the same upload doesn't re-import on every rerun; success → restore state + `st.rerun()`; `SessionImportError` → `st.error`, no traceback. Added `hashlib` import.

**Security verification (smoke, py -3.13):** `sk-ant-SECRET` and the model id are both absent from export bytes; `api_key` inside an imported record is stripped; 4 malformed inputs all raise `SessionImportError` (no traceback). Round-trip preserves UI tags + fills schema defaults. Full pytest **24 passed**. black clean. `app.py` parses.

**Deviations:**
- D9: Board listed `pages/reports_export.py` in WO-06's touch set, but the spec's UI description says "Sidebar". Implemented entirely in the `app.py` sidebar + `services/session_io.py`; `pages/reports_export.py` left untouched (no import-path change needed). Board Files-touched updated to drop it. Keeps the diff localized — relevant because WO-07 edits app.py next.
- D10 (security note, by design): export is a strict allow-list (only `org_roles`/`org_companies` copied), not a denylist — future session keys can't accidentally leak. `_imported_digest` is internal and not exported (it lives in session_state, never read by export).

**For WO-07 (next, same file app.py):** my edits are the `hashlib` import (line ~3), `from services import session_io` (line ~50), and the "Session" sidebar block (lines ~142-174). WO-07 targets `_reload_modules` (line ~9) and the page-routing reload calls (lines ~181-199) — disjoint from my block, clean to layer on top.

### WO-08 (Opus 4.8, 2026-06-12) — REVIEW

**Done:**
- `services/prompts.py`: added `MARKETS` dict keyed by market name, each holding `label`, `beta`, `industries`, `key_players`, `regulators`, `competitor_descriptor`, `trends`. **Luxembourg** = full default profile; **Belgium** = beta skeleton (real regulators FSMA/NBB/GBA-APD + real players KBC/Belfius/Euroclear/etc.; `trends` is an explicit placeholder string).
- `COMPANY_SYSTEM` is now built by `company_system("Luxembourg")` and `company_prompt(client_name, industry="", market=None)` parametrizes the market — both **byte-identical** to the originals for Luxembourg (verified, see below).
- Market resolution via `_resolve_market(market)`: explicit arg wins; else reads `st.session_state["market"]` defensively (try/except, same pattern WO-03 used for model); else falls back to Luxembourg. Unknown market key → Luxembourg.
- `pages/client_research.py`: added "Market" `selectbox` (key=`"market"`, `format_func` shows "Belgium (beta)") inside the research form + a beta caption when a beta market is picked; spinner text now uses the selected market.

**HARD CONSTRAINT verification:** asserted current `COMPANY_SYSTEM` == original literal and `company_prompt(...)` == original builder output across 3 (name, industry) combos — byte-identical, pass. Belgium prompt is coherent: contains "this Belgium client", FSMA + NBB, "real Belgian/EU market player", and zero "Luxembourg" leakage.

**Tests:** `py -3.13 -m pytest -q` → **24 passed** (prompt tests green; 32 warnings are pre-existing fpdf `ln=` deprecations, not from this WO).

**Deviations:**
- D11: WO-08 may only touch prompts.py + client_research.py, but the market value has to reach `company_prompt`, which is called by `research_company` in `claude_client.py` (out of scope). Resolved without touching claude_client: `company_prompt` reads `st.session_state["market"]` defensively (mirrors WO-03's `_resolve_model`). Dropdown sets that key. `research_company`'s call `company_prompt(client_name, industry)` is unchanged and still works (market defaults via session/Luxembourg).
- D12 (minor, by design): the JSON field name `"luxembourg_presence"` is the literal key Claude must return (schema in WO-02's `CompanyResearch`), so the *key* stays `luxembourg_presence` for all markets; only its `<description>` placeholder text is market-parametrized (`their {label} role and footprint`). Renaming the key would break the schema + UI access in client_research.py. Left as-is.
- D13: `MARKETS[*]["trends"]` is carried per the WO spec ("trends per market") but is **not yet injected** into any prompt (current prompts let Claude generate trends freely). It's metadata for a future WO; Belgium's value is flagged as placeholder. No output impact.

**For coordinator:** Belgium is beta-quality only — regulators/players are real but unreviewed by a Belgian SME, and `trends` is a placeholder. Recommend a follow-up WO to (a) inject `trends` into `company_system`/`company_prompt` if desired, and (b) have a market expert validate Belgium before un-beta-ing.

## WO-09 — Agent template library (slice 1) — DONE

**Objective (delivered):** Consultants apply curated AI-agent templates to a role and save tweaked agents back to a library, instead of trusting a fresh Claude generation each time. Addresses the "are these figures real?" credibility concern by putting a human-curated, reproducible layer over the LLM output.

**Design — persistence seam:** `services/agent_library.py::get_templates(state)` = built-in constant templates + session custom templates. Custom templates live in `session_state["custom_agent_templates"]` today; a future WO swaps that store for a per-user/project DB behind the SAME accessor, no UI change. `services/session_io.py` export/import carries the custom list (sanitised), so saved templates already survive a session round-trip — the immediate bridge to real persistence.

**Files:** `services/agent_library.py` (new: 6 Luxembourg-seeded built-ins + get_templates/save_template/apply_to_role/sanitize_custom_templates), `pages/role_analysis.py` ("Agent library" expander under the AI-agents grid — multiselect to add, selectbox+category to save), `services/session_io.py` (carry `custom_agent_templates`), `app.py` (restore on import), `tests/test_agent_library.py` (7 tests).

**Verification:** 31/31 pytest (24 prior + 7 new). E2E: apply built-in to a role → appears in ai_agents (+ PDF, same object as org_roles entry); save custom → reusable; export→import round-trips custom templates + applied agents; no credential leak. black clean.

**Deferred:** WO-11 = dedicated "Agent Library" page + nav (browse/edit/delete). WO-12 = DB persistence behind get_templates accessor (the seam is ready).

---

## WO-10 — Company entity disambiguation (SPEC, not yet built)

**Problem (user-reported):** Client Research sends only the bare company name; Claude guesses which entity it is. Ambiguous names map to multiple real entities — e.g. "Cactus" in Luxembourg is BOTH a retail supermarket group AND a financial/holding entity. The research can silently profile the wrong sector.

**Objective:** Before committing to a full research run, resolve WHICH entity the consultant means, so the profile is anchored to the correct sector/registration.

**Proposed approach (two-step, lightweight):**
1. New `services/claude_client.py::disambiguate_company(api_key, name, market)` → returns a short list of candidate entities for that name in the selected market: each `{legal_name, sector, short_description, hint}` (e.g. registration type / RCS hint). Reuses `_call` + a new schema `CompanyCandidates` (WO-02 style, validated).
2. New prompt builder `prompts.py::disambiguation_prompt(name, market)` instructing market-aware candidate listing (uses the WO-08 MARKETS context).
3. `pages/client_research.py`: after the consultant types a name and clicks a new "Find entity" step, show the candidates as selectable cards/radio; the chosen candidate's `legal_name` + `sector` are then passed into `research_company` as strengthened context (industry/legal name), removing the guess. If only one candidate or the consultant skips, fall back to today's direct path.

**Files:** services/claude_client.py, services/prompts.py, pages/client_research.py (+ a schema in services/schemas.py).

**Risks:** extra API call/latency + cost per research (one cheap haiku call); candidate list itself is LLM-generated so not authoritative — frame as "select the best match", not ground truth; must not break the existing one-shot research path (keep skip/fallback).

**Acceptance:** typing an ambiguous name ("Cactus", Luxembourg) yields ≥2 distinct candidates with different sectors; selecting one routes that sector/legal name into research_company so the profile matches the chosen entity; single-candidate or skip → unchanged behaviour; pytest stays green with a new disambiguation prompt/schema test.

**Open question for user:** authoritative source. Pure-LLM candidates are still guesses (better-anchored, but unverified). If you want real disambiguation, candidates should come from a registry (e.g. Luxembourg RCS / LBR, or GLEIF LEI data) — that's a WO-10b with an external data source. Recommend shipping the LLM-assisted version first, then grounding it if the accuracy matters for client work.

**DELIVERED (LLM-assisted, user chose this option 2026-06-13):**
- `services/schemas.py`: `CompanyCandidate` + `CompanyCandidates` (no required field — empty list valid → UI falls back to direct research).
- `services/prompts.py`: `DISAMBIG_SYSTEM` + `disambiguation_prompt(name, market)` — market-aware via existing MARKETS/_resolve_market.
- `services/claude_client.py`: `disambiguate_company(api_key, name, market="")` → `_call` (max_tokens=1200, cheap) + `_validate(CompanyCandidates)`.
- `pages/client_research.py`: removed st.form (multi-step needs free reruns); two buttons — "Find entity" (lists candidates as a radio with sector + hint) and "Research client" (direct path, unchanged). Selecting a candidate routes its legal_name → client_name and sector → industry into the SHARED `_run_research` helper, killing the guess. Single-candidate or skip → today's behaviour. Candidate state cleared after a successful run.
- `tests/test_disambiguation.py` (5 tests).
- **Verification:** 36/36 pytest; WO-08 Luxembourg byte-identity RE-CONFIRMED (no regression from the prompts.py additions); disambiguate_company validated-candidates path proven via mock (Cactus → retail vs financial). Server restarted to load it.
- **Caveat carried:** candidates are LLM-generated — framed in UI as "pick the right one", not ground truth. Registry grounding (RCS/LBR/GLEIF) remains the open WO-10b if client-grade accuracy is needed.

## WO-10b / WO-11 / WO-12 (Fable session, 2026-06-13) — DONE

**WO-12 — Pluggable template persistence (DB-ready seam):** `services/template_store.py` defines `TemplateStore` interface + `SessionStore` (default, today's behaviour) + `FileStore` (JSON on disk, survives restarts). `get_store(state)` picks the backend from env `TC_TEMPLATE_STORE` (session|file) + `TC_TEMPLATE_PATH`. `agent_library` now delegates `get_templates/save_template/list_custom_templates/delete_template` through the store and mirrors into `state[CUSTOM_KEY]` so session export/import + sidebar still see customs in either mode. `CUSTOM_KEY` moved to template_store, re-exported from agent_library (session_io import unchanged). No DB server (app has no backend); a future `DBStore(project_id)` slots into the same interface. 7 new tests.

**WO-11 — Agent Library page:** `pages/agent_library_page.py` — browse built-ins (read-only), create/edit/delete custom templates (CRUD via the store), persistence-mode caption. Nav entry "AGENT LIBRARY" + routing added to app.py (reloads template_store/agent_library/page when TC_DEV). UI page (no unit tests; syntax-verified).

**WO-10b — Registry-grounded candidates:** `services/registry.py` queries the free GLEIF LEI API (stdlib urllib, no new dep) for authoritative legal entities. `disambiguate_company(..., use_registry=True)` tries the registry first → real candidates tagged `source="registry"`; on no-match / disabled (`TC_USE_REGISTRY=0`) / any network error → fails safe to the LLM listing tagged `source="llm"`. `CompanyCandidate.source` added to schema. client_research shows "✓ Authoritative — GLEIF registry" vs "AI-listed — verify before use" on the chosen candidate. 6 new tests (parser, disabled, network-error-safe, registry-preferred-no-LLM-call, LLM fallback).

**Verification:** 49/49 pytest (was 36 → +5 disambig already counted; net +13 across these three: 7 store + 6 registry). black clean across all touched files. Server restarted to load (TC_DEV reload off by default).

**Bug caught + fixed mid-build:** LLM-fallback `source` tagging used `setdefault`, but `model_dump()` already emits `source=None` (schema default) so the key existed → tag never applied. Switched to `if not c.get("source")`. Test `test_disambiguate_falls_back_to_llm` caught it.

**Honesty note (WO-10b):** the live GLEIF call could not be exercised in this sandbox (no network). The PARSER and the registry→LLM fallback control flow are unit-tested with mocked HTTP; the live request path is fail-safe (any exception → LLM fallback). First real-network run should be smoke-tested by the user. GLEIF `category` is coarse (GENERAL/FUND/BRANCH), so registry candidates disambiguate by distinct legal_name + LEI rather than rich sector — the LLM path still gives richer sector when the registry is thin.

## Coordinator log

- 2026-06-12: Plan created. Wave 1 (WO-01, WO-04) released.
- 2026-06-12: WO-01 DONE. Acceptance verified after `pip install -r requirements.txt` (resolves D2). D1 accepted — board Files-touched updated by worker, task body was authoritative. D2 accepted. WO-01 follow-up note for WO-02 retained: schema-validation failure must NOT trigger the JSON-decode retry (valid JSON, wrong shape) — raise bad_json directly.
- 2026-06-12: WO-04 IN PROGRESS claim was phantom (no tests/ on disk). Executed inline in Fable coordinator session via 3 internal sub-agents (Analyzer → Test Writer → Refiner). Result: 24 tests pass twice, golden PDFs byte-stable (froze _ts + fpdf creation_date/ID). 8 files added (tests/ + requirements-dev.txt), zero production source touched. WO-04 DONE.
- 2026-06-12: WO-04 sub-agents corrected 2 design errors — (1) non-BMP emoji is valid UTF-8 so _safe KEEPS it (spec wrongly said dropped); (2) "...enterprise" substring hits Enterprise bucket before SME, fixtures adjusted. company_context got 11 cases (board criterion >=4).
- 2026-06-12: WO-01 D2 resolved — `pip install -r requirements.txt pytest black` done; the import acceptance check `from services.claude_client import analyze_role, research_company, ClaudeClientError` now PASSES.
- 2026-06-12: Wave 1 COMPLETE (WO-01 + WO-04 DONE). Wave 2 unlocked. Per wave plan WO-02 and WO-03 both touch services/claude_client.py → sequential, NOT parallel: WO-02 READY now; WO-03 dependency changed WO-01→WO-02 and stays BLOCKED until WO-02 DONE. Paste blocks emitted for both.
- Tree note (from Refiner): working tree carries WO-01 production edits + WO-04 tests together on same branch; no commits made yet (awaiting user). __pycache__ / graphify-out / CLAUDE.md loose — consider .gitignore.
- 2026-06-12: WO-02 DONE. Acceptance verified (smoke + 24/24 pytest, pydantic installed). D3 (no page edits) + D4 (list[str] strictness, advisory) logged. Wave 2 WO-03 RELEASED — sequential, edits services/claude_client.py (same file WO-02 touched, now free). Hardcode moved by WO-01 refactor: model string lives in _send(), not old line 13.
- 2026-06-12: WO-03 DONE. Verified model param actually sent (mock), session_state→opus, haiku fallback; 24/24 pytest; black clean. D5 (read via _resolve_model not raw inline) + D6 (reload interaction note for WO-07) logged. WAVE 2 COMPLETE (WO-02 + WO-03 DONE). Wave 3 unlocked → WO-05 (PDF split) RELEASED; WO-04 goldens protect it (byte-identical PDF assertion). WO-05 runs ALONE in its wave (large refactor, no parallel).
- 2026-06-12: WO-05 DONE. PDF monolith → services/pdf package + shim; goldens byte-identical (behavior-preserving proof); 24/24 pytest; black clean. D7 (conftest patch targets moved to services.pdf.builders) + D8 (black wrap, advisory) logged. WAVE 3 COMPLETE. Wave 4 unlocked: WO-06 + WO-08 both READY and PARALLEL-SAFE (disjoint files); WO-07 stays BLOCKED on WO-06 (shared app.py). Paste blocks emitted for WO-06 and WO-08.
- 2026-06-12: WO-06 DONE (ran in parallel with WO-08, which is owned by a separate Opus session — disjoint files, no conflict). Session export/import via services/session_io.py + app.py sidebar. Security verified: api_key + model never exported, api_key stripped from imports, malformed files → friendly SessionImportError; 24/24 pytest; black clean. D9 (reports_export.py not needed) + D10 (allow-list export) logged. WO-07 RELEASED — edits app.py, disjoint from WO-06's sidebar block; safe to start now even while WO-08 runs (WO-08 touches prompts.py/client_research.py only). NOTE: WO-06 + WO-07 + WO-03 all edit app.py — since they run in the SAME coordinator session sequentially, no merge race; if WO-07 is dispatched to a separate session, it must start from the current app.py (post-WO-06).
- 2026-06-12: WO-07 DONE. _reload_modules gated behind TC_DEV=1 (single in-function guard covers all call sites); README Development section added. Verified via monkeypatched importlib.reload: no reload when TC_DEV unset or =0, fires at =1; 24/24 pytest; black clean. No deviations.
- 2026-06-12: WO-08 DONE. Independently gated the HARD CONSTRAINT: loaded git HEAD prompts.py (decoded UTF-8 — caught a harness bug where subprocess text=True mis-decoded as cp1252 and mojibake'd the ↓ glyph, a FALSE diff) and asserted ROLE_SYSTEM/role_prompt unchanged, COMPANY_SYSTEM + company_prompt(Luxembourg) BYTE-IDENTICAL across 3 combos, Belgium coherent with no Luxembourg leak, backward-compatible company_prompt signature. 24/24 pytest. D11 (market via session_state, claude_client untouched) + D12 (luxembourg_presence JSON key kept for schema) + D13 (MARKETS trends carried but not yet injected) accepted. Follow-up flagged by worker: inject trends + have a Belgian expert validate before un-beta-ing — candidate WO-09 if desired.
- 2026-06-12: WAVE 4 COMPLETE. ALL 8 WORK ORDERS DONE. Suite 24/24 green; black clean across all touched files. Working tree uncommitted — handoff to user for commit/PR + recommend .gitignore for __pycache__/ and graphify-out/.
- 2026-06-12: Post-MVP. Added .gitignore + untracked __pycache__ from index (user-approved). Added .streamlit/config.toml pinning light theme + Deloitte palette (fixed dark-mode contrast clash). Fixed Material-icons-as-text bug in styles/main.css ([data-baseweb] * font override was clobbering the icon font → ligature text like "keyboard_arrow_down"; added a restore rule).
- 2026-06-12: WO-09 DONE (new Wave 5). Agent template library slice 1 — apply/save curated agents, session persistence with DB-ready accessor seam, export/import carries custom templates. 31/31 pytest. Server restarted to load it (TC_DEV reload is off by default, so Python changes need a restart).
- 2026-06-12: WO-10 SPEC'd (company entity disambiguation, e.g. "Cactus" supermarket vs financial entity). Two-step LLM candidate-selection design; open question logged on whether to ground candidates in a real registry (RCS/LBR/GLEIF) vs LLM-only. Awaiting user go-ahead to build.
- 2026-06-13: WO-10 DONE (user chose LLM-assisted). "Find entity" step lists candidates → consultant picks → chosen legal_name+sector feed research, removing the guess. 36/36 pytest; WO-08 byte-identity re-confirmed (no regression). Server restarted. WO-10b (registry-grounded candidates) left as the open follow-up for client-grade accuracy. 10 work orders DONE total (WO-01..10); WO-11 (Agent Library page) + WO-12 (DB persistence) + WO-10b (registry) remain as future candidates.
- 2026-06-13: WO-12 + WO-11 + WO-10b DONE in one session. Pluggable persistence (session/file store, DB-ready), Agent Library CRUD page + nav, GLEIF registry-grounded disambiguation with fail-safe LLM fallback. 49/49 pytest; black clean; server restarted. 13 work orders DONE total. Open: WO-12b (real DBStore behind the store interface, needs identity/infra), live GLEIF smoke test (sandbox had no network). Working tree still uncommitted — user's commit/PR call.
