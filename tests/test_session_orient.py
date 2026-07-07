"""Behavioral tests for the SessionStart orientation hook (session-orientation spec).

Covers the red-teamed invariants: silent outside Drydock (INV1), never blocks a
session (INV2), no false 'live' (INV3), no content/path leak (INV4).
"""
import io
import json
import sys

import session_orient as so


def make_project(root, context="real", packet="demo-change", pending=2, unfilled=True):
    (root / "sdd-plus" / "protocols").mkdir(parents=True)
    (root / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    if context == "template":
        (root / "PROJECT_CONTEXT.md").write_text(
            "Copy this file to `PROJECT_CONTEXT.md`\n\n- TBD\n- TBD\n- TBD\n", encoding="utf-8")
    elif context == "real":
        (root / "PROJECT_CONTEXT.md").write_text("# Project\n\nReal secret content here.\n", encoding="utf-8")
    if packet:
        pdir = root / "sdd-plus" / "changes" / packet
        pdir.mkdir(parents=True)
        (pdir / "tasks.md").write_text("\n".join(["- [x] done"] + ["- [ ] todo"] * pending) + "\n", encoding="utf-8")
        (pdir / "verification.md").write_text(
            "## Result\n\n" + ("Pending.\n" if unfilled else "PASS.\n"), encoding="utf-8")
    return root


def _fake_guard(path, block_rc, block_msg, benign_rc):
    path.write_text(
        "import sys, json\n"
        "d = json.load(sys.stdin)\n"
        "cmd = (d.get('tool_input') or {}).get('command')\n"
        "if cmd == 'BLOCK':\n"
        f"    sys.stderr.write({block_msg!r})\n"
        f"    sys.exit({block_rc})\n"
        f"sys.exit({benign_rc})\n",
        encoding="utf-8")


def _feed(monkeypatch, payload):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))


# --- INV1: discovery / silent-outside-Drydock ------------------------------
def test_noop_outside_drydock(tmp_path):
    assert so.find_drydock_root(tmp_path, None) is None


def test_finds_real_project(tmp_path):
    make_project(tmp_path)
    assert so.find_drydock_root(tmp_path, None) == tmp_path


def test_finds_from_subdirectory(tmp_path):
    make_project(tmp_path)
    assert so.find_drydock_root(tmp_path / "sdd-plus" / "changes", None) == tmp_path


def test_requires_a_marker_not_just_sddplus(tmp_path):
    (tmp_path / "sdd-plus").mkdir()  # bare sdd-plus, no AGENTS.md / protocols
    assert so.find_drydock_root(tmp_path, None) is None


def test_excludes_plugin_own_tree(tmp_path):
    make_project(tmp_path)
    assert so.find_drydock_root(tmp_path, plugin_root=tmp_path) is None


def test_excludes_scaffold_template(tmp_path):
    scaffold = tmp_path / "assets" / "project-scaffold"
    make_project(scaffold)
    assert so.find_drydock_root(scaffold, None) is None


def test_does_not_ascend_past_git_root_into_foreign_drydock(tmp_path):
    make_project(tmp_path)                 # ancestor IS a Drydock project
    inner = tmp_path / "inner-repo"
    (inner / ".git").mkdir(parents=True)   # a non-Drydock git repo nested inside
    assert so.find_drydock_root(inner, None) is None  # must stop at inner .git


# --- context / scan --------------------------------------------------------
def test_context_states(tmp_path):
    make_project(tmp_path / "m", context="missing"); assert so._context_state(tmp_path / "m") == "missing"
    make_project(tmp_path / "t", context="template"); assert so._context_state(tmp_path / "t") == "template"
    make_project(tmp_path / "r", context="real"); assert so._context_state(tmp_path / "r") == "real"


def test_scan_reports_pending_and_unfilled(tmp_path):
    make_project(tmp_path, pending=3, unfilled=True)
    _, packets = so.scan(tmp_path)
    assert packets == [("demo-change", 1, 3, True, False)]


# --- INV4: output hygiene --------------------------------------------------
def test_output_has_no_abspath_or_file_content(tmp_path):
    make_project(tmp_path)
    ctx = so.build_context(tmp_path, tmp_path)  # tmp hooks_dir has no guards -> degraded, fine here
    assert str(tmp_path) not in ctx                 # no absolute path leak
    assert "secret content" not in ctx              # no file-content leak
    assert "demo-change" in ctx                     # kebab name is fine


# --- INV3: guardrail probe -------------------------------------------------
def test_probe_live_only_on_genuine_block(tmp_path):
    _fake_guard(tmp_path / "g.py", 2, "the test guardrail fired", 0)
    v = so.probe_guard(tmp_path, "g.py", {"tool_input": {"command": "BLOCK"}},
                       {"tool_input": {"command": "OK"}}, b"guardrail")
    assert v == "live"


