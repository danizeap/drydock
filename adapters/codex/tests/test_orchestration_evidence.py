from __future__ import annotations

import hashlib
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
        "scope": "full_required_suite",
        "executable_surface_sha256": fingerprint,
    }
    assert evidence.final_suite_acceptance(
        full, executable_fingerprint=fingerprint
    )["accepted"] is True
    full["executable_surface_sha256"] = DIGEST_A
    assert evidence.final_suite_acceptance(
        full, executable_fingerprint=fingerprint
    )["accepted"] is False


def test_fresh_proof_root_selects_explicit_extraction_filter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    commit = _git(repo, "rev-parse", "HEAD")
    observed: list[object] = []
    original = evidence.tarfile.TarFile.extractall

    def recording_extractall(
        bundle: object,
        path: object = ".",
        members: object = None,
        *,
        numeric_owner: bool = False,
        filter: object = None,
    ) -> None:
        observed.append(filter)
        original(
            bundle,
            path,
            members,
            numeric_owner=numeric_owner,
            filter=filter,
        )

    monkeypatch.setattr(
        evidence.tarfile.TarFile, "extractall", recording_extractall
    )
    with evidence.fresh_proof_root(repo, commit) as root:
        assert (root / "app.py").is_file()
    assert observed == ["fully_trusted"]


def test_reusable_proof_is_intermediate_and_exactly_bound() -> None:
    command = [sys.executable, "-m", "pytest", "-q"]
    environment_digest = DIGEST_B
    record = {
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
            "executable_surface_sha256": DIGEST_A,
        },
        command=command,
        environment_sha256=DIGEST_B,
    )
    assert dirty["reusable"] is False
    clean = store.intermediate(
        candidate_state={
            "reuse_eligible": True,
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
    store.record(
        executable_fingerprint=DIGEST_A,
        result=result,
        scope="full_required_suite",
    )
    assert store.final(
        executable_fingerprint=DIGEST_A,
        command=command,
        environment_sha256=DIGEST_B,
    )["accepted"] is True
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
