"""Deloitte-branded PDF export for TalentCompass session results."""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from fpdf import FPDF

DTT_GREEN   = (134, 188, 37)
DTT_BLACK   = (26, 26, 26)
DTT_GREY    = (100, 100, 100)
DTT_HEADING = (74, 110, 30)

_FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def _root() -> Path:
    return Path(__file__).resolve().parent.parent


def _logo_path() -> Path | None:
    p = _root() / "Logo_of_Deloitte.svg.png"
    return p if p.is_file() else None


# ── Unicode safety ─────────────────────────────────────────────────────────────
def _safe(text: Any) -> str:
    """Normalise text to something DejaVu can always render."""
    if text is None:
        return ""
    text = str(text)
    replacements = {
        "\u2014": "--",   # em dash  —
        "\u2013": "-",    # en dash  –
        "\u2018": "'",    # left single quote
        "\u2019": "'",    # right single quote
        "\u201C": '"',    # left double quote
        "\u201D": '"',    # right double quote
        "\u2026": "...",  # ellipsis
        "\u2022": "-",    # bullet
        "\u00A0": " ",    # non-breaking space
        "\u00B7": ".",    # middle dot
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    # Final fallback: drop anything outside BMP that DejaVu can't handle
    return text.encode("utf-8", errors="ignore").decode("utf-8")


# ── Base PDF class ─────────────────────────────────────────────────────────────
class _DeloittePDF(FPDF):
    def __init__(self, subtitle: str = ""):
        super().__init__(orientation="P", unit="mm", format="A4")
        # Register DejaVu — full Unicode support
        self.add_font("DejaVu",  "",  str(_FONT_DIR / "DejaVuSans.ttf"))
        self.add_font("DejaVu",  "B", str(_FONT_DIR / "DejaVuSans-Bold.ttf"))
        self._logo = _logo_path()
        self._subtitle = subtitle
        self.set_auto_page_break(auto=True, margin=14)
        self.set_margins(16, 32, 16)

    def header(self) -> None:
        self.set_fill_color(*DTT_GREEN)
        self.rect(0, 0, self.w, 22, style="F")
        self.set_xy(14, 5)
        self.set_font("DejaVu", "B", 15)
        self.set_text_color(255, 255, 255)
        self.cell(0, 7, _safe("TALENTCOMPASS"), ln=1)
        self.set_x(14)
        self.set_font("DejaVu", "", 9)
        line = "AI Workforce Intelligence  -  Deloitte Luxembourg"
        if self._subtitle:
            line = f"{line}  -  {self._subtitle}"
        self.cell(0, 5, _safe(line), ln=1)
        if self._logo:
            try:
                self.image(str(self._logo), x=self.w - 48, y=3, w=36)
            except Exception:
                pass
        self.set_text_color(*DTT_BLACK)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(*DTT_GREY)
        self.cell(0, 4, _safe("Confidential  -  Deloitte Luxembourg  -  Session export"), align="C", ln=1)
        self.cell(0, 4, _safe(f"Page {self.page_no()}"), align="C", ln=0)
        self.set_text_color(*DTT_BLACK)


# ── Timestamp ──────────────────────────────────────────────────────────────────
def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ── Low-level rendering helpers ────────────────────────────────────────────────
def _body(pdf: FPDF, text: Any, size: int = 10) -> None:
    if not text:
        return
    pdf.set_x(pdf.l_margin)
    pdf.set_font("DejaVu", "", size)
    pdf.set_text_color(*DTT_BLACK)
    pdf.multi_cell(0, 5.2, text=_safe(text))


def _h(pdf: FPDF, title: Any, size: int = 13) -> None:
    pdf.ln(3)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("DejaVu", "B", size)
    pdf.set_text_color(*DTT_HEADING)
    pdf.multi_cell(0, 6, text=_safe(title))
    pdf.set_text_color(*DTT_BLACK)


def _subh(pdf: FPDF, title: Any) -> None:
    pdf.ln(1)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("DejaVu", "B", 10)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 5, text=_safe(title))
    pdf.set_text_color(*DTT_BLACK)


def _bullets(pdf: FPDF, items: list[str]) -> None:
    pdf.set_font("DejaVu", "", 9)
    for it in items:
        if not it:
            continue
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 4.8, text=_safe(f"  -  {it}"))


