# 🧭 TalentCompass

**AI Workforce & Client Intelligence — Built for Deloitte Luxembourg**

TalentCompass is a Streamlit app that connects to Claude to generate:
- **Live role assessments** — automation potential, task breakdown, AI agent recommendations, reskilling, roadmap, and risk analysis — all driven by the actual job description you provide, nothing pre-coded.
- **Luxembourg client intelligence** — AI potential score, industry trends, competitor moves, key opportunities, strategic recommendations, and a Deloitte engagement angle.
- **Organization overview** — compare multiple role assessments in a single view with charts.

---

## Project Structure

```
talentcompass/
├── app.py                     # Streamlit entry point + sidebar + routing
├── requirements.txt
├── README.md
├── services/
│   ├── __init__.py
│   ├── claude_client.py       # All Anthropic API calls
│   └── prompts.py             # System prompts + user prompt builders
└── pages/
    ├── __init__.py
    ├── role_analysis.py       # Role Analysis page
    ├── client_research.py     # Client Research page
    └── org_overview.py        # Organization Overview page
```

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the app
```bash
streamlit run app.py
```

### 3. Open in browser
Streamlit will open automatically at `http://localhost:8501`

### 4. Enter your API key
Paste your `sk-ant-...` key in the sidebar. It is stored only in the browser session — never on disk or server.

---

## How it works

### Role Analysis
1. Enter a client name (optional), job title, department, company size, and job description.
2. Click **Analyze Role →**
3. The app sends your input to `claude-opus-4-5` via a structured JSON prompt.
4. Claude returns a full assessment: automation score, task breakdown, AI agents, reskilling, 3-phase roadmap, and risk management points.
5. All outputs are rendered as interactive charts and structured cards.

### Client Research
1. Enter a client company name and optionally an industry.
2. Click **Research Client →**
3. Claude generates a Luxembourg-market-focused profile covering:
   - AI potential score and summary
   - Industry AI trends with impact/timeline
   - Real competitor moves (Luxembourg/EU market players)
   - Key AI opportunities with priority tags
   - Risks, barriers, and mitigations
   - Recommended AI strategy and a Deloitte engagement angle

### Organization Overview
All roles analyzed during the session are automatically collected and visualized:
- Automation score bar chart
- Weekly hours saved chart
- Task distribution (Fully Automatable / AI-Augmented / Human-Only) stacked chart
- Individual role cards with key metrics

---

## Notes
- Requires an Anthropic API key with access to `claude-opus-4-5`
- API key is session-only and never stored
- All role and company assessments are dynamically generated — no hardcoded scores
- Presets are helper input templates only; the actual analysis is always live
