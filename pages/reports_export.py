"""Session history, tabbed review, and Deloitte-branded PDF downloads."""
from __future__ import annotations

import copy
import re

import streamlit as st

try:
    from services.pdf_export import (
        build_combined_pdf,
        build_companies_pdf,
        build_roles_pdf,
        build_single_company_pdf,
        build_single_role_pdf,
    )
    _PDF_OK = True
    _PDF_ERROR = ""
except Exception as _e:
    _PDF_OK = False
    _PDF_ERROR = str(_e)


def _slug(s: str, fallback: str) -> str:
    s = (s or "").strip() or fallback
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[-\s]+", "_", s).strip("_")
    return (s[:60] or fallback).lower()


def _ensure_company_history() -> None:
    if "org_companies" not in st.session_state:
        st.session_state["org_companies"] = []
    if not st.session_state["org_companies"] and st.session_state.get("last_company_result"):
        st.session_state["org_companies"] = [
            copy.deepcopy(st.session_state["last_company_result"])
        ]


def _safe_pdf(fn, *args) -> bytes | None:
    """Call a PDF builder and return bytes, or show an error and return None."""
    try:
        return fn(*args)
    except Exception as e:
        st.error(f"PDF generation failed: {e}")
        return None


def render() -> None:
    st.markdown("## Reports & export")
    st.caption(
        "Review every role analysis and client research from this browser session, "
        "then download Deloitte-branded PDFs."
    )

    # Surface import errors immediately
    if not _PDF_OK:
        st.error(f"PDF engine failed to load: {_PDF_ERROR}")
        st.info("Check that `assets/fonts/DejaVuSans.ttf` and `DejaVuSans-Bold.ttf` exist.")
        return

    try:
        _ensure_company_history()
    except Exception as e:
        st.error(f"Session state error: {e}")
        return

    roles: list = list(st.session_state.get("org_roles") or [])
    companies: list = list(st.session_state.get("org_companies") or [])

    # ── Tabs ──────────────────────────────────────────────────────────────────
    try:
        tab_roles, tab_clients, tab_bundle = st.tabs(
            ["Role analyses", "Client research", "Combined PDF"]
        )
    except Exception as e:
        st.error(f"Failed to render tabs: {e}")
        return

    # ── Tab 1: Role analyses ──────────────────────────────────────────────────
    with tab_roles:
        if not roles:
            st.info("No role analyses yet. Run **Role Analysis** first.", icon="ℹ️")
        else:
            st.markdown(f"**{len(roles)}** analysis record(s) in this session.")
            for i, r in enumerate(roles, start=1):
                title = r.get("_title") or "Role"
                client = r.get("_client") or ""
                with st.expander(f"{i}. {title}  \u2014  {client}"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Automation", f"{r.get('automation_score', 0)}%")
                    c2.metric("Hours / week", r.get("weekly_hours_saved", 0))
                    c3.metric("Priority", r.get("transformation_priority", ""))
                    st.write(r.get("summary", ""))

                    fname = f"TalentCompass_Role_{i}_{_slug(title, 'role')}.pdf"
                    pdf_bytes = _safe_pdf(build_single_role_pdf, r)
                    if pdf_bytes:
                        st.download_button(
                            label="Download this analysis (PDF)",
                            data=pdf_bytes,
                            file_name=fname,
                            mime="application/pdf",
                            key=f"dl_role_{i}",
                            use_container_width=True,
                        )

            st.divider()
            all_roles_pdf = _safe_pdf(build_roles_pdf, roles)
            if all_roles_pdf:
                st.download_button(
                    label=f"Download all {len(roles)} role analyses (single PDF)",
                    data=all_roles_pdf,
                    file_name="TalentCompass_All_Role_Analyses.pdf",
                    mime="application/pdf",
                    key="dl_roles_all",
                    type="primary",
                    use_container_width=True,
                )

    # ── Tab 2: Client research ─────────────────────────────────────────────────
    with tab_clients:
        if not companies:
            st.info("No client research yet. Run **Client Research** first.", icon="ℹ️")
        else:
            st.markdown(f"**{len(companies)}** research record(s) in this session.")
            for i, r in enumerate(companies, start=1):
                prof = r.get("company_profile") or {}
                name = prof.get("name") or f"Company {i}"
                with st.expander(f"{i}. {name}"):
                    c1, c2 = st.columns(2)
                    c1.metric("AI potential", f"{r.get('ai_potential_score', 0)} / 100")
                    c2.markdown(f"**{r.get('ai_potential_label', '')}**")
                    st.caption(
                        f"{prof.get('inferred_industry', '')}  \u00b7  {prof.get('inferred_size', '')}"
                    )
                    st.write(r.get("ai_potential_summary", ""))

                    fname = f"TalentCompass_Client_{i}_{_slug(name, 'client')}.pdf"
                    pdf_bytes = _safe_pdf(build_single_company_pdf, r)
                    if pdf_bytes:
                        st.download_button(
                            label="Download this research (PDF)",
                            data=pdf_bytes,
                            file_name=fname,
                            mime="application/pdf",
                            key=f"dl_co_{i}",
                            use_container_width=True,
                        )

            st.divider()
            all_co_pdf = _safe_pdf(build_companies_pdf, companies)
            if all_co_pdf:
                st.download_button(
                    label=f"Download all {len(companies)} client studies (single PDF)",
                    data=all_co_pdf,
                    file_name="TalentCompass_All_Client_Research.pdf",
                    mime="application/pdf",
                    key="dl_co_all",
                    type="primary",
                    use_container_width=True,
                )

    # ── Tab 3: Combined PDF ────────────────────────────────────────────────────
    with tab_bundle:
        if not roles and not companies:
            st.info(
                "Complete at least one role analysis or client research to build a combined PDF.",
                icon="ℹ️",
            )
        else:
            st.markdown(
                f"This export includes **{len(roles)}** role analysis(es) and "
                f"**{len(companies)}** client research record(s) in one document."
            )
            combined_pdf = _safe_pdf(build_combined_pdf, roles, companies)
            if combined_pdf:
                st.download_button(
                    label="Download full session report (PDF)",
                    data=combined_pdf,
                    file_name="TalentCompass_Session_Report.pdf",
                    mime="application/pdf",
                    key="dl_combined",
                    type="primary",
                    use_container_width=True,
                )