from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import delegation_contracts as contracts
import delegation_ledger


NOW = "2026-07-27T12:00:00.000Z"


def test_append_persists_canonical_sequence_and_honest_limitations(
    tmp_path: Path,
) -> None:
    ledger = delegation_ledger.RunLedger(tmp_path, "run-1")
    first = ledger.append(
        event_type="delegation_started",
        status="started",
        payload={"objective_digest": "sha256:" + "a" * 64},
        event_id="event-1",
        recorded_at=NOW,
    )
    second = ledger.append(
        event_type="delegation_finished",
        status="completed",
        payload={"duration_ms": 10},
        event_id="event-2",
        recorded_at=NOW,
    )

    assert first["sequence"] == 1
    assert second["sequence"] == 2
    assert second["previous_record_digest"] == first["record_digest"]
    lines = ledger.path.read_text(encoding="utf-8").splitlines()
    assert lines == [
        contracts.canonical_json(json.loads(line)) for line in lines
    ]
    report = ledger.verify()
    assert report["valid"] is True
    assert report["record_count"] == 2
    assert report["authenticity"] == "not_established"
    assert report["suffix_completeness"] == "not_established"
    assert "user-writable" in " ".join(report["limitations"])
    assert "not ruled out" in " ".join(report["limitations"])


def test_tamper_is_reported_and_prevents_append(tmp_path: Path) -> None:
    ledger = delegation_ledger.RunLedger(tmp_path, "run-1")
    ledger.append(
        event_type="delegation_started",
        status="started",
        payload={"attempt": 1},
        event_id="event-1",
        recorded_at=NOW,
    )
    record = json.loads(ledger.path.read_text(encoding="utf-8"))
    record["status"] = "completed"
    ledger.path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    report = ledger.verify()
    assert report["valid"] is False
    assert report["corruption"]["line"] == 1
    assert "record_digest" in report["corruption"]["reason"]
    with pytest.raises(delegation_ledger.LedgerError, match="corrupt"):
        ledger.append(
            event_type="delegation_finished",
            status="completed",
            payload={},
        )
    assert len(ledger.path.read_text(encoding="utf-8").splitlines()) == 1


def test_reordering_and_incomplete_final_line_are_not_positive_results(
    tmp_path: Path,
) -> None:
    ledger = delegation_ledger.RunLedger(tmp_path, "run-1")
    for number in (1, 2):
        ledger.append(
            event_type="event",
            status="recorded",
            payload={"number": number},
            event_id="event-{}".format(number),
            recorded_at=NOW,
        )
    lines = ledger.path.read_bytes().splitlines(keepends=True)
    ledger.path.write_bytes(lines[1] + lines[0])
    assert ledger.verify()["valid"] is False

    ledger.path.write_bytes(lines[0].rstrip(b"\n"))
    report = ledger.verify()
    assert report["valid"] is False
    assert "newline-terminated" in report["corruption"]["reason"]


def test_sensitive_or_oversized_payload_is_rejected_before_file_creation(
    tmp_path: Path,
) -> None:
    ledger = delegation_ledger.RunLedger(tmp_path, "run-1")
    with pytest.raises(contracts.ContractError, match="forbidden"):
        ledger.append(
            event_type="delegation_started",
            status="started",
            payload={"raw_response": "provider body"},
        )
    with pytest.raises(contracts.ContractError, match="byte bound"):
        ledger.append(
            event_type="delegation_started",
            status="started",
            payload={"summary": "x" * 513},
        )
    assert not ledger.path.exists()


@pytest.mark.skipif(os.name not in {"nt", "posix"}, reason="unsupported lock OS")
def test_two_processes_append_with_contiguous_sequences(tmp_path: Path) -> None:
    script = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from delegation_ledger import RunLedger
ledger = RunLedger(Path(sys.argv[2]), "shared-run")
ledger.append(
    event_type="worker_event",
    status="completed",
    payload={"worker": sys.argv[3]},
    event_id="event-" + sys.argv[3],
    recorded_at="2026-07-27T12:00:00.000Z",
)
"""
    scripts = str(Path(delegation_ledger.__file__).resolve().parent)
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", script, scripts, str(tmp_path), worker],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for worker in ("one", "two")
    ]
    failures = []
    for process in processes:
        stdout, stderr = process.communicate(timeout=20)
        if process.returncode != 0:
            failures.append((process.returncode, stdout, stderr))
    assert failures == []

    ledger = delegation_ledger.RunLedger(tmp_path, "shared-run")
    records = ledger.read_records()
    assert [record["sequence"] for record in records] == [1, 2]
    assert {record["payload"]["worker"] for record in records} == {"one", "two"}
    assert ledger.verify()["valid"] is True
