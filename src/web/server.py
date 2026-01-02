"""Flask web server for FFXIV Battle Tracker dashboard."""

import json
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, render_template, request

from ..models.data_models import FightAttempt, ParserState, RaidSession
from ..parser.log_parser import LogParser


# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"


def create_app(parser: Optional[LogParser] = None, log_file_path: Optional[str] = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        parser: Optional LogParser instance with parsed data.
                If not provided, creates an empty parser.
        log_file_path: Path to the log file for refresh functionality.

    Returns:
        Configured Flask application
    """
    app = Flask(
        __name__,
        template_folder=str(TEMPLATE_DIR),
        static_folder=str(STATIC_DIR),
    )

    # Store parser and log file path in app config for access in routes
    app.config["parser"] = parser or LogParser()
    app.config["log_file_path"] = log_file_path

    # Register routes
    register_routes(app)

    return app


def register_routes(app: Flask) -> None:
    """Register all routes for the application."""

    @app.route("/")
    def index():
        """Serve the main dashboard page."""
        return render_template("index.html")

    @app.route("/api/refresh", methods=["POST"])
    def refresh_data():
        """Re-parse the log file to get latest data."""
        log_file_path = app.config.get("log_file_path")

        if not log_file_path:
            return jsonify({"error": "No log file configured"}), 400

        path = Path(log_file_path)
        if not path.exists():
            return jsonify({"error": f"Log file not found: {log_file_path}"}), 404

        # Create a new parser and re-parse the file
        new_parser = LogParser()
        new_parser.parse_file(log_file_path)

        # Replace the parser in app config
        app.config["parser"] = new_parser

        return jsonify({
            "success": True,
            "lines_processed": new_parser.lines_processed,
            "attempts": len(new_parser.get_session().attempts),
        })

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


def run_server(
    parser: LogParser,
    log_file_path: str,
    host: str = "0.0.0.0",
    port: int = 8080,
    debug: bool = False
) -> None:
    """Run the Flask development server.

    Args:
        parser: LogParser instance with parsed data
        log_file_path: Path to the log file for refresh functionality
        host: Host to bind to
        port: Port to listen on
        debug: Enable debug mode
    """
    app = create_app(parser, log_file_path)
    print(f"Starting web dashboard at http://localhost:{port}")
    print(f"Monitoring log file: {log_file_path}")
    print("Use the Refresh button in the dashboard to reload data")
    app.run(host=host, port=port, debug=debug, threaded=True)
