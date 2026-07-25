#!/usr/bin/env python3
"""Mutating delegation: Codex writes in an ISOLATED git worktree, gated before merge.

Codex gets its own worktree + `codex/…` branch with sandbox `workspace-write` — the
ONE place the conductor enables writes, confined to the worktree, never the Owner's
branch. The resulting diff passes an APPLICABILITY-FIRST gate (tests where they
apply; N/A is a clean pass, never a false fail). This module NEVER merges: it
returns a structured verdict + the diff + the worktree/branch for Claude to review
and merge deliberately. Every outcome is structured JSON.
"""
import argparse
import json
import os
import re
import signal
import shlex
import stat
import subprocess
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))  # scripts/ -> `conductor` importable
from conductor import codex_bridge as cb  # noqa: E402
from conductor import review as rv  # noqa: E402  (secret scan + fence, shared)

# Extensions whose change means "behavior changed" -> the test gate APPLIES.
_CODE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".go", ".rs",
             ".java", ".rb", ".php", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs",
             ".swift", ".kt", ".scala", ".sh", ".ps1", ".sql", ".lua", ".r",
             ".vue", ".svelte", ".dart", ".ex", ".exs", ".prisma"}
# Behavior-bearing files that carry no extension.
_CODE_BASENAMES = {"dockerfile", "containerfile", "makefile", "rakefile", "gemfile",
                   "procfile", "jenkinsfile", "vagrantfile", "justfile", "brewfile"}


def _is_code_file(path):
    base = os.path.basename(path)
    if base.lower() in _CODE_BASENAMES:
        return True
    return os.path.splitext(path)[1].lower() in _CODE_EXT


MAX_TEST_STEPS = 8
MAX_TEST_ARGS_PER_STEP = 128
MAX_TEST_PLAN_CHARS = 32768
MAX_TEST_ARG_CHARS = 8192
TEST_PROCESS_CLEANUP_TIMEOUT_S = 5
TEST_SANDBOX_PROFILE = "drydock_test_runner"
_SHELL_LAUNCHERS = {
    "bash", "sh", "zsh", "fish", "csh", "cmd", "command",
    "powershell", "pwsh", "wsl",
}
_WINDOWS_BATCH_SUFFIXES = {".bat", ".cmd"}


class TestPlanError(ValueError):
    """The requested test plan cannot be compiled under the bounded contract."""


class TestPlan:
    """Immutable, pre-resolved test commands compiled before delegation."""

    __slots__ = ("steps", "requested_steps", "source")

    def __init__(self, steps, requested_steps, source):
        self.steps = tuple(tuple(step) for step in steps)
        self.requested_steps = tuple(tuple(step) for step in requested_steps)
        self.source = source


class TestSandbox:
    """Pinned, locally-preflighted Codex sandbox command prefix."""

    __slots__ = ("prefix",)

    def __init__(self, prefix):
        self.prefix = tuple(prefix)


def _validate_sandbox_prefix(core):
    """Return an immutable absolute CLI prefix or fail closed."""
    try:
        prefix = cb._as_prefix(core)
    except (TypeError, ValueError) as exc:
        raise TestPlanError(f"invalid Codex sandbox command: {exc}") from exc
    if not prefix or not all(isinstance(argument, str) for argument in prefix):
        raise TestPlanError("Codex sandbox command must be a non-empty argv vector")
    if any(
        not argument or "\0" in argument or "\r" in argument or "\n" in argument
        for argument in prefix
    ):
        raise TestPlanError("Codex sandbox command contains an invalid argument")
    executable = os.path.realpath(prefix[0])
    try:
        metadata = os.stat(executable)
    except OSError as exc:
        raise TestPlanError(
            f"Codex sandbox executable is unavailable: {exc}"
        ) from exc
    if not os.path.isabs(executable) or not stat.S_ISREG(metadata.st_mode):
        raise TestPlanError(
            "Codex sandbox executable must resolve to an absolute regular file"
        )
    if os.name != "nt" and not os.access(executable, os.X_OK):
        raise TestPlanError("Codex sandbox executable is not executable")
    return (executable, *prefix[1:])


def _toml_basic_string(value):
    """Encode one dynamic config value without relying on shell quoting."""
    return (
        '"'
        + value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\b", "\\b")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\f", "\\f")
        .replace("\r", "\\r")
        + '"'
    )


def _sandbox_metadata(worktree):
    return {
        "mechanism": "codex sandbox permission profile",
        "profile": TEST_SANDBOX_PROFILE,
        "requested_write_scope": os.path.realpath(worktree),
        "requested_direct_network": "disabled",
        "per_run_boundary_verification": "not performed",
        "host_read_isolation": "not established",
        "trusted_configuration": "active Codex home plus managed configuration",
        "platform": sys.platform,
    }


def _build_test_sandbox_argv(prefix, worktree, step):
    """Build the model-free sandbox command for one already-validated step."""
    root = os.path.realpath(worktree)
    if not os.path.isabs(root) or not os.path.isdir(root):
        raise TestPlanError("test worktree must be an existing absolute directory")
    if len(root) > 4096:
        raise TestPlanError("test worktree path exceeds its character bound")
    root_value = _toml_basic_string(root)
    temp_root = _toml_basic_string(root)
    description = (
        f"permissions.{TEST_SANDBOX_PROFILE}.description="
        + _toml_basic_string("Drydock isolated test runner")
    )
    filesystem = (
        f"permissions.{TEST_SANDBOX_PROFILE}.filesystem="
        f'{{ ":minimal" = "read", {root_value} = "write" }}'
    )
    network = f"permissions.{TEST_SANDBOX_PROFILE}.network.enabled=false"
    environment = "shell_environment_policy.inherit='core'"
    environment_excludes = (
        "shell_environment_policy.ignore_default_excludes=false"
    )
    environment_temp = (
        "shell_environment_policy.set="
        f"{{ TEMP = {temp_root}, TMP = {temp_root}, TMPDIR = {temp_root} }}"
    )
    platform_config = (
        ["-c", "windows.sandbox='elevated'"] if os.name == "nt" else []
    )
    return [
        *prefix,
        "sandbox",
        *platform_config,
        "-c",
        description,
        "-c",
        filesystem,
        "-c",
        network,
        "-c",
        environment,
        "-c",
        environment_excludes,
        "-c",
        environment_temp,
        "-P",
        TEST_SANDBOX_PROFILE,
        "--include-managed-config",
        "--sandbox-state-disable-network",
        "-C",
        root,
        *step,
    ]


