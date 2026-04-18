import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from services.claude_client import analyze_role
from services.company_context import SIZE_OPTIONS

PRESETS = {
    "Financial Analyst": {
        "title": "Senior Financial Analyst",
        "dept": "Finance",
        "desc": (
            "Responsible for monthly and quarterly financial reporting, reconciliations, "
            "dashboard production, variance analysis, and budget tracking. Manages invoice "
            "review, stakeholder queries, financial data quality control, and ensures "
            "audit-readiness of records. Prepares board-level reports, coordinates cross-"
            "departmental financial reviews, and monitors regulatory compliance."
        ),
    },
    "Compliance Officer": {
        "title": "Compliance Officer",
        "dept": "Compliance",
        "desc": (
            "Monitors regulatory changes and updates internal compliance policies. Prepares "
            "regulatory submissions (AIFMD, CSSF, EBA). Reviews KYC and AML documentation. "
            "Supports internal and external audits, tracks remediation actions, maintains "
            "risk registers, and coordinates with legal counsel and regulators."
        ),
    },
    "HR Manager": {
        "title": "HR Manager",
        "dept": "Human Resources",
        "desc": (
            "Manages end-to-end recruitment, employee onboarding, HR administration, payroll "
            "input, leave and absence tracking, policy support, employee communications, "
            "performance review coordination, training programmes, and HR dashboard reporting."
        ),
    },
    "Data Analyst": {
        "title": "Data Analyst",
        "dept": "Business Intelligence",
        "desc": (
            "Collects, transforms, validates, and analyses data from multiple internal and "
            "external sources. Builds and maintains BI dashboards, handles ad hoc data "
            "requests, writes SQL queries, documents data pipelines, and presents insights "
            "to business stakeholders."
        ),
    },
    "Fund Accountant": {
        "title": "Fund Accountant",
        "dept": "Fund Administration",
        "desc": (
            "Performs daily NAV calculations and fund accounting for investment funds. "
            "Reconciles positions, cash, and portfolio valuations. Processes subscriptions, "
            "redemptions, and corporate actions. Prepares investor reports and regulatory "
            "filings. Coordinates with custodians, transfer agents, and portfolio managers."
        ),
    },
}

SCORE_COLORS = {
    "Fully Automatable": "#01696f",
    "AI-Augmented": "#d19900",
    "Human-Only": "#8a8a8a",
}


def _apply_role_preset() -> None:
    sel = st.session_state.get("role_preset_select", "- none -")
    if sel == "- none -":
        return
    p = PRESETS[sel]
    st.session_state["rj_title"] = p["title"]
    st.session_state["rj_dept"] = p["dept"]
    st.session_state["rj_desc"] = p["desc"]


def _init_role_inputs() -> None:
    for key, default in (
        ("rj_client", ""),
        ("rj_title", ""),
        ("rj_dept", ""),
        ("rj_desc", ""),
    ):
        if key not in st.session_state:
            st.session_state[key] = default

    if st.session_state.pop("_sync_role_company_size", False):
        bucket = st.session_state.get("researched_company_size_bucket", "SME")
        if bucket in SIZE_OPTIONS:
            st.session_state["role_company_size"] = bucket
        rname = (st.session_state.get("researched_company_name") or "").strip()
        if rname:
            st.session_state["rj_client"] = rname

    if "role_company_size" not in st.session_state:
        init = st.session_state.get("researched_company_size_bucket", "SME")
        st.session_state["role_company_size"] = init if init in SIZE_OPTIONS else "SME"


