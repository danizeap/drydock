#!/usr/bin/env python3
"""Read-only Codex bridge for the Drydock conductor.

Four primitives, all proven live (see sdd-plus/specs/multi-agent-orchestration-vision.md §8):
  discover_core()      -> newest installed Codex core (never the stale sandbox copy)
  read_rate_limits()   -> Codex remaining-quota snapshot via app-server JSON-RPC
  route()              -> fuel-aware model selection (legible policy)
  delegate()           -> run a Codex `exec` turn, READ-ONLY, schema-locked output

Read-only by construction: delegation flags are hardcoded; no caller input can
enable writes or sandbox escalation. Secret-bearing content is refused before it
leaves the machine (`guard_outbound`, fail-closed).
"""
import glob
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

# ---------------------------------------------------------------------------
# Reuse the plugin's tested secret-path matcher (single source of truth).
# ---------------------------------------------------------------------------
def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    _HOOKS_DIR = os.path.join(_repo_root(), "hooks")
    if _HOOKS_DIR not in sys.path:
        sys.path.insert(0, _HOOKS_DIR)
    from protect_secrets import path_is_secret as _path_is_secret  # type: ignore
except Exception:  # pragma: no cover - exercised via fail-closed guard
    _path_is_secret = None

# Fixed safety flags for every delegation. No caller may override these.
_SAFETY_FLAGS = ["-s", "read-only", "--ephemeral", "--skip-git-repo-check"]
# Substrings that would break the read-only boundary; must never appear in argv.
FORBIDDEN_FLAGS = ("--dangerously-bypass-approvals-and-sandbox",
                   "workspace-write", "danger-full-access")

FLAGSHIP = "gpt-5.6-sol"
WORKHORSE = "gpt-5.4-mini"
CONSERVE_FLOOR_PCT = 15

# A model identifier is a bare token; reject anything flag-shaped as defense in depth.
_SAFE_MODEL = re.compile(r"^[A-Za-z0-9._\-]+$")


def _as_prefix(core):
    """Accept a core as a string exe path or a list argv prefix (for a fake)."""
    return [core] if isinstance(core, str) else list(core)


def _fail(stage, error, **extra):
    out = {"ok": False, "stage": stage, "error": error}
    out.update(extra)
    return out


# ---------------------------------------------------------------------------
# 1. DISCOVER
# ---------------------------------------------------------------------------
def discover_core(localappdata=None):
    """Newest `%LOCALAPPDATA%\\OpenAI\\Codex\\bin\\*\\codex.exe`, or None.

    Never returns the stale `~/.codex/.sandbox-bin` copy (it lives outside this
    discovery root by design).
    """
    root = localappdata or os.environ.get("LOCALAPPDATA", "")
    if not root:
        return None
    cands = glob.glob(os.path.join(root, "OpenAI", "Codex", "bin", "*", "codex.exe"))
    return max(cands, key=os.path.getmtime) if cands else None


# ---------------------------------------------------------------------------
# 2. FUEL GAUGE
# ---------------------------------------------------------------------------
def read_rate_limits(core, timeout_s=25):
    """Read Codex remaining quota via `app-server` JSON-RPC over stdio.

    Always returns a structured dict: {ok:true, result} or {ok:false, stage, ...}.
    Never raises for operational failures; always reaps the subprocess.
    """
    try:
        proc = subprocess.Popen(
            [*_as_prefix(core), "app-server"], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            bufsize=1, encoding="utf-8", errors="replace")
    except (OSError, ValueError) as e:
        return _fail("spawn", str(e))

    outq = queue.Queue()
    errbuf = []

    def pump_out(s):
        for ln in s:
            outq.put(ln.rstrip("\n"))
        outq.put(None)

    def pump_err(s):
        for ln in s:
            errbuf.append(ln.rstrip("\n"))
            if len(errbuf) > 40:
                del errbuf[:-40]

    threading.Thread(target=pump_out, args=(proc.stdout,), daemon=True).start()
    threading.Thread(target=pump_err, args=(proc.stderr,), daemon=True).start()

    def send(o):
        proc.stdin.write(json.dumps(o) + "\n")
        proc.stdin.flush()

    def err_tail():
        return "\n".join(errbuf[-8:])

    def wait_id(want, deadline):
        while time.monotonic() < deadline:
            try:
                ln = outq.get(timeout=0.3)
            except queue.Empty:
                if proc.poll() is not None:
                    return _fail("server_exit",
                                 f"app-server exited early (code {proc.returncode})",
                                 exit_code=proc.returncode, stderr=err_tail())
                continue
            if ln is None:
                return _fail("eof", "app-server closed stdout before responding",
                             exit_code=proc.poll(), stderr=err_tail())
            try:
                m = json.loads(ln)
            except Exception:
                continue
            if isinstance(m, dict) and m.get("id") == want and ("result" in m or "error" in m):
                return m
        return _fail("timeout", f"no response within {timeout_s}s", stderr=err_tail())

    try:
        end = time.monotonic() + timeout_s
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"clientInfo": {"name": "drydock-conductor", "version": "0.1.0"}}})
        init = wait_id(1, end)
        if init.get("ok") is False:
            return init
        if "error" in init:
            return _fail("initialize", init["error"], stderr=err_tail())
        try:
            send({"jsonrpc": "2.0", "method": "initialized"})
        except OSError:
            pass
        send({"jsonrpc": "2.0", "id": 2, "method": "account/rateLimits/read", "params": None})
        rl = wait_id(2, end)
        if rl.get("ok") is False:
            return rl
        if "error" in rl:
            return _fail("rateLimits", rl["error"], stderr=err_tail())
        return {"ok": True, "result": rl.get("result")}
    except (BrokenPipeError, OSError) as e:
        return _fail("io", str(e), stderr=err_tail())
    finally:
        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
        except OSError:
            pass
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=5)
            except Exception:
                pass
        except Exception:
            pass


