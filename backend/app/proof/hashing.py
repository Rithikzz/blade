import hashlib
import json
from typing import Any

def sha256_json(value: Any) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def generate_code_hash(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()
