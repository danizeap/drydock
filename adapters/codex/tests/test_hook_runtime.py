from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

import build_hooks
import drydock_codex


PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "drydock"
SOURCE = PLUGIN_ROOT / "scripts" / "hook_runtime_source.py"
HOOKS = PLUGIN_ROOT / "hooks"


def _handler(plugin_root: Path, event: str, index: int = 0) -> dict[str, object]:
    document = json.loads(
        (plugin_root / "hooks" / "hooks.json").read_text(encoding="utf-8")
    )
    return document["hooks"][event][index]["hooks"][0]


def _run(
    plugin_root: Path,
    payload: dict[str, object],
    *,
    event: str = "PreToolUse",
    index: int = 0,
    plugin_data: Path | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    handler = _handler(plugin_root, event, index)
    command_key = "commandWindows" if os.name == "nt" else "command"
    environment = dict(os.environ)
    environment["PLUGIN_ROOT"] = str(plugin_root.resolve())
    if plugin_data is not None:
        environment["PLUGIN_DATA"] = str(plugin_data.resolve())
    return subprocess.run(
        handler[command_key],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        shell=True,
        cwd=cwd or plugin_root,
        env=environment,
        timeout=20,
        check=False,
    )


def _pretool(
    tool_name: str,
    tool_input: dict[str, object],
    cwd: Path,
    session_id: str = "hook-test",
) -> dict[str, object]:
    return {
        "hook_event_name": "PreToolUse",
        "session_id": session_id,
        "cwd": str(cwd.resolve()),
        "tool_name": tool_name,
        "tool_input": tool_input,
        "model": "gpt-test",
        "permission_mode": "default",
    }


def _deny_reason(result: subprocess.CompletedProcess[str]) -> str | None:
    if not result.stdout.strip():
        return None
    document = json.loads(result.stdout)
    return document["hookSpecificOutput"].get("permissionDecisionReason")


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "sdd-plus" / "changes").mkdir(parents=True)
    (root / "AGENTS.md").write_text("# governed\n", encoding="utf-8")
    return root


def test_generated_hooks_are_exact_and_narrow() -> None:
    assert build_hooks.verify_outputs(SOURCE, HOOKS) == []
    runtime = (HOOKS / "runtime.py").read_bytes()
    assert runtime.startswith(b"# DRYDOCK CODEX HOOK RUNTIME v1\n")
    assert not runtime.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in runtime

    manifest = json.loads(
        (HOOKS / "runtime.manifest.json").read_text(encoding="utf-8")
    )
    digest = hashlib.sha256(runtime).hexdigest()
    assert manifest["files"] == [{"path": "runtime.py", "sha256": digest}]

    hooks = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))
    assert [group["matcher"] for group in hooks["hooks"]["PreToolUse"]] == [
        "^Bash$",
        "^apply_patch$",
    ]
    assert "mcp__" not in json.dumps(hooks["hooks"]["PreToolUse"])
    handler = hooks["hooks"]["PreToolUse"][0]["hooks"][0]
    assert digest in hooks["description"]
    assert "-I -S -c" in handler["command"]
    assert "-I -S -c" in handler["commandWindows"]
    assert len(handler["commandWindows"]) < 8191
    encoded = re.search(
        r"b64decode\('([^']+)'\)", handler["commandWindows"]
    )
    assert encoded is not None
    verifier = base64.b64decode(encoded.group(1))
    assert f"EXPECTED={digest!r}".encode("ascii") in verifier
    assert b"'DRYDOCK_RUNTIME_SHA256':EXPECTED" in verifier


def test_safe_shell_and_patch_emit_no_decision(tmp_path: Path) -> None:
    root = _project(tmp_path)
    shell = _run(PLUGIN_ROOT, _pretool("Bash", {"command": "git status"}, root))
    patch = _run(
        PLUGIN_ROOT,
        _pretool(
            "apply_patch",
            {"command": "*** Begin Patch\n*** Add File: app.py\n+print('ok')\n*** End Patch\n"},
            root,
        ),
        index=1,
    )
    assert shell.returncode == 0
    assert shell.stdout == ""
    assert patch.returncode == 0
    assert patch.stdout == ""


@pytest.mark.parametrize(
    ("tool_name", "tool_input", "expected"),
    [
        ("Bash", {"command": "git -C . reset --hard"}, "hard reset"),
        ("Bash", {"command": "Set-Content -LiteralPath .env -Value secret"}, "secret"),
        (
            "apply_patch",
            {"command": "*** Begin Patch\n*** Add File: .env\n+x=y\n*** End Patch\n"},
            "secret",
        ),
        ("apply_patch", {}, "unsupported apply_patch contract"),
        ("renamed_shell", {"command": "git status"}, "unsupported tool contract"),
    ],
)
def test_supported_contracts_fail_closed(
    tmp_path: Path,
    tool_name: str,
    tool_input: dict[str, object],
    expected: str,
) -> None:
    root = _project(tmp_path)
    result = _run(
        PLUGIN_ROOT,
        _pretool(tool_name, tool_input, root),
        index=1 if tool_name == "apply_patch" else 0,
    )
    assert result.returncode == 0
    assert expected.casefold() in (_deny_reason(result) or "").casefold()


