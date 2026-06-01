"""Small deterministic primitives adapted from the Primordial audit.

The package is intentionally dependency-light: typed absence, references,
reversible summaries, chamber records, and a JSONL store.  These helpers are
support code for Hermes systems; they do not mutate prompts or memory by
import side effect.
"""

from .absence import AbsenceState, ForgeNullError, absent
from .refs import Ref, content_ref, file_ref
from .summary import ReversibleSummary
from .chamber import ChamberRecord, ChamberVoice
from .store import PrimordialStore

__all__ = [
    "AbsenceState",
    "ForgeNullError",
    "absent",
    "Ref",
    "content_ref",
    "file_ref",
    "ReversibleSummary",
    "ChamberRecord",
    "ChamberVoice",
    "PrimordialStore",
]
