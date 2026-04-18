import copy

import streamlit as st
import plotly.graph_objects as go
from services.claude_client import research_company
from services.company_context import inferred_size_to_company_size


def render():
    st.markdown("## Client Research")
    st.caption(
        "Enter a client name to generate a Luxembourg-focused AI potential assessment, "
        "competitor intelligence, and strategic recommendations - all generated live from Claude."
    )

    with st.form("company_form"):
        col1, col2 = st.columns(2)
        with col1:
            client_name = st.text_input(
                "Client Name *",
                placeholder="e.g. Clearstream, Pictet, Arendt, State Street, Alter Domus",
            )
        with col2:
            industry = st.text_input(
                "Industry",
                placeholder="e.g. Fund Administration, Banking, Legal - leave blank to auto-infer",
            )
        submitted = st.form_submit_button("Research client", type="primary", use_container_width=True)

    if submitted:
        api_key = st.session_state.get("api_key", "")
        if not api_key:
            st.error("Enter your Claude API key in the sidebar first.")
            return
        if not client_name:
            st.error("Client name is required.")
            return

        with st.spinner(f"Researching {client_name} in the Luxembourg market..."):
            try:
                result = research_company(api_key=api_key, client_name=client_name, industry=industry)
                st.session_state["last_company_result"] = result
                if "org_companies" not in st.session_state:
                    st.session_state["org_companies"] = []
                st.session_state["org_companies"].append(copy.deepcopy(result))
                profile = result.get("company_profile", {})
                st.session_state["researched_company_size_bucket"] = inferred_size_to_company_size(
                    profile.get("inferred_size", "")
                )
                st.session_state["researched_company_name"] = profile.get("name", client_name)
                st.session_state["_sync_role_company_size"] = True
            except Exception as e:
                st.error(f"Research failed: {e}")
                return

    r = st.session_state.get("last_company_result")
    if not r:
        return

    st.divider()

# --- Company header ---
    profile = r.get("company_profile", {})
    col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
    with col_h1:
        st.markdown(f"### {profile.get('name', '')}")
        st.caption(f"{profile.get('inferred_industry', '')}  -  {profile.get('inferred_size', '')}")
    with col_h2:
        st.metric("AI Potential Score", f"{r.get('ai_potential_score', 0)} / 100")
    with col_h3:
        st.markdown(f"**{r.get('ai_potential_label', '')}**")

# --- AI potential gauge ---
    col_gauge, col_profile = st.columns([1, 2])
    score = r.get("ai_potential_score", 0)
    with col_gauge:
        gauge_color = "#a12c7b" if score >= 75 else "#da7101" if score >= 55 else "#01696f"
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": gauge_color},
                "bgcolor": "#f3f0ec",
                "steps": [
                    {"range": [0, 40], "color": "#e6f4f4"},
                    {"range": [40, 70], "color": "#fef6e0"},
                    {"range": [70, 100], "color": "#f5dded"},
                ],
            },
            title={"text": "AI Potential"},
            number={"suffix": "%"},
        ))
        fig.update_layout(height=260, margin=dict(t=40, b=0, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)

    with col_profile:
        with st.container(border=True):
            st.markdown("**Company Profile**")
            st.write(r.get("ai_potential_summary", ""))
            st.markdown(f"**Luxembourg presence:** {profile.get('luxembourg_presence', '')}")
            st.markdown(f"**Regulatory context:** {profile.get('regulatory_context', '')}")

    st.divider()

# --- Industry trends + competitor moves ---
    col_trends, col_comp = st.columns(2)

    with col_trends:
        st.markdown("### Industry AI trends")
        for trend in r.get("industry_ai_trends", []):
            impact = trend.get("impact", "Medium")
            with st.container(border=True):
                st.markdown(f"**{trend.get('trend', '')}**")
                st.caption(f"Impact: {impact}  -  Timeline: {trend.get('timeline', '')}")
                st.write(trend.get("description", ""))

    with col_comp:
        st.markdown("### Competitor moves")
        for comp in r.get("competitor_moves", []):
            threat = comp.get("threat_level", "Medium")
            with st.container(border=True):
                st.markdown(f"**{comp.get('competitor', '')}**")
                st.caption(f"Threat level: {threat}")
                st.write(comp.get("move", ""))

    st.divider()

# --- Key opportunities ---
    st.markdown("### Key AI Opportunities")
    opps = r.get("key_ai_opportunities", [])
    priority_colors = {"Quick Win": "#437a22", "Strategic": "#006494", "Long-term": "#7a39bb"}
    for opp in opps:
        priority = opp.get("priority", "Strategic")
        color = priority_colors.get(priority, "#01696f")
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{opp.get('area', '')}** - {opp.get('opportunity', '')}")
                st.caption(f"Estimated impact: {opp.get('estimated_impact', '')}")
            with c2:
                st.markdown(
                    f"<div style='color:{color};font-weight:700;text-align:right'>{priority}</div>",
                    unsafe_allow_html=True,
                )

    st.divider()

# --- Risks ---
    col_risks, col_strategy = st.columns(2)

    with col_risks:
        st.markdown("### Risks & Barriers")
        for risk in r.get("risks_and_barriers", []):
            with st.container(border=True):
                st.markdown(f"**{risk.get('risk', '')}**")
                st.write(risk.get("description", ""))
                st.caption(f"Mitigation: {risk.get('mitigation', '')}")

    with col_strategy:
        strategy = r.get("recommended_ai_strategy", {})
        st.markdown("### Recommended AI Strategy")
        with st.container(border=True):
            st.markdown(f"**{strategy.get('headline', '')}**")
            st.write(strategy.get("approach", ""))
            st.markdown("**Quick wins:**")
            for qw in strategy.get("quick_wins", []):
                st.markdown(f"- {qw}")
            st.markdown("**Strategic bets:**")
            for sb in strategy.get("strategic_bets", []):
                st.markdown(f"- {sb}")

    st.divider()
    st.markdown("### Deloitte engagement angle")
    with st.container(border=True):
        st.markdown("**Deloitte**")
        st.write(r.get("deloitte_angle", ""))

