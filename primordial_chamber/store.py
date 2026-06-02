"""Append-only JSONL store for primordial records."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

from .absence import validate_record


def get_chamber_home() -> Path:
    """Return the standalone chamber data directory."""

    configured = os.environ.get("PRIMORDIAL_CHAMBER_HOME")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".primordial-chamber"


class PrimordialStore:
    """Small append-only JSONL store.

    The default path is ``$PRIMORDIAL_CHAMBER_HOME/records.jsonl`` or
    ``~/.primordial-chamber/records.jsonl``.
    """

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else get_chamber_home() / "records.jsonl"

    def append(self, record_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not record_type.strip():
            raise ValueError("record_type is required")
        payload_dict = validate_record(dict(payload))
        record = {"type": record_type, "payload": payload_dict}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        return record

    def rewrite_records(self, records: list[Mapping[str, Any]]) -> None:
        """Rewrite the JSONL store with already-normalized records."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            for record in records:
                fh.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
        tmp.replace(self.path)

    def update_payload_by_id(
        self,
        record_type: str,
        record_id: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Replace the payload for the newest matching record id."""

        records = self.list_records()
        payload_dict = validate_record(dict(payload))
        replacement = {"type": record_type, "payload": payload_dict}
        for i in range(len(records) - 1, -1, -1):
            record = records[i]
            if record.get("type") != record_type:
                continue
            existing = record.get("payload")
            if isinstance(existing, dict) and existing.get("id") == record_id:
                records[i] = replacement
                self.rewrite_records(records)
                return replacement
        raise KeyError(f"{record_type} record not found: {record_id}")

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

    def find_by_id(self, record_type: str, record_id: str) -> dict[str, Any] | None:
        for record in reversed(self.list_records(record_type=record_type)):
            payload = record.get("payload")
            if isinstance(payload, dict) and payload.get("id") == record_id:
                return record
        return None
