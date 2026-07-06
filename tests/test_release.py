"""Behavioral tests for the release helper (release-tooling spec).

All tests run against a temp fixture repo (REPO_ROOT monkeypatched) so the real
repo files are never touched, and subprocess.run is stubbed so no pytest/git
process is actually spawned.
"""
import json
import release


def make_repo(root, version="0.1.5", changelog_versions=("0.1.5",), guide_version=None):
    """Create a minimal fixture repo declaring `version` in all four locations."""
    guide_version = guide_version or version
    (root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "drydock", "version": version}, indent=2), encoding="utf-8")
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"name": "drydock", "plugins": [{"name": "drydock", "version": version}]}, indent=2),
        encoding="utf-8")
    (root / "docs" / "AI_OPERATOR_GUIDE.md").write_text(
        f"# Guide\n\nVERSION: Drydock {guide_version} | Scanner: launchguardian 0.1.1 (PyPI)\n",
        encoding="utf-8")
    body = "# Changelog\n\n" + "".join(f"## {v}\n- notes\n\n" for v in changelog_versions)
    (root / "CHANGELOG.md").write_text(body, encoding="utf-8")
    return root


class Recorder:
    """Stub for subprocess.run: records argv, returns success, spawns nothing."""
    def __init__(self):
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        class R:
            returncode = 0
        return R()


# --- pure helpers ----------------------------------------------------------
def test_version_tuple_orders_numerically_not_lexically():
    # '0.1.10' must be greater than '0.1.9' (string compare would say the opposite)
    assert release.version_tuple("0.1.10") > release.version_tuple("0.1.9")


def test_version_regex():
    assert release.VERSION_RE.match("0.1.6")
    assert not release.VERSION_RE.match("0.1")
    assert not release.VERSION_RE.match("v0.1.6")


# --- read / check ----------------------------------------------------------
def test_read_versions_on_aligned_fixture(tmp_path, monkeypatch):
    make_repo(tmp_path, "0.1.5")
    monkeypatch.setattr(release, "REPO_ROOT", tmp_path)
    v = release.read_versions()
    assert v == {"plugin.json": "0.1.5", "marketplace.json": "0.1.5",
                 "operator-guide": "0.1.5", "changelog-top": "0.1.5"}


def test_check_passes_when_aligned(tmp_path, monkeypatch):
    make_repo(tmp_path, "0.1.5")
    monkeypatch.setattr(release, "REPO_ROOT", tmp_path)
    assert release.cmd_check() == 0


def test_check_detects_operator_guide_drift(tmp_path, monkeypatch, capsys):
    make_repo(tmp_path, "0.1.5", guide_version="0.1.3")  # the real bug we hit
    monkeypatch.setattr(release, "REPO_ROOT", tmp_path)
    assert release.cmd_check() == 1
    err = capsys.readouterr().err
    assert "0.1.3" in err and "0.1.5" in err


# --- bump ------------------------------------------------------------------
def test_bump_rejects_non_increasing_version(tmp_path, monkeypatch):
    make_repo(tmp_path, "0.1.5")
    monkeypatch.setattr(release, "REPO_ROOT", tmp_path)
    assert release.cmd_bump("0.1.5", dry_run=False) == 2
    # nothing changed
    assert release.read_versions()["plugin.json"] == "0.1.5"


def test_bump_rejects_missing_changelog_entry(tmp_path, monkeypatch):
    make_repo(tmp_path, "0.1.5", changelog_versions=("0.1.5",))
    monkeypatch.setattr(release, "REPO_ROOT", tmp_path)
    assert release.cmd_bump("0.1.6", dry_run=False) == 1  # no ## 0.1.6 heading


def test_dry_run_writes_nothing(tmp_path, monkeypatch):
    make_repo(tmp_path, "0.1.5", changelog_versions=("0.1.6", "0.1.5"))
    monkeypatch.setattr(release, "REPO_ROOT", tmp_path)
    assert release.cmd_bump("0.1.6", dry_run=True) == 0
    assert release.read_versions()["plugin.json"] == "0.1.5"  # unchanged


def test_bump_rewrites_all_locations_and_prints_git_without_executing(tmp_path, monkeypatch, capsys):
    make_repo(tmp_path, "0.1.5", changelog_versions=("0.1.6", "0.1.5"))
    monkeypatch.setattr(release, "REPO_ROOT", tmp_path)
    rec = Recorder()
    monkeypatch.setattr(release.subprocess, "run", rec)

    rc = release.cmd_bump("0.1.6", dry_run=False)
    out = capsys.readouterr().out
    assert rc == 0

    # every declaring location moved to 0.1.6
    v = release.read_versions()
    assert v["plugin.json"] == v["marketplace.json"] == v["operator-guide"] == "0.1.6"

    # preflight ran tests + check_sync, and NEVER git
    joined = [" ".join(c) for c in rec.calls]
    assert any("pytest" in c for c in joined)
    assert any("check_sync" in c for c in joined)
    assert not any("git" in c for c in joined), f"release.py must not execute git, got: {rec.calls}"

    # the git publish commands are printed as text for the Owner to run
    assert "git commit" in out and "git tag v0.1.6" in out and "git push" in out