def prepare_test_sandbox(core, timeout_s=20):
    """Pin and execute a model-free readiness probe before delegation."""
    prefix = _validate_sandbox_prefix(core)
    try:
        with tempfile.TemporaryDirectory(
            prefix="drydock-test-sandbox-readiness-"
        ) as probe_root:
            argv = _build_test_sandbox_argv(
                prefix,
                probe_root,
                [sys.executable, "-c", "pass"],
            )
            process, timeout_output, timeout_cleanup = _run_test_step(
                argv,
                probe_root,
                timeout_s,
            )
            if timeout_cleanup is not None:
                cleanup_state = (
                    "confirmed"
                    if timeout_cleanup.get("confirmed")
                    else "unconfirmed"
                )
                detail = (timeout_output or "")[-200:]
                raise TestPlanError(
                    f"Codex sandbox readiness probe exceeded {timeout_s}s; "
                    f"process-tree cleanup {cleanup_state}"
                    + (f": {detail}" if detail else "")
                )
    except (OSError, ValueError) as exc:
        raise TestPlanError(
            f"Codex sandbox readiness probe could not start: {exc}"
        ) from exc
    if process.returncode != 0:
        detail = ((process.stderr or "") + (process.stdout or ""))[-400:]
        raise TestPlanError(
            "Codex sandbox readiness probe failed"
            + (f": {detail}" if detail else "")
        )
    return TestSandbox(prefix)


def _validate_test_sandbox(sandbox):
    if not isinstance(sandbox, TestSandbox):
        raise TestPlanError(
            "a prepared Codex test sandbox is required; direct execution is refused"
        )
    prefix = _validate_sandbox_prefix(sandbox.prefix)
    if prefix != sandbox.prefix:
        raise TestPlanError("prepared Codex sandbox command changed after readiness")
    return sandbox


def _captured_text(value):
    """Normalize TimeoutExpired output without assuming text-mode behavior."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _start_test_process(argv, worktree):
    """Start one sandboxed test in an OS grouping suitable for timeout cleanup."""
    kwargs = {
        "cwd": worktree,
        "shell": False,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(argv, **kwargs)


def _windows_taskkill_path():
    """Return the absolute system taskkill path without consulting PATH."""
    system_root = os.environ.get("SystemRoot")
    if not system_root or not os.path.isabs(system_root):
        return None
    candidate = os.path.realpath(
        os.path.join(system_root, "System32", "taskkill.exe")
    )
    try:
        metadata = os.stat(candidate)
    except OSError:
        return None
    if not stat.S_ISREG(metadata.st_mode):
        return None
    return candidate


def _posix_process_group_exists(group_id):
    try:
        os.killpg(group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _terminate_test_process_tree(process, timeout_s=TEST_PROCESS_CLEANUP_TIMEOUT_S):
    """Attempt bounded tree cleanup and return evidence, never a silent success."""
    mechanism = (
        "taskkill /T /F"
        if os.name == "nt"
        else "POSIX process-group SIGTERM/SIGKILL"
    )
    evidence = {
        "attempted": True,
        "mechanism": mechanism,
        "confirmed": False,
        "direct_process_stopped": process.poll() is not None,
        "escaped_descendants": "not ruled out",
        "detail": None,
    }
    deadline = time.monotonic() + max(0.1, timeout_s)
    if os.name == "nt":
        taskkill = _windows_taskkill_path()
        if taskkill is None:
            evidence["detail"] = "absolute system taskkill executable unavailable"
        else:
            remaining = max(0.1, deadline - time.monotonic())
            try:
                killer = subprocess.run(
                    [
                        taskkill,
                        "/PID",
                        str(process.pid),
                        "/T",
                        "/F",
                    ],
                    shell=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=remaining,
                )
                evidence["detail"] = (
                    f"taskkill exited {killer.returncode}: "
                    + ((killer.stdout or "") + (killer.stderr or ""))[-300:]
                ).strip()
                evidence["confirmed"] = killer.returncode == 0
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                evidence["detail"] = f"taskkill failed: {exc}"
    else:
        group_id = process.pid
        try:
            os.killpg(group_id, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except OSError as exc:
            evidence["detail"] = f"process-group SIGTERM failed: {exc}"
        remaining = max(0.0, deadline - time.monotonic())
        if remaining:
            try:
                process.wait(timeout=min(0.5, remaining))
            except subprocess.TimeoutExpired:
                pass
        if _posix_process_group_exists(group_id):
            try:
                os.killpg(group_id, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError as exc:
                evidence["detail"] = f"process-group SIGKILL failed: {exc}"
        evidence["confirmed"] = not _posix_process_group_exists(group_id)
        if evidence["detail"] is None:
            evidence["detail"] = "process-group termination completed"

    if process.poll() is None:
        try:
            process.kill()
        except OSError:
            pass
        remaining = max(0.0, deadline - time.monotonic())
        if remaining:
            try:
                process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                pass
    evidence["direct_process_stopped"] = process.poll() is not None
    if os.name != "nt" and evidence["direct_process_stopped"]:
        evidence["confirmed"] = not _posix_process_group_exists(process.pid)
    evidence["confirmed"] = bool(
        evidence["confirmed"] and evidence["direct_process_stopped"]
    )
    return evidence


def _run_test_step(argv, worktree, timeout_s):
    """Run one sandbox step and return (process, timeout_output, cleanup)."""
    process = _start_test_process(argv, worktree)
    try:
        stdout, stderr = process.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        cleanup = _terminate_test_process_tree(process)
        timeout_output = _captured_text(exc.stdout) + _captured_text(exc.stderr)
        try:
            stdout, stderr = process.communicate(timeout=1)
        except subprocess.TimeoutExpired as final_exc:
            cleanup["confirmed"] = False
            cleanup["detail"] = (
                (cleanup.get("detail") or "")
                + "; output pipes remained open after tree cleanup"
            ).strip("; ")
            timeout_output += _captured_text(
                final_exc.stdout
            ) + _captured_text(final_exc.stderr)
            for stream in (process.stdout, process.stderr):
                try:
                    if stream is not None:
                        stream.close()
                except OSError:
                    pass
        else:
            timeout_output = _captured_text(stdout) + _captured_text(stderr)
        return None, timeout_output, cleanup
    return (
        subprocess.CompletedProcess(
            argv, process.returncode, stdout=stdout, stderr=stderr
        ),
        None,
        None,
    )


def decode_test_argv_json(raw):
    """Decode one argv vector or a list of argv vectors from the CLI."""
    try:
        value = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise TestPlanError(f"--test-argv-json is not valid JSON: {exc}") from exc
    if not isinstance(value, list) or not value:
        raise TestPlanError(
            "--test-argv-json must be a non-empty argv array or array of argv arrays"
        )
    if all(isinstance(item, str) for item in value):
        return value
    if all(
        isinstance(item, list)
        and item
        and all(isinstance(argument, str) for argument in item)
        for item in value
    ):
        return value
    raise TestPlanError(
        "--test-argv-json must contain only strings in one argv array "
        "or non-empty argv arrays"
    )


def _windows_split_arguments(command):
    """Apply Windows' native command-line quoting rules without invoking cmd."""
    import ctypes
    from ctypes import wintypes

    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    shell32.CommandLineToArgvW.argtypes = [
        wintypes.LPCWSTR,
        ctypes.POINTER(ctypes.c_int),
    ]
    shell32.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
    kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
    kernel32.LocalFree.restype = wintypes.HLOCAL
    count = ctypes.c_int()
    values = shell32.CommandLineToArgvW(command, ctypes.byref(count))
    if not values:
        raise TestPlanError(
            f"Windows could not parse the legacy test command: {ctypes.get_last_error()}"
        )
    try:
        return [values[index] for index in range(count.value)]
    finally:
        kernel32.LocalFree(values)


def _split_legacy_test_steps(command):
    """Accept only simple commands and `&&`, never general shell grammar."""
    if not isinstance(command, str) or not command.strip():
        raise TestPlanError("legacy test command must be a non-empty string")
    if len(command) > MAX_TEST_PLAN_CHARS:
        raise TestPlanError("test plan exceeds its character bound")
    posix = os.name != "nt"
    in_single = False
    in_double = False
    current = []
    steps = []
    index = 0
    while index < len(command):
        character = command[index]
        if character in "\r\n\0":
            raise TestPlanError("newlines and NUL bytes are not allowed in a test plan")
        if character == "`" or (
            character == "$"
            and index + 1 < len(command)
            and command[index + 1] == "("
        ):
            raise TestPlanError(
                "command substitution is not allowed in a test plan"
            )
        if posix and character == "\\" and not in_single:
            if index + 1 >= len(command):
                raise TestPlanError("legacy test command ends with an escape")
            current.extend((character, command[index + 1]))
            index += 2
            continue
        if character == "'" and posix and not in_double:
            in_single = not in_single
            current.append(character)
            index += 1
            continue
        if character == '"' and not in_single:
            if posix:
                in_double = not in_double
            else:
                slash_count = 0
                cursor = index - 1
                while cursor >= 0 and command[cursor] == "\\":
                    slash_count += 1
                    cursor -= 1
                if slash_count % 2 == 0:
                    in_double = not in_double
            current.append(character)
            index += 1
            continue
        if not in_single and not in_double:
            if character == "&":
                if index + 1 < len(command) and command[index + 1] == "&":
                    step = "".join(current).strip()
                    if not step:
                        raise TestPlanError("empty command before or after &&")
                    steps.append(step)
                    current = []
                    index += 2
                    continue
                raise TestPlanError(
                    "bare '&' and background/sequencing operators are not allowed"
                )
            if character == "|":
                raise TestPlanError("pipes and '||' are not allowed in a test plan")
            if character in ";<>":
                raise TestPlanError(
                    "shell sequencing and redirects are not allowed in a test plan"
                )
        current.append(character)
        index += 1
    if in_single or in_double:
        raise TestPlanError("legacy test command contains an unterminated quote")
    final = "".join(current).strip()
    if not final:
        raise TestPlanError("empty command before or after &&")
    steps.append(final)
    parsed = []
    for step in steps:
        try:
            arguments = (
                shlex.split(step, posix=True)
                if posix
                else _windows_split_arguments(step)
            )
        except ValueError as exc:
            raise TestPlanError(
                f"legacy test command could not be parsed: {exc}"
            ) from exc
        if not arguments:
            raise TestPlanError("test step has no executable")
        parsed.append(arguments)
    return parsed


def _resolve_test_executable(name):
    """Resolve a bare executable from absolute parent PATH entries only."""
    if (
        not isinstance(name, str)
        or not name
        or os.path.isabs(name)
        or os.path.basename(name) != name
        or "/" in name
        or "\\" in name
        or name in (".", "..")
    ):
        raise TestPlanError(
            "each test step must name a bare executable from the parent PATH"
        )
    if os.name == "nt":
        _, suffix = os.path.splitext(name)
        if suffix:
            names = [name]
        else:
            extensions = [
                value.lower()
                for value in os.environ.get(
                    "PATHEXT", ".COM;.EXE;.BAT;.CMD"
                ).split(os.pathsep)
                if value
            ]
            names = [name + extension for extension in extensions]
    else:
        names = [name]
    for raw_directory in os.environ.get("PATH", "").split(os.pathsep):
        value = raw_directory.strip().strip('"')
        if not value or not os.path.isabs(value):
            continue
        directory = os.path.abspath(value)
        for candidate_name in names:
            candidate = os.path.join(directory, candidate_name)
            try:
                resolved = os.path.realpath(candidate)
                metadata = os.stat(resolved)
            except OSError:
                continue
            if not stat.S_ISREG(metadata.st_mode):
                continue
            if os.name != "nt" and not os.access(resolved, os.X_OK):
                continue
            writable_roots = {
                os.path.realpath(value)
                for value in (
                    tempfile.gettempdir(),
                    os.environ.get("TEMP"),
                    os.environ.get("TMP"),
                    os.environ.get("TMPDIR"),
                )
                if value and os.path.isabs(value)
            }
            try:
                in_worker_writable_root = any(
                    os.path.commonpath((resolved, root)) == root
                    for root in writable_roots
                )
            except (OSError, ValueError):
                in_worker_writable_root = True
            if in_worker_writable_root:
                raise TestPlanError(
                    f"test executable {name!r} resolves inside a temporary "
                    "directory writable by the mutating worker"
                )
            return resolved
    raise TestPlanError(
        f"test executable {name!r} was not found in an absolute parent PATH entry"
    )


def compile_test_plan(specification):
    """Validate and pin an optional test plan before the worker can write."""
    if specification is None or specification == "":
        return None
    if isinstance(specification, TestPlan):
        if specification.source not in {"legacy-string", "structured-argv"}:
            raise TestPlanError("compiled test plan has an invalid source")
        try:
            requested_copy = [
                list(step) for step in specification.requested_steps
            ]
        except (TypeError, ValueError) as exc:
            raise TestPlanError("compiled test plan has an invalid shape") from exc
        recompiled = compile_test_plan(requested_copy)
        if recompiled.steps != specification.steps:
            raise TestPlanError(
                "compiled test plan does not match its validated absolute argv"
            )
        return specification
    if isinstance(specification, str):
        requested = _split_legacy_test_steps(specification)
        source = "legacy-string"
    elif isinstance(specification, (list, tuple)) and specification:
        if all(isinstance(item, str) for item in specification):
            requested = [list(specification)]
        elif all(
            isinstance(item, (list, tuple))
            and item
            and all(isinstance(argument, str) for argument in item)
            for item in specification
        ):
            requested = [list(item) for item in specification]
        else:
            raise TestPlanError(
                "structured test plan must be one argv vector or a list of argv vectors"
            )
        source = "structured-argv"
    else:
        raise TestPlanError(
            "test plan must be a legacy string, argv vector, or list of argv vectors"
        )
    if len(requested) > MAX_TEST_STEPS:
        raise TestPlanError(f"test plan exceeds {MAX_TEST_STEPS} steps")
    total_characters = 0
    resolved_steps = []
    for step in requested:
        if not step or len(step) > MAX_TEST_ARGS_PER_STEP:
            raise TestPlanError(
                f"each test step must contain 1-{MAX_TEST_ARGS_PER_STEP} arguments"
            )
        for argument in step:
            if "\0" in argument or "\r" in argument or "\n" in argument:
                raise TestPlanError(
                    "structured test arguments cannot contain NUL or newline bytes"
                )
            if len(argument) > MAX_TEST_ARG_CHARS:
                raise TestPlanError("one test argument exceeds its character bound")
            total_characters += len(argument)
            if total_characters > MAX_TEST_PLAN_CHARS:
                raise TestPlanError("test plan exceeds its character bound")
        requested_name = step[0]
        normalized_name = os.path.splitext(
            os.path.basename(requested_name)
        )[0].lower()
        if normalized_name in _SHELL_LAUNCHERS:
            raise TestPlanError(
                f"shell launcher {requested_name!r} is not allowed in a test plan"
            )
        executable = _resolve_test_executable(requested_name)
        if os.path.splitext(executable)[1].lower() in _WINDOWS_BATCH_SUFFIXES:
            raise TestPlanError(
                "Windows batch/command shims are not allowed because the OS may "
                "dispatch them through a shell"
            )
        resolved_steps.append([executable, *step[1:]])
    return TestPlan(resolved_steps, requested, source)


