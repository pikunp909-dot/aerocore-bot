import os
import time
import uuid
import hashlib
import base64
import struct
from nacl.signing import SigningKey

PRIVATE_KEY_B64 = os.environ.get("AEROCORE_PRIVATE_KEY", "")

def generate_license(device_id: str, days: int) -> dict:
    if not PRIVATE_KEY_B64:
        raise ValueError("AEROCORE_PRIVATE_KEY not set")

    raw_priv = base64.b64decode(PRIVATE_KEY_B64)
    if len(raw_priv) != 32:
        raise ValueError(f"Private key must be 32 bytes, got {len(raw_priv)}")

    signing_key = SigningKey(raw_priv)

    issued_at = int(time.time() * 1000)
    expires_at = issued_at + (days * 24 * 60 * 60 * 1000)
    license_id = uuid.uuid4()

    device_hash = hashlib.sha256(device_id.encode()).digest()

    payload = (
        b"AERO" +
        struct.pack(">B", 0x01) +
        struct.pack(">q", issued_at) +
        struct.pack(">q", expires_at) +
        license_id.bytes +
        device_hash +
        struct.pack(">i", 0x01) +
        struct.pack(">q", 0)
    )

    signature = signing_key.sign(payload).signature
    blob = payload + signature
    encoded = base64.urlsafe_b64encode(blob).rstrip(b"=").decode()

    return {
        "license": encoded,
        "device": device_id,
        "days": days,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "license_id": str(license_id),
    }
