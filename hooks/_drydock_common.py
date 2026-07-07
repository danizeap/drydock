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


def _candidate_state_bases():
    """Ordered candidate base dirs for per-user state. The WRITE side uses the
    first usable one; the ledger READ side probes all of them, because the hook
    process and a script process can resolve different winners (python3-vs-python
    env divergence — a red-teamed silent-empty-ledger failure mode)."""
    out = []
    if os.name == "nt":
        la = os.environ.get("LOCALAPPDATA")
        if la:
            out.append(la)
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        out.append(xdg)
    try:
        out.append(str(Path.home() / ".cache"))
    except (OSError, RuntimeError):
        pass
    out.append(tempfile.gettempdir())
    return out


def _state_dir():
    """Per-user app dir (never world-writable /tmp): %LOCALAPPDATA%/drydock or
    ~/.cache/drydock. Created 0o700. None on failure."""
    for base in _candidate_state_bases():
        try:
            d = Path(base) / "drydock"
            d.mkdir(parents=True, exist_ok=True, mode=0o700)
            return d
        except OSError:
            continue
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


def bash_write_targets(command):
    """Best-effort set of paths a Bash command writes to (redirections, tee, cp/mv).
    Shared by protect_secrets (secret paths) and packet_guard (high-risk paths) so
    the two guards' extraction logic can never drift."""
    import shlex
    targets = []
    tokenized = True
    try:
        tokens = shlex.split(command, comments=False, posix=True)
    except ValueError:  # unbalanced quotes -> regex-only fallback below
        tokens = []
        tokenized = False
    for i, tok in enumerate(tokens):
        if tok in (">", ">>", "1>", "2>", "&>", ">|") and i + 1 < len(tokens):
            targets.append(tokens[i + 1])
        elif re.match(r"^\d*>>?\|?\S", tok) and re.match(r"^\d*>", tok):
            # attached redirection like >.env, >>out.log, 2>err.log
            targets.append(re.sub(r"^\d*>>?\|?", "", tok))
        elif tok == "tee":
            for nxt in tokens[i + 1:]:
                if not nxt.startswith("-"):
                    targets.append(nxt)
                    break
        elif tok in ("cp", "mv") and len(tokens) > i + 2:
            targets.append(tokens[-1])  # destination is the last argument
    if not tokenized:
        # Regex fallback ONLY when tokenization failed. Running it on successfully
        # tokenized commands treats '>' inside QUOTED arguments (grep patterns,
        # commit messages) as redirections — a wrongful-deny/false-block class
        # found by adversarial verification.
        for m in re.finditer(r">>?\|?\s*([^\s;|&>]+)", command):
            targets.append(m.group(1))
    return targets


def write_state(path, obj):
    """Atomic write (mkstemp + os.replace, 0o600). Returns True only if the new
    state is durably in place — callers gate any user-visible action on this.

    WRITER CONTRACT: the state file is shared by multiple hooks (orientation
    stamp, completion gate's `nudged`, packet guard's `warned`). Every writer
    MUST copy-and-update the existing dict, preserving keys it does not own —
    never reconstruct the dict from its own known fields."""
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


# --- event ledger (per-user, per-project, category-only, best-effort) --------
# The ledger is a DISPOSABLE telemetry cache feeding the Owner brief. Contract
# (red-team-derived, spec-pinned): appends fire only after a non-silent verdict
# is decided; they never fsync, never raise, and can never change a verdict or
# its delivery. Categories are validated HERE at the sink — callers cannot leak
# paths/commands into the file by mistake. DRYDOCK_PROBE=1 (set by the
# orientation liveness probe on its children) makes append a no-op so synthetic
# probe denies never pollute the Owner-facing history.
LEDGER_CATEGORIES = frozenset({
    "session",                       # orientation coverage marker (new sessions)
    "ledger-created",                # first line of every journal
    "packet-deny:migration",
    "packet-deny:new-ci",
    "packet-deny:container-config",
    "packet-deny:status-file",
    "packet-warn",
    "secrets-deny",
    "git-deny",
    "verify-nudge",
    "verify-run",                    # deterministic gate pass recorded by brief.py
})
PREVENTION_CATEGORIES = frozenset({
    "packet-deny:migration", "packet-deny:new-ci", "packet-deny:container-config",
    "packet-deny:status-file", "secrets-deny", "git-deny",
})
_LEDGER_HOOKS = frozenset({"packet_guard", "protect_secrets", "git_safety",
                           "completion_gate", "session_orient", "brief", "ledger"})
_LEDGER_ACTIONS = frozenset({"deny", "warn", "nudge", "session", "created", "verify"})
_MAX_LEDGER_BYTES = 256 * 1024   # writer rotation threshold
_LEDGER_TAIL_BYTES = 128 * 1024  # reader tail window (the true growth bound)
_MAX_EVENT_LINE = 512            # writer refuses longer lines; reader skips them
_MAX_EVENTS = 2000
_HEX16 = re.compile(r"^[0-9a-f]{16}$")


