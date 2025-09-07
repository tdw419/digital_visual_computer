from __future__ import annotations

import json
from typing import Any, Dict


def write_canonical_json(path: str, obj: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        f.write("\n")


def read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