_RUNNER_FIRST = {
    "make",
    "bash",
    "sh",
    "cmd",
    "powershell",
    "pwsh",
    "yarn",
    "pnpm",
    "env",
    "xargs",
    "nice",
    "timeout",
    "nohup",
    "stdbuf",
    "setsid",
    "script",
    "busybox",
    "doskey",
    "perl",
    "python",
    "python3",
    "py",
    "node",
    "nodejs",
    "ruby",
    "php",
}


def _delegates_to_runner(cmd):
    """Name the script-runner a command delegates to, if any.

    This matcher can only judge the SHAPE of the top-level command. If that
    command hands off to a runner (`npm run ci`, `make test`, `bash -c '…'`), any
    masking inside that script is invisible to us — `bash -c "false; true"` is a
    genuinely simple command that exits 0. We cannot detect it, so we DISCLOSE it.
    """
    toks = list(cmd) if isinstance(cmd, (list, tuple)) else (cmd or "").split()
    if not toks:
        return None
    first = os.path.splitext(os.path.basename(toks[0]))[0].lower()
    if first in _RUNNER_FIRST:
        return first
    if first == "npm" and len(toks) >= 2 and toks[1].lower() in ("run", "test"):
        return f"npm {toks[1].lower()}"
    return None


_TEST_DIR_SEGMENTS = {"test", "tests", "spec", "specs", "__tests__"}


def _looks_like_test(path):
    """Segment/filename precise — must NOT count `latest.py`, `inspector.py`,
    `contest.ts` as tests (a substring match silently suppressed the advisory)."""
    p = path.replace("\\", "/").lower()
    parts = p.split("/")
    if any(seg in _TEST_DIR_SEGMENTS for seg in parts[:-1]):
        return True
    name = parts[-1]
    stem = name.split(".")[0]
    return (name.startswith("test_") or stem.endswith("_test") or stem.endswith("_spec")
            or ".test." in name or ".spec." in name)


def _has_shell_masking(cmd):
    """Compatibility predicate backed by the fail-closed legacy parser."""
    try:
        _split_legacy_test_steps(cmd)
        return False
    except TestPlanError:
        return True


def _int_or_none(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _num_or_none(v):
    """`isinstance(True, (int, float))` is True in Python, and JSON `true` decodes
    to it — so an unguarded gauge reading turns a boolean into an arithmetic
    result. Guarding the token path and not this one produced a literal `0`."""
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def summarize_cost(usage, gauge_before, gauge_after, elapsed_s=None):
    """What the run actually cost.

    Field report #2 corrected the roles. The weekly fuel gauge reads in integer
    percent, so a typical task (181k input tokens on a real repo) moves it by less
    than 1% — below its own resolution. Reporting that as `fuel_used_percent: 0`
    reads as "free", which is the same absence-of-evidence-as-reassurance failure
    the boolean gauge was: below-resolution is NOT zero.

    So TOKENS are the per-task cost signal — they have resolution at task scale —
    and the fuel delta is the coarse "am I draining the window" signal, reported
    only when the gauge actually moved. Every field is `None` when unmeasured; a
    measurable-but-sub-resolution delta is `null` with `fuel_resolution` set, never 0.
    """
    u = usage if isinstance(usage, dict) else {}
    # Codex has shipped both `input_tokens` and `prompt_tokens` spellings.
    inp = _int_or_none(u.get("input_tokens", u.get("prompt_tokens")))
    out = _int_or_none(u.get("output_tokens", u.get("completion_tokens")))
    cached = _int_or_none(u.get("cached_input_tokens", u.get("cache_read_input_tokens")))
    total = _int_or_none(u.get("total_tokens"))
    # Only a COMPLETE pair yields a total: `(inp or 0) + (out or 0)` silently
    # asserts that the missing half was zero, in a dict whose own note says
    # null means not measured.
    if total is None and inp is not None and out is not None:
        total = inp + out

    def _used(g):
        return _num_or_none(g.get("used_percent")) if isinstance(g, dict) else None

    b, a = _used(gauge_before), _used(gauge_after)
    spent = bool((total or 0) or (inp or 0) or (out or 0))
    # A real before AND after yield a delta; a reset mid-run makes it negative and
    # meaningless. And a zero delta while tokens were clearly spent means the task
    # cost less than the gauge can resolve — that is `null`, not `0`.
    delta, resolution = None, None
    if isinstance(b, (int, float)) and isinstance(a, (int, float)):
        d = round(a - b, 2)
        if d < 0:
            resolution = "window reset mid-run"
        elif d == 0 and spent:
            resolution = "below gauge resolution (<1% of the weekly window)"
        else:
            delta = d
    return {"input_tokens": inp, "cached_input_tokens": cached, "output_tokens": out,
            "total_tokens": total, "fuel_used_percent": delta,
            "fuel_resolution": resolution,
            "fuel_used_before_percent": b, "fuel_used_after_percent": a,
            "elapsed_s": elapsed_s,
            "note": ("token counts are the per-task cost (they have resolution at task "
                     "scale); fuel_used_percent is the coarse window-drain signal and is "
                     "null when the task cost less than the gauge can resolve — see "
                     "fuel_resolution. Both are null when unmeasured, never zero. "
                     "fuel_used_*_percent are USED percentages (opposite of the gauge's "
                     "remaining_percent).")}


def _git(args, cwd=None, timeout=60):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)


def _slugify(s):
    keep = "".join(c if c.isalnum() or c in "-_" else "-" for c in (s or "").lower())
    return (keep.strip("-") or "task")[:40]


def create_worktree(base, task):
    """Create an isolated worktree + a fresh `codex/…` branch from `base`.
    Returns (worktree, branch, None) or (None, None, error) — never raises."""
    try:
        wt = tempfile.mkdtemp(prefix="drydock-codex-wt-")
    except OSError as e:
        return None, None, f"mkdtemp failed: {e}"
    branch = f"codex/{_slugify(task)}-{os.path.basename(wt)[-6:]}"
    try:
        r = _git(["worktree", "add", wt, "-b", branch, base])
    except (OSError, subprocess.SubprocessError) as e:  # git absent, timeout, etc.
        try:
            os.rmdir(wt)
        except OSError:
            pass
        return None, None, f"git worktree add failed: {e}"
    if r.returncode != 0:
        try:
            os.rmdir(wt)
        except OSError:
            pass
        return None, None, r.stderr.strip()
    return wt, branch, None


