"""Tests for the read-only Codex conductor bridge.

All tests use a fake Codex (tests/fake_codex.py) invoked through the REAL
subprocess path — zero network, zero account quota. Proves R1-R6 of the
codex-conductor delta spec.
"""
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from conductor import codex_bridge as cb  # noqa: E402

FAKE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_codex.py")]


def _make_core(base, name, mtime=None):
    d = os.path.join(base, "OpenAI", "Codex", "bin", name)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "codex.exe")
    with open(p, "w") as f:
        f.write("x")
    if mtime:
        os.utime(p, (mtime, mtime))
    return p


# ---- R1: discovery ----
def test_discover_returns_newest(tmp_path):
    base = str(tmp_path)
    _make_core(base, "aaa", mtime=time.time() - 1000)
    new = _make_core(base, "bbb", mtime=time.time())
    assert cb.discover_core(localappdata=base) == new


def test_discover_none_when_absent(tmp_path):
    assert cb.discover_core(localappdata=str(tmp_path)) is None


def test_discover_never_returns_sandbox(tmp_path):
    # A .sandbox-bin-style path under a different root is structurally excluded.
    d = os.path.join(str(tmp_path), ".codex", ".sandbox-bin")
    os.makedirs(d)
    open(os.path.join(d, "codex.exe"), "w").close()
    assert cb.discover_core(localappdata=str(tmp_path)) is None


# ---- R3: delegation is structurally read-only ----
def test_build_argv_is_readonly(tmp_path):
    argv = cb.build_exec_argv("codex.exe", cb.FLAGSHIP, "s.json", "o.json", str(tmp_path))
    assert "-s" in argv and "read-only" in argv
    joined = " ".join(argv)
    for bad in cb.FORBIDDEN_FLAGS:
        assert bad not in joined


# ---- R5: routing policy ----
def test_route_policy():
    assert cb.route("heavy", {"remaining_percent": 95})["model"] == cb.FLAGSHIP
    assert cb.route("heavy", {"remaining_percent": 10})["model"] == cb.WORKHORSE
    assert cb.route("light", {"remaining_percent": 95})["model"] == cb.WORKHORSE
    assert cb.route("heavy", None)["model"] == cb.FLAGSHIP  # unknown fuel -> proceed


# ---- R4: secret guard ----
def test_guard_outbound_refuses_secrets():
    assert cb.guard_outbound([".env"])                      # truthy refusal reason
    assert cb.guard_outbound(["config/secrets.json"])
    assert cb.guard_outbound(["src/app.py"]) is None        # ordinary file passes


def test_delegate_file_refuses_secret_without_spawning():
    r = cb.delegate_file(FAKE, ".env", "review", "schema.json", cb.FLAGSHIP)
    assert r["ok"] is False and r["stage"] == "secret_guard"


# ---- R2: fuel gauge (success + failure modes) ----
def test_gauge_ok(monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_MODE", "normal")
    rl = cb.read_rate_limits(FAKE, timeout_s=10)
    assert rl["ok"] is True
    g = cb.summarize_gauge(rl)
    assert g["remaining_percent"] == 95 and g["plan"] == "plus"


def test_gauge_spawn_error():
    rl = cb.read_rate_limits(r"C:\drydock_no_such_dir_xyz\codex.exe", timeout_s=5)
    assert rl["ok"] is False and rl["stage"] == "spawn"


def test_gauge_ignores_nonobject_line(monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_MODE", "nonobject")
    rl = cb.read_rate_limits(FAKE, timeout_s=10)
    assert rl["ok"] is True


def test_gauge_early_exit_is_structured(monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_MODE", "early_exit")
    rl = cb.read_rate_limits(FAKE, timeout_s=5)
    assert rl["ok"] is False  # never a traceback


def test_gauge_timeout(monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_MODE", "timeout")
    rl = cb.read_rate_limits(FAKE, timeout_s=1)
    assert rl["ok"] is False and rl["stage"] == "timeout"


# ---- R3/R6: delegate parses schema-locked result, no quota ----
def test_delegate_parses_result(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_MODE", "normal")
    schema = tmp_path / "schema.json"
    schema.write_text("{}")
    r = cb.delegate(FAKE, "review please", str(schema), cb.FLAGSHIP, timeout_s=30)
    assert r["exit"] == 0
    assert r["result"] == {"overall_assessment": "FAKE_OK", "findings": []}
    assert r["usage"]["output_tokens"] == 5


def test_delegate_rejects_flag_shaped_model(tmp_path):
    # Defense in depth: a flag-shaped model identifier is refused before any spawn.
    schema = tmp_path / "schema.json"
    schema.write_text("{}")
    r = cb.delegate(FAKE, "hi", str(schema),
                    "gpt --dangerously-bypass-approvals-and-sandbox", timeout_s=30)
    assert r["ok"] is False and r["stage"] == "bad_model"


# ---- opt-in LIVE smoke test: excluded from CI; spends a little real quota ----
@pytest.mark.skipif(os.environ.get("DRYDOCK_CODEX_LIVE") != "1",
                    reason="live Codex round-trip; set DRYDOCK_CODEX_LIVE=1 to run (spends quota)")
def test_live_roundtrip(tmp_path):
    core = cb.discover_core()
    assert core, "no Codex core discovered under %LOCALAPPDATA%\\OpenAI\\Codex\\bin"
    rl = cb.read_rate_limits(core)
    assert rl["ok"] is True
    gauge = cb.summarize_gauge(rl)
    assert isinstance(gauge["remaining_percent"], int)
    schema = tmp_path / "live_schema.json"
    schema.write_text('{"type":"object","additionalProperties":false,'
                      '"required":["reply"],"properties":{"reply":{"type":"string"}}}')
    model = cb.route("light", gauge)["model"]  # workhorse -> cheap
    r = cb.delegate(core, 'Reply with JSON: {"reply":"BRIDGE_OK"}',
                    str(schema), model, timeout_s=180)
    assert r["exit"] == 0 and r["result"].get("reply")
