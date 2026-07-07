"""Shared read-only helpers for Drydock's SessionStart/Stop hooks.

Both hooks import this ONE module so project discovery and packet fingerprinting
can never drift between them (a documented failure mode of this repo's dual-copy
files). Everything here is best-effort and side-effect-light: callers wrap use in
`try/except BaseException` and always exit 0. No third-party deps.
"""
import hashlib
import os
import re
import stat
import tempfile
from pathlib import Path

_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_MAX_READ_BYTES = 64 * 1024
_MAX_PACKETS = 25
_MAX_STATE_BYTES = 64 * 1024
_MAX_NUDGES = 3            # hard session cap on forced continuations
_MIN_SID = 8              # reject too-short/degenerate session ids
STATE_SCHEMA = 1


# --- bounded reads ---------------------------------------------------------
def read_head(path):
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            return f.read(_MAX_READ_BYTES)
    except OSError:
        return ""


# --- project discovery (single source of truth for both hooks) -------------
def _looks_real_root(cand, plugin_root):
    s = str(cand).replace("\\", "/")
    if "assets/project-scaffold" in s:
        return False
    if plugin_root is not None:
        try:
            if cand == plugin_root or plugin_root in cand.parents:
                return False
        except OSError:
            pass
    try:
        return (cand / "AGENTS.md").is_file() or (cand / "sdd-plus" / "protocols").is_dir()
    except OSError:
        return False


def find_drydock_root(cwd, plugin_root):
    """Closest ancestor of cwd that is a real Drydock project, bounded by the git
    root / $HOME, excluding the plugin tree and the scaffold template. None if
    outside a Drydock project."""
    try:
        home = Path.home()
    except (OSError, RuntimeError):
        home = None
    chain = [cwd]
    try:
        chain += list(cwd.parents)
    except OSError:
        pass
    for level, cand in enumerate(chain):
        if level >= 40:
            break
        try:
            has_sddplus = (cand / "sdd-plus").is_dir()
        except OSError:
            has_sddplus = False
        if has_sddplus and _looks_real_root(cand, plugin_root):
            return cand
        try:
            if (cand / ".git").exists():
                break
        except OSError:
            pass
        if home is not None and cand == home:
            break
    return None


def plugin_root_from_env():
    p = os.environ.get("CLAUDE_PLUGIN_ROOT")
    return Path(p) if p else None


# --- packet state & fingerprint --------------------------------------------
def _pending_and_done(tasks_text):
    """(pending count, claimed_done) from a tasks.md body. claimed_done means the
    implementation tasks are finished — either nothing pending, or the only
    remaining unchecked item is the 'Run verification' task."""
    unchecked = re.findall(r"(?m)^\s*-\s*\[\s\]\s+(.*)$", tasks_text)
    pending = len(unchecked)
    if pending == 0:
        return 0, True
    if pending == 1 and re.search(r"verif", unchecked[0], re.IGNORECASE):
        return pending, True
    return pending, False


def _verification_pending(verif_path):
    """Pending if the file is missing, empty, or its Result section still reads
    'Pending.' — so deleting/emptying the file cannot evade the gate."""
    if not verif_path.is_file():
        return True
    text = read_head(verif_path)
    if not text.strip():
        return True
    m = re.search(r"(?im)^##\s+Result\s*$(.*)", text, re.DOTALL)
    tail = m.group(1) if m else text
    return bool(re.search(r"(?im)^\s*Pending\.\s*$", tail))


def _packet_hash(pkg_dir):
    """sha256 (hex[:16]) over the heads of the packet's top-level .md files —
    content-based, so git checkouts / mtime changes that preserve content do not
    register as work, and no directory walk is needed."""
    h = hashlib.sha256()
    try:
        files = sorted(p for p in pkg_dir.glob("*.md") if p.is_file())[:_MAX_PACKETS]
    except OSError:
        files = []
    for f in files:
        h.update(f.name.encode("utf-8", "replace"))
        h.update(read_head(f).encode("utf-8", "replace"))
    return h.hexdigest()[:16]


def packet_state(pkg_dir):
    """Return {hash, pending, verification_pending, claimed_done} for one packet."""
    pending, done = _pending_and_done(read_head(pkg_dir / "tasks.md"))
    return {
        "hash": _packet_hash(pkg_dir),
        "pending": pending,
        "verification_pending": _verification_pending(pkg_dir / "verification.md"),
        "claimed_done": done,
    }


def fingerprint_project(root):
    """{packet_name: packet_state} for every active packet (kebab names only)."""
    out = {}
    changes = root / "sdd-plus" / "changes"
    try:
        dirs = sorted(p for p in changes.iterdir() if p.is_dir()) if changes.is_dir() else []
    except OSError:
        dirs = []
    for p in dirs[:_MAX_PACKETS]:
        if _KEBAB.match(p.name):
            out[p.name] = packet_state(p)
    return out


# --- session-state file (per-user dir, hashed name, atomic, validated) ------
def sanitize_sid(raw):
    """Return the raw session id if it is a usable string of adequate length,
    else None (never fall back to a shared/default id)."""
    if not isinstance(raw, str):
        return None
    raw = raw.strip()
    if len(raw) < _MIN_SID:
        return None
    return raw


def _state_dir():
    """Per-user app dir (never world-writable /tmp): %LOCALAPPDATA%/drydock or
    ~/.cache/drydock. Created 0o700. None on failure."""
    base = None
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
    if not base:
        base = os.environ.get("XDG_CACHE_HOME")
    if not base:
        try:
            base = str(Path.home() / ".cache")
        except (OSError, RuntimeError):
            base = None
    if not base:
        base = tempfile.gettempdir()
    try:
        d = Path(base) / "drydock"
        d.mkdir(parents=True, exist_ok=True, mode=0o700)
        return d
    except OSError:
        return None


def state_path(sid):
    d = _state_dir()
    if d is None:
        return None
    digest = hashlib.sha256(sid.encode("utf-8")).hexdigest()[:16]
    return d / f"drydock-state-{digest}.json"


def _valid_state(obj, sid):
    if not isinstance(obj, dict) or obj.get("v") != STATE_SCHEMA:
        return False
    if obj.get("session_id") != sid:
        return False
    fp = obj.get("fingerprints")
    if not isinstance(fp, dict) or len(fp) > _MAX_PACKETS:
        return False
    for name in fp:
        if not (isinstance(name, str) and _KEBAB.match(name)):
            return False
    nudged = obj.get("nudged")
    if not isinstance(nudged, list) or len(nudged) > _MAX_NUDGES:
        return False
    return True


def read_state(path, sid):
    """Parsed state dict if the file is a safe, valid, matching state file; else
    None (missing / symlink / oversized / corrupt / foreign all collapse here)."""
    import json
    if path is None:
        return None
    try:
        st = path.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_size > _MAX_STATE_BYTES:
            return None
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return obj if _valid_state(obj, sid) else None


def write_state(path, obj):
    """Atomic write (mkstemp + os.replace, 0o600). Returns True only if the new
    state is durably in place — callers gate any user-visible action on this."""
    import json
    if path is None:
        return False
    try:
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".drydock-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(json.dumps(obj))
            os.replace(tmp, str(path))
            return True
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            return False
    except OSError:
        return False


def new_state(sid, fingerprints):
    return {"v": STATE_SCHEMA, "session_id": sid, "fingerprints": fingerprints, "nudged": []}
