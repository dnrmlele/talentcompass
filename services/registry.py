"""Registry-grounded company candidates via the GLEIF LEI API (WO-10b).

GLEIF (Global Legal Entity Identifier Foundation) publishes a free, no-auth API
of registered legal entities. Querying it gives AUTHORITATIVE candidate identities
for an ambiguous name — distinct legal entities sharing a name appear as separate
LEI records — instead of the LLM's best guess.

This is best-effort and fail-safe: any network/parse problem returns an empty list
so the caller falls back to the LLM disambiguation path. Uses only the stdlib
(urllib), so no new dependency. Disable entirely with env TC_USE_REGISTRY=0.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any

GLEIF_URL = "https://api.gleif.org/api/v1/lei-records"

# Market -> ISO country code used to scope the registry query.
_MARKET_COUNTRY = {"Luxembourg": "LU", "Belgium": "BE"}


def _registry_enabled() -> bool:
    return os.environ.get("TC_USE_REGISTRY", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def _http_get_json(url: str, timeout: float) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.api+json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec - fixed host
        return json.loads(resp.read().decode("utf-8"))


def parse_gleif(payload: dict[str, Any], country: str = "") -> list[dict[str, Any]]:
    """Map a GLEIF lei-records response into candidate dicts."""
    out: list[dict[str, Any]] = []
    for rec in (payload or {}).get("data", []) or []:
        attrs = rec.get("attributes", {}) or {}
        entity = attrs.get("entity", {}) or {}
        legal_name = (entity.get("legalName") or {}).get("name")
        if not legal_name:
            continue
        addr_country = (entity.get("legalAddress") or {}).get("country", "") or country
        category = entity.get("category") or entity.get("status") or ""
        lei = attrs.get("lei", "") or rec.get("id", "")
        desc = (
            f"Registered legal entity in {addr_country}."
            if addr_country
            else "Registered legal entity."
        )
        out.append(
            {
                "legal_name": legal_name,
                "sector": category or "",
                "description": desc,
                "hint": f"LEI {lei}" if lei else "",
                "source": "registry",
            }
        )
    return out


def registry_candidates(
    name: str, market: str = "", limit: int = 5, timeout: float = 6.0
) -> list[dict[str, Any]]:
    """Authoritative candidates for *name* from GLEIF, or [] on any problem."""
    if not _registry_enabled() or not (name or "").strip():
        return []
    country = _MARKET_COUNTRY.get(market, "")
    params = {"filter[fulltext]": name, "page[size]": str(limit)}
    if country:
        params["filter[entity.legalAddress.country]"] = country
    url = GLEIF_URL + "?" + urllib.parse.urlencode(params)
    try:
        payload = _http_get_json(url, timeout)
    except Exception:
        return []
    return parse_gleif(payload, country)
