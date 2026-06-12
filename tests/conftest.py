"""Shared fixtures for the WO-04 unit suite.

Provides:
  * an autouse determinism-freeze fixture that pins both nondeterminism sources
    in services.pdf_export so PDF byte output is reproducible run-to-run, and
  * realistic ROLE / COMPANY fixture dicts consumed by the section writers.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

# WO-05 split the PDF monolith into a package. The builders now live in
# services.pdf.builders and resolve _ts / _DeloittePDF in THAT module's
# namespace, so the freeze must patch there — patching the services.pdf_export
# shim would not reach the builders' own globals.
import services.pdf.builders as pdf_builders

# ── Frozen clock values ─────────────────────────────────────────────────────────
_FIXED_TS = "2026-01-01 00:00 UTC"
_FIXED_CREATION = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _freeze_pdf_clock(monkeypatch):
    """Make PDF builders byte-deterministic WITHOUT touching production code.

    Two independent nondeterminism sources must both be pinned:
      (a) _ts() -> datetime.now(...) stamped into visible text (called in builders).
      (b) fpdf2 FPDF.__init__ sets self.creation_date = datetime.now(utc); that value
          feeds BOTH the /CreationDate Info entry and the /ID md5 (via _default_file_id).
    Patch targets are in services.pdf.builders — the module where the builders
    look these names up at call time.
    """
    # (a) freeze the visible 'Generated:' timestamp.
    monkeypatch.setattr(pdf_builders, "_ts", lambda: _FIXED_TS)

    # (b) freeze fpdf creation_date by subclassing the class the builders instantiate.
    _Orig = pdf_builders._DeloittePDF

    class _FrozenDeloittePDF(_Orig):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.creation_date = _FIXED_CREATION

    monkeypatch.setattr(pdf_builders, "_DeloittePDF", _FrozenDeloittePDF)
    yield


# ── Golden checksum helper ──────────────────────────────────────────────────────
GOLDEN = Path(__file__).parent / "golden" / "checksums.json"


def _check_or_update(key: str, data: bytes) -> None:
    """Assert the sha256 of *data* matches the stored golden, or (re)seed it.

    With UPDATE_GOLDEN=1 in the environment, the golden file is regenerated.
    Otherwise the digest is asserted equal to the stored value.
    """
    digest = hashlib.sha256(data).hexdigest()
    update = os.environ.get("UPDATE_GOLDEN") == "1"
    golden = json.loads(GOLDEN.read_text()) if GOLDEN.exists() else {}
    if update:
        golden[key] = digest
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(golden, indent=2, sort_keys=True) + "\n")
    else:
        assert key in golden, f"No golden for {key}; run UPDATE_GOLDEN=1 pytest"
        assert digest == golden[key], f"{key} PDF bytes changed vs golden"


# ── Realistic fixture dicts ─────────────────────────────────────────────────────
@pytest.fixture
def role() -> dict:
    return {
        "_title": "Fund Accountant",
        "_client": "Acme Fund Services",
        "_dept": "Operations",
        "automation_score": 62,
        "weekly_hours_saved": 14,
        "transformation_priority": "High",
        # em dash, curly quotes, non-BMP emoji -> exercises _safe inside the golden.
        "summary": "Reconciles NAV — “core” duty \U0001f680 daily.",
        "tasks": [
            {
                "name": "NAV reconciliation",
                "type": "AI-Augmented",
                "score": 70,
                "rationale": "Rule-based matching dominates.",
            },
            {
                "name": "Investor relations",
                "type": "Human-Only",
                "score": 10,
                "rationale": "Requires judgement.",
            },
        ],
        "ai_agents": [
            {
                "name": "ReconBot",
                "icon": "\U0001f4b0",
                "description": "Auto-matches ledgers.",
                "handles": "NAV reconciliation",
                "time_saving": "↓ 80% time",
                "setup_complexity": "Medium",
            },
        ],
        "reskilling": {
            "develop": ["Python", "Data viz"],
            "retain": ["Domain expertise"],
        },
        "roadmap": [
            {
                "phase": "Phase 1",
                "duration": "0-3 months",
                "title": "Pilot",
                "items": ["Map tasks", "Select tooling"],
            },
        ],
        "risks": [
            {
                "title": "Change resistance",
                "color_key": "change",
                "items": ["Stakeholder workshops", "Phased rollout"],
            },
        ],
    }


@pytest.fixture
def role2(role) -> dict:
    r = dict(role)
    r["_title"] = "Compliance Officer"
    r["_dept"] = "Risk"
    return r


@pytest.fixture
def company() -> dict:
    return {
        "company_profile": {
            "name": "Clearstream",
            "inferred_industry": "Fund administration",
            "inferred_size": "Large enterprise",
            "luxembourg_presence": "Major post-trade hub in Luxembourg.",
            "regulatory_context": "CSSF, CNPD, AIFMD",
        },
        "ai_potential_score": 78,
        "ai_potential_label": "High Transformation Potential",
        "ai_potential_summary": "Strong AI fit across settlement — see below.",
        "industry_ai_trends": [
            {
                "trend": "Doc automation",
                "impact": "High",
                "timeline": "Now",
                "description": "LLMs parse prospectuses. Cuts manual review.",
            },
        ],
        "competitor_moves": [
            {
                "competitor": "Euroclear",
                "threat_level": "Medium",
                "move": "Piloting AI reconciliation.",
            },
        ],
        "key_ai_opportunities": [
            {
                "area": "Settlement",
                "priority": "Quick Win",
                "opportunity": "Exception triage",
                "estimated_impact": "30% fewer breaks",
            },
        ],
        "risks_and_barriers": [
            {
                "risk": "Data residency",
                "description": "EU constraints.",
                "mitigation": "On-prem inference.",
            },
        ],
        "recommended_ai_strategy": {
            "headline": "Automate the back office",
            "approach": "Start with reconciliation. Expand to KYC. Govern centrally.",
            "quick_wins": ["Exception triage", "Doc parsing"],
            "strategic_bets": ["Agentic settlement"],
        },
        "deloitte_angle": "Deloitte can run a 6-week AI readiness sprint.",
    }


@pytest.fixture
def company2(company) -> dict:
    c = dict(company)
    prof = dict(company["company_profile"])
    prof["name"] = "Euroclear"
    c["company_profile"] = prof
    return c
