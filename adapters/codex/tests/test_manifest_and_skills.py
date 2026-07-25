from __future__ import annotations

import json
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "drydock"
REPO_ROOT = Path(__file__).resolve().parents[3]


def test_manifest_is_self_contained_and_does_not_override_hooks() -> None:
    manifest = json.loads(
        (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert manifest["name"] == "drydock"
    assert manifest["version"] == "0.12.1"
    assert manifest["skills"] == "./skills/"
    assert "hooks" not in manifest


def test_thin_skills_have_valid_frontmatter_and_honest_vocabulary() -> None:
    expected = {
        "drydock-init-project",
        "drydock-lifecycle",
        "drydock-orchestrate",
        "drydock-readiness",
    }
    skill_files = sorted((PLUGIN_ROOT / "skills").glob("*/SKILL.md"))
    assert {path.parent.name for path in skill_files} == expected
    for path in skill_files:
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\nname: ")
        assert "\ndescription: " in text.split("---", 2)[1]
        assert "slash-command alias" in text or path.parent.name != "drydock-init-project"

    readiness = (
        PLUGIN_ROOT / "skills" / "drydock-readiness" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "ready_for_enforcement" in readiness
    assert "cannot be reasoned around" in readiness


def test_repo_marketplace_points_to_self_contained_plugin() -> None:
    marketplace = json.loads(
        (REPO_ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
            encoding="utf-8"
        )
    )
    assert marketplace["name"] == "drydock"
    entries = marketplace["plugins"]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["name"] == "drydock"
    assert entry["source"]["source"] == "local"
    source = REPO_ROOT / entry["source"]["path"]
    assert source.resolve() == PLUGIN_ROOT.resolve()
    assert entry["policy"] == {
        "installation": "AVAILABLE",
        "authentication": "ON_USE",
    }
