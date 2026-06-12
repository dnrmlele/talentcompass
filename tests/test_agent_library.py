"""Tests for the AI-agent template library (WO-09)."""

from __future__ import annotations

from services.agent_library import (
    AGENT_FIELDS,
    BUILTIN_AGENT_TEMPLATES,
    CUSTOM_KEY,
    apply_to_role,
    get_templates,
    sanitize_custom_templates,
    save_template,
)


def test_builtins_have_all_agent_fields():
    for t in BUILTIN_AGENT_TEMPLATES:
        for f in AGENT_FIELDS:
            assert f in t and t[f], f"builtin {t.get('name')} missing {f}"
        assert t["category"]


def test_get_templates_includes_builtins_and_custom():
    state = {CUSTOM_KEY: [{"name": "My Agent", "category": "Custom"}]}
    names = [t["name"] for t in get_templates(state)]
    assert "My Agent" in names
    assert len(names) == len(BUILTIN_AGENT_TEMPLATES) + 1


def test_save_template_dedupes_by_name_case_insensitive():
    state = {}
    save_template(state, {"name": "Recon Bot", "description": "v1", "category": "X"})
    save_template(state, {"name": "recon bot", "description": "v2", "category": "X"})
    customs = state[CUSTOM_KEY]
    assert len(customs) == 1
    assert customs[0]["description"] == "v2"


def test_save_template_requires_name():
    import pytest

    with pytest.raises(ValueError):
        save_template({}, {"name": "  ", "description": "x"})


def test_apply_to_role_appends_and_dedupes():
    role = {"ai_agents": [{"name": "Existing", "description": "keep"}]}
    apply_to_role(role, {"name": "New Agent", "description": "d", "category": "C"})
    names = [a["name"] for a in role["ai_agents"]]
    assert names == ["Existing", "New Agent"]
    # applying same name replaces, no duplicate
    apply_to_role(role, {"name": "new agent", "description": "d2"})
    names = [a["name"] for a in role["ai_agents"]]
    assert names.count("new agent") + names.count("New Agent") == 1


def test_apply_to_role_drops_category_keeps_agent_fields():
    role = {}
    apply_to_role(role, {"name": "A", "category": "Finance", "time_saving": "↓ 50%"})
    agent = role["ai_agents"][0]
    assert "category" not in agent
    assert agent["time_saving"] == "↓ 50%"
    assert set(agent.keys()) <= set(AGENT_FIELDS)


def test_sanitize_drops_nameless_and_nonlists():
    assert sanitize_custom_templates("nope") == []
    cleaned = sanitize_custom_templates(
        [{"name": "Keep", "category": "C"}, {"description": "no name"}, {"name": "  "}]
    )
    assert [c["name"] for c in cleaned] == ["Keep"]