def test_packet_guard_blocks_new_ci_without_packet(tmp_path: Path) -> None:
    root = _project(tmp_path)
    result = _run(
        PLUGIN_ROOT,
        _pretool(
            "apply_patch",
            {
                "command": (
                    "*** Begin Patch\n"
                    "*** Add File: .github/workflows/release.yml\n"
                    "+name: release\n"
                    "*** End Patch\n"
                )
            },
            root,
        ),
        index=1,
    )
    assert "new CI workflow/config" in (_deny_reason(result) or "")
    assert not (root / ".github" / "workflows" / "release.yml").exists()


def test_tampered_runtime_denies_before_execution(tmp_path: Path) -> None:
    plugin = tmp_path / "plugin path with spaces"
    shutil.copytree(PLUGIN_ROOT, plugin)
    runtime = plugin / "hooks" / "runtime.py"
    runtime.write_text("print('TAMPERED_EXECUTED')\n", encoding="utf-8")

    result = _run(
        plugin,
        _pretool("Bash", {"command": "git status"}, tmp_path),
    )
    assert "TAMPERED_EXECUTED" not in result.stdout
    assert "integrity verification failed" in (_deny_reason(result) or "")


def test_unmanifested_python_file_denies_and_check_fails(tmp_path: Path) -> None:
    plugin = tmp_path / "plugin"
    shutil.copytree(PLUGIN_ROOT, plugin)
    (plugin / "hooks" / "extra.py").write_text("print('EXTRA')\n", encoding="utf-8")

    assert any(
        "unexpected executable hook files" in failure
        for failure in build_hooks.verify_outputs(
            plugin / "scripts" / "hook_runtime_source.py", plugin / "hooks"
        )
    )
    result = _run(
        plugin,
        _pretool("Bash", {"command": "git status"}, tmp_path),
    )
    assert "EXTRA" not in result.stdout
    assert "integrity verification failed" in (_deny_reason(result) or "")


def test_current_invocation_executes_captured_bytes_after_replacement(
    tmp_path: Path,
) -> None:
    plugin = tmp_path / "plugin with spaces"
    source = plugin / "scripts" / "source.py"
    hooks = plugin / "hooks"
    source.parent.mkdir(parents=True)
    source.write_text(
        "import os\n"
        "from pathlib import Path\n"
        "runtime = Path(os.environ['PLUGIN_ROOT']) / 'hooks' / 'runtime.py'\n"
        "runtime.write_text(\"print('REPLACEMENT_EXECUTED')\\n\", encoding='utf-8')\n"
        "print('CAPTURED_EXECUTED')\n",
        encoding="utf-8",
    )
    for name, content in build_hooks.build_outputs(source).items():
        hooks.mkdir(parents=True, exist_ok=True)
        (hooks / name).write_bytes(content)

    payload = _pretool("Bash", {"command": "git status"}, tmp_path)
    first = _run(plugin, payload)
    second = _run(plugin, payload)
    assert first.stdout.strip() == "CAPTURED_EXECUTED"
    assert "REPLACEMENT_EXECUTED" not in first.stdout
    assert "REPLACEMENT_EXECUTED" not in second.stdout
    assert "integrity verification failed" in (_deny_reason(second) or "")


def test_isolated_startup_ignores_repository_sitecustomize(tmp_path: Path) -> None:
    marker = tmp_path / "startup-injection-ran.txt"
    (tmp_path / "sitecustomize.py").write_text(
        f"open({str(marker)!r}, 'w').write('ran')\n", encoding="utf-8"
    )
    result = _run(
        PLUGIN_ROOT,
        _pretool("Bash", {"command": "git status"}, tmp_path),
        cwd=tmp_path,
    )
    assert result.returncode == 0
    assert result.stdout == ""
    assert not marker.exists()


