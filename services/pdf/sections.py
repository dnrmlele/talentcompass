"""Per-record section writers for role analyses and company research.

These build on the visual toolkit in ``services.pdf.base`` (KPI tiles, donut
gauge, meter and horizontal bar charts) so each record reads as a branded
one-pager rather than a wall of text. Every visual block stays guarded by the
data key that feeds it, so records lacking a key render identically to before
that block existed -- which keeps the golden PDF tests stable.
"""

from __future__ import annotations

from typing import Any

from fpdf import FPDF

from services.pdf.base import (
    _safe,
    _need,
    _record_title,
    _subh,
    _body,
    _bullets,
    _kpi_tiles,
    _meter,
    _hbar_chart,
    _gauge,
    _cat_color,
    DTT_GREEN,
    DTT_BLUE,
    DTT_DARKGREEN,
    DTT_SLATE,
)


def _eur(v: Any) -> str:
    try:
        return f"EUR {float(v):,.0f}"
    except (TypeError, ValueError):
        return "EUR 0"


def _write_role_section(pdf: FPDF, r: dict[str, Any], index: int | None = None) -> None:
    eyebrow = f"Role analysis {index}" if index is not None else "Role analysis"
    title = r.get("_title") or "Role"
    _record_title(pdf, eyebrow, title)

    _body(
        pdf,
        f"Client: {r.get('_client', 'N/A')}   |   Department: {r.get('_dept', 'N/A')}",
        9,
    )
    pdf.ln(1)

    # Headline KPIs as visual tiles.
    _kpi_tiles(
        pdf,
        [
            (f"{r.get('automation_score', 0)}%", "Automation potential"),
            (f"{r.get('weekly_hours_saved', 0)} h", "Hours saved / week"),
            (str(r.get("transformation_priority", "") or "-"), "Transformation priority"),
        ],
    )
    pdf.ln(1)

    _subh(pdf, "Executive summary")
    _body(pdf, r.get("summary") or "")

    tasks = r.get("tasks") or []
    if tasks:
        # Keep the heading with at least the first few bars on one page.
        _need(pdf, min(230, 16 + min(len(tasks), 14) * 10.8))
        _subh(pdf, "Task breakdown (automation potential per task)")
        rows = []
        for t in tasks[:14]:
            name = t.get("name", "")
            ttype = t.get("type", "")
            label = f"{name}  ({ttype})" if ttype else name
            rows.append((label, t.get("score", 0) or 0, _cat_color(ttype)))
        _hbar_chart(pdf, rows, unit="%", maxv=100)

    agents = r.get("ai_agents") or []
    if agents:
        _subh(pdf, "Recommended AI agents")
        for a in agents[:12]:
            pdf.set_font("OpenSans", "B", 9)
            _body(pdf, a.get("name", ""), 9)
            _body(
                pdf,
                f"{a.get('description', '')}  Handles: {a.get('handles', '')}  |  "
                f"Saving: {a.get('time_saving', '')}",
                9,
            )

    resk = r.get("reskilling") or {}
    dev, ret = resk.get("develop") or [], resk.get("retain") or []
    if dev or ret:
        _subh(pdf, "Reskilling")
        if dev:
            pdf.set_font("OpenSans", "B", 9)
            _body(pdf, "Develop:", 9)
            _bullets(pdf, [str(x) for x in dev[:12]])
        if ret:
            pdf.set_font("OpenSans", "B", 9)
            _body(pdf, "Retain:", 9)
            _bullets(pdf, [str(x) for x in ret[:12]])

    roadmap = r.get("roadmap") or []
    if roadmap:
        _subh(pdf, "Transformation roadmap")
        for ph in roadmap:
            pdf.set_font("OpenSans", "B", 9)
            _body(
                pdf,
                f"{ph.get('phase', '')} ({ph.get('duration', '')}): {ph.get('title', '')}",
                9,
            )
            _bullets(pdf, [str(it) for it in (ph.get("items") or [])])

    risks = r.get("risks") or []
    if risks:
        _subh(pdf, "Risks & change")
        for risk in risks:
            pdf.set_font("OpenSans", "B", 9)
            _body(pdf, f"{risk.get('title', '')}", 9)
            _bullets(pdf, [str(it) for it in (risk.get("items") or [])])

    wf = r.get("workforce")
    if wf:
        # Keep tiles + the 4 financial bars together with their heading.
        _need(pdf, 78)
        _subh(pdf, "Workforce & financial impact (computed)")
        _kpi_tiles(
            pdf,
            [
                (str(wf.get("headcount", 0)), "Headcount"),
                (f"{wf.get('fte_freed', 0)}", "FTE freed"),
                (f"{wf.get('displaced_fte', 0)}", "Displaced FTE"),
            ],
        )
        pdf.ln(1)
        _hbar_chart(
            pdf,
            [
                ("Annual payroll savings", wf.get("annual_payroll_savings", 0) or 0, DTT_GREEN),
                ("Transition cost", wf.get("transition_cost", 0) or 0, DTT_BLUE),
                ("Net annual savings", wf.get("net_annual_savings", 0) or 0, DTT_DARKGREEN),
                (
                    f"Severance exposure ({wf.get('severance_months', 0):.0f} mo basis)",
                    wf.get("severance_exposure", 0) or 0,
                    DTT_SLATE,
                ),
            ],
            fmt=_eur,
        )

    adv = r.get("hr_advisory")
    if adv:
        _subh(pdf, "HR management & advisory")
        if adv.get("summary"):
            _body(pdf, adv["summary"], 9)
        if adv.get("redeployment_options"):
            _body(pdf, "Redeployment options:", 9)
            for o in adv["redeployment_options"]:
                _body(
                    pdf,
                    f"    - {o.get('option', '')} ({o.get('effort', '')}): {o.get('description', '')}",
                    9,
                )
        if adv.get("reskilling_focus"):
            _body(pdf, "Reskilling focus:", 9)
            _bullets(pdf, [str(s) for s in adv["reskilling_focus"]])
        if adv.get("retention_priorities"):
            _body(pdf, "Retention priorities:", 9)
            for p in adv["retention_priorities"]:
                _body(
                    pdf,
                    f"    - {p.get('group', '')}: {p.get('reason', '')} -> {p.get('action', '')}",
                    9,
                )
        if adv.get("change_management"):
            _body(pdf, "Change management:", 9)
            for step in adv["change_management"]:
                _body(pdf, f"    {step.get('phase', '')}", 9)
                for a in step.get("actions") or []:
                    _body(pdf, f"        - {a}", 9)
        if adv.get("workforce_planning"):
            _body(pdf, "Workforce planning:", 9)
            _bullets(pdf, [str(s) for s in adv["workforce_planning"]])
        if adv.get("hr_risks"):
            _body(pdf, "HR risks:", 9)
            for hr in adv["hr_risks"]:
                _body(
                    pdf,
                    f"    - {hr.get('risk', '')} -> {hr.get('mitigation', '')}",
                    9,
                )

    pdf.ln(2)