# ── Section writers ────────────────────────────────────────────────────────────
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
        0, 5,
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
            _body(pdf, f"{ph.get('phase', '')} ({ph.get('duration', '')}): {ph.get('title', '')}", 9)
            for it in ph.get("items") or []:
                _body(pdf, f"    - {it}", 9)

    risks = r.get("risks") or []
    if risks:
        _subh(pdf, "Risks & change")
        for risk in risks:
            _body(pdf, f"{risk.get('title', '')}", 9)
            for it in risk.get("items") or []:
                _body(pdf, f"    - {it}", 9)

    pdf.ln(2)


def _write_company_section(pdf: FPDF, r: dict[str, Any], index: int | None = None) -> None:
    prof = r.get("company_profile") or {}
    name = prof.get("name") or "Company"
    prefix = f"Research {index}: " if index is not None else ""
    _h(pdf, f"{prefix}{name}", 14)

    pdf.set_font("DejaVu", "", 9)
    _body(pdf, f"{prof.get('inferred_industry', '')}  |  {prof.get('inferred_size', '')}", 9)

    pdf.set_font("DejaVu", "B", 10)
    _body(pdf, f"AI potential: {r.get('ai_potential_score', 0)}/100  -  {r.get('ai_potential_label', '')}", 10)

    _subh(pdf, "AI potential summary")
    _body(pdf, r.get("ai_potential_summary") or "")

    _subh(pdf, "Luxembourg & regulatory")
    _body(pdf, f"Presence: {prof.get('luxembourg_presence', '')}", 9)
    _body(pdf, f"Regulatory: {prof.get('regulatory_context', '')}", 9)

    trends = r.get("industry_ai_trends") or []
    if trends:
        _subh(pdf, "Industry AI trends")
        for tr in trends[:10]:
            _body(pdf, f"{tr.get('trend', '')} ({tr.get('impact', '')}, {tr.get('timeline', '')})", 9)
            _body(pdf, tr.get("description") or "", 9)

    comp = r.get("competitor_moves") or []
    if comp:
        _subh(pdf, "Competitor moves")
        for c in comp[:10]:
            _body(pdf, f"{c.get('competitor', '')} ({c.get('threat_level', '')}): {c.get('move', '')}", 9)

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


# ── Public builders ────────────────────────────────────────────────────────────
def build_roles_pdf(roles: list[dict[str, Any]]) -> bytes:
    pdf = _DeloittePDF(subtitle="Role automation analyses")
    pdf.add_page()
    pdf.set_y(28)
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(*DTT_GREY)
    pdf.multi_cell(0, 4, text=_safe(f"Generated: {_ts()}  -  {len(roles)} role analysis record(s)"))
    pdf.set_text_color(*DTT_BLACK)
    pdf.ln(2)
    for i, r in enumerate(roles, start=1):
        _write_role_section(pdf, r, index=i)
    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def build_companies_pdf(companies: list[dict[str, Any]]) -> bytes:
    pdf = _DeloittePDF(subtitle="Client research")
    pdf.add_page()
    pdf.set_y(28)
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(*DTT_GREY)
    pdf.multi_cell(0, 4, text=_safe(f"Generated: {_ts()}  -  {len(companies)} client research record(s)"))
    pdf.set_text_color(*DTT_BLACK)
    pdf.ln(2)
    for i, r in enumerate(companies, start=1):
        _write_company_section(pdf, r, index=i)
    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def build_combined_pdf(
    roles: list[dict[str, Any]],
    companies: list[dict[str, Any]],
) -> bytes:
    pdf = _DeloittePDF(subtitle="Full session report")
    pdf.add_page()
    pdf.set_y(28)
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(*DTT_GREY)
    pdf.multi_cell(
        0, 4,
        text=_safe(f"Generated: {_ts()}  -  Roles: {len(roles)}  -  Client studies: {len(companies)}"),
    )
    pdf.set_text_color(*DTT_BLACK)
    pdf.ln(3)
    if roles:
        _h(pdf, "Part A  -  Role automation analyses", 15)
        for i, r in enumerate(roles, start=1):
            _write_role_section(pdf, r, index=i)
    if companies:
        _h(pdf, "Part B  -  Client research", 15)
        for i, r in enumerate(companies, start=1):
            _write_company_section(pdf, r, index=i)
    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def build_single_role_pdf(role: dict[str, Any]) -> bytes:
    return build_roles_pdf([role])


def build_single_company_pdf(company: dict[str, Any]) -> bytes:
    return build_companies_pdf([company])