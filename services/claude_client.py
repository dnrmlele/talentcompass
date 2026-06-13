import json
import re
import anthropic
from pydantic import ValidationError
from services.prompts import (
    ROLE_SYSTEM,
    role_prompt,
    COMPANY_SYSTEM,
    company_prompt,
    DISAMBIG_SYSTEM,
    disambiguation_prompt,
)
from services.schemas import RoleAnalysis, CompanyResearch, CompanyCandidates

_RETRY_INSTRUCTION = (
    "Your previous reply was not valid JSON. Return ONLY the JSON object, "
    "no markdown, no commentary."
)


class ClaudeClientError(Exception):
    """Raised when a Claude API call fails or returns unusable output.

    kind is one of: "auth", "rate_limit", "bad_json", "api".
    """

    def __init__(self, message: str, kind: str):
        super().__init__(message)
        self.kind = kind


def _parse(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


_DEFAULT_MODEL = "claude-haiku-4-5"


def _resolve_model() -> str:
    """Model id chosen in the sidebar (st.session_state['model']), else default.

    Reads session_state lazily and defensively so the client still works when
    called outside a Streamlit script run (tests, scripts) — falls back to
    _DEFAULT_MODEL when unset or unavailable.
    """
    try:
        import streamlit as st

        chosen = st.session_state.get("model")
        if chosen:
            return chosen
    except Exception:
        pass
    return _DEFAULT_MODEL


def _send(
    client, system: str, messages: list, max_tokens: int, model: str = None
) -> str:
    msg = client.messages.create(
        model=model or _resolve_model(),
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    return msg.content[0].text


def _call(
    api_key: str, system: str, user: str, max_tokens: int = 3500, model: str = None
) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    messages = [{"role": "user", "content": user}]

    try:
        raw = _send(client, system, messages, max_tokens, model)
    except anthropic.AuthenticationError as e:
        raise ClaudeClientError(str(e), kind="auth") from e
    except anthropic.RateLimitError as e:
        raise ClaudeClientError(str(e), kind="rate_limit") from e
    except anthropic.APIError as e:
        raise ClaudeClientError(str(e), kind="api") from e

    try:
        return _parse(raw)
    except json.JSONDecodeError:
        pass  # retry exactly once below

    retry_messages = messages + [
        {"role": "assistant", "content": raw},
        {"role": "user", "content": _RETRY_INSTRUCTION},
    ]
    try:
        raw = _send(client, system, retry_messages, max_tokens, model)
    except anthropic.AuthenticationError as e:
        raise ClaudeClientError(str(e), kind="auth") from e
    except anthropic.RateLimitError as e:
        raise ClaudeClientError(str(e), kind="rate_limit") from e
    except anthropic.APIError as e:
        raise ClaudeClientError(str(e), kind="api") from e

    try:
        return _parse(raw)
    except json.JSONDecodeError as e:
        raise ClaudeClientError(
            "Claude returned invalid JSON after one retry.", kind="bad_json"
        ) from e


def _validate(data: dict, model_cls) -> dict:
    """Validate Claude's parsed JSON against a schema.

    Runs AFTER _call() has already done its json.JSONDecodeError retry, so a
    failure here is valid JSON of the wrong shape — it must NOT trigger another
    API retry. Surface it directly as a bad_json error for the UI to catch.
    """
    try:
        return model_cls.model_validate(data).model_dump()
    except ValidationError as e:
        raise ClaudeClientError(
            f"Claude response did not match the expected schema: {e.error_count()} issue(s).",
            kind="bad_json",
        ) from e


def analyze_role(
    api_key, job_title, department, company_size, job_description, client_name=""
) -> dict:
    prompt = role_prompt(
        job_title, department, company_size, job_description, client_name
    )
    return _validate(_call(api_key, ROLE_SYSTEM, prompt), RoleAnalysis)


def research_company(api_key, client_name, industry="") -> dict:
    prompt = company_prompt(client_name, industry)
    return _validate(
        _call(api_key, COMPANY_SYSTEM, prompt, max_tokens=3500), CompanyResearch
    )


def disambiguate_company(api_key, name, market="", use_registry=True) -> dict:
    """List candidate real-world entities for an ambiguous company name.

    Returns {"candidates": [...]}. Used before research to avoid profiling the
    wrong entity (e.g. a retailer vs a financial firm sharing a name).

    Sourcing: an authoritative registry (GLEIF LEI) is tried first; if it yields
    candidates they are used as-is (source="registry"). On no match, registry
    disabled, or any error, falls back to a cheap LLM listing (source="llm").
    Market resolves via prompts._resolve_market (session/Luxembourg).
    """
    if use_registry:
        try:
            from services.registry import registry_candidates

            grounded = registry_candidates(name, market)
        except Exception:
            grounded = []
        if grounded:
            return _validate({"candidates": grounded}, CompanyCandidates)

    prompt = disambiguation_prompt(name, market)
    result = _validate(
        _call(api_key, DISAMBIG_SYSTEM, prompt, max_tokens=1200), CompanyCandidates
    )
    for c in result.get("candidates", []):
        if not c.get("source"):
            c["source"] = "llm"
    return result