def _write_company_section(
    pdf: FPDF, r: dict[str, Any], index: int | None = None
) -> None:
    prof = r.get("company_profile") or {}
    name = prof.get("name") or "Company"
    eyebrow = f"Client research {index}" if index is not None else "Client research"
    _record_title(pdf, eyebrow, name)

    _body(
        pdf,
        f"{prof.get('inferred_industry', '')}   |   {prof.get('inferred_size', '')}",
        9,
    )
    pdf.ln(1)

    # AI potential as a donut gauge with the label alongside.
    _gauge(
        pdf,
        r.get("ai_potential_score", 0) or 0,
        r.get("ai_potential_label", "") or "AI potential",
        maxv=100,
        suffix="/100",
    )

    _subh(pdf, "AI potential summary")
    _body(pdf, r.get("ai_potential_summary") or "")

    _subh(pdf, "Luxembourg & regulatory")
    _body(pdf, f"Presence: {prof.get('luxembourg_presence', '')}", 9)
    _body(pdf, f"Regulatory: {prof.get('regulatory_context', '')}", 9)

    trends = r.get("industry_ai_trends") or []
    if trends:
        _subh(pdf, "Industry AI trends")
        for tr in trends[:10]:
            pdf.set_font("OpenSans", "B", 9)
            _body(
                pdf,
                f"{tr.get('trend', '')} ({tr.get('impact', '')}, {tr.get('timeline', '')})",
                9,
            )
            _body(pdf, tr.get("description") or "", 9)

    comp = r.get("competitor_moves") or []
    if comp:
        _subh(pdf, "Competitor moves")
        for c in comp[:10]:
            _body(
                pdf,
                f"{c.get('competitor', '')} ({c.get('threat_level', '')}): {c.get('move', '')}",
                9,
            )

    opps = r.get("key_ai_opportunities") or []
    if opps:
        _subh(pdf, "Key AI opportunities")
        for o in opps[:12]:
            pdf.set_font("OpenSans", "B", 9)
            _body(
                pdf,
                f"{o.get('area', '')} [{o.get('priority', '')}]",
                9,
            )
            _body(
                pdf,
                f"{o.get('opportunity', '')}  Impact: {o.get('estimated_impact', '')}",
                9,
            )

    risks = r.get("risks_and_barriers") or []
    if risks:
        _subh(pdf, "Risks & barriers")
        for x in risks[:10]:
            pdf.set_font("OpenSans", "B", 9)
            _body(pdf, f"{x.get('risk', '')}", 9)
            _body(pdf, f"{x.get('description', '')}", 9)
            _body(pdf, f"Mitigation: {x.get('mitigation', '')}", 9)

    strat = r.get("recommended_ai_strategy") or {}
    if strat:
        _subh(pdf, "Recommended AI strategy")
        pdf.set_font("OpenSans", "B", 9)
        _body(pdf, strat.get("headline") or "", 9)
        _body(pdf, strat.get("approach") or "", 9)
        if strat.get("quick_wins"):
            _body(pdf, "Quick wins:", 9)
            _bullets(pdf, [str(x) for x in strat.get("quick_wins", [])])
        if strat.get("strategic_bets"):
            _body(pdf, "Strategic bets:", 9)
            _bullets(pdf, [str(x) for x in strat.get("strategic_bets", [])])

    if r.get("deloitte_angle"):
        _subh(pdf, "Deloitte engagement angle")
        _body(pdf, r.get("deloitte_angle") or "")

    pdf.ln(2)
