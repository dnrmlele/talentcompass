"""Tests for the Workload Impact engine, schema, prompt and client (WO-16).

These lock the deterministic maths (the defensible, auditable layer) and the
determinism boundary: with no llm_workload the output is byte-identical to the
original basic dict; with one, the annual 1,960 h/yr model adds task-level
hours, ST/MT FTE impact, scenarios, classification and regulatory flags.
"""

from __future__ import annotations

import json
import types
from unittest.mock import MagicMock, patch

from services.workforce import (
    compute_workforce_impact,
    rollup_workforce,
    build_scenarios,
    classify_role,
    regulatory_flags,
    _adoption_rate,
    _automation_rate,
    ANNUAL_FTE_HOURS,
    OVERSIGHT_FLOOR,
)
from services.schemas import WorkloadImpact
from services.prompts import workload_prompt, WORKLOAD_SYSTEM
import services.claude_client as cc

_ROLE = {
    "_title": "Fund Accountant",
    "_dept": "Operations",
    "weekly_hours_saved": 10,
    "stats": {"fully_automatable_pct": 25},
    "tasks": [{"name": "NAV reconciliation", "type": "AI-Augmented"}],
}

_LLM = {
    "tasks": [
        {
            "name": "A",
            "automation_type": "full",
            "time_allocation_pct": 50,
            "adoption_st": {
                "tech_readiness": "Low",
                "change_readiness": "Low",
                "data_readiness": "Low",
                "regulatory_clearance": "Low",
            },
            "adoption_mt": {
                "tech_readiness": "High",
                "change_readiness": "High",
                "data_readiness": "High",
                "regulatory_clearance": "High",
            },
        },
        {
            "name": "B",
            "automation_type": "human_only",
            "time_allocation_pct": 50,
            "adoption_st": {"tech_readiness": "High"},
            "adoption_mt": {"tech_readiness": "High"},
        },
    ],
    "strategic_value": "Support",
    "confidence": "Medium",
}


# ── Determinism boundary / back-compat ────────────────────────────────────────
def test_basic_path_unchanged_no_workload_keys():
    w = compute_workforce_impact(_ROLE, headcount=20, loaded_cost=80000)
    assert "hours_saved_mt" not in w
    assert "scenarios" not in w
    # the original 12-key contract
    assert set(w) == {
        "headcount",
        "loaded_cost",
        "weekly_hours_saved_per_fte",
        "total_weekly_hours_freed",
        "fte_freed",
        "annual_payroll_savings",
        "reskill_cost_per_fte",
        "transition_cost",
        "net_annual_savings",
        "displaced_fte",
        "severance_months",
        "severance_exposure",
    }


def test_workload_is_deterministic():
    a = compute_workforce_impact(_ROLE, 20, 80000, llm_workload=_LLM)
    b = compute_workforce_impact(_ROLE, 20, 80000, llm_workload=_LLM)
    assert a == b


# ── 1,960 h reconciliation (Step 0) ───────────────────────────────────────────
def test_annual_hours_reconcile_to_1960():
    w = compute_workforce_impact(_ROLE, headcount=10, loaded_cost=0, llm_workload=_LLM)
    # allocations sum to 100 -> total task hours == headcount * 1960 (within rounding)
    total_task_hours = sum(t["task_hours"] for t in w["tasks"])
    assert abs(total_task_hours - 10 * ANNUAL_FTE_HOURS) <= 0.05 * 10 * ANNUAL_FTE_HOURS
    assert w["total_annual_hours"] == 10 * ANNUAL_FTE_HOURS
    assert w["reconciliation"]["reconciled"] is True


def test_allocation_variance_flagged():
    bad = {"tasks": [{"name": "A", "automation_type": "full", "time_allocation_pct": 70}]}
    w = compute_workforce_impact(_ROLE, 10, 0, llm_workload=bad)
    assert w["reconciliation"]["reconciled"] is False
    assert w["reconciliation"]["variance_pct"] == -30.0


# ── Adoption = min of factors ─────────────────────────────────────────────────
def test_adoption_rate_is_min_of_factors():
    factors = {
        "tech_readiness": "High",
        "change_readiness": "High",
        "data_readiness": "High",
        "regulatory_clearance": "Low",  # bottleneck
    }
    assert _adoption_rate(factors, "realistic") == 0.3  # Low


def test_adoption_missing_factor_defaults_medium():
    # only one factor given; others default to Medium (0.6); min = 0.6
    assert _adoption_rate({"tech_readiness": "High"}, "realistic") == 0.6


# ── Automation bands + oversight floor ────────────────────────────────────────
def test_automation_bands_and_oversight_floor():
    assert _automation_rate("full", "realistic") == 1.0 - OVERSIGHT_FLOOR  # capped 0.85
    assert _automation_rate("ai_led", "realistic") == 0.55  # band midpoint
    assert _automation_rate("ai_led", "conservative") == 0.40  # band low
    assert _automation_rate("ai_led", "ambitious") == 0.70  # band high
    assert _automation_rate("human_led", "realistic") == 0.20
    assert _automation_rate("human_only", "realistic") == 0.0


