from pathlib import Path
import base64
import hashlib
import importlib
import os
import sys
import streamlit as st


def _reload_modules(*names: str) -> None:
    """Reload submodules so local edits apply without restarting Streamlit.

    Development-only: Streamlit caches imported submodules across reruns, so this
    forces a reload to pick up code edits. It is a no-op unless TC_DEV=1 is set,
    since reloading on every rerun adds overhead and risks stale-module state in
    production. Set TC_DEV=1 in your shell while iterating on the code.
    """
    if os.environ.get("TC_DEV") != "1":
        return
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
from services import session_io

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

    # ── Model selection ──────────────────────────────────────────────────────
    st.markdown(
        "<p style='color:#86BC25;font-weight:800;letter-spacing:1.5px;"
        "font-size:0.78rem;margin-bottom:6px;text-transform:uppercase;'>Model</p>",
        unsafe_allow_html=True,
    )
    MODEL_OPTIONS = {
        "claude-haiku-4-5 (fast)": "claude-haiku-4-5",
        "claude-opus-4-5 (quality)": "claude-opus-4-5",
    }
    model_label = st.selectbox(
        "model_select",
        options=list(MODEL_OPTIONS.keys()),
        label_visibility="collapsed",
    )
    st.session_state["model"] = MODEL_OPTIONS[model_label]
    st.caption("Haiku: fast, low cost · Opus: higher quality, ~10-15x the cost.")

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
    st.markdown(
        f"**{n_roles}** role analyses  ·  **{n_companies}** client research records"
    )
    if has_company:
        name = (
            st.session_state["last_company_result"]
            .get("company_profile", {})
            .get("name", "")
        )
        st.markdown(f"Last company: **{name}**")

    st.divider()

    # ── Session save / load ───────────────────────────────────────────────────
    st.markdown(
        "<p style='color:#86BC25;font-weight:800;letter-spacing:1.5px;"
        "font-size:0.78rem;margin-bottom:6px;text-transform:uppercase;'>Session</p>",
        unsafe_allow_html=True,
    )
    st.download_button(
        "Export session (JSON)",
        data=session_io.export_session(st.session_state),
        file_name="talentcompass_session.json",
        mime="application/json",
        use_container_width=True,
        help="Saves your role analyses and client research. Your API key is never included.",
    )
    uploaded = st.file_uploader(
        "Import session (JSON)", type=["json"], key="session_import"
    )
    if uploaded is not None:
        digest = hashlib.sha256(uploaded.getvalue()).hexdigest()
        # Guard against re-importing the same file on every Streamlit rerun.
        if st.session_state.get("_imported_digest") != digest:
            try:
                restored = session_io.import_session(uploaded.getvalue())
                st.session_state["org_roles"] = restored["org_roles"]
                st.session_state["org_companies"] = restored["org_companies"]
                st.session_state[session_io.CUSTOM_KEY] = restored.get(
                    session_io.CUSTOM_KEY, []
                )
                st.session_state["_imported_digest"] = digest
                st.success(
                    f"Imported {len(restored['org_roles'])} role(s), "
                    f"{len(restored['org_companies'])} client(s)."
                )
                st.rerun()
            except session_io.SessionImportError as e:
                st.error(f"Import failed: {e}")

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
    _reload_modules(
        "services.company_context", "services.claude_client", "pages.client_research"
    )
    client_research.render()
elif page == "ORGANIZATION VIEW":
    _reload_modules("pages.org_overview")
    org_overview.render()
elif page == "REPORTS & EXPORT":
    _reload_modules("services.pdf_export", "pages.reports_export")
    reports_export.render()
