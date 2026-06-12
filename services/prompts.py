
ROLE_SYSTEM = """You are an expert AI transformation consultant specializing in workforce automation.
You always respond with valid, parseable JSON only - no markdown, no prose, no explanation. Raw JSON only."""

def role_prompt(job_title, department, company_size, job_description, client_name=""):
    client_ctx = f"The client is {client_name} (Luxembourg market)." if client_name else ""
    return f"""Analyze this role for AI automation potential. {client_ctx}

Job Title: {job_title}
Department: {department}
Company Size: {company_size}
Job Description:
{job_description}

Return a JSON object with exactly this structure (no extra keys):
{{
  "automation_score": <integer 0-100, realistic based on actual tasks>,
  "weekly_hours_saved": <integer, realistic estimate>,
  "transformation_priority": "<High|Medium|Low>",
  "summary": "<3-sentence executive summary specific to this role and its actual tasks>",
  "tasks": [
    {{
      "name": "<task name extracted from the description>",
      "type": "<Fully Automatable|AI-Augmented|Human-Only>",
      "score": <integer 0-100>,
      "rationale": "<one sentence specific to this task>"
    }}
  ],
  "ai_agents": [
    {{
      "name": "<agent name>",
      "icon": "<emoji>",
      "description": "<what it does for this specific role>",
      "handles": "<specific tasks from this job description it replaces>",
      "time_saving": "<e.g. ↓ 80% time>",
      "setup_complexity": "<Low|Medium|High>"
    }}
  ],
  "reskilling": {{
    "develop": ["<skill>", "<skill>", "<skill>", "<skill>", "<skill>"],
    "retain": ["<skill>", "<skill>", "<skill>", "<skill>", "<skill>"]
  }},
  "roadmap": [
    {{"phase": "Phase 1", "duration": "0-3 months", "title": "<title>", "items": ["<action>", "<action>", "<action>"]}},
    {{"phase": "Phase 2", "duration": "3-9 months", "title": "<title>", "items": ["<action>", "<action>", "<action>"]}},
    {{"phase": "Phase 3", "duration": "9-18 months", "title": "<title>", "items": ["<action>", "<action>", "<action>"]}}
  ],
  "risks": [
    {{"title": "<risk>", "color_key": "<change|data|compliance>", "items": ["<mitigation>", "<mitigation>", "<mitigation>"]}}
  ],
  "stats": {{
    "fully_automatable_pct": <integer>,
    "ai_augmented_pct": <integer>,
    "human_only_pct": <integer>
  }}
}}

Rules:
- Base ALL analysis on the actual text of the job description, not generic assumptions.
- Tasks must map to real responsibilities listed.
- stats must sum to 100.
- ai_agents: include as many distinct agents as the role warrants (typically 3–6, not a fixed count).
- Be specific, honest, and realistic."""


# ── Market profiles ───────────────────────────────────────────────────────────
# Luxembourg is the fully-supported, default profile and the source of the
# byte-identical COMPANY_SYSTEM below. Belgium is a beta skeleton: real Belgian
# regulators/players are filled in, but trends are placeholders pending review.
MARKETS = {
    "Luxembourg": {
        "label": "Luxembourg",
        "beta": False,
        "industries": "fund administration, banking, fintech, insurance, legal, consulting, technology",
        "key_players": (
            "Clearstream, Amundi, Pictet, BGL BNP Paribas, ING, Arendt, Linklaters, PwC, KPMG, EY,\n"
            "State Street, Northern Trust, Alter Domus, Apex Group, CACEIS, SGSS, and others"
        ),
        "regulators": "CSSF, CNPD, EBA, AIFMD, etc.",
        "competitor_descriptor": "real Luxembourg/EU market player",
        "trends": "fund-admin automation, RegTech for CSSF reporting, AI-assisted KYC/AML, NAV automation",
    },
    "Belgium": {
        "label": "Belgium",
        "beta": True,
        "industries": "banking, insurance, fund management, logistics, pharmaceuticals, technology",
        "key_players": (
            "KBC, Belfius, ING Belgium, BNP Paribas Fortis, Ageas, Euroclear, Degroof Petercam, "
            "and others"
        ),
        "regulators": "FSMA, NBB (National Bank of Belgium), GBA/APD, GDPR, etc.",
        "competitor_descriptor": "real Belgian/EU market player",
        "trends": "(beta) placeholder Belgian AI trends — pending market review",
    },
}


