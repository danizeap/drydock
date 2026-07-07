"""Behavioral tests for the PreToolUse packet guard (packet-guard spec).
Every red-team false-positive class is pinned here; wrongful DENY is the
failure mode this suite exists to prevent.
"""
import io
import json

import pytest

import _drydock_common as common
import completion_gate as cg
import packet_guard as pg

SID = "session-abcdef123456"


@pytest.fixture
def state_dir(tmp_path, monkeypatch):
    d = tmp_path / "state"
    d.mkdir()
    monkeypatch.setattr(common, "_state_dir", lambda: d)
    return d


def make_project(root, with_packet=False):
    (root / "sdd-plus" / "protocols").mkdir(parents=True)
    (root / "sdd-plus" / "changes").mkdir(parents=True)
    (root / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    (root / "src").mkdir()
    if with_packet:
        p = root / "sdd-plus" / "changes" / "some-work"
        p.mkdir()
        (p / "tasks.md").write_text("- [ ] a\n", encoding="utf-8")
    return root


def call(root, file_path, tool="Write", sid=SID, cwd=None):
    return pg.classify({"tool_name": tool, "session_id": sid,
                        "cwd": str(cwd or root),
                        "tool_input": {"file_path": str(file_path)}})


def bash(root, command):
    return pg.classify({"tool_name": "Bash", "session_id": SID, "cwd": str(root),
                        "tool_input": {"command": command}})


# --- silent tier: never bother legitimate flows ------------------------------
def test_silent_outside_drydock(tmp_path, state_dir):
    (tmp_path / "src").mkdir()
    assert call(tmp_path, tmp_path / "src" / "x.py")[0] == "silent"


def test_silent_when_packet_active(tmp_path, state_dir):
    root = make_project(tmp_path, with_packet=True)
    assert call(root, root / "src" / "x.py")[0] == "silent"
    assert call(root, root / "migrations" / "0001.sql")[0] == "silent"  # even high-risk


def test_non_kebab_packet_counts_as_active(tmp_path, state_dir):
    root = make_project(tmp_path)
    p = root / "sdd-plus" / "changes" / "Fix_CI"
    p.mkdir()
    (p / "tasks.md").write_text("- [ ] x\n", encoding="utf-8")
    assert call(root, root / "src" / "x.py")[0] == "silent"


def test_bare_decoy_dir_without_tasks_does_not_count(tmp_path, state_dir):
    root = make_project(tmp_path)
    (root / "sdd-plus" / "changes" / "decoy").mkdir()
    assert call(root, root / "src" / "x.py")[0] == "warn"


def test_silent_for_docs_and_exempt(tmp_path, state_dir):
    root = make_project(tmp_path)
    assert call(root, root / "README.md")[0] == "silent"
    assert call(root, root / "LICENSE")[0] == "silent"
    assert call(root, root / ".gitignore")[0] == "silent"
    assert call(root, root / "sdd-plus" / "changes" / "x" / "brief.md")[0] == "silent"


def test_silent_for_target_outside_project(tmp_path, state_dir):
    root = make_project(tmp_path)
    outside = tmp_path.parent / "scratch.py"
    assert call(root, outside)[0] == "silent"


def test_sibling_prefix_repo_is_not_inside(tmp_path, state_dir):
    root = make_project(tmp_path / "drydock")
    sibling = tmp_path / "drydock-experiments" / "auth"
    sibling.mkdir(parents=True)
    # sibling repo shares the string prefix but is NOT inside -> silent
    assert call(root, sibling / "handler.py")[0] == "silent"


def test_claude_dir_exempt_except_settings(tmp_path, state_dir):
    root = make_project(tmp_path)
    assert call(root, root / ".claude" / "launch.json")[0] == "silent"
    assert call(root, root / ".claude" / "settings.local.json")[0] == "warn"


# --- deny tier: narrow, suppressed by soft segments --------------------------
def test_deny_migrations(tmp_path, state_dir):
    root = make_project(tmp_path)
    assert call(root, root / "migrations" / "0002_add_users.sql") == ("deny", "schema migration")
    assert call(root, root / "db" / "migrate" / "20260707_add_x.rb") == ("deny", "schema migration")


def test_deny_is_case_insensitive(tmp_path, state_dir):
    root = make_project(tmp_path)
    assert call(root, root / "Migrations" / "V1__init.cs")[0] == "deny"


def test_tests_under_auth_or_migrations_not_denied(tmp_path, state_dir):
    root = make_project(tmp_path)
    assert call(root, root / "tests" / "migrations" / "test_0001.py")[0] == "warn"
    assert call(root, root / "src" / "auth" / "login.tsx")[0] == "warn"  # auth demoted to warn
    assert call(root, root / "fixtures" / "migrations" / "seed.sql")[0] == "warn"


def test_docs_in_migrations_exempt_before_deny(tmp_path, state_dir):
    root = make_project(tmp_path)
    assert call(root, root / "migrations" / "README.md")[0] == "silent"


def test_new_workflow_denied_existing_workflow_warns(tmp_path, state_dir):
    root = make_project(tmp_path)
    wf = root / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    assert call(root, wf / "ci.yml")[0] == "warn"                     # existing: routine
    assert call(root, wf / "deploy.yml") == ("deny", "new CI workflow/config")  # new: high-risk


def test_deny_dockerfile_and_compose(tmp_path, state_dir):
    root = make_project(tmp_path)
    assert call(root, root / "Dockerfile")[0] == "deny"
    assert call(root, root / "Dockerfile.prod")[0] == "deny"
    assert call(root, root / "compose.yaml")[0] == "deny"
    assert call(root, root / "examples" / "Dockerfile")[0] == "warn"  # soft segment suppresses
    assert call(root, root / "src" / "dockerfile_gen.py")[0] == "warn"  # helper, not a config


def test_bash_redirect_into_migrations_denied(tmp_path, state_dir):
    root = make_project(tmp_path)
    mig = root / "migrations"
    mig.mkdir()
    assert bash(root, f'echo "ALTER TABLE x" > "{mig / "0003.sql"}"')[0] == "deny"


def test_bash_ordinary_write_does_not_warn(tmp_path, state_dir):
    root = make_project(tmp_path)
    # Bash participates in the deny tier only; no warn from shell writes
    assert bash(root, f'echo hi > "{root / "src" / "notes.py"}"')[0] == "silent"


# --- warn tier: once per session, persist-before-speak -----------------------
def test_warn_once_per_session(tmp_path, state_dir):
    root = make_project(tmp_path)
    assert pg._mark_warned(root, SID) is True
    assert pg._mark_warned(root, SID) is False  # second time: already warned


def test_warn_not_spoken_if_state_unavailable(tmp_path, state_dir, monkeypatch):
    root = make_project(tmp_path)
    monkeypatch.setattr(common, "_state_dir", lambda: None)
    assert pg._mark_warned(root, SID) is False  # no channel -> silence, never nag


def test_warn_none_sid_is_silent(tmp_path, state_dir):
    root = make_project(tmp_path)
    assert pg._mark_warned(root, None) is False


# --- cross-hook state contract ----------------------------------------------
def test_completion_gate_preserves_warned_flag(tmp_path, state_dir):
    """The v0.2.1 bug the red-team caught: nudge persistence must not drop keys
    other hooks own."""
    root = make_project(tmp_path)
    pkt = root / "sdd-plus" / "changes" / "demo-pkt"
    pkt.mkdir(parents=True)
    pkt.joinpath("tasks.md").write_text("- [ ] a\n", encoding="utf-8")
    pkt.joinpath("verification.md").write_text("## Result\n\nPending.\n", encoding="utf-8")
    # baseline + warned flag
    p = common.state_path(SID)
    common.write_state(p, common.new_state(SID, common.fingerprint_project(root)))
    assert pg._mark_warned(root, SID) is True
    # complete the packet -> completion gate nudges and rewrites state
    pkt.joinpath("tasks.md").write_text("- [x] a\n", encoding="utf-8")
    assert cg.run({"cwd": str(root), "session_id": SID}) == "demo-pkt"
    state = common.read_state(p, SID)
    assert state.get("warned") is True  # survived the nudge rewrite
    assert state.get("nudged") == ["demo-pkt"]


# --- never break an edit ------------------------------------------------------
def test_main_exits_zero_on_garbage(monkeypatch):
    for payload in ("not json", "", "[1,2]", '{"tool_name":"Write"}'):
        monkeypatch.setattr(pg.sys, "stdin", io.StringIO(payload))
        assert pg.main() == 0


def test_deny_emits_valid_json(tmp_path, state_dir, monkeypatch, capsys):
    root = make_project(tmp_path)
    payload = json.dumps({"tool_name": "Write", "session_id": SID, "cwd": str(root),
                          "tool_input": {"file_path": str(root / "migrations" / "x.sql")}})
    monkeypatch.setattr(pg.sys, "stdin", io.StringIO(payload))
    assert pg.main() == 0
    out = json.loads(capsys.readouterr().out)
    hso = out["hookSpecificOutput"]
    assert hso["permissionDecision"] == "deny"
    assert "/drydock:new" in hso["permissionDecisionReason"] or "sdd.py new" in hso["permissionDecisionReason"]


def test_relative_path_resolved_against_cwd(tmp_path, state_dir):
    root = make_project(tmp_path)
    assert call(root, "migrations/0001.sql")[0] == "deny"  # relative, joined to cwd


# --- wrongful-deny regressions (classes found by adversarial verification) ---
def test_project_under_migrations_ancestor_not_poisoned(tmp_path, state_dir):
    """Class 1: a project living below a folder named 'migrations' must not have
    every source edit denied — classification is project-relative only."""
    root = make_project(tmp_path / "migrations" / "projC")
    assert call(root, root / "src" / "app.py")[0] == "warn"
    # ...while a real migrations dir INSIDE the project still denies
    assert call(root, root / "migrations" / "0001.sql")[0] == "deny"


def test_quoted_redirect_in_bash_strings_not_denied(tmp_path, state_dir):
    """Class 2: '>' inside quoted arguments (grep patterns, commit messages) is
    not a redirection."""
    root = make_project(tmp_path)
    (root / "migrations").mkdir()
    assert bash(root, 'grep "x > migrations/0001.sql" log.txt')[0] == "silent"
    assert bash(root, 'git commit -m "guard: deny writes > migrations/0001.sql"')[0] == "silent"
    # ...while a REAL redirect still denies
    assert bash(root, 'echo "ALTER" > migrations/0002.sql')[0] == "deny"


def test_db_migrate_requires_adjacency(tmp_path, state_dir):
    """Class 3: spec says ADJACENT db+migrate segments."""
    root = make_project(tmp_path)
    assert call(root, root / "db" / "helpers" / "migrate" / "util.py")[0] == "warn"
    assert call(root, root / "db" / "migrate" / "20260707_x.rb")[0] == "deny"


# --- promised-in-plan coverage (verifier-noted gaps) --------------------------
def test_multiedit_uses_top_level_file_path(tmp_path, state_dir):
    root = make_project(tmp_path)
    out = pg.classify({"tool_name": "MultiEdit", "session_id": SID, "cwd": str(root),
                       "tool_input": {"file_path": str(root / "migrations" / "m.sql"),
                                      "edits": [{"old_string": "a", "new_string": "b"}]}})
    assert out[0] == "deny"


def test_latency_sanity(tmp_path, state_dir):
    """classify() is pure file-stat work — a full evaluation must be far under
    the per-edit budget (no subprocesses, bounded reads)."""
    import time
    root = make_project(tmp_path)
    t0 = time.monotonic()
    for _ in range(20):
        call(root, root / "src" / "x.py")
    per_call = (time.monotonic() - t0) / 20
    assert per_call < 0.05, f"classify too slow: {per_call*1000:.1f}ms per edit"
