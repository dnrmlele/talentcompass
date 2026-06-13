"""Tests for company entity disambiguation (WO-10)."""

from __future__ import annotations

from services.prompts import disambiguation_prompt, DISAMBIG_SYSTEM
from services.schemas import CompanyCandidates


def test_prompt_embeds_name_and_market():
    p = disambiguation_prompt("Cactus", market="Luxembourg")
    assert "Cactus" in p
    assert "Luxembourg" in p
    assert "candidates" in p


def test_prompt_market_aware_belgium():
    p = disambiguation_prompt("KBC", market="Belgium")
    assert "Belgium" in p
    assert "Luxembourg" not in p


def test_system_prompt_demands_json():
    assert "JSON" in DISAMBIG_SYSTEM


def test_schema_defaults_to_empty_candidates():
    out = CompanyCandidates.model_validate({}).model_dump()
    assert out["candidates"] == []


def test_schema_parses_candidates_and_fills_missing_fields():
    out = CompanyCandidates.model_validate(
        {"candidates": [{"legal_name": "Cactus S.A.", "sector": "Retail"}]}
    ).model_dump()
    c = out["candidates"][0]
    assert c["legal_name"] == "Cactus S.A."
    assert c["sector"] == "Retail"
    assert c["description"] is None and c["hint"] is None
