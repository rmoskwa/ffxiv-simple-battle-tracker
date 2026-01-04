#!/usr/bin/env python3
"""FFXIV Battle Tracker - Main entry point.

Usage:
    python -m src.main --parse /path/to/log.log           # Parse a completed log
    python -m src.main --parse /path/to/log.log --web     # Parse and launch dashboard
"""

import argparse
import sys
from pathlib import Path

from .models.data_models import FightAttempt, ParserState
from .parser.log_parser import LogParser
from .web.server import run_server


def print_attempt_report(attempt: FightAttempt) -> None:
    """Print a formatted report for a fight attempt."""
    print("\n" + "=" * 70)
    print(f"ATTEMPT #{attempt.attempt_number} - {attempt.outcome.value.upper()}")
    print(f"Boss: {attempt.boss_name}")
    print(f"Duration: {attempt.duration_seconds:.1f}s")
    print(f"Start: {attempt.start_time.strftime('%H:%M:%S')}")
    if attempt.end_time:
        print(f"End: {attempt.end_time.strftime('%H:%M:%S')}")
    print("=" * 70)

    # Ability Hits Summary
    print("\n--- ABILITY HITS ---")
    abilities_by_name = attempt.get_abilities_by_name()
    if abilities_by_name:
        print(f"{'Ability':<30} {'Hits':>6} {'Total Damage':>12}")
        print("-" * 50)
        for ability_name, hits in sorted(
            abilities_by_name.items(), key=lambda x: -len(x[1])
        ):
            total_damage = sum(h.damage for h in hits)
            print(f"{ability_name:<30} {len(hits):>6} {total_damage:>12,}")
    else:
        print("  No ability hits recorded")

    # Hits by Player
    print("\n--- HITS BY PLAYER ---")
    hits_by_player = attempt.get_hits_by_player()
    if hits_by_player:
        print(f"{'Player':<25} {'Times Hit':>10} {'Total Damage':>12}")
        print("-" * 50)
        for player_name, hits in sorted(
            hits_by_player.items(), key=lambda x: -len(x[1])
        ):
            total_damage = sum(h.damage for h in hits)
            print(f"{player_name:<25} {len(hits):>10} {total_damage:>12,}")
    else:
        print("  No player hits recorded")

    # Debuffs Applied
    print("\n--- DEBUFFS APPLIED ---")
    if attempt.debuffs_applied:
        debuffs_by_player = attempt.get_debuffs_by_player()
        print(f"{'Player':<25} {'Debuff':<25} {'Count':>6}")
        print("-" * 60)
        for player_name, debuffs in sorted(debuffs_by_player.items()):
            # Group by debuff name
            debuff_counts = {}
            for d in debuffs:
                debuff_counts[d.effect_name] = debuff_counts.get(d.effect_name, 0) + 1
            for debuff_name, count in debuff_counts.items():
                print(f"{player_name:<25} {debuff_name:<25} {count:>6}")
    else:
        print("  No debuffs applied by boss")

    # Deaths
    print("\n--- DEATHS ---")
    if attempt.deaths:
        print(f"{'Time':<12} {'Player':<25} {'Killed By':<25}")
        print("-" * 65)
        for death in attempt.deaths:
            time_str = death.timestamp.strftime("%H:%M:%S")
            killed_by = death.source_name if death.source_name else "(unknown)"
            print(f"{time_str:<12} {death.player_name:<25} {killed_by:<25}")
    else:
        print("  No deaths recorded")

    print()


def print_session_summary(parser: LogParser) -> None:
    """Print a summary of the entire session."""
    session = parser.get_session()

    print("\n" + "=" * 70)
    print("SESSION SUMMARY")
    print("=" * 70)
    print(f"Zone: {session.zone_name}")
    print(f"Boss: {session.boss_name}")
    print(f"Total Attempts: {len(session.attempts)}")
    print(f"Wipes: {session.total_wipes}")
    print(f"Victories: {session.total_victories}")
    print(f"Players: {len(session.players)}")

    if session.players:
        print("\n--- PLAYERS ---")
        for player in session.players.values():
            print(f"  {player.name} ({player.id})")

    # Cross-attempt statistics
    stats = session.get_cross_attempt_stats()

    if stats["deaths_by_player"]:
        print("\n--- DEATHS BY PLAYER (ALL ATTEMPTS) ---")
        for player, count in sorted(
            stats["deaths_by_player"].items(), key=lambda x: -x[1]
        ):
            print(f"  {player}: {count} deaths")

    print("\n" + "=" * 70)


def on_attempt_complete(attempt: FightAttempt) -> None:
    """Callback when an attempt completes."""
    print_attempt_report(attempt)


def on_state_change(state: ParserState) -> None:
    """Callback when parser state changes."""
    print(f"[STATE] {state.value}")


def parse_log(
    filepath: str, verbose: bool = False, web: bool = False, port: int = 8080
) -> None:
    """Parse a complete log file."""
    path = Path(filepath)
    if not path.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    print(f"Parsing log file: {filepath}")

    parser = LogParser()

    if not web:
        parser.set_on_attempt_complete(on_attempt_complete)

    if verbose:
        parser.set_on_state_change(on_state_change)

    parser.parse_file(filepath)

    print(f"Processed {parser.lines_processed:,} lines")

    if web:
        print(f"Launching web dashboard at http://localhost:{port}")
        print("Press Ctrl+C to stop\n")
        run_server(parser, log_file_path=filepath, port=port)
    else:
        print_session_summary(parser)


def main():
    """Main entry point."""
    arg_parser = argparse.ArgumentParser(
        description="FFXIV Battle Tracker - Parse ACT logs for raid analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main --parse Network_12345.log
  python -m src.main --parse Network_12345.log --web
  python -m src.main --parse Network_12345.log --web --port 9000
        """,
    )

    arg_parser.add_argument(
        "--parse", metavar="LOGFILE", required=True, help="Parse a log file"
    )
    arg_parser.add_argument(
        "--port", type=int, default=8080, help="Port for web dashboard (default: 8080)"
    )
    arg_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show verbose output including state changes",
    )
    arg_parser.add_argument(
        "--web",
        action="store_true",
        help="Launch web dashboard after parsing (use Refresh button to reload data)",
    )

    args = arg_parser.parse_args()
    parse_log(args.parse, verbose=args.verbose, web=args.web, port=args.port)


if __name__ == "__main__":
    main()