def test_session_liveness_is_revision_bound_and_readiness_stays_inactive(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    (root / "PROJECT_CONTEXT.md").write_text(
        "# Context\n\nConfirmed outcome, stack, users, constraints, and done state.\n",
        encoding="utf-8",
    )
    data = tmp_path / "plugin-data"
    payload = {
        "hook_event_name": "SessionStart",
        "session_id": "session-123",
        "source": "startup",
        "cwd": str(root.resolve()),
        "model": "gpt-test",
        "permission_mode": "default",
    }
    result = _run(
        PLUGIN_ROOT,
        payload,
        event="SessionStart",
        plugin_data=data,
    )
    assert "hook_liveness=recorded" in result.stdout

    session_record = data / "liveness" / "session-123.json"
    baseline = session_record.read_bytes()
    report = drydock_codex.readiness(
        root, "session-123", data, hook_liveness_probe=True
    )
    assert (
        report["enforcement"]["active_task_liveness"]
        == "stale_or_mismatched"
    )

    ordinary = _run(
        PLUGIN_ROOT,
        _pretool("Bash", {"command": "git status"}, root, "session-123"),
        plugin_data=data,
    )
    assert ordinary.returncode == 0
    assert ordinary.stdout == ""
    assert not (data / "activity" / "session-123.json").exists()
    assert session_record.read_bytes() == baseline

    quoted_probe = _run(
        PLUGIN_ROOT,
        _pretool(
            "Bash",
            {"command": "echo readiness --hook-liveness-probe"},
            root,
            "session-123",
        ),
        plugin_data=data,
    )
    assert quoted_probe.returncode == 0
    assert quoted_probe.stdout == ""
    assert not (data / "activity" / "session-123.json").exists()

    patch = _run(
        PLUGIN_ROOT,
        _pretool(
            "apply_patch",
            {
                "command": (
                    "*** Begin Patch\n"
                    "*** Add File: app.py\n"
                    "+print('ok')\n"
                    "*** End Patch\n"
                )
            },
            root,
            "session-123",
        ),
        index=1,
        plugin_data=data,
    )
    assert patch.returncode == 0
    assert patch.stdout == ""
    assert not (data / "activity" / "session-123.json").exists()

    denied_probe = _run(
        PLUGIN_ROOT,
        _pretool(
            "Bash",
            {
                "command": (
                    f'python "{PLUGIN_ROOT / "scripts" / "drydock_codex.py"}" '
                    f'readiness --root "{root}" --hook-liveness-probe ; '
                    "Set-Content -LiteralPath .env -Value blocked"
                )
            },
            root,
            "session-123",
        ),
        plugin_data=data,
    )
    assert "secret" in (_deny_reason(denied_probe) or "").casefold()
    assert not (data / "activity" / "session-123.json").exists()

    probe_command = (
        f'python "{PLUGIN_ROOT / "scripts" / "drydock_codex.py"}" '
        f'readiness --root "{root}" --hook-liveness-probe'
    )
    activity = _run(
        PLUGIN_ROOT,
        _pretool(
            "Bash",
            {"command": probe_command},
            root,
            "session-123",
        ),
        plugin_data=data,
    )
    assert activity.returncode == 0
    assert activity.stdout == ""

    report = drydock_codex.readiness(
        root, "session-123", data, hook_liveness_probe=True
    )
    assert (
        report["enforcement"]["active_task_liveness"]
        == "current_revision_observed"
    )
    assert report["enforcement"]["liveness_evidence"]["model"] == "gpt-test"
    assert (
        report["enforcement"]["liveness_evidence"]["permission_mode"]
        == "default"
    )
    assert (
        report["enforcement"]["liveness_evidence"][
            "model_and_permission_source"
        ]
        == "fresh_PreToolUse_activity"
    )
    assert report["enforcement"]["liveness_evidence"]["activity_tool"] == "Bash"
    assert (
        report["enforcement"]["liveness_evidence"]["authentication"]
        == "none_unsigned_user_writable_plugin_data"
    )
    assert report["enforcement"]["active"] is False
    assert report["ready_for_enforcement"] is False
    assert report["enforcement"]["trusted"] == "unknown"

    activity_path = data / "activity" / "session-123.json"
    activity_record = json.loads(activity_path.read_text(encoding="utf-8"))
    activity_record["observed_unix_ns"] = (
        time.time_ns() - drydock_codex.ACTIVITY_FRESHNESS_WINDOW_NS - 1
    )
    activity_path.write_text(json.dumps(activity_record), encoding="utf-8")
    replayed = drydock_codex.readiness(
        root, "session-123", data, hook_liveness_probe=True
    )
    assert (
        replayed["enforcement"]["active_task_liveness"]
        == "stale_or_mismatched"
    )


def test_stop_gate_uses_session_baseline_and_pending_verification(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path)
    packet = root / "sdd-plus" / "changes" / "change"
    packet.mkdir()
    tasks = packet / "tasks.md"
    tasks.write_text("- [ ] implement\n", encoding="utf-8")
    (packet / "verification.md").write_text(
        "# Verification\n\n## Result\n\nPending.\n", encoding="utf-8"
    )
    data = tmp_path / "plugin-data"
    common = {
        "session_id": "stop-session",
        "cwd": str(root.resolve()),
        "model": "gpt-test",
        "permission_mode": "default",
    }
    start = _run(
        PLUGIN_ROOT,
        {**common, "hook_event_name": "SessionStart", "source": "startup"},
        event="SessionStart",
        plugin_data=data,
    )
    assert start.returncode == 0
    tasks.write_text("- [x] implement\n", encoding="utf-8")

    stop = _run(
        PLUGIN_ROOT,
        {**common, "hook_event_name": "Stop"},
        event="Stop",
        plugin_data=data,
    )
    document = json.loads(stop.stdout)
    assert document["continue"] is False
    assert "verification.md is still Pending" in document["stopReason"]
