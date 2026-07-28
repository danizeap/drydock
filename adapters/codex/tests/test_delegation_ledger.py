from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Mapping

import pytest

from adapters.codex.drydock.scripts import delegation_contracts as contracts
from adapters.codex.drydock.scripts import delegation_ledger


NOW = "2026-07-28T12:00:00.000Z"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def append_event(
    ledger: delegation_ledger.RunLedger,
    number: int = 1,
) -> Mapping[str, object]:
    return ledger.append(
        event_type="delegation_event",
        runtime_status="completed",
        payload={"number": number},
        event_id="event-{}".format(number),
        recorded_at=NOW,
    )


def add_torn_tail(ledger: delegation_ledger.RunLedger) -> str:
    append_event(ledger)
    with ledger.path.open("ab") as stream:
        stream.write(
            b'{"schema_version":2,"sequence":2,"event_id":"torn-event'
        )
        stream.flush()
        os.fsync(stream.fileno())
    return contracts.digest_bytes(ledger.path.read_bytes())


def test_append_persists_v2_canonical_sequence_and_honest_limitations(
    tmp_path: Path,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-1")
    first = append_event(target, 1)
    second = append_event(target, 2)

    assert first["schema_version"] == 2
    assert first["sequence"] == 1
    assert second["sequence"] == 2
    assert second["previous_record_digest"] == first["record_digest"]
    lines = target.path.read_text(encoding="utf-8").splitlines()
    assert lines == [
        contracts.canonical_json(contracts.strict_json_loads(line))
        for line in lines
    ]
    report = target.verify()
    assert report["valid"] is True
    assert report["record_count"] == 2
    assert report["authenticity"] == "not_established"
    assert report["suffix_completeness"] == "not_established"
    assert "user-writable" in " ".join(report["limitations"])
    assert "not ruled out" in " ".join(report["limitations"])


def test_read_only_empty_ledger_calls_do_not_mutate_filesystem(
    tmp_path: Path,
) -> None:
    root = tmp_path / "absent"
    target = delegation_ledger.RunLedger(root, "run-1")
    before = list(tmp_path.rglob("*"))

    assert target.verify()["valid"] is True
    assert target.read_records() == []
    assert list(tmp_path.rglob("*")) == before
    assert not target.lock_path.exists()
    assert not target.directory.exists()


def test_payload_is_detached_before_persistence(tmp_path: Path) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-1")
    payload = {"claims": [{"state": "initial"}]}
    target.append(
        event_type="claim_observed",
        runtime_status="completed",
        payload=payload,
        event_id="event-1",
        recorded_at=NOW,
    )
    before = target.path.read_bytes()
    payload["claims"][0]["state"] = "mutated"  # type: ignore[index]
    payload["claims"].append({"state": "outside"})  # type: ignore[union-attr]

    assert target.path.read_bytes() == before
    assert target.read_records()[0]["payload"] == {
        "claims": [{"state": "initial"}]
    }


def test_tamper_and_v1_are_reported_and_prevent_append(tmp_path: Path) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-1")
    append_event(target)
    record = contracts.strict_json_loads(
        target.path.read_text(encoding="utf-8").strip()
    )
    assert isinstance(record, dict)
    record["schema_version"] = 1
    target.path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    report = target.verify()
    assert report["valid"] is False
    assert report["corruption"]["line"] == 1
    assert "v2 required" in report["corruption"]["reason"]
    before = target.path.read_bytes()
    with pytest.raises(delegation_ledger.LedgerError, match="corrupt"):
        append_event(target, 2)
    assert target.path.read_bytes() == before


def test_reordering_and_incomplete_final_line_fail_closed(
    tmp_path: Path,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-1")
    append_event(target, 1)
    append_event(target, 2)
    lines = target.path.read_bytes().splitlines(keepends=True)
    target.path.write_bytes(lines[1] + lines[0])
    assert target.verify()["valid"] is False

    target.path.write_bytes(lines[0].rstrip(b"\n"))
    report = target.verify()
    assert report["valid"] is False
    assert "newline-terminated" in report["corruption"]["reason"]


def test_sensitive_or_oversized_payload_is_rejected_before_ledger_creation(
    tmp_path: Path,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-1")
    with pytest.raises(contracts.ContractError, match="forbidden"):
        target.append(
            event_type="delegation_started",
            runtime_status="started",
            payload={"raw_response": "provider body"},
        )
    with pytest.raises(contracts.ContractError, match="byte bound"):
        target.append(
            event_type="delegation_started",
            runtime_status="started",
            payload={"summary": "x" * 513},
        )
    assert not target.path.exists()


@pytest.mark.skipif(os.name not in {"nt", "posix"}, reason="unsupported lock OS")
def test_two_processes_append_with_contiguous_sequences(tmp_path: Path) -> None:
    script = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from adapters.codex.drydock.scripts.delegation_ledger import RunLedger
target = RunLedger(Path(sys.argv[2]), "shared-run")
target.append(
    event_type="worker_event",
    runtime_status="completed",
    payload={"worker": sys.argv[3]},
    event_id="event-" + sys.argv[3],
    recorded_at="2026-07-28T12:00:00.000Z",
)
"""
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                script,
                str(REPOSITORY_ROOT),
                str(tmp_path),
                worker,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for worker in ("one", "two")
    ]
    failures = []
    for process in processes:
        stdout, stderr = process.communicate(timeout=40)
        if process.returncode != 0:
            failures.append((process.returncode, stdout, stderr))
    assert failures == []

    target = delegation_ledger.RunLedger(tmp_path, "shared-run")
    records = target.read_records()
    assert [record["sequence"] for record in records] == [1, 2]
    assert {record["payload"]["worker"] for record in records} == {"one", "two"}
    assert target.verify()["valid"] is True


@pytest.mark.parametrize(
    ("fault_step", "quarantine"),
    [
        ("pre_intent", False),
        ("post_intent", False),
        ("post_quarantine", True),
        ("post_candidate", False),
        ("post_replace", False),
    ],
)
def test_repair_replays_idempotently_after_every_durable_step(
    tmp_path: Path,
    fault_step: str,
    quarantine: bool,
) -> None:
    target = delegation_ledger.RunLedger(
        tmp_path / fault_step, "run-repair"
    )
    expected_digest = add_torn_tail(target)
    valid_prefix = target.path.read_bytes().split(b"\n", 1)[0] + b"\n"

    with pytest.raises(delegation_ledger.RepairInterrupted):
        target.repair_torn_tail(
            expected_digest=expected_digest,
            quarantine=quarantine,
            _fault_after=fault_step,
        )
    repaired = target.repair_torn_tail(
        expected_digest=expected_digest,
        quarantine=quarantine,
    )
    assert repaired["status"] in {"repaired", "completed_replay"}
    assert target.path.read_bytes() == valid_prefix
    assert target.verify()["valid"] is True

    replay = target.repair_torn_tail(
        expected_digest=expected_digest,
        quarantine=quarantine,
    )
    assert replay["status"] == "completed_replay"
    assert target.path.read_bytes() == valid_prefix
    intents = list(target.intent_directory.glob("*.json"))
    assert len(intents) == 1
    if quarantine:
        quarantines = list(target.quarantine_directory.glob("*.bin"))
        assert len(quarantines) == 1


def test_repair_refuses_stale_digest_without_changing_bytes(tmp_path: Path) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-repair")
    expected_digest = add_torn_tail(target)
    before = target.path.read_bytes()
    stale = "sha256:" + ("0" * 64)

    with pytest.raises(delegation_ledger.LedgerError, match="stale"):
        target.repair_torn_tail(expected_digest=stale)
    assert target.path.read_bytes() == before
    assert expected_digest == contracts.digest_bytes(before)


def test_repair_refuses_newline_semantic_interior_and_ambiguous_tail(
    tmp_path: Path,
) -> None:
    newline_target = delegation_ledger.RunLedger(tmp_path / "newline", "run-1")
    append_event(newline_target)
    with newline_target.path.open("ab") as stream:
        stream.write(b"{}\n")
    newline_digest = contracts.digest_bytes(newline_target.path.read_bytes())
    with pytest.raises(delegation_ledger.LedgerError, match="non-newline"):
        newline_target.repair_torn_tail(expected_digest=newline_digest)

    interior_target = delegation_ledger.RunLedger(tmp_path / "interior", "run-1")
    append_event(interior_target)
    data = bytearray(interior_target.path.read_bytes())
    data[data.index(b"completed")] = ord("x")
    data.extend(b'{"sequence":2,"event_id":"torn')
    interior_target.path.write_bytes(bytes(data))
    interior_digest = contracts.digest_bytes(interior_target.path.read_bytes())
    with pytest.raises(delegation_ledger.LedgerError, match="prefix is corrupt"):
        interior_target.repair_torn_tail(expected_digest=interior_digest)

    ambiguous_target = delegation_ledger.RunLedger(
        tmp_path / "ambiguous", "run-1"
    )
    append_event(ambiguous_target)
    complete = append_event(ambiguous_target, 2)
    assert complete["sequence"] == 2
    ambiguous_target.path.write_bytes(
        ambiguous_target.path.read_bytes().rstrip(b"\n")
    )
    ambiguous_digest = contracts.digest_bytes(
        ambiguous_target.path.read_bytes()
    )
    with pytest.raises(delegation_ledger.LedgerError, match="ambiguous"):
        ambiguous_target.repair_torn_tail(expected_digest=ambiguous_digest)

    semantic_target = delegation_ledger.RunLedger(
        tmp_path / "semantic", "run-1"
    )
    append_event(semantic_target)
    with semantic_target.path.open("ab") as stream:
        stream.write(b'{"sequence":2,"value":NaN')
    semantic_digest = contracts.digest_bytes(semantic_target.path.read_bytes())
    with pytest.raises(delegation_ledger.LedgerError, match="non-finite"):
        semantic_target.repair_torn_tail(expected_digest=semantic_digest)

    sequence_target = delegation_ledger.RunLedger(
        tmp_path / "sequence", "run-1"
    )
    append_event(sequence_target)
    with sequence_target.path.open("ab") as stream:
        stream.write(b'{"sequence":9,"event_id":"torn')
    sequence_digest = contracts.digest_bytes(sequence_target.path.read_bytes())
    with pytest.raises(delegation_ledger.LedgerError, match="not the next"):
        sequence_target.repair_torn_tail(expected_digest=sequence_digest)


def test_malformed_existing_repair_intent_blocks_manual_recovery(
    tmp_path: Path,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-repair")
    expected_digest = add_torn_tail(target)
    target.intent_directory.mkdir(parents=True)
    (target.intent_directory / "bad.json").write_text(
        '{"schema_version":2}\n', encoding="utf-8"
    )
    before = target.path.read_bytes()

    with pytest.raises(delegation_ledger.LedgerError, match="malformed"):
        target.repair_torn_tail(expected_digest=expected_digest)
    assert target.path.read_bytes() == before


def test_v1_repair_intent_is_explicitly_refused(tmp_path: Path) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "run-repair")
    expected_digest = add_torn_tail(target)
    target.intent_directory.mkdir(parents=True)
    (target.intent_directory / "v1.json").write_text(
        '{"schema_version":1}\n', encoding="utf-8"
    )

    with pytest.raises(delegation_ledger.LedgerError, match="malformed"):
        target.repair_torn_tail(expected_digest=expected_digest)


def _prebuilt_ledger_bytes(run_id: str, count: int) -> bytes:
    lines = []
    previous = None
    for sequence in range(1, count + 1):
        event = {
            "schema_version": contracts.SCHEMA_VERSION,
            "sequence": sequence,
            "event_id": "event-{}".format(sequence),
            "run_id": run_id,
            "event_type": "capacity_sample",
            "recorded_at": NOW,
            "delegation_id": None,
            "task_id": None,
            "runtime_status": "completed",
            "payload": {"number": sequence},
            "previous_record_digest": previous,
        }
        event["record_digest"] = contracts.digest_json(event)
        previous = event["record_digest"]
        lines.append(contracts.canonical_json(event).encode("utf-8") + b"\n")
    return b"".join(lines)


def test_prebuilt_capacity_sample_full_verification_fits_lock_budget(
    tmp_path: Path,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "capacity-run")
    target.directory.mkdir(parents=True)
    data = _prebuilt_ledger_bytes(target.run_id, delegation_ledger.MAX_RECORDS)
    assert len(data) <= delegation_ledger.MAX_LEDGER_BYTES
    target.path.write_bytes(data)

    started = time.perf_counter()
    report = target.verify()
    elapsed = time.perf_counter() - started

    assert report["valid"] is True
    assert report["record_count"] == delegation_ledger.MAX_RECORDS
    assert elapsed < delegation_ledger.DEFAULT_LOCK_TIMEOUT_S


def test_sequential_append_timing_is_observational_not_a_correctness_gate(
    tmp_path: Path,
    record_property,
) -> None:
    target = delegation_ledger.RunLedger(tmp_path, "sequential-run")
    started = time.perf_counter()
    for number in range(1, 51):
        append_event(target, number)
    elapsed = time.perf_counter() - started
    record_property("sequential_append_50_seconds", elapsed)

    assert target.verify()["record_count"] == 50
