import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from services.claude_client import (
    analyze_role,
    analyze_hr_advisory,
    ClaudeClientError,
)
from services.company_context import SIZE_OPTIONS
from services import agent_library
from services.workforce import compute_workforce_impact

_ERROR_MESSAGES = {
    "auth": "Invalid API key. Check the key in the sidebar and try again.",
    "rate_limit": "The model is rate-limited right now. Wait a moment and retry.",
    "bad_json": "The model returned an unreadable response. Please retry the analysis.",
    "api": "The API call failed. Check your connection and try again.",
}

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

# Deloitte data-viz palette: green is the accent, blue the second category,
# cool grey the neutral. No amber/teal/magenta.
SCORE_COLORS = {
    "Fully Automatable": "#046A38",  # Deloitte Green 7
    "AI-Augmented": "#0076A8",       # Deloitte Blue
    "Human-Only": "#75787B",         # Deloitte Cool Gray 9
}

# ── Shared Plotly layout defaults ─────────────────────────────────────────────
_PLOTLY_BASE = dict(
    template="plotly_white",
    paper_bgcolor="white",
    plot_bgcolor="white",
    font=dict(color="#1A1A1A", family="Open Sans, sans-serif", size=12),
)


def _apply_role_preset() -> None:
    sel = st.session_state.get("role_preset_select", "- none -")
    if sel == "- none -":
        return
    p = PRESETS[sel]
    st.session_state["rj_title"] = p["title"]
    st.session_state["rj_dept"] = p["dept"]
    st.session_state["rj_desc"] = p["desc"]


def _attach_workforce(role: dict) -> None:
    """Compute and attach deterministic workforce impact from the current inputs.
    No-op (and clears any stale value) when headcount is 0."""
    headcount = st.session_state.get("wf_headcount", 0) or 0
    if not headcount:
        role.pop("workforce", None)
        return
    role["workforce"] = compute_workforce_impact(
        role,
        headcount=headcount,
        loaded_cost=st.session_state.get("wf_cost", 0),
        reskill_cost_per_fte=st.session_state.get("wf_reskill", 0),
        severance_months=st.session_state.get("wf_sev", 3.0),
    )


