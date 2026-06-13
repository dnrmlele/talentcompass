"""Pydantic schemas for Claude API responses.

Mirrors the exact JSON structures requested in services/prompts.py
(role_prompt and company_prompt). Validation happens at the API boundary
in services/claude_client.py so the UI never KeyErrors on malformed output.

Design:
- extra="allow" everywhere → never drop keys Claude returns beyond the schema.
- Only the primary score fields are required (automation_score / ai_potential_score);
  a response missing those is unusable, so it should surface a friendly error.
- Every other field is Optional-with-default, because the prompt requests but
  cannot guarantee them — missing ones get safe defaults and the UI still renders.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    # Preserve any keys Claude sends beyond the declared schema, and keep them
    # in model_dump() output so downstream consumers lose nothing.
    model_config = ConfigDict(extra="allow")


# ── Role analysis ───────────────────────────────────────────────────────────────
class Task(_Base):
    name: Optional[str] = None
    type: Optional[str] = None
    score: Optional[int] = None
    rationale: Optional[str] = None


class AIAgent(_Base):
    name: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    handles: Optional[str] = None
    time_saving: Optional[str] = None
    setup_complexity: Optional[str] = None


class Reskilling(_Base):
    develop: list[str] = Field(default_factory=list)
    retain: list[str] = Field(default_factory=list)


class RoadmapPhase(_Base):
    phase: Optional[str] = None
    duration: Optional[str] = None
    title: Optional[str] = None
    items: list[str] = Field(default_factory=list)


class Risk(_Base):
    title: Optional[str] = None
    color_key: Optional[str] = None
    items: list[str] = Field(default_factory=list)


class RoleStats(_Base):
    fully_automatable_pct: Optional[int] = None
    ai_augmented_pct: Optional[int] = None
    human_only_pct: Optional[int] = None


class RoleAnalysis(_Base):
    automation_score: int  # required — a role analysis without it is unusable
    weekly_hours_saved: Optional[int] = None
    transformation_priority: Optional[str] = None
    summary: Optional[str] = None
    tasks: list[Task] = Field(default_factory=list)
    ai_agents: list[AIAgent] = Field(default_factory=list)
    reskilling: Reskilling = Field(default_factory=Reskilling)
    roadmap: list[RoadmapPhase] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    stats: RoleStats = Field(default_factory=RoleStats)


# ── Company research ─────────────────────────────────────────────────────────────
class CompanyProfile(_Base):
    name: Optional[str] = None
    inferred_industry: Optional[str] = None
    inferred_size: Optional[str] = None
    luxembourg_presence: Optional[str] = None
    regulatory_context: Optional[str] = None


class IndustryTrend(_Base):
    trend: Optional[str] = None
    description: Optional[str] = None
    impact: Optional[str] = None
    timeline: Optional[str] = None


class CompetitorMove(_Base):
    competitor: Optional[str] = None
    move: Optional[str] = None
    threat_level: Optional[str] = None


class AIOpportunity(_Base):
    area: Optional[str] = None
    opportunity: Optional[str] = None
    estimated_impact: Optional[str] = None
    priority: Optional[str] = None


class RiskBarrier(_Base):
    risk: Optional[str] = None
    description: Optional[str] = None
    mitigation: Optional[str] = None


class AIStrategy(_Base):
    headline: Optional[str] = None
    approach: Optional[str] = None
    quick_wins: list[str] = Field(default_factory=list)
    strategic_bets: list[str] = Field(default_factory=list)


class CompanyResearch(_Base):
    company_profile: CompanyProfile = Field(default_factory=CompanyProfile)
    ai_potential_score: int  # required — core metric the UI renders on
    ai_potential_label: Optional[str] = None
    ai_potential_summary: Optional[str] = None
    industry_ai_trends: list[IndustryTrend] = Field(default_factory=list)
    competitor_moves: list[CompetitorMove] = Field(default_factory=list)
    key_ai_opportunities: list[AIOpportunity] = Field(default_factory=list)
    risks_and_barriers: list[RiskBarrier] = Field(default_factory=list)
    recommended_ai_strategy: AIStrategy = Field(default_factory=AIStrategy)
    deloitte_angle: Optional[str] = None


# ── Entity disambiguation (WO-10) ────────────────────────────────────────────────
class CompanyCandidate(_Base):
    legal_name: Optional[str] = None
    sector: Optional[str] = None
    description: Optional[str] = None
    hint: Optional[str] = None
    source: Optional[str] = None  # "registry" (GLEIF) or "llm"


class CompanyCandidates(_Base):
    # No required field: an empty list is valid (name was unambiguous / no match),
    # and the UI falls back to direct research in that case.
    candidates: list[CompanyCandidate] = Field(default_factory=list)


# ── HR management & advisory (WO-14) ─────────────────────────────────────────────
class RedeploymentOption(_Base):
    option: Optional[str] = None
    description: Optional[str] = None
    effort: Optional[str] = None  # Low | Medium | High


class RetentionPriority(_Base):
    group: Optional[str] = None
    reason: Optional[str] = None
    action: Optional[str] = None


class ChangeStep(_Base):
    phase: Optional[str] = None
    actions: list[str] = Field(default_factory=list)


class HRRisk(_Base):
    risk: Optional[str] = None
    mitigation: Optional[str] = None


class HRAdvisory(_Base):
    # All-optional: advisory is best-effort qualitative guidance, not a hard schema.
    summary: Optional[str] = None
    redeployment_options: list[RedeploymentOption] = Field(default_factory=list)
    reskilling_focus: list[str] = Field(default_factory=list)
    change_management: list[ChangeStep] = Field(default_factory=list)
    retention_priorities: list[RetentionPriority] = Field(default_factory=list)
    workforce_planning: list[str] = Field(default_factory=list)
    hr_risks: list[HRRisk] = Field(default_factory=list)
