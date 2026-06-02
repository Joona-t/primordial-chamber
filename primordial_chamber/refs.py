"""Stable reference helpers for evidence and artifacts."""

from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Ref:
    """A compact stable reference to content or a local file."""

    id: str
    kind: str
    uri: str
    sha256: str | None = None
    bytes: int | None = None
    mime: str | None = None
    label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


def _digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_ref(content: str | bytes, *, kind: str = "content", label: str | None = None) -> Ref:
    """Build a deterministic ref for inline content."""

    data = content.encode("utf-8") if isinstance(content, str) else bytes(content)
    digest = _digest_bytes(data)
    return Ref(
        id=f"{kind}:sha256:{digest[:16]}",
        kind=kind,
        uri=f"urn:sha256:{digest}",
        sha256=digest,
        bytes=len(data),
        mime="text/plain; charset=utf-8" if isinstance(content, str) else None,
        label=label,
    )


def file_ref(path: str | Path, *, label: str | None = None) -> Ref:
    """Build a deterministic ref for a local file by hashing its bytes."""

    p = Path(path).expanduser().resolve()
    data = p.read_bytes()
    digest = _digest_bytes(data)
    mime, _ = mimetypes.guess_type(str(p))
    return Ref(
        id=f"file:sha256:{digest[:16]}",
        kind="file",
        uri=str(p),
        sha256=digest,
        bytes=len(data),
        mime=mime,
        label=label or p.name,
    )
