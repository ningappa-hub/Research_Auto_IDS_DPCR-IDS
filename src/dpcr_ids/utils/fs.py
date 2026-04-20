"""Filesystem helpers."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any
from typing import Iterable


def ensure_dir(path: str | Path) -> Path:
    resolved = Path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def write_json(path: str | Path, payload: Any) -> Path:
    target = Path(path)
    ensure_dir(target.parent)
    serializable = asdict(payload) if hasattr(payload, "__dataclass_fields__") else payload
    target.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
    return target


def write_jsonl(path: str | Path, rows: Iterable[Any]) -> Path:
    target = Path(path)
    ensure_dir(target.parent)
    with target.open("w", encoding="utf-8") as handle:
        for row in rows:
            serializable = asdict(row) if hasattr(row, "__dataclass_fields__") else row
            handle.write(json.dumps(serializable))
            handle.write("\n")
    return target


def append_jsonl(path: str | Path, row: Any) -> Path:
    target = Path(path)
    ensure_dir(target.parent)
    serializable = asdict(row) if hasattr(row, "__dataclass_fields__") else row
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(serializable))
        handle.write("\n")
    return target


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