def _today():
    import time
    return time.strftime("%Y-%m-%d")


def ledger_path(root):
    d = _state_dir()
    if d is None:
        return None
    digest = hashlib.sha256(os.path.normcase(str(root)).encode("utf-8", "replace")).hexdigest()[:16]
    return d / f"drydock-journal-{digest}.ndjson"


def append_event(root, hook, action, category, extra=None):
    """Best-effort single-line NDJSON append. Never raises, returns None. Every
    field is validated/coerced at this sink; ts is DATE-ONLY (full timestamps
    would fingerprint work hours into a file the brief may summarize publicly)."""
    import json
    try:
        if os.environ.get("DRYDOCK_PROBE") == "1":
            return
        path = ledger_path(root)
        if path is None:
            return
        evt = {
            "ts": _today(),
            "hook": hook if hook in _LEDGER_HOOKS else "other",
            "action": action if action in _LEDGER_ACTIONS else "other",
            "category": category if category in LEDGER_CATEGORIES else "other",
        }
        if isinstance(extra, dict):
            pk, hs = extra.get("packet"), extra.get("hash")
            if isinstance(pk, str) and len(pk) <= 64 and _KEBAB.match(pk):
                evt["packet"] = pk
            if isinstance(hs, str) and _HEX16.match(hs):
                evt["hash"] = hs
        line = (json.dumps(evt, separators=(",", ":")) + "\n").encode("utf-8")
        if len(line) > _MAX_EVENT_LINE:
            return
        existed = True
        try:
            st = path.lstat()
            if not stat.S_ISREG(st.st_mode):
                return  # symlinked/odd journal: refuse to touch it
            if st.st_size > _MAX_LEDGER_BYTES:
                try:
                    os.replace(str(path), str(path) + ".1")
                    existed = False
                except OSError:
                    pass  # e.g. Windows sharing violation: append to the big file
        except OSError:
            existed = False
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(str(path), flags, 0o600)
        try:
            if not existed:
                born = {"ts": _today(), "hook": "ledger", "action": "created",
                        "category": "ledger-created"}
                os.write(fd, (json.dumps(born, separators=(",", ":")) + "\n").encode("utf-8"))
            os.write(fd, line)  # one complete line per single write: no torn lines
        finally:
            os.close(fd)
    except BaseException:
        return


def read_events(root):
    """Parsed event dicts from the ledger's tail window, oldest-first, or None if
    NO ledger could be read (callers must render that as 'unavailable' — absence
    is not zero). Probes every candidate base, mirrors read_state's lstat and
    size discipline, skips malformed/oversized lines instead of crashing."""
    import json
    digest = hashlib.sha256(os.path.normcase(str(root)).encode("utf-8", "replace")).hexdigest()[:16]
    name = f"drydock-journal-{digest}.ndjson"
    candidates = []
    primary = _state_dir()
    if primary is not None:
        candidates.append(primary / name)
    for base in _candidate_state_bases():
        p = Path(base) / "drydock" / name
        if p not in candidates:
            candidates.append(p)
    for path in candidates:
        try:
            st = path.lstat()
            if not stat.S_ISREG(st.st_mode):
                continue
            size = st.st_size
            with open(path, "rb") as f:
                if size > _LEDGER_TAIL_BYTES:
                    f.seek(size - _LEDGER_TAIL_BYTES)
                    f.readline()  # discard the partial first line
                data = f.read(_LEDGER_TAIL_BYTES + 4096)
        except OSError:
            continue
        events = []
        for ln in data.decode("utf-8", "replace").splitlines()[-_MAX_EVENTS:]:
            if not ln.strip() or len(ln) > _MAX_EVENT_LINE:
                continue
            try:
                obj = json.loads(ln)
            except ValueError:
                continue
            if (isinstance(obj, dict) and isinstance(obj.get("ts"), str)
                    and isinstance(obj.get("category"), str)):
                events.append(obj)
        return events
    return None


def project_fingerprint_hex(root):
    """One 16-hex token over active-packet states + archive dir names — the
    'has anything moved' signal embedded in OWNER_STATUS.md and compared by the
    orientation staleness sentinel."""
    h = hashlib.sha256()
    for name, st in sorted(fingerprint_project(root).items()):
        h.update(name.encode("utf-8", "replace"))
        h.update(str(st.get("hash", "")).encode("utf-8", "replace"))
    arch = root / "sdd-plus" / "archive"
    try:
        names = sorted(p.name for p in arch.iterdir() if p.is_dir())[:200] if arch.is_dir() else []
    except OSError:
        names = []
    for n in names:
        h.update(n.encode("utf-8", "replace"))
    return h.hexdigest()[:16]
