"""Flask web server for FFXIV Battle Tracker dashboard."""

from pathlib import Path

from flask import Flask, jsonify, render_template, request

from ..parser.log_parser import LogParser

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"


def create_app(
    parser: LogParser | None = None, log_file_path: str | None = None
) -> Flask:
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
    # Session-scoped manual hit type overrides (ability_id -> hit_type)
    app.config["manual_hit_types"] = {}

    # Register routes
    register_routes(app)

    return app


def apply_manual_hit_types(app: Flask) -> int:
    """Apply manual hit type overrides to all attempts and recalculate damage.

    Args:
        app: Flask application with parser and manual_hit_types in config

    Returns:
        Number of abilities updated
    """
    parser: LogParser = app.config["parser"]
    manual_overrides: dict[str, str] = app.config.get("manual_hit_types", {})

    if not manual_overrides:
        return 0

    session = parser.get_session()
    updated_count = 0

    for fight in session.fights:
        for attempt in fight.attempts:
            needs_recalc = False
            for hit in attempt.ability_hits:
                ability_id_upper = hit.ability_id.upper()
                if ability_id_upper in manual_overrides:
                    new_type = manual_overrides[ability_id_upper]
                    if hit.hit_type != new_type:
                        hit.hit_type = new_type
                        updated_count += 1
                        needs_recalc = True

            # Recalculate unmitigated damage if any hit types changed
            if needs_recalc:
                attempt.calculate_unmitigated_damage()

    return updated_count


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

        # Re-apply manual hit type overrides if any exist
        overrides_applied = apply_manual_hit_types(app)

        session = new_parser.get_session()
        return jsonify(
            {
                "success": True,
                "lines_processed": new_parser.lines_processed,
                "fights": len(session.fights),
                "attempts": len(session.attempts),
                "manual_overrides_applied": overrides_applied,
            }
        )

    @app.route("/api/session")
    def get_session():
        """Get the current session data."""
        parser: LogParser = app.config["parser"]
        session = parser.get_session()
        return jsonify(session.to_dict())

    @app.route("/api/fights")
    def get_fights():
        """Get list of all fights with summaries."""
        parser: LogParser = app.config["parser"]
        session = parser.get_session()

        fights_summary = []
        for fight in session.fights:
            fights_summary.append(
                {
                    "fight_id": fight.fight_id,
                    "zone_id": fight.zone_id,
                    "zone_name": fight.zone_name,
                    "boss_name": fight.boss_name or "(Unknown Boss)",
                    "start_time": fight.start_time.isoformat()
                    if fight.start_time
                    else None,
                    "total_attempts": len(fight.completed_attempts),
                    "total_wipes": fight.total_wipes,
                    "total_victories": fight.total_victories,
                    "total_deaths": fight.total_deaths,
                }
            )

        return jsonify(
            {
                "fights": fights_summary,
                "total": len(fights_summary),
            }
        )

    @app.route("/api/fights/<int:fight_id>")
    def get_fight(fight_id: int):
        """Get detailed data for a specific fight."""
        parser: LogParser = app.config["parser"]
        session = parser.get_session()

        # Find the fight
        for fight in session.fights:
            if fight.fight_id == fight_id:
                return jsonify(fight.to_dict())

        return jsonify({"error": "Fight not found"}), 404

    @app.route("/api/fights/<int:fight_id>/attempts")
    def get_fight_attempts(fight_id: int):
        """Get list of attempts for a specific fight."""
        parser: LogParser = app.config["parser"]
        session = parser.get_session()

        # Find the fight
        for fight in session.fights:
            if fight.fight_id == fight_id:
                attempts_summary = []
                for attempt in fight.completed_attempts:
                    attempts_summary.append(
                        {
                            "attempt_number": attempt.attempt_number,
                            "outcome": attempt.outcome.value,
                            "boss_name": attempt.boss_name,
                            "duration_seconds": attempt.duration_seconds,
                            "start_time": attempt.start_time.isoformat(),
                            "end_time": attempt.end_time.isoformat()
                            if attempt.end_time
                            else None,
                            "total_hits": len(attempt.ability_hits),
                            "total_debuffs": len(attempt.debuffs_applied),
                            "total_deaths": len(attempt.deaths),
                        }
                    )
                return jsonify(
                    {
                        "fight_id": fight_id,
                        "attempts": attempts_summary,
                        "total": len(attempts_summary),
                    }
                )

        return jsonify({"error": "Fight not found"}), 404

    @app.route("/api/fights/<int:fight_id>/attempts/<int:attempt_num>")
    def get_fight_attempt(fight_id: int, attempt_num: int):
        """Get detailed data for a specific attempt in a fight."""
        parser: LogParser = app.config["parser"]
        session = parser.get_session()

        # Find the fight
        for fight in session.fights:
            if fight.fight_id == fight_id:
                # Find the attempt
                for attempt in fight.completed_attempts:
                    if attempt.attempt_number == attempt_num:
                        return jsonify(attempt.to_dict())
                return jsonify({"error": "Attempt not found"}), 404

        return jsonify({"error": "Fight not found"}), 404

    @app.route("/api/state")
    def get_state():
        """Get the current parser state."""
        parser: LogParser = app.config["parser"]
        return jsonify(
            {
                "state": parser.get_state().value,
                "lines_processed": parser.lines_processed,
            }
        )

    @app.route("/api/attempts")
    def get_attempts():
        """Get list of all attempts with summaries."""
        parser: LogParser = app.config["parser"]
        session = parser.get_session()

        attempts_summary = []
        for attempt in session.attempts:
            attempts_summary.append(
                {
                    "attempt_number": attempt.attempt_number,
                    "outcome": attempt.outcome.value,
                    "boss_name": attempt.boss_name,
                    "duration_seconds": attempt.duration_seconds,
                    "start_time": attempt.start_time.isoformat(),
                    "end_time": attempt.end_time.isoformat()
                    if attempt.end_time
                    else None,
                    "total_hits": len(attempt.ability_hits),
                    "total_debuffs": len(attempt.debuffs_applied),
                    "total_deaths": len(attempt.deaths),
                }
            )

        return jsonify(
            {
                "attempts": attempts_summary,
                "total": len(attempts_summary),
            }
        )

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

        return jsonify(
            {
                "abilities": [a.to_dict() for a in abilities],
                "total": len(abilities),
            }
        )

    @app.route("/api/attempts/<int:attempt_num>/deaths")
    def get_attempt_deaths(attempt_num: int):
        """Get deaths for a specific attempt."""
        parser: LogParser = app.config["parser"]
        session = parser.get_session()

        # Find the attempt
        for attempt in session.attempts:
            if attempt.attempt_number == attempt_num:
                return jsonify(
                    {
                        "deaths": [d.to_dict() for d in attempt.deaths],
                        "total": len(attempt.deaths),
                    }
                )

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

        return jsonify(
            {
                "debuffs": [d.to_dict() for d in debuffs],
                "total": len(debuffs),
            }
        )

    @app.route("/api/summary")
    def get_summary():
        """Get cross-attempt statistics."""
        parser: LogParser = app.config["parser"]
        session = parser.get_session()

        stats = session.get_cross_attempt_stats()

        return jsonify(
            {
                "zone_name": session.zone_name,
                "boss_name": session.boss_name,
                "total_fights": stats.get("total_fights", len(session.fights)),
                "total_attempts": stats["total_attempts"],
                "total_wipes": stats["total_wipes"],
                "total_victories": stats["total_victories"],
                "deaths_by_player": stats["deaths_by_player"],
                "players": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "job_id": p.job_id,
                        "job_name": p.job_name,
                    }
                    for p in session.players.values()
                ],
            }
        )

    @app.route("/api/players")
    def get_players():
        """Get list of players in the session."""
        parser: LogParser = app.config["parser"]
        session = parser.get_session()

        return jsonify(
            {
                "players": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "job_id": p.job_id,
                        "job_name": p.job_name,
                    }
                    for p in session.players.values()
                ],
                "total": len(session.players),
            }
        )

    @app.route("/api/manual-hit-types", methods=["GET"])
    def get_manual_hit_types():
        """Get current manual hit type overrides."""
        manual_overrides: dict[str, str] = app.config.get("manual_hit_types", {})
        return jsonify({"manual_hit_types": manual_overrides})

    @app.route("/api/manual-hit-types", methods=["POST"])
    def set_manual_hit_types():
        """Set manual hit type overrides and recalculate unmitigated damage.

        Expected JSON body:
            {"overrides": {"ABILITY_ID": "Physical|Magical|Special", ...}}
        """
        data = request.get_json()
        if not data or "overrides" not in data:
            return jsonify({"error": "Missing 'overrides' in request body"}), 400

        new_overrides = data["overrides"]
        if not isinstance(new_overrides, dict):
            return jsonify({"error": "'overrides' must be a dictionary"}), 400

        # Validate hit types
        valid_types = {"Physical", "Magical", "Special", "Unknown"}
        for ability_id, hit_type in new_overrides.items():
            if hit_type not in valid_types:
                return jsonify(
                    {"error": f"Invalid hit type '{hit_type}' for {ability_id}"}
                ), 400

        # Normalize ability IDs to uppercase and merge with existing overrides
        normalized = {k.upper(): v for k, v in new_overrides.items()}
        app.config["manual_hit_types"].update(normalized)

        # Apply overrides to all attempts
        updated_count = apply_manual_hit_types(app)

        return jsonify(
            {
                "success": True,
                "abilities_updated": updated_count,
                "total_overrides": len(app.config["manual_hit_types"]),
            }
        )

    @app.route("/api/manual-hit-types", methods=["DELETE"])
    def clear_manual_hit_types():
        """Clear all manual hit type overrides."""
        app.config["manual_hit_types"] = {}
        return jsonify({"success": True, "message": "All manual overrides cleared"})

    @app.route("/api/fights/<int:fight_id>/attempts/<int:attempt_num>/unique-abilities")
    def get_attempt_unique_abilities(fight_id: int, attempt_num: int):
        """Get unique abilities for a specific attempt with current hit types.

        Returns a list of unique abilities with their IDs, names, and current hit types.
        Used by the Manual Hit Type Entry modal.
        """
        parser: LogParser = app.config["parser"]
        session = parser.get_session()
        manual_overrides: dict[str, str] = app.config.get("manual_hit_types", {})

        # Find the fight and attempt
        for fight in session.fights:
            if fight.fight_id == fight_id:
                for attempt in fight.completed_attempts:
                    if attempt.attempt_number == attempt_num:
                        # Collect unique abilities
                        unique_abilities: dict[str, dict] = {}
                        for hit in attempt.ability_hits:
                            aid_upper = hit.ability_id.upper()
                            if aid_upper not in unique_abilities:
                                unique_abilities[aid_upper] = {
                                    "ability_id": aid_upper,
                                    "ability_name": hit.ability_name,
                                    "hit_type": hit.hit_type or "Unknown",
                                    "is_manual_override": aid_upper in manual_overrides,
                                }
                        # Sort by ability name
                        sorted_abilities = sorted(
                            unique_abilities.values(),
                            key=lambda x: x["ability_name"].lower(),
                        )
                        return jsonify(
                            {
                                "abilities": sorted_abilities,
                                "total": len(sorted_abilities),
                            }
                        )
                return jsonify({"error": "Attempt not found"}), 404
        return jsonify({"error": "Fight not found"}), 404


def run_server(
    parser: LogParser,
    log_file_path: str,
    host: str = "0.0.0.0",
    port: int = 8080,
    debug: bool = False,
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
