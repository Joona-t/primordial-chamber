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
    start = sub.add_parser("start", help="Run OpenClaw and leave Codex voice pending")
    start.add_argument("--message", required=True, help="Prompt to send into the chamber")
    start.add_argument("--hermes-session-id", default=None, help="Hermes session id for source refs")
    start.add_argument("--openclaw-session-key", default=DEFAULT_OPENCLAW_SESSION_KEY)
    start.add_argument("--timeout", type=int, default=600)
    start.add_argument("--openclaw-bin", default="openclaw")
    finalize = sub.add_parser("finalize", help="Attach Codex text to a pending chamber")
    finalize.add_argument("--id", required=True, help="Chamber id")
    finalize.add_argument("--codex-text", required=True, help="Codex voice text")
    list_cmd = sub.add_parser("list", help="List chamber records")
    list_cmd.add_argument("--limit", type=int, default=20)
    show = sub.add_parser("show", help="Show one chamber record")
    show.add_argument("--id", default=None, help="Chamber id")
    show.add_argument("--latest", action="store_true", help="Show latest chamber")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    orchestrator = CodexChamberOrchestrator()
    if args.command == "run":
        result = orchestrator.run_two_seat_chamber(
            message=args.message,
            codex_text=args.codex_text,
            hermes_session_id=args.hermes_session_id,
            openclaw_session_key=args.openclaw_session_key,
            timeout_seconds=args.timeout,
            openclaw_bin=args.openclaw_bin,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
        return 0 if result.openclaw.ok else 2
    if args.command == "start":
        result = orchestrator.start_chamber(
            message=args.message,
            hermes_session_id=args.hermes_session_id,
            openclaw_session_key=args.openclaw_session_key,
            timeout_seconds=args.timeout,
            openclaw_bin=args.openclaw_bin,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
        return 0 if result.openclaw.ok else 2
    if args.command == "finalize":
        result = orchestrator.finalize_chamber(
            chamber_id=args.id,
            codex_text=args.codex_text,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "list":
        print(json.dumps(orchestrator.list_chambers(limit=args.limit), ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "show":
        record = orchestrator.show_chamber(chamber_id=args.id, latest=args.latest)
        print(json.dumps(record, ensure_ascii=False, sort_keys=True))
        return 0 if record is not None else 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
