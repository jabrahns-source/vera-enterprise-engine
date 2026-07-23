"""Append-only SQLite ledger with Merkle chaining and cryptographic receipts."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from . import crypto
from .config import settings


def _canonical_json(obj: Any) -> bytes:
    """Deterministic JSON serialization."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class Receipt:
    receipt_id: str
    tenant_id: str
    event_type: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: float
    prev_root: str
    merkle_root: str
    signature: str
    sequence: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "tenant_id": self.tenant_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "prev_root": self.prev_root,
            "merkle_root": self.merkle_root,
            "signature": self.signature,
            "sequence": self.sequence,
        }


class Ledger:
    """Thread-safe-ish SQLite append-only store (single-writer recommended)."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = str(db_path or settings.db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS receipts (
                    receipt_id   TEXT PRIMARY KEY,
                    tenant_id    TEXT NOT NULL,
                    event_type   TEXT NOT NULL,
                    payload      TEXT NOT NULL,
                    metadata     TEXT NOT NULL,
                    timestamp    REAL NOT NULL,
                    prev_root    TEXT NOT NULL,
                    merkle_root  TEXT NOT NULL,
                    signature    TEXT NOT NULL,
                    sequence     INTEGER NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_tenant_seq
                    ON receipts(tenant_id, sequence);

                CREATE TABLE IF NOT EXISTS metering (
                    tenant_id    TEXT PRIMARY KEY,
                    receipt_count INTEGER NOT NULL DEFAULT 0,
                    last_updated REAL NOT NULL
                );
                """
            )

    def _latest_root(self, conn: sqlite3.Connection, tenant_id: str) -> tuple[str, int]:
        row = conn.execute(
            "SELECT merkle_root, sequence FROM receipts WHERE tenant_id = ? ORDER BY sequence DESC LIMIT 1",
            (tenant_id,),
        ).fetchone()
        if row is None:
            return ("0" * 64, 0)
        return row["merkle_root"], row["sequence"]

    def append(
        self,
        tenant_id: str,
        event_type: str,
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Receipt:
        """Append a new receipt. Returns the fully signed Receipt."""
        metadata = metadata or {}
        receipt_id = str(uuid.uuid4())
        timestamp = time.time()

        with self._connect() as conn:
            prev_root, prev_seq = self._latest_root(conn, tenant_id)
            sequence = prev_seq + 1

            # Canonical body that will be hashed and signed
            body = {
                "receipt_id": receipt_id,
                "tenant_id": tenant_id,
                "event_type": event_type,
                "payload": payload,
                "metadata": metadata,
                "timestamp": timestamp,
                "prev_root": prev_root,
                "sequence": sequence,
            }
            body_bytes = _canonical_json(body)
            leaf_hash = _sha256(body_bytes)

            # Simple sequential Merkle: H(prev_root || leaf)
            merkle_root = _sha256((prev_root + leaf_hash).encode("utf-8"))

            # Sign the full commitment
            to_sign = _canonical_json({
                **body,
                "merkle_root": merkle_root,
            })
            signature = crypto.sign(to_sign).hex()

            conn.execute(
                """
                INSERT INTO receipts (
                    receipt_id, tenant_id, event_type, payload, metadata,
                    timestamp, prev_root, merkle_root, signature, sequence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt_id,
                    tenant_id,
                    event_type,
                    json.dumps(payload, sort_keys=True),
                    json.dumps(metadata, sort_keys=True),
                    timestamp,
                    prev_root,
                    merkle_root,
                    signature,
                    sequence,
                ),
            )

            # Metering
            if settings.metering_enabled:
                conn.execute(
                    """
                    INSERT INTO metering (tenant_id, receipt_count, last_updated)
                    VALUES (?, 1, ?)
                    ON CONFLICT(tenant_id) DO UPDATE SET
                        receipt_count = receipt_count + 1,
                        last_updated = excluded.last_updated
                    """,
                    (tenant_id, timestamp),
                )

            conn.commit()

        return Receipt(
            receipt_id=receipt_id,
            tenant_id=tenant_id,
            event_type=event_type,
            payload=payload,
            metadata=metadata,
            timestamp=timestamp,
            prev_root=prev_root,
            merkle_root=merkle_root,
            signature=signature,
            sequence=sequence,
        )

    def get(self, receipt_id: str) -> Optional[Receipt]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM receipts WHERE receipt_id = ?", (receipt_id,)
            ).fetchone()
            if row is None:
                return None
            return Receipt(
                receipt_id=row["receipt_id"],
                tenant_id=row["tenant_id"],
                event_type=row["event_type"],
                payload=json.loads(row["payload"]),
                metadata=json.loads(row["metadata"]),
                timestamp=row["timestamp"],
                prev_root=row["prev_root"],
                merkle_root=row["merkle_root"],
                signature=row["signature"],
                sequence=row["sequence"],
            )

    def verify(self, receipt_id: str) -> Dict[str, Any]:
        """Full cryptographic verification of a stored receipt."""
        receipt = self.get(receipt_id)
        if receipt is None:
            return {"valid": False, "reason": "receipt_not_found"}

        body = {
            "receipt_id": receipt.receipt_id,
            "tenant_id": receipt.tenant_id,
            "event_type": receipt.event_type,
            "payload": receipt.payload,
            "metadata": receipt.metadata,
            "timestamp": receipt.timestamp,
            "prev_root": receipt.prev_root,
            "sequence": receipt.sequence,
        }
        body_bytes = _canonical_json(body)
        leaf_hash = _sha256(body_bytes)
        expected_root = _sha256((receipt.prev_root + leaf_hash).encode("utf-8"))

        if expected_root != receipt.merkle_root:
            return {"valid": False, "reason": "merkle_mismatch"}

        to_verify = _canonical_json({**body, "merkle_root": receipt.merkle_root})
        sig_ok = crypto.verify(bytes.fromhex(receipt.signature), to_verify)

        if not sig_ok:
            return {"valid": False, "reason": "signature_invalid"}

        return {
            "valid": True,
            "receipt": receipt.to_dict(),
            "public_key_pem": crypto.public_key_pem(),
        }

    def metering_stats(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if tenant_id:
                rows = conn.execute(
                    "SELECT * FROM metering WHERE tenant_id = ?", (tenant_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM metering").fetchall()
            return [dict(r) for r in rows]


# Singleton for the API layer
ledger = Ledger()
