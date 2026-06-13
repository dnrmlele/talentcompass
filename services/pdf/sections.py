"""Per-record section writers for role analyses and company research."""

from __future__ import annotations

from typing import Any

from fpdf import FPDF

from services.pdf.base import _safe, _h, _subh, _body, _bullets


def _write_role_section(pdf: FPDF, r: dict[str, Any], index: int | None = None) -> None:
    prefix = f"Analysis {index}: " if index is not None else ""
    title = r.get("_title") or "Role"
    _h(pdf, f"{prefix}{title}", 14)

    meta = f"Client: {r.get('_client', 'N/A')}  |  Department: {r.get('_dept', 'N/A')}"
    pdf.set_x(pdf.l_margin)
    pdf.set_font("DejaVu", "", 9)
    _body(pdf, meta, 9)
    pdf.ln(1)

    pdf.set_x(pdf.l_margin)
    pdf.set_font("DejaVu", "B", 10)
    pdf.multi_cell(
        0,
        5,
        text=_safe(
            f"Automation score: {r.get('automation_score', 0)}%  |  "
            f"Hours saved / week: {r.get('weekly_hours_saved', 0)}  |  "
            f"Priority: {r.get('transformation_priority', '')}"
        ),
    )

    _subh(pdf, "Executive summary")
    _body(pdf, r.get("summary") or "")

    tasks = r.get("tasks") or []
    if tasks:
        _subh(pdf, "Task breakdown")
        for t in tasks[:25]:
            line = (
                f"{t.get('name', '')}  ({t.get('type', '')}  {t.get('score', 0)}%)  "
                f"{t.get('rationale', '')}"
            )
            _body(pdf, line, 9)

    agents = r.get("ai_agents") or []
    if agents:
        _subh(pdf, "Recommended AI agents")
        for a in agents[:12]:
            _body(
                pdf,
                f"{a.get('name', '')}: {a.get('description', '')}  "
                f"Handles: {a.get('handles', '')}  |  Saving: {a.get('time_saving', '')}",
                9,
            )

    resk = r.get("reskilling") or {}
    dev, ret = resk.get("develop") or [], resk.get("retain") or []
    if dev or ret:
        _subh(pdf, "Reskilling")
        if dev:
            pdf.set_font("DejaVu", "B", 9)
            _body(pdf, "Develop:", 9)
            _bullets(pdf, [str(x) for x in dev[:12]])
        if ret:
            pdf.set_font("DejaVu", "B", 9)
            _body(pdf, "Retain:", 9)
            _bullets(pdf, [str(x) for x in ret[:12]])

    roadmap = r.get("roadmap") or []
    if roadmap:
        _subh(pdf, "Transformation roadmap")
        for ph in roadmap:
            _body(
                pdf,
                f"{ph.get('phase', '')} ({ph.get('duration', '')}): {ph.get('title', '')}",
                9,
            )
            for it in ph.get("items") or []:
                _body(pdf, f"    - {it}", 9)

    risks = r.get("risks") or []
    if risks:
        _subh(pdf, "Risks & change")
        for risk in risks:
            _body(pdf, f"{risk.get('title', '')}", 9)
            for it in risk.get("items") or []:
                _body(pdf, f"    - {it}", 9)

    wf = r.get("workforce")
    if wf:
        _subh(pdf, "Workforce & financial impact (computed)")
        _body(
            pdf,
            f"Headcount: {wf.get('headcount', 0)}  |  "
            f"FTE freed: {wf.get('fte_freed', 0)}  |  "
            f"Displaced (fully-automatable): {wf.get('displaced_fte', 0)} FTE",
            9,
        )
        _body(
            pdf,
            f"Annual payroll savings: EUR {wf.get('annual_payroll_savings', 0):,.0f}  |  "
            f"Transition cost: EUR {wf.get('transition_cost', 0):,.0f}  |  "
            f"Net annual savings: EUR {wf.get('net_annual_savings', 0):,.0f}",
            9,
        )
        _body(
            pdf,
            f"Severance exposure ({wf.get('severance_months', 0):.0f} months basis): "
            f"EUR {wf.get('severance_exposure', 0):,.0f}",
            9,
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
    prefix = f"Research {index}: " if index is not None else ""
    _h(pdf, f"{prefix}{name}", 14)

    pdf.set_font("DejaVu", "", 9)
    _body(
        pdf,
        f"{prof.get('inferred_industry', '')}  |  {prof.get('inferred_size', '')}",
        9,
    )

    pdf.set_font("DejaVu", "B", 10)
    _body(
        pdf,
        f"AI potential: {r.get('ai_potential_score', 0)}/100  -  {r.get('ai_potential_label', '')}",
        10,
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
            _body(
                pdf,
                f"{o.get('area', '')} [{o.get('priority', '')}]: {o.get('opportunity', '')}  "
                f"Impact: {o.get('estimated_impact', '')}",
                9,
            )

    risks = r.get("risks_and_barriers") or []
    if risks:
        _subh(pdf, "Risks & barriers")
        for x in risks[:10]:
            _body(pdf, f"{x.get('risk', '')}: {x.get('description', '')}", 9)
            _body(pdf, f"Mitigation: {x.get('mitigation', '')}", 9)

    strat = r.get("recommended_ai_strategy") or {}
    if strat:
        _subh(pdf, "Recommended AI strategy")
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
