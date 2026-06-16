"""Deterministic workforce & financial impact maths (WO-13, extended WO-16).

Unlike the LLM-generated automation_score (a judgement), these figures are plain
arithmetic on consultant-supplied headcount and fully-loaded cost. They are
defensible: same inputs always give the same numbers, and the formulas are
explicit below. The LLM only supplies weekly_hours_saved / automation_score /
fully_automatable_pct (basic path) and qualitative task ratings (workload path);
everything numeric is computed here.

Two layers share this module:

1. Basic impact (unchanged, weekly basis — kept byte-identical for back-compat):
     total_weekly_hours_freed = weekly_hours_saved_per_fte * headcount
     fte_freed                = min(headcount, total_weekly_hours_freed / 40)
     annual_payroll_savings   = fte_freed * loaded_cost
     transition_cost          = fte_freed * reskill_cost_per_fte
     net_annual_savings       = annual_payroll_savings - transition_cost
     displaced_fte            = headcount * fully_automatable_pct / 100
     severance_exposure       = displaced_fte * loaded_cost * severance_months / 12

2. Workload Impact engine (annual basis, adoption-aware, ST/MT, scenarios). Built
   only when an ``llm_workload`` dict (validated WorkloadImpact) is supplied. The
   LLM rates automation type + adoption factors per task; every hour/FTE/% here is
   computed. Reference standard: 1 FTE = 1,960 hours/year (Luxembourg). Note that
   1,960 = 40h x 49 working weeks, so the basic per-role FTE numbers above stay
   consistent with the annual model.
"""

from __future__ import annotations

from typing import Any

# ── Reference standards ──────────────────────────────────────────────────────
ANNUAL_FTE_HOURS = 1960.0  # Luxembourg standard — mandatory (WO-16)
FULL_WEEK_HOURS = 40.0     # legacy weekly basis (1960 = 40 * 49 working weeks)

# ── Automation model ─────────────────────────────────────────────────────────
AUTOMATION_TYPES = ("full", "ai_led", "human_led", "human_only")
AUTOMATION_TYPE_LABELS = {
    "full": "Full automation",
    "ai_led": "Augmentation (AI-led)",
    "human_led": "Augmentation (human-led)",
    "human_only": "Human-only",
}
# Removable fraction of task hours (theoretical), as (low, high) bands per spec.
AUTOMATION_BANDS = {
    "full": (1.0, 1.0),
    "ai_led": (0.40, 0.70),
    "human_led": (0.10, 0.30),
    "human_only": (0.0, 0.0),
}
# Mandatory minimum human-oversight floor: even fully-automatable work retains
# oversight, so realistic removal is capped at (1 - floor). Tunable default —
# validate with delivery. Set to 0.0 to treat full automation as 100% removable.
OVERSIGHT_FLOOR = 0.15

# ── Adoption model ───────────────────────────────────────────────────────────
# Adoption rate = min of the four factors (the bottleneck gates realism). All
# factors are framed so HIGH = most favourable to adoption, which keeps min()
# meaningful. Mapping to the spec's named factors:
#   tech_readiness        (spec: tech readiness)         High = tech is ready
#   change_readiness      (spec: change complexity)      High = change is easy
#   data_readiness        (spec: data readiness)         High = data is ready
#   regulatory_clearance  (spec: regulatory constraints) High = few blockers
ADOPTION_FACTORS = (
    "tech_readiness",
    "change_readiness",
    "data_readiness",
    "regulatory_clearance",
)
ADOPTION_FACTOR_LABELS = {
    "tech_readiness": "Tech readiness",
    "change_readiness": "Change readiness",
    "data_readiness": "Data readiness",
    "regulatory_clearance": "Regulatory clearance",
}
RATING_OPTIONS = ("High", "Medium", "Low")
RATING_PCT = {"High": 0.9, "Medium": 0.6, "Low": 0.3}
_DEFAULT_RATING = "Medium"

# ── Scenarios ────────────────────────────────────────────────────────────────
# Each scenario picks a band position and an adoption transition multiplier.
# Monotonic by construction: conservative <= realistic <= ambitious.
SCENARIOS = {
    "conservative": {"band": "low", "adoption_mult": 0.75},
    "realistic": {"band": "mid", "adoption_mult": 1.0},
    "ambitious": {"band": "high", "adoption_mult": 1.0},
}
SCENARIO_NAMES = ("conservative", "realistic", "ambitious")

