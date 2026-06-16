"""Golden-checksum tests for the five public PDF builders.

Each test builds a PDF from the shared fixtures, asserts the output is non-empty
bytes starting with b"%PDF", then compares (or seeds) a sha256 golden via the
_check_or_update helper from conftest. The autouse _freeze_pdf_clock fixture pins
both nondeterminism sources so the bytes are reproducible.

Seed/regenerate goldens:
    UPDATE_GOLDEN=1 py -3.13 -m pytest tests/test_pdf_builders.py
"""

from services.pdf_export import (
    build_combined_pdf,
    build_companies_pdf,
    build_roles_pdf,
    build_single_company_pdf,
    build_single_role_pdf,
)

from .conftest import _check_or_update


def _assert_pdf(data: bytes) -> None:
    assert isinstance(data, bytes)
    assert len(data) > 0
    assert data[:4] == b"%PDF"


def test_build_single_role_pdf(role):
    data = build_single_role_pdf(role)
    _assert_pdf(data)
    _check_or_update("build_single_role_pdf", data)


def test_build_roles_pdf(role, role2):
    data = build_roles_pdf([role, role2])
    _assert_pdf(data)
    _check_or_update("build_roles_pdf", data)


def test_build_single_role_pdf_workload(role_workload):
    # Exercises the Workload Impact PDF block (annual basis, scenarios, flags).
    data = build_single_role_pdf(role_workload)
    _assert_pdf(data)
    _check_or_update("build_single_role_pdf_workload", data)


def test_build_single_company_pdf(company):
    data = build_single_company_pdf(company)
    _assert_pdf(data)
    _check_or_update("build_single_company_pdf", data)


def test_build_companies_pdf(company, company2):
    data = build_companies_pdf([company, company2])
    _assert_pdf(data)
    _check_or_update("build_companies_pdf", data)


def test_build_combined_pdf(role, company):
    data = build_combined_pdf([role], [company])
    _assert_pdf(data)
    _check_or_update("build_combined_pdf", data)
