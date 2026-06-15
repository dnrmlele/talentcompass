# 🧭 TalentCompass

**AI Workforce Intelligence & HR Advisory**

TalentCompass is a Streamlit app that connects to Claude to generate:
- **Role assessments** — automation potential, task breakdown, AI agent recommendations, reskilling, roadmap, risks — driven by the actual job description you provide.
- **Workforce & financial impact** — FTE freed, annual payroll savings, transition cost and severance exposure, computed by real arithmetic from your headcount and loaded cost (not AI estimates).
- **HR management & advisory** — redeployment, reskilling investment, change management, retention priorities and workforce planning, generated on demand.
- **Client intelligence** — market-focused AI potential score, trends, competitor moves and a Deloitte engagement angle, with entity disambiguation for ambiguous company names.
- **Organization overview** — compare all analysed roles, with an org-wide workforce/financial rollup.
- **Agent library** — curated AI-agent templates you can apply to roles and extend.

---

## Project Structure

```
talentcompass/
├── app.py                      # Entry point: sidebar (key, model, session I/O) + routing
├── .streamlit/config.toml      # Pinned light theme
├── services/
│   ├── claude_client.py        # All Claude API calls (validated, error-handled)
│   ├── prompts.py              # System prompts + builders; market profiles
│   ├── schemas.py              # pydantic models validating every Claude response
│   ├── company_context.py      # Company-size inference
│   ├── session_io.py           # JSON session export/import
│   ├── agent_library.py        # AI-agent template library
│   ├── template_store.py       # Session/file persistence for custom templates
│   ├── registry.py             # GLEIF registry lookup for entity disambiguation
│   ├── workforce.py            # Deterministic FTE / payroll / severance maths
│   └── pdf/                    # Deloitte-branded PDF package (+ pdf_export.py shim)
├── pages/                      # role_analysis, client_research, org_overview,
│                               #   agent_library_page, reports_export
├── styles/main.css
├── assets/fonts/
├── tests/                      # pytest suite (+ golden PDF checksums)
├── requirements.txt
└── requirements-dev.txt
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
streamlit run app.py

# 3. Open http://localhost:8501 and paste your sk-ant-... key in the sidebar
```

Your API key is stored only in the browser session — never on disk or a server.

---

## How it works

### Role Analysis
1. Enter client (optional), job title, department, company size and job description.
2. (Optional) Open **Workforce inputs** and enter headcount + fully-loaded annual cost/FTE to unlock the financial impact figures.
3. Click **Analyze Role**. Claude returns automation score, task breakdown, AI agents, reskilling, roadmap and risks.
4. **Workforce & Financial Impact** (FTE freed, payroll savings, net savings, severance) is computed live from your inputs.
5. Click **Generate HR advisory** for redeployment, reskilling, change-management, retention and workforce-planning guidance.
6. Apply curated agents from the **Agent library** expander.

### Client Research
1. Enter a client name, market, and optional industry.
2. Click **Find entity** to list candidate organisations for an ambiguous name (e.g. a retailer vs a financial firm) and pick the right one — or **Research client** to go directly.
3. Claude generates a market-focused profile: AI potential, industry trends, competitor moves, opportunities, risks, strategy and a Deloitte angle.

### Agent Library
Browse built-in templates, create/edit/delete your own, and apply them to roles. Custom templates persist for the session (or to disk — see flags below) and travel with session export.

### Organization Overview
All analysed roles compared in charts, plus an org-wide workforce/financial rollup across roles that have headcount entered.

### Reports & Export
Download Deloitte-branded PDFs (single role/company, all, or a combined session report), and export/import your whole session as JSON.

---

## Configuration flags

| Env var | Effect |
|---------|--------|
| `TC_DEV=1` | Hot-reload code modules on each rerun (dev only; off by default). |
| `TC_TEMPLATE_STORE=file` | Persist custom agent templates to disk (`TC_TEMPLATE_PATH` to override the path). |
| `TC_USE_REGISTRY=0` | Disable the GLEIF registry lookup; use LLM-only entity disambiguation. |

```bash
# macOS / Linux              # Windows PowerShell
TC_DEV=1 streamlit run app.py    $env:TC_DEV=1; streamlit run app.py
```

---

## Development

- **Tests:** `pip install -r requirements-dev.txt` then `pytest` from the repo root.
- **Hot reload** is off by default — set `TC_DEV=1` to apply code edits without restarting.
- **PDF golden tests** assert byte-identical output; any new PDF section must be guarded by its data key so existing fixtures stay unchanged.

---

## Notes
- Model is selectable in the sidebar (`claude-haiku-4-5` fast / `claude-opus-4-5` quality).
- Financial figures (FTE, payroll, severance) are deterministic arithmetic on your inputs; automation scores and advisory are AI-generated.
- API key is session-only and never stored or exported.
- Luxembourg is the fully-supported market; Belgium is an early beta profile.
