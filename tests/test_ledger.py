"""Core ledger correctness tests. Must pass on first run."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from vera_engine.ledger import Ledger


@pytest.fixture
def ledger(tmp_path: Path):
    db = tmp_path / "test.db"
    return Ledger(db_path=str(db))


def test_append_and_verify(ledger: Ledger):
    r1 = ledger.append(
        tenant_id="test",
        event_type="unit_test",
        payload={"value": 42},
        metadata={"source": "pytest"},
    )
    assert r1.sequence == 1
    assert r1.prev_root == "0" * 64

    result = ledger.verify(r1.receipt_id)
    assert result["valid"] is True
    assert result["receipt"]["receipt_id"] == r1.receipt_id


def test_chain_integrity(ledger: Ledger):
    r1 = ledger.append("test", "a", {"n": 1})
    r2 = ledger.append("test", "b", {"n": 2})
    r3 = ledger.append("test", "c", {"n": 3})

    assert r2.prev_root == r1.merkle_root
    assert r3.prev_root == r2.merkle_root
    assert r3.sequence == 3

    for rid in (r1.receipt_id, r2.receipt_id, r3.receipt_id):
        assert ledger.verify(rid)["valid"] is True


def test_metering(ledger: Ledger):
    ledger.append("tenant-a", "evt", {})
    ledger.append("tenant-a", "evt", {})
    ledger.append("tenant-b", "evt", {})

    stats = {s["tenant_id"]: s["receipt_count"] for s in ledger.metering_stats()}
    assert stats["tenant-a"] == 2
    assert stats["tenant-b"] == 1
