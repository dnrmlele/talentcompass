import streamlit as st
import plotly.express as px
import pandas as pd


def render():
    st.markdown("## Organization Overview")
    st.caption("All roles you have analyzed in this session are compared here.")

    roles = st.session_state.get("org_roles", [])

    if not roles:
        st.info("No roles analyzed yet. Run a Role Analysis first, then return here.", icon="ℹ️")
        return

# --- Summary table ---
    rows = []
    for r in roles:
        rows.append({
            "Role": r.get("_title", ""),
            "Client": r.get("_client", ""),
            "Department": r.get("_dept", ""),
            "Automation Score": r.get("automation_score", 0),
            "Hours Saved / Week": r.get("weekly_hours_saved", 0),
            "Priority": r.get("transformation_priority", ""),
            "AI Agents": len(r.get("ai_agents", [])),
            "Fully Automatable %": r.get("stats", {}).get("fully_automatable_pct", 0),
            "AI-Augmented %": r.get("stats", {}).get("ai_augmented_pct", 0),
            "Human-Only %": r.get("stats", {}).get("human_only_pct", 0),
        })
    df = pd.DataFrame(rows)

    # Automation score bar chart
    fig = px.bar(
        df.sort_values("Automation Score", ascending=True),
        x="Automation Score",
        y="Role",
        orientation="h",
        color="Automation Score",
        color_continuous_scale=["#01696f", "#d19900", "#a12c7b"],
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
        color_continuous_scale=["#e6f4f4", "#01696f"],
        text="Hours Saved / Week",
        title="Weekly Hours Saved per Employee",
        height=max(300, len(roles) * 60),
    )
    fig2.update_traces(texttemplate="%{text}h", textposition="outside")
    fig2.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=40, t=40, b=0))
    st.plotly_chart(fig2, use_container_width=True)

    # Stacked distribution
    df_stacked = df[["Role", "Fully Automatable %", "AI-Augmented %", "Human-Only %"]].copy()
    df_melted = df_stacked.melt(id_vars="Role", var_name="Category", value_name="Percentage")
    color_map = {"Fully Automatable %": "#01696f", "AI-Augmented %": "#d19900", "Human-Only %": "#c0beba"}
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
    fig3.update_layout(margin=dict(l=0, r=40, t=40, b=0), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig3, use_container_width=True)

# --- Role cards ---
    st.markdown("### Role Detail Cards")
    cols = st.columns(min(len(roles), 3))
    for i, r in enumerate(roles):
        score = r.get("automation_score", 0)
        priority = r.get("transformation_priority", "Medium")
        score_color = "#a12c7b" if score >= 75 else "#da7101" if score >= 55 else "#01696f"
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"**{r.get('_title', '')}**")
                st.caption(f"{r.get('_dept', '')}  -  {r.get('_client', '')}")
                st.markdown(
                    f"<div style='font-size:2rem;font-weight:800;color:{score_color}'>{score}%</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"**{priority} priority**")
                st.caption(f"{r.get('weekly_hours_saved', 0)} hours saved/week  -  {len(r.get('ai_agents', []))} agents")

# --- Clear session ---
    if st.button("Clear all roles", type="secondary"):
        st.session_state["org_roles"] = []
        st.session_state.pop("last_role_result", None)
        st.rerun()

