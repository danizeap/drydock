"""Tests for mutating-delegation cost metering, soft file scoping, and the
diff-shape advisory (`scripts/conductor/mutate.py`).

Field report §6.3: a one-tool change ingested 553,941 tokens. These cover what the
tool now reports about its own cost, what `--files` does and refuses to do, and the
"awkward middle" advisory. No real Codex, no quota.
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from conductor import mutate as mutate_mod  # noqa: E402

FAKE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_codex.py")]


def _g(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def _init_repo(path):
    _g(["init"], path)
    _g(["config", "user.email", "t@example.com"], path)
    _g(["config", "user.name", "Test"], path)
    with open(os.path.join(path, "seed.txt"), "w") as f:
        f.write("seed\n")
    _g(["add", "-A"], path)
    _g(["commit", "-m", "seed"], path)


def _mutate_in(repo, monkeypatch, writer, **kw):
    monkeypatch.chdir(repo)
    monkeypatch.setenv("FAKE_CODEX_MODE", "normal")
    monkeypatch.setattr(mutate_mod.cb, "discover_core", lambda *a, **k: FAKE)
    monkeypatch.setattr(mutate_mod, "delegate_mutation", writer)
    return mutate_mod.mutate("do a thing", base="HEAD", **kw)


# ---- cost metering: measured, or null — never fabricated ----

def test_cost_reports_tokens_and_a_real_fuel_delta():
    c = mutate_mod.summarize_cost({"input_tokens": 500000, "output_tokens": 2000,
                                   "cached_input_tokens": 100},
                                  {"used_percent": 8}, {"used_percent": 11.5}, 42.0)
    assert c["input_tokens"] == 500000 and c["output_tokens"] == 2000
    assert c["total_tokens"] == 502000 and c["cached_input_tokens"] == 100
    assert c["fuel_used_percent"] == 3.5          # a genuine, above-resolution move
    assert c["fuel_resolution"] is None and c["elapsed_s"] == 42.0


def test_cost_accepts_the_alternate_usage_spelling():
    c = mutate_mod.summarize_cost({"prompt_tokens": 10, "completion_tokens": 4}, {}, {})
    assert c["input_tokens"] == 10 and c["output_tokens"] == 4 and c["total_tokens"] == 14


def test_cost_is_null_not_zero_when_unmeasurable():
    """A fabricated cost is worse than an admitted unknown: the Owner budgets
    against a fiction and the shortfall arrives silently."""
    c = mutate_mod.summarize_cost(None, None, None)
    assert c["input_tokens"] is None and c["total_tokens"] is None
    assert c["fuel_used_percent"] is None        # NOT 0
    assert c["fuel_used_before_percent"] is None


def test_cost_delta_is_null_when_the_window_reset_mid_run():
    """A reset makes after < before, and a negative cost is meaningless."""
    c = mutate_mod.summarize_cost({}, {"used_percent": 90}, {"used_percent": 2})
    assert c["fuel_used_percent"] is None


def test_cost_never_does_arithmetic_on_a_boolean_gauge():
    """`isinstance(True, (int, float))` is True and JSON `true` decodes to it, so an
    unguarded gauge turned a boolean into an authoritative-looking number — and
    True/True produced literal 0, the one value the spec forbids."""
    c = mutate_mod.summarize_cost({}, {"used_percent": True}, {"used_percent": 5})
    assert c["fuel_used_percent"] is None and c["fuel_used_before_percent"] is None
    c2 = mutate_mod.summarize_cost({}, {"used_percent": True}, {"used_percent": True})
    assert c2["fuel_used_percent"] is None        # NOT 0
    c3 = mutate_mod.summarize_cost({}, {"used_percent": "8"}, {"used_percent": 9})
    assert c3["fuel_used_percent"] is None        # strings are not measurements


def test_total_tokens_is_null_when_a_component_is_missing():
    """`(inp or 0) + (out or 0)` silently asserts the missing half was zero."""
    c = mutate_mod.summarize_cost({"input_tokens": 5}, None, None)
    assert c["input_tokens"] == 5 and c["output_tokens"] is None
    assert c["total_tokens"] is None              # not 5


def test_cost_survives_a_garbage_usage_payload():
    c = mutate_mod.summarize_cost({"input_tokens": "lots", "output_tokens": True},
                                  {"used_percent": None}, {"used_percent": 5})
    assert c["input_tokens"] is None and c["output_tokens"] is None
    assert c["fuel_used_percent"] is None


# ---- --files: opt-in, SOFT, guarded, disclosed ----

def test_scoped_task_inlines_named_targets(tmp_path):
    wt = str(tmp_path)
    with open(os.path.join(wt, "tool.py"), "w") as f:
        f.write("def existing_tool():\n    return 1\n")
    prompt, err = mutate_mod.build_scoped_task("add a tool", wt, ["tool.py"])
    assert err is None
    assert "def existing_tool" in prompt and "EDIT TARGETS" in prompt
    assert "add a tool" in prompt


def test_scoped_task_allows_a_target_that_does_not_exist_yet(tmp_path):
    """Naming a file still to be CREATED is normal; it must not fail the run."""
    prompt, err = mutate_mod.build_scoped_task("create it", str(tmp_path), ["new/thing.py"])
    assert err is None and "new/thing.py" in prompt


def test_scoped_task_is_a_noop_without_files(tmp_path):
    """--files is opt-in: omitting it leaves the prompt byte-identical."""
    prompt, err = mutate_mod.build_scoped_task("just do it", str(tmp_path), None)
    assert err is None and prompt == "just do it"


def test_scoped_task_refuses_a_secret_target_by_name(tmp_path):
    with open(os.path.join(str(tmp_path), ".env"), "w") as f:
        f.write("TOKEN=1\n")
    prompt, err = mutate_mod.build_scoped_task("t", str(tmp_path), [".env"])
    assert prompt is None and "secret-bearing" in err


def test_scoped_task_refuses_a_secret_target_by_content(tmp_path):
    """Inlining sends content off-machine — the exposure review.py already guards."""
    with open(os.path.join(str(tmp_path), "cfg.py"), "w") as f:
        f.write("KEY = 'sk-proj-" + "a" * 30 + "'\n")
    prompt, err = mutate_mod.build_scoped_task("t", str(tmp_path), ["cfg.py"])
    assert prompt is None and "secret material" in err


def test_scoped_task_content_cannot_close_its_own_fence(tmp_path):
    with open(os.path.join(str(tmp_path), "evil.py"), "w") as f:
        f.write("# DRYDOCK_FILE_BOUNDARY\n")
    prompt, _err = mutate_mod.build_scoped_task("t", str(tmp_path), ["evil.py"])
    assert "DRYDOCK_FILE_BOUNDARY_1" in prompt


def test_scoped_task_refuses_to_blow_the_inline_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(mutate_mod, "MAX_INLINE_BYTES", 100)
    with open(os.path.join(str(tmp_path), "big.py"), "w") as f:
        f.write("x" * 500)
    prompt, err = mutate_mod.build_scoped_task("t", str(tmp_path), ["big.py"])
    assert prompt is None and "inline budget" in err


def test_scoped_task_refuses_a_path_outside_the_worktree(tmp_path):
    """`--files ../../../secrets.txt` read straight out of the worktree."""
    wt = tmp_path / "wt"
    wt.mkdir()
    (tmp_path / "private.txt").write_text("out-of-tree content\n")
    prompt, err = mutate_mod.build_scoped_task("t", str(wt), ["../private.txt"])
    assert prompt is None and "outside the worktree" in err


def test_scoped_task_refuses_an_absolute_path(tmp_path):
    p = str(tmp_path / "anywhere.txt")
    prompt, err = mutate_mod.build_scoped_task("t", str(tmp_path), [p])
    assert prompt is None and "repo-relative" in err


def test_scoped_task_guards_the_RESOLVED_path_not_just_the_name(tmp_path):
    """A SYMLINK with an innocent name walks a secret file past a name-only guard.
    Guarding the resolved path closes it."""
    wt = str(tmp_path)
    secret = os.path.join(wt, ".env")
    with open(secret, "w") as f:
        f.write("DB_PASSWORD=hunter2\n")
    try:
        os.symlink(secret, os.path.join(wt, "notes.txt"))
    except (OSError, NotImplementedError, AttributeError):
        pytest.skip("symlink creation not permitted here")
    prompt, err = mutate_mod.build_scoped_task("t", wt, ["notes.txt"])
    assert prompt is None and "secret-bearing" in err


def test_hardlink_alias_is_a_STATED_limit_not_a_covered_case(tmp_path):
    """Documents a real gap rather than implying coverage. A hardlink has no
    target — both names are equal directory entries to one inode — so realpath
    returns the name it was given and no path-resolution guard can see through
    it. `review.py` shares this limit; it is disclosed, not fixed. If this test
    ever starts failing, the guard got stronger and the limit can be retired."""
    wt = str(tmp_path)
    secret = os.path.join(wt, ".env")
    with open(secret, "w") as f:
        f.write("DB_PASSWORD=hunter2\n")
    try:
        os.link(secret, os.path.join(wt, "notes.txt"))
    except (OSError, NotImplementedError, AttributeError):
        pytest.skip("hardlink creation not permitted here")
    prompt, err = mutate_mod.build_scoped_task("t", wt, ["notes.txt"])
    assert err is None and prompt is not None        # NOT caught — the stated limit
    assert os.path.realpath(os.path.join(wt, "notes.txt")).endswith("notes.txt")


def test_scoped_task_caps_the_number_of_names(tmp_path):
    """Names are payload too: 50,000 non-existent names built an 839KB prompt,
    in a change whose whole premise is a token blowout."""
    many = ["f%d.py" % i for i in range(mutate_mod.MAX_INLINE_FILES + 1)]
    prompt, err = mutate_mod.build_scoped_task("t", str(tmp_path), many)
    assert prompt is None and "limit is" in err


def test_scoped_task_caps_each_file_not_just_the_total(tmp_path, monkeypatch):
    monkeypatch.setattr(mutate_mod, "MAX_INLINE_FILE_BYTES", 50)
    with open(os.path.join(str(tmp_path), "one.py"), "w") as f:
        f.write("x" * 200)
    prompt, err = mutate_mod.build_scoped_task("t", str(tmp_path), ["one.py"])
    assert prompt is None and "per-file inline limit" in err


def test_scoped_task_read_is_hard_capped_when_the_size_check_is_lied_to(tmp_path, monkeypatch):
    """R3 scenario 6. Without this, dropping the `+1` from `fh.read(CAP + 1)`
    would pass the whole suite while silently restoring the TOCTOU."""
    monkeypatch.setattr(mutate_mod, "MAX_INLINE_FILE_BYTES", 64)
    p = os.path.join(str(tmp_path), "liar.py")
    with open(p, "wb") as f:
        f.write(b"z" * 5000)

    class _FakeStat:
        st_size = 8                                # under-reports

    monkeypatch.setattr(mutate_mod.os, "fstat", lambda fd: _FakeStat())
    prompt, err = mutate_mod.build_scoped_task("t", str(tmp_path), ["liar.py"])
    assert prompt is None and "grew past" in err


def test_scoped_task_budget_is_cumulative_across_many_small_files(tmp_path):
    """The aggregate budget must not be bypassable by naming many small files.
    Each file is well under the per-file cap; together they exceed the total."""
    per = mutate_mod.MAX_INLINE_BYTES // 30 + 1     # 30 of these overflow the total
    names = []
    for i in range(40):
        n = "f%d.py" % i
        with open(os.path.join(str(tmp_path), n), "w") as f:
            f.write("y" * per)
        names.append(n)
    assert per < mutate_mod.MAX_INLINE_FILE_BYTES    # each individually fits
    prompt, err = mutate_mod.build_scoped_task("t", str(tmp_path), names)
    assert prompt is None and "inline budget" in err


def test_dotfile_targets_are_not_mangled_into_false_out_of_scope():
    """`lstrip('./')` strips a CHARACTER SET, so `.github/…` became `github/…`
    and a run that edited exactly the declared file reported a false advisory."""
    s = mutate_mod.assess_scope([".github/workflows/ci.yml"], [".github/workflows/ci.yml"])
    assert s["out_of_scope"] == [] and s["declared_untouched"] == []
    assert s["honored"] is True and s["declared"] == [".github/workflows/ci.yml"]


def test_leading_dot_slash_is_still_normalized():
    s = mutate_mod.assess_scope(["./src/a.py"], ["src/a.py"])
    assert s["honored"] is True and s["out_of_scope"] == []


def test_scope_discloses_out_of_scope_edits_without_blocking():
    """The reporter's own 3-file change was a tool body, a test's expected-tools
    list, and i18n labels. The coupled files are the ones you forget to name —
    so reporting beats blocking."""
    s = mutate_mod.assess_scope(["src/tool.py"],
                                ["src/tool.py", "tests/tools.test.ts", "i18n/en.json"])
    assert s["honored"] is False
    assert s["out_of_scope"] == ["i18n/en.json", "tests/tools.test.ts"]
    assert s["declared_untouched"] == []


def test_scope_reports_a_declared_file_codex_never_touched():
    s = mutate_mod.assess_scope(["a.py", "b.py"], ["a.py"])
    assert s["declared_untouched"] == ["b.py"] and s["honored"] is True


def test_scope_is_absent_when_nothing_was_declared():
    assert mutate_mod.assess_scope(None, ["a.py"]) is None


def test_out_of_scope_edits_raise_an_advisory_but_never_gate():
    scope = {"out_of_scope": ["i18n/en.json"], "declared": ["src/tool.py"], "honored": False}
    g = mutate_mod.assess_gate(["src/tool.py", "i18n/en.json"],
                               {"ran": True, "pass": True, "exit_code_trusted": True},
                               None, scope)
    assert g["verdict"] == "green" and g["clears"] is True       # verdict untouched
    assert any("outside the declared" in a for a in g["advisories"])


# ---- diff shape: the "awkward middle", measured ----

def _diff_for(files_lines):
    out = []
    for name, lines in files_lines:
        out.append("--- a/" + name)
        out.append("+++ b/" + name)
        out.append("@@ -1,0 +1,%d @@" % len(lines))
        out += ["+" + ln for ln in lines]
    return "\n".join(out)


def test_wide_mechanical_sweep_is_not_flagged():
    """A dozen call sites gaining the same parameter: different names, SAME shape.
    Comparing raw text would score this as divergent and cry wolf."""
    files = ["m%d.py" % i for i in range(12)]
    diff = _diff_for([(f, ["    call_%d(arg_%d, timeout=%d)" % (i, i, i)])
                      for i, f in enumerate(files)])
    shape = mutate_mod.describe_diff_shape(files, diff)
    assert shape["kind"] == "wide-repetitive" and shape["repetition"] > 0.9
    g = mutate_mod.assess_gate(files, {"ran": True, "pass": True, "exit_code_trusted": True},
                               shape)
    assert not any("judgment calls" in a for a in g["advisories"])


def test_wide_divergent_diff_is_flagged_as_needing_a_real_read():
    bodies = [
        ["    if user.role != 'admin': raise Forbidden()"],
        ["    return [x for x in items if x.active]"],
        ["    conn.execute('UPDATE t SET v=1')"],
        ["    logger.warning('deprecated path hit')"],
        ["    cache.invalidate(key, cascade=True)"],
        ["    yield from _walk(node.children)"],
        ["    self._retries += 1"],
        ["    return json.dumps({'a': 1}, sort_keys=True)"],
        ["    with lock: shared.append(item)"],
    ]
    files = ["d%d.py" % i for i in range(len(bodies))]
    diff = _diff_for(list(zip(files, bodies)))
    shape = mutate_mod.describe_diff_shape(files, diff)
    assert shape["kind"] == "wide-divergent"
    g = mutate_mod.assess_gate(files, {"ran": True, "pass": True, "exit_code_trusted": True},
                               shape)
    assert any("weak evidence" in a for a in g["advisories"])
    assert g["verdict"] == "green" and g["clears"] is True       # advisory NEVER gates


def test_added_content_cannot_hijack_the_diff_parser():
    """Codex writes the diff. An added line reading `++ b/ghost.py` renders as
    `+++ b/ghost.py`; a prefix-matching parser read it as a file header and stole
    the rest of that file's lines — the reviewed party suppressing its own warning.
    The poison line sits MID-FILE with real content after it. That placement is
    the whole test: with it at the end of the last file, the broken parser has
    nothing left to misattribute and passes too — a guard that cannot fail for
    the case it names.
    """
    bodies = [
        ["    if user.role != 'admin': raise Forbidden()"],
        ["    return [x for x in items if x.active]"],
        ["    conn.execute('UPDATE t SET v=1')"],
        ["    logger.warning('deprecated path hit')"],
        ["    cache.invalidate(key, cascade=True)"],
        ["    yield from _walk(node.children)"],
        ["    self._retries += 1"],
        # the poison, with content following it INSIDE the same file:
        ["    banner = 1", "++ b/ghost.py", "    trailer = compute(2)"],
        ["    with lock: shared.append(item)"],
    ]
    files = ["d%d.py" % i for i in range(len(bodies))]
    diff = _diff_for(list(zip(files, bodies)))
    per = mutate_mod._added_shapes(diff)
    assert "ghost.py" not in per                    # never became a file key
    assert set(per) == set(files)                   # and stole nothing from d7.py
    shape = mutate_mod.describe_diff_shape(files, diff)
    assert shape["compared_files"] == len(files)    # all nine still compared
    assert shape["kind"] == "wide-divergent"        # advisory survives the attack
    assert shape["repetition"] is not None


def test_unmeasurable_repetition_is_unknown_not_reassuring():
    """A ten-file deletion sweep reported `wide-repetitive` — an affirmative
    'the gate means what it usually means' from an absence of evidence."""
    files = ["g%d.py" % i for i in range(10)]
    deletions = "\n".join(
        "--- a/%s\n+++ b/%s\n@@ -1,1 +0,0 @@\n-old line" % (f, f) for f in files)
    shape = mutate_mod.describe_diff_shape(files, deletions)
    assert shape["repetition"] is None and shape["kind"] == "unknown"
    g = mutate_mod.assess_gate(files, {"ran": True, "pass": True, "exit_code_trusted": True},
                               shape)
    assert any("could not be measured" in a for a in g["advisories"])
    assert g["verdict"] == "green" and g["clears"] is True     # still never gates


def test_unmeasurable_narrow_diff_stays_narrow():
    assert mutate_mod.describe_diff_shape(["a.py", "b.py"], "")["kind"] == "narrow"


def test_shape_reports_the_thresholds_and_what_it_compared():
    """R4 requires the basis to ship with the verdict — otherwise the judgment
    cannot be re-derived from constants the reader cannot see."""
    files = ["m%d.py" % i for i in range(12)]
    diff = _diff_for([(f, ["    call_%d(a_%d)" % (i, i)]) for i, f in enumerate(files)])
    shape = mutate_mod.describe_diff_shape(files, diff)
    assert shape["thresholds"] == {"wide_files": mutate_mod.WIDE_DIFF_FILES,
                                   "low_repetition": mutate_mod.LOW_REPETITION}
    assert shape["compared_files"] == 12 and shape["sampled"] is False


def test_shape_comparison_is_bounded_and_says_so(monkeypatch):
    """Bounded for cost is fine; a bounded measurement presented as complete is not."""
    monkeypatch.setattr(mutate_mod, "MAX_SHAPE_FILES", 5)
    files = ["m%d.py" % i for i in range(20)]
    diff = _diff_for([(f, ["    call_%d(a_%d)" % (i, i)]) for i, f in enumerate(files)])
    shape = mutate_mod.describe_diff_shape(files, diff)
    assert shape["sampled"] is True and shape["compared_files"] == 5
    assert shape["files"] == 20                     # true width still reported


def test_narrow_diff_is_never_flagged_however_divergent():
    diff = _diff_for([("a.py", ["    x = 1"]), ("b.py", ["    raise SystemExit(2)"])])
    assert mutate_mod.describe_diff_shape(["a.py", "b.py"], diff)["kind"] == "narrow"


def test_diff_shape_repetition_is_none_with_too_little_to_compare():
    shape = mutate_mod.describe_diff_shape(["a.py"], _diff_for([("a.py", ["    x = 1"])]))
    assert shape["repetition"] is None and shape["kind"] == "narrow"


def test_diff_shape_survives_an_empty_or_malformed_diff():
    assert mutate_mod.describe_diff_shape([], "")["kind"] == "narrow"
    assert mutate_mod.describe_diff_shape(["a.py"], "not a diff at all")["repetition"] is None


def test_shape_erases_identifiers_but_keeps_structure():
    assert (mutate_mod._shape_of("add_tool(name, timeout=5)")
            == mutate_mod._shape_of("add_tool(other, timeout=99)"))
    assert mutate_mod._shape_of("if x:") != mutate_mod._shape_of("return f(a, b)")


# ---- end to end ----

def test_mutate_reports_cost_and_scope(monkeypatch, tmp_path):
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    _init_repo(repo)
    with open(os.path.join(repo, "tool.py"), "w") as f:
        f.write("def a():\n    return 1\n")
    _g(["add", "-A"], repo)
    _g(["commit", "-m", "tool"], repo)

    def writer(core, worktree, task, model, timeout_s=600):
        assert "def a():" in task                 # the target was inlined
        with open(os.path.join(worktree, "tool.py"), "a") as f:
            f.write("def b():\n    return 2\n")
        with open(os.path.join(worktree, "notes.md"), "w") as f:
            f.write("side effect\n")              # outside the declared scope
        return {"ok": True, "exit": 0, "usage": {"input_tokens": 42, "output_tokens": 7}}

    out = _mutate_in(repo, monkeypatch, writer, files=["tool.py"])
    try:
        assert out["cost"]["input_tokens"] == 42 and out["cost"]["total_tokens"] == 49
        assert out["cost"]["elapsed_s"] is not None
        assert out["scope"]["out_of_scope"] == ["notes.md"]
        assert out["scope"]["honored"] is False
        assert any("outside the declared" in a for a in out["gate"]["advisories"])
        assert out["diff_shape"]["files"] == 2
    finally:
        if out.get("worktree"):
            mutate_mod.cleanup_worktree(out["worktree"], out["branch"])


def test_mutate_refuses_before_spawning_when_a_target_is_secret(monkeypatch, tmp_path):
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    _init_repo(repo)
    with open(os.path.join(repo, ".env"), "w") as f:
        f.write("TOKEN=1\n")
    _g(["add", "-A", "-f"], repo)
    _g(["commit", "-m", "env"], repo)
    spawned = []

    def writer(core, worktree, task, model, timeout_s=600):
        spawned.append(1)
        return {"ok": True, "exit": 0}

    out = _mutate_in(repo, monkeypatch, writer, files=[".env"])
    assert out["ok"] is False and out["stage"] == "scope_guard"
    assert spawned == []                          # refused BEFORE Codex ran


def test_mutate_without_files_is_unchanged(monkeypatch, tmp_path):
    """The opt-in guarantee: no --files means the old path, plus reporting."""
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    _init_repo(repo)

    def writer(core, worktree, task, model, timeout_s=600):
        assert task == "do a thing"               # prompt untouched
        with open(os.path.join(worktree, "NOTES.md"), "w") as f:
            f.write("# note\n")
        return {"ok": True, "exit": 0, "usage": {"input_tokens": 1, "output_tokens": 1}}

    out = _mutate_in(repo, monkeypatch, writer)
    try:
        assert out["ok"] is True and out["merged"] is False
        assert out["scope"] is None               # nothing declared, nothing to disclose
        assert out["gate"]["verdict"] == "n/a" and out["clears_gate"] is True
    finally:
        if out.get("worktree"):
            mutate_mod.cleanup_worktree(out["worktree"], out["branch"])
