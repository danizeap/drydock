from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest

import scaffold_bundle


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE = REPO_ROOT / "assets" / "project-scaffold"
BUNDLE = (
    REPO_ROOT
    / "adapters"
    / "codex"
    / "drydock"
    / "assets"
    / "project-scaffold.bundle.json"
)


def test_bundle_is_exact_deterministic_rebuild() -> None:
    raw = BUNDLE.read_bytes()
    assert raw == scaffold_bundle.build_bundle_bytes(SOURCE)
    entries = scaffold_bundle.load_bundle_bytes(raw)
    assert len(entries) == 40
    assert entries == sorted(entries, key=lambda entry: entry.path)


def test_bundle_excludes_claude_and_legacy_fail_open_codex_hook() -> None:
    paths = {entry.path for entry in scaffold_bundle.load_bundle(BUNDLE)}
    assert "AGENTS.md" in paths
    assert "CLAUDE.md" not in paths
    assert ".codex/hooks.json" not in paths
    assert ".codex/hooks/drydock_guard.py" not in paths
    assert ".codex/agents/drydock-explorer.toml" in paths
    assert ".codex/agents/drydock-reviewer.toml" in paths


def test_bundle_rejects_path_traversal() -> None:
    document = json.loads(BUNDLE.read_text(encoding="utf-8"))
    document["entries"][0]["path"] = "../escape"
    raw = (json.dumps(document) + "\n").encode("utf-8")
    with pytest.raises(scaffold_bundle.BundleError, match="unsafe bundle path"):
        scaffold_bundle.load_bundle_bytes(raw)


def test_bundle_rejects_content_digest_mismatch() -> None:
    document = json.loads(BUNDLE.read_text(encoding="utf-8"))
    document["entries"][0]["content_b64"] = "bm90IHRoZSBzb3VyY2UgYnl0ZXM="
    raw = (json.dumps(document) + "\n").encode("utf-8")
    with pytest.raises(scaffold_bundle.BundleError, match="digest mismatch"):
        scaffold_bundle.load_bundle_bytes(raw)


def test_bundle_rejects_embedded_crlf_in_text_entry() -> None:
    document = json.loads(BUNDLE.read_text(encoding="utf-8"))
    raw_entries = document["entries"]
    selected = next(
        item for item in raw_entries if item["path"] == "AGENTS.md"
    )
    content = base64.b64decode(selected["content_b64"])
    assert b"\n" in content
    crlf_content = content.replace(b"\n", b"\r\n", 1)
    selected["content_b64"] = base64.b64encode(crlf_content).decode("ascii")
    selected["sha256"] = hashlib.sha256(crlf_content).hexdigest()
    entries = [
        scaffold_bundle.BundleEntry(
            path=item["path"],
            sha256=item["sha256"],
            content=base64.b64decode(item["content_b64"]),
        )
        for item in raw_entries
    ]
    document["source_tree_sha256"] = scaffold_bundle._tree_digest(entries)
    raw = (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")

    with pytest.raises(scaffold_bundle.BundleError, match="contains CRLF"):
        scaffold_bundle.load_bundle_bytes(raw)


def test_source_rejects_symlink(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "target.txt"
    target.write_text("target", encoding="utf-8")
    link = source / "linked.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is not permitted on this Windows installation")
    with pytest.raises(scaffold_bundle.BundleError, match="symlinks are not allowed"):
        scaffold_bundle.collect_source(source)
