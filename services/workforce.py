"""Deterministic workforce & financial impact maths (WO-13).

Unlike the LLM-generated automation_score (a judgement), these figures are plain
arithmetic on consultant-supplied headcount and fully-loaded cost. They are
defensible: same inputs always give the same numbers, and the formulas are
explicit below. The LLM only supplies weekly_hours_saved / automation_score /
fully_automatable_pct; everything financial is computed here.

Formulas (per role):
  total_weekly_hours_freed = weekly_hours_saved_per_fte * headcount
  fte_freed                = min(headcount, total_weekly_hours_freed / 40)
  annual_payroll_savings   = fte_freed * loaded_cost
  transition_cost          = fte_freed * reskill_cost_per_fte
  net_annual_savings       = annual_payroll_savings - transition_cost
  displaced_fte            = headcount * fully_automatable_pct / 100
  severance_exposure       = displaced_fte * loaded_cost * severance_months / 12
"""

from __future__ import annotations

from typing import Any

FULL_WEEK_HOURS = 40.0

# Keys that roll up additively across roles.
_ROLLUP_KEYS = (
    "headcount",
    "fte_freed",
    "annual_payroll_savings",
    "transition_cost",
    "net_annual_savings",
    "displaced_fte",
    "severance_exposure",
)


def _num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def compute_workforce_impact(
    role: dict[str, Any],
    headcount: Any,
    loaded_cost: Any,
    reskill_cost_per_fte: Any = 0.0,
    severance_months: Any = 3.0,
) -> dict[str, Any]:
    """Compute FTE, payroll, transition and severance figures for one role."""
    headcount = max(0, int(_num(headcount)))
    loaded_cost = max(0.0, _num(loaded_cost))
    reskill_cost_per_fte = max(0.0, _num(reskill_cost_per_fte))
    severance_months = max(0.0, _num(severance_months))

    weekly_hours_saved = max(0.0, _num(role.get("weekly_hours_saved")))
    stats = role.get("stats") or {}
    fully_auto_pct = max(0.0, min(100.0, _num(stats.get("fully_automatable_pct"))))

    total_hours_freed = weekly_hours_saved * headcount
    fte_freed = min(float(headcount), total_hours_freed / FULL_WEEK_HOURS)
    payroll_savings = fte_freed * loaded_cost
    transition_cost = fte_freed * reskill_cost_per_fte
    net_savings = payroll_savings - transition_cost

    displaced_fte = headcount * fully_auto_pct / 100.0
    severance_exposure = displaced_fte * loaded_cost * (severance_months / 12.0)

    return {
        "headcount": headcount,
        "loaded_cost": round(loaded_cost, 0),
        "weekly_hours_saved_per_fte": round(weekly_hours_saved, 1),
        "total_weekly_hours_freed": round(total_hours_freed, 1),
        "fte_freed": round(fte_freed, 2),
        "annual_payroll_savings": round(payroll_savings, 0),
        "reskill_cost_per_fte": round(reskill_cost_per_fte, 0),
        "transition_cost": round(transition_cost, 0),
        "net_annual_savings": round(net_savings, 0),
        "displaced_fte": round(displaced_fte, 2),
        "severance_months": severance_months,
        "severance_exposure": round(severance_exposure, 0),
    }


def rollup_workforce(roles: list[dict[str, Any]]) -> dict[str, Any]:
    """Sum workforce impact across all roles that carry a 'workforce' dict."""
    total = {k: 0.0 for k in _ROLLUP_KEYS}
    n = 0
    for r in roles:
        w = r.get("workforce")
        if not w:
            continue
        n += 1
        for k in _ROLLUP_KEYS:
            total[k] += _num(w.get(k))
    # round for display
    total = {k: round(v, 2) for k, v in total.items()}
    total["roles_with_data"] = n
    return total
