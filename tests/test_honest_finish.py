"""The 'honest finish' (0.12.0): the archive-readiness refactor, the unified
done-predicate, the delta-grammar lint, and the ready-at-green prompt that FAILS
TOWARD 'needs sync' — closing the pre-existing vacuous-pass hole at the VERIFY
PROMPT, where an unsynced non-canonical delta used to read as READY.

Scope boundary (pinned by test_archive_warns_but_proceeds_on_non_canonical): the
ARCHIVE-direct path stays permissive on non-canonical grammar — it warns but does
not block. Making archive itself fail toward needs-sync on grammar is a soft-REJECT
that would force --force (or canonical authoring) on every archive; that is a
deliberately deferred Owner decision, not part of this packet. So verify's prompt
is intentionally STRICTER than archive's gate on grammar; they agree on the four
structural blockers, which is what the shared archive_readiness guarantees.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import sdd  # noqa: E402

SDD = os.path.join(ROOT, "scripts", "sdd.py")

COMPLETE = {
    "brief.md": "# Brief\nreal content here\n",
    "plan.md": "# Plan\nreal approach\n",
    "tasks.md": "# Tasks\n- [x] did the thing\n",
    "decision-log.md": "# Decision Log\nreal decision\n",
    "verification.md": "# Verification\n## Result\nPASS. all green.\n",
}


def _make_root(tmp_path, name, files=None, delta=None, living=None):
    """Build an isolated drydock root and return (root, change_dir)."""
    root = tmp_path
    (root / "sdd-plus" / "standards").mkdir(parents=True)
    (root / "sdd-plus" / "standards" / "engineering.md").write_text("x", encoding="utf-8")
    caps = root / "sdd-plus" / "specs" / "capabilities"
    caps.mkdir(parents=True)
    if living is not None:
        (caps / "demo-cap.md").write_text(living, encoding="utf-8")
    ch = root / "sdd-plus" / "changes" / name
    (ch / "specs").mkdir(parents=True)
    for n, c in (files or COMPLETE).items():
        (ch / n).write_text(c, encoding="utf-8")
    if delta is not None:
        (ch / "specs" / "demo-cap.md").write_text(delta, encoding="utf-8")
    return root, ch


def _verify(root, name):
    return subprocess.run([sys.executable, SDD, "verify", name],
                          cwd=str(root), capture_output=True, text=True)


# ---- delta_heading_issues: the grammar lint ----

def test_lint_flags_non_canonical_requirement_heading(tmp_path):
    f = tmp_path / "d.md"
    f.write_text("Capability: c\n\n## ADDED Requirements\n\n### R5 — Cost is reported\n"
                 "The tool SHALL x.\n\n#### Scenario: s\n- **WHEN** a\n- **THEN** b\n",
                 encoding="utf-8")
    issues = sdd.delta_heading_issues(f)
    assert issues == ["### R5 — Cost is reported"]      # the level-3 non-canonical head


def test_lint_accepts_canonical_and_ignores_scenarios(tmp_path):
    f = tmp_path / "d.md"
    f.write_text("Capability: c\n\n## ADDED Requirements\n\n### Requirement: Real Name\n"
                 "SHALL.\n\n#### Scenario: something\n- **WHEN** a\n- **THEN** b\n",
                 encoding="utf-8")
    assert sdd.delta_heading_issues(f) == []            # canonical + scenario not flagged


def test_lint_ignores_headings_outside_added(tmp_path):
    f = tmp_path / "d.md"
    f.write_text("Capability: c\n\n## Notes\n\n### R9 — not a requirement section\n",
                 encoding="utf-8")
    assert sdd.delta_heading_issues(f) == []


# ---- archive_readiness: the single shared gate ----

def test_readiness_empty_for_a_clean_synced_packet(tmp_path):
    living = "# Capability: demo-cap\n\n## Requirements\n\n### Requirement: A\nSHALL.\n"
    delta = "Capability: demo-cap\n\n## ADDED Requirements\n\n### Requirement: A\nSHALL.\n"
    root, ch = _make_root(tmp_path, "clean", delta=delta, living=living)
    caps = root / "sdd-plus" / "specs" / "capabilities"
    assert sdd.archive_readiness(ch, caps) == []


def test_readiness_flags_canonical_but_unsynced(tmp_path):
    delta = "Capability: demo-cap\n\n## ADDED Requirements\n\n### Requirement: A\nSHALL.\n"
    root, ch = _make_root(tmp_path, "unsynced", delta=delta,
                          living="# Capability: demo-cap\n\n## Requirements\n")
    caps = root / "sdd-plus" / "specs" / "capabilities"
    cats = [c for c, _ in sdd.archive_readiness(ch, caps)]
    assert "missing-requirement" in cats


def test_readiness_flags_pending_and_unfilled(tmp_path):
    files = dict(COMPLETE, **{"tasks.md": "# Tasks\n- [ ] not done\n",
                              "verification.md": "# Verification\n## Result\nPending.\n"})
    root, ch = _make_root(tmp_path, "incomplete", files=files)
    caps = root / "sdd-plus" / "specs" / "capabilities"
    cats = [c for c, _ in sdd.archive_readiness(ch, caps)]
    assert "incomplete" in cats


def test_packet_unfilled_detects_pending_result(tmp_path):
    _root, ch = _make_root(tmp_path, "p", files=dict(
        COMPLETE, **{"verification.md": "# Verification\n## Result\nPending.\n"}))
    assert "verification.md" in sdd.packet_unfilled(ch)


# ---- the ready-at-green prompt (integration via subprocess) ----

def test_prompt_says_ready_when_green_and_synced(tmp_path):
    living = "# Capability: demo-cap\n\n## Requirements\n\n### Requirement: A\nSHALL.\n"
    delta = "Capability: demo-cap\n\n## ADDED Requirements\n\n### Requirement: A\nSHALL.\n"
    root, _ch = _make_root(tmp_path, "green", delta=delta, living=living)
    out = _verify(root, "green").stdout
    assert "READY TO ARCHIVE" in out and "archive green" in out


def test_prompt_refuses_ready_on_non_canonical_delta(tmp_path):
    """The vacuous-pass bug: a non-canonical unsynced delta used to read as ready.
    delta_added_requirements returns [] for '### R5 —', so nothing was 'missing'."""
    delta = ("Capability: demo-cap\n\n## ADDED Requirements\n\n### R5 — New thing\n"
             "SHALL.\n\n#### Scenario: s\n- **WHEN** a\n- **THEN** b\n")
    root, _ch = _make_root(tmp_path, "noncanon", delta=delta,
                           living="# Capability: demo-cap\n\n## Requirements\n")
    out = _verify(root, "noncanon").stdout
    assert "READY TO ARCHIVE" not in out             # the hole is closed
    assert "not the canonical" in out                # grammar warned
    assert "not machine-verifiable" in out           # prompt fails toward needs-sync


def test_prompt_says_nearly_there_when_canonical_but_unsynced(tmp_path):
    delta = "Capability: demo-cap\n\n## ADDED Requirements\n\n### Requirement: A\nSHALL.\n"
    root, _ch = _make_root(tmp_path, "nearly", delta=delta,
                           living="# Capability: demo-cap\n\n## Requirements\n")
    out = _verify(root, "nearly").stdout
    assert "READY TO ARCHIVE" not in out
    assert "/drydock:sync" in out


def test_prompt_silent_when_tasks_pending(tmp_path):
    files = dict(COMPLETE, **{"tasks.md": "# Tasks\n- [ ] todo\n"})
    root, _ch = _make_root(tmp_path, "pending", files=files)
    out = _verify(root, "pending").stdout
    assert "READY TO ARCHIVE" not in out and "Pending tasks remain" in out


# ---- archive still enforces the same gate (behavior preserved) ----

def test_archive_warns_but_proceeds_on_non_canonical(tmp_path):
    """Pins the deliberately-deferred scope boundary the verifier flagged: verify's
    prompt refuses READY on a non-canonical unsynced delta, but ARCHIVE only warns
    and proceeds (no block, no override). This asymmetry is intentional — closing
    it is a soft-REJECT that changes the authoring workflow, an Owner decision. If
    this test starts failing, archive got stricter and that decision was taken."""
    delta = ("Capability: demo-cap\n\n## ADDED Requirements\n\n### R5 — New thing\n"
             "SHALL.\n\n#### Scenario: s\n- **WHEN** a\n- **THEN** b\n")
    root, _ch = _make_root(tmp_path, "noncanon2", delta=delta,
                           living="# Capability: demo-cap\n\n## Requirements\n")
    v = _verify(root, "noncanon2")
    assert "READY TO ARCHIVE" not in v.stdout            # verify refuses
    a = subprocess.run([sys.executable, SDD, "archive", "noncanon2"],
                       cwd=str(root), capture_output=True, text=True)
    assert a.returncode == 0                             # archive proceeds (permissive)
    assert "not the canonical" in a.stdout               # ...but is NOT silent — it warns
    archived = list((root / "sdd-plus" / "archive").glob("*-noncanon2"))
    assert archived and "Override" not in (
        archived[0] / "decision-log.md").read_text(encoding="utf-8")   # no override needed


def test_archive_blocks_unsynced_then_force_waives(tmp_path):
    delta = "Capability: demo-cap\n\n## ADDED Requirements\n\n### Requirement: A\nSHALL.\n"
    root, _ch = _make_root(tmp_path, "arch", delta=delta,
                           living="# Capability: demo-cap\n\n## Requirements\n")
    blocked = subprocess.run([sys.executable, SDD, "archive", "arch"],
                             cwd=str(root), capture_output=True, text=True)
    assert blocked.returncode != 0 and "not archive-ready" in blocked.stderr
    forced = subprocess.run([sys.executable, SDD, "archive", "arch", "--force",
                             "--reason", "test waive"], cwd=str(root),
                            capture_output=True, text=True)
    assert forced.returncode == 0 and "Archived change" in forced.stdout
    # the override records the actual blocker, not a fabricated pass
    archived = list((root / "sdd-plus" / "archive").glob("*-arch"))
    assert archived and "Override" in (archived[0] / "decision-log.md").read_text(encoding="utf-8")
