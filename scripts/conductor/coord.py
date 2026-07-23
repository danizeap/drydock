#!/usr/bin/env python3
"""Multi-chat coordination — the "Shared Dipstick" (P0 + P1).

When several Claude Code chats run concurrently on different repos but share ONE
Codex account, each independently spawning `codex app-server` to read the fuel
gauge stampedes shared ~/.codex state. This module gives them a single, shared,
TTL-cached, single-flight gauge read per tank — so N chats collapse to ~1
app-server read per TTL instead of N.

Two hard rules (from the design panel):
  1. HONEST: it caches and shares the real gauge; it does NOT invent a "reserved
     fuel %" (the gauge is integer-percent-of-a-weekly-window; per-turn burn is
     sub-1% and unquantifiable in %, so any reservation would be fabricated). It
     only ever serves real numbers, tagged with their age.
  2. FAIL-OPEN: a coordination bug must NEVER brick a session. Every path is
     wrapped to fall back to today's behavior — a direct `executor.read_remaining()`.

State lives OUTSIDE ~/.codex and outside the repo (%LOCALAPPDATA%\\Drydock on
Windows / $XDG_STATE_HOME/drydock on POSIX); it self-heals and is reconstructed
from reality on every read. `DRYDOCK_COORD_DISABLE=1` turns it off entirely.
Stdlib only.
"""
import json
import os
import tempfile
import time

_CACHE_TTL_S = 75          # a shared gauge read is reused for this long
_STALE_LOCK_S = 30         # a refresh lock older than this is stealable (> the ~25s read timeout)


def _disabled():
    return os.environ.get("DRYDOCK_COORD_DISABLE") == "1"


def _state_dir():
    """Coordination state dir, or None if it can't be created (-> fail open)."""
    try:
        override = os.environ.get("DRYDOCK_STATE")
        if override:
            base = override
        elif os.name == "nt":
            base = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "Drydock")
        else:
            base = (os.environ.get("XDG_STATE_HOME")
                    or os.path.join(os.path.expanduser("~"), ".local", "state", "drydock"))
        d = os.path.join(base, "fleet")
        os.makedirs(d, exist_ok=True)
        return d
    except OSError:
        return None


def _cache_path(d, name):
    return os.path.join(d, f"tank-{name}.json")


def _lock_path(d, name):
    return os.path.join(d, f"tank-{name}.refresh.lock")


def _replace_retry(src, dst, tries=6):
    """os.replace with a short retry — Windows AV/indexers can briefly lock the dst."""
    for i in range(tries):
        try:
            os.replace(src, dst)
            return True
        except PermissionError:
            time.sleep(0.04 * (i + 1))
        except OSError:
            break
    try:
        os.replace(src, dst)
        return True
    except OSError:
        try:
            os.remove(src)
        except OSError:
            pass
        return False


def _atomic_write(d, dst, text):
    fd, tmp = tempfile.mkstemp(prefix=".w-", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        return _replace_retry(tmp, dst)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _write_cache(d, name, gauge, as_of):
    _atomic_write(d, _cache_path(d, name), json.dumps({"gauge": gauge, "as_of": as_of}))


def _try_acquire_refresh(d, name):
    """Best-effort single-flight lock. Not mutual exclusion — worst case a couple
    of sessions refresh at once (== today's behaviour). Never deadlocks: a lock
    older than _STALE_LOCK_S is stealable via atomic replace."""
    lock = _lock_path(d, name)
    mark = f"{os.getpid()}-{time.time()}"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, mark.encode())
        os.close(fd)
        return mark
    except FileExistsError:
        prev = ""
        try:
            with open(lock, encoding="utf-8") as f:
                prev = f.read()
        except OSError:
            pass
        held_at = 0.0
        if "-" in prev:
            try:
                held_at = float(prev.rsplit("-", 1)[1])
            except ValueError:
                held_at = 0.0
        if time.time() - held_at > _STALE_LOCK_S:
            # steal: atomically replace the stale lock, then confirm we won
            fd2, tmp = tempfile.mkstemp(prefix=".lk-", dir=d)
            try:
                os.write(fd2, mark.encode())
                os.close(fd2)
            except OSError:
                return None
            if not _replace_retry(tmp, lock):
                return None
            try:
                with open(lock, encoding="utf-8") as f:
                    return mark if f.read() == mark else None
            except OSError:
                return None
        return None
    except OSError:
        return None


def _release_refresh(d, name, mark):
    lock = _lock_path(d, name)
    try:
        with open(lock, encoding="utf-8") as f:
            if f.read() != mark:
                return  # someone stole it; leave theirs
    except OSError:
        return
    try:
        os.remove(lock)
    except OSError:
        pass


def _serve(cache, now, source):
    """Return the cached gauge, adjusting the reset countdown by the cache age so
    resets_in_hours stays honest, and tagging the age + source."""
    out = dict(cache.get("gauge") or {})
    age = max(0.0, now - float(cache.get("as_of") or now))
    if isinstance(out.get("resets_in_hours"), (int, float)):
        out["resets_in_hours"] = round(max(0.0, out["resets_in_hours"] - age / 3600.0), 1)
    out["as_of_age_s"] = round(age, 1)
    out["source"] = source
    return out


def _direct(executor):
    try:
        r = executor.read_remaining()
        if isinstance(r, dict):
            r = dict(r)
            r["source"] = "direct"
            return r
        return {"ok": False, "source": "direct", "error": "bad read_remaining"}
    except Exception as e:  # noqa: BLE001 — fail open, never raise into delegation
        return {"ok": False, "source": "direct", "error": str(e)}


def get_gauge(executor, ttl=_CACHE_TTL_S):
    """Shared, TTL-cached, single-flight gauge read for a tank. ALWAYS returns a
    dict; ALWAYS falls back to a direct read on any error (fail-open)."""
    if _disabled():
        return _direct(executor)
    d = _state_dir()
    if d is None:
        return _direct(executor)
    try:
        name = executor.name
        cache = _read_json(_cache_path(d, name))
        if not isinstance(cache, dict):
            cache = None  # corrupt/wrong-shape -> treat as absent (self-heals on next refresh)
        now = time.time()
        if cache and (now - float(cache.get("as_of") or 0)) < ttl:
            return _serve(cache, now, "cache")           # fresh shared hit
        mark = _try_acquire_refresh(d, name)
        if mark:
            try:
                fresh = executor.read_remaining()
                if isinstance(fresh, dict) and fresh.get("ok"):
                    _write_cache(d, name, fresh, now)
                    return _serve({"gauge": fresh, "as_of": now}, now, "fresh")
                return _serve(cache, now, "stale") if cache else _direct(executor)
            finally:
                _release_refresh(d, name, mark)
        # another session is refreshing -> serve slightly-stale cache, else direct
        return _serve(cache, now, "stale") if cache else _direct(executor)
    except Exception:  # noqa: BLE001
        return _direct(executor)