def test_probe_exit2_wrong_reason_is_degraded(tmp_path):
    _fake_guard(tmp_path / "g.py", 2, "argparse: error: unrecognized", 0)  # exit 2, no 'guardrail'
    v = so.probe_guard(tmp_path, "g.py", {"tool_input": {"command": "BLOCK"}},
                       {"tool_input": {"command": "OK"}}, b"guardrail")
    assert v.startswith("degraded")


def test_probe_blocking_benign_is_degraded(tmp_path):
    _fake_guard(tmp_path / "g.py", 2, "guardrail", 2)  # blocks EVERYTHING, incl. benign
    v = so.probe_guard(tmp_path, "g.py", {"tool_input": {"command": "BLOCK"}},
                       {"tool_input": {"command": "OK"}}, b"guardrail")
    assert v.startswith("degraded")


def test_probe_missing_script_is_degraded(tmp_path):
    assert "missing" in so.probe_guard(tmp_path, "nope.py", {}, {}, b"x")


# --- INV2: run()/main() never block ----------------------------------------
def test_run_noop_in_non_drydock(tmp_path, monkeypatch):
    _feed(monkeypatch, {"cwd": str(tmp_path), "source": "startup"})
    assert so.run() == ""


def test_run_orients_real_project(tmp_path, monkeypatch):
    make_project(tmp_path)
    _feed(monkeypatch, {"cwd": str(tmp_path), "source": "startup"})
    out = so.run()
    assert "Drydock" in out and "demo-change" in out


def test_run_rejects_untrusted_cwd(tmp_path, monkeypatch):
    _feed(monkeypatch, {"cwd": "relative/not/abs", "source": "startup"})
    assert so.run() == ""
    _feed(monkeypatch, {"source": "startup"})  # missing cwd entirely
    assert so.run() == ""


def test_main_exits_zero_even_on_systemexit(monkeypatch):
    def boom():
        raise SystemExit(2)  # BaseException, escapes `except Exception`
    monkeypatch.setattr(so, "run", boom)
    assert so.main() == 0


# --- v0.3.0: staleness sentinel + coverage marker (owner-brief packet) -------
import pytest
import _drydock_common as common


@pytest.fixture
def iso_state(tmp_path, monkeypatch):
    d = tmp_path / "state"
    d.mkdir()
    monkeypatch.setattr(common, "_state_dir", lambda: d)
    monkeypatch.setattr(common, "_candidate_state_bases", lambda: [])
    monkeypatch.delenv("DRYDOCK_PROBE", raising=False)
    return d


def _status_file(root, fp):
    (root / "OWNER_STATUS.md").write_text(
        f"# Project status - 2026-01-01\n\nold content\n\n"
        f"<!-- drydock-brief fp={fp} lang=en v=1 -->\n", encoding="utf-8")


def test_stale_status_yields_trust_line_on_startup(tmp_path, monkeypatch, iso_state):
    root = make_project(tmp_path)
    _status_file(root, "0" * 16)  # never the real fingerprint
    _feed(monkeypatch, {"cwd": str(root), "source": "startup", "session_id": "session-abcdef123456"})
    out = so.run()
    assert "OWNER_STATUS.md is STALE" in out
    assert "do not cite it as current" in out


def test_resume_and_compact_never_rearm_sentinel(tmp_path, monkeypatch, iso_state):
    root = make_project(tmp_path)
    _status_file(root, "0" * 16)
    for source in ("resume", "compact"):
        _feed(monkeypatch, {"cwd": str(root), "source": source, "session_id": "session-abcdef123456"})
        assert "STALE" not in so.run()


def test_fresh_or_absent_status_is_silent(tmp_path, monkeypatch, iso_state):
    root = make_project(tmp_path)
    _feed(monkeypatch, {"cwd": str(root), "source": "startup", "session_id": "session-abcdef123456"})
    assert "STALE" not in so.run()  # absent file
    _status_file(root, common.project_fingerprint_hex(root))
    _feed(monkeypatch, {"cwd": str(root), "source": "startup", "session_id": "session-abcdef123456"})
    assert "STALE" not in so.run()  # matching fingerprint


def test_session_marker_only_on_true_session_start(tmp_path, monkeypatch, iso_state):
    root = make_project(tmp_path)
    _feed(monkeypatch, {"cwd": str(root), "source": "startup", "session_id": "session-abcdef123456"})
    so.run()
    _feed(monkeypatch, {"cwd": str(root), "source": "resume", "session_id": "session-abcdef123456"})
    so.run()
    _feed(monkeypatch, {"cwd": str(root), "source": "compact", "session_id": "session-abcdef123456"})
    so.run()
    events = common.read_events(root)
    assert sum(1 for e in events if e.get("category") == "session") == 1
