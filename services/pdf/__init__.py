"""Deloitte-branded PDF export package.

Split out of the former monolithic services/pdf_export.py (WO-05):
  base.py     — _DeloittePDF, colours, _safe, _ts, low-level render helpers
  sections.py — _write_role_section, _write_company_section
  builders.py — the 5 public build_* functions

services/pdf_export.py remains as a thin re-export shim for backwards compatibility.
"""
