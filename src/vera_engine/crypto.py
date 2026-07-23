"""Ed25519 signing primitives. Deterministic key material management."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .config import settings


def _load_or_generate_keypair() -> Tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """Load existing keys or generate a fresh pair. Keys are persisted for reproducibility."""
    priv_path = settings.private_key_path
    pub_path = settings.public_key_path

    if priv_path.exists() and pub_path.exists():
        private_key = serialization.load_pem_private_key(
            priv_path.read_bytes(), password=None
        )
        public_key = serialization.load_pem_public_key(pub_path.read_bytes())
        return private_key, public_key  # type: ignore[return-value]

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    pub_path.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return private_key, public_key


_PRIVATE_KEY, _PUBLIC_KEY = _load_or_generate_keypair()


def sign(data: bytes) -> bytes:
    """Produce an Ed25519 signature over the given bytes."""
    return _PRIVATE_KEY.sign(data)


def verify(signature: bytes, data: bytes) -> bool:
    """Verify an Ed25519 signature. Returns True on success."""
    try:
        _PUBLIC_KEY.verify(signature, data)
        return True
    except Exception:
        return False


def public_key_pem() -> str:
    """Return the public key in PEM form for external verifiers."""
    return _PUBLIC_KEY.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
