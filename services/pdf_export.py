"""Backwards-compatible shim for the Deloitte-branded PDF export.

The implementation moved into the services/pdf package (WO-05). This module
re-exports the public builders and a few helpers so existing imports such as
``from services.pdf_export import build_combined_pdf`` keep working unchanged.

Note: the byte-determinism freeze fixture in tests patches the symbols where the
builders actually resolve them (services.pdf.builders._ts / ._DeloittePDF), not
this shim — re-exporting here would not affect the builders' own namespace.
"""

from __future__ import annotations

from services.pdf.base import _safe, _ts, _DeloittePDF
from services.pdf.builders import (
    build_roles_pdf,
    build_companies_pdf,
    build_combined_pdf,
    build_single_role_pdf,
    build_single_company_pdf,
)

__all__ = [
    "_safe",
    "_ts",
    "_DeloittePDF",
    "build_roles_pdf",
    "build_companies_pdf",
    "build_combined_pdf",
    "build_single_role_pdf",
    "build_single_company_pdf",
]
