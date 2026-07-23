"""Tests for the codex-review CLI (`scripts/conductor/review.py`).

`discover_core` is monkeypatched to the fake Codex so the full review() path
(gauge -> route -> guard -> delegate) runs through the real subprocess layer with
zero account quota.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from conductor import codex_bridge as cb  # noqa: E402
from conductor import review as review_mod  # noqa: E402

FAKE = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_codex.py")]


def test_review_happy_path(monkeypatch, tmp_path):
    monkeypatch.setenv("FAKE_CODEX_MODE", "normal")
    monkeypatch.setattr(review_mod.cb, "discover_core", lambda *a, **k: FAKE)
    target = tmp_path / "x.py"
    target.write_text("print(1)\n")
    out = review_mod.review([str(target)], "heavy")
    assert out["ok"] is True
    assert out["delegation"]["result"] == {"overall_assessment": "FAKE_OK", "findings": []}
    assert out["gauge"]["remaining_percent"] == 95
    assert out["route"]["model"] == cb.FLAGSHIP  # heavy + full fuel


def test_review_light_routes_workhorse(monkeypatch, tmp_path):
    monkeypatch.setenv("FAKE_CODEX_MODE", "normal")
    monkeypatch.setattr(review_mod.cb, "discover_core", lambda *a, **k: FAKE)
    target = tmp_path / "x.py"
    target.write_text("x = 1\n")
    out = review_mod.review([str(target)], "light")
    assert out["ok"] is True and out["route"]["model"] == cb.WORKHORSE


def test_review_refuses_secret(monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_MODE", "normal")
    monkeypatch.setattr(review_mod.cb, "discover_core", lambda *a, **k: FAKE)
    out = review_mod.review([".env"], "heavy")
    assert out["ok"] is False and out["stage"] == "secret_guard"


def test_review_no_core(monkeypatch, tmp_path):
    monkeypatch.setattr(review_mod.cb, "discover_core", lambda *a, **k: None)
    out = review_mod.review([str(tmp_path / "x.py")], "heavy")
    assert out["ok"] is False and out["stage"] == "discover"


def test_review_missing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("FAKE_CODEX_MODE", "normal")
    monkeypatch.setattr(review_mod.cb, "discover_core", lambda *a, **k: FAKE)
    out = review_mod.review([str(tmp_path / "does_not_exist.py")], "heavy")
    assert out["ok"] is False and out["stage"] == "missing_file"


def test_review_rejects_oversized_file(monkeypatch, tmp_path):
    monkeypatch.setenv("FAKE_CODEX_MODE", "normal")
    monkeypatch.setattr(review_mod.cb, "discover_core", lambda *a, **k: FAKE)
    big = tmp_path / "big.py"
    big.write_text("x" * (review_mod.MAX_FILE_BYTES + 1))
    out = review_mod.review([str(big)], "heavy")
    assert out["ok"] is False and out["stage"] == "too_large"


def test_build_prompt_marks_content_untrusted():
    prompt = review_mod._build_prompt([("evil.py", "print('hi')")])
    assert "UNTRUSTED DATA" in prompt and "evil.py" in prompt