def cleanup_worktree(worktree, branch=None):
    """Remove a codex worktree and (ONLY) a `codex/` branch — never anything else."""
    if worktree and os.path.isdir(worktree):
        _git(["worktree", "remove", "--force", worktree])
    if worktree and not os.path.isdir(worktree) and branch and branch.startswith("codex/"):
        _git(["branch", "-D", branch])
    return True


def _worktree_has_work(path):
    """True if a codex worktree holds work worth keeping — UNCOMMITTED changes OR
    commits unique to its codex branch. Fails SAFE: on any doubt it returns True,
    because the whole point is never to destroy salvageable work (the N2 lesson).

    'no uncommitted changes' is NOT 'no work' — Codex or an operator can commit
    inside the worktree. A tip that no non-codex branch contains is unique work.
    """
    st = _git(["status", "--porcelain"], cwd=path)
    if st.returncode != 0 or (st.stdout or "").strip():
        return True                        # uncommitted work, or can't tell -> keep
    r = _git(["branch", "--contains", "HEAD", "--format=%(refname)"], cwd=path)
    if r.returncode != 0:
        return True                        # can't tell -> keep
    containers = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
    # If some NON-codex branch already contains this tip, the worktree added no
    # unique commits. If only codex branches contain it (or none do), keep it.
    return not any("refs/heads/codex/" not in c for c in containers)


def gc_worktrees(dry_run=False):
    """Sweep orphaned `codex/` worktrees. Field report #2, N3: an externally-killed
    run left a worktree + branch behind with no cleanup path.

    Blast-radius rules, inherited from cleanup_worktree: only `codex/` branches are
    ever touched, and — the N2 lesson — a worktree that still holds work (uncommitted
    OR committed-and-unique) is KEPT and reported, never auto-removed. Only worktrees
    with genuinely nothing to salvage go.
    """
    _git(["worktree", "prune"])           # drop admin entries for already-deleted trees
    r = _git(["worktree", "list", "--porcelain"])
    entries, cur = [], {}
    for ln in (r.stdout or "").splitlines():
        if ln.startswith("worktree "):
            if cur:
                entries.append(cur)
            cur = {"path": ln[len("worktree "):].strip()}
        elif ln.startswith("branch "):
            cur["branch"] = ln[len("branch "):].strip()
    if cur:
        entries.append(cur)

    removed, kept = [], []
    for e in entries:
        ref = e.get("branch", "")
        if "refs/heads/codex/" not in ref:
            continue                       # never touch a non-codex worktree
        path, branch = e["path"], ref.split("refs/heads/", 1)[-1]
        # A missing dir means git still tracks a deleted tree; nothing to salvage.
        has_work = _worktree_has_work(path) if os.path.isdir(path) else False
        if has_work:
            kept.append({"worktree": path, "branch": branch,
                         "reason": "holds work (uncommitted or committed) — "
                                   "salvage or remove manually"})
        else:
            if not dry_run:
                cleanup_worktree(path, branch)
            removed.append({"worktree": path, "branch": branch})
    return {"ok": True, "removed": removed, "kept_with_work": kept, "dry_run": dry_run}


# Field report #2, N1: the 64KB per-file cap sat below a real 90KB source file, and
# was ASYMMETRIC with review.py's 256KB — a file could be reviewable but not scopable.
# Since repo ingestion is the dominant cost, scoping is the ONLY lever on it, so it
# must not fail on the files most worth scoping. Share review.py's caps so the two
# paths can never drift apart again.
MAX_INLINE_FILE_BYTES = rv.MAX_FILE_BYTES     # 256 KB, == --diff per-file
MAX_INLINE_BYTES = rv.MAX_TOTAL_BYTES         # 512 KB, == --diff total
MAX_INLINE_FILES = 64          # names are payload too: 50k names built an 839KB prompt


def build_scoped_task(task, worktree, files):
    """Inline the named edit targets into the task prompt.

    SOFT scoping by design. The reporter's own 3-file change was a tool body, a
    test's expected-tools list, and i18n labels — coupled files that are NOT
    discoverable from the target's name. The files an operator forgets to name are
    exactly the ones that make the change complete, so a hard boundary would turn
    an under-scoped run into a red gate caused by the scoping, not the code.
    Inlining removes the need to CRAWL for the targets; it does not forbid reading.

    Returns (prompt, error). Content leaves the machine here, so the same
    by-name/by-content refusal `review.py` applies to explicitly named paths
    applies here too.
    """
    if not files:
        return task, None
    if len(files) > MAX_INLINE_FILES:
        return None, (f"{len(files)} files named; the limit is {MAX_INLINE_FILES}. Names are "
                      "payload too — scoping is for a small coupled change, so omit --files "
                      "for a wide sweep")
    root = os.path.realpath(worktree)
    blocks, names, total = [], [], 0
    for rel in files:
        rel = rel.replace("\\", "/")
        if os.path.isabs(rel) or (len(rel) > 1 and rel[1] == ":"):
            return None, f"--files takes repo-relative paths; got an absolute path: {rel}"
        full = os.path.normpath(os.path.join(root, *rel.split("/")))
        rp = os.path.realpath(full)
        # CONTAINMENT — `../../../secrets.txt` read straight out of the worktree.
        if not (rp == root or rp.startswith(root + os.sep)):
            return None, f"path resolves outside the worktree: {rel}"
        # realpath in the guard too: without it a hardlink or symlink alias with an
        # innocent name walks a secret file straight past the name check.
        if cb.guard_outbound([rel, full, rp]):
            return None, f"refusing to inline secret-bearing path: {rel}"
        if not os.path.isfile(full):
            # A named target may legitimately not exist yet (a file to be created).
            names.append(rel)
            continue
        # Size AND content from one handle, hard-capped — the same treatment
        # review.py gives an explicitly named path, which R3 promises.
        try:
            with open(full, "rb") as fh:
                size = os.fstat(fh.fileno()).st_size
                if size > MAX_INLINE_FILE_BYTES:
                    return None, (f"{rel} is {size} bytes (> {MAX_INLINE_FILE_BYTES} per-file "
                                  "inline limit)")
                if total + size > MAX_INLINE_BYTES:
                    return None, (f"named files exceed the {MAX_INLINE_BYTES}-byte inline "
                                  "budget — name fewer files, or omit --files")
                raw = fh.read(MAX_INLINE_FILE_BYTES + 1)
        except OSError as e:
            return None, f"{rel}: {e}"
        if len(raw) > MAX_INLINE_FILE_BYTES:
            return None, f"{rel} grew past the {MAX_INLINE_FILE_BYTES} limit while being read"
        text = raw.decode("utf-8", errors="replace")
        if rv.content_has_secret(text):
            return None, f"{rel} contains what looks like secret material; not sending"
        total += len(raw)
        names.append(rel)
        blocks.append((rel, text))

    marker = rv._fence("\n".join(t for _, t in blocks), "\n".join(names), task)
    parts = [task, "\n\n--- EDIT TARGETS ---\n",
             "Start from these files; their current content is included below so you do "
             "not need to search for them. You MAY read or edit other files when the "
             "change genuinely requires it (a test that asserts a list, a translation "
             "file, a caller that must be updated) — anything you touch outside this set "
             "is reported to the reviewer, not blocked. Do not crawl the repository "
             "looking for work that was not asked for.\n",
             "Files in scope: " + ", ".join(names) + "\n"]
    for rel, text in blocks:
        parts.append(f"\n=== BEGIN {marker} {rel} ===\n{text}\n=== END {marker} ===\n")
    return "".join(parts), None


