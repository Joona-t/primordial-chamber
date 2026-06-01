#!/usr/bin/env python3
"""Run a Codex-orchestrated two-seat Primordial chamber."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.primordial.openclaw_adapter import DEFAULT_OPENCLAW_SESSION_KEY
from agent.primordial.orchestrator import CodexChamberOrchestrator


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Run one two-seat chamber")
    run.add_argument("--message", required=True, help="Prompt to send into the chamber")
    run.add_argument("--codex-text", default=None, help="Codex voice text to seal into the chamber")
    run.add_argument("--hermes-session-id", default=None, help="Hermes session id for source refs")
    run.add_argument(
        "--openclaw-session-key",
        default=DEFAULT_OPENCLAW_SESSION_KEY,
        help="OpenClaw session key to target",
    )
    run.add_argument("--timeout", type=int, default=600, help="OpenClaw timeout seconds")
    run.add_argument("--openclaw-bin", default="openclaw", help="OpenClaw executable")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "run":
        result = CodexChamberOrchestrator().run_two_seat_chamber(
            message=args.message,
            codex_text=args.codex_text,
            hermes_session_id=args.hermes_session_id,
            openclaw_session_key=args.openclaw_session_key,
            timeout_seconds=args.timeout,
            openclaw_bin=args.openclaw_bin,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
        return 0 if result.openclaw.ok else 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
