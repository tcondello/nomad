import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from nomad.server import app
from nomad.config import settings
from nomad.agent.tools import (
    search_vault,
    find_backlinks,
    list_vault_tags,
    create_vault_note,
    get_custom_vault_tools,
)

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "default_model" in data
    assert "fireworks_configured" in data


def test_models_endpoint():
    response = client.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert len(data["models"]) >= 4


def test_vault_tools_in_temporary_vault(tmp_path: Path, monkeypatch):
    # Setup test vault structure
    note1 = tmp_path / "Ideas.md"
    note1.write_text("# Ideas\nHere is a thought about #research and [[Project Alpha]].", encoding="utf-8")

    note2 = tmp_path / "Project Alpha.md"
    note2.write_text("# Project Alpha\nDetails regarding [[Ideas]] and #status/active.", encoding="utf-8")

    # Monkeypatch settings vault path
    monkeypatch.setattr(settings, "obsidian_vault_path", str(tmp_path))

    # Test search_vault
    search_res = search_vault.invoke({"query": "research"})
    assert "Ideas.md" in search_res

    # Test find_backlinks
    backlinks_res = find_backlinks.invoke({"note_title": "Project Alpha"})
    assert "Ideas.md" in backlinks_res

    # Test list_vault_tags
    tags_res = list_vault_tags.invoke({})
    assert "#research" in tags_res
    assert "#status/active" in tags_res

    # Test create_vault_note
    create_res = create_vault_note.invoke({
        "title": "Meeting Notes",
        "content": "# Meeting Notes\nDiscussion about [[Ideas]].",
        "folder": "Daily"
    })
    assert "Daily/Meeting Notes.md" in create_res
    created_file = tmp_path / "Daily" / "Meeting Notes.md"
    assert created_file.exists()
    assert "[[Ideas]]" in created_file.read_text(encoding="utf-8")


def test_inline_missing_key():
    # If no key is set, transform returns 400 with a clear message
    response = client.post(
        "/v1/inline/format",
        json={"action": "format", "text": "Some text to format"}
    )
    assert response.status_code == 400
    assert "Fireworks API key is not configured" in response.json()["detail"]
