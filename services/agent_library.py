"""Reusable AI-agent template library.

Consultants pick curated agent templates and apply them to a role instead of
relying on a fresh Claude generation each time — reproducible and owned.

Persistence seam: `get_templates(state)` returns built-in templates (shipped in
code) plus any custom templates the consultant saved this session. Custom
templates live in session_state today; a later work order can back the same
accessor with a per-user/project database WITHOUT touching the UI. The export/
import flow (services/session_io.py) already carries the custom list, so saved
templates survive a session round-trip immediately.
"""

from __future__ import annotations

from typing import Any

# CUSTOM_KEY is owned by template_store now; re-exported here so existing imports
# (services.session_io) keep working. get_store resolves the persistence backend.
from services.template_store import CUSTOM_KEY, get_store

# Fields that make up an AI agent (must match what Claude returns / the PDF reads).
AGENT_FIELDS = (
    "name",
    "icon",
    "description",
    "handles",
    "time_saving",
    "setup_complexity",
)
# A template is an agent plus a category label for browsing.
_TEMPLATE_EXTRA = ("category",)


# Built-in library — seeded for the Luxembourg fund-admin / finance market.
BUILTIN_AGENT_TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "NAV Reconciliation Agent",
        "icon": "📊",
        "description": "Matches fund positions, cash, and portfolio valuations against custodian and administrator records, flagging breaks for review.",
        "handles": "Daily NAV reconciliation, position/cash break detection",
        "time_saving": "↓ 70% time",
        "setup_complexity": "Medium",
        "category": "Fund Administration",
    },
    {
        "name": "KYC/AML Document Agent",
        "icon": "🛡️",
        "description": "Extracts and validates KYC/AML documentation, screens against watchlists, and pre-fills onboarding checklists for compliance review.",
        "handles": "KYC document intake, AML screening, onboarding checklists",
        "time_saving": "↓ 60% time",
        "setup_complexity": "High",
        "category": "Compliance",
    },
    {
        "name": "Regulatory Reporting Agent",
        "icon": "📑",
        "description": "Assembles draft CSSF/AIFMD/EBA submissions from source data, validates completeness, and tracks filing deadlines.",
        "handles": "Regulatory filing drafts, deadline tracking, completeness checks",
        "time_saving": "↓ 50% time",
        "setup_complexity": "High",
        "category": "Compliance",
    },
    {
        "name": "Invoice & AP Agent",
        "icon": "🧾",
        "description": "Reads invoices, matches to purchase orders, routes exceptions, and prepares payment runs for approval.",
        "handles": "Invoice capture, PO matching, AP exception routing",
        "time_saving": "↓ 80% time",
        "setup_complexity": "Low",
        "category": "Finance",
    },
    {
        "name": "Management Reporting Agent",
        "icon": "📈",
        "description": "Builds recurring management dashboards and board packs from validated data, with variance commentary drafts.",
        "handles": "Dashboard production, variance analysis, board-pack drafts",
        "time_saving": "↓ 65% time",
        "setup_complexity": "Medium",
        "category": "Finance",
    },
    {
        "name": "Investor Query Agent",
        "icon": "✉️",
        "description": "Drafts responses to routine investor and stakeholder queries using approved templates and fund data, escalating non-standard cases.",
        "handles": "Routine investor correspondence, query triage",
        "time_saving": "↓ 55% time",
        "setup_complexity": "Low",
        "category": "Client Service",
    },
]


def _clean(d: dict[str, Any], keep_category: bool) -> dict[str, Any]:
    """Project an arbitrary dict onto the allowed agent/template fields."""
    fields = AGENT_FIELDS + (_TEMPLATE_EXTRA if keep_category else ())
    out = {
        f: ("" if d.get(f) is None else str(d.get(f)))
        for f in fields
        if f in d or f in AGENT_FIELDS
    }
    return out


def _mirror(state: Any, customs: list[dict[str, Any]]) -> None:
    """Keep state[CUSTOM_KEY] in sync with the store so session export/import and
    the sidebar see custom templates regardless of which backend persists them."""
    try:
        state[CUSTOM_KEY] = list(customs)
    except Exception:
        pass


def list_custom_templates(state: Any) -> list[dict[str, Any]]:
    """Custom templates from the configured store (built-ins excluded)."""
    customs = [_clean(t, keep_category=True) for t in get_store(state).load()]
    _mirror(state, customs)
    return customs


def get_templates(state: Any) -> list[dict[str, Any]]:
    """Built-in templates plus the configured store's custom ones (built-ins first)."""
    return [dict(t) for t in BUILTIN_AGENT_TEMPLATES] + list_custom_templates(state)


def save_template(state: Any, template: dict[str, Any]) -> dict[str, Any]:
    """Save (or replace by name) a custom template via the configured store.

    Returns the cleaned template. Raises ValueError if it has no name.
    """
    name = (template.get("name") or "").strip()
    if not name:
        raise ValueError("A template needs a name.")
    cleaned = _clean(template, keep_category=True)
    cleaned["name"] = name
    store = get_store(state)
    custom = [
        c for c in store.load() if (c.get("name") or "").strip().lower() != name.lower()
    ]
    custom.append(cleaned)
    store.save(custom)
    _mirror(state, custom)
    return cleaned


def delete_template(state: Any, name: str) -> bool:
    """Delete a custom template by name. Returns True if one was removed."""
    target = (name or "").strip().lower()
    store = get_store(state)
    before = store.load()
    after = [c for c in before if (c.get("name") or "").strip().lower() != target]
    if len(after) == len(before):
        return False
    store.save(after)
    _mirror(state, after)
    return True


def apply_to_role(role: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    """Append a template (as an agent) to a role's ai_agents, deduped by name.

    Mutates and returns the role dict. The category field is dropped — the role's
    ai_agents entries carry only the agent fields the UI/PDF render.
    """
    agent = _clean(template, keep_category=False)
    name = (agent.get("name") or "").strip()
    agents = list(role.get("ai_agents") or [])
    agents = [
        a for a in agents if (a.get("name") or "").strip().lower() != name.lower()
    ]
    agents.append(agent)
    role["ai_agents"] = agents
    return role


def sanitize_custom_templates(items: Any) -> list[dict[str, Any]]:
    """Normalise an untrusted list of custom templates (used on session import)."""
    if not isinstance(items, list):
        return []
    out = []
    for it in items:
        if isinstance(it, dict) and (it.get("name") or "").strip():
            out.append(_clean(it, keep_category=True))
    return out