def _resolve_market(market=None) -> str:
    """Market key to build the company prompt for.

    Explicit `market` wins. Otherwise reads st.session_state['market']
    defensively so the builder still works outside a Streamlit run (tests,
    scripts), falling back to Luxembourg — which keeps the default output
    byte-identical to the original COMPANY_SYSTEM / company_prompt.
    """
    if market:
        return market if market in MARKETS else "Luxembourg"
    try:
        import streamlit as st

        chosen = st.session_state.get("market")
        if chosen in MARKETS:
            return chosen
    except Exception:
        pass
    return "Luxembourg"


def company_system(market=None) -> str:
    m = MARKETS[_resolve_market(market)]
    return f"""You are a strategic AI consultant with deep knowledge of the {m['label']} market.
You know its major industries: {m['industries']}.
You know key players: {m['key_players']}.
You always respond with valid, parseable JSON only - no markdown, no prose, no explanation. Raw JSON only."""


# Default (Luxembourg) system prompt — byte-identical to the original literal.
COMPANY_SYSTEM = company_system("Luxembourg")


DISAMBIG_SYSTEM = """You are a market entity resolver. You distinguish between different
real-world organisations that share a similar name. You always respond with valid, parseable
JSON only - no markdown, no prose, no explanation. Raw JSON only."""


def disambiguation_prompt(name, market=None):
    m = MARKETS[_resolve_market(market)]
    label = m["label"]
    return f"""A consultant typed the company name "{name}". In the {label} market this name may
refer to more than one distinct organisation operating in different sectors. List the distinct
candidate entities so the consultant can pick the right one before research begins.

Return a JSON object with exactly this structure:
{{
  "candidates": [
    {{
      "legal_name": "<full/registered name of the entity>",
      "sector": "<its industry or sector>",
      "description": "<one sentence that distinguishes this entity from the others>",
      "hint": "<an identifying hint: registration type, group, or what it is best known for>"
    }}
  ]
}}

Rules:
- Only include entities plausibly operating in, or relevant to, the {label} market.
- If the name clearly maps to a single organisation, return exactly one candidate.
- Return between 1 and 5 candidates. Order the most likely match first.
- Be concrete and factual. Do NOT invent entities that do not exist."""


def company_prompt(client_name, industry="", market=None):
    m = MARKETS[_resolve_market(market)]
    label = m["label"]
    industry_ctx = (
        f"Known industry: {industry}."
        if industry
        else f"Infer industry from the company name and {label} context."
    )
    return f"""Research and assess AI transformation potential for this {label} client.

Company: {client_name}
{industry_ctx}

Return a JSON object with exactly this structure:
{{
  "company_profile": {{
    "name": "{client_name}",
    "inferred_industry": "<sector>",
    "inferred_size": "<e.g. Large enterprise, Mid-sized firm>",
    "luxembourg_presence": "<description of their {label} role and footprint>",
    "regulatory_context": "<key regulators and frameworks: {m['regulators']}>"
  }},
  "ai_potential_score": <integer 0-100>,
  "ai_potential_label": "<e.g. High Transformation Potential>",
  "ai_potential_summary": "<4 sentences on AI opportunity for this company type in {label}>",
  "industry_ai_trends": [
    {{"trend": "<trend>", "description": "<2 sentences>", "impact": "<High|Medium|Low>", "timeline": "<Now|6-12 months|1-2 years|3+ years>"}}
  ],
  "competitor_moves": [
    {{"competitor": "<{m['competitor_descriptor']}>", "move": "<specific AI initiative they are pursuing>", "threat_level": "<High|Medium|Low>"}}
  ],
  "key_ai_opportunities": [
    {{"area": "<business area>", "opportunity": "<specific AI use case>", "estimated_impact": "<time or cost estimate>", "priority": "<Quick Win|Strategic|Long-term>"}}
  ],
  "risks_and_barriers": [
    {{"risk": "<risk title>", "description": "<1 sentence>", "mitigation": "<1 sentence>"}}
  ],
  "recommended_ai_strategy": {{
    "headline": "<strategic headline>",
    "approach": "<3 sentences>",
    "quick_wins": ["<action>", "<action>", "<action>"],
    "strategic_bets": ["<bet>", "<bet>"]
  }},
  "deloitte_angle": "<2 sentences on how a Deloitte AI engagement could specifically help this client>"
}}"""
