"""Public PDF builders. Each returns the finished document as bytes."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from services.pdf.base import (
    _DeloittePDF,
    _ts,
    _safe,
    _h,
    _cover,
    DTT_GREY,
    DTT_BLACK,
)
from services.pdf.sections import _write_role_section, _write_company_section


def build_roles_pdf(roles: list[dict[str, Any]]) -> bytes:
    pdf = _DeloittePDF(subtitle="Role automation analyses")
    # A multi-record export opens with a premium cover; a single record stays
    # compact (the single-role download delegates here with one item).
    if len(roles) > 1:
        _cover(
            pdf,
            "Session report",
            "Role Automation Analyses",
            "AI workforce intelligence across the roles assessed in this session.",
            [
                f"Generated  {_ts()}",
                f"{len(roles)} role analysis record(s)",
                "Deloitte Luxembourg",
            ],
        )
    pdf.add_page()
    pdf.set_y(28)
    pdf.set_font("OpenSans", "", 9)
    pdf.set_text_color(*DTT_GREY)
    pdf.multi_cell(
        0, 4, text=_safe(f"Generated: {_ts()}  -  {len(roles)} role analysis record(s)")
    )
    pdf.set_text_color(*DTT_BLACK)
    pdf.ln(2)
    for i, r in enumerate(roles, start=1):
        _write_role_section(pdf, r, index=i)
    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def build_companies_pdf(companies: list[dict[str, Any]]) -> bytes:
    pdf = _DeloittePDF(subtitle="Client research")
    if len(companies) > 1:
        _cover(
            pdf,
            "Session report",
            "Client Research",
            "Market intelligence and AI-transformation potential for the clients reviewed.",
            [
                f"Generated  {_ts()}",
                f"{len(companies)} client research record(s)",
                "Deloitte Luxembourg",
            ],
        )
    pdf.add_page()
    pdf.set_y(28)
    pdf.set_font("OpenSans", "", 9)
    pdf.set_text_color(*DTT_GREY)
    pdf.multi_cell(
        0,
        4,
        text=_safe(
            f"Generated: {_ts()}  -  {len(companies)} client research record(s)"
        ),
    )
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
    _cover(
        pdf,
        "Session report",
        "AI Workforce Intelligence",
        "A combined view of role automation analyses and client research from this session.",
        [
            f"Generated  {_ts()}",
            f"{len(roles)} role analysis record(s)  -  {len(companies)} client research record(s)",
            "Deloitte Luxembourg",
        ],
    )
    pdf.add_page()
    pdf.set_y(28)
    pdf.set_font("OpenSans", "", 9)
    pdf.set_text_color(*DTT_GREY)
    pdf.multi_cell(
        0,
        4,
        text=_safe(
            f"Generated: {_ts()}  -  Roles: {len(roles)}  -  Client studies: {len(companies)}"
        ),
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
