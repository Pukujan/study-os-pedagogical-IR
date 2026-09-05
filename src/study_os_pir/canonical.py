from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value: BaseModel | dict[str, Any]) -> bytes:
    if isinstance(value, BaseModel):
        payload: dict[str, Any] = value.model_dump(mode="json")
    else:
        payload = value
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: BaseModel | dict[str, Any]) -> str:
    return sha256_hex(canonical_json_bytes(value))
