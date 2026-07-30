from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import orchestration_evidence as evidence


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64


def test_stdin_reader_preserves_raw_utf8_under_non_utf8_text_wrapper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = "Codex \u2192 verifier"
    monkeypatch.setattr(
        sys,
        "stdin",
        io.TextIOWrapper(
            io.BytesIO(expected.encode("utf-8")),
            encoding="cp1252",
        ),
    )

    assert (
        evidence.read_utf8_stdin(maximum=64, label="test input") == expected
    )


@pytest.mark.parametrize(
    ("body", "maximum", "message"),
    [
        (b"\x81", 64, "not valid UTF-8"),
        (b"x" * 65, 64, "exceeds its input byte bound"),
    ],
)
def test_stdin_reader_fails_closed_on_invalid_or_oversized_bytes(
    body: bytes,
    maximum: int,
    message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.TextIOWrapper(io.BytesIO(body), encoding="cp1252"),
    )

    with pytest.raises(evidence.EvidenceError, match=message):
        evidence.read_utf8_stdin(maximum=maximum, label="test input")


def _launchguardian_report(
    target: Path,
    *,
    launch_status: str = "APPROVED",
    scanner_state: str = "ran",
    blocked: bool = False,
) -> dict[str, object]:
    scanners = {
        name: "ran"
        for name in evidence.EXPECTED_LAUNCHGUARDIAN_SCANNERS
    }
    if scanner_state != "ran":
        scanners["semgrep"] = scanner_state
    blocking_counts = {
        name: 0 for name in evidence.EXPECTED_LAUNCHGUARDIAN_SCANNERS
    }
    scanner_counts = {
        name: 0 for name in evidence.EXPECTED_LAUNCHGUARDIAN_SCANNERS
    }
    findings: list[dict[str, object]] = []
    blocking_findings: list[dict[str, object]] = []
    counts_by_severity = {
        severity: 0
        for severity in evidence.EXPECTED_LAUNCHGUARDIAN_SEVERITIES
    }
    counts_by_scanner: dict[str, int] = {}
    counts_by_status: dict[str, int] = {}
    counts_by_gate: dict[str, int] = {}
    configured_dispositions: list[dict[str, str]] = []
    if scanner_state == "unavailable":
        findings.append(
            {
                "title": "Semgrep scanner unavailable",
                "category": "scanner_unavailable",
                "source": "semgrep",
                "severity": "medium",
                "status": "open",
                "related_gate": "Gate 3",
                "blocks_launch": True,
                "rule_id": "",
                "disposition": None,
            }
        )
    elif scanner_state == "disabled":
        findings.append(
            {
                "title": "Semgrep scanner disabled by config",
                "category": "scanner_disabled",
                "source": "config",
                "severity": "high",
                "status": "open",
                "related_gate": "Gate 3",
                "blocks_launch": True,
                "rule_id": "",
                "disposition": None,
            }
        )
    if launch_status == "APPROVED_WITH_DISPOSITIONS":
        disposition = {
            "source": "semgrep",
            "rule_id": "test.semgrep.rule",
            "status": "not_applicable",
            "reason": "The exact test rule is outside the supported runtime.",
            "evidence": "The test fixture binds this exact reviewed rule.",
            "approved_by": "Drydock test owner",
            "approved_on": "2026-07-25",
        }
        configured_dispositions.append(disposition)
        findings.append(
            {
                "title": "Semgrep disposed finding",
                "category": "code_security",
                "source": "semgrep",
                "severity": "high",
                "status": "not_applicable",
                "related_gate": "Gate 3",
                "blocks_launch": True,
                "rule_id": "test.semgrep.rule",
                "disposition": disposition,
            }
        )
    if blocked:
        finding = {
            "title": "Semgrep policy finding",
            "category": "code_security",
            "source": "semgrep",
            "severity": "high",
            "status": "open",
            "related_gate": "Gate 3",
            "blocks_launch": True,
            "rule_id": "test.semgrep.blocker",
            "disposition": None,
        }
        findings.append(finding)
    blocking_findings = [
        finding
        for finding in findings
        if finding["blocks_launch"] is True and finding["status"] == "open"
    ]
    for finding in findings:
        severity = str(finding["severity"])
        source = str(finding["source"])
        status = str(finding["status"])
        gate = str(finding["related_gate"]) or "Unmapped"
        counts_by_severity[severity] += 1
        counts_by_scanner[source] = counts_by_scanner.get(source, 0) + 1
        counts_by_status[status] = counts_by_status.get(status, 0) + 1
        counts_by_gate[gate] = counts_by_gate.get(gate, 0) + 1
    if scanners["semgrep"] == "ran":
        scanner_counts["semgrep"] = sum(
            1 for finding in findings if finding["source"] == "semgrep"
        )
        blocking_counts["semgrep"] = sum(
            1
            for finding in blocking_findings
            if finding["source"] == "semgrep"
        )
    elif scanners["semgrep"] == "unavailable":
        blocking_counts["semgrep"] = sum(
            1
            for finding in blocking_findings
            if finding["source"] == "semgrep"
        )
    elif scanners["semgrep"] == "disabled":
        blocking_counts["semgrep"] = sum(
            1
            for finding in blocking_findings
            if finding["source"] == "config"
            and finding["category"] == "scanner_disabled"
            and finding["title"] == "Semgrep scanner disabled by config"
        )
    return {
        "schema_name": "launchguardian.report",
        "schema_version": "0.2.0",
        "generated_at": "2026-07-29T00:00:00Z",
        "launchguardian_version": "0.2.0",
        "target": str(target.resolve(strict=True)),
        "mode": "framework",
        "validation_mode": "framework",
        "scan_mode": "local",
        "lgf_validation_skipped": False,
        "strict_scanners": True,
        "launch_status": launch_status,
        "lgf_config_valid": True,
        "lgf_validation_status": "valid",
        "scanner_availability": scanners,
        "scanner_counts": scanner_counts,
        "scanner_blocking_counts": blocking_counts,
        "counts_by_severity": counts_by_severity,
        "counts_by_scanner": counts_by_scanner,
        "counts_by_status": counts_by_status,
        "counts_by_gate": counts_by_gate,
        "blocking_findings": blocking_findings,
        "launchguardian_config": {
            "finding_dispositions": configured_dispositions,
        },
        "blocked": bool(blocking_findings),
        "findings": findings,
    }


def _git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "drydock@example.invalid")
    _git(repo, "config", "user.name", "Drydock Tests")
    (repo / ".gitignore").write_text(
        "__pycache__/\n*.py[cod]\nconftest.py\n", encoding="utf-8"
    )
    (repo / ".gitattributes").write_text("* text=auto eol=lf\n", encoding="utf-8")
    (repo / "app.py").write_text("print('ok')\n", encoding="utf-8")
    packet = repo / "sdd-plus" / "changes" / "change"
    packet.mkdir(parents=True)
    (packet / "tasks.md").write_text("- [ ] verify\n", encoding="utf-8")
    (packet / "verification.md").write_text("# Verification\n", encoding="utf-8")
    review = {
        "schema_version": 1,
        "evidence_kind": "peer_review_summary",
        "converged": True,
        "overall": "reviewed",
        "blocking_concerns": [],
        "gaps": [],
        "risks": [],
        "required_changes": [],
    }
    (packet / "claude-architecture-review-round-1.json").write_text(
        json.dumps(review), encoding="utf-8"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "fixture")
    return repo


