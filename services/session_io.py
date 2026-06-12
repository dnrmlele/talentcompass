"""Export / import a TalentCompass browser session as JSON.

Only the analysis history is persisted — org_roles and org_companies. The
Claude API key is NEVER written to the export and is stripped from any imported
file, so a shared session file can never leak credentials.

Round-trip safety: each record is validated through the same pydantic schemas
the API boundary uses (services.schemas). Role records keep their _title/_dept/
_client UI tags because the schemas allow extra keys.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from services.schemas import RoleAnalysis, CompanyResearch
from services.agent_library import CUSTOM_KEY, sanitize_custom_templates

SCHEMA_VERSION = 1
_APP_TAG = "TalentCompass"


class SessionImportError(Exception):
    """Raised when an uploaded session file is missing, malformed, or invalid."""


def export_session(session_state: Any) -> bytes:
    """Serialise the current session's analysis history to JSON bytes.

    Pulls only org_roles + org_companies — never the api_key or any other
    session key — and stamps an app tag + schema version for safe re-import.
    """
    roles = list(session_state.get("org_roles") or [])
    companies = list(session_state.get("org_companies") or [])
    custom_templates = sanitize_custom_templates(session_state.get(CUSTOM_KEY))
    payload = {
        "app": _APP_TAG,
        "version": SCHEMA_VERSION,
        "org_roles": roles,
        "org_companies": companies,
        CUSTOM_KEY: custom_templates,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def import_session(raw: bytes | str) -> dict:
    """Parse, validate, and normalise an uploaded session file.

    Returns {"org_roles": [...], "org_companies": [...]} with every record
    run through the schema (defaults filled, extra UI tags preserved). Any
    api_key present in the file is dropped. Raises SessionImportError with a
    user-friendly message on any problem.
    """
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as e:
            raise SessionImportError("File is not valid UTF-8 text.") from e

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SessionImportError("File is not valid JSON.") from e

    if not isinstance(data, dict):
        raise SessionImportError("Not a TalentCompass session file.")

    version = data.get("version")
    if version is None:
        raise SessionImportError("Not a TalentCompass session file (no version).")
    if not isinstance(version, int) or version > SCHEMA_VERSION:
        raise SessionImportError(
            f"Unsupported session version: {version}. This app reads version "
            f"{SCHEMA_VERSION} or older."
        )

    raw_roles = data.get("org_roles") or []
    raw_companies = data.get("org_companies") or []
    if not isinstance(raw_roles, list) or not isinstance(raw_companies, list):
        raise SessionImportError("org_roles / org_companies must be lists.")

    try:
        roles = [RoleAnalysis.model_validate(r).model_dump() for r in raw_roles]
        companies = [
            CompanyResearch.model_validate(c).model_dump() for c in raw_companies
        ]
    except ValidationError as e:
        raise SessionImportError(
            f"A record did not match the expected structure: {e.error_count()} issue(s)."
        ) from e

    # Defensive: never let a credential ride in through an imported file.
    for rec in roles + companies:
        rec.pop("api_key", None)

    custom_templates = sanitize_custom_templates(data.get(CUSTOM_KEY))

    return {
        "org_roles": roles,
        "org_companies": companies,
        CUSTOM_KEY: custom_templates,
    }
