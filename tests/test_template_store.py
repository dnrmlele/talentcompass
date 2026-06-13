"""Tests for pluggable template persistence (WO-12)."""

from __future__ import annotations

import json

from services import agent_library as al
from services.template_store import (
    CUSTOM_KEY,
    FileStore,
    SessionStore,
    get_store,
)


def test_session_store_roundtrip():
    state = {}
    s = SessionStore(state)
    assert s.load() == []
    s.save([{"name": "A"}])
    assert s.load() == [{"name": "A"}]
    assert state[CUSTOM_KEY] == [{"name": "A"}]


def test_file_store_roundtrip(tmp_path):
    p = tmp_path / "templates.json"
    s = FileStore(p)
    assert s.load() == []  # missing file -> empty
    s.save([{"name": "Recon", "category": "Fund"}])
    assert json.loads(p.read_text(encoding="utf-8"))[0]["name"] == "Recon"
    assert FileStore(p).load()[0]["name"] == "Recon"  # survives a fresh instance


def test_file_store_corrupt_file_is_safe(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    assert FileStore(p).load() == []


def test_get_store_defaults_to_session(monkeypatch):
    monkeypatch.delenv("TC_TEMPLATE_STORE", raising=False)
    assert isinstance(get_store({}), SessionStore)


def test_get_store_file_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("TC_TEMPLATE_STORE", "file")
    monkeypatch.setenv("TC_TEMPLATE_PATH", str(tmp_path / "t.json"))
    assert isinstance(get_store({}), FileStore)


def test_agent_library_file_mode_persists(monkeypatch, tmp_path):
    monkeypatch.setenv("TC_TEMPLATE_STORE", "file")
    monkeypatch.setenv("TC_TEMPLATE_PATH", str(tmp_path / "t.json"))
    state = {}
    al.save_template(state, {"name": "Persisted", "category": "X"})
    # a brand-new session dict still sees it via the file store
    assert any(t["name"] == "Persisted" for t in al.list_custom_templates({}))
    # and it is mirrored into state for session export
    assert state[CUSTOM_KEY][0]["name"] == "Persisted"


def test_delete_template(monkeypatch):
    monkeypatch.delenv("TC_TEMPLATE_STORE", raising=False)
    state = {}
    al.save_template(state, {"name": "Gone", "category": "X"})
    assert al.delete_template(state, "gone") is True  # case-insensitive
    assert al.delete_template(state, "gone") is False  # already removed
    assert al.list_custom_templates(state) == []
