import json
import re
import anthropic
from services.prompts import (
    ROLE_SYSTEM, role_prompt,
    COMPANY_SYSTEM, company_prompt
)


def _call(api_key: str, system: str, user: str, max_tokens: int = 3500) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}]
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def analyze_role(api_key, job_title, department, company_size, job_description, client_name="") -> dict:
    prompt = role_prompt(job_title, department, company_size, job_description, client_name)
    return _call(api_key, ROLE_SYSTEM, prompt)


def research_company(api_key, client_name, industry="") -> dict:
    prompt = company_prompt(client_name, industry)
    return _call(api_key, COMPANY_SYSTEM, prompt, max_tokens=3500)

