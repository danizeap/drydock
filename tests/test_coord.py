"""Tests for the multi-chat coordination gauge cache (`scripts/conductor/coord.py`).

In-process with a fake executor + an isolated state dir (DRYDOCK_STATE). Covers
the single-process logic: cache hit/miss, TTL expiry, fail-open, kill switch,
age-adjusted reset countdown, and the stale-lock steal / fresh-lock defer paths.
Cross-process timing races are covered by design (best-effort, fail-open) + review.
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from conductor import coord  # noqa: E402


class FakeExec:
    name = "codex"

    def __init__(self, gauge=None, raises=False):
        self.calls = 0
        self.raises = raises
        self.gauge = gauge or {"ok": True, "remaining_percent": 90,
                               "resets_in_hours": 100.0, "plan": "plus"}

    def read_remaining(self):
        self.calls += 1
        if self.raises:
            raise RuntimeError("boom")
        return dict(self.gauge)


def _iso(monkeypatch, tmp_path):
    monkeypatch.setenv("DRYDOCK_STATE", str(tmp_path))
    monkeypatch.delenv("DRYDOCK_COORD_DISABLE", raising=False)


def test_cache_hit_shares_one_read(monkeypatch, tmp_path):
    _iso(monkeypatch, tmp_path)
    e = FakeExec()
    r1 = coord.get_gauge(e)   # miss -> real read
    r2 = coord.get_gauge(e)   # hit  -> cache
    assert e.calls == 1
    assert r1["source"] == "fresh" and r2["source"] == "cache"
    assert r2["remaining_percent"] == 90


def test_ttl_expiry_refreshes(monkeypatch, tmp_path):
    _iso(monkeypatch, tmp_path)
    e = FakeExec()
    coord.get_gauge(e, ttl=0)
    coord.get_gauge(e, ttl=0)
    assert e.calls == 2  # ttl=0 -> always stale -> refresh each time


def test_fail_open_on_read_error(monkeypatch, tmp_path):
    _iso(monkeypatch, tmp_path)
    e = FakeExec(raises=True)
    r = coord.get_gauge(e)          # must NOT raise
    assert r["source"] == "direct" and r["ok"] is False


def test_kill_switch_bypasses_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("DRYDOCK_STATE", str(tmp_path))
    monkeypatch.setenv("DRYDOCK_COORD_DISABLE", "1")
    e = FakeExec()
    coord.get_gauge(e)
    coord.get_gauge(e)
    assert e.calls == 2  # no caching when disabled


def test_reset_countdown_adjusted_by_age(monkeypatch, tmp_path):
    _iso(monkeypatch, tmp_path)
    d = coord._state_dir()
    coord._write_cache(d, "codex",
                       {"ok": True, "remaining_percent": 80, "resets_in_hours": 100.0},
                       time.time() - 7200)  # 2h old
    e = FakeExec()
    r = coord.get_gauge(e, ttl=99999)  # big TTL -> served from cache, age-adjusted
    assert r["source"] == "cache" and e.calls == 0
    assert abs(r["resets_in_hours"] - 98.0) < 0.2   # 100 - 2h
    assert r["as_of_age_s"] >= 7000


def test_stale_lock_is_stolen_and_refreshed(monkeypatch, tmp_path):
    _iso(monkeypatch, tmp_path)
    d = coord._state_dir()
    with open(coord._lock_path(d, "codex"), "w", encoding="utf-8") as f:
        f.write(f"999-{time.time() - 1000}")   # a stale lock, no cache present
    e = FakeExec()
    r = coord.get_gauge(e)
    assert r["source"] == "fresh" and e.calls == 1


def test_fresh_lock_defers_and_serves_stale(monkeypatch, tmp_path):
    _iso(monkeypatch, tmp_path)
    d = coord._state_dir()
    coord._write_cache(d, "codex",
                       {"ok": True, "remaining_percent": 70, "resets_in_hours": 50.0},
                       time.time() - 1000)      # cache older than TTL
    with open(coord._lock_path(d, "codex"), "w", encoding="utf-8") as f:
        f.write(f"888-{time.time()}")           # a FRESH lock (peer refreshing)
    e = FakeExec()
    r = coord.get_gauge(e)
    assert r["source"] == "stale" and r["remaining_percent"] == 70 and e.calls == 0


def test_negative_countdown_is_clamped(monkeypatch, tmp_path):
    _iso(monkeypatch, tmp_path)
    d = coord._state_dir()
    coord._write_cache(d, "codex",
                       {"ok": True, "remaining_percent": 50, "resets_in_hours": 0.1},
                       time.time() - 7200)   # aged well past the reset
    r = coord.get_gauge(FakeExec(), ttl=99999)
    assert r["resets_in_hours"] == 0.0        # clamped, never negative


def test_wrong_shape_cache_self_heals(monkeypatch, tmp_path):
    _iso(monkeypatch, tmp_path)
    d = coord._state_dir()
    with open(coord._cache_path(d, "codex"), "w", encoding="utf-8") as f:
        f.write("[1, 2, 3]")                  # valid JSON, wrong shape
    e = FakeExec()
    r = coord.get_gauge(e)
    assert r["source"] == "fresh" and e.calls == 1   # treated as absent -> refreshed


def test_unwritable_state_fails_open(monkeypatch, tmp_path):
    # If the state dir can't be resolved, coord must degrade to a direct read.
    monkeypatch.setattr(coord, "_state_dir", lambda: None)
    monkeypatch.delenv("DRYDOCK_COORD_DISABLE", raising=False)
    e = FakeExec()
    r = coord.get_gauge(e)
    assert r["source"] == "direct" and r["ok"] is True and e.calls == 1