# ── Role-level FTE classification (by % of role hours impacted) ───────────────
RELEASE_RISK_PCT = 80.0
REDUCTION_PCT = 30.0
CLASSIFICATION_LABELS = {
    "release_risk": "Release risk (>80% of hours impacted)",
    "reduction": "Reduction (30-80% of hours impacted)",
    "augmentation": "Augmentation (<30% of hours impacted)",
}
MIN_VIABLE_RESIDUAL_FTE = 0.5  # residual per incumbent below this -> redesign flag

# ── Luxembourg regulatory thresholds (DEFAULTS — validate with legal counsel) ─
LUX_STAFF_DELEGATION_MIN_HEADCOUNT = 15
LUX_COLLECTIVE_REDUNDANCY_30D = 7
LUX_COLLECTIVE_REDUNDANCY_90D = 15
HIGH_TRANSFORMATION_PCT = 50.0

# Keys that roll up additively across roles (basic layer).
_ROLLUP_KEYS = (
    "headcount",
    "fte_freed",
    "annual_payroll_savings",
    "transition_cost",
    "net_annual_savings",
    "displaced_fte",
    "severance_exposure",
)
# Workload-layer keys that also roll up additively (present only on workload roles).
_ROLLUP_KEYS_EXT = (
    "total_annual_hours",
    "hours_saved_st",
    "hours_saved_mt",
    "fte_saved_st",
    "fte_saved_mt",
    "annual_payroll_savings_mt",
)


def _num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ── Normalisation helpers ─────────────────────────────────────────────────────
def _norm_type(t: Any) -> str:
    """Map any automation-type label to one of AUTOMATION_TYPES.

    Unknown / blank defaults to 'human_only' (zero automation) — the conservative
    "do not overestimate" choice.
    """
    s = str(t or "").strip().lower().replace("-", "_").replace(" ", "_")
    if s in AUTOMATION_TYPES:
        return s
    if "full" in s:
        return "full"
    if "ai" in s and ("led" in s or "augment" in s):
        return "ai_led"
    if "human" in s and "led" in s:
        return "human_led"
    if "augment" in s:
        return "ai_led"
    if "human" in s:
        return "human_only"
    return "human_only"


def _norm_rating(r: Any) -> str:
    s = str(r or "").strip().lower()
    if s.startswith("h"):
        return "High"
    if s.startswith("l"):
        return "Low"
    if s.startswith("m"):
        return "Medium"
    return _DEFAULT_RATING


def _automation_rate(automation_type: Any, scenario: str = "realistic") -> float:
    """Realistic removable fraction for a task type under a scenario, capped by
    the human-oversight floor."""
    lo, hi = AUTOMATION_BANDS.get(_norm_type(automation_type), (0.0, 0.0))
    band = SCENARIOS.get(scenario, SCENARIOS["realistic"])["band"]
    rate = lo if band == "low" else hi if band == "high" else (lo + hi) / 2.0
    return min(rate, 1.0 - OVERSIGHT_FLOOR)


def _adoption_rate(factors: Any, scenario: str = "realistic") -> float:
    """Adoption = min of the (favourability-framed) factor percentages, scaled by
    the scenario's transition multiplier. Missing factors default to Medium."""
    factors = factors or {}
    vals = [RATING_PCT[_norm_rating(factors.get(k))] for k in ADOPTION_FACTORS]
    base = min(vals) if vals else 0.0
    mult = SCENARIOS.get(scenario, SCENARIOS["realistic"])["adoption_mult"]
    return max(0.0, min(1.0, base * mult))


def classify_role(pct_impacted: float) -> str:
    if pct_impacted >= RELEASE_RISK_PCT:
        return "release_risk"
    if pct_impacted >= REDUCTION_PCT:
        return "reduction"
    return "augmentation"


def regulatory_flags(
    headcount: int,
    fte_saved_mt: float,
    pct_impacted_mt: float,
    market: str = "Luxembourg",
) -> list[str]:
    """Luxembourg regulatory watch-flags. Worded as conditional ('if actioned')
    because this engine quantifies capacity only — it does not recommend actions.
    Thresholds are DEFAULTS; validate with legal counsel. Non-LU markets: none."""
    if market != "Luxembourg":
        return []
    flags: list[str] = []
    reduced = int(round(fte_saved_mt))
    if headcount >= LUX_STAFF_DELEGATION_MIN_HEADCOUNT and fte_saved_mt >= 1.0:
        flags.append(
            "Staff-delegation (delegation du personnel) consultation likely required "
            "before any capacity change is actioned (employers with >=15 staff). "
            "Validate with legal."
        )
    if reduced >= LUX_COLLECTIVE_REDUNDANCY_30D:
        flags.append(
            f"Freed capacity ~ {reduced} FTE approaches Luxembourg collective-redundancy "
            f"thresholds (>={LUX_COLLECTIVE_REDUNDANCY_30D} in 30 days / "
            f">={LUX_COLLECTIVE_REDUNDANCY_90D} in 90 days). A 'plan de maintien dans "
            "l'emploi' / social plan and ITM notification would apply IF realised as "
            "redundancies. Validate with legal."
        )
    if pct_impacted_mt >= HIGH_TRANSFORMATION_PCT:
        flags.append(
            f"High transformation ({pct_impacted_mt:.0f}% of role hours impacted) — "
            "reskilling / employability obligations apply. Validate with legal."
        )
    return flags