def assess_scope(declared, changed):
    """Which edits landed outside what the operator declared. Disclosure, not a gate."""
    if not declared:
        return None
    def _norm(d):
        d = d.replace("\\", "/")
        # `lstrip("./")` strips a CHARACTER SET, so `.github/…` became `github/…`
        # and every dotfile reported a false out-of-scope edit.
        return d[2:] if d.startswith("./") else d

    norm = {_norm(d) for d in declared}
    touched = [c.replace("\\", "/") for c in changed]
    outside = sorted(c for c in touched if c not in norm)
    untouched = sorted(n for n in norm if n not in set(touched))
    return {"declared": sorted(norm), "out_of_scope": outside,
            "declared_untouched": untouched, "honored": not outside}


DEFAULT_MUTATE_TIMEOUT = 900   # up from 600: a mechanical sweep legitimately runs longer
MAX_MUTATE_TIMEOUT = 3600


def _usage_from(stdout):
    usage = None
    for ln in (stdout or "").splitlines():
        try:
            ev = json.loads(ln)
            if isinstance(ev, dict) and ev.get("type") == "turn.completed":
                usage = ev.get("usage")
        except Exception:
            pass
    return usage


def delegate_mutation(core, worktree, task, model, timeout_s=DEFAULT_MUTATE_TIMEOUT):
    """Run Codex with sandbox=workspace-write, confined to `worktree`. This is the
    ONLY conductor path that enables writes; it never runs against the Owner's tree.

    On timeout, whatever Codex already wrote to the worktree is real work. The
    result carries `partial: True` so the caller keeps the tree instead of deleting
    it — discarding a timed-out sweep's 100 insertions is the failure this avoids."""
    if not cb._SAFE_MODEL.match(model or ""):
        return {"ok": False, "stage": "bad_model", "error": repr(model)}
    argv = [*cb._as_prefix(core), "exec", "--json", "--skip-git-repo-check",
            "-s", "workspace-write", "-m", model, "-C", worktree]
    try:
        p = subprocess.run(argv, input=task, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout_s)
    except subprocess.TimeoutExpired as e:
        # capture_output populates .stdout/.stderr with what was captured before the
        # kill, so a partial usage read and the salvage flag both survive.
        return {"ok": False, "stage": "delegate_timeout", "partial": True,
                "timeout_s": timeout_s, "usage": _usage_from(e.stdout),
                "hint": (f"exceeded {timeout_s}s; re-run with --timeout up to "
                         f"{MAX_MUTATE_TIMEOUT}, or scope the task"),
                "stderr_tail": (e.stderr or "")[-400:]}
    except (OSError, ValueError) as e:
        return {"ok": False, "stage": "delegate_spawn", "error": str(e)}
    return {"ok": p.returncode == 0, "exit": p.returncode, "usage": _usage_from(p.stdout),
            "stderr_tail": (p.stderr or "")[-400:]}


def extract_changes(worktree, base):
    """Stage everything Codex produced in the worktree and diff it against base."""
    _git(["add", "-A"], cwd=worktree)
    names = _git(["diff", "--cached", "--name-only", base], cwd=worktree)
    files = [f for f in names.stdout.splitlines() if f.strip()]
    diff = _git(["diff", "--cached", base], cwd=worktree).stdout
    return files, diff


def _runner_note(steps):
    runners = []
    for step in steps or []:
        runner = _delegates_to_runner(step)
        if runner and runner not in runners:
            runners.append(runner)
    if not runners:
        return None
    return (
        "test plan delegates to "
        + ", ".join(repr(runner) for runner in runners)
        + " — Drydock pins and invokes the top-level executable without a shell, "
        "but cannot prove what that project runner executes internally"
    )


def run_tests(worktree, test_cmd, timeout_s=300, sandbox=None):
    """Run a pre-resolved argv plan through Codex sandbox under one deadline."""
    if not test_cmd:
        return None
    try:
        plan = compile_test_plan(test_cmd)
        prepared_sandbox = _validate_test_sandbox(sandbox)
    except TestPlanError as exc:
        return {
            "ran": False,
            "error": str(exc),
            "exit_code_trusted": False,
            "trust_reason": (
                "the test plan was refused before execution: " + str(exc)
            ),
            "runner_note": None,
            "env_warning": None,
            "sandbox": None,
        }
    sandbox_evidence = _sandbox_metadata(worktree)
    runner_note = _runner_note(plan.requested_steps)
    post_test_worktree = (
        "tests run after review diff extraction; test-created files may remain "
        "unstaged in the retained worktree and were not part of that diff"
    )
    env_warning = None
    try:
        if (os.path.isfile(os.path.join(worktree, "package.json"))
                and not os.path.isdir(os.path.join(worktree, "node_modules"))):
            env_warning = ("worktree has package.json but no node_modules — JS/TS tests cannot "
                           "resolve dependencies here, so the result is not meaningful")
    except OSError:
        pass
    deadline = time.monotonic() + timeout_s
    output = []
    completed = 0
    return_code = 0
    for step in plan.steps:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {
                "ran": True,
                "pass": False,
                "output_tail": ("".join(output) + "test run timed out")[-800:],
                "exit_code_trusted": True,
                "trust_reason": None,
                "runner_note": runner_note,
                "env_warning": env_warning,
                "steps_completed": completed,
                "steps_total": len(plan.steps),
                "plan_source": plan.source,
                "sandbox": sandbox_evidence,
                "timeout_cleanup": {
                    "attempted": False,
                    "mechanism": None,
                    "confirmed": None,
                    "escaped_descendants": "not applicable; no step was started",
                    "detail": "the shared deadline expired before the next step",
                },
                "post_test_worktree": post_test_worktree,
            }
        try:
            argv = _build_test_sandbox_argv(
                prepared_sandbox.prefix,
                worktree,
                step,
            )
            process, timeout_output, timeout_cleanup = _run_test_step(
                argv,
                worktree,
                remaining,
            )
            if timeout_cleanup is not None:
                return {
                    "ran": True,
                    "pass": False,
                    "output_tail": (
                        "".join(output)
                        + (timeout_output or "")
                        + "test run timed out"
                    )[-800:],
                    "exit_code_trusted": True,
                    "trust_reason": None,
                    "runner_note": runner_note,
                    "env_warning": env_warning,
                    "steps_completed": completed,
                    "steps_total": len(plan.steps),
                    "plan_source": plan.source,
                    "sandbox": sandbox_evidence,
                    "timeout_cleanup": timeout_cleanup,
                    "post_test_worktree": post_test_worktree,
                }
        except (OSError, ValueError) as exc:
            return {
                "ran": False,
                "error": str(exc),
                "exit_code_trusted": False,
                "trust_reason": (
                    "the Codex sandbox could not execute the test plan: "
                    + str(exc)
                ),
                "runner_note": runner_note,
                "env_warning": env_warning,
                "steps_completed": completed,
                "steps_total": len(plan.steps),
                "plan_source": plan.source,
                "sandbox": sandbox_evidence,
                "post_test_worktree": post_test_worktree,
            }
        completed += 1
        return_code = process.returncode
        output.append((process.stdout or "") + (process.stderr or ""))
        if return_code != 0:
            break
    return {
        "ran": True,
        "pass": return_code == 0 and completed == len(plan.steps),
        "output_tail": "".join(output)[-800:],
        "exit_code_trusted": True,
        "trust_reason": None,
        "runner_note": runner_note,
        "env_warning": env_warning,
        "steps_completed": completed,
        "steps_total": len(plan.steps),
        "plan_source": plan.source,
        "sandbox": sandbox_evidence,
        "post_test_worktree": post_test_worktree,
    }


