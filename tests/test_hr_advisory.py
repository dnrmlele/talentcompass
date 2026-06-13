"""Tests for HR management & advisory module (WO-14)."""

from __future__ import annotations

import json
import types
from unittest.mock import MagicMock, patch

from services.prompts import hr_advisory_prompt, HR_ADVISORY_SYSTEM
from services.schemas import HRAdvisory
import services.claude_client as cc

_ROLE = {
    "_title": "Fund Accountant",
    "_dept": "Operations",
    "automation_score": 62,
    "stats": {
        "fully_automatable_pct": 25,
        "ai_augmented_pct": 50,
        "human_only_pct": 25,
    },
}


def test_prompt_embeds_role_and_workforce():
    p = hr_advisory_prompt(
        _ROLE,
        {
            "headcount": 20,
            "fte_freed": 5,
            "displaced_fte": 5,
            "annual_payroll_savings": 400000,
        },
    )
    assert "Fund Accountant" in p
    assert "Headcount: 20" in p
    assert "redeployment_options" in p


def test_prompt_without_workforce_omits_figures():
    p = hr_advisory_prompt(_ROLE, None)
    assert "Workforce figures" not in p
    assert "Fund Accountant" in p


def test_system_demands_json():
    assert "JSON" in HR_ADVISORY_SYSTEM


def test_schema_all_optional_defaults():
    out = HRAdvisory.model_validate({}).model_dump()
    assert out["summary"] is None
    assert out["redeployment_options"] == []
    assert out["change_management"] == []


def test_schema_parses_nested():
    out = HRAdvisory.model_validate(
        {
            "summary": "x",
            "redeployment_options": [{"option": "Advisory", "effort": "Medium"}],
            "change_management": [
                {"phase": "Consult", "actions": ["Inform staff council"]}
            ],
        }
    ).model_dump()
    assert out["redeployment_options"][0]["option"] == "Advisory"
    assert out["change_management"][0]["actions"] == ["Inform staff council"]


def test_analyze_hr_advisory_validates(monkeypatch):
    payload = {"summary": "advice", "reskilling_focus": ["Python", "Data viz"]}

    def fake_create(**kw):
        m = MagicMock()
        m.content = [types.SimpleNamespace(text=json.dumps(payload))]
        return m

    client = MagicMock()
    client.messages.create.side_effect = fake_create
    with patch.object(cc.anthropic, "Anthropic", return_value=client):
        out = cc.analyze_hr_advisory("k", _ROLE, {"headcount": 20})
    assert out["summary"] == "advice"
    assert out["reskilling_focus"] == ["Python", "Data viz"]