def render():
    st.markdown("## Role Automation Analysis")
    st.caption("Every assessment is generated live by Claude based on the exact role description you provide.")

    _init_role_inputs()

    st.selectbox(
        "Load a preset role",
        ["- none -"] + list(PRESETS.keys()),
        key="role_preset_select",
        on_change=_apply_role_preset,
        help="Fills Job Title, Department, and Job Description immediately. You can edit before analyzing.",
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        st.text_input(
            "Client Name",
            placeholder="e.g. Amundi Luxembourg, Alter Domus, BGL BNP Paribas",
            help="Optional but recommended - adds client context to the analysis.",
            key="rj_client",
        )
        st.text_input("Job Title *", placeholder="e.g. Senior Financial Analyst", key="rj_title")
        st.text_input("Department", placeholder="e.g. Finance, Compliance, Operations", key="rj_dept")

    with col2:
        st.selectbox("Company Size", list(SIZE_OPTIONS), key="role_company_size")
        rcn = st.session_state.get("researched_company_name")
        rcb = st.session_state.get("researched_company_size_bucket")
        if rcn and rcb:
            st.caption(
                f"From latest **Client Research** on *{rcn}*: suggested size **{rcb}**. "
                "Change above if needed."
            )

    st.text_area(
        "Job Description *",
        height=220,
        placeholder=(
            "Paste the real job description or list the main responsibilities. "
            "Claude will base its analysis on this text - the more specific, "
            "the more accurate and defensible the output."
        ),
        key="rj_desc",
    )

    with st.form("role_form"):
        submitted = st.form_submit_button("Analyze Role", type="primary", use_container_width=True)

    if submitted:
        api_key = st.session_state.get("api_key", "")
        if not api_key:
            st.error("Enter your Claude API key in the sidebar first.")
            return

        job_title = (st.session_state.get("rj_title") or "").strip()
        job_desc = (st.session_state.get("rj_desc") or "").strip()
        preset_sel = st.session_state.get("role_preset_select", "- none -")

        if preset_sel != "- none -":
            p = PRESETS[preset_sel]
            if not job_title:
                job_title = p["title"]
            if not job_desc:
                job_desc = p["desc"]

        department = (st.session_state.get("rj_dept") or "").strip()
        if preset_sel != "- none -" and not department:
            department = PRESETS[preset_sel]["dept"]

        if not job_title or not job_desc:
            st.error("Job Title and Job Description are required (load a preset or enter them manually).")
            return

        client_name = (st.session_state.get("rj_client") or "").strip()
        company_size = st.session_state.get("role_company_size", "SME")
        if company_size not in SIZE_OPTIONS:
            company_size = "SME"

        with st.spinner("Calling Claude for a live role assessment..."):
            try:
                result = analyze_role(
                    api_key=api_key,
                    job_title=job_title,
                    department=department,
                    company_size=company_size,
                    job_description=job_desc,
                    client_name=client_name,
                )
                result["_title"] = job_title
                result["_dept"] = department
                result["_client"] = client_name or "Not specified"
                st.session_state["last_role_result"] = result
                if "org_roles" not in st.session_state:
                    st.session_state["org_roles"] = []
                st.session_state["org_roles"].append(result)
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                return

    r = st.session_state.get("last_role_result")
    if not r:
        return

    st.divider()

    col_h1, col_h2, col_h3, col_h4 = st.columns(4)
    with col_h1:
        st.markdown(f"### {r.get('_title', '')}")
        st.caption(f"{r.get('_dept', '')}  -  {r.get('_client', '')}")
    with col_h2:
        priority = r.get("transformation_priority", "Medium")
        st.metric("Transformation Priority", priority)
    with col_h3:
        st.metric("Automation Score", f"{r.get('automation_score', 0)}%")
    with col_h4:
        st.metric("Weekly Hours Saved", f"{r.get('weekly_hours_saved', 0)} hrs")

    with st.container(border=True):
        st.markdown("**Executive Summary**")
        st.write(r.get("summary", ""))
        st.caption("Live Claude assessment  -  Generated from your exact role description")

    stats = r.get("stats", {})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fully Automatable", f"{stats.get('fully_automatable_pct', 0)}%")
    c2.metric("AI-Augmented", f"{stats.get('ai_augmented_pct', 0)}%")
    c3.metric("Human-Only", f"{stats.get('human_only_pct', 0)}%")
    c4.metric("AI Agents Identified", len(r.get("ai_agents", [])))

    tasks = r.get("tasks", [])
    col_gauge, col_tasks = st.columns([1, 2])

    with col_gauge:
        score = r.get("automation_score", 0)
        gauge_color = "#a12c7b" if score >= 75 else "#da7101" if score >= 55 else "#01696f"
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#7a7974"},
                "bar": {"color": gauge_color},
                "bgcolor": "#f3f0ec",
                "steps": [
                    {"range": [0, 45], "color": "#e6f4f4"},
                    {"range": [45, 70], "color": "#fef6e0"},
                    {"range": [70, 100], "color": "#f5dded"},
                ],
            },
            title={"text": "Automation Score"},
            number={"suffix": "%", "font": {"size": 36}},
        ))
        fig_gauge.update_layout(height=280, margin=dict(t=40, b=0, l=20, r=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_tasks:
        st.markdown("**Task Breakdown**")
        if tasks:
            df_tasks = pd.DataFrame(tasks)
            fig_tasks = px.bar(
                df_tasks, x="score", y="name", orientation="h",
                color="type",
                color_discrete_map=SCORE_COLORS,
                text="score",
                labels={"score": "Automation Score (%)", "name": "", "type": "Type"},
                height=max(250, len(tasks) * 42),
            )
            fig_tasks.update_traces(texttemplate="%{text}%", textposition="outside")
            fig_tasks.update_layout(margin=dict(l=0, r=30, t=10, b=0), legend=dict(orientation="h", y=-0.15))
            st.plotly_chart(fig_tasks, use_container_width=True)

    with st.expander("Task-by-task rationale"):
        for t in tasks:
            color = SCORE_COLORS.get(t.get("type", ""), "#999")
            st.markdown(
                f"**{t.get('name', '')}** - "
                f"<span style='color:{color};font-weight:600'>{t.get('type', '')}</span> "
                f"({t.get('score', 0)}%)  -  {t.get('rationale', '')}",
                unsafe_allow_html=True,
            )

    st.markdown("### Recommended AI Agents")
    agents = r.get("ai_agents", [])
    agent_cols = st.columns(min(len(agents), 3)) if agents else []
    for i, agent in enumerate(agents):
        with agent_cols[i % 3] if agent_cols else st.container():
            with st.container(border=True):
                st.markdown(f"#### {agent.get('name', '')}")
                st.caption(agent.get("description", ""))
                st.markdown(f"**Handles:** {agent.get('handles', '')}")
                st.markdown(f"**Saving:** `{agent.get('time_saving', '')}`")
                st.markdown(f"**Setup complexity:** `{agent.get('setup_complexity', '')}`")

    st.markdown("### Reskilling Priorities")
    reskilling = r.get("reskilling", {})
    col_dev, col_ret = st.columns(2)
    with col_dev:
        with st.container(border=True):
            st.markdown("**Skills to Develop**")
            for skill in reskilling.get("develop", []):
                st.markdown(f"- {skill}")
    with col_ret:
        with st.container(border=True):
            st.markdown("**Skills to Retain**")
            for skill in reskilling.get("retain", []):
                st.markdown(f"- {skill}")

    st.markdown("### Transformation Roadmap")
    roadmap = r.get("roadmap", [])
    phase_colors = ["#01696f", "#d19900", "#006494"]
    road_cols = st.columns(len(roadmap)) if roadmap else []
    for i, phase in enumerate(roadmap):
        with road_cols[i] if road_cols else st.container():
            with st.container(border=True):
                st.markdown(
                    f"<div style='font-weight:800;color:{phase_colors[i % 3]};margin-bottom:4px'>"
                    f"{phase.get('phase', '')}  -  {phase.get('duration', '')}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"**{phase.get('title', '')}**")
                for item in phase.get("items", []):
                    st.markdown(f"- {item}")

    st.markdown("### Risk & Change Management")
    risks = r.get("risks", [])
    risk_colors = {"change": "#964219", "data": "#da7101", "compliance": "#006494"}
    risk_cols = st.columns(len(risks)) if risks else []
    for i, risk in enumerate(risks):
        with risk_cols[i] if risk_cols else st.container():
            with st.container(border=True):
                c = risk_colors.get(risk.get("color_key", ""), "#01696f")
                st.markdown(
                    f"<div style='color:{c};font-weight:700'>{risk.get('title', '')}</div>",
                    unsafe_allow_html=True,
                )
                for item in risk.get("items", []):
                    st.markdown(f"- {item}")