def test_git_helper_pins_canonical_root_and_strips_hostile_git_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "proof root with spaces"
    parent.mkdir()
    repo = _repo(parent)
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", str(tmp_path / "poison"))
    observed: dict[str, object] = {}
    original = evidence.subprocess.run

    def capture(
        arguments: list[str], *args: object, **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        observed["arguments"] = list(arguments)
        observed["cwd"] = kwargs["cwd"]
        observed["env"] = dict(kwargs["env"])
        return original(arguments, *args, **kwargs)

    monkeypatch.setattr(evidence.subprocess, "run", capture)
    head = evidence._git(repo, ["rev-parse", "HEAD"])
    assert len(head.strip()) == 40

    arguments = observed["arguments"]
    assert isinstance(arguments, list)
    assert arguments[1:3] == [
        "-c",
        f"safe.directory={repo.resolve().as_posix()}",
    ]
    assert observed["cwd"] == repo.resolve()
    environment = observed["env"]
    assert isinstance(environment, dict)
    assert "GIT_OBJECT_DIRECTORY" not in environment
    assert environment["GIT_CONFIG_GLOBAL"] == os.devnull
    assert environment["GIT_CONFIG_SYSTEM"] == os.devnull
    assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
    assert environment["GIT_ATTR_NOSYSTEM"] == "1"
    assert environment["GIT_OPTIONAL_LOCKS"] == "0"
    assert environment["GIT_TERMINAL_PROMPT"] == "0"


def test_git_object_batch_pins_canonical_root_and_strips_hostile_git_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "proof root with spaces"
    parent.mkdir()
    repo = _repo(parent)
    hostile = {
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(tmp_path / "alternate"),
        "GIT_COMMON_DIR": str(tmp_path / "common"),
        "GIT_DIR": str(tmp_path / "git-dir"),
        "GIT_INDEX_FILE": str(tmp_path / "index"),
        "GIT_OBJECT_DIRECTORY": str(tmp_path / "objects"),
        "GIT_WORK_TREE": str(tmp_path / "work-tree"),
    }
    for key, value in hostile.items():
        monkeypatch.setenv(key, value)
    observed: list[dict[str, object]] = []
    original = evidence.subprocess.run

    def capture(
        arguments: list[str], *args: object, **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        if "cat-file" in arguments:
            observed.append(
                {
                    "arguments": list(arguments),
                    "cwd": kwargs["cwd"],
                    "env": dict(kwargs["env"]),
                }
            )
        return original(arguments, *args, **kwargs)

    monkeypatch.setattr(evidence.subprocess, "run", capture)
    evidence.repository_fingerprints(
        repo,
        packet_root="sdd-plus/changes/change",
    )
    assert len(observed) == 1

    invocation = observed[0]
    arguments = invocation["arguments"]
    assert isinstance(arguments, list)
    assert arguments[1:5] == [
        "-c",
        f"safe.directory={repo.resolve().as_posix()}",
        "cat-file",
        "--batch",
    ]
    assert invocation["cwd"] == repo.resolve()
    environment = invocation["env"]
    assert isinstance(environment, dict)
    expected_git_environment = {
        "GIT_ATTR_NOSYSTEM",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_NOSYSTEM",
        "GIT_CONFIG_SYSTEM",
        "GIT_OPTIONAL_LOCKS",
        "GIT_TERMINAL_PROMPT",
    }
    assert {
        key for key in environment if key.upper().startswith("GIT_")
    } == expected_git_environment
    assert environment["GIT_CONFIG_GLOBAL"] == os.devnull
    assert environment["GIT_CONFIG_SYSTEM"] == os.devnull
    assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
    assert environment["GIT_ATTR_NOSYSTEM"] == "1"
    assert environment["GIT_OPTIONAL_LOCKS"] == "0"
    assert environment["GIT_TERMINAL_PROMPT"] == "0"


def test_git_path_resolution_failure_is_structured_evidence_error(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing repository"
    with pytest.raises(
        evidence.EvidenceError,
        match="Git repository path could not be resolved",
    ):
        evidence._resolved_git_path(missing)


def test_envelope_rejects_invalid_values() -> None:
    with pytest.raises(evidence.EvidenceError, match="positive"):
        evidence.Envelope(0, 1, 1, 1)
    with pytest.raises(evidence.EvidenceError, match="positive"):
        evidence.Envelope(1, 0, 1, 1)


def test_run_ledger_enforces_phase_and_cumulative_envelopes(
    tmp_path: Path,
) -> None:
    root = evidence.state_root(tmp_path / "state")
    phase = evidence.Envelope(30, 1, 20, 1)
    ledger = evidence.RunLedger.start(
        root,
        objective_digest=DIGEST_A,
        owner_action_digest=DIGEST_B,
        phase_envelopes={"plan_peer": phase},
        run_envelope=evidence.Envelope(60, 2, 30, 2),
        now=100,
    )
    first = ledger.reserve(
        "plan_peer",
        input_bytes=20,
        configured_provider_usd=1,
        model="claude-opus-5",
        now=101,
    )
    assert first["ok"] is True
    blocked = ledger.reserve(
        "plan_peer",
        input_bytes=1,
        configured_provider_usd=0,
        model="claude-opus-5",
        now=102,
    )
    assert blocked["stage"] == "envelope_exhausted"
    assert blocked["gate_effect"] == "none"
    report = ledger.complete(
        first["reservation_id"],
        observed_provider_usd=None,
        now=103,
    )
    assert report["elapsed_seconds"] == 2
    assert report["provider_cost"] == "unknown"
    assert report["run"]["usage"]["token_usage"] == "unknown"


def test_run_elapsed_ceiling_spans_resumed_idle_time(tmp_path: Path) -> None:
    root = evidence.state_root(tmp_path / "state")
    ledger = evidence.RunLedger.start(
        root,
        objective_digest=DIGEST_A,
        owner_action_digest=DIGEST_B,
        run_envelope=evidence.Envelope(10, 4, 1000, 4),
        now=100,
    )
    reservation = ledger.reserve(
        "plan_peer",
        input_bytes=10,
        configured_provider_usd=1,
        model="claude-opus-5",
        now=101,
    )
    ledger.complete(
        reservation["reservation_id"],
        observed_provider_usd=0.1,
        now=102,
    )
    resumed = ledger.reserve(
        "mutation",
        input_bytes=10,
        configured_provider_usd=0,
        model="gpt-5.6-sol",
        now=111,
    )
    assert resumed["stage"] == "envelope_exhausted"
    assert "run.elapsed_seconds" in resumed["exhausted"]


def test_run_supersession_requires_recorded_owner_digests(
    tmp_path: Path,
) -> None:
    root = evidence.state_root(tmp_path / "state")
    first = evidence.RunLedger.start(
        root,
        objective_digest=DIGEST_A,
        owner_action_digest=DIGEST_B,
        now=100,
    )
    second = evidence.RunLedger.start(
        root,
        objective_digest=DIGEST_C,
        owner_action_digest=DIGEST_A,
        previous_run_id=first.run_id,
        now=200,
    )
    assert first.read()["status"] == "superseded"
    transition = second.read()["transition"]
    assert transition["old_run_id"] == first.run_id
    assert transition["new_run_id"] == second.run_id
    serialized = second.path.read_text(encoding="utf-8")
    assert "raw objective" not in serialized
    with pytest.raises(evidence.EvidenceError, match="digest"):
        evidence.RunLedger.start(
            root,
            objective_digest="raw objective",
            owner_action_digest=DIGEST_B,
        )


def _write_abandoned_lock(path: Path, body: object) -> None:
    lock = path.with_name(f".{path.name}.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps(body), encoding="utf-8")


def test_dead_ledger_locks_recover_across_all_mutations(tmp_path: Path) -> None:
    root = evidence.state_root(tmp_path / "state")

    reserving = evidence.RunLedger.start(
        root,
        objective_digest=DIGEST_A,
        owner_action_digest=DIGEST_B,
    )
    _write_abandoned_lock(
        reserving.path,
        {
            "process": {"pid": 2147483646, "started": "dead"},
            "created_at": 0,
        },
    )
    reservation = reserving.reserve(
        "plan_peer",
        input_bytes=1,
        configured_provider_usd=0,
        model="claude-opus-5",
    )
    assert reservation["ok"] is True

    reserving.path.with_name(f".{reserving.path.name}.lock").write_text(
        "not-json", encoding="utf-8"
    )
    reserving.complete(
        reservation["reservation_id"],
        observed_provider_usd=0,
    )

    closing = evidence.RunLedger.start(
        root,
        objective_digest=DIGEST_A,
        owner_action_digest=DIGEST_B,
    )
    _write_abandoned_lock(
        closing.path,
        {
            "process": {
                "pid": os.getpid(),
                "started": "definitely-not-the-current-process-token",
            },
            "created_at": time.time(),
        },
    )
    closing.close("blocked")
    assert closing.read()["status"] == "blocked"

    superseded = evidence.RunLedger.start(
        root,
        objective_digest=DIGEST_A,
        owner_action_digest=DIGEST_B,
    )
    _write_abandoned_lock(
        superseded.path,
        {
            "process": evidence.process_identity(os.getpid()),
            "created_at": 0,
        },
    )
    successor = evidence.RunLedger.start(
        root,
        objective_digest=DIGEST_C,
        owner_action_digest=DIGEST_A,
        previous_run_id=superseded.run_id,
    )
    assert superseded.read()["status"] == "superseded"
    assert successor.read()["transition"]["old_run_id"] == superseded.run_id


def test_live_ledger_lock_is_refused(tmp_path: Path) -> None:
    root = evidence.state_root(tmp_path / "state")
    ledger = evidence.RunLedger.start(
        root,
        objective_digest=DIGEST_A,
        owner_action_digest=DIGEST_B,
    )
    with evidence._exclusive_record_lock(ledger.path):
        with pytest.raises(evidence.EvidenceError, match="concurrent"):
            ledger.reserve(
                "plan_peer",
                input_bytes=1,
                configured_provider_usd=0,
                model="claude-opus-5",
            )
    live_payload = {
        "process": evidence.process_identity(os.getpid()),
        "created_at": time.time(),
    }
    _write_abandoned_lock(ledger.path, live_payload)
    with pytest.raises(evidence.EvidenceError, match="live"):
        ledger.reserve(
            "plan_peer",
            input_bytes=1,
            configured_provider_usd=0,
            model="claude-opus-5",
        )
    assert json.loads(
        ledger.path.with_name(f".{ledger.path.name}.lock").read_text(
            encoding="utf-8"
        )
    ) == live_payload


def test_objective_properties_force_full_critique_and_skip_is_not_gate() -> None:
    result = evidence.objective_critique_requirement(
        ["permissions", "documentation"]
    )
    assert result == {
        "mode": "FULL",
        "critique_required": True,
        "matched_properties": ["permissions"],
    }
    skipped = evidence.critique_skipped("peer rate limited")
    assert skipped["peer_convergence"] == "not_established"
    assert skipped["gate_satisfied"] is False


def _invocation_fingerprint(run_id: str) -> str:
    return evidence.InvocationStore.fingerprint(
        candidate=DIGEST_A,
        request_digest=DIGEST_B,
        model="claude-opus-5",
        schema_digest=DIGEST_C,
        configuration_digest=DIGEST_A,
        run_id=run_id,
    )


def test_single_flight_attaches_then_recovers_bounded_terminal(
    tmp_path: Path,
) -> None:
    store = evidence.InvocationStore(evidence.state_root(tmp_path / "state"))
    fingerprint = _invocation_fingerprint("1" * 32)
    assert store.prepare(fingerprint, lease_seconds=30, now=100)["action"] == "start"
    attached = store.prepare(fingerprint, lease_seconds=30, now=101)
    assert attached["action"] == "attach"
    persisted = store.terminal(
        fingerprint,
        {"ok": True, "critique": {"converged": True}},
        classification="complete",
        reason="schema-valid",
        now=102,
    )
    assert persisted["status"] == "persisted"
    recovered = store.prepare(fingerprint, lease_seconds=30, now=103)
    assert recovered["action"] == "recover"
    assert recovered["authenticated"] is False
    assert recovered["body"]["ok"] is True
@pytest.mark.parametrize(
    "body",
    [
        {"result": "api_key=abcdefghijklmnop"},
        {"result": "x" * (evidence.MAX_TERMINAL_BYTES + 1)},
    ],
)
def test_terminal_secret_or_oversize_body_is_not_recoverable(
    tmp_path: Path, body: dict[str, str]
) -> None:
    store = evidence.InvocationStore(evidence.state_root(tmp_path / uuid_name()))
    fingerprint = _invocation_fingerprint(hashlib.sha256(str(body).encode()).hexdigest()[:32])
    assert store.prepare(fingerprint, lease_seconds=30)["action"] == "start"
    result = store.terminal(
        fingerprint,
        body,
        classification="complete",
        reason="screened",
    )
    assert result["status"] == "terminal_result_not_persisted"
    retry = store.prepare(fingerprint, lease_seconds=30)
    assert retry["action"] == "return_to_owner"
    assert retry["stage"] == "terminal_result_not_persisted"


def uuid_name() -> str:
    return hashlib.sha256(os.urandom(16)).hexdigest()[:16]


def test_terminal_expiry_deletes_body_on_next_access(tmp_path: Path) -> None:
    store = evidence.InvocationStore(evidence.state_root(tmp_path / "state"))
    fingerprint = _invocation_fingerprint("2" * 32)
    store.prepare(fingerprint, lease_seconds=30, now=100)
    store.terminal(
        fingerprint,
        {"ok": True},
        classification="complete",
        reason="done",
        now=101,
    )
    result = store.prepare(
        fingerprint,
        lease_seconds=30,
        now=101 + evidence.MAX_RESULT_AGE_SECONDS + 1,
    )
    assert result["stage"] == "stale_terminal_result"
    record = json.loads(store._path(fingerprint).read_text(encoding="utf-8"))
    assert "body" not in record


def test_interrupted_invocation_never_restarts_automatically(
    tmp_path: Path,
) -> None:
    store = evidence.InvocationStore(evidence.state_root(tmp_path / "state"))
    fingerprint = _invocation_fingerprint("3" * 32)
    store.prepare(fingerprint, lease_seconds=30, now=100)
    path = store._path(fingerprint)
    record = json.loads(path.read_text(encoding="utf-8"))
    record["process"] = {"pid": 2147483646, "started": "absent"}
    record["lease_expires_at"] = 101
    path.write_text(json.dumps(record), encoding="utf-8")
    result = store.prepare(fingerprint, lease_seconds=30, now=200)
    assert result["stage"] == "indeterminate_interrupted_call"
    assert result["automatic_restart"] is False


def test_state_root_refuses_repository_descendant(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(evidence.EvidenceError, match="outside"):
        evidence.state_root(repo / ".state", repository_root=repo)


def test_repository_fingerprints_partition_evidence_and_bytecode(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    packet_root = "sdd-plus/changes/change"
    clean = evidence.repository_fingerprints(
        repo,
        packet_root=packet_root,
        exclude_evidence_path=f"{packet_root}/verification.md",
    )
    assert clean["reuse_eligible"] is True
    assert clean["packet_evidence_excluded_path"].endswith("verification.md")

    cache = repo / "__pycache__"
    cache.mkdir()
    (cache / "app.cpython-311.pyc").write_bytes(b"derived")
    ignored_cache = evidence.repository_fingerprints(
        repo, packet_root=packet_root
    )
    assert ignored_cache["reuse_eligible"] is True
    assert ignored_cache["ignored_bytecode_blocks_reuse"] is False

    (repo / "conftest.py").write_text("pytest_plugins=[]\n", encoding="utf-8")
    injected = evidence.repository_fingerprints(repo, packet_root=packet_root)
    assert injected["reuse_eligible"] is False
    assert injected["ignored_code_injection"] == ["conftest.py"]


def test_v2_fingerprint_uses_committed_blobs_not_clean_checkout_bytes(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    packet_root = "sdd-plus/changes/change"
    baseline = evidence.repository_fingerprints(repo, packet_root=packet_root)
    assert baseline["fingerprint_version"] == evidence.FINGERPRINT_VERSION
    assert baseline["fingerprint_source"] == "exact committed Git tree and blob bytes"
    assert baseline["task_projection"]["status"] == "applied"

    (repo / "app.py").write_bytes(b"print('ok')\r\n")
    assert _git(repo, "status", "--porcelain") == ""
    checkout_drift = evidence.repository_fingerprints(
        repo, packet_root=packet_root
    )
    assert checkout_drift["clean"] is True
    assert (
        checkout_drift["executable_surface_sha256"]
        == baseline["executable_surface_sha256"]
    )


def test_v2_tree_serialization_frames_embedded_nul_bytes() -> None:
    first = evidence.GitTreeEntry(
        path="a",
        path_bytes=b"a",
        mode="100644",
        object_type="blob",
        object_id="1" * 40,
        body=b"",
    )
    second = evidence.GitTreeEntry(
        path="b",
        path_bytes=b"b",
        mode="100644",
        object_type="blob",
        object_id="2" * 40,
        body=b"",
    )
    impersonating_body = b"x\x00b\x00file\x00100644\x00y"

    def legacy_serialization(entry: evidence.GitTreeEntry, body: bytes) -> bytes:
        return b"\0".join(
            (
                entry.path_bytes,
                entry.kind,
                entry.mode.encode("ascii"),
                body,
                b"",
            )
        )

    assert legacy_serialization(
        first, impersonating_body
    ) == legacy_serialization(first, b"x") + legacy_serialization(second, b"y")
    one_entry = hashlib.sha256(evidence.EXECUTABLE_DIGEST_DOMAIN)
    evidence._update_tree_digest(one_entry, first, impersonating_body)
    two_entries = hashlib.sha256(evidence.EXECUTABLE_DIGEST_DOMAIN)
    evidence._update_tree_digest(two_entries, first, b"x")
    evidence._update_tree_digest(two_entries, second, b"y")

    assert one_entry.digest() != two_entries.digest()


def test_task_status_is_evidence_but_task_contract_stays_executable(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    packet_root = "sdd-plus/changes/change"
    baseline = evidence.repository_fingerprints(repo, packet_root=packet_root)

    tasks = repo / packet_root / "tasks.md"
    tasks.write_text("- [x] verify\n", encoding="utf-8")
    _git(repo, "add", packet_root + "/tasks.md")
    _git(repo, "commit", "-m", "complete task")
    status_only = evidence.repository_fingerprints(repo, packet_root=packet_root)
    assert (
        status_only["executable_surface_sha256"]
        == baseline["executable_surface_sha256"]
    )
    assert (
        status_only["packet_evidence_sha256"]
        != baseline["packet_evidence_sha256"]
    )

    tasks.write_text("- [x] verify exact candidate\n", encoding="utf-8")
    _git(repo, "add", packet_root + "/tasks.md")
    _git(repo, "commit", "-m", "change task contract")
    contract_change = evidence.repository_fingerprints(
        repo, packet_root=packet_root
    )
    assert (
        contract_change["executable_surface_sha256"]
        != status_only["executable_surface_sha256"]
    )


def test_task_projection_is_exactly_scoped_and_declines_noncanonical_bytes(
    tmp_path: Path,
) -> None:
    canonical = (
        b"- [x] one\n"
        b"\t- [X] two\n"
        b"  - [ ] three\n"
        b"> - [x] blockquote\n"
        b"1. [x] ordered\n"
        b"```\n- [x] protocol-marker-not-Markdown\n```\n"
        b"- [~] noncanonical\n"
    )
    normalized, reason = evidence._project_tasks(canonical)
    assert reason == "applied"
    assert normalized == (
        b"- [ ] one\n"
        b"\t- [ ] two\n"
        b"  - [ ] three\n"
        b"> - [x] blockquote\n"
        b"1. [x] ordered\n"
        b"```\n- [ ] protocol-marker-not-Markdown\n```\n"
        b"- [~] noncanonical\n"
    )
    assert evidence._project_tasks(normalized)[0] == normalized
    assert evidence._project_tasks(b"\xef\xbb\xbf- [x] task\n")[0] is None
    assert evidence._project_tasks(b"- [x] task\r\n")[0] is None
    assert evidence._project_tasks("\u00a0- [x] task\n".encode("utf-8"))[0] is None

    repo = _repo(tmp_path)
    packet_root = "sdd-plus/changes/change"
    template = repo / "sdd-plus" / "templates" / "tasks.md"
    template.parent.mkdir(parents=True)
    template.write_text("- [ ] template\n", encoding="utf-8")
    _git(repo, "add", "sdd-plus/templates/tasks.md")
    _git(repo, "commit", "-m", "add template")
    baseline = evidence.repository_fingerprints(repo, packet_root=packet_root)
    template.write_text("- [x] template\n", encoding="utf-8")
    _git(repo, "add", "sdd-plus/templates/tasks.md")
    _git(repo, "commit", "-m", "change template status")
    changed = evidence.repository_fingerprints(repo, packet_root=packet_root)
    assert (
        changed["executable_surface_sha256"]
        != baseline["executable_surface_sha256"]
    )


@pytest.mark.parametrize(
    ("initial", "changed", "reason"),
    [
        (
            b"\xef\xbb\xbf- [ ] task\n",
            b"\xef\xbb\xbf- [x] task\n",
            "leading UTF-8 BOM",
        ),
        (b"- [ ] task\r\n", b"- [x] task\r\n", "CR bytes"),
        (b"\xff- [ ] task\n", b"\xff- [x] task\n", "not valid UTF-8"),
        (
            "\u00a0- [ ] task\n".encode("utf-8"),
            "\u00a0- [x] task\n".encode("utf-8"),
            "outside the canonical ASCII grammar",
        ),
    ],
)
def test_declined_task_projection_hashes_complete_file_as_executable(
    tmp_path: Path, initial: bytes, changed: bytes, reason: str
) -> None:
    repo = _repo(tmp_path)
    packet_root = "sdd-plus/changes/change"
    tasks = repo / packet_root / "tasks.md"
    with (repo / ".gitattributes").open(
        "a", encoding="utf-8", newline="\n"
    ) as stream:
        stream.write(f"{packet_root}/tasks.md -text\n")
    _git(repo, "add", ".gitattributes")
    _git(repo, "commit", "-m", "preserve raw task bytes")
    tasks.write_bytes(initial)
    _git(repo, "add", packet_root + "/tasks.md")
    _git(repo, "commit", "-m", "add noncanonical tasks")
    baseline = evidence.repository_fingerprints(repo, packet_root=packet_root)
    assert baseline["task_projection"]["status"] == "declined"
    assert reason in baseline["task_projection"]["reason"]

    tasks.write_bytes(changed)
    _git(repo, "add", packet_root + "/tasks.md")
    _git(repo, "commit", "-m", "change noncanonical task state")
    result = evidence.repository_fingerprints(repo, packet_root=packet_root)
    assert result["task_projection"]["status"] == "declined"
    assert result["executable_surface_sha256"] != baseline[
        "executable_surface_sha256"
    ]
    assert result["packet_evidence_sha256"] == baseline[
        "packet_evidence_sha256"
    ]


@pytest.mark.parametrize(
    "task_path",
    [
        "sdd-plus/templates/tasks.md",
        "assets/project-scaffold/sdd-plus/templates/tasks.md",
        "sdd-plus/changes/other/tasks.md",
    ],
)
def test_only_exact_active_packet_tasks_are_projected(
    tmp_path: Path, task_path: str
) -> None:
    repo = _repo(tmp_path)
    packet_root = "sdd-plus/changes/change"
    target = repo / task_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("- [ ] outside active packet\n", encoding="utf-8")
    _git(repo, "add", task_path)
    _git(repo, "commit", "-m", "add non-target tasks")
    baseline = evidence.repository_fingerprints(repo, packet_root=packet_root)

    target.write_text("- [x] outside active packet\n", encoding="utf-8")
    _git(repo, "add", task_path)
    _git(repo, "commit", "-m", "change non-target task state")
    changed = evidence.repository_fingerprints(repo, packet_root=packet_root)
    assert changed["executable_surface_sha256"] != baseline[
        "executable_surface_sha256"
    ]


@pytest.mark.parametrize(
    "changed",
    [
        b"- [ ] alpha\n  continuation\n- [ ] beta\n- [~] parked\n- [ ] added\n",
        b"- [ ] alpha\n  continuation\n- [~] parked\n",
        b"- [ ] beta\n- [ ] alpha\n  continuation\n- [~] parked\n",
        b"- [ ] alpha\n  changed continuation\n- [ ] beta\n- [~] parked\n",
        b"- [ ] alpha\n  continuation\n- [ ] beta\n- [?] parked\n",
    ],
)
def test_task_contract_mutations_change_executable_identity(
    tmp_path: Path, changed: bytes
) -> None:
    repo = _repo(tmp_path)
    packet_root = "sdd-plus/changes/change"
    tasks = repo / packet_root / "tasks.md"
    tasks.write_bytes(
        b"- [ ] alpha\n  continuation\n- [ ] beta\n- [~] parked\n"
    )
    _git(repo, "add", packet_root + "/tasks.md")
    _git(repo, "commit", "-m", "set task contract")
    baseline = evidence.repository_fingerprints(repo, packet_root=packet_root)

    tasks.write_bytes(changed)
    _git(repo, "add", packet_root + "/tasks.md")
    _git(repo, "commit", "-m", "change task contract")
    result = evidence.repository_fingerprints(repo, packet_root=packet_root)
    assert result["executable_surface_sha256"] != baseline[
        "executable_surface_sha256"
    ]


@pytest.mark.parametrize("attribute", ["export-ignore", "export-subst"])
def test_proof_archive_must_match_committed_tree(
    tmp_path: Path, attribute: str
) -> None:
    repo = _repo(tmp_path)
    if attribute == "export-subst":
        (repo / "app.py").write_text(
            "print('$Format:%H$')\n", encoding="utf-8"
        )
    with (repo / ".gitattributes").open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(f"app.py {attribute}\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", attribute)
    commit = _git(repo, "rev-parse", "HEAD")
    with pytest.raises(evidence.EvidenceError, match="proof archive"):
        with evidence.fresh_proof_root(repo, commit):
            pass


def test_proof_archive_rejects_tracked_symlink(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    target = repo / "symlink-target"
    target.write_text("target\n", encoding="utf-8")
    blob = _git(repo, "hash-object", "-w", "symlink-target")
    target.unlink()
    _git(repo, "update-index", "--add", "--cacheinfo", f"120000,{blob},linked")
    _git(repo, "commit", "-m", "add tracked symlink")
    commit = _git(repo, "rev-parse", "HEAD")
    with pytest.raises(evidence.EvidenceError, match="proof archive"):
        with evidence.fresh_proof_root(repo, commit):
            pass


def test_proof_materialization_rejects_gitlink(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    commit = _git(repo, "rev-parse", "HEAD")
    _git(repo, "update-index", "--add", "--cacheinfo", f"160000,{commit},nested")
    _git(repo, "commit", "-m", "add gitlink")
    commit = _git(repo, "rev-parse", "HEAD")
    with pytest.raises(evidence.EvidenceError, match="unsupported tracked types"):
        with evidence.fresh_proof_root(repo, commit):
            pass


def test_untracked_and_tracked_bytecode_disable_reuse(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "notes.tmp").write_text("untracked\n", encoding="utf-8")
    assert evidence.repository_fingerprints(repo)["reuse_eligible"] is False
    (repo / "notes.tmp").unlink()
    tracked = repo / "tracked.pyc"
    tracked.write_bytes(b"bytecode")
    _git(repo, "add", "-f", "tracked.pyc")
    _git(repo, "commit", "-m", "tracked bytecode")
    result = evidence.repository_fingerprints(repo)
    assert result["reuse_eligible"] is False
    assert result["tracked_bytecode"] == ["tracked.pyc"]


def test_fresh_proof_root_and_final_suite_binding(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    commit = _git(repo, "rev-parse", "HEAD")
    result = evidence.run_proof_command(
        repo,
        commit=commit,
        command=[
            sys.executable,
            "-c",
            "import os; assert os.environ['PYTHONDONTWRITEBYTECODE']=='1'",
        ],
        timeout=30,
    )
    assert result["terminal_status"] == "passed"
    fingerprint = evidence.repository_fingerprints(repo)[
        "executable_surface_sha256"
    ]
    full = {
        **result,
        "schema_version": 2,
        "fingerprint_version": evidence.FINGERPRINT_VERSION,
        "scope": "full_required_suite",
        "executable_surface_sha256": fingerprint,
        "authenticated": False,
    }
    assert evidence.final_suite_acceptance(
        full, executable_fingerprint=fingerprint
    )["accepted"] is True
    full["fingerprint_version"] = "drydock-repository-fingerprint-v1"
    assert evidence.final_suite_acceptance(
        full, executable_fingerprint=fingerprint
    )["accepted"] is False
    full["fingerprint_version"] = evidence.FINGERPRINT_VERSION
    full["executable_surface_sha256"] = DIGEST_A
    assert evidence.final_suite_acceptance(
        full, executable_fingerprint=fingerprint
    )["accepted"] is False


def test_fresh_proof_root_materializes_verified_blobs_without_tar_extraction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    archive_named_file = repo / ".archive.tar"
    archive_named_file.write_bytes(b"committed archive-named file\n")
    _git(repo, "add", ".archive.tar")
    _git(repo, "commit", "-m", "add archive-named file")
    commit = _git(repo, "rev-parse", "HEAD")

    def refuse_tar_extraction(*args: object, **kwargs: object) -> None:
        raise AssertionError("verified proof blobs must not use tar extraction")

    monkeypatch.setattr(
        evidence.tarfile.TarFile, "extractall", refuse_tar_extraction
    )
    monkeypatch.setattr(
        evidence.tarfile.TarFile, "extract", refuse_tar_extraction
    )
    with evidence.fresh_proof_root(repo, commit) as root:
        assert (root / "app.py").is_file()
        assert (root / ".archive.tar").read_bytes() == (
            b"committed archive-named file\n"
        )


def test_reusable_proof_is_intermediate_and_exactly_bound() -> None:
    command = [sys.executable, "-m", "pytest", "-q"]
    environment_digest = DIGEST_B
    record = {
        "fingerprint_version": evidence.FINGERPRINT_VERSION,
        "scope": "intermediate",
        "terminal_status": "passed",
        "executable_surface_sha256": DIGEST_A,
        "command": command,
        "environment_sha256": environment_digest,
    }
    assert evidence.reusable_proof(
        record,
        executable_fingerprint=DIGEST_A,
        command=command,
        environment_sha256=environment_digest,
    )
    record["fingerprint_version"] = "drydock-repository-fingerprint-v1"
    assert not evidence.reusable_proof(
        record,
        executable_fingerprint=DIGEST_A,
        command=command,
        environment_sha256=environment_digest,
    )
    record["fingerprint_version"] = evidence.FINGERPRINT_VERSION
    record["scope"] = "full_required_suite"
    assert not evidence.reusable_proof(
        record,
        executable_fingerprint=DIGEST_A,
        command=command,
        environment_sha256=environment_digest,
    )


def test_proof_store_requires_clean_candidate_and_full_exact_binding(
    tmp_path: Path,
) -> None:
    store = evidence.ProofStore(evidence.state_root(tmp_path / "state"))
    command = [sys.executable, "-m", "pytest", "-q"]
    result = {
        "command": command,
        "environment_sha256": DIGEST_B,
        "terminal_status": "passed",
        "exit_code": 0,
        "timed_out": False,
        "elapsed_seconds": 1.5,
        "output_sha256": DIGEST_C,
    }
    store.record(
        executable_fingerprint=DIGEST_A,
        result=result,
        scope="intermediate",
    )
    dirty = store.intermediate(
        candidate_state={
            "reuse_eligible": False,
            "fingerprint_version": evidence.FINGERPRINT_VERSION,
            "executable_surface_sha256": DIGEST_A,
        },
        command=command,
        environment_sha256=DIGEST_B,
    )
    assert dirty["reusable"] is False
    clean = store.intermediate(
        candidate_state={
            "reuse_eligible": True,
            "fingerprint_version": evidence.FINGERPRINT_VERSION,
            "executable_surface_sha256": DIGEST_A,
        },
        command=command,
        environment_sha256=DIGEST_B,
    )
    assert clean["reusable"] is True
    assert store.final(
        executable_fingerprint=DIGEST_A,
        command=command,
        environment_sha256=DIGEST_B,
    )["accepted"] is False
    final_record = store.record(
        executable_fingerprint=DIGEST_A,
        result=result,
        scope="full_required_suite",
    )
    assert store.final(
        executable_fingerprint=DIGEST_A,
        command=command,
        environment_sha256=DIGEST_B,
    )["accepted"] is True
    assert store.accepted_record(
        str(final_record["record_key"]),
        executable_fingerprint=DIGEST_A,
    )["accepted"] is True
    assert store.accepted_record(
        DIGEST_C,
        executable_fingerprint=DIGEST_A,
    )["accepted"] is False
    intermediate_record = store.record(
        executable_fingerprint=DIGEST_A,
        result=result,
        scope="intermediate",
    )
    assert store.accepted_record(
        str(intermediate_record["record_key"]),
        executable_fingerprint=DIGEST_A,
    )["accepted"] is False
    store.record(
        executable_fingerprint=DIGEST_A,
        result=result,
        scope="intermediate",
    )
    assert store.final(
        executable_fingerprint=DIGEST_A,
        command=command,
        environment_sha256=DIGEST_B,
    )["accepted"] is True


@pytest.mark.parametrize(
    "launch_status",
    ["APPROVED", "APPROVED_WITH_DISPOSITIONS"],
)
def test_launchguardian_accepts_only_complete_candidate_bound_reports(
    tmp_path: Path, launch_status: str
) -> None:
    target = tmp_path / "candidate"
    target.mkdir()
    report = _launchguardian_report(target, launch_status=launch_status)

    accepted = evidence.launchguardian_report_acceptance(
        report,
        expected_target=target,
    )

    assert accepted["accepted"] is True
    assert accepted["workflow_outcome"] == "passed"
    assert accepted["launch_status"] == launch_status
    assert set(accepted["scanner_availability"]) == set(
        evidence.EXPECTED_LAUNCHGUARDIAN_SCANNERS
    )


@pytest.mark.parametrize(
    ("scanner_state", "launch_status", "expected_outcome"),
    [
        ("disabled", "BLOCKED", "technical_blocker"),
        ("unavailable", "BLOCKED", "technical_blocker"),
        ("failed", "INCOMPLETE", "procedural_failure"),
    ],
)
def test_launchguardian_incomplete_scanner_state_never_passes(
    tmp_path: Path,
    scanner_state: str,
    launch_status: str,
    expected_outcome: str,
) -> None:
    target = tmp_path / "candidate"
    target.mkdir()
    report = _launchguardian_report(
        target,
        launch_status=launch_status,
        scanner_state=scanner_state,
    )

    acceptance = evidence.launchguardian_report_acceptance(
        report,
        expected_target=target,
    )

    assert acceptance["accepted"] is False
    assert acceptance["workflow_outcome"] == expected_outcome


@pytest.mark.parametrize("scanner_state", ["skipped", "execution_failed"])
def test_launchguardian_unknown_scanner_state_is_malformed(
    tmp_path: Path, scanner_state: str,
) -> None:
    target = tmp_path / "candidate"
    target.mkdir()
    report = _launchguardian_report(
        target,
        launch_status="INCOMPLETE",
        scanner_state=scanner_state,
    )

    with pytest.raises(evidence.EvidenceError, match="availability state"):
        evidence.launchguardian_report_acceptance(
            report,
            expected_target=target,
        )


def test_launchguardian_policy_blocker_is_technical_and_target_is_exact(
    tmp_path: Path,
) -> None:
    target = tmp_path / "candidate"
    target.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    report = _launchguardian_report(
        target,
        launch_status="BLOCKED",
        blocked=True,
    )

    blocked = evidence.launchguardian_report_acceptance(
        report,
        expected_target=target,
    )
    assert blocked["accepted"] is False
    assert blocked["workflow_outcome"] == "technical_blocker"
    assert blocked["open_blocking_findings"] == 1

    invalid_lgf = _launchguardian_report(
        target,
        launch_status="BLOCKED",
        blocked=True,
    )
    invalid_lgf["lgf_config_valid"] = False
    invalid_lgf["lgf_validation_status"] = "blocked"
    invalid_lgf["blocked"] = True
    invalid = evidence.launchguardian_report_acceptance(
        invalid_lgf,
        expected_target=target,
    )
    assert invalid["accepted"] is False
    assert invalid["workflow_outcome"] == "technical_blocker"

    with pytest.raises(evidence.EvidenceError, match="target"):
        evidence.launchguardian_report_acceptance(
            report,
            expected_target=other,
        )


def test_launchguardian_report_rejects_schema_drift_and_duplicate_json(
    tmp_path: Path,
) -> None:
    target = tmp_path / "candidate"
    target.mkdir()
    report = _launchguardian_report(target)
    report["unexpected"] = True
    with pytest.raises(evidence.EvidenceError, match="fields"):
        evidence.launchguardian_report_acceptance(
            report,
            expected_target=target,
        )

    with pytest.raises(evidence.EvidenceError, match="duplicate key"):
        evidence._strict_json_bytes(b'{"a":1,"a":2}', "report")

    contradictory = _launchguardian_report(target)
    contradictory["scanner_counts"]["semgrep"] = 1
    with pytest.raises(evidence.EvidenceError, match="scanner counts"):
        evidence.launchguardian_report_acceptance(
            contradictory,
            expected_target=target,
        )


def test_launchguardian_dispositions_and_launch_status_are_cross_checked(
    tmp_path: Path,
) -> None:
    target = tmp_path / "candidate"
    target.mkdir()

    missing_config_record = _launchguardian_report(
        target,
        launch_status="APPROVED_WITH_DISPOSITIONS",
    )
    missing_config_record["launchguardian_config"][
        "finding_dispositions"
    ] = []
    with pytest.raises(evidence.EvidenceError, match="disposition"):
        evidence.launchguardian_report_acceptance(
            missing_config_record,
            expected_target=target,
        )

    future_review = _launchguardian_report(
        target,
        launch_status="APPROVED_WITH_DISPOSITIONS",
    )
    future_review["launchguardian_config"]["finding_dispositions"][0][
        "approved_on"
    ] = "2999-01-01"
    future_review["findings"][0]["disposition"]["approved_on"] = "2999-01-01"
    with pytest.raises(evidence.EvidenceError, match="configuration"):
        evidence.launchguardian_report_acceptance(
            future_review,
            expected_target=target,
        )

    reclassified_disposition = _launchguardian_report(
        target,
        launch_status="APPROVED_WITH_DISPOSITIONS",
    )
    reclassified_disposition["findings"][0]["blocks_launch"] = False
    with pytest.raises(evidence.EvidenceError, match="disposition"):
        evidence.launchguardian_report_acceptance(
            reclassified_disposition,
            expected_target=target,
        )

    omitted_unused_review = _launchguardian_report(target)
    omitted_unused_review["launchguardian_config"][
        "finding_dispositions"
    ] = [
        {
            "source": "semgrep",
            "rule_id": "test.semgrep.unused",
            "status": "not_applicable",
            "reason": "The exact test rule is outside the supported runtime.",
            "evidence": "The test fixture binds this exact reviewed rule.",
            "approved_by": "Drydock test owner",
            "approved_on": "2026-07-25",
        }
    ]
    with pytest.raises(evidence.EvidenceError, match="unused disposition"):
        evidence.launchguardian_report_acceptance(
            omitted_unused_review,
            expected_target=target,
        )

    contradictory_status = _launchguardian_report(target)
    contradictory_status["launch_status"] = "APPROVED_WITH_DISPOSITIONS"
    with pytest.raises(evidence.EvidenceError, match="launch or LGF status"):
        evidence.launchguardian_report_acceptance(
            contradictory_status,
            expected_target=target,
        )


def test_launchguardian_report_recomputes_every_finding_aggregate(
    tmp_path: Path,
) -> None:
    target = tmp_path / "candidate"
    target.mkdir()
    report = _launchguardian_report(target)
    finding = {
        "title": "Semgrep medium finding",
        "category": "code_security",
        "source": "semgrep",
        "severity": "medium",
        "status": "open",
        "related_gate": "Gate 3",
        "blocks_launch": False,
        "rule_id": "test.semgrep.medium",
        "disposition": None,
    }
    report["findings"] = [finding]
    report["scanner_counts"]["semgrep"] = 1
    report["counts_by_severity"] = {
        severity: int(severity == "medium")
        for severity in evidence.EXPECTED_LAUNCHGUARDIAN_SEVERITIES
    }
    report["counts_by_scanner"] = {"semgrep": 1}
    report["counts_by_status"] = {"open": 1}
    report["counts_by_gate"] = {"Gate 3": 1}
    assert evidence.launchguardian_report_acceptance(
        report,
        expected_target=target,
    )["accepted"] is True

    reassigned_aggregate = json.loads(json.dumps(report))
    reassigned_aggregate["counts_by_scanner"] = {"gitleaks": 1}
    with pytest.raises(evidence.EvidenceError, match="aggregate counts"):
        evidence.launchguardian_report_acceptance(
            reassigned_aggregate,
            expected_target=target,
        )

    reassigned_scanner_count = json.loads(json.dumps(report))
    reassigned_scanner_count["scanner_counts"]["semgrep"] = 0
    reassigned_scanner_count["scanner_counts"]["gitleaks"] = 1
    with pytest.raises(evidence.EvidenceError, match="scanner counts"):
        evidence.launchguardian_report_acceptance(
            reassigned_scanner_count,
            expected_target=target,
        )

    unmapped_gate = json.loads(json.dumps(report))
    unmapped_gate["findings"][0]["related_gate"] = ""
    unmapped_gate["counts_by_gate"] = {"Unmapped": 1}
    assert evidence.launchguardian_report_acceptance(
        unmapped_gate,
        expected_target=target,
    )["accepted"] is True

    invented_source = json.loads(json.dumps(report))
    invented_source["findings"][0]["source"] = "invented_scanner"
    invented_source["counts_by_scanner"] = {"invented_scanner": 1}
    invented_source["scanner_counts"]["semgrep"] = 0
    with pytest.raises(evidence.EvidenceError, match="source"):
        evidence.launchguardian_report_acceptance(
            invented_source,
            expected_target=target,
        )

    invented_status = json.loads(json.dumps(report))
    invented_status["findings"][0]["status"] = "invented_status"
    invented_status["counts_by_status"] = {"invented_status": 1}
    with pytest.raises(evidence.EvidenceError, match="status"):
        evidence.launchguardian_report_acceptance(
            invented_status,
            expected_target=target,
        )

    critical_without_disposition = json.loads(json.dumps(report))
    critical_without_disposition["findings"][0]["severity"] = "critical"
    critical_without_disposition["findings"][0]["status"] = "not_applicable"
    critical_without_disposition["counts_by_severity"] = {
        severity: int(severity == "critical")
        for severity in evidence.EXPECTED_LAUNCHGUARDIAN_SEVERITIES
    }
    critical_without_disposition["counts_by_status"] = {
        "not_applicable": 1
    }
    critical_without_disposition["blocking_findings"] = []
    critical_without_disposition["scanner_blocking_counts"]["semgrep"] = 0
    critical_without_disposition["blocked"] = False
    with pytest.raises(evidence.EvidenceError, match="disposition"):
        evidence.launchguardian_report_acceptance(
            critical_without_disposition,
            expected_target=target,
        )

    unavailable_reclassified = _launchguardian_report(
        target,
        launch_status="BLOCKED",
        scanner_state="unavailable",
    )
    unavailable_reclassified["findings"][0]["status"] = "not_applicable"
    unavailable_reclassified["findings"][0]["blocks_launch"] = False
    unavailable_reclassified["blocking_findings"] = []
    unavailable_reclassified["scanner_blocking_counts"]["semgrep"] = 0
    unavailable_reclassified["counts_by_status"] = {"not_applicable": 1}
    unavailable_reclassified["blocked"] = False
    unavailable_reclassified["launch_status"] = "INCOMPLETE"
    with pytest.raises(evidence.EvidenceError, match="disposition"):
        evidence.launchguardian_report_acceptance(
            unavailable_reclassified,
            expected_target=target,
        )



@pytest.mark.parametrize(
    ("scanner_state", "launch_status"),
    [
        ("disabled", "BLOCKED"),
        ("unavailable", "INCOMPLETE"),
        ("failed", "INCOMPLETE"),
    ],
)
def test_launchguardian_rejects_nonran_scanner_count_contradictions(
    tmp_path: Path,
    scanner_state: str,
    launch_status: str,
) -> None:
    target = tmp_path / "candidate"
    target.mkdir()
    report = _launchguardian_report(
        target,
        launch_status=launch_status,
        scanner_state=scanner_state,
    )

    detected_count_inflation = json.loads(json.dumps(report))
    detected_count_inflation["scanner_counts"]["semgrep"] += 1005
    with pytest.raises(evidence.EvidenceError, match="scanner counts"):
        evidence.launchguardian_report_acceptance(
            detected_count_inflation,
            expected_target=target,
        )

    blocking_count_inflation = json.loads(json.dumps(report))
    blocking_count_inflation["scanner_blocking_counts"]["semgrep"] += 1005
    with pytest.raises(evidence.EvidenceError, match="scanner counts"):
        evidence.launchguardian_report_acceptance(
            blocking_count_inflation,
            expected_target=target,
        )


def test_security_review_store_rejects_stale_replayed_and_tampered_evidence(
    tmp_path: Path,
) -> None:
    target = tmp_path / "candidate"
    target.mkdir()
    store = evidence.SecurityReviewStore(
        evidence.state_root(tmp_path / "state")
    )
    report_body = json.dumps(
        _launchguardian_report(target),
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    executable_path = str((tmp_path / "launchguardian.exe").resolve())
    command = [
        executable_path,
        "scan",
        "--target",
        str(target.resolve(strict=True)),
        "--framework-mode",
        "--strict-scanners",
        "--output-dir",
        str((tmp_path / "reports").resolve()),
    ]
    record = store.record(
        candidate_commit="1" * 40,
        executable_fingerprint=DIGEST_A,
        executable_path=executable_path,
        executable_sha256=DIGEST_B,
        command_contract=command,
        report_body=report_body,
        expected_target=target,
        elapsed_seconds=1.0,
        process_exit_code=0,
        process_output_sha256=DIGEST_C,
        owner_checkout_unchanged=True,
        workflow_binding_sha256=DIGEST_C,
    )
    assert store.acceptance(
        record,
        candidate_commit="1" * 40,
        executable_fingerprint=DIGEST_A,
    )["accepted"] is True
    assert store.accepted_record(
        str(record["record_key"]),
        executable_fingerprint=DIGEST_A,
        workflow_binding_sha256=DIGEST_C,
    )["accepted"] is True
    assert store.accepted_record(
        DIGEST_C,
        executable_fingerprint=DIGEST_A,
        workflow_binding_sha256=DIGEST_C,
    )["accepted"] is False
    assert store.accepted_record(
        str(record["record_key"]),
        executable_fingerprint=DIGEST_A,
        workflow_binding_sha256=DIGEST_B,
    )["accepted"] is False
    stale = store.acceptance(
        record,
        candidate_commit="1" * 40,
        executable_fingerprint=DIGEST_A,
        now=(
            float(record["recorded_at"])
            + evidence.MAX_RESULT_AGE_SECONDS
            + 1
        ),
    )
    assert stale["accepted"] is False
    assert "stale" in str(stale["reason"])
    assert store.acceptance(
        record,
        candidate_commit="2" * 40,
        executable_fingerprint=DIGEST_A,
    )["accepted"] is False
    assert store.acceptance(
        record,
        candidate_commit="1" * 40,
        executable_fingerprint="d" * 64,
    )["accepted"] is False
    changed_command = json.loads(json.dumps(record))
    changed_command["command_contract"][4] = "--skip-framework"
    assert store.acceptance(
        changed_command,
        candidate_commit="1" * 40,
        executable_fingerprint=DIGEST_A,
    )["accepted"] is False

    report_path = (
        store.report_root / f"{record['report_sha256']}.json"
    )
    report_path.write_bytes(report_body + b" ")
    assert store.acceptance(
        record,
        candidate_commit="1" * 40,
        executable_fingerprint=DIGEST_A,
    )["accepted"] is False
    report_path.unlink()
    report_path.mkdir()
    assert store.acceptance(
        record,
        candidate_commit="1" * 40,
        executable_fingerprint=DIGEST_A,
    )["accepted"] is False


def test_security_review_nonzero_exit_cannot_be_accepted(
    tmp_path: Path,
) -> None:
    target = tmp_path / "candidate"
    target.mkdir()
    store = evidence.SecurityReviewStore(
        evidence.state_root(tmp_path / "state")
    )
    report_body = json.dumps(
        _launchguardian_report(target),
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    executable_path = str((tmp_path / "launchguardian.exe").resolve())
    command = [
        executable_path,
        "scan",
        "--target",
        str(target.resolve(strict=True)),
        "--framework-mode",
        "--strict-scanners",
        "--output-dir",
        str((tmp_path / "reports").resolve()),
    ]
    record = store.record(
        candidate_commit="1" * 40,
        executable_fingerprint=DIGEST_A,
        executable_path=executable_path,
        executable_sha256=DIGEST_B,
        command_contract=command,
        report_body=report_body,
        expected_target=target,
        elapsed_seconds=1.0,
        process_exit_code=1,
        process_output_sha256=DIGEST_C,
        owner_checkout_unchanged=True,
    )

    acceptance = store.acceptance(
        record,
        candidate_commit="1" * 40,
        executable_fingerprint=DIGEST_A,
    )
    assert acceptance["accepted"] is False
    assert acceptance["workflow_outcome"] == "procedural_failure"
    forged = json.loads(json.dumps(record))
    forged["process_exit_code"] = 0
    forged["acceptance"] = evidence.launchguardian_report_acceptance(
        _launchguardian_report(target),
        expected_target=target,
    )
    assert store.acceptance(
        forged,
        candidate_commit="1" * 40,
        executable_fingerprint=DIGEST_A,
    )["accepted"] is False

    blocked_report = json.dumps(
        _launchguardian_report(
            target,
            launch_status="BLOCKED",
            blocked=True,
        ),
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    blocked_record = store.record(
        candidate_commit="1" * 40,
        executable_fingerprint=DIGEST_A,
        executable_path=executable_path,
        executable_sha256=DIGEST_B,
        command_contract=command,
        report_body=blocked_report,
        expected_target=target,
        elapsed_seconds=1.0,
        process_exit_code=1,
        process_output_sha256=DIGEST_C,
        owner_checkout_unchanged=True,
    )
    blocked_acceptance = store.acceptance(
        blocked_record,
        candidate_commit="1" * 40,
        executable_fingerprint=DIGEST_A,
    )
    assert blocked_acceptance["accepted"] is False
    assert blocked_acceptance["workflow_outcome"] == "technical_blocker"


def test_security_procedural_record_requires_stage_process_consistency(
    tmp_path: Path,
) -> None:
    store = evidence.SecurityReviewStore(
        evidence.state_root(tmp_path / "state")
    )
    with pytest.raises(
        evidence.EvidenceError,
        match="stage contradicts",
    ):
        store.record_procedural_failure(
            candidate_commit="1" * 40,
            executable_fingerprint=DIGEST_A,
            stage="launchguardian_timeout",
            reason="timeout",
            executable_path=str((tmp_path / "launchguardian.exe").resolve()),
            executable_sha256=DIGEST_B,
            process_exit_code=1,
            process_output_sha256=DIGEST_C,
            process_liveness="absent",
            timed_out=False,
            owner_checkout_unchanged=True,
            workflow_binding_sha256=DIGEST_B,
        )

    record = store.record_procedural_failure(
        candidate_commit="1" * 40,
        executable_fingerprint=DIGEST_A,
        stage="launchguardian_unavailable",
        reason="executable missing",
        executable_path=None,
        executable_sha256=None,
        process_exit_code=None,
        process_output_sha256=DIGEST_C,
        process_liveness="not_started",
        timed_out=False,
        owner_checkout_unchanged=True,
        workflow_binding_sha256=DIGEST_B,
    )
    accepted = store.accepted_record(
        str(record["record_key"]),
        executable_fingerprint=DIGEST_A,
        workflow_binding_sha256=DIGEST_B,
    )
    assert accepted["workflow_outcome"] == "procedural_failure"

    contradictory = json.loads(json.dumps(record))
    contradictory["stage"] = "launchguardian_timeout"
    unkeyed = {
        key: value
        for key, value in contradictory.items()
        if key != "record_key"
    }
    contradictory["record_key"] = evidence._digest_bytes(
        evidence._canonical_json(unkeyed)
    )
    refused = store.procedural_failure_acceptance(
        contradictory,
        executable_fingerprint=DIGEST_A,
    )
    assert refused["accepted"] is False
    assert "stage contradicts" in str(refused["reason"])


def test_checked_in_launchguardian_report_satisfies_strict_report_contract() -> None:
    repository = Path(__file__).resolve().parents[3]
    report_path = (
        repository
        / "reports"
        / "launchguardian"
        / "launchguardian-report.json"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert isinstance(report, dict)
    target = report.get("target")
    assert isinstance(target, str)

    acceptance = evidence.launchguardian_report_acceptance(
        report,
        expected_target=target,
    )

    assert acceptance["accepted"] is True
    assert acceptance["launch_status"] == "APPROVED_WITH_DISPOSITIONS"
