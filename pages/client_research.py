import copy

import streamlit as st
import plotly.graph_objects as go
from services.claude_client import (
    research_company,
    disambiguate_company,
    ClaudeClientError,
)
from services.company_context import inferred_size_to_company_size
from services.prompts import MARKETS


def _market_label(key: str) -> str:
    return f"{key} (beta)" if MARKETS[key].get("beta") else key


_ERROR_MESSAGES = {
    "auth": "Invalid Claude API key. Check the key in the sidebar and try again.",
    "rate_limit": "Claude is rate-limited right now. Wait a moment and retry.",
    "bad_json": "Claude returned an unreadable response. Please retry the research.",
    "api": "Claude API call failed. Check your connection and try again.",
}


def _run_research(api_key: str, client_name: str, industry: str, market: str) -> None:
    """Run the full company research and update session state. Shared by the
    direct path and the disambiguation path."""
    with st.spinner(f"Researching {client_name} in the {market} market..."):
        try:
            result = research_company(
                api_key=api_key, client_name=client_name, industry=industry
            )
        except ClaudeClientError as e:
            st.error(_ERROR_MESSAGES.get(e.kind, _ERROR_MESSAGES["api"]))
            return
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
    # Clear candidate state once research has run.
    st.session_state.pop("entity_candidates", None)
    st.session_state.pop("entity_candidates_for", None)


def render():
    st.markdown("## Client Research")
    st.caption(
        "Enter a client name to generate a Luxembourg-focused AI potential assessment, "
        "competitor intelligence, and strategic recommendations - all generated live from Claude."
    )

    col1, col2 = st.columns(2)
    with col1:
        client_name = st.text_input(
            "Client Name *",
            placeholder="e.g. Clearstream, Pictet, Arendt, State Street, Alter Domus",
            key="cr_name",
        )
    with col2:
        industry = st.text_input(
            "Industry",
            placeholder="e.g. Fund Administration, Banking, Legal - leave blank to auto-infer",
            key="cr_industry",
        )
    market = st.selectbox(
        "Market",
        list(MARKETS.keys()),
        format_func=_market_label,
        key="market",
        help="Luxembourg is the fully-supported profile. Belgium is an early beta.",
    )
    if MARKETS[market].get("beta"):
        st.caption(
            f"{market} is a beta market profile - regulators are real, trend data is still placeholder."
        )

    c_find, c_research = st.columns(2)
    find = c_find.button(
        "Find entity",
        use_container_width=True,
        help="Some names map to several real entities (e.g. a retailer vs a financial firm). "
        "List candidates and pick the right one before research.",
    )
    research = c_research.button(
        "Research client", type="primary", use_container_width=True
    )

    api_key = st.session_state.get("api_key", "")

    if find:
        if not api_key:
            st.error("Enter your Claude API key in the sidebar first.")
        elif not client_name:
            st.error("Client name is required.")
        else:
            with st.spinner(f"Finding entities named '{client_name}' in {market}..."):
                try:
                    cands = disambiguate_company(api_key, client_name, market).get(
                        "candidates", []
                    )
                    st.session_state["entity_candidates"] = cands
                    st.session_state["entity_candidates_for"] = client_name
                except ClaudeClientError as e:
                    st.error(_ERROR_MESSAGES.get(e.kind, _ERROR_MESSAGES["api"]))

    # ── Candidate picker (only for the name the candidates were fetched for) ──
    cands = st.session_state.get("entity_candidates") or []
    if cands and st.session_state.get("entity_candidates_for") == client_name:
        if len(cands) == 1:
            st.info(
                "One entity matched. Research it below, or refine the name and search again."
            )
        else:
            st.markdown(
                f"**{len(cands)} entities match “{client_name}” — pick the right one:**"
            )
        idx = st.radio(
            "Matching entities",
            list(range(len(cands))),
            format_func=lambda i: f"{cands[i].get('legal_name', '?')}  —  {cands[i].get('sector', '?')}",
            key="entity_pick",
        )
        chosen = cands[idx]
        meta = chosen.get("description", "") or ""
        if chosen.get("hint"):
            meta = f"{meta}  ·  {chosen['hint']}" if meta else chosen["hint"]
        src_note = (
            "✓ Authoritative — GLEIF registry"
            if chosen.get("source") == "registry"
            else "AI-listed — verify before use"
        )
        st.caption(f"{meta}  ·  {src_note}" if meta else src_note)
        if st.button(
            "Research selected entity", type="primary", key="research_selected"
        ):
            if not api_key:
                st.error("Enter your Claude API key in the sidebar first.")
            else:
                _run_research(
                    api_key,
                    chosen.get("legal_name") or client_name,
                    chosen.get("sector") or industry,
                    market,
                )

    if research:
        if not api_key:
            st.error("Enter your Claude API key in the sidebar first.")
        elif not client_name:
            st.error("Client name is required.")
        else:
            _run_research(api_key, client_name, industry, market)

    r = st.session_state.get("last_company_result")
    if not r:
        return

    st.divider()

    # --- Company header ---
    profile = r.get("company_profile", {})
    col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
    with col_h1:
        st.markdown(f"### {profile.get('name', '')}")
        st.caption(
            f"{profile.get('inferred_industry', '')}  -  {profile.get('inferred_size', '')}"
        )
    with col_h2:
        st.metric("AI Potential Score", f"{r.get('ai_potential_score', 0)} / 100")
    with col_h3:
        st.markdown(f"**{r.get('ai_potential_label', '')}**")

    # --- AI potential gauge ---
    col_gauge, col_profile = st.columns([1, 2])
    score = r.get("ai_potential_score", 0)
    with col_gauge:
        gauge_color = (
            "#a12c7b" if score >= 75 else "#da7101" if score >= 55 else "#01696f"
        )
        fig = go.Figure(
            go.Indicator(
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
            )
        )
        fig.update_layout(height=260, margin=dict(t=40, b=0, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)

    with col_profile:
        with st.container(border=True):
            st.markdown("**Company Profile**")
            st.write(r.get("ai_potential_summary", ""))
            st.markdown(
                f"**Luxembourg presence:** {profile.get('luxembourg_presence', '')}"
            )
            st.markdown(
                f"**Regulatory context:** {profile.get('regulatory_context', '')}"
            )

    st.divider()

    # --- Industry trends + competitor moves ---
    col_trends, col_comp = st.columns(2)

    with col_trends:
        st.markdown("### Industry AI trends")
        for trend in r.get("industry_ai_trends", []):
            impact = trend.get("impact", "Medium")
            with st.container(border=True):
                st.markdown(f"**{trend.get('trend', '')}**")
                st.caption(
                    f"Impact: {impact}  -  Timeline: {trend.get('timeline', '')}"
                )
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
    priority_colors = {
        "Quick Win": "#437a22",
        "Strategic": "#006494",
        "Long-term": "#7a39bb",
    }
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
