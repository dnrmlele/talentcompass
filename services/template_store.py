"""Pluggable persistence for custom agent templates (WO-12).

The agent library needs custom templates to outlive a browser session and,
eventually, to be scoped per user/project in a real database. This module is the
seam: `get_store(state)` returns a `TemplateStore` chosen by configuration, and
the agent library reads/writes only through that interface. Swapping in a DB
later means adding one `TemplateStore` subclass — no change to the library or UI.

Stores shipped now:
  * SessionStore — custom templates live in st.session_state (default; today's
    behaviour, cleared on refresh, carried by session export/import).
  * FileStore    — custom templates persist to a JSON file on disk, surviving
    restarts. Opt in with env TC_TEMPLATE_STORE=file (+ optional TC_TEMPLATE_PATH).

A future DBStore(project_id) would implement the same load()/save() pair.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Session-state key holding consultant-saved custom templates (also the JSON
# array key used by session export/import).
CUSTOM_KEY = "custom_agent_templates"


class TemplateStore:
    """Interface: load and persist a list of custom template dicts."""

    def load(self) -> list[dict[str, Any]]:  # pragma: no cover - abstract
        raise NotImplementedError

    def save(self, templates: list[dict[str, Any]]) -> None:  # pragma: no cover
        raise NotImplementedError


class SessionStore(TemplateStore):
    """Back custom templates with Streamlit session state (or any dict)."""

    def __init__(self, state: Any):
        self._state = state

    def load(self) -> list[dict[str, Any]]:
        return list(self._state.get(CUSTOM_KEY) or [])

    def save(self, templates: list[dict[str, Any]]) -> None:
        self._state[CUSTOM_KEY] = list(templates)


class FileStore(TemplateStore):
    """Back custom templates with a JSON file on disk (persists across runs)."""

    def __init__(self, path: str | os.PathLike):
        self._path = Path(path)

    def load(self) -> list[dict[str, Any]]:
        if not self._path.is_file():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        return data if isinstance(data, list) else []

    def save(self, templates: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(list(templates), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def default_file_path() -> Path:
    return Path.home() / ".talentcompass" / "agent_templates.json"


def get_store(state: Any) -> TemplateStore:
    """Resolve the configured store. Defaults to SessionStore (no behaviour change).

    TC_TEMPLATE_STORE=file → FileStore at TC_TEMPLATE_PATH (or ~/.talentcompass/
    agent_templates.json).
    """
    mode = os.environ.get("TC_TEMPLATE_STORE", "session").strip().lower()
    if mode == "file":
        path = os.environ.get("TC_TEMPLATE_PATH") or default_file_path()
        return FileStore(path)
    return SessionStore(state)