def _resolve_task(llm_task: dict, override: dict | None) -> dict:
    """Merge consultant overrides onto an LLM task rating (override wins)."""
    t = dict(llm_task or {})
    o = override or {}
    if o.get("automation_type"):
        t["automation_type"] = o["automation_type"]
    if o.get("time_allocation_pct") is not None:
        t["time_allocation_pct"] = o["time_allocation_pct"]
    for h in ("adoption_st", "adoption_mt"):
        if o.get(h):
            merged = dict(t.get(h) or {})
            merged.update(o[h])
            t[h] = merged
    return t


def _compute_tasks(
    headcount: int,
    llm_tasks: list[dict],
    overrides: dict | None,
    scenario: str,
) -> list[dict[str, Any]]:
    """Per-task hours baseline + hours saved (ST/MT) for one scenario."""
    overrides = overrides or {}
    rows: list[dict[str, Any]] = []
    for i, lt in enumerate(llm_tasks):
        t = _resolve_task(lt, overrides.get(i) or overrides.get(str(i)))
        atype = _norm_type(t.get("automation_type"))
        alloc = max(0.0, _num(t.get("time_allocation_pct")))
        task_hours = headcount * ANNUAL_FTE_HOURS * alloc / 100.0
        arate = _automation_rate(atype, scenario)
        adopt_st = _adoption_rate(t.get("adoption_st"), scenario)
        adopt_mt = _adoption_rate(t.get("adoption_mt"), scenario)
        saved_st = task_hours * arate * adopt_st
        saved_mt = task_hours * arate * adopt_mt
        rows.append(
            {
                "name": t.get("name") or f"Task {i + 1}",
                "process": t.get("process") or "",
                "automation_type": atype,
                "automation_type_label": AUTOMATION_TYPE_LABELS[atype],
                "criticality": t.get("criticality") or "",
                "time_allocation_pct": round(alloc, 1),
                "task_hours": round(task_hours, 0),
                "automation_rate": round(arate, 3),
                "adoption_st": round(adopt_st, 3),
                "adoption_mt": round(adopt_mt, 3),
                "hours_saved_st": round(saved_st, 0),
                "hours_saved_mt": round(saved_mt, 0),
                "residual_hours_mt": round(task_hours - saved_mt, 0),
                "residual_nature": t.get("residual_nature") or "",
                "secondary_impacts": t.get("secondary_impacts") or [],
                "confidence": _norm_rating(t.get("confidence")) if t.get("confidence") else "",
            }
        )
    return rows


def build_scenarios(
    headcount: int, llm_tasks: list[dict], overrides: dict | None = None
) -> dict[str, dict[str, float]]:
    """Conservative / realistic / ambitious hours & FTE saved (ST/MT)."""
    out: dict[str, dict[str, float]] = {}
    for sc in SCENARIO_NAMES:
        rows = _compute_tasks(headcount, llm_tasks, overrides, sc)
        hs_st = sum(r["hours_saved_st"] for r in rows)
        hs_mt = sum(r["hours_saved_mt"] for r in rows)
        out[sc] = {
            "hours_saved_st": round(hs_st, 0),
            "hours_saved_mt": round(hs_mt, 0),
            "fte_saved_st": round(hs_st / ANNUAL_FTE_HOURS, 2),
            "fte_saved_mt": round(hs_mt / ANNUAL_FTE_HOURS, 2),
        }
    return out


