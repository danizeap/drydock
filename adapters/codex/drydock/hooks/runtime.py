# DRYDOCK CODEX HOOK RUNTIME v1
# Generated deterministically from scripts/hook_runtime_source.py.
# Do not edit: run scripts/build_hooks.py.

"""Authoritative source for Drydock's generated Codex hook runtime.

This file is a build input. Codex hooks execute only the generated, digest-
bound ``hooks/runtime.py`` bytes after the inline verifier captures and checks
them. Keep this module self-contained: the generated runtime may import only
the Python standard library.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import sys
from pathlib import Path


MAX_INPUT_BYTES = 1024 * 1024
MAX_TARGETS = 32
SECRET_ALLOW = {".env.example", ".env.template", ".env.sample"}
SECRET_PATTERN = re.compile(
    r"""^(
        \.env(\..+)?
        |.+\.env
        |\.envrc
        |.+\.(pem|key|ppk|p12|pfx|jks)
        |id_(rsa|dsa|ecdsa|ed25519)(\..+)?
        |credentials(\..+)?
        |secrets?\.(json|ya?ml|toml)
        |service[-_]account.*\.json
    )$""",
    re.IGNORECASE | re.VERBOSE,
)
PATCH_LINE = re.compile(
    r"^\*\*\*\s+(?:Add|Update|Delete) File:\s*(.+?)\s*$", re.MULTILINE
)
PATCH_MOVE = re.compile(r"^\*\*\*\s+Move to:\s*(.+?)\s*$", re.MULTILINE)
REDIRECT = re.compile(r"(?:^|[\s;&|])(?:\d*>>?|2>&1\s*>)\s*([^\s;&|]+)")
POWERSHELL_WRITE = re.compile(
    r"\b(?:Set-Content|Add-Content|Out-File|Copy-Item|Move-Item|"
    r"New-Item|Remove-Item)\b(?P<args>[^;\r\n]*)",
    re.IGNORECASE,
)
PATH_ARGUMENT = re.compile(
    r"(?:-LiteralPath|-Path|-Destination)\s+"
    r"(?:'([^']+)'|\"([^\"]+)\"|([^\s;|]+))",
    re.IGNORECASE,
)
SOFT_SEGMENTS = {
    "test",
    "tests",
    "__tests__",
    "spec",
    "specs",
    "fixtures",
    "e2e",
    "stories",
    "__mocks__",
    "__snapshots__",
    "examples",
    "example",
    "samples",
    "docs",
    "doc",
}
EXEMPT_BASENAMES = {
    "license",
    "license.txt",
    "notice",
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
    "codeowners",
}
EXEMPT_SUFFIXES = (".md", ".markdown", ".rst", ".txt")
GIT_GLOBAL_WITH_ARGUMENT = {
    "-C",
    "-c",
    "--git-dir",
    "--work-tree",
    "--namespace",
    "--super-prefix",
    "--exec-path",
    "--config-env",
}
GIT_GLOBAL_NO_ARGUMENT = {
    "-p",
    "--paginate",
    "-P",
    "--no-pager",
    "--bare",
    "--no-replace-objects",
    "--literal-pathspecs",
    "--no-literal-pathspecs",
    "--glob-pathspecs",
    "--noglob-pathspecs",
    "--icase-pathspecs",
    "--no-optional-locks",
}
SHELL_SEPARATORS = {"&&", "||", ";", "|", "&", "|&"}


def _emit(document: dict[str, object]) -> None:
    print(json.dumps(document, separators=(",", ":"), sort_keys=True))
    sys.stdout.flush()


def deny(reason: str) -> None:
    _emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )


def path_is_secret(value: str) -> bool:
    if not isinstance(value, str) or not value:
        return False
    basename = value.replace("\\", "/").rstrip("/").split("/")[-1]
    if basename.casefold() in SECRET_ALLOW:
        return False
    return bool(SECRET_PATTERN.match(basename))


def apply_patch_targets(tool_input: dict[str, object]) -> list[str]:
    targets: set[str] = set()
    for key in ("command", "input", "patch", "content", "diff", "unified_diff"):
        value = tool_input.get(key)
        if isinstance(value, str):
            targets.update(match.group(1).strip() for match in PATCH_LINE.finditer(value))
            targets.update(match.group(1).strip() for match in PATCH_MOVE.finditer(value))
    for key in ("file_path", "path", "move_path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            targets.add(value)
    for key in ("fileChanges", "changes", "files"):
        value = tool_input.get(key)
        if isinstance(value, dict):
            targets.update(item for item in value if isinstance(item, str) and item)
    return sorted(targets)[:MAX_TARGETS]


def shell_write_targets(command: str) -> list[str]:
    targets: set[str] = set()
    for match in REDIRECT.finditer(command):
        target = match.group(1).strip("'\"")
        if target:
            targets.add(target)
    for command_match in POWERSHELL_WRITE.finditer(command):
        arguments = command_match.group("args")
        for match in PATH_ARGUMENT.finditer(arguments):
            target = next((group for group in match.groups() if group), "")
            if target:
                targets.add(target)
        if not any(PATH_ARGUMENT.finditer(arguments)):
            positional = re.findall(r"(?:'([^']+)'|\"([^\"]+)\"|([^\s;|]+))", arguments)
            flattened = [next((group for group in groups if group), "") for groups in positional]
            flattened = [item for item in flattened if item and not item.startswith("-")]
            if flattened:
                targets.add(flattened[0])
    return sorted(targets)[:MAX_TARGETS]


def _segments(tokens: list[str]) -> list[list[str]]:
    result: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token in SHELL_SEPARATORS:
            if current:
                result.append(current)
            current = []
        else:
            current.append(token)
    if current:
        result.append(current)
    return result


def _git_subcommand(tokens: list[str], git_index: int) -> int | None:
    index = git_index + 1
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("--") and "=" in token:
            index += 1
        elif token in GIT_GLOBAL_WITH_ARGUMENT:
            index += 2
        elif token in GIT_GLOBAL_NO_ARGUMENT or token.startswith("-"):
            index += 1
        else:
            return index
    return None


def _short_force(token: str) -> bool:
    return token.startswith("-") and not token.startswith("--") and "f" in token[1:]


def _destructive_git_action(subcommand: str, arguments: list[str]) -> str | None:
    if subcommand == "reset" and "--hard" in arguments:
        return "hard reset"
    if subcommand == "clean" and any(
        argument == "--force" or _short_force(argument) for argument in arguments
    ):
        return "git clean -f"
    if subcommand == "checkout" and any(
        argument in {".", "*", "-f", "--force"} for argument in arguments
    ):
        return "checkout discard"
    if subcommand == "switch" and any(
        argument in {"-f", "--force", "--discard-changes"} for argument in arguments
    ):
        return "switch discard"
    if subcommand == "restore":
        staged_only = "--staged" in arguments and "--worktree" not in arguments
        if not staged_only and any(argument in {".", "*"} for argument in arguments):
            return "working-tree restore"
    if subcommand == "stash" and arguments[:1] in (["drop"], ["clear"]):
        return "stash deletion"
    if subcommand == "push":
        destructive = any(
            argument in {"--force", "-f", "--mirror", "--delete", "-d"}
            or (argument.startswith("+") and not argument.startswith("--"))
            or (
                ":" in argument
                and argument.split(":", 1)[0] == ""
                and not argument.startswith("-")
            )
            for argument in arguments
        )
        if destructive:
            return "force or delete push"
    if subcommand == "branch" and (
        "-D" in arguments
        or ("--delete" in arguments and "--force" in arguments)
    ):
        return "force-delete branch"
    if subcommand == "update-ref" and any(
        argument in {"-d", "--delete"} for argument in arguments
    ):
        return "ref deletion"
    if (
        subcommand == "worktree"
        and arguments[:1] == ["remove"]
        and any(argument in {"-f", "--force"} for argument in arguments)
    ):
        return "forced worktree removal"
    return None


def destructive_git(command: str) -> str | None:
    try:
        tokens = shlex.split(command, comments=False, posix=True)
    except ValueError:
        lowered = command.casefold()
        if "git" in lowered and (
            "reset --hard" in lowered
            or "clean -f" in lowered
            or "push --force" in lowered
        ):
            return "unparseable destructive git command"
        return None
    for segment in _segments(tokens):
        for index, token in enumerate(segment):
            normalized = token[:-4] if token.casefold().endswith(".exe") else token
            if normalized == "git" or normalized.endswith(("/git", "\\git")):
                subcommand_index = _git_subcommand(segment, index)
                if subcommand_index is None:
                    continue
                reason = _destructive_git_action(
                    segment[subcommand_index], segment[subcommand_index + 1 :]
                )
                if reason:
                    return reason
    return None


def _find_project(cwd: str) -> Path | None:
    if not isinstance(cwd, str) or not cwd or not os.path.isabs(cwd):
        return None
    current = Path(cwd)
    try:
        current = current.resolve()
    except OSError:
        return None
    for _ in range(16):
        if (current / "sdd-plus").is_dir() and (current / "AGENTS.md").is_file():
            return current
        if (current / ".git").exists() or current.parent == current:
            break
        current = current.parent
    return None


def _inside(target: Path, root: Path) -> bool:
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


def _active_packet(root: Path) -> bool:
    changes = root / "sdd-plus" / "changes"
    try:
        return any(
            child.is_dir() and (child / "tasks.md").is_file()
            for child in changes.iterdir()
        )
    except OSError:
        return False


def _high_risk(target: Path, root: Path) -> str | None:
    try:
        parts = [part.casefold() for part in target.relative_to(root).parts]
    except ValueError:
        return None
    basename = target.name.casefold()
    if basename == "owner_status.md" and not SOFT_SEGMENTS.intersection(parts):
        return "generated Owner status"
    if (
        basename in EXEMPT_BASENAMES
        or basename.endswith(EXEMPT_SUFFIXES)
        or "sdd-plus" in parts
        or SOFT_SEGMENTS.intersection(parts)
    ):
        return None
    if "migrations" in parts or any(
        parts[index : index + 2] == ["db", "migrate"]
        for index in range(max(0, len(parts) - 1))
    ):
        return "schema migration"
    is_ci = (
        ".github" in parts
        and "workflows" in parts
        or basename in {".gitlab-ci.yml", ".gitlab-ci.yaml", "jenkinsfile"}
    )
    if is_ci and not target.exists():
        return "new CI workflow/config"
    if (
        basename == "dockerfile"
        or basename.startswith("dockerfile.")
        or basename.startswith("docker-compose.")
        or basename in {"compose.yml", "compose.yaml"}
    ):
        return "container build/deploy config"
    return None


def packet_guard(payload: dict[str, object], targets: list[str]) -> str | None:
    root = _find_project(payload.get("cwd", ""))
    if root is None or _active_packet(root):
        return None
    cwd = Path(payload["cwd"])
    for raw_target in targets:
        target = Path(raw_target)
        if not target.is_absolute():
            target = cwd / target
        try:
            target = target.resolve(strict=False)
        except OSError:
            continue
        if not _inside(target, root):
            continue
        risk = _high_risk(target, root)
        if risk:
            return risk
    return None


def _state_path(session_id: object) -> Path | None:
    if not isinstance(session_id, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{1,128}", session_id
    ):
        return None
    data_root = os.environ.get("PLUGIN_DATA") or os.environ.get("CLAUDE_PLUGIN_DATA")
    if not data_root or not os.path.isabs(data_root):
        return None
    return Path(data_root) / "liveness" / f"{session_id}.json"


def _packet_fingerprints(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    changes = root / "sdd-plus" / "changes"
    try:
        children = sorted(child for child in changes.iterdir() if child.is_dir())[:50]
    except OSError:
        return result
    for child in children:
        digest = hashlib.sha256()
        for name in ("tasks.md", "verification.md"):
            path = child / name
            try:
                content = path.read_bytes()[: 256 * 1024]
            except OSError:
                content = b""
            digest.update(name.encode("ascii"))
            digest.update(b"\0")
            digest.update(content)
        result[child.name] = digest.hexdigest()
    return result


def _write_liveness(payload: dict[str, object]) -> bool:
    path = _state_path(payload.get("session_id"))
    if path is None:
        return False
    root = _find_project(payload.get("cwd", ""))
    document = {
        "schema_version": 1,
        "session_id": payload["session_id"],
        "runtime_sha256": DRYDOCK_RUNTIME_SHA256,
        "permission_mode": payload.get("permission_mode"),
        "model": payload.get("model"),
        "project_root": str(root) if root else None,
        "packet_fingerprints": _packet_fingerprints(root) if root else {},
    }
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(
            json.dumps(document, separators=(",", ":"), sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
        return True
    except OSError:
        try:
            temporary.unlink()
        except OSError:
            pass
        return False


def _session_start(payload: dict[str, object]) -> None:
    live = _write_liveness(payload)
    root = _find_project(payload.get("cwd", ""))
    if root is None:
        return
    packets = _packet_fingerprints(root)
    context_status = "missing"
    context_path = root / "PROJECT_CONTEXT.md"
    if context_path.is_file():
        try:
            text = context_path.read_text(encoding="utf-8-sig")[: 64 * 1024]
            context_status = (
                "template"
                if text.lower().count("tbd") >= 3
                or "Copy this file to `PROJECT_CONTEXT.md`" in text
                else "present"
            )
        except OSError:
            context_status = "unreadable"
    message = (
        "[Drydock] Codex-native project orientation: "
        f"PROJECT_CONTEXT={context_status}; active_packets={len(packets)}; "
        f"hook_liveness={'recorded' if live else 'unavailable'}; "
        "ordinary plugin guardrails are non-managed and conditional."
    )
    _emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": message,
            }
        }
    )


def _claimed_done(tasks_path: Path) -> bool:
    try:
        text = tasks_path.read_text(encoding="utf-8-sig")[: 256 * 1024]
    except OSError:
        return False
    return bool(re.search(r"(?m)^\s*-\s*\[[xX]\]\s+", text)) and not bool(
        re.search(r"(?m)^\s*-\s*\[\s\]\s+", text)
    )


def _verification_pending(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8-sig")[: 256 * 1024]
    except OSError:
        return True
    return bool(re.search(r"(?im)^\s*Pending\.\s*$", text))


def _stop(payload: dict[str, object]) -> None:
    path = _state_path(payload.get("session_id"))
    root = _find_project(payload.get("cwd", ""))
    if path is None or root is None or not path.is_file():
        return
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if state.get("runtime_sha256") != DRYDOCK_RUNTIME_SHA256:
        return
    baseline = state.get("packet_fingerprints")
    if not isinstance(baseline, dict):
        return
    current = _packet_fingerprints(root)
    for name, fingerprint in current.items():
        packet = root / "sdd-plus" / "changes" / name
        if (
            baseline.get(name) != fingerprint
            and _claimed_done(packet / "tasks.md")
            and _verification_pending(packet / "verification.md")
        ):
            _emit(
                {
                    "continue": False,
                    "stopReason": (
                        "Drydock completion check: this task changed a packet "
                        f"that now looks complete, but {name}/verification.md "
                        "is still Pending. Verify it before calling the work done."
                    ),
                }
            )
            return


def _pre_tool(payload: dict[str, object]) -> None:
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        deny("Drydock guard denied a malformed supported tool payload.")
        return
    if tool_name == "Bash":
        command = tool_input.get("command")
        if not isinstance(command, str) or not command.strip():
            deny("Drydock guard denied a malformed Bash contract.")
            return
        targets = shell_write_targets(command)
        destructive = destructive_git(command)
        if destructive:
            deny(
                "Drydock git-safety guardrail blocked a "
                f"{destructive}. Destructive Git requires explicit Owner approval."
            )
            return
    elif tool_name == "apply_patch":
        targets = apply_patch_targets(tool_input)
        if not targets:
            deny("Drydock guard denied an unsupported apply_patch contract.")
            return
    else:
        deny(
            "Drydock guard received an unsupported tool contract inside a "
            f"guarded matcher: {tool_name!r}."
        )
        return
    for target in targets:
        if path_is_secret(target):
            deny(
                "Drydock secrets guardrail blocked a write to a "
                "secret-bearing path. Ask the Owner to handle it manually."
            )
            return
    risk = packet_guard(payload, targets)
    if risk:
        deny(
            "Drydock packet guard blocked an ungoverned write to a "
            f"high-impact path ({risk}). Create a change packet and retry."
        )


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            deny("Drydock guard denied an oversized supported tool payload.")
            return 0
        payload = json.loads(raw.decode("utf-8")) if raw.strip() else {}
        if not isinstance(payload, dict):
            deny("Drydock guard denied a malformed supported tool payload.")
            return 0
        event = payload.get("hook_event_name")
        if event == "SessionStart":
            _session_start(payload)
        elif event == "Stop":
            _stop(payload)
        elif event == "PreToolUse":
            _pre_tool(payload)
        else:
            deny(f"Drydock guard received an unsupported hook event: {event!r}.")
    except BaseException:
        deny(
            "Drydock guard denied this supported call because policy "
            "evaluation failed internally."
        )
    return 0


if __name__ == "__main__":
    main()
