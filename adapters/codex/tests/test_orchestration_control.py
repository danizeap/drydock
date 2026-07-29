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

import orchestration_control as control
import orchestration_evidence as evidence
import orchestrator


OBJECTIVE = hashlib.sha256(b"objective").hexdigest()
OBJECTIVE_ID = "01" * 16
OWNER_ACTION = hashlib.sha256(b"owner action").hexdigest()
TASK_ID = "task-123"
NOW = 1_000.0
PLAN_BODY = b"# Canonical plan\n"
PLAN_SHA256 = hashlib.sha256(PLAN_BODY).hexdigest()


def _authority(
    repo: Path,
    *,
    owner_action: str = OWNER_ACTION,
    actions: list[str] | None = None,
    paths: list[str] | None = None,
    push: dict[str, str] | None = None,
    objective_digest: str = OBJECTIVE,
    objective_id: str = OBJECTIVE_ID,
    circuit_limits: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "allowed_actions": actions
        or ["mutate", "peer", "proof", "security_review"],
        "allowed_paths": paths or ["docs/guide.md", "plan.md"],
        "circuit_limits": circuit_limits or {
            "elapsed_seconds": control.DEFAULT_OBJECTIVE_ELAPSED_LIMIT,
            "input_bytes": control.DEFAULT_OBJECTIVE_INPUT_LIMIT,
            "phase_entries": control.DEFAULT_OBJECTIVE_PHASE_ENTRY_LIMIT,
            "procedural_failures": control.DEFAULT_PROCEDURAL_FAILURE_LIMIT,
            "provider_usd": control.DEFAULT_OBJECTIVE_PROVIDER_USD_LIMIT,
        },
        "expires_at": NOW + 600,
        "issued_at": NOW - 10,
        "limits": {
            "elapsed_seconds": 1_800,
            "input_bytes": 65_536,
            "peer_rounds": 2,
            "provider_usd": 3.0,
        },
        "objective_digest": objective_digest,
        "objective_id": objective_id,
        "owner_action_digest": owner_action,
        "predecessor_objective_id": None,
        "push": push,
        "repository_root": str(repo.resolve(strict=True)),
        "schema_version": control.SCHEMA_VERSION,
        "task_id": TASK_ID,
    }


def _plan(
    *,
    revision: int = 1,
    supersedes: str | None = None,
    summary: str = "Update the operator guide.",
    actions: list[str] | None = None,
    paths: list[str] | None = None,
    phases: list[str] | None = None,
    push: dict[str, str] | None = None,
    objective_digest: str = OBJECTIVE,
    objective_id: str = OBJECTIVE_ID,
) -> dict[str, object]:
    return {
        "mode": "FULL",
        "objective_digest": objective_digest,
        "objective_id": objective_id,
        "phases": phases
        or [
            "preflight",
            "plan_peer",
            "mutation",
            "proof",
            "security_review",
            "complete",
        ],
        "primary_skill": "drydock-orchestrate",
        "push": push,
        "required_actions": actions
        or ["mutate", "peer", "proof", "security_review"],
        "required_paths": paths or ["docs/guide.md", "plan.md"],
        "resource_request": {
            "elapsed_seconds": 900,
            "input_bytes": 32_768,
            "peer_rounds": 2,
            "provider_usd": 1.5,
        },
        "revision": revision,
        "schema_version": control.SCHEMA_VERSION,
        "source_plan_path": "plan.md",
        "source_plan_sha256": PLAN_SHA256,
        "summary": summary,
        "supersedes": supersedes,
    }


def _store(tmp_path: Path) -> tuple[Path, control.WorkflowStore]:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "plan.md").write_bytes(PLAN_BODY)
    state = tmp_path / "state"
    state.mkdir()
    return repo, control.WorkflowStore(state, OBJECTIVE_ID)


def _admit_consume(
    store: control.WorkflowStore,
    phase: str,
    *,
    body: bytes,
    now: float,
    candidate: str | None = None,
) -> tuple[str, str]:
    digest = hashlib.sha256(body).hexdigest()
    admission = store.admit(
        phase,
        input_digest=digest,
        input_bytes=len(body),
        candidate_digest=candidate,
        now=now,
    )
    admission_id = str(admission["admission_id"])
    store.consume_admission(
        phase,
        admission_id=admission_id,
        input_digest=digest,
        candidate_digest=candidate,
        now=now + 0.1,
    )
    return admission_id, digest


def _security_evidence_digest(
    store: control.WorkflowStore,
    tmp_path: Path,
    *,
    candidate: str,
    blocked: bool = False,
    process_exit_code: int = 0,
) -> str:
    target = tmp_path / "security-target"
    target.mkdir(exist_ok=True)
    executable = (tmp_path / "launchguardian.exe").resolve()
    output = (tmp_path / "security-output").resolve()
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
    if blocked:
        finding = {
            "source": "semgrep",
            "severity": "high",
            "status": "open",
            "related_gate": "Gate 3",
            "blocks_launch": True,
        }
        findings.append(finding)
        blocking_findings.append(finding)
        scanner_counts["semgrep"] = 1
        counts_by_severity["high"] = 1
        counts_by_scanner["semgrep"] = 1
        counts_by_status["open"] = 1
        counts_by_gate["Gate 3"] = 1
    scanner_blocking_counts = dict(scanner_counts)
    report = {
        "schema_name": "launchguardian.report",
        "schema_version": "0.2.0",
        "generated_at": "2026-07-30T00:00:00Z",
        "launchguardian_version": "0.2.0",
        "target": str(target.resolve(strict=True)),
        "mode": "framework",
        "validation_mode": "framework",
        "scan_mode": "local",
        "lgf_validation_skipped": False,
        "strict_scanners": True,
        "launch_status": "BLOCKED" if blocked else "APPROVED",
        "lgf_config_valid": True,
        "lgf_validation_status": "valid",
        "scanner_availability": {
            name: "ran"
            for name in evidence.EXPECTED_LAUNCHGUARDIAN_SCANNERS
        },
        "scanner_counts": scanner_counts,
        "scanner_blocking_counts": scanner_blocking_counts,
        "counts_by_severity": counts_by_severity,
        "counts_by_scanner": counts_by_scanner,
        "counts_by_status": counts_by_status,
        "counts_by_gate": counts_by_gate,
        "blocking_findings": blocking_findings,
        "launchguardian_config": {},
        "blocked": blocked,
        "findings": findings,
    }
    record = evidence.SecurityReviewStore(store.root).record(
        candidate_commit="1" * 40,
        executable_fingerprint=candidate,
        executable_path=str(executable),
        executable_sha256=hashlib.sha256(b"launchguardian").hexdigest(),
        command_contract=[
            str(executable),
            "scan",
            "--target",
            str(target.resolve(strict=True)),
            "--framework-mode",
            "--strict-scanners",
            "--output-dir",
            str(output),
        ],
        report_body=json.dumps(
            report,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8"),
        expected_target=target,
        elapsed_seconds=1.0,
        process_exit_code=process_exit_code,
        process_output_sha256=hashlib.sha256(b"output").hexdigest(),
        owner_checkout_unchanged=True,
        workflow_binding_sha256=control.canonical_digest(
            store.read()["admission"]
        ),
    )
    return str(record["record_key"])


def test_preflight_rejects_scope_push_and_task_mismatches(
    tmp_path: Path,
) -> None:
    repo, _ = _store(tmp_path)
    checked = control.preflight(
        _authority(repo), _plan(), expected_task_id=TASK_ID, now=NOW
    )
    assert checked["plan"]["summary"] == "Update the operator guide."
    assert checked["authority_digest"] != checked["authority_scope_digest"]

    with pytest.raises(control.ControlError, match="paths are outside"):
        control.preflight(
            _authority(repo),
            _plan(paths=["plan.md", "src/other.py"]),
            expected_task_id=TASK_ID,
            now=NOW,
        )
    with pytest.raises(control.ControlError, match="task ID"):
        control.preflight(
            _authority(repo),
            _plan(),
            expected_task_id="different-task",
            now=NOW,
        )

    authorized_push = {"branch": "codex/test", "remote": "origin"}
    authority = _authority(
        repo,
        actions=["push"],
        push=authorized_push,
    )
    plan = _plan(
        actions=["push"],
        phases=["preflight", "push", "complete"],
        push={"branch": "codex/other", "remote": "origin"},
    )
    with pytest.raises(control.ControlError, match="destination differs"):
        control.preflight(
            authority, plan, expected_task_id=TASK_ID, now=NOW
        )


def test_one_current_plan_recovers_and_preserves_superseded_plan(
    tmp_path: Path,
) -> None:
    repo, store = _store(tmp_path)
    authority = _authority(repo)
    first = store.start(
        authority, _plan(), expected_task_id=TASK_ID, now=NOW
    )
    recovered = store.start(
        authority, _plan(), expected_task_id=TASK_ID, now=NOW + 1
    )
    assert first["recovered"] is False
    assert recovered["recovered"] is True

    first_digest = str(first["current_plan_digest"])
    second_plan = _plan(
        revision=2,
        supersedes=first_digest,
        summary="Update only the exact operator-guide paragraph.",
    )
    revision_authority = _authority(
        repo,
        owner_action=hashlib.sha256(b"revision action").hexdigest(),
    )
    second = store.revise(
        revision_authority,
        second_plan,
        expected_task_id=TASK_ID,
        now=NOW + 2,
    )
    assert second["current_plan"]["revision"] == 2
    assert second["history"] == [
        {
            "digest": first_digest,
            "revision": 1,
            "state": "superseded",
            "superseded_at": NOW + 2,
        }
    ]
    assert (store.plan_root / f"{first_digest}.json").is_file()

    stale = _plan(
        revision=3,
        supersedes=first_digest,
        summary="A stale competing plan.",
    )
    with pytest.raises(control.ControlError, match="exact current digest"):
        store.revise(
            _authority(
                repo,
                owner_action=hashlib.sha256(b"stale action").hexdigest(),
            ),
            stale,
            expected_task_id=TASK_ID,
            now=NOW + 3,
        )


def test_phase_admission_enforces_order_and_exact_token(
    tmp_path: Path,
) -> None:
    repo, store = _store(tmp_path)
    record = store.start(
        _authority(repo), _plan(), expected_task_id=TASK_ID, now=NOW
    )
    assert record["current_phase"] == "plan_peer"
    digest = hashlib.sha256(b"phase input").hexdigest()
    with pytest.raises(control.ControlError, match="expects plan_peer"):
        store.admit(
            "mutation", input_digest=digest, input_bytes=11, now=NOW + 1
        )

    admission = store.admit(
        "plan_peer", input_digest=digest, input_bytes=11, now=NOW + 2
    )
    with pytest.raises(control.ControlError, match="does not match"):
        store.finish(
            "plan_peer",
            admission_id="wrong",
            outcome="passed",
            evidence_digest=digest,
            now=NOW + 3,
        )
    store.consume_admission(
        "plan_peer",
        admission_id=str(admission["admission_id"]),
        input_digest=digest,
        now=NOW + 2.5,
    )
    peer = store.finish(
        "plan_peer",
        admission_id=str(admission["admission_id"]),
        outcome="passed",
        evidence_digest=digest,
        provider_usd=0.2,
        now=NOW + 3,
    )
    assert peer["current_phase"] == "mutation"
    mutation = store.admit(
        "mutation", input_digest=digest, input_bytes=11, now=NOW + 4
    )
    store.consume_admission(
        "mutation",
        admission_id=str(mutation["admission_id"]),
        input_digest=digest,
        now=NOW + 4.5,
    )
    candidate = hashlib.sha256(b"candidate").hexdigest()
    mutated = store.finish(
        "mutation",
        admission_id=str(mutation["admission_id"]),
        outcome="passed",
        evidence_digest=digest,
        candidate_digest=candidate,
        provider_usd=0.0,
        now=NOW + 5,
    )
    assert mutated["status"] == "active"
    assert mutated["current_phase"] == "proof"
    proof_id, proof_digest = _admit_consume(
        store,
        "proof",
        body=b"proof",
        now=NOW + 6,
        candidate=candidate,
    )
    proved = store.finish(
        "proof",
        admission_id=proof_id,
        outcome="passed",
        evidence_digest=proof_digest,
        candidate_digest=candidate,
        provider_usd=0.0,
        now=NOW + 7,
    )
    assert proved["current_phase"] == "security_review"
    security_id, security_digest = _admit_consume(
        store,
        "security_review",
        body=b"security",
        now=NOW + 8,
        candidate=candidate,
    )
    with pytest.raises(
        control.ControlError,
        match="lacks accepted candidate-bound LaunchGuardian evidence",
    ):
        store.finish(
            "security_review",
            admission_id=security_id,
            outcome="passed",
            evidence_digest=security_digest,
            candidate_digest=candidate,
            provider_usd=0.0,
            now=NOW + 9,
        )
    security_evidence = _security_evidence_digest(
        store,
        tmp_path,
        candidate=candidate,
    )
    completed = store.finish(
        "security_review",
        admission_id=security_id,
        outcome="passed",
        evidence_digest=security_evidence,
        candidate_digest=candidate,
        provider_usd=0.0,
        now=NOW + 10,
    )
    assert completed["status"] == "complete"
    assert completed["circuit"]["worker_started"] is True
    assert completed["candidate_digest"] == candidate


def test_source_plan_drift_refuses_next_executor_admission(
    tmp_path: Path,
) -> None:
    repo, store = _store(tmp_path)
    store.start(
        _authority(repo), _plan(), expected_task_id=TASK_ID, now=NOW
    )
    (repo / "plan.md").write_text(
        "# A different plan\n", encoding="utf-8"
    )
    digest = hashlib.sha256(b"phase input").hexdigest()
    with pytest.raises(control.ControlError, match="stale relative"):
        store.admit(
            "plan_peer", input_digest=digest, input_bytes=11, now=NOW + 1
        )
    record = store.read()
    assert record["current_phase"] == "plan_peer"
    assert record["admission"] is None


def test_owner_action_is_single_use_and_objective_id_is_not_reminted(
    tmp_path: Path,
) -> None:
    repo, store = _store(tmp_path)
    first = store.start(
        _authority(repo), _plan(), expected_task_id=TASK_ID, now=NOW
    )
    revision = _plan(
        revision=2,
        supersedes=str(first["current_plan_digest"]),
        summary="Same objective, renamed plan prose.",
    )
    with pytest.raises(control.ControlError, match="already consumed"):
        store.revise(
            _authority(repo),
            revision,
            expected_task_id=TASK_ID,
            now=NOW + 1,
        )

    changed_digest = hashlib.sha256(b"renamed objective prose").hexdigest()
    with pytest.raises(control.ControlError, match="already has workflow history"):
        store.start(
            _authority(repo, objective_digest=changed_digest),
            _plan(objective_digest=changed_digest),
            expected_task_id=TASK_ID,
            now=NOW + 2,
        )
    assert store.path.name == f"{OBJECTIVE_ID}.json"


def test_crash_after_owner_action_consume_requires_fresh_owner_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, store = _store(tmp_path)
    original = control._atomic_json

    def fail_workflow_commit(path: Path, value: object) -> None:
        if path == store.path:
            raise control.EvidenceError("simulated workflow commit crash")
        original(path, value)

    monkeypatch.setattr(control, "_atomic_json", fail_workflow_commit)
    with pytest.raises(control.EvidenceError, match="simulated"):
        store.start(
            _authority(repo), _plan(), expected_task_id=TASK_ID, now=NOW
        )
    assert not store.path.exists()

    monkeypatch.setattr(control, "_atomic_json", original)
    with pytest.raises(control.ControlError, match="already consumed"):
        store.start(
            _authority(repo), _plan(), expected_task_id=TASK_ID, now=NOW + 1
        )
    fresh = _authority(
        repo,
        owner_action=hashlib.sha256(b"fresh action after crash").hexdigest(),
    )
    result = store.start(
        fresh, _plan(), expected_task_id=TASK_ID, now=NOW + 2
    )
    assert result["status"] == "active"


def test_admission_is_consumed_once_and_burned_before_executor(
    tmp_path: Path,
) -> None:
    repo, store = _store(tmp_path)
    store.start(
        _authority(repo), _plan(), expected_task_id=TASK_ID, now=NOW
    )
    body = b"peer input"
    digest = hashlib.sha256(body).hexdigest()
    admission = store.admit(
        "plan_peer",
        input_digest=digest,
        input_bytes=len(body),
        now=NOW + 1,
    )
    admission_id = str(admission["admission_id"])
    consumed = store.consume_admission(
        "plan_peer",
        admission_id=admission_id,
        input_digest=digest,
        now=NOW + 1.1,
    )
    assert consumed["state"] == "consumed"
    with pytest.raises(control.ControlError, match="consumed"):
        store.consume_admission(
            "plan_peer",
            admission_id=admission_id,
            input_digest=digest,
            now=NOW + 1.2,
        )
    assert store.read()["admission"]["state"] == "consumed"


def test_consumed_admission_crash_burns_token_but_not_owner_action(
    tmp_path: Path,
) -> None:
    repo, store = _store(tmp_path)
    store.start(
        _authority(repo), _plan(), expected_task_id=TASK_ID, now=NOW
    )
    body = b"peer input"
    digest = hashlib.sha256(body).hexdigest()
    admission = store.admit(
        "plan_peer",
        input_digest=digest,
        input_bytes=len(body),
        now=NOW + 1,
    )
    store.consume_admission(
        "plan_peer",
        admission_id=str(admission["admission_id"]),
        input_digest=digest,
        now=NOW + 2,
    )
    recovered = store.recover_expired_admission(
        now=NOW + 1 + control.ADMISSION_TTL_SECONDS
    )
    assert recovered["status"] == "active"
    assert recovered["admission"] is None
    assert (
        recovered["admission_history"][-1]["state"]
        == "burned_after_executor_crash"
    )
    assert (
        recovered["circuit"]["totals"]["unknown_provider_cost_entries"]
        == 1
    )
    replacement = store.admit(
        "plan_peer",
        input_digest=digest,
        input_bytes=len(body),
        now=NOW + 2 + control.ADMISSION_TTL_SECONDS,
    )
    assert replacement["admission_id"] != admission["admission_id"]


def test_disabled_or_invalid_control_feature_fails_closed_before_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, store = _store(tmp_path)
    monkeypatch.setenv(control.WORKFLOW_FEATURE_ENV, "0")
    with pytest.raises(control.ControlError, match="disabled"):
        store.start(
            _authority(repo), _plan(), expected_task_id=TASK_ID, now=NOW
        )
    assert not store.path.exists()

    monkeypatch.setenv(control.WORKFLOW_FEATURE_ENV, "maybe")
    with pytest.raises(control.ControlError, match="exactly 0 or 1"):
        store.start(
            _authority(repo), _plan(), expected_task_id=TASK_ID, now=NOW
        )
    assert not store.path.exists()


def test_post_worker_retry_entries_still_open_the_objective_circuit(
    tmp_path: Path,
) -> None:
    repo, store = _store(tmp_path)
    limits = {
        "elapsed_seconds": 1_000,
        "input_bytes": 1_000,
        "phase_entries": 4,
        "procedural_failures": 4,
        "provider_usd": 10.0,
    }
    actions = [
        "cross_review",
        "mutate",
        "peer",
        "proof",
        "security_review",
    ]
    phases = [
        "preflight",
        "plan_peer",
        "mutation",
        "cross_review",
        "proof",
        "security_review",
        "complete",
    ]
    store.start(
        _authority(
            repo,
            actions=actions,
            circuit_limits=limits,
        ),
        _plan(actions=actions, phases=phases),
        expected_task_id=TASK_ID,
        now=NOW,
    )
    peer_id, peer_digest = _admit_consume(
        store, "plan_peer", body=b"peer", now=NOW + 1
    )
    store.finish(
        "plan_peer",
        admission_id=peer_id,
        outcome="passed",
        evidence_digest=peer_digest,
        provider_usd=0.0,
        now=NOW + 2,
    )
    mutation_id, mutation_digest = _admit_consume(
        store, "mutation", body=b"mutation", now=NOW + 3
    )
    candidate = hashlib.sha256(b"candidate one").hexdigest()
    store.finish(
        "mutation",
        admission_id=mutation_id,
        outcome="passed",
        evidence_digest=mutation_digest,
        candidate_digest=candidate,
        provider_usd=0.0,
        now=NOW + 4,
    )
    review_id, review_digest = _admit_consume(
        store,
        "cross_review",
        body=b"review",
        now=NOW + 5,
        candidate=candidate,
    )
    blocked = store.finish(
        "cross_review",
        admission_id=review_id,
        outcome="technical_blocker",
        evidence_digest=review_digest,
        candidate_digest=candidate,
        provider_usd=0.0,
        now=NOW + 6,
    )
    assert blocked["circuit"]["worker_started"] is True
    assert blocked["circuit"]["totals"]["phase_entries"] == 3
    assert blocked["current_phase"] == "mutation"

    store.resume(
        _authority(
            repo,
            owner_action=hashlib.sha256(b"resume").hexdigest(),
            actions=actions,
            circuit_limits=limits,
        ),
        _plan(actions=actions, phases=phases),
        expected_task_id=TASK_ID,
        now=NOW + 7,
    )
    with pytest.raises(control.ControlError, match="opened before spawn"):
        store.admit(
            "mutation",
            input_digest=mutation_digest,
            input_bytes=8,
            now=NOW + 8,
        )
    reopened = store.read()
    assert reopened["circuit"]["open"] is True
    assert (
        reopened["circuit"]["opening_snapshot"]["reason"]
        == "objective_phase_entries_limit"
    )


def test_rejection_invalidates_candidate_and_every_downstream_gate(
    tmp_path: Path,
) -> None:
    repo, store = _store(tmp_path)
    actions = [
        "cross_review",
        "mutate",
        "peer",
        "proof",
        "security_review",
    ]
    phases = [
        "preflight",
        "plan_peer",
        "mutation",
        "cross_review",
        "proof",
        "security_review",
        "complete",
    ]
    store.start(
        _authority(repo, actions=actions),
        _plan(actions=actions, phases=phases),
        expected_task_id=TASK_ID,
        now=NOW,
    )
    peer_id, peer_digest = _admit_consume(
        store, "plan_peer", body=b"peer", now=NOW + 1
    )
    store.finish(
        "plan_peer",
        admission_id=peer_id,
        outcome="passed",
        evidence_digest=peer_digest,
        provider_usd=0.0,
        now=NOW + 2,
    )
    mutation_id, mutation_digest = _admit_consume(
        store, "mutation", body=b"mutation", now=NOW + 3
    )
    candidate = hashlib.sha256(b"candidate").hexdigest()
    store.finish(
        "mutation",
        admission_id=mutation_id,
        outcome="passed",
        evidence_digest=mutation_digest,
        candidate_digest=candidate,
        provider_usd=0.0,
        now=NOW + 4,
    )
    review_id, review_digest = _admit_consume(
        store,
        "cross_review",
        body=b"review",
        now=NOW + 5,
        candidate=candidate,
    )
    store.finish(
        "cross_review",
        admission_id=review_id,
        outcome="passed",
        evidence_digest=review_digest,
        candidate_digest=candidate,
        provider_usd=0.0,
        now=NOW + 6,
    )
    proof_id, proof_digest = _admit_consume(
        store,
        "proof",
        body=b"proof",
        now=NOW + 7,
        candidate=candidate,
    )
    result = store.finish(
        "proof",
        admission_id=proof_id,
        outcome="technical_blocker",
        evidence_digest=proof_digest,
        candidate_digest=candidate,
        provider_usd=0.0,
        now=NOW + 8,
    )
    assert result["current_phase"] == "mutation"
    assert result["candidate_digest"] is None
    assert [
        item["phase"] for item in result["completed_phases"]
    ] == ["preflight", "plan_peer"]


def test_mutating_plan_requires_proof_before_security_review(
    tmp_path: Path,
) -> None:
    repo, store = _store(tmp_path)
    actions = ["mutate", "proof"]
    phases = ["preflight", "mutation", "proof", "complete"]
    with pytest.raises(
        control.ControlError,
        match="lacks required proof/security actions",
    ):
        store.start(
            _authority(repo, actions=actions),
            _plan(actions=actions, phases=phases),
            expected_task_id=TASK_ID,
            now=NOW,
        )

    actions = ["mutate", "proof", "security_review"]
    phases = [
        "preflight",
        "mutation",
        "security_review",
        "proof",
        "complete",
    ]
    with pytest.raises(
        control.ControlError,
        match="ordered workflow subsequence",
    ):
        store.start(
            _authority(repo, actions=actions),
            _plan(actions=actions, phases=phases),
            expected_task_id=TASK_ID,
            now=NOW,
        )


@pytest.mark.parametrize(
    ("outcome", "expected_phase", "candidate_preserved"),
    [
        ("technical_blocker", "mutation", False),
        ("procedural_failure", "security_review", True),
    ],
)
def test_security_review_failure_has_conservative_resume_boundary(
    tmp_path: Path,
    outcome: str,
    expected_phase: str,
    candidate_preserved: bool,
) -> None:
    repo, store = _store(tmp_path)
    actions = ["mutate", "proof", "security_review"]
    phases = [
        "preflight",
        "mutation",
        "proof",
        "security_review",
        "complete",
    ]
    store.start(
        _authority(repo, actions=actions),
        _plan(actions=actions, phases=phases),
        expected_task_id=TASK_ID,
        now=NOW,
    )
    mutation_id, mutation_digest = _admit_consume(
        store, "mutation", body=b"mutation", now=NOW + 1
    )
    candidate = hashlib.sha256(b"candidate").hexdigest()
    store.finish(
        "mutation",
        admission_id=mutation_id,
        outcome="passed",
        evidence_digest=mutation_digest,
        candidate_digest=candidate,
        provider_usd=0.0,
        now=NOW + 2,
    )
    proof_id, proof_digest = _admit_consume(
        store,
        "proof",
        body=b"proof",
        now=NOW + 3,
        candidate=candidate,
    )
    store.finish(
        "proof",
        admission_id=proof_id,
        outcome="passed",
        evidence_digest=proof_digest,
        candidate_digest=candidate,
        provider_usd=0.0,
        now=NOW + 4,
    )
    security_id, security_digest = _admit_consume(
        store,
        "security_review",
        body=b"security",
        now=NOW + 5,
        candidate=candidate,
    )
    security_evidence = _security_evidence_digest(
        store,
        tmp_path,
        candidate=candidate,
        blocked=outcome == "technical_blocker",
        process_exit_code=1 if outcome == "procedural_failure" else 0,
    )
    blocked = store.finish(
        "security_review",
        admission_id=security_id,
        outcome=outcome,
        evidence_digest=security_evidence,
        candidate_digest=candidate,
        provider_usd=0.0,
        now=NOW + 6,
    )

    assert blocked["status"] == "blocked"
    assert blocked["current_phase"] == expected_phase
    assert blocked["candidate_digest"] == (
        candidate if candidate_preserved else None
    )
    completed = [
        item["phase"] for item in blocked["completed_phases"]
    ]
    if candidate_preserved:
        assert completed == ["preflight", "mutation", "proof"]
    else:
        assert completed == ["preflight"]


def test_security_review_refuses_caller_reclassification_of_keyed_result(
    tmp_path: Path,
) -> None:
    repo, store = _store(tmp_path)
    actions = ["mutate", "proof", "security_review"]
    phases = [
        "preflight",
        "mutation",
        "proof",
        "security_review",
        "complete",
    ]
    store.start(
        _authority(repo, actions=actions),
        _plan(actions=actions, phases=phases),
        expected_task_id=TASK_ID,
        now=NOW,
    )
    mutation_id, mutation_digest = _admit_consume(
        store, "mutation", body=b"mutation", now=NOW + 1
    )
    candidate = hashlib.sha256(b"candidate").hexdigest()
    store.finish(
        "mutation",
        admission_id=mutation_id,
        outcome="passed",
        evidence_digest=mutation_digest,
        candidate_digest=candidate,
        provider_usd=0.0,
        now=NOW + 2,
    )
    proof_id, proof_digest = _admit_consume(
        store,
        "proof",
        body=b"proof",
        now=NOW + 3,
        candidate=candidate,
    )
    store.finish(
        "proof",
        admission_id=proof_id,
        outcome="passed",
        evidence_digest=proof_digest,
        candidate_digest=candidate,
        provider_usd=0.0,
        now=NOW + 4,
    )
    security_id, _ = _admit_consume(
        store,
        "security_review",
        body=b"security",
        now=NOW + 5,
        candidate=candidate,
    )
    technical_evidence = _security_evidence_digest(
        store,
        tmp_path,
        candidate=candidate,
        blocked=True,
    )

    with pytest.raises(
        control.ControlError,
        match="outcome contradicts",
    ):
        store.finish(
            "security_review",
            admission_id=security_id,
            outcome="procedural_failure",
            evidence_digest=technical_evidence,
            candidate_digest=candidate,
            provider_usd=0.0,
            now=NOW + 6,
        )

    record = store.read()
    assert record["current_phase"] == "security_review"
    assert record["candidate_digest"] == candidate
    assert [
        item["phase"] for item in record["completed_phases"]
    ] == ["preflight", "mutation", "proof"]


def test_ambiguous_integration_failure_is_terminal_not_resumable(
    tmp_path: Path,
) -> None:
    repo, store = _store(tmp_path)
    actions = ["integrate", "mutate", "proof", "security_review"]
    phases = [
        "preflight",
        "mutation",
        "proof",
        "security_review",
        "integration",
        "complete",
    ]
    store.start(
        _authority(repo, actions=actions),
        _plan(actions=actions, phases=phases),
        expected_task_id=TASK_ID,
        now=NOW,
    )
    mutation_id, mutation_digest = _admit_consume(
        store, "mutation", body=b"mutation", now=NOW + 1
    )
    candidate = hashlib.sha256(b"candidate").hexdigest()
    store.finish(
        "mutation",
        admission_id=mutation_id,
        outcome="passed",
        evidence_digest=mutation_digest,
        candidate_digest=candidate,
        provider_usd=0.0,
        now=NOW + 2,
    )
    proof_id, proof_digest = _admit_consume(
        store,
        "proof",
        body=b"proof",
        now=NOW + 3,
        candidate=candidate,
    )
    store.finish(
        "proof",
        admission_id=proof_id,
        outcome="passed",
        evidence_digest=proof_digest,
        candidate_digest=candidate,
        provider_usd=0.0,
        now=NOW + 4,
    )
    security_id, _ = _admit_consume(
        store,
        "security_review",
        body=b"security",
        now=NOW + 5,
        candidate=candidate,
    )
    security_evidence = _security_evidence_digest(
        store,
        tmp_path,
        candidate=candidate,
    )
    store.finish(
        "security_review",
        admission_id=security_id,
        outcome="passed",
        evidence_digest=security_evidence,
        candidate_digest=candidate,
        provider_usd=0.0,
        now=NOW + 6,
    )
    integration_id, integration_digest = _admit_consume(
        store,
        "integration",
        body=b"integration",
        now=NOW + 7,
        candidate=candidate,
    )
    terminal = store.finish(
        "integration",
        admission_id=integration_id,
        outcome="technical_blocker",
        evidence_digest=integration_digest,
        candidate_digest=candidate,
        integration_unchanged=False,
        provider_usd=0.0,
        now=NOW + 8,
    )
    assert terminal["status"] == "terminal_blocked"
    assert terminal["resume"] is None


def test_missing_current_plan_body_fails_closed_on_every_read(
    tmp_path: Path,
) -> None:
    repo, store = _store(tmp_path)
    record = store.start(
        _authority(repo), _plan(), expected_task_id=TASK_ID, now=NOW
    )
    plan_body = store.plan_root / f"{record['current_plan_digest']}.json"
    plan_body.unlink()
    with pytest.raises(control.ControlError, match="body is unavailable"):
        store.read()


def test_insufficient_context_is_technical_and_push_stays_unavailable(
    tmp_path: Path,
) -> None:
    repo, store = _store(tmp_path)
    store.start(
        _authority(repo), _plan(), expected_task_id=TASK_ID, now=NOW
    )
    admission_id, digest = _admit_consume(
        store, "plan_peer", body=b"bounded delta", now=NOW + 1
    )
    result = store.finish(
        "plan_peer",
        admission_id=admission_id,
        outcome="insufficient_context",
        evidence_digest=digest,
        now=NOW + 2,
    )
    assert result["status"] == "blocked"
    assert result["resume"]["phase"] == "plan_peer"
    assert result["circuit"]["totals"]["procedural_failures"] == 0

    push_root = tmp_path / "push-state"
    push_root.mkdir()
    push = {"branch": "codex/test", "remote": "origin"}
    push_store = control.WorkflowStore(push_root, "02" * 16)
    push_store.start(
        _authority(
            repo,
            objective_id="02" * 16,
            owner_action=hashlib.sha256(b"push action").hexdigest(),
            actions=["push"],
            paths=["plan.md"],
            push=push,
        ),
        _plan(
            objective_id="02" * 16,
            actions=["push"],
            paths=["plan.md"],
            phases=["preflight", "push", "complete"],
            push=push,
        ),
        expected_task_id=TASK_ID,
        now=NOW,
    )
    with pytest.raises(control.ControlError, match="push is unavailable"):
        push_store.admit(
            "push",
            input_digest=hashlib.sha256(b"push").hexdigest(),
            input_bytes=4,
            now=NOW + 1,
        )


def test_objective_circuit_survives_revision_and_needs_material_change(
    tmp_path: Path,
) -> None:
    repo, store = _store(tmp_path)
    authority = _authority(repo)
    first = store.start(
        authority, _plan(), expected_task_id=TASK_ID, now=NOW
    )
    evidence = hashlib.sha256(b"failure").hexdigest()
    admission = store.admit(
        "plan_peer", input_digest=evidence, input_bytes=7, now=NOW + 1
    )
    store.consume_admission(
        "plan_peer",
        admission_id=str(admission["admission_id"]),
        input_digest=evidence,
        now=NOW + 1.5,
    )
    blocked_once = store.finish(
        "plan_peer",
        admission_id=str(admission["admission_id"]),
        outcome="procedural_failure",
        evidence_digest=evidence,
        now=NOW + 2,
    )
    assert (
        blocked_once["circuit"]["totals"]["procedural_failures"] == 1
    )
    assert blocked_once["circuit"]["open"] is False

    second_plan = _plan(
        revision=2,
        supersedes=str(first["current_plan_digest"]),
        summary="Correct the local preflight input.",
    )
    revision_authority = _authority(
        repo,
        owner_action=hashlib.sha256(b"revision approval").hexdigest(),
    )
    second = store.revise(
        revision_authority,
        second_plan,
        expected_task_id=TASK_ID,
        now=NOW + 3,
    )
    admission = store.admit(
        "plan_peer", input_digest=evidence, input_bytes=7, now=NOW + 4
    )
    store.consume_admission(
        "plan_peer",
        admission_id=str(admission["admission_id"]),
        input_digest=evidence,
        now=NOW + 4.5,
    )
    blocked_twice = store.finish(
        "plan_peer",
        admission_id=str(admission["admission_id"]),
        outcome="procedural_failure",
        evidence_digest=evidence,
        now=NOW + 5,
    )
    assert blocked_twice["circuit"]["open"] is True
    assert (
        blocked_twice["circuit"]["opening_snapshot"]["reason"]
        == "objective_procedural_failures_limit"
    )

    reapproval = _authority(
        repo,
        owner_action=hashlib.sha256(b"new approval").hexdigest(),
    )
    with pytest.raises(control.ControlError, match="changed authority scope"):
        store.resolve_circuit(
            reapproval,
            second_plan,
            expected_task_id=TASK_ID,
            now=NOW + 6,
        )

    third_plan = _plan(
        revision=3,
        supersedes=str(second["current_plan_digest"]),
        summary="Correct the controller contract before retry.",
    )
    resolved = store.resolve_circuit(
        reapproval,
        third_plan,
        expected_task_id=TASK_ID,
        now=NOW + 7,
    )
    assert resolved["status"] == "active"
    assert resolved["circuit"]["open"] is False
    assert resolved["circuit"]["resolution_count"] == 1
    assert resolved["resolution_history"][-1]["changes"]["plan"] is True


def test_second_circuit_open_is_terminal_after_one_resolution(
    tmp_path: Path,
) -> None:
    repo, store = _store(tmp_path)
    limits = {
        "elapsed_seconds": 1_000,
        "input_bytes": 1_000,
        "phase_entries": 8,
        "procedural_failures": 1,
        "provider_usd": 10.0,
    }
    authority = _authority(repo, circuit_limits=limits)
    first = store.start(
        authority, _plan(), expected_task_id=TASK_ID, now=NOW
    )
    first_id, digest = _admit_consume(
        store, "plan_peer", body=b"failure one", now=NOW + 1
    )
    opened = store.finish(
        "plan_peer",
        admission_id=first_id,
        outcome="procedural_failure",
        evidence_digest=digest,
        provider_usd=0.0,
        now=NOW + 2,
    )
    assert opened["circuit"]["open"] is True
    second_plan = _plan(
        revision=2,
        supersedes=str(first["current_plan_digest"]),
        summary="Correct the controller after its first circuit opening.",
    )
    resolved = store.resolve_circuit(
        _authority(
            repo,
            owner_action=hashlib.sha256(b"one resolution").hexdigest(),
            circuit_limits=limits,
        ),
        second_plan,
        expected_task_id=TASK_ID,
        now=NOW + 3,
    )
    assert resolved["circuit"]["resolution_count"] == 1
    second_id, second_digest = _admit_consume(
        store, "plan_peer", body=b"failure two", now=NOW + 4
    )
    terminal = store.finish(
        "plan_peer",
        admission_id=second_id,
        outcome="procedural_failure",
        evidence_digest=second_digest,
        provider_usd=0.0,
        now=NOW + 5,
    )
    assert terminal["status"] == "terminal_blocked"
    assert terminal["resume"] is None
    assert terminal["circuit"]["open"] is True
    with pytest.raises(control.ControlError, match="resolution limit"):
        store.resolve_circuit(
            _authority(
                repo,
                owner_action=hashlib.sha256(b"forbidden second").hexdigest(),
                circuit_limits=limits,
            ),
            second_plan,
            expected_task_id=TASK_ID,
            now=NOW + 6,
        )


@pytest.mark.parametrize(
    ("finish_now", "provider_usd", "reason"),
    [
        (
            NOW + control.DEFAULT_OBJECTIVE_ELAPSED_LIMIT,
            0.0,
            "objective_elapsed_seconds_limit",
        ),
        (
            NOW + 1,
            control.DEFAULT_OBJECTIVE_PROVIDER_USD_LIMIT,
            "objective_provider_usd_limit",
        ),
    ],
)
def test_elapsed_and_spend_open_the_objective_circuit(
    tmp_path: Path,
    finish_now: float,
    provider_usd: float,
    reason: str,
) -> None:
    repo, store = _store(tmp_path)
    store.start(
        _authority(repo), _plan(), expected_task_id=TASK_ID, now=NOW
    )
    evidence = hashlib.sha256(reason.encode("utf-8")).hexdigest()
    admission = store.admit(
        "plan_peer", input_digest=evidence, input_bytes=7, now=NOW
    )
    store.consume_admission(
        "plan_peer",
        admission_id=str(admission["admission_id"]),
        input_digest=evidence,
        now=NOW,
    )
    result = store.finish(
        "plan_peer",
        admission_id=str(admission["admission_id"]),
        outcome="passed",
        evidence_digest=evidence,
        provider_usd=provider_usd,
        now=finish_now,
    )
    assert result["status"] == "blocked"
    assert result["circuit"]["open"] is True
    assert result["circuit"]["opening_snapshot"]["reason"] == reason


def test_delta_review_contains_only_blockers_and_changed_fields() -> None:
    plan = _plan(summary="Rebind the verifier proof.")
    payload = control.compact_delta_review(
        current_plan=plan,
        previous_blockers=["Verifier proof identity is stale."],
        changed_fields={"summary": plan["summary"]},
    )
    assert payload["review_kind"] == "technical_delta"
    assert payload["changed_fields"] == {
        "summary": "Rebind the verifier proof."
    }
    assert payload["unresolved_blockers"] == [
        {
            "id": control.stable_blocker_id(
                "Verifier proof identity is stale."
            ),
            "text": "Verifier proof identity is stale.",
        }
    ]
    assert "required_actions" not in payload["changed_fields"]


def test_workflow_payload_rejects_duplicate_keys() -> None:
    with pytest.raises(control.ControlError, match="duplicate key"):
        control.parse_workflow_payload(
            '{"authority":{},"authority":{},"plan":{}}'
        )


def test_owner_action_consume_is_single_winner_across_real_processes(
    tmp_path: Path,
) -> None:
    state = tmp_path / "concurrent-state"
    state.mkdir()
    action = hashlib.sha256(b"one cross-process action").hexdigest()
    binding = hashlib.sha256(b"one binding").hexdigest()
    module_root = Path(control.__file__).resolve().parent
    script = (
        "import sys,time\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(module_root)!r})\n"
        "from orchestration_control import ControlError,OwnerActionLedger\n"
        "try:\n"
        " OwnerActionLedger(Path(sys.argv[1])).consume("
        "sys.argv[2],objective_id=sys.argv[3],transition='resume',"
        "binding_digest=sys.argv[4],now=time.time())\n"
        " print('consumed')\n"
        "except ControlError:\n"
        " print('refused')\n"
    )
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    argv = [
        sys.executable,
        "-B",
        "-c",
        script,
        str(state),
        action,
        OBJECTIVE_ID,
        binding,
    ]
    first = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
    )
    second = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
    )
    first_output, first_error = first.communicate(timeout=20)
    second_output, second_error = second.communicate(timeout=20)
    assert first.returncode == 0, first_error
    assert second.returncode == 0, second_error
    assert sorted([first_output.strip(), second_output.strip()]) == [
        "consumed",
        "refused",
    ]
    record = json.loads(
        (
            state
            / "owner-actions"
            / f"{action}.json"
        ).read_text(encoding="utf-8")
    )
    assert record["binding_digest"] == binding


