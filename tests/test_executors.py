"""Tests for the executor fleet (`scripts/conductor/executors.py`).

Codex fuel is read through the fake Codex (no quota). The key safety property:
a STAGED (unverified) executor is never reported as usable and never runs, even
if it is present on the machine.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from conductor import executors as ex  # noqa: E402

FAKE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_codex.py")]


# ---- Codex adapter (proven) ----
def test_codex_available_and_fuel(monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_MODE", "normal")
    monkeypatch.setattr(ex.cb, "discover_core", lambda *a, **k: FAKE)
    c = ex.CodexExecutor()
    assert c.available() is True and c.verified is True
    fuel = c.read_remaining()
    assert fuel["ok"] is True and fuel["remaining_percent"] == 95


def test_codex_unavailable(monkeypatch):
    monkeypatch.setattr(ex.cb, "discover_core", lambda *a, **k: None)
    assert ex.CodexExecutor().available() is False


# ---- Kimi adapter (staged / unverified) ----
def test_kimi_is_unverified_and_refuses():
    k = ex.KimiExecutor()
    assert k.verified is False
    try:
        k.read_remaining()
        assert False, "staged Kimi must refuse to run"
    except ex.ExecutorUnverified:
        pass


def test_kimi_present_is_staged_never_usable(monkeypatch):
    # Even if Kimi is present, unverified means STAGED, never usable.
    monkeypatch.setattr(ex.KimiExecutor, "available", lambda self: True)
    st = ex.KimiExecutor().status()
    assert st["available"] is True and st["verified"] is False
    assert st["fuel"]["staged"] is True


# ---- fleet status + stack config ----
def test_fleet_status_codex_usable_kimi_absent(monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_MODE", "normal")
    monkeypatch.setattr(ex.cb, "discover_core", lambda *a, **k: FAKE)
    monkeypatch.setattr(ex.KimiExecutor, "available", lambda self: False)
    monkeypatch.delenv("DRYDOCK_EXECUTORS", raising=False)
    fs = ex.fleet_status()
    assert "codex" in fs["usable"]
    assert "kimi" not in fs["usable"] and "kimi" not in fs["staged"]
    assert fs["conductor"]["name"] == "claude"


def test_fleet_status_kimi_present_is_staged_not_usable(monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_MODE", "normal")
    monkeypatch.setattr(ex.cb, "discover_core", lambda *a, **k: FAKE)
    monkeypatch.setattr(ex.KimiExecutor, "available", lambda self: True)
    monkeypatch.delenv("DRYDOCK_EXECUTORS", raising=False)
    fs = ex.fleet_status()
    assert "codex" in fs["usable"]
    assert "kimi" in fs["staged"] and "kimi" not in fs["usable"]


def test_stack_config_pins_executor_set(monkeypatch):
    monkeypatch.setenv("DRYDOCK_EXECUTORS", "codex")
    names = [e.name for e in ex.executors()]
    assert names == ["codex"]
    monkeypatch.setenv("DRYDOCK_EXECUTORS", "kimi")
    assert [e.name for e in ex.executors()] == ["kimi"]
