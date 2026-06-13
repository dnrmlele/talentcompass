"""Tests for registry-grounded disambiguation (WO-10b)."""

from __future__ import annotations

import json
import types
from unittest.mock import patch

import services.registry as registry
import services.claude_client as cc

_SAMPLE = {
    "data": [
        {
            "id": "LEI-RETAIL",
            "attributes": {
                "lei": "LEI-RETAIL",
                "entity": {
                    "legalName": {"name": "Cactus S.A."},
                    "legalAddress": {"country": "LU"},
                    "category": "GENERAL",
                },
            },
        },
        {
            "attributes": {
                "lei": "LEI-FIN",
                "entity": {
                    "legalName": {"name": "Cactus Participations S.A."},
                    "legalAddress": {"country": "LU"},
                    "category": "FUND",
                },
            },
        },
        {"attributes": {"entity": {"legalName": {}}}},  # no name -> skipped
    ]
}


def test_parse_gleif_maps_records():
    out = registry.parse_gleif(_SAMPLE)
    assert [c["legal_name"] for c in out] == [
        "Cactus S.A.",
        "Cactus Participations S.A.",
    ]
    assert all(c["source"] == "registry" for c in out)
    assert out[0]["hint"] == "LEI LEI-RETAIL"


def test_registry_disabled_returns_empty(monkeypatch):
    monkeypatch.setenv("TC_USE_REGISTRY", "0")
    assert registry.registry_candidates("Cactus", "Luxembourg") == []


def test_registry_network_error_is_safe(monkeypatch):
    monkeypatch.delenv("TC_USE_REGISTRY", raising=False)
    with patch.object(registry, "_http_get_json", side_effect=OSError("offline")):
        assert registry.registry_candidates("Cactus", "Luxembourg") == []


def test_registry_success(monkeypatch):
    monkeypatch.delenv("TC_USE_REGISTRY", raising=False)
    with patch.object(registry, "_http_get_json", return_value=_SAMPLE):
        cands = registry.registry_candidates("Cactus", "Luxembourg")
    assert len(cands) == 2 and cands[1]["sector"] == "FUND"


def test_disambiguate_prefers_registry_no_llm_call(monkeypatch):
    monkeypatch.delenv("TC_USE_REGISTRY", raising=False)
    with patch.object(registry, "_http_get_json", return_value=_SAMPLE), patch.object(
        cc, "_call"
    ) as mock_call:
        out = cc.disambiguate_company("k", "Cactus", "Luxembourg")
    mock_call.assert_not_called()  # registry hit -> no LLM spend
    assert len(out["candidates"]) == 2
    assert out["candidates"][0]["source"] == "registry"


def test_disambiguate_falls_back_to_llm(monkeypatch):
    monkeypatch.delenv("TC_USE_REGISTRY", raising=False)
    llm_payload = json.dumps(
        {"candidates": [{"legal_name": "Cactus LLM", "sector": "Retail"}]}
    )

    def fake_call(*a, **k):
        return json.loads(llm_payload)

    with patch.object(
        registry, "_http_get_json", return_value={"data": []}
    ), patch.object(cc, "_call", side_effect=fake_call):
        out = cc.disambiguate_company("k", "Cactus", "Luxembourg")
    assert out["candidates"][0]["legal_name"] == "Cactus LLM"
    assert out["candidates"][0]["source"] == "llm"  # tagged by fallback
