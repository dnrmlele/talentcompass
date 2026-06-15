import streamlit as st
import plotly.express as px
import pandas as pd

from services.workforce import rollup_workforce


def _eur(v) -> str:
    try:
        return f"€{float(v):,.0f}"
    except (TypeError, ValueError):
        return "€0"


def render():
    st.markdown("## Organization Overview")
    st.caption("All roles you have analyzed in this session are compared here.")

    roles = st.session_state.get("org_roles", [])

    if not roles:
        st.info(
            "No roles analyzed yet. Run a Role Analysis first, then return here.",
            icon="ℹ️",
        )
        return

    # --- Org-wide workforce & financial rollup (deterministic) ---
    total = rollup_workforce(roles)
    if total["roles_with_data"]:
        st.markdown("### Workforce & Financial Impact (org-wide)")
        st.caption(
            f"Summed across the {total['roles_with_data']} of {len(roles)} role(s) with headcount entered. "
            "Real arithmetic on your numbers, not AI estimates."
        )
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total FTE freed", f"{total['fte_freed']:.1f}")
        m2.metric("Annual payroll savings", _eur(total["annual_payroll_savings"]))
        m3.metric("Net annual savings", _eur(total["net_annual_savings"]))
        m4.metric("Severance exposure", _eur(total["severance_exposure"]))
        st.caption(
            f"Headcount covered {total['headcount']:.0f}  ·  "
            f"displaced (fully-automatable) {total['displaced_fte']:.1f} FTE  ·  "
            f"transition cost {_eur(total['transition_cost'])}"
        )
        st.divider()

    # --- Summary table ---
    rows = []
    for r in roles:
        rows.append(
            {
                "Role": r.get("_title", ""),
                "Client": r.get("_client", ""),
                "Department": r.get("_dept", ""),
                "Automation Score": r.get("automation_score", 0),
                "Hours Saved / Week": r.get("weekly_hours_saved", 0),
                "Priority": r.get("transformation_priority", ""),
                "AI Agents": len(r.get("ai_agents", [])),
                "Fully Automatable %": r.get("stats", {}).get(
                    "fully_automatable_pct", 0
                ),
                "AI-Augmented %": r.get("stats", {}).get("ai_augmented_pct", 0),
                "Human-Only %": r.get("stats", {}).get("human_only_pct", 0),
            }
        )
    df = pd.DataFrame(rows)

    # Automation score bar chart
    fig = px.bar(
        df.sort_values("Automation Score", ascending=True),
        x="Automation Score",
        y="Role",
        orientation="h",
        color="Automation Score",
        color_continuous_scale=["#DDEFE8", "#86BC25", "#046A38"],
        range_color=[0, 100],
        text="Automation Score",
        title="Automation Potential by Role",
        labels={"Automation Score": "Score (%)"},
        height=max(300, len(roles) * 60),
    )
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    fig.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=40, t=40, b=0))
    st.plotly_chart(fig, use_container_width=True)

    # Hours saved comparison
    fig2 = px.bar(
        df.sort_values("Hours Saved / Week", ascending=True),
        x="Hours Saved / Week",
        y="Role",
        orientation="h",
        color="Hours Saved / Week",
        color_continuous_scale=["#DDEFE8", "#046A38"],
        text="Hours Saved / Week",
        title="Weekly Hours Saved per Employee",
        height=max(300, len(roles) * 60),
    )
    fig2.update_traces(texttemplate="%{text}h", textposition="outside")
    fig2.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=40, t=40, b=0))
    st.plotly_chart(fig2, use_container_width=True)

    # Stacked distribution
    df_stacked = df[
        ["Role", "Fully Automatable %", "AI-Augmented %", "Human-Only %"]
    ].copy()
    df_melted = df_stacked.melt(
        id_vars="Role", var_name="Category", value_name="Percentage"
    )
    color_map = {
        "Fully Automatable %": "#046A38",
        "AI-Augmented %": "#0076A8",
        "Human-Only %": "#75787B",
    }
    fig3 = px.bar(
        df_melted,
        x="Percentage",
        y="Role",
        color="Category",
        orientation="h",
        barmode="stack",
        color_discrete_map=color_map,
        title="Task Distribution Breakdown",
        height=max(300, len(roles) * 60),
    )
    fig3.update_layout(
        margin=dict(l=0, r=40, t=40, b=0), legend=dict(orientation="h", y=-0.2)
    )
    st.plotly_chart(fig3, use_container_width=True)

    # --- Role cards ---
    st.markdown("### Role Detail Cards")
    cols = st.columns(min(len(roles), 3))
    for i, r in enumerate(roles):
        score = r.get("automation_score", 0)
        priority = r.get("transformation_priority", "Medium")
        score_color = (
            "#046A38" if score >= 75 else "#86BC25" if score >= 55 else "#75787B"
        )
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"**{r.get('_title', '')}**")
                st.caption(f"{r.get('_dept', '')}  -  {r.get('_client', '')}")
                st.markdown(
                    f"<div style='font-size:2rem;font-weight:800;color:{score_color}'>{score}%</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"**{priority} priority**")
                st.caption(
                    f"{r.get('weekly_hours_saved', 0)} hours saved/week  -  {len(r.get('ai_agents', []))} agents"
                )

    # --- Clear session ---
    if st.button("Clear all roles", type="secondary"):
        st.session_state["org_roles"] = []
        st.session_state.pop("last_role_result", None)
        st.rerun()