# PROVISIONAL, and advisory-only until calibrated against real diffs. They decide
# whether a sentence is printed — never whether the gate clears.
WIDE_DIFF_FILES = 8
LOW_REPETITION = 0.45
MAX_SHAPE_FILES = 200          # pairwise comparison is quadratic; bound and disclose it
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NUM = re.compile(r"\d+")


def _shape_of(line):
    """Structural signature: identifiers and numbers erased, punctuation kept.

    `add_tool(name, timeout=5)` and `add_tool(other, timeout=9)` collapse to the
    same shape. That is the point — a mechanical sweep adds the same STRUCTURE
    with different names, so comparing raw text would score it as divergent.
    """
    return _NUM.sub("0", _IDENT.sub("#", line)).strip()


_HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@")


def _added_shapes(diff):
    """{file: set(shapes)} for added lines, from a unified diff.

    HUNK-AWARE, and it has to be: an added source line whose text is `++ b/x.py`
    renders as `+++ b/x.py`, and a header-by-prefix parser reads it as a file
    boundary. Codex writes the diff, so a naive parser lets the reviewed party
    collapse every file into one phantom key and SUPPRESS its own advisory.
    Inside a hunk, line counts from the `@@` header decide where the body ends —
    content can never be mistaken for structure.
    """
    per, cur = {}, None
    old_left = new_left = 0
    for ln in (diff or "").splitlines():
        if old_left > 0 or new_left > 0:          # inside a hunk body: content only
            c = ln[:1]
            if c == "+":
                new_left -= 1
                if cur:
                    s = _shape_of(ln[1:])
                    if s:
                        per.setdefault(cur, set()).add(s)
            elif c == "-":
                old_left -= 1
            elif c == "\\":                        # "\ No newline at end of file"
                pass
            else:                                  # context line
                old_left -= 1
                new_left -= 1
            old_left, new_left = max(0, old_left), max(0, new_left)
            continue
        m = _HUNK.match(ln)
        if m:
            old_left = int(m.group(1) if m.group(1) is not None else 1)
            new_left = int(m.group(2) if m.group(2) is not None else 1)
        elif ln.startswith("+++ b/"):
            cur = ln[6:].strip()
    return {f: s for f, s in per.items() if s}


def describe_diff_shape(files, diff):
    """Width x cross-file repetition — the reporter's 'awkward middle', measured.

    A wide, REPETITIVE diff is a mechanical sweep and a passing suite means what it
    usually means. A wide, DIVERGENT diff is a dozen separate judgment calls, where
    'tests pass' is the weakest evidence and the human review is doing all the work.
    Nothing here gates; it tells the reviewer when the cheap signal is cheap.
    """
    n = len(files or [])
    per = _added_shapes(diff)
    rep, sampled = None, False
    sets = list(per.values())
    if len(sets) > MAX_SHAPE_FILES:               # bounded, and SAID so — never silent
        sets, sampled = sets[:MAX_SHAPE_FILES], True
    if len(sets) >= 2:
        scores = []
        for i, a in enumerate(sets):
            best = 0.0
            for j, b in enumerate(sets):
                if i == j:
                    continue
                union = len(a | b)
                if union:
                    best = max(best, len(a & b) / union)   # Jaccard on shapes
                if best >= 1.0:
                    break                                  # cannot improve
            scores.append(best)
        rep = round(sum(scores) / len(scores), 3)
    if rep is None:
        # Deletion-only, binary, or unparseable: repetition was NOT measured.
        # Calling that "wide-repetitive" would assert the reassuring case from
        # an absence of evidence — the same fabrication R1 forbids for cost.
        kind = "unknown" if n >= WIDE_DIFF_FILES else "narrow"
    elif n < WIDE_DIFF_FILES:
        kind = "narrow"
    elif rep < LOW_REPETITION:
        kind = "wide-divergent"
    else:
        kind = "wide-repetitive"
    return {"files": n, "repetition": rep, "kind": kind, "sampled": sampled,
            "compared_files": len(sets),
            "thresholds": {"wide_files": WIDE_DIFF_FILES, "low_repetition": LOW_REPETITION}}


def assess_gate(files, test_result, diff_shape=None, scope=None):
    """APPLICABILITY-FIRST gate. Decide 'does the test gate apply?' BEFORE pass/fail.
    N/A is a first-class clean pass, distinct from a FAIL. `clears` means the
    deterministic gate is satisfied — Claude's diff review is still required."""
    if not files:
        return {"applies": False, "verdict": "empty", "clears": False,
                "reason": "no changes produced", "advisories": []}
    code_changed = any(_is_code_file(f) for f in files)
    advisories = []
    if code_changed and not any(_looks_like_test(f) for f in files):
        advisories.append("new/changed code but no test file in the diff — "
                          "check coverage before merging")
    if isinstance(test_result, dict) and test_result.get("runner_note"):
        advisories.append(test_result["runner_note"])
    if isinstance(diff_shape, dict) and diff_shape.get("kind") == "unknown":
        advisories.append(
            f"{diff_shape['files']} files changed but cross-file repetition could not be "
            "measured (no readable added lines — deletions, binary, or an unparseable "
            "diff), so the shape signal is unavailable here rather than reassuring")
    if isinstance(diff_shape, dict) and diff_shape.get("kind") == "wide-divergent":
        advisories.append(
            f"{diff_shape['files']} files changed with little repetition between them "
            f"(shape similarity {diff_shape['repetition']}) — this is not a mechanical "
            "sweep but a set of separate judgment calls, so a passing test suite is weak "
            "evidence here. Read this diff properly, or split the task.")
    if isinstance(scope, dict) and scope.get("out_of_scope"):
        advisories.append(
            "edited outside the declared --files scope: "
            + ", ".join(scope["out_of_scope"][:8])
            + (" …" if len(scope["out_of_scope"]) > 8 else "")
            + " — often correct (a coupled test or translation file), but review these first")
    if not code_changed:
        return {"applies": False, "verdict": "n/a", "clears": True,
                "reason": "docs/config-only change — test gate does not apply",
                "advisories": advisories}
    if test_result is None or not test_result.get("ran"):
        return {"applies": True, "verdict": "blocked", "clears": False,
                "reason": "code changed but tests were not run", "advisories": advisories}
    # A result we cannot TRUST must never read as green (fail-safe direction).
    # Default FALSE: a result that does not assert its own trust is not trusted.
    if not test_result.get("exit_code_trusted", False):
        return {"applies": True, "verdict": "unverifiable", "clears": False,
                "reason": ((test_result.get("trust_reason")
                            or "the test result did not assert a trustworthy exit code")
                           + " — refusing to report green"),
                "advisories": advisories}
    if test_result.get("env_warning"):
        return {"applies": True, "verdict": "unverifiable", "clears": False,
                "reason": test_result["env_warning"], "advisories": advisories}
    if test_result.get("pass"):
        return {"applies": True, "verdict": "green", "clears": True,
                "reason": "code changed; tests pass", "advisories": advisories}
    return {"applies": True, "verdict": "red", "clears": False,
            "reason": "code changed; tests fail", "advisories": advisories}


