"""Flask web server for FFXIV Battle Tracker dashboard."""

import json
import os
import queue
import threading
from pathlib import Path
from typing import Generator, List, Optional

from flask import Flask, Response, jsonify, render_template, request

from ..models.data_models import FightAttempt, ParserState, RaidSession
from ..parser.log_parser import LogParser


# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"


class EventManager:
    """Manages Server-Sent Events subscriptions and broadcasting."""

    def __init__(self):
        """Initialize the event manager."""
        self._subscribers: List[queue.Queue] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue:
        """Subscribe to events and return a queue for receiving them."""
        q = queue.Queue(maxsize=100)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        """Unsubscribe from events."""
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def broadcast(self, event_type: str, data: dict) -> None:
        """Broadcast an event to all subscribers."""
        message = {
            "type": event_type,
            "data": data,
        }
        with self._lock:
            dead_queues = []
            for q in self._subscribers:
                try:
                    q.put_nowait(message)
                except queue.Full:
                    dead_queues.append(q)
            # Remove dead queues
            for q in dead_queues:
                self._subscribers.remove(q)

    def subscriber_count(self) -> int:
        """Get the number of active subscribers."""
        with self._lock:
            return len(self._subscribers)


# Global event manager
event_manager = EventManager()


def create_app(parser: Optional[LogParser] = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        parser: Optional LogParser instance with parsed data.
                If not provided, creates an empty parser.

    Returns:
        Configured Flask application
    """
    app = Flask(
        __name__,
        template_folder=str(TEMPLATE_DIR),
        static_folder=str(STATIC_DIR),
    )

    # Store parser in app config for access in routes
    app.config["parser"] = parser or LogParser()

    # Register routes
    register_routes(app)

    return app


def register_routes(app: Flask) -> None:
    """Register all routes for the application."""

    @app.route("/")
    def index():
        """Serve the main dashboard page."""
        return render_template("index.html")

    @app.route("/api/events")
    def sse_events():
        """Server-Sent Events endpoint for real-time updates."""
        def generate() -> Generator[str, None, None]:
            q = event_manager.subscribe()
            try:
                # Send initial connection message
                yield f"data: {json.dumps({'type': 'connected', 'data': {}})}\n\n"

                while True:
                    try:
                        # Wait for events with timeout
                        message = q.get(timeout=30)
                        yield f"data: {json.dumps(message)}\n\n"
                    except queue.Empty:
                        # Send keepalive
                        yield f": keepalive\n\n"
            finally:
                event_manager.unsubscribe(q)

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.route("/api/session")
    def get_session():
        """Get the current session data."""
        parser: LogParser = app.config["parser"]
        session = parser.get_session()
        return jsonify(session.to_dict())

    @app.route("/api/state")
    def get_state():
        """Get the current parser state."""
        parser: LogParser = app.config["parser"]
        return jsonify({
            "state": parser.get_state().value,
            "lines_processed": parser.lines_processed,
        })

    @app.route("/api/attempts")
    def get_attempts():
        """Get list of all attempts with summaries."""
        parser: LogParser = app.config["parser"]
        session = parser.get_session()

        attempts_summary = []
        for attempt in session.attempts:
            attempts_summary.append({
                "attempt_number": attempt.attempt_number,
                "outcome": attempt.outcome.value,
                "boss_name": attempt.boss_name,
                "duration_seconds": attempt.duration_seconds,
                "start_time": attempt.start_time.isoformat(),
                "end_time": attempt.end_time.isoformat() if attempt.end_time else None,
                "total_hits": len(attempt.ability_hits),
                "total_debuffs": len(attempt.debuffs_applied),
                "total_deaths": len(attempt.deaths),
            })

        return jsonify({
            "attempts": attempts_summary,
            "total": len(attempts_summary),
        })

    @app.route("/api/attempts/<int:attempt_num>")
    def get_attempt(attempt_num: int):
        """Get detailed data for a specific attempt."""
        parser: LogParser = app.config["parser"]
        session = parser.get_session()

        # Find the attempt
        for attempt in session.attempts:
            if attempt.attempt_number == attempt_num:
                return jsonify(attempt.to_dict())

        return jsonify({"error": "Attempt not found"}), 404

    @app.route("/api/attempts/<int:attempt_num>/abilities")
    def get_attempt_abilities(attempt_num: int):
        """Get ability hits for a specific attempt with optional filtering."""
        parser: LogParser = app.config["parser"]
        session = parser.get_session()

        # Find the attempt
        attempt = None
        for a in session.attempts:
            if a.attempt_number == attempt_num:
                attempt = a
                break

        if not attempt:
            return jsonify({"error": "Attempt not found"}), 404

        # Get filter parameters
        player_filter = request.args.get("player")
        ability_filter = request.args.get("ability")

        # Filter abilities
        abilities = attempt.ability_hits
        if player_filter:
            abilities = [a for a in abilities if a.target_name == player_filter]
        if ability_filter:
            abilities = [a for a in abilities if a.ability_name == ability_filter]

        return jsonify({
            "abilities": [a.to_dict() for a in abilities],
            "total": len(abilities),
        })

    @app.route("/api/attempts/<int:attempt_num>/deaths")
    def get_attempt_deaths(attempt_num: int):
        """Get deaths for a specific attempt."""
        parser: LogParser = app.config["parser"]
        session = parser.get_session()

        # Find the attempt
        for attempt in session.attempts:
            if attempt.attempt_number == attempt_num:
                return jsonify({
                    "deaths": [d.to_dict() for d in attempt.deaths],
                    "total": len(attempt.deaths),
                })

        return jsonify({"error": "Attempt not found"}), 404

    @app.route("/api/attempts/<int:attempt_num>/debuffs")
    def get_attempt_debuffs(attempt_num: int):
        """Get debuffs for a specific attempt with optional filtering."""
        parser: LogParser = app.config["parser"]
        session = parser.get_session()

        # Find the attempt
        attempt = None
        for a in session.attempts:
            if a.attempt_number == attempt_num:
                attempt = a
                break

        if not attempt:
            return jsonify({"error": "Attempt not found"}), 404

        # Get filter parameters
        player_filter = request.args.get("player")
        debuff_filter = request.args.get("debuff")

        # Filter debuffs
        debuffs = attempt.debuffs_applied
        if player_filter:
            debuffs = [d for d in debuffs if d.target_name == player_filter]
        if debuff_filter:
            debuffs = [d for d in debuffs if d.effect_name == debuff_filter]

        return jsonify({
            "debuffs": [d.to_dict() for d in debuffs],
            "total": len(debuffs),
        })

    @app.route("/api/summary")
    def get_summary():
        """Get cross-attempt statistics."""
        parser: LogParser = app.config["parser"]
        session = parser.get_session()

        stats = session.get_cross_attempt_stats()

        return jsonify({
            "zone_name": session.zone_name,
            "boss_name": session.boss_name,
            "total_attempts": stats["total_attempts"],
            "total_wipes": stats["total_wipes"],
            "total_victories": stats["total_victories"],
            "deaths_by_player": stats["deaths_by_player"],
            "players": [{"id": p.id, "name": p.name} for p in session.players.values()],
        })

    @app.route("/api/players")
    def get_players():
        """Get list of players in the session."""
        parser: LogParser = app.config["parser"]
        session = parser.get_session()

        return jsonify({
            "players": [{"id": p.id, "name": p.name} for p in session.players.values()],
            "total": len(session.players),
        })


def broadcast_state_change(state: ParserState) -> None:
    """Broadcast a state change event."""
    event_manager.broadcast("state_change", {"state": state.value})


def broadcast_attempt_complete(attempt: FightAttempt) -> None:
    """Broadcast an attempt completion event."""
    event_manager.broadcast("attempt_complete", {
        "attempt_number": attempt.attempt_number,
        "outcome": attempt.outcome.value,
        "boss_name": attempt.boss_name,
        "duration_seconds": attempt.duration_seconds,
        "total_deaths": len(attempt.deaths),
    })


def broadcast_new_data() -> None:
    """Broadcast that new data is available (generic refresh signal)."""
    event_manager.broadcast("data_update", {})


def run_server(parser: LogParser, host: str = "0.0.0.0", port: int = 8080, debug: bool = False) -> None:
    """Run the Flask development server.

    Args:
        parser: LogParser instance with parsed data
        host: Host to bind to
        port: Port to listen on
        debug: Enable debug mode
    """
    app = create_app(parser)
    print(f"Starting web dashboard at http://localhost:{port}")
    app.run(host=host, port=port, debug=debug, threaded=True)


def run_server_background(parser: LogParser, host: str = "0.0.0.0", port: int = 8080) -> threading.Thread:
    """Run the Flask server in a background thread.

    Args:
        parser: LogParser instance with parsed data
        host: Host to bind to
        port: Port to listen on

    Returns:
        The thread running the server
    """
    app = create_app(parser)

    def run():
        # Suppress Flask's default logging for cleaner output
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.WARNING)

        app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread
