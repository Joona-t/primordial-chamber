"""Append-only JSONL store for primordial records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from hermes_constants import get_hermes_home

from .absence import validate_record


class PrimordialStore:
    """Small append-only JSONL store.

    The default path is profile-aware via ``get_hermes_home()``:
    ``$HERMES_HOME/primordial/records.jsonl``.
    """

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else get_hermes_home() / "primordial" / "records.jsonl"

    def append(self, record_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not record_type.strip():
            raise ValueError("record_type is required")
        payload_dict = validate_record(dict(payload))
        record = {"type": record_type, "payload": payload_dict}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        return record

    def iter_records(self, *, record_type: str | None = None) -> Iterable[dict[str, Any]]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                raw = line.strip()
                if not raw:
                    continue
                record = json.loads(raw)
                if record_type is None or record.get("type") == record_type:
                    yield record

    def list_records(self, *, record_type: str | None = None) -> list[dict[str, Any]]:
        return list(self.iter_records(record_type=record_type))