# ── ST vs MT ──────────────────────────────────────────────────────────────────
def test_mt_saves_more_than_st_when_adoption_grows():
    w = compute_workforce_impact(_ROLE, 10, 0, llm_workload=_LLM)
    assert w["hours_saved_mt"] > w["hours_saved_st"]
    # FTE saved derives from hours / 1960
    assert w["fte_saved_mt"] == round(w["hours_saved_mt"] / ANNUAL_FTE_HOURS, 2)


# ── Classification ────────────────────────────────────────────────────────────
def test_classification_thresholds():
    assert classify_role(85) == "release_risk"
    assert classify_role(80) == "release_risk"
    assert classify_role(50) == "reduction"
    assert classify_role(30) == "reduction"
    assert classify_role(10) == "augmentation"


def test_min_viable_role_redesign_flag():
    # single incumbent, one fully-automatable task at full MT adoption -> tiny residual
    llm = {
        "tasks": [
            {
                "name": "A",
                "automation_type": "full",
                "time_allocation_pct": 100,
                "adoption_mt": {
                    "tech_readiness": "High",
                    "change_readiness": "High",
                    "data_readiness": "High",
                    "regulatory_clearance": "High",
                },
            }
        ]
    }
    w = compute_workforce_impact(_ROLE, headcount=1, loaded_cost=0, llm_workload=llm)
    # full capped at 0.85 * adoption 0.9 = 0.765 removed -> residual 0.235 FTE < 0.5
    assert w["redesign_flag"] is True


# ── Scenario monotonicity ─────────────────────────────────────────────────────
def test_scenarios_are_monotonic():
    s = build_scenarios(10, _LLM["tasks"])
    assert (
        s["conservative"]["hours_saved_mt"]
        <= s["realistic"]["hours_saved_mt"]
        <= s["ambitious"]["hours_saved_mt"]
    )


# ── Regulatory flags ──────────────────────────────────────────────────────────
def test_regulatory_flags_luxembourg():
    flags = regulatory_flags(headcount=20, fte_saved_mt=8, pct_impacted_mt=60, market="Luxembourg")
    joined = " ".join(flags).lower()
    assert "collective-redundancy" in joined  # 8 >= 7
    assert "staff-delegation" in joined  # headcount >= 15 and fte >= 1
    assert "high transformation" in joined  # 60 >= 50


def test_regulatory_flags_none_below_thresholds():
    assert regulatory_flags(headcount=5, fte_saved_mt=0.2, pct_impacted_mt=10) == []


def test_regulatory_flags_non_lu_market_empty():
    assert regulatory_flags(20, 8, 60, market="Belgium") == []


# ── Overrides ─────────────────────────────────────────────────────────────────
def test_override_changes_result():
    base = compute_workforce_impact(_ROLE, 10, 0, llm_workload=_LLM)
    # force task B from human_only to full -> more hours saved
    over = {1: {"automation_type": "full"}}
    bumped = compute_workforce_impact(_ROLE, 10, 0, llm_workload=_LLM, overrides=over)
    assert bumped["hours_saved_mt"] > base["hours_saved_mt"]


# ── Rollup includes workload keys ─────────────────────────────────────────────
def test_rollup_sums_workload_keys():
    roles = [
        {"workforce": compute_workforce_impact(_ROLE, 10, 80000, llm_workload=_LLM)},
        {"workforce": compute_workforce_impact(_ROLE, 5, 80000, llm_workload=_LLM)},
        {"workforce": {"fte_freed": 1, "headcount": 2}},  # basic only
    ]
    total = rollup_workforce(roles)
    assert total["roles_with_data"] == 3
    assert total["roles_with_workload"] == 2
    assert total["fte_saved_mt"] > 0


# ── Schema ────────────────────────────────────────────────────────────────────
def test_schema_empty_defaults():
    out = WorkloadImpact.model_validate({}).model_dump()
    assert out["tasks"] == []
    assert out["strategic_value"] is None


def test_schema_parses_nested_task():
    out = WorkloadImpact.model_validate(_LLM).model_dump()
    assert out["tasks"][0]["automation_type"] == "full"
    assert out["tasks"][0]["adoption_mt"]["tech_readiness"] == "High"


# ── Prompt & system ───────────────────────────────────────────────────────────
def test_prompt_embeds_role_and_schema():
    p = workload_prompt(_ROLE)
    assert "Fund Accountant" in p
    assert "automation_type" in p
    assert "NAV reconciliation" in p  # task list injected


def test_system_quantify_only_and_json():
    assert "JSON" in WORKLOAD_SYSTEM
    assert "never recommend workforce actions" in WORKLOAD_SYSTEM.lower()


# ── Client end-to-end (mocked API) ────────────────────────────────────────────
def test_analyze_workload_impact_validates():
    payload = {"tasks": [{"name": "A", "automation_type": "ai_led", "time_allocation_pct": 100}]}

    def fake_create(**kw):
        m = MagicMock()
        m.content = [types.SimpleNamespace(text=json.dumps(payload))]
        return m

    client = MagicMock()
    client.messages.create.side_effect = fake_create
    with patch.object(cc.anthropic, "Anthropic", return_value=client):
        out = cc.analyze_workload_impact("k", _ROLE, "Luxembourg")
    assert out["tasks"][0]["automation_type"] == "ai_led"
