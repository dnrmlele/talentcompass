# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tech Stack

**TalentCompass** is a Python-based web application for AI workforce intelligence analysis, built with:

- **Framework**: Streamlit (v1.35+) — interactive single-page UI with sidebar navigation
- **LLM Integration**: Anthropic Claude API (currently claude-haiku-4-5 for role analysis, claude-opus-4-5 referenced in README for future upgrades)
- **Data & Visualization**: Plotly (v5.22+), Pandas (v2.2+) for charts and tables
- **PDF Export**: fpdf2 (v2.8+) with custom Deloitte-branded templates
- **Styling**: Custom CSS with Deloitte brand colors; Cabinet Grotesk font via Fontshare
- **Dev Container**: Python 3.11 (Debian bookworm) for consistent development

## Project Purpose

TalentCompass generates dynamic, AI-driven assessments for:
1. **Role Analysis**: Automation potential, task breakdown, AI agent recommendations, reskilling roadmap, and risk analysis — all generated live from job descriptions
2. **Client Research**: Luxembourg market intelligence including AI potential scoring, industry trends, competitor moves, and Deloitte engagement angles
3. **Organization Overview**: Comparative charts across multiple role analyses
4. **Reports & Export**: Deloitte-branded PDFs for individual analyses or combined session reports

All assessments are dynamically generated via Claude API; no hardcoded scores or presets.

## Architecture

### Directory Structure

```
talentcompass/
├── app.py                     # Streamlit entry point, sidebar, page routing
├── services/
│   ├── claude_client.py       # Anthropic API wrapper; analyze_role() & research_company()
│   ├── prompts.py             # System prompts (ROLE_SYSTEM, COMPANY_SYSTEM) and prompt builders
│   ├── company_context.py     # Company size inference (inferred_size_to_company_size)
│   └── pdf_export.py          # PDF builders with Deloitte branding
├── pages/
│   ├── role_analysis.py       # Role Analysis UI & presets
│   ├── client_research.py     # Client Research form & results
│   ├── org_overview.py        # Comparative charts (automation, hours saved, task distribution)
│   └── reports_export.py      # Session history, tabbed review, PDF downloads
├── styles/main.css            # Deloitte brand styling (green #86BC25, fonts, components)
├── assets/fonts/              # DejaVuSans.ttf, DejaVuSans-Bold.ttf for PDF rendering
└── requirements.txt
```

### Key Design Patterns

**Session State Management**: Streamlit's `st.session_state` is the single source of truth for:
- `api_key`: User's Claude API key (never persisted, browser session only)
- `org_roles`: List of analyzed roles (each entry tagged with `_title`, `_client`, `_dept`)
- `org_companies`: List of researched companies
- `last_company_result`: Last company research result (enables client→role sync)

**Module Reloading**: `app.py` calls `importlib.reload()` on service modules before each page render to apply live code edits without restarting Streamlit.

**API Abstraction**: `services/claude_client.py` centralizes all Claude API calls with two main functions:
- `analyze_role(api_key, job_title, department, company_size, job_description, client_name)` → JSON with automation_score, tasks[], ai_agents[], roadmap[], risks[], stats
- `research_company(api_key, client_name, industry)` → JSON with company_profile, ai_potential_score, industry_ai_trends[], competitor_moves[], key_ai_opportunities[], risks_and_barriers[]

Both call `_call()` which strips markdown fencing from Claude's response and parses raw JSON.

**Prompt Engineering**: System prompts instruct Claude to output only valid JSON without markdown. User prompts are dynamically built with actual job descriptions or company names; no generic templates. Role analysis prompt explicitly instructs Claude to base all analysis on actual job description text.

**Presets System**: `role_analysis.py` includes PRESETS dict (Financial Analyst, Compliance Officer, HR Manager, Data Analyst, Fund Accountant) for quick form population during development/demo, but actual analysis is always live.

## Commands

### Install & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run the development server
streamlit run app.py

# Access at http://localhost:8501 in your browser
```

### Dev Container (VS Code)

If using `.devcontainer/devcontainer.json`:
- Open in Dev Container → automatically installs dependencies and launches Streamlit on port 8501
- Streamlit runs with `--server.enableCORS false --server.enableXsrfProtection false`

### Workflow Notes

- **No build or test command**: This is a runtime-only app; there are no tests or build steps.
- **Hot reload**: Streamlit reruns `app.py` on file save. Service modules are explicitly reloaded to pick up edits.
- **API key requirement**: All Claude calls require a valid `sk-ant-...` API key pasted in the sidebar at runtime.

## Important Architectural Constraints

1. **JSON-only responses**: Claude must return valid JSON. Both `_call()` in `claude_client.py` and system prompts enforce this strictly. If Claude returns markdown, JSON parsing fails.

2. **Exact JSON structure**: Role analysis and company research prompts specify exact JSON schemas with fixed keys. Claude must respect these structures or the UI will fail to render results.

3. **Luxembourg market focus**: Company research is heavily weighted toward Luxembourg market context (fund admin, banking, CSSF/CNPD compliance, etc.). Competitor names, regulatory frameworks, and industry trends are hardcoded in the system prompt.

4. **Session-only persistence**: API keys and all analysis results live only in the browser session. There is no backend database or file persistence (except PDF downloads). Refreshing the page clears all data.

5. **No API key storage**: Keys are never written to disk, environment variables, or server-side storage. They are validated at runtime only.

## CSS & Branding

- **Color scheme**: Deloitte green (#86BC25), black (#1A1A1A), greys for borders/backgrounds
- **Typography**: Cabinet Grotesk (imported from Fontshare) for headings; system fonts for body
- **Custom Streamlit overrides**: `main.css` hides default header, customizes buttons, inputs, alerts, metric cards, radio buttons, and tabs
- **Deloitte logo**: Embedded as base64 data URI in sidebar; also used in PDF headers

## PDF Export Details

- **Library**: fpdf2 with custom `_DeloittePDF` base class in `pdf_export.py`
- **Fonts**: DejaVu fonts (UTF-8 support); characters outside BMP are dropped or replaced
- **Safe text rendering**: `_safe()` function normalizes Unicode (em dashes, quotes, ellipses) for PDF compatibility
- **Multiple export modes**: Single role, all roles, single company, all companies, or combined session report
- **PDF builders**: `build_single_role_pdf()`, `build_roles_pdf()`, `build_single_company_pdf()`, `build_companies_pdf()`, `build_combined_pdf()`

## Known Gaps & Future Improvements

- Model is currently `claude-haiku-4-5` for cost/speed, but README mentions potential upgrade to `claude-opus-4-5` for higher quality
- Company research is hardcoded for Luxembourg; scaling to other markets would require system prompt rework
- No version pinning beyond minimum versions in `requirements.txt`
- No input validation beyond empty checks; malformed job descriptions or company names are passed directly to Claude

