"""FastAPI surface for VERA Enterprise Engine."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from . import crypto
from .ledger import ledger

app = FastAPI(
    title="VERA Enterprise Engine",
    description="Deterministic verifiable compute runtime for enterprise compliance and AI auditing.",
    version="0.1.0",
    contact={
        "name": "Even The Odds Foundry",
        "email": "eventheoddsfoundry@gmail.com",
    },
)


class ReceiptRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1, max_length=128)
    event_type: str = Field(..., min_length=1, max_length=64)
    payload: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class ReceiptResponse(BaseModel):
    receipt_id: str
    tenant_id: str
    event_type: str
    sequence: int
    merkle_root: str
    signature: str
    timestamp: float


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "vera-enterprise-engine"}


@app.get("/ready")
def ready() -> Dict[str, str]:
    # Could add DB ping here; for now the ledger init is the readiness gate
    return {"status": "ready"}


@app.get("/v1/public-key")
def public_key() -> Dict[str, str]:
    return {"public_key_pem": crypto.public_key_pem()}


@app.post("/v1/receipts", response_model=ReceiptResponse, status_code=status.HTTP_201_CREATED)
def create_receipt(req: ReceiptRequest) -> ReceiptResponse:
    try:
        receipt = ledger.append(
            tenant_id=req.tenant_id,
            event_type=req.event_type,
            payload=req.payload,
            metadata=req.metadata,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ReceiptResponse(
        receipt_id=receipt.receipt_id,
        tenant_id=receipt.tenant_id,
        event_type=receipt.event_type,
        sequence=receipt.sequence,
        merkle_root=receipt.merkle_root,
        signature=receipt.signature,
        timestamp=receipt.timestamp,
    )


@app.get("/v1/receipts/{receipt_id}")
def get_receipt(receipt_id: str) -> Dict[str, Any]:
    receipt = ledger.get(receipt_id)
    if receipt is None:
        raise HTTPException(status_code=404, detail="receipt not found")
    return receipt.to_dict()


@app.get("/v1/receipts/{receipt_id}/verify")
def verify_receipt(receipt_id: str) -> Dict[str, Any]:
    result = ledger.verify(receipt_id)
    if not result.get("valid"):
        raise HTTPException(status_code=400, detail=result)
    return result


@app.get("/v1/metering")
def metering(tenant_id: Optional[str] = None) -> Dict[str, Any]:
    stats = ledger.metering_stats(tenant_id)
    return {"tenants": stats}


@app.get("/metrics")
def metrics() -> str:
    """Minimal Prometheus text exposition."""
    stats = ledger.metering_stats()
    lines = [
        "# HELP vera_receipts_total Total receipts issued per tenant",
        "# TYPE vera_receipts_total counter",
    ]
    for s in stats:
        lines.append(f'vera_receipts_total{{tenant_id="{s["tenant_id"]}"}} {s["receipt_count"]}')
    return "\n".join(lines) + "\n"