def _clamp_timeout(t):
    if t is None:
        return DEFAULT_MUTATE_TIMEOUT
    return max(60, min(MAX_MUTATE_TIMEOUT, int(t)))


def mutate(task, base="HEAD", test_cmd=None, weight="heavy", model=None, keep=True,
           files=None, timeout=None):
    try:
        test_plan = compile_test_plan(test_cmd)
    except TestPlanError as exc:
        return {"ok": False, "stage": "test_plan", "error": str(exc)}
    core = cb.discover_core()
    if not core:
        return {"ok": False, "stage": "discover"}
    try:
        test_sandbox = (
            prepare_test_sandbox(core) if test_plan is not None else None
        )
    except TestPlanError as exc:
        return {"ok": False, "stage": "test_sandbox", "error": str(exc)}
    gauge = cb.summarize_gauge(cb.read_rate_limits(core))
    model = model or cb.route(weight, gauge)["model"]
    wt, branch, err = create_worktree(base, task)
    if not wt:
        return {"ok": False, "stage": "worktree", "error": err, "gauge": gauge}
    try:
        prompt, scope_err = build_scoped_task(task, wt, files)
        if scope_err:
            cleanup_worktree(wt, branch)
            return {"ok": False, "stage": "scope_guard", "error": scope_err, "gauge": gauge}
        t0 = time.monotonic()
        d = delegate_mutation(core, wt, prompt, model, timeout_s=_clamp_timeout(timeout))
        elapsed = round(time.monotonic() - t0, 1)
        # Re-read AFTER the run: the delta is what the account was actually charged.
        gauge_after = cb.summarize_gauge(cb.read_rate_limits(core))
        cost = summarize_cost(d.get("usage"), gauge, gauge_after, elapsed)
        changed, diff = extract_changes(wt, base)
        scope = assess_scope(files, changed)
        shape = describe_diff_shape(changed, diff)
        tests = run_tests(wt, test_plan, sandbox=test_sandbox)
        gate = assess_gate(changed, tests, shape, scope)
        # A timed-out run that already wrote files is salvageable, not garbage. It
        # is INCOMPLETE, so it never clears the gate regardless of what tests say.
        partial = bool(d.get("partial")) and bool(changed)
        clears = gate["clears"] and not partial
        result = {"ok": True, "gauge": gauge, "gauge_after": gauge_after, "cost": cost,
                  "model": model, "worktree": wt, "branch": branch, "base": base,
                  "delegation": d, "files": changed, "diff": diff,
                  "scope": scope, "diff_shape": shape, "partial": partial,
                  "tests": tests, "gate": gate, "clears_gate": clears,
                  "merged": False,
                  "note": (("INCOMPLETE — the delegation timed out; the diff below is "
                            "partial work salvaged from the worktree. Do not merge as-is; "
                            "re-run with --timeout to finish, or complete it by hand. ")
                           if partial else
                           ("NOT merged. Review the diff, then merge deliberately. "
                            "Clearing the gate is necessary, not sufficient — Claude "
                            "must review scope/security/architecture before merge."))}
        # Keep the worktree when there is reviewable work — success OR a salvageable
        # partial. Only clean up on no-changes or a hard failure with nothing to keep.
        if not keep or not changed or (not d.get("ok") and not partial):
            cleanup_worktree(wt, branch)
            result["worktree"] = None
            result["cleaned_up"] = True
        return result
    except Exception as e:  # noqa: BLE001
        cleanup_worktree(wt, branch)
        return {"ok": False, "stage": "mutate_error", "error": str(e), "gauge": gauge}


def main():
    ap = argparse.ArgumentParser(
        description="Delegate a MUTATING task to Codex in an isolated worktree (no auto-merge).")
    ap.add_argument("task", nargs="?", help="the implementation task for Codex")
    ap.add_argument("--base", default="HEAD", help="branch/commit to branch from")
    test_group = ap.add_mutually_exclusive_group()
    test_group.add_argument(
        "--test-cmd",
        default=None,
        help=(
            "compatibility form for one simple command or an && chain; shell "
            "operators/redirects and direct known shell launchers are refused "
            "before delegation"
        ),
    )
    test_group.add_argument(
        "--test-argv-json",
        default=None,
        help=(
            "preferred unambiguous test plan: a JSON argv array or array of argv "
            "arrays, e.g. '[\"python\",\"-m\",\"pytest\",\"-q\"]'"
        ),
    )
    ap.add_argument("--weight", choices=["heavy", "light"], default="heavy")
    ap.add_argument("--model", default=None)
    ap.add_argument("--files", nargs="+", metavar="PATH", default=None,
                    help="repo-relative edit targets to inline (opt-in, SOFT scope): Codex "
                         "starts here instead of crawling, may still edit elsewhere, and "
                         "any out-of-scope edit is reported. Best for a small coupled "
                         "change; omit it for a wide mechanical sweep.")
    ap.add_argument("--timeout", type=int, default=None,
                    help=f"delegation timeout in seconds (default {DEFAULT_MUTATE_TIMEOUT}, "
                         f"max {MAX_MUTATE_TIMEOUT}). Raise it for a mechanical sweep over a "
                         "large file; a timed-out run keeps its partial work.")
    ap.add_argument("--cleanup", nargs=2, metavar=("WORKTREE", "BRANCH"),
                    help="remove a worktree+branch from a prior run, then exit")
    ap.add_argument("--gc", action="store_true",
                    help="sweep orphaned codex/ worktrees (empty ones removed, ones holding "
                         "work kept and reported), then exit")
    ap.add_argument("--dry-run", action="store_true", help="with --gc: report, remove nothing")
    args = ap.parse_args()
    if args.gc:
        print(json.dumps(gc_worktrees(dry_run=args.dry_run), indent=2))
        return 0
    if args.cleanup:
        cleanup_worktree(args.cleanup[0], args.cleanup[1])
        print(json.dumps({"ok": True, "cleaned_up": args.cleanup}))
        return 0
    if not args.task:
        ap.error("task is required unless --cleanup or --gc is used")
    try:
        test_specification = (
            decode_test_argv_json(args.test_argv_json)
            if args.test_argv_json is not None
            else args.test_cmd
        )
    except TestPlanError as exc:
        print(json.dumps(
            {"ok": False, "stage": "test_plan", "error": str(exc)},
            indent=2,
        ))
        return 1
    out = mutate(args.task, args.base, test_specification, args.weight, args.model,
                 files=args.files, timeout=args.timeout)
    print(json.dumps(out, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