def compute_workforce_impact(
    role: dict[str, Any],
    headcount: Any,
    loaded_cost: Any,
    reskill_cost_per_fte: Any = 0.0,
    severance_months: Any = 3.0,
    llm_workload: dict[str, Any] | None = None,
    overrides: dict | None = None,
    scenario: str = "realistic",
    market: str = "Luxembourg",
) -> dict[str, Any]:
    """Compute FTE, payroll, transition and severance figures for one role.

    Basic path (llm_workload is None) returns the original 12-key dict, unchanged
    and byte-identical. When an ``llm_workload`` dict (validated WorkloadImpact) is
    supplied, the annual Workload Impact engine adds task-level hours, ST/MT FTE
    impact, scenarios, classification and regulatory flags on top.
    """
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

    result: dict[str, Any] = {
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

    if not llm_workload:
        return result

    # ── Workload Impact engine (annual basis) ────────────────────────────────
    llm_tasks = llm_workload.get("tasks") or []
    sc = scenario if scenario in SCENARIOS else "realistic"
    rows = _compute_tasks(headcount, llm_tasks, overrides, sc)

    total_annual_hours = headcount * ANNUAL_FTE_HOURS
    alloc_sum = sum(_num(t.get("time_allocation_pct")) for t in llm_tasks)
    variance_pct = alloc_sum - 100.0

    hs_st = round(sum(r["hours_saved_st"] for r in rows), 0)
    hs_mt = round(sum(r["hours_saved_mt"] for r in rows), 0)
    fte_st = hs_st / ANNUAL_FTE_HOURS
    fte_mt = hs_mt / ANNUAL_FTE_HOURS
    pct_st = (hs_st / total_annual_hours * 100.0) if total_annual_hours else 0.0
    pct_mt = (hs_mt / total_annual_hours * 100.0) if total_annual_hours else 0.0
    residual_fte_mt = (
        (total_annual_hours - hs_mt) / ANNUAL_FTE_HOURS if total_annual_hours else 0.0
    )
    residual_per_head = residual_fte_mt / headcount if headcount else 0.0

    # Process / function aggregation (Step 4). Process from the task rating if
    # present; function from the role's department.
    by_process: dict[str, float] = {}
    for r in rows:
        key = r["process"] or "Unassigned"
        by_process[key] = round(by_process.get(key, 0.0) + r["hours_saved_mt"], 0)
    by_function = {role.get("_dept") or "Unassigned": hs_mt}

    result.update(
        {
            "annual_fte_hours": ANNUAL_FTE_HOURS,
            "total_annual_hours": round(total_annual_hours, 0),
            "scenario": sc,
            "tasks": rows,
            "hours_saved_st": hs_st,
            "hours_saved_mt": hs_mt,
            "fte_saved_st": round(fte_st, 2),
            "fte_saved_mt": round(fte_mt, 2),
            "pct_workload_impacted_st": round(pct_st, 1),
            "pct_workload_impacted_mt": round(pct_mt, 1),
            "classification": classify_role(pct_mt),
            "residual_fte_mt": round(residual_fte_mt, 2),
            "residual_fte_per_head": round(residual_per_head, 2),
            "redesign_flag": bool(headcount) and residual_per_head < MIN_VIABLE_RESIDUAL_FTE,
            "annual_payroll_savings_mt": round(fte_mt * loaded_cost, 0),
            "scenarios": build_scenarios(headcount, llm_tasks, overrides),
            "by_process": by_process,
            "by_function": {k: round(v, 0) for k, v in by_function.items()},
            "regulatory_flags": regulatory_flags(headcount, fte_mt, pct_mt, market),
            "reconciliation": {
                "allocation_sum_pct": round(alloc_sum, 1),
                "variance_pct": round(variance_pct, 1),
                "reconciled": abs(variance_pct) <= 5.0,
            },
            # Qualitative passthrough from the LLM (labels / text only).
            "strategic_value": llm_workload.get("strategic_value") or "",
            "confidence": llm_workload.get("confidence") or "",
            "assumptions": llm_workload.get("assumptions") or [],
            "gaps": llm_workload.get("gaps") or [],
            "exec_summary": llm_workload.get("exec_summary") or [],
            "no_regret_moves": llm_workload.get("no_regret_moves") or [],
        }
    )
    return result


def rollup_workforce(roles: list[dict[str, Any]]) -> dict[str, Any]:
    """Sum workforce impact across all roles that carry a 'workforce' dict.

    Basic keys always roll up; the workload-layer keys (_ROLLUP_KEYS_EXT) are
    summed too and are 0 for roles that only have the basic impact."""
    total = {k: 0.0 for k in (_ROLLUP_KEYS + _ROLLUP_KEYS_EXT)}
    n = 0
    n_workload = 0
    for r in roles:
        w = r.get("workforce")
        if not w:
            continue
        n += 1
        if w.get("hours_saved_mt") is not None:
            n_workload += 1
        for k in (_ROLLUP_KEYS + _ROLLUP_KEYS_EXT):
            total[k] += _num(w.get(k))
    total = {k: round(v, 2) for k, v in total.items()}
    total["roles_with_data"] = n
    total["roles_with_workload"] = n_workload
    return total
