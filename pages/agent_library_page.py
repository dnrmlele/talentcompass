"""Agent Library management page (WO-11).

Browse built-in agent templates (read-only) and create / edit / delete custom
ones. Custom templates persist via the configured store (services.template_store)
and can be applied to roles from the Role Analysis page.
"""

import os

import streamlit as st

from services import agent_library

_FIELDS = (
    "name",
    "icon",
    "category",
    "description",
    "handles",
    "time_saving",
    "setup_complexity",
)
_SETUP_OPTIONS = ["", "Low", "Medium", "High"]


def _persistence_caption() -> None:
    mode = os.environ.get("TC_TEMPLATE_STORE", "session").strip().lower()
    if mode == "file":
        st.caption("Persistence: file store — custom templates survive restarts.")
    else:
        st.caption(
            "Persistence: session only. Export your session to keep custom templates, "
            "or set TC_TEMPLATE_STORE=file for on-disk persistence."
        )


def _template_form(form_key: str, src: dict | None, submit_label: str):
    """Render a template form; return (submitted_dict, deleted_bool)."""
    src = src or {}
    with st.form(form_key):
        cols = st.columns([2, 1, 1])
        name = cols[0].text_input("Name *", value=src.get("name", ""))
        icon = cols[1].text_input("Icon", value=src.get("icon", ""), help="An emoji")
        category = cols[2].text_input("Category", value=src.get("category", ""))
        description = st.text_area("Description", value=src.get("description", ""))
        handles = st.text_input("Handles", value=src.get("handles", ""))
        c1, c2 = st.columns(2)
        time_saving = c1.text_input(
            "Time saving",
            value=src.get("time_saving", ""),
            placeholder="e.g. ↓ 60% time",
        )
        setup_val = src.get("setup_complexity", "")
        setup = c2.selectbox(
            "Setup complexity",
            _SETUP_OPTIONS,
            index=_SETUP_OPTIONS.index(setup_val) if setup_val in _SETUP_OPTIONS else 0,
        )
        b1, b2 = st.columns(2)
        submitted = b1.form_submit_button(
            submit_label, type="primary", use_container_width=True
        )
        deleted = (
            b2.form_submit_button("Delete", use_container_width=True) if src else False
        )
    payload = {
        "name": name,
        "icon": icon,
        "category": category,
        "description": description,
        "handles": handles,
        "time_saving": time_saving,
        "setup_complexity": setup,
    }
    return (payload if submitted else None), deleted


def render():
    st.markdown("## Agent Library")
    st.caption(
        "Curated AI-agent templates you can apply to roles in Role Analysis. "
        "Built-ins ship with the app; custom templates are yours to manage."
    )
    _persistence_caption()

    # ── Built-in templates (read-only) ────────────────────────────────────────
    st.markdown("### Built-in templates")
    for t in agent_library.BUILTIN_AGENT_TEMPLATES:
        with st.container(border=True):
            st.markdown(
                f"**{t.get('icon', '')} {t['name']}**  ·  _{t.get('category', '')}_"
            )
            st.caption(t.get("description", ""))
            st.markdown(
                f"**Handles:** {t.get('handles', '')}  ·  "
                f"**Saving:** `{t.get('time_saving', '')}`  ·  "
                f"**Setup:** `{t.get('setup_complexity', '')}`"
            )

    # ── Custom templates (edit / delete) ──────────────────────────────────────
    st.markdown("### Your custom templates")
    customs = agent_library.list_custom_templates(st.session_state)
    if not customs:
        st.info(
            "No custom templates yet. Create one below, or save an agent from a Role Analysis."
        )
    for t in customs:
        with st.expander(
            f"{t.get('icon', '')} {t['name']}  ·  {t.get('category', '')}"
        ):
            payload, deleted = _template_form(
                f"edit_{t['name']}", t, submit_label="Save changes"
            )
            if deleted:
                agent_library.delete_template(st.session_state, t["name"])
                st.rerun()
            if payload:
                new_name = (payload.get("name") or "").strip()
                if not new_name:
                    st.error("A template needs a name.")
                else:
                    # If renamed, drop the old entry so we don't leave a duplicate.
                    if new_name.lower() != t["name"].lower():
                        agent_library.delete_template(st.session_state, t["name"])
                    agent_library.save_template(st.session_state, payload)
                    st.success("Saved.")
                    st.rerun()

    # ── Create a new template ─────────────────────────────────────────────────
    st.markdown("### Create a new template")
    payload, _ = _template_form("new_template", None, submit_label="Create template")
    if payload:
        try:
            agent_library.save_template(st.session_state, payload)
            st.success(f"Created “{payload['name'].strip()}”.")
            st.rerun()
        except ValueError as e:
            st.error(str(e))
