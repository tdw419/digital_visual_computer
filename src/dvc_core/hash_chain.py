from __future__ import annotations

import hashlib
import json
from typing import Dict, Any


ZERO_HASH = "0" * 64


def canonical_json_bytes(obj: Dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def step_hash(step_obj: Dict[str, Any], prev_hash_hex: str) -> str:
    data = canonical_json_bytes(step_obj) + prev_hash_hex.encode("utf-8")
    return hashlib.sha256(data).hexdigest()

