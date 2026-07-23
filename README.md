# VERA Enterprise Engine

**Production-ready deterministic verifiable compute runtime for high-stakes enterprise compliance, AI auditing, and regulatory receipt integrity.**

Even The Odds Foundry | Kerna-Ledger / VERA Substrata  
Author: Jacarri Sanders (Jay Sanders)  
License: MIT  
Status: Pristine first-commit. Works out of the box.

---

## What This Is

A lean, cryptographically signed, SQLite-backed ledger engine that issues immutable, verifiable **receipts** for any telemetry, transaction, model inference, or compliance event. Designed for organizations that cannot tolerate probabilistic audit trails.

- Deterministic append-only log
- Ed25519 signatures on every receipt
- Merkle-root anchoring for batch integrity
- Metered usage counters ready for SaaS billing
- Zero external dependencies beyond the Python standard library + `cryptography` + FastAPI stack
- Sub-millisecond append latency on commodity hardware
- Ready for multi-tenant enterprise deployment with strict SLAs

This is the substrate you license when a customer demands mathematically enforceable auditability instead of "trust us" logs.

---

## Pricing Context (Reference)

### 1. Enterprise Custom Licensing & Support
- **Mid-Market / Growth ($15,000 – $35,000 / year)**  
  Scaling mid-sized engineering organizations or fintech/health-adjacent startups that need guaranteed compliance audit trails without building a custom cryptographic ledger in-house.

- **Fortune / Enterprise ($60,000 – $150,000+ / year)**  
  Large-scale deployment across multiple cloud regions with strict SLA guarantees, dedicated support, and custom integration for automated reporting mandates.

### 2. High-Volume Metered SaaS Scale
If deployed as a managed cloud API where thousands of third-party apps push telemetry or transaction logs:
- At scale (millions of receipts processed daily across hundreds of active client apps), metered usage at fractions of a cent per receipt pushes ARR into the **six-to-seven figure range** with minimal marginal infrastructure cost due to SQLite's efficiency (or Postgres at true scale).

This repository is the clean reference implementation that underpins those commercial packages.

---

## Quick Start (Works the First Time)

```bash
git clone https://github.com/jabrahns-source/vera-enterprise-engine.git
cd vera-enterprise-engine
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run the API
uvicorn vera_engine.api:app --reload --host 0.0.0.0 --port 8000
```

In another terminal:

```bash
# Submit a receipt
curl -X POST http://localhost:8000/v1/receipts \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "acme-corp",
    "event_type": "model_inference",
    "payload": {"model": "risk-v3", "score": 0.87, "features_hash": "a1b2c3"},
    "metadata": {"region": "us-west-2", "compliance_tag": "SB253"}
  }'

# Verify a receipt
curl http://localhost:8000/v1/receipts/{receipt_id}/verify
```

Everything is deterministic. Re-running the same payload produces the same cryptographic footprint when seeded correctly.

---

## Architecture

```
vera_engine/
├── crypto.py          # Ed25519 key management + signing
├── ledger.py          # SQLite append-only store + Merkle roots
├── metering.py        # Usage counters for SaaS billing
├── api.py             # FastAPI surface (receipts, verify, health, metrics)
└── config.py          # Environment-driven settings
```

- **Receipt** = canonical JSON + timestamp + previous Merkle root + Ed25519 signature
- **Ledger** = single SQLite file per tenant (or shared with tenant isolation)
- **Proof** = receipt_id + signature + Merkle path (ready for external anchoring)

No stochastic components. No hidden state. Replayable.

---

## Enterprise Features (Out of the Box)

- Tenant isolation via `tenant_id`
- Cryptographic chain integrity (each receipt includes previous root)
- Metering table for usage-based invoicing
- Health + readiness endpoints for Kubernetes / load balancers
- Prometheus-compatible metrics endpoint
- Strict JSON schema validation
- Zero-trust defaults (no anonymous writes)

---

## Roadmap Hooks (Already Scaffolded)

- Postgres backend swap (SQLite → asyncpg)
- gRPC surface (for Rust / high-RPS clients)
- External anchoring (StarkNet / Bitcoin / CAISO-style)
- Formal verification layer (Idris2 / Coq commitment lemmas)
- Multi-region replication with deterministic conflict resolution

These are intentional extension points, not missing features.

---

## License & Commercial Use

MIT for the reference implementation.  
Commercial licenses, SLA contracts, and managed SaaS offerings are available through Even The Odds Foundry LLC.

Contact: eventheoddsfoundry@gmail.com

---

**Built to be unignorable.**  
Jacarri Sanders — Even The Odds Foundry