def summarize_gauge(rl):
    """Flatten a read_rate_limits result into a compact routing view, or None."""
    if not rl or not rl.get("ok"):
        return None
    snap = (rl.get("result") or {}).get("rateLimits", {})
    prim = snap.get("primary") or {}
    used = prim.get("usedPercent")
    resets = prim.get("resetsAt")
    return {
        "plan": snap.get("planType"),
        "used_percent": used,
        "remaining_percent": (100 - used) if isinstance(used, int) else None,
        "window_mins": prim.get("windowDurationMins"),
        "resets_in_hours": round((resets - time.time()) / 3600, 1) if resets else None,
        "has_overflow_credits": (snap.get("credits") or {}).get("hasCredits"),
    }


# ---------------------------------------------------------------------------
# 3. ROUTE
# ---------------------------------------------------------------------------
def route(task_weight, gauge):
    """Legible, fuel-aware model selection. Never a hidden default."""
    remaining = (gauge or {}).get("remaining_percent")
    if task_weight == "heavy":
        if remaining is None or remaining > CONSERVE_FLOOR_PCT:
            return {"model": FLAGSHIP,
                    "reason": f"heavy task; {remaining}% fuel > {CONSERVE_FLOOR_PCT}% floor -> flagship"}
        return {"model": WORKHORSE,
                "reason": f"heavy task but only {remaining}% fuel -> conserve with workhorse"}
    return {"model": WORKHORSE, "reason": "light task -> workhorse model"}


# ---------------------------------------------------------------------------
# 4. SECRET GUARD (outbound)
# ---------------------------------------------------------------------------
def guard_outbound(paths):
    """Refusal reason if any path is secret-bearing, else None. Fails CLOSED:
    if the secret checker can't be loaded, refuse (never egress unchecked)."""
    if _path_is_secret is None:
        return "secret-path checker unavailable; refusing delegation (fail-closed)"
    for p in paths or ():
        if _path_is_secret(p):
            return f"refusing to send secret-bearing path to an external model: {p}"
    return None


# ---------------------------------------------------------------------------
# 5. DELEGATE (read-only)
# ---------------------------------------------------------------------------
def build_exec_argv(core, model, schema_path, out_file, cwd):
    """Assemble the exec argv with the fixed read-only safety prefix."""
    return [*_as_prefix(core), "exec", "--json", *_SAFETY_FLAGS,
            "-m", model, "-C", cwd,
            "--output-schema", schema_path, "--output-last-message", out_file]


def delegate(core, prompt, schema_path, model, cwd=None, timeout_s=240):
    """Run a single read-only Codex `exec` turn with schema-locked output.

    Returns {exit, usage, result, stderr_tail} on completion, or a structured
    {ok:false,...} on refusal/failure. `result` is the parsed schema-conforming
    JSON. No code path here writes into the repository: the working root defaults
    to a fresh temp dir (cleaned up) and the sandbox is always read-only.
    """
    if not _SAFE_MODEL.match(model or ""):
        return _fail("bad_model", f"unsafe model identifier: {model!r}")
    created_cwd = cwd is None
    tmp_cwd = cwd or tempfile.mkdtemp(prefix="drydock-conductor-")
    out_fd, out_file = tempfile.mkstemp(prefix="codex-out-", suffix=".json")
    os.close(out_fd)
    try:
        try:
            os.remove(out_file)  # let Codex create it fresh
        except OSError:
            pass
        argv = build_exec_argv(core, model, schema_path, out_file, tmp_cwd)
        t0 = time.monotonic()
        try:
            p = subprocess.run(argv, input=prompt, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=timeout_s)
        except subprocess.TimeoutExpired:
            return _fail("delegate_timeout", f"no completion within {timeout_s}s")
        except (OSError, ValueError) as e:
            return _fail("delegate_spawn", str(e))

        usage = None
        for ln in (p.stdout or "").splitlines():
            try:
                ev = json.loads(ln)
                if isinstance(ev, dict) and ev.get("type") == "turn.completed":
                    usage = ev.get("usage")
            except Exception:
                pass
        result = None
        if os.path.exists(out_file):
            try:
                with open(out_file, encoding="utf-8") as fh:
                    result = json.load(fh)
            except Exception as e:
                result = {"_parse_error": str(e)}
        return {"exit": p.returncode, "elapsed_s": round(time.monotonic() - t0, 1),
                "usage": usage, "result": result,
                "stderr_tail": (p.stderr or "")[-400:]}
    finally:
        try:
            if os.path.exists(out_file):
                os.remove(out_file)
        except OSError:
            pass
        if created_cwd:
            shutil.rmtree(tmp_cwd, ignore_errors=True)


def delegate_file(core, path, instruction, schema_path, model, cwd=None, timeout_s=240):
    """Delegate an analysis of a single file — guarding it against secret egress
    BEFORE anything is read or spawned."""
    refusal = guard_outbound([path])
    if refusal:
        return {"ok": False, "stage": "secret_guard", "error": refusal}
    try:
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
    except OSError as e:
        return _fail("read_target", str(e))
    prompt = (f"{instruction}\n\nFile: {os.path.basename(path)}\n\n"
              f"```\n{content}\n```")
    return delegate(core, prompt, schema_path, model, cwd=cwd, timeout_s=timeout_s)