def _eur(v) -> str:
    try:
        return f"€{float(v):,.0f}"
    except (TypeError, ValueError):
        return "€0"


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
    st.caption(
        "Every assessment is generated live from the exact role description you provide."
    )

    _init_role_inputs()

    col1, col2 = st.columns([1, 1])
    with col1:
        st.text_input(
            "Client Name",
            placeholder="e.g. Amundi Luxembourg, Alter Domus, BGL BNP Paribas",
            help="Optional but recommended - adds client context to the analysis.",
            key="rj_client",
        )
        st.text_input(
            "Job Title *", placeholder="e.g. Senior Financial Analyst", key="rj_title"
        )
        st.text_input(
            "Department",
            placeholder="e.g. Finance, Compliance, Operations",
            key="rj_dept",
        )

    with col2:
        st.selectbox("Company Size", list(SIZE_OPTIONS), key="role_company_size")
        rcn = st.session_state.get("researched_company_name")
        rcb = st.session_state.get("researched_company_size_bucket")
        if rcn and rcb:
            st.caption(
                f"From latest **Client Research** on *{rcn}*: suggested size **{rcb}**. "
                "Change above if needed."
            )
        st.selectbox(
            "Load a preset role",
            ["- none -"] + list(PRESETS.keys()),
            key="role_preset_select",
            on_change=_apply_role_preset,
            help="Fills Job Title, Department, and Job Description immediately.",
        )

    st.text_area(
        "Job Description *",
        height=220,
        placeholder=(
            "Paste the real job description or list the main responsibilities. "
            "The analysis is based on this text - the more specific, "
            "the more accurate and defensible the output."
        ),
        key="rj_desc",
    )

    with st.expander(
        "Workforce inputs — for FTE, payroll & severance impact (optional)"
    ):
        st.caption(
            "These drive the deterministic financial figures (real arithmetic on your "
            "numbers, not AI estimates). Leave headcount at 0 to skip the impact section."
        )
        wcol1, wcol2 = st.columns(2)
        wcol1.number_input(
            "Headcount in this role", min_value=0, step=1, key="wf_headcount"
        )
        wcol2.number_input(
            "Fully-loaded annual cost / FTE (EUR)",
            min_value=0,
            step=5000,
            key="wf_cost",
            help="Salary + employer charges + overhead.",
        )
        wcol3, wcol4 = st.columns(2)
        wcol3.number_input(
            "Reskilling / transition cost per freed FTE (EUR)",
            min_value=0,
            step=1000,
            key="wf_reskill",
        )
        wcol4.number_input(
            "Severance basis (months of cost)",
            min_value=0.0,
            step=1.0,
            value=3.0,
            key="wf_sev",
        )

    with st.form("role_form"):
        submitted = st.form_submit_button(
            "Analyze Role", type="primary", use_container_width=True
        )

    if submitted:
        api_key = st.session_state.get("api_key", "")
        if not api_key:
            st.error("Enter your API key in the sidebar first.")
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
            st.error("Job Title and Job Description are required.")
            return

        client_name = (st.session_state.get("rj_client") or "").strip()
        company_size = st.session_state.get("role_company_size", "SME")
        if company_size not in SIZE_OPTIONS:
            company_size = "SME"

        with st.spinner("Generating a live role assessment..."):
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
                _attach_workforce(result)
                st.session_state["last_role_result"] = result
                if "org_roles" not in st.session_state:
                    st.session_state["org_roles"] = []
                st.session_state["org_roles"].append(result)
            except ClaudeClientError as e:
                st.error(_ERROR_MESSAGES.get(e.kind, _ERROR_MESSAGES["api"]))
                return

    r = st.session_state.get("last_role_result")
    if not r:
        return

    st.divider()

    # ── Header metrics ────────────────────────────────────────────────────────
    col_h1, col_h2, col_h3, col_h4 = st.columns(4)
    with col_h1:
        st.markdown(f"### {r.get('_title', '')}")
        st.caption(f"{r.get('_dept', '')}  -  {r.get('_client', '')}")
    with col_h2:
        st.metric("Transformation Priority", r.get("transformation_priority", "Medium"))
    with col_h3:
        st.metric("Automation Score", f"{r.get('automation_score', 0)}%")
    with col_h4:
        st.metric("Weekly Hours Saved", f"{r.get('weekly_hours_saved', 0)} hrs")

    # ── Executive summary ─────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**Executive Summary**")
        st.write(r.get("summary", ""))
        st.caption(
            "Live assessment  -  Generated from your exact role description"
        )

    # ── Stat metrics ──────────────────────────────────────────────────────────
    stats = r.get("stats", {})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fully Automatable", f"{stats.get('fully_automatable_pct', 0)}%")
    c2.metric("AI-Augmented", f"{stats.get('ai_augmented_pct', 0)}%")
    c3.metric("Human-Only", f"{stats.get('human_only_pct', 0)}%")
    c4.metric("AI Agents Identified", len(r.get("ai_agents", [])))

    # ── Workforce & financial impact (deterministic) ──────────────────────────
    # Recompute live from current inputs so tweaks update without re-calling Claude.
    _attach_workforce(r)
    wf = r.get("workforce")
    if wf:
        st.markdown("### Workforce & Financial Impact")
        st.caption(
            "Computed from your headcount and loaded cost — real arithmetic, not an AI estimate."
        )
        w1, w2, w3, w4 = st.columns(4)
        w1.metric("FTE freed", f"{wf['fte_freed']:.2f}")
        w2.metric("Annual payroll savings", _eur(wf["annual_payroll_savings"]))
        w3.metric("Net annual savings", _eur(wf["net_annual_savings"]))
        w4.metric("Severance exposure", _eur(wf["severance_exposure"]))
        st.caption(
            f"Headcount {wf['headcount']}  ·  {wf['total_weekly_hours_freed']:.0f} h/week freed  ·  "
            f"displaced (fully-automatable) {wf['displaced_fte']:.2f} FTE  ·  "
            f"transition cost {_eur(wf['transition_cost'])} "
            f"(reskill {_eur(wf['reskill_cost_per_fte'])}/FTE)  ·  "
            f"severance basis {wf['severance_months']:.0f} months"
        )
    else:
        st.caption(
            "Add a headcount in **Workforce inputs** above to see FTE, payroll and severance impact."
        )

    # ── HR Management & Advisory (LLM, opt-in) ────────────────────────────────
    st.markdown("### HR Management & Advisory")
    adv = r.get("hr_advisory")
    if not adv:
        st.caption(
            "Qualitative people guidance: redeployment, reskilling, change management, "
            "retention and workforce planning. Generated on demand (one extra API call)."
        )
        if st.button("Generate HR advisory", key="gen_hr_advisory"):
            api_key = st.session_state.get("api_key", "")
            if not api_key:
                st.error("Enter your API key in the sidebar first.")
            else:
                with st.spinner("Generating HR advisory..."):
                    try:
                        r["hr_advisory"] = analyze_hr_advisory(
                            api_key, r, r.get("workforce")
                        )
                        st.rerun()
                    except ClaudeClientError as e:
                        st.error(_ERROR_MESSAGES.get(e.kind, _ERROR_MESSAGES["api"]))
    else:
        if adv.get("summary"):
            with st.container(border=True):
                st.write(adv["summary"])
        ac1, ac2 = st.columns(2)
        with ac1:
            if adv.get("redeployment_options"):
                st.markdown("**Redeployment options**")
                for o in adv["redeployment_options"]:
                    st.markdown(
                        f"- **{o.get('option', '')}** ({o.get('effort', '')}): {o.get('description', '')}"
                    )
            if adv.get("reskilling_focus"):
                st.markdown("**Reskilling focus**")
                for s in adv["reskilling_focus"]:
                    st.markdown(f"- {s}")
            if adv.get("workforce_planning"):
                st.markdown("**Workforce planning**")
                for s in adv["workforce_planning"]:
                    st.markdown(f"- {s}")
        with ac2:
            if adv.get("retention_priorities"):
                st.markdown("**Retention priorities**")
                for p in adv["retention_priorities"]:
                    st.markdown(
                        f"- **{p.get('group', '')}** — {p.get('reason', '')}  →  {p.get('action', '')}"
                    )
            if adv.get("change_management"):
                st.markdown("**Change management**")
                for step in adv["change_management"]:
                    st.markdown(f"- **{step.get('phase', '')}**")
                    for a in step.get("actions", []):
                        st.markdown(f"    - {a}")
            if adv.get("hr_risks"):
                st.markdown("**HR risks**")
                for hr in adv["hr_risks"]:
                    st.markdown(
                        f"- {hr.get('risk', '')} → _{hr.get('mitigation', '')}_"
                    )
        if st.button("Regenerate HR advisory", key="regen_hr_advisory"):
            r.pop("hr_advisory", None)
            st.rerun()

    # ── Gauge + Task bar chart ────────────────────────────────────────────────
    tasks = r.get("tasks", [])
    col_gauge, col_tasks = st.columns([1, 2])

    with col_gauge:
        score = r.get("automation_score", 0)
        gauge_color = (
            "#046A38" if score >= 75 else "#86BC25" if score >= 55 else "#75787B"
        )
        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=score,
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#7a7974"},
                    "bar": {"color": gauge_color},
                    "bgcolor": "#F7F7F7",
                    "steps": [
                        {"range": [0, 45], "color": "#F2F8E8"},
                        {"range": [45, 70], "color": "#DDEFE8"},
                        {"range": [70, 100], "color": "#C5E0A0"},
                    ],
                },
                title={
                    "text": "Automation Score",
                    "font": {"color": "#1A1A1A", "size": 14},
                },
                number={"suffix": "%", "font": {"size": 36, "color": "#1A1A1A"}},
            )
        )
        fig_gauge.update_layout(
            height=280,
            margin=dict(t=40, b=0, l=20, r=20),
            **_PLOTLY_BASE,
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_tasks:
        st.markdown("**Task Breakdown**")
        if tasks:
            df_tasks = pd.DataFrame(tasks)
            fig_tasks = px.bar(
                df_tasks,
                x="score",
                y="name",
                orientation="h",
                color="type",
                color_discrete_map=SCORE_COLORS,
                text="score",
                labels={"score": "Automation Score (%)", "name": "", "type": "Type"},
                height=max(250, len(tasks) * 42),
            )
            fig_tasks.update_traces(texttemplate="%{text}%", textposition="outside")
            fig_tasks.update_layout(
                margin=dict(l=0, r=30, t=10, b=0),
                legend=dict(orientation="h", y=-0.15, font=dict(color="#1A1A1A")),
                xaxis=dict(color="#1A1A1A", gridcolor="#EEEEEE"),
                yaxis=dict(color="#1A1A1A", tickfont=dict(color="#1A1A1A")),
                **_PLOTLY_BASE,
            )
            st.plotly_chart(fig_tasks, use_container_width=True)

    # ── Task-by-task rationale ────────────────────────────────────────────────
    with st.expander("Task-by-task rationale"):
        for t in tasks:
            color = SCORE_COLORS.get(t.get("type", ""), "#555555")
            st.markdown(
                f"<span style='color:#1A1A1A;font-weight:600'>{t.get('name', '')}</span>"
                f" &mdash; "
                f"<span style='color:{color};font-weight:600'>{t.get('type', '')}</span>"
                f" <span style='color:#555555'>({t.get('score', 0)}%)</span>"
                f"<br><span style='color:#1A1A1A'>{t.get('rationale', '')}</span>",
                unsafe_allow_html=True,
            )
            st.divider()

    # ── AI Agents ─────────────────────────────────────────────────────────────
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
                st.markdown(
                    f"**Setup complexity:** `{agent.get('setup_complexity', '')}`"
                )

    # ── Agent library (apply / save reusable templates) ───────────────────────
    with st.expander("Agent library — apply or save reusable agent templates"):
        templates = agent_library.get_templates(st.session_state)
        existing_names = {(a.get("name") or "").strip().lower() for a in agents}

        st.markdown("**Add agents from the library**")
        addable = [
            t
            for t in templates
            if (t.get("name") or "").strip().lower() not in existing_names
        ]
        if addable:
            labels = {
                f"{t.get('icon', '')} {t['name']}  ·  {t.get('category', '')}".strip(): t
                for t in addable
            }
            picked = st.multiselect(
                "Templates to add to this role",
                options=list(labels.keys()),
                key="agentlib_pick",
            )
            if st.button(
                "Add selected to this role", key="agentlib_add", disabled=not picked
            ):
                for lbl in picked:
                    agent_library.apply_to_role(r, labels[lbl])
                st.success(f"Added {len(picked)} agent(s) to this role.")
                st.rerun()
        else:
            st.caption("Every library template is already on this role.")

        st.divider()
        st.markdown("**Save one of this role's agents to the library**")
        if agents:
            agent_names = [a.get("name", "") for a in agents]
            sel = st.selectbox(
                "Agent to save as a template", agent_names, key="agentlib_save_sel"
            )
            cat = st.text_input(
                "Category",
                placeholder="e.g. Fund Administration",
                key="agentlib_save_cat",
            )
            if st.button("Save as template", key="agentlib_save_btn"):
                src = next((a for a in agents if a.get("name") == sel), None)
                if src:
                    tmpl = dict(src)
                    if cat.strip():
                        tmpl["category"] = cat.strip()
                    agent_library.save_template(st.session_state, tmpl)
                    st.success(f"Saved “{sel}” to the library.")
                    st.rerun()
        else:
            st.caption("No agents on this role yet.")

        n_custom = len(st.session_state.get(agent_library.CUSTOM_KEY) or [])
        if n_custom:
            st.caption(f"{n_custom} custom template(s) saved this session.")

    # ── Reskilling ────────────────────────────────────────────────────────────
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

    # ── Transformation Roadmap ────────────────────────────────────────────────
    st.markdown("### Transformation Roadmap")
    roadmap = r.get("roadmap", [])
    phase_colors = ["#046A38", "#86BC25", "#0076A8"]
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

    # ── Risk & Change Management ──────────────────────────────────────────────
    st.markdown("### Risk & Change Management")
    risks = r.get("risks", [])
    risk_colors = {"change": "#75787B", "data": "#0076A8", "compliance": "#046A38"}
    risk_cols = st.columns(len(risks)) if risks else []
    for i, risk in enumerate(risks):
        with risk_cols[i] if risk_cols else st.container():
            with st.container(border=True):
                c = risk_colors.get(risk.get("color_key", ""), "#046A38")
                st.markdown(
                    f"<div style='color:{c};font-weight:700'>{risk.get('title', '')}</div>",
                    unsafe_allow_html=True,
                )
                for item in risk.get("items", []):
                    st.markdown(f"- {item}")
