#!/usr/bin/env python3
"""Codex-native Drydock lifecycle bootstrap and readiness CLI."""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Iterator

from scaffold_bundle import BundleEntry, BundleError, load_bundle


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
BUNDLE_PATH = PLUGIN_ROOT / "assets" / "project-scaffold.bundle.json"
REPOSITORY_MARKERS = (
    "AGENTS.md",
    "PROJECT_CONTEXT.template.md",
    "scripts/sdd.py",
    "sdd-plus/protocols/framework-usage.md",
)
LOCK_NAME = ".drydock-init.lock"


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _context_status(root: Path) -> str:
    path = root / "PROJECT_CONTEXT.md"
    if not path.is_file():
        return "missing"
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return "unreadable"
    lowered = text.lower()
    if (
        "copy this file to `project_context.md`" in lowered
        or lowered.count("tbd") >= 3
        or len(text.strip()) < 40
    ):
        return "template"
    return "real"


def _manifest_evidence() -> dict[str, object]:
    try:
        document = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {"status": "invalid", "error": str(exc)}
    required = {"name": "drydock", "skills": "./skills/"}
    mismatches = {
        key: {"expected": value, "actual": document.get(key)}
        for key, value in required.items()
        if document.get(key) != value
    }
    version = document.get("version")
    if not isinstance(version, str) or not version:
        mismatches["version"] = {"expected": "non-empty string", "actual": version}
    if mismatches:
        return {"status": "invalid", "mismatches": mismatches}
    return {
        "status": "valid",
        "name": document["name"],
        "version": version,
        "manifest": str(MANIFEST_PATH),
    }


def _codex_evidence() -> dict[str, object]:
    candidates: list[str] = []
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.extend(
            glob.glob(
                os.path.join(
                    local_app_data, "OpenAI", "Codex", "bin", "*", "codex.exe"
                )
            )
        )
    executable = max(candidates, key=os.path.getmtime) if candidates else None
    executable = executable or shutil.which("codex")
    if not executable:
        return {"status": "not_found"}
    try:
        result = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "unavailable", "executable": executable, "error": str(exc)}
    output = (result.stdout or result.stderr).strip()
    if result.returncode != 0:
        return {
            "status": "unavailable",
            "executable": executable,
            "exit_code": result.returncode,
            "output": output,
        }
    return {"status": "reported", "executable": executable, "version": output}