def test_atomic_record_replacement_has_no_torn_windows_reader(
    tmp_path: Path,
) -> None:
    record_path = tmp_path / "atomic" / "workflow.json"
    record_path.parent.mkdir()
    record_path.write_text(
        json.dumps({"generation": 0, "payload": "a" * 8192}),
        encoding="utf-8",
    )
    module_root = Path(control.__file__).resolve().parent
    script = (
        "import sys\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(module_root)!r})\n"
        "from orchestration_evidence import _atomic_json\n"
        "path=Path(sys.argv[1])\n"
        "for generation in range(1,201):\n"
        " marker='a' if generation % 2 == 0 else 'b'\n"
        " _atomic_json(path,{'generation':generation,'payload':marker*8192})\n"
    )
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    writer = subprocess.Popen(
        [sys.executable, "-B", "-c", script, str(record_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
    )
    observed = 0
    refused_reads = 0
    while writer.poll() is None:
        try:
            value = control._read_json(record_path)
        except control.EvidenceError:
            refused_reads += 1
            continue
        marker = "a" if int(value["generation"]) % 2 == 0 else "b"
        assert value["payload"] == marker * 8192
        observed += 1
    output, error = writer.communicate(timeout=20)
    assert writer.returncode == 0, output + error
    final = json.loads(record_path.read_text(encoding="utf-8"))
    assert final["generation"] == 200
    assert observed > 0
    assert refused_reads >= 0


def test_workflow_cli_starts_and_reports_only_bounded_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, _ = _store(tmp_path)
    state = tmp_path / "cli-state"
    authority = _authority(repo)
    authority["issued_at"] = time.time() - 10
    authority["expires_at"] = time.time() + 600
    payload = json.dumps(
        {"authority": authority, "plan": _plan()}
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    assert (
        orchestrator.main(
            [
                "workflow-start",
                "--task-id",
                TASK_ID,
                "--state-dir",
                str(state),
            ]
        )
        == 0
    )
    started = json.loads(capsys.readouterr().out)
    assert started["status"] == "active"
    assert started["current_phase"] == "plan_peer"
    assert started["plan_revision"] == 1
    assert "current_plan" not in started
    assert "authority" not in started

    assert (
        orchestrator.main(
                [
                    "workflow-status",
                    "--objective-id",
                    OBJECTIVE_ID,
                "--repo",
                str(repo),
                "--state-dir",
                str(state),
            ]
        )
        == 0
    )
    status = json.loads(capsys.readouterr().out)
    assert status["plan_digest"] == started["plan_digest"]
    assert status["authority_scope_digest"] == started[
        "authority_scope_digest"
    ]


def test_workflow_cli_consumes_digest_bound_out_of_tree_payload_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo, _ = _store(tmp_path)
    state = tmp_path / "file-state"
    payload_root = state / "payloads"
    payload_root.mkdir(parents=True)
    authority = _authority(repo)
    authority["issued_at"] = time.time() - 10
    authority["expires_at"] = time.time() + 600
    payload = json.dumps({"authority": authority, "plan": _plan()}).encode(
        "utf-8"
    )
    payload_path = payload_root / "workflow.json"
    payload_path.write_bytes(payload)
    payload_digest = hashlib.sha256(payload).hexdigest()
    argv = [
        "workflow-start",
        "--task-id",
        TASK_ID,
        "--payload-file",
        str(payload_path),
        "--payload-sha256",
        payload_digest,
        "--state-dir",
        str(state),
    ]
    assert payload.decode("utf-8") not in argv
    assert orchestrator.main(argv) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "active"
    assert not payload_path.exists()

    second_state = tmp_path / "mismatch-state"
    second_payload_root = second_state / "payloads"
    second_payload_root.mkdir(parents=True)
    mismatched = second_payload_root / "workflow.json"
    mismatched.write_bytes(payload)
    assert (
        orchestrator.main(
            [
                "workflow-start",
                "--task-id",
                TASK_ID,
                "--payload-file",
                str(mismatched),
                "--payload-sha256",
                hashlib.sha256(b"different").hexdigest(),
                "--state-dir",
                str(second_state),
            ]
        )
        == 1
    )
    error = json.loads(capsys.readouterr().out)
    assert error["stage"] == "input_error"
    assert "SHA-256 is mismatched" in error["error"]
    assert not mismatched.exists()


def test_payload_transport_rejects_links_and_reaps_only_expired_files(
    tmp_path: Path,
) -> None:
    state = tmp_path / "payload-state"
    payload_root = state / "payloads"
    payload_root.mkdir(parents=True)
    stale = payload_root / "stale.json"
    stale.write_text("{}", encoding="utf-8")
    fresh = payload_root / "fresh.json"
    fresh.write_text("{}", encoding="utf-8")
    now = time.time()
    os.utime(
        stale,
        (
            now - control.PAYLOAD_RETENTION_SECONDS - 1,
            now - control.PAYLOAD_RETENTION_SECONDS - 1,
        ),
    )
    removed = control.reap_stale_workflow_payloads(state, now=now)
    assert removed == ["stale.json"]
    assert not stale.exists()
    assert fresh.exists()

    target = payload_root / "target.json"
    target.write_text("{}", encoding="utf-8")
    link = payload_root / "link.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("this Windows account cannot create a symlink")
    with pytest.raises(control.ControlError, match="regular non-link"):
        control.consume_workflow_payload_file(
            link,
            hashlib.sha256(b"{}").hexdigest(),
            state_directory=state,
        )
    assert link.exists()
    assert target.exists()
