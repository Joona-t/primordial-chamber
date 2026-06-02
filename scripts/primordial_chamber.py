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
from agent.primordial.council_runner import CouncilRunner
from agent.primordial.harness import PrimordialHarness
from agent.primordial.seats import openclaw_seat, placeholder_seat, static_seat


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
    council = sub.add_parser("council", help="Run or inspect staged council chambers")
    council_sub = council.add_subparsers(dest="council_command", required=True)
    council_run = council_sub.add_parser("run", help="Run a staged council chamber")
    council_run.add_argument("--message", required=True, help="Prompt to send into the council")
    council_run.add_argument("--codex-text", default=None, help="Static Codex/Hermes seat text")
    council_run.add_argument("--chairman-text", default=None, help="Static chairman synthesis text")
    council_run.add_argument("--include-openclaw", action="store_true", help="Include OpenClaw as a live CLI seat")
    council_run.add_argument("--openclaw-session-key", default=DEFAULT_OPENCLAW_SESSION_KEY)
    council_run.add_argument("--timeout", type=int, default=600)
    council_run.add_argument("--openclaw-bin", default="openclaw")
    council_show = council_sub.add_parser("show", help="Show a staged council chamber")
    council_show.add_argument("--id", default=None, help="Council chamber id")
    council_show.add_argument("--latest", action="store_true", help="Show latest council chamber")
    council_show.add_argument("--compact", action="store_true", help="Show compact summary")
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
    if args.command == "council":
        harness = PrimordialHarness()
        if args.council_command == "run":
            seats = []
            chairman_seat = None
            chairman_seat_id = "codex"
            if args.codex_text:
                seats.append(static_seat("codex", args.codex_text, label="Codex/Hermes"))
            if args.include_openclaw:
                seats.append(
                    openclaw_seat(
                        session_key=args.openclaw_session_key,
                        timeout_seconds=args.timeout,
                        openclaw_bin=args.openclaw_bin,
                    )
                )
            if args.chairman_text:
                chairman_seat_id = "chairman"
                chairman_seat = static_seat("chairman", args.chairman_text, label="Chairman")
            if not seats:
                seats.append(placeholder_seat("codex", label="Codex/Hermes"))
            resolved_chairman_id = (
                chairman_seat_id
                if chairman_seat is not None or any(s.seat_id == chairman_seat_id for s in seats)
                else seats[0].seat_id
            )
            runner = CouncilRunner(
                seats,
                chairman_seat_id=resolved_chairman_id,
                chairman_seat=chairman_seat,
            )
            result = runner.run(args.message)
            record = harness.record_council_chamber(result.record)
            print(json.dumps(record, ensure_ascii=False, sort_keys=True))
            return 0 if record["payload"]["status"] == "sealed" else 2
        if args.council_command == "show":
            if args.id:
                record = harness.store.find_by_id("council_chamber_record", args.id)
            else:
                records = harness.store.list_records(record_type="council_chamber_record")
                record = records[-1] if records and args.latest else None
            if args.compact and record:
                payload = record.get("payload", {})
                stages = payload.get("stages", {}) if isinstance(payload, dict) else {}
                record = {
                    "type": record.get("type"),
                    "id": payload.get("id"),
                    "status": payload.get("status"),
                    "question": payload.get("question"),
                    "stage1_count": len(stages.get("stage1_first_opinions") or []),
                    "stage2_count": len(stages.get("stage2_peer_reviews") or []),
                    "chairman_seat_id": (stages.get("stage3_chairman_synthesis") or {}).get("chairman_seat_id"),
                }
            print(json.dumps(record, ensure_ascii=False, sort_keys=True))
            return 0 if record is not None else 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