def _enforcement_evidence(
    session_id: str | None, plugin_data: Path | None
) -> dict[str, object]:
    hook_definition = PLUGIN_ROOT / "hooks" / "hooks.json"
    manifest_path = PLUGIN_ROOT / "hooks" / "runtime.manifest.json"
    runtime_path = PLUGIN_ROOT / "hooks" / "runtime.py"
    definition_valid = False
    revision: str | None = None
    definition_error: str | None = None
    if hook_definition.is_file() and manifest_path.is_file() and runtime_path.is_file():
        try:
            hook_document = json.loads(hook_definition.read_text(encoding="utf-8"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            files = manifest["files"]
            if (
                not isinstance(files, list)
                or len(files) != 1
                or files[0].get("path") != "runtime.py"
            ):
                raise ValueError("runtime manifest has an unexpected shape")
            revision = files[0].get("sha256")
            if not isinstance(revision, str) or _sha256(runtime_path.read_bytes()) != revision:
                raise ValueError("runtime digest does not match its manifest")
            description = hook_document.get("description", "")
            if f"runtime-sha256={revision}" not in description:
                raise ValueError("hook definition does not bind the runtime digest")
            python_files = sorted(path.name for path in runtime_path.parent.glob("*.py"))
            if python_files != ["runtime.py"]:
                raise ValueError("unexpected executable hook file")
            definition_valid = True
        except (OSError, UnicodeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            definition_error = str(exc)

    resolved_plugin_data = plugin_data
    if resolved_plugin_data is None:
        value = os.environ.get("PLUGIN_DATA") or os.environ.get("CLAUDE_PLUGIN_DATA")
        resolved_plugin_data = Path(value) if value and os.path.isabs(value) else None
    liveness = "unavailable"
    liveness_evidence: dict[str, object] | None = None
    if (
        session_id
        and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", session_id)
        and resolved_plugin_data is not None
    ):
        state_path = resolved_plugin_data / "liveness" / f"{session_id}.json"
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if (
                state.get("session_id") == session_id
                and revision
                and state.get("runtime_sha256") == revision
            ):
                liveness = "current_revision_observed"
                liveness_evidence = {
                    "session_id": session_id,
                    "runtime_sha256": revision,
                    "model": state.get("model"),
                    "permission_mode": state.get("permission_mode"),
                }
            else:
                liveness = "stale_or_mismatched"
        except (OSError, ValueError, AttributeError):
            liveness = "not_observed"

    return {
        "definition": (
            "valid" if definition_valid else "invalid" if hook_definition.exists() else "absent"
        ),
        "definition_error": definition_error,
        "source": str(hook_definition) if hook_definition.exists() else None,
        "enabled": "unknown",
        "trusted": "unknown",
        "managed": "unknown",
        "active_task_liveness": liveness,
        "liveness_evidence": liveness_evidence,
        "handler_revision": revision,
        "active": False,
        "defined_tool_contracts": ["Bash", "apply_patch"] if definition_valid else [],
        "covered_tool_paths": [],
        "uncovered_tool_paths": [
            "MCP tools without an explicit schema contract",
            "other local function tools",
            "hosted tools",
            "specialized opted-out paths",
        ],
        "profile": "non-managed",
        "trust_action_required": (
            "Review and trust the current Drydock definitions in Codex /hooks."
            if hook_definition.exists()
            else None
        ),
        "trusted_computing_base": [
            "Codex host",
            "operating system",
            "selected Python interpreter",
            "hook definition and Codex trust store",
        ],
    }


def readiness(
    root: Path,
    session_id: str | None = None,
    plugin_data: Path | None = None,
    check_peer: bool = False,
) -> dict[str, object]:
    root = root.resolve(strict=False)
    plugin = _manifest_evidence()
    python_supported = sys.version_info >= (3, 9)
    try:
        entries = load_bundle(BUNDLE_PATH)
        bundle: dict[str, object] = {
            "status": "valid",
            "path": str(BUNDLE_PATH),
            "files": len(entries),
            "sha256": _sha256(BUNDLE_PATH.read_bytes()),
        }
    except (OSError, BundleError) as exc:
        bundle = {"status": "invalid", "path": str(BUNDLE_PATH), "error": str(exc)}

    missing = [marker for marker in REPOSITORY_MARKERS if not (root / marker).is_file()]
    initialized = not missing
    context = _context_status(root)
    enforcement = _enforcement_evidence(session_id, plugin_data)

    blockers: list[str] = []
    if plugin.get("status") != "valid":
        blockers.append("plugin manifest is invalid")
    if not python_supported:
        blockers.append("Python 3.9 or newer is required")
    if bundle.get("status") != "valid":
        blockers.append("project scaffold bundle is invalid")
    if not initialized:
        blockers.append("repository is not initialized")
    if context != "real":
        blockers.append("PROJECT_CONTEXT.md does not contain confirmed project context")

    lifecycle_ready = not blockers
    peer: dict[str, object] = {"status": "not_checked"}
    if check_peer:
        try:
            from orchestrator import ClaudePeer

            peer = ClaudePeer().status()
        except (ImportError, OSError, ValueError, RuntimeError) as exc:
            peer = {"status": "unavailable", "error": str(exc)}

    return {
        "schema_version": 1,
        "host": "codex",
        "plugin": plugin,
        "codex": _codex_evidence(),
        "python": {
            "status": "supported" if python_supported else "unsupported",
            "version": ".".join(str(part) for part in sys.version_info[:3]),
            "executable": sys.executable,
        },
        "bundle": bundle,
        "repository": {
            "root": str(root),
            "initialized": initialized,
            "missing_markers": missing,
            "project_context": context,
        },
        "enforcement": enforcement,
        "peer": peer,
        "ready_for_lifecycle": lifecycle_ready,
        "ready_for_enforcement": False,
        "blockers": blockers,
    }


def _destination(root: Path, relative: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise BundleError(f"unsafe destination path: {relative!r}")
    return root.joinpath(*pure.parts)


def _assert_safe_parent(root: Path, destination: Path) -> None:
    try:
        destination.relative_to(root)
    except ValueError as exc:
        raise BundleError(f"destination escapes root: {destination}") from exc
    current = root
    for part in destination.relative_to(root).parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise BundleError(f"destination parent is a symlink: {current}")
        if current.exists() and not current.is_dir():
            raise BundleError(f"destination parent is not a directory: {current}")


@contextmanager
def _init_lock(root: Path) -> Iterator[None]:
    path = root / LOCK_NAME
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
        os.close(descriptor)
        descriptor = -1
        yield
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _write_new(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _missing_gitignore_lines(existing: bytes, desired: bytes) -> list[str]:
    try:
        existing_text = existing.decode("utf-8")
        desired_text = desired.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BundleError(".gitignore must be UTF-8 to merge safely") from exc
    present = set(existing_text.splitlines())
    return [
        line
        for line in desired_text.splitlines()
        if line.strip() and line not in present
    ]


def _append_gitignore(path: Path, lines: list[str]) -> None:
    if not lines:
        return
    with path.open("ab") as stream:
        if path.stat().st_size:
            stream.write(b"\n")
        stream.write(("\n".join(lines) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())


def initialize(root: Path, apply: bool) -> dict[str, object]:
    entries = load_bundle(BUNDLE_PATH)
    root = root.resolve(strict=False)
    if root.exists() and (root.is_symlink() or not root.is_dir()):
        raise BundleError(f"repository root is not a safe directory: {root}")

    report: dict[str, object] = {
        "schema_version": 1,
        "mode": "apply" if apply else "preview",
        "root": str(root),
        "bundle_sha256": _sha256(BUNDLE_PATH.read_bytes()),
        "planned": {"create": [], "gitignore_add": []},
        "created": [],
        "unchanged": [],
        "conflicts": [],
        "gitignore_added": [],
        "errors": [],
        "git_hook_installed": False,
    }

    actions: list[tuple[BundleEntry, Path, str, list[str], str | None]] = []
    for entry in entries:
        destination = _destination(root, entry.path)
        _assert_safe_parent(root, destination)
        if destination.is_symlink():
            report["errors"].append(
                {"path": entry.path, "reason": "destination is a symlink"}
            )
            continue
        if not destination.exists():
            actions.append((entry, destination, "create", [], None))
        elif not destination.is_file():
            report["errors"].append(
                {"path": entry.path, "reason": "destination is not a file"}
            )
        elif entry.path == ".gitignore":
            try:
                missing_lines = _missing_gitignore_lines(
                    destination.read_bytes(), entry.content
                )
            except (OSError, BundleError) as exc:
                report["errors"].append({"path": entry.path, "reason": str(exc)})
            else:
                if missing_lines:
                    actions.append(
                        (
                            entry,
                            destination,
                            "merge_gitignore",
                            missing_lines,
                            _sha256(destination.read_bytes()),
                        )
                    )
                else:
                    report["unchanged"].append(entry.path)
        elif _sha256(destination.read_bytes()) == entry.sha256:
            report["unchanged"].append(entry.path)
        else:
            report["conflicts"].append(entry.path)

    for entry, _destination_path, action, lines, _expected_digest in actions:
        if action == "create":
            report["planned"]["create"].append(entry.path)
        else:
            report["planned"]["gitignore_add"].extend(lines)

    if not apply or report["errors"]:
        report["applied"] = False
        return report

    root.mkdir(parents=True, exist_ok=True)
    try:
        with _init_lock(root):
            for entry, destination, action, lines, expected_digest in actions:
                _assert_safe_parent(root, destination)
                if action == "create":
                    _write_new(destination, entry.content)
                    report["created"].append(entry.path)
                else:
                    if (
                        destination.is_symlink()
                        or not destination.is_file()
                        or _sha256(destination.read_bytes()) != expected_digest
                    ):
                        raise BundleError(
                            ".gitignore changed after preview; refusing to merge"
                        )
                    _append_gitignore(destination, lines)
                    report["gitignore_added"].extend(lines)
    except FileExistsError:
        report["errors"].append(
            {"path": LOCK_NAME, "reason": "another initialization is active"}
        )
        report["applied"] = False
        return report
    except (OSError, BundleError) as exc:
        report["errors"].append({"path": None, "reason": str(exc)})
        report["applied"] = False
        return report

    report["applied"] = True
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    readiness_parser = subparsers.add_parser("readiness")
    readiness_parser.add_argument("--root", type=Path, default=Path.cwd())
    readiness_parser.add_argument("--session-id")
    readiness_parser.add_argument("--plugin-data", type=Path)
    readiness_parser.add_argument(
        "--check-peer",
        action="store_true",
        help="run the no-quota Claude authentication status check",
    )

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--root", type=Path, default=Path.cwd())
    init_parser.add_argument(
        "--apply",
        action="store_true",
        help="perform the create-only writes; otherwise emit a preview",
    )
    args = parser.parse_args(argv)

    try:
        if args.command == "readiness":
            result = readiness(
                args.root,
                args.session_id,
                args.plugin_data,
                args.check_peer,
            )
        else:
            result = initialize(args.root, args.apply)
    except (OSError, BundleError) as exc:
        result = {"schema_version": 1, "error": str(exc)}
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    if args.command == "init":
        return 0 if not result.get("errors") else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
