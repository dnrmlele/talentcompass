"""Tests for deterministic workforce impact maths (WO-13)."""

from __future__ import annotations

from services.workforce import compute_workforce_impact, rollup_workforce

_ROLE = {"weekly_hours_saved": 10, "stats": {"fully_automatable_pct": 25}}


def test_basic_fte_and_payroll():
    w = compute_workforce_impact(_ROLE, headcount=20, loaded_cost=80000)
    # 10h * 20 = 200h freed / 40 = 5 FTE
    assert w["fte_freed"] == 5.0
    assert w["annual_payroll_savings"] == 400000  # 5 * 80000
    # displaced = 20 * 25% = 5 FTE; severance default 3 months
    assert w["displaced_fte"] == 5.0
    assert w["severance_exposure"] == 100000  # 5 * 80000 * 3/12


def test_fte_freed_capped_at_headcount():
    # absurd hours can't free more FTE than exist
    w = compute_workforce_impact(
        {"weekly_hours_saved": 200, "stats": {}}, headcount=3, loaded_cost=50000
    )
    assert w["fte_freed"] == 3.0
    assert w["annual_payroll_savings"] == 150000


def test_transition_cost_and_net():
    w = compute_workforce_impact(
        _ROLE, headcount=20, loaded_cost=80000, reskill_cost_per_fte=10000
    )
    assert w["transition_cost"] == 50000  # 5 FTE * 10000
    assert w["net_annual_savings"] == 350000  # 400000 - 50000


def test_severance_months_zero():
    w = compute_workforce_impact(
        _ROLE, headcount=20, loaded_cost=80000, severance_months=0
    )
    assert w["severance_exposure"] == 0


def test_garbage_inputs_are_safe():
    w = compute_workforce_impact({}, headcount="oops", loaded_cost=None)
    assert w["fte_freed"] == 0.0
    assert w["annual_payroll_savings"] == 0
    assert w["headcount"] == 0


def test_rollup_sums_only_roles_with_data():
    roles = [
        {
            "workforce": {
                "fte_freed": 5,
                "annual_payroll_savings": 400000,
                "headcount": 20,
            }
        },
        {
            "workforce": {
                "fte_freed": 2,
                "annual_payroll_savings": 100000,
                "headcount": 8,
            }
        },
        {"_title": "no workforce data"},
    ]
    total = rollup_workforce(roles)
    assert total["roles_with_data"] == 2
    assert total["fte_freed"] == 7.0
    assert total["annual_payroll_savings"] == 500000
    assert total["headcount"] == 28
