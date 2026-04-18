from pathlib import Path
import base64
import importlib
import sys
import streamlit as st


def _reload_modules(*names: str) -> None:
    """Streamlit re-runs app.py but keeps imported submodules cached; reload so edits apply."""
    for name in names:
        mod = sys.modules.get(name)
        if mod is not None:
            importlib.reload(mod)

st.set_page_config(
    page_title="TalentCompass",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _load_logo_data_uri(path: Path) -> str:
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{data}"


LOGO_URI = _load_logo_data_uri(
    Path(__file__).resolve().parent / "Logo_of_Deloitte.svg.png"
)

# ── Load external CSS ────────────────────────────────────────────────────────
def _load_css(css_path: str) -> None:
    """Load CSS from external file."""
    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

_load_css(Path(__file__).resolve().parent / "styles" / "main.css")

import pages.client_research as client_research
import pages.org_overview as org_overview
import pages.reports_export as reports_export
import pages.role_analysis as role_analysis

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f"""
        <a href='https://www2.deloitte.com' target='_blank'
           style='display:flex;align-items:center;gap:14px;text-decoration:none;
                  color:inherit;padding:14px 0;
                  border-bottom:3px solid #86BC25;margin-bottom:16px;'>
            <img src='{LOGO_URI}' alt='Deloitte logo' style='height:36px;width:auto;'/>
            <div style='display:flex;flex-direction:column;'>
                <span style='font-weight:800;font-size:1.15rem;color:#86BC25;
                             letter-spacing:1px;'>TALENTCOMPASS</span>
                <span style='font-size:0.72rem;color:#888888;
                             letter-spacing:0.3px;'>AI Workforce Intelligence</span>
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    api_key = st.text_input(
        "Claude API Key",
        type="password",
        placeholder="sk-ant-...",
        help="Your key is stored only in this browser session and sent directly to Anthropic.",
        value=st.session_state.get("api_key", ""),
    )
    if api_key:
        st.session_state["api_key"] = api_key
        st.success("✓ API key loaded")
    else:
        st.warning("Enter your Claude API key to begin.")

    st.divider()

    st.markdown(
        "<p style='color:#86BC25;font-weight:800;letter-spacing:1.5px;"
        "font-size:0.78rem;margin-bottom:6px;text-transform:uppercase;'>Navigate</p>",
        unsafe_allow_html=True,
    )
    page = st.radio(
        "page_nav",
        options=[
            "ROLE ANALYSIS",
            "CLIENT RESEARCH",
            "ORGANIZATION VIEW",
            "REPORTS & EXPORT",
        ],
        label_visibility="collapsed",
    )
    st.divider()

    # Session stats
    n_roles = len(st.session_state.get("org_roles", []))
    n_companies = len(st.session_state.get("org_companies", []))
    has_company = "last_company_result" in st.session_state
    st.markdown(f"**{n_roles}** role analyses  ·  **{n_companies}** client research records")
    if has_company:
        name = (
            st.session_state["last_company_result"]
            .get("company_profile", {})
            .get("name", "")
        )
        st.markdown(f"Last company: **{name}**")

    st.divider()
    st.caption("Built for Deloitte Luxembourg · Powered by Claude")
    st.caption("UI: presets + client-research sync (reloads code each run)")

# ── Page routing ───────────────────────────────────────────────────────────────
if page == "ROLE ANALYSIS":
    _reload_modules(
        "services.company_context",
        "services.prompts",
        "services.claude_client",
        "pages.role_analysis",
    )
    role_analysis.render()
elif page == "CLIENT RESEARCH":
    _reload_modules("services.company_context", "services.claude_client", "pages.client_research")
    client_research.render()
elif page == "ORGANIZATION VIEW":
    _reload_modules("pages.org_overview")
    org_overview.render()
elif page == "REPORTS & EXPORT":
    _reload_modules("services.pdf_export", "pages.reports_export")
    reports_export.render()