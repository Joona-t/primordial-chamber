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
from .chamber_runner import build_two_seat_chamber
from .council_runner import (
    CouncilRunResult,
    CouncilRunner,
    build_review_prompt,
    build_synthesis_prompt,
    parse_final_ranking,
)
from .store import PrimordialStore
from .harness import PrimordialHarness, classify_summary_absence, record_delegation_safely
from .openclaw_adapter import (
    DEFAULT_OPENCLAW_SESSION_KEY,
    OpenClawAgentResult,
    normalize_openclaw_json,
    run_openclaw_agent,
)
from .orchestrator import ChamberOrchestrationResult, CodexChamberOrchestrator
from .seats import (
    SeatResult,
    SeatSpec,
    cli_seat,
    openclaw_seat,
    placeholder_seat,
    run_seat,
    static_seat,
)

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
    "build_two_seat_chamber",
    "CouncilRunResult",
    "CouncilRunner",
    "build_review_prompt",
    "build_synthesis_prompt",
    "parse_final_ranking",
    "PrimordialStore",
    "PrimordialHarness",
    "classify_summary_absence",
    "record_delegation_safely",
    "DEFAULT_OPENCLAW_SESSION_KEY",
    "OpenClawAgentResult",
    "normalize_openclaw_json",
    "run_openclaw_agent",
    "ChamberOrchestrationResult",
    "CodexChamberOrchestrator",
    "SeatResult",
    "SeatSpec",
    "cli_seat",
    "openclaw_seat",
    "placeholder_seat",
    "run_seat",
    "static_seat",
]
