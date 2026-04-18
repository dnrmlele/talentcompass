
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


COMPANY_SYSTEM = """You are a strategic AI consultant with deep knowledge of the Luxembourg market.
You know its major industries: fund administration, banking, fintech, insurance, legal, consulting, technology.
You know key players: Clearstream, Amundi, Pictet, BGL BNP Paribas, ING, Arendt, Linklaters, PwC, KPMG, EY,
State Street, Northern Trust, Alter Domus, Apex Group, CACEIS, SGSS, and others.
You always respond with valid, parseable JSON only - no markdown, no prose, no explanation. Raw JSON only."""

def company_prompt(client_name, industry=""):
    industry_ctx = f"Known industry: {industry}." if industry else "Infer industry from the company name and Luxembourg context."
    return f"""Research and assess AI transformation potential for this Luxembourg client.

Company: {client_name}
{industry_ctx}

Return a JSON object with exactly this structure:
{{
  "company_profile": {{
    "name": "{client_name}",
    "inferred_industry": "<sector>",
    "inferred_size": "<e.g. Large enterprise, Mid-sized firm>",
    "luxembourg_presence": "<description of their Luxembourg role and footprint>",
    "regulatory_context": "<key regulators and frameworks: CSSF, CNPD, EBA, AIFMD, etc.>"
  }},
  "ai_potential_score": <integer 0-100>,
  "ai_potential_label": "<e.g. High Transformation Potential>",
  "ai_potential_summary": "<4 sentences on AI opportunity for this company type in Luxembourg>",
  "industry_ai_trends": [
    {{"trend": "<trend>", "description": "<2 sentences>", "impact": "<High|Medium|Low>", "timeline": "<Now|6-12 months|1-2 years|3+ years>"}}
  ],
  "competitor_moves": [
    {{"competitor": "<real Luxembourg/EU market player>", "move": "<specific AI initiative they are pursuing>", "threat_level": "<High|Medium|Low>"}}
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

