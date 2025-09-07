from __future__ import annotations

import json
from typing import Any

from dvc_core.program import Program


def load_program_json(path: str) -> Program:
    with open(path, "r", encoding="utf-8") as f:
        arr: Any = json.load(f)
    if not isinstance(arr, list):
        raise ValueError("Program JSON must be an array of instruction objects")
    return Program.from_json_array(arr)

