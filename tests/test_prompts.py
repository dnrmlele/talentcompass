"""Tests for services.prompts: prompt builders embed inputs; system prompts demand JSON."""

from services.prompts import (
    COMPANY_SYSTEM,
    ROLE_SYSTEM,
    company_prompt,
    role_prompt,
)


def test_role_prompt_embeds_inputs_verbatim():
    p = role_prompt(
        job_title="Fund Accountant",
        department="Operations",
        company_size="Enterprise",
        job_description="Reconcile NAV daily and produce investor statements.",
    )
    assert "Fund Accountant" in p
    assert "Operations" in p
    assert "Enterprise" in p
    assert "Reconcile NAV daily and produce investor statements." in p


def test_role_prompt_client_clause():
    with_client = role_prompt("Analyst", "Finance", "SME", "desc", client_name="Acme")
    assert "Acme" in with_client
    assert "(Luxembourg market)" in with_client

    without_client = role_prompt("Analyst", "Finance", "SME", "desc")
    assert "Acme" not in without_client
    assert "(Luxembourg market)" not in without_client


def test_company_prompt_embeds_name_and_industry():
    known = company_prompt("Clearstream", "Banking")
    assert "Clearstream" in known
    assert "Known industry: Banking." in known

    inferred = company_prompt("Clearstream")
    assert "Clearstream" in inferred
    assert "Infer industry" in inferred
    assert "Known industry:" not in inferred


def test_system_prompts_demand_json_only():
    for system in (ROLE_SYSTEM, COMPANY_SYSTEM):
        assert "valid, parseable JSON only" in system
        assert "no markdown" in system
