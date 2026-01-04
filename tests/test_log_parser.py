"""Tests for the log parser state machine."""

from src.models.data_models import AttemptOutcome, ParserState
from src.parser.log_parser import LogParser


class TestLogParserInitialization:
    """Tests for parser initialization."""

    def test_initial_state_is_idle(self):
        parser = LogParser()
        assert parser.state == ParserState.IDLE

    def test_initial_session_is_empty(self):
        parser = LogParser()
        assert parser.session.current_fight is None
        assert len(parser.session.fights) == 0

    def test_reset_clears_state(self):
        parser = LogParser()
        parser.state = ParserState.IN_COMBAT
        parser.lines_processed = 100

        parser.reset()

        assert parser.state == ParserState.IDLE
        assert parser.lines_processed == 0


class TestZoneChangeHandling:
    """Tests for zone change state transitions."""

    def test_combat_zone_transitions_to_in_instance(self, sample_zone_change_combat):
        parser = LogParser()
        parser.parse_line(sample_zone_change_combat)

        assert parser.state == ParserState.IN_INSTANCE
        assert parser.session.current_fight is not None
        assert parser.session.current_fight.zone_name == "Hell on Rails (Extreme)"

    def test_city_zone_stays_idle(self, sample_zone_change_city):
        parser = LogParser()
        parser.parse_line(sample_zone_change_city)

        assert parser.state == ParserState.IDLE
        assert parser.session.current_fight is None

    def test_zone_change_clears_players(
        self,
        sample_zone_change_combat,
        sample_add_combatant_player,
        sample_zone_change_city,
    ):
        parser = LogParser()

        # Add a player first
        parser.parse_line(sample_zone_change_combat)
        parser.parse_line(sample_add_combatant_player)
        assert len(parser.session.players) == 1

        # Zone change should clear players
        parser.parse_line(sample_zone_change_city)
        assert len(parser.session.players) == 0


class TestCombatStateTransitions:
    """Tests for combat state machine transitions."""

    def test_commence_starts_combat(self, sample_zone_change_combat, sample_commence):
        parser = LogParser()
        parser.parse_line(sample_zone_change_combat)
        parser.parse_line(sample_commence)

        assert parser.state == ParserState.IN_COMBAT
        assert parser.session.current_attempt is not None

    def test_victory_ends_combat(
        self, sample_zone_change_combat, sample_commence, sample_victory
    ):
        parser = LogParser()
        parser.parse_line(sample_zone_change_combat)
        parser.parse_line(sample_commence)
        parser.parse_line(sample_victory)

        assert parser.state == ParserState.IN_INSTANCE
        assert len(parser.session.current_fight.attempts) == 1
        assert (
            parser.session.current_fight.attempts[0].outcome == AttemptOutcome.VICTORY
        )

    def test_wipe_transitions_to_pending(
        self, sample_zone_change_combat, sample_commence, sample_wipe
    ):
        parser = LogParser()
        parser.parse_line(sample_zone_change_combat)
        parser.parse_line(sample_commence)
        parser.parse_line(sample_wipe)

        assert parser.state == ParserState.WIPE_PENDING

    def test_barrier_up_after_wipe_returns_to_instance(
        self,
        sample_zone_change_combat,
        sample_commence,
        sample_wipe,
        sample_barrier_up,
    ):
        parser = LogParser()
        parser.parse_line(sample_zone_change_combat)
        parser.parse_line(sample_commence)
        parser.parse_line(sample_wipe)
        parser.parse_line(sample_barrier_up)

        assert parser.state == ParserState.IN_INSTANCE
        assert len(parser.session.current_fight.attempts) == 1
        assert parser.session.current_fight.attempts[0].outcome == AttemptOutcome.WIPE

    def test_recommence_starts_new_attempt(
        self,
        sample_zone_change_combat,
        sample_commence,
        sample_wipe,
        sample_recommence,
    ):
        parser = LogParser()
        parser.parse_line(sample_zone_change_combat)
        parser.parse_line(sample_commence)
        parser.parse_line(sample_wipe)
        parser.parse_line(sample_recommence)

        assert parser.state == ParserState.IN_COMBAT
        # Previous wipe should be finalized, new attempt started
        assert len(parser.session.current_fight.attempts) == 2


class TestEventRecording:
    """Tests for recording combat events."""

    def test_ability_recorded_in_combat(
        self,
        sample_zone_change_combat,
        sample_commence,
        sample_ability_enemy_to_player,
    ):
        parser = LogParser()
        parser.parse_line(sample_zone_change_combat)
        parser.parse_line(sample_commence)
        parser.parse_line(sample_ability_enemy_to_player)

        assert len(parser.session.current_attempt.ability_hits) == 1
        assert (
            parser.session.current_attempt.ability_hits[0].ability_name
            == "Dead Man's Blastpipe"
        )

    def test_ability_ignored_outside_combat(
        self, sample_zone_change_combat, sample_ability_enemy_to_player
    ):
        parser = LogParser()
        parser.parse_line(sample_zone_change_combat)
        # No commence, so not in combat
        parser.parse_line(sample_ability_enemy_to_player)

        # No current attempt, so ability shouldn't be recorded anywhere
        assert parser.session.current_attempt is None

    def test_death_recorded_in_combat(
        self, sample_zone_change_combat, sample_commence, sample_death
    ):
        parser = LogParser()
        parser.parse_line(sample_zone_change_combat)
        parser.parse_line(sample_commence)
        parser.parse_line(sample_death)

        assert len(parser.session.current_attempt.deaths) == 1
        assert parser.session.current_attempt.deaths[0].player_name == "Gyodo Ohta"

    def test_death_recorded_during_wipe_pending(
        self, sample_zone_change_combat, sample_commence, sample_wipe, sample_death
    ):
        """Deaths during wipe sequence should still be recorded."""
        parser = LogParser()
        parser.parse_line(sample_zone_change_combat)
        parser.parse_line(sample_commence)
        parser.parse_line(sample_wipe)
        parser.parse_line(sample_death)

        assert len(parser.session.current_attempt.deaths) == 1

    def test_debuff_recorded_in_combat(
        self, sample_zone_change_combat, sample_commence, sample_debuff_enemy_source
    ):
        parser = LogParser()
        parser.parse_line(sample_zone_change_combat)
        parser.parse_line(sample_commence)
        parser.parse_line(sample_debuff_enemy_source)

        assert len(parser.session.current_attempt.debuffs_applied) == 1


class TestPlayerTracking:
    """Tests for player roster tracking."""

    def test_player_added_to_session(
        self, sample_zone_change_combat, sample_add_combatant_player
    ):
        parser = LogParser()
        parser.parse_line(sample_zone_change_combat)
        parser.parse_line(sample_add_combatant_player)

        assert len(parser.session.players) == 1
        # players is a dict with player IDs as keys
        player = list(parser.session.players.values())[0]
        assert player.name == "Jalapeno Jeff"

    def test_player_added_to_fight(
        self, sample_zone_change_combat, sample_add_combatant_player
    ):
        parser = LogParser()
        parser.parse_line(sample_zone_change_combat)
        parser.parse_line(sample_add_combatant_player)

        assert len(parser.session.current_fight.players) == 1

    def test_enemy_not_added_as_player(
        self, sample_zone_change_combat, sample_add_combatant_enemy
    ):
        parser = LogParser()
        parser.parse_line(sample_zone_change_combat)
        parser.parse_line(sample_add_combatant_enemy)

        assert len(parser.session.players) == 0


class TestBossDetection:
    """Tests for boss name detection."""

    def test_boss_detected_from_first_enemy_ability(
        self,
        sample_zone_change_combat,
        sample_commence,
        sample_ability_enemy_to_player,
    ):
        parser = LogParser()
        parser.parse_line(sample_zone_change_combat)
        parser.parse_line(sample_commence)
        parser.parse_line(sample_ability_enemy_to_player)

        assert parser.session.current_fight.boss_name == "Doomtrain"
        assert parser.session.current_attempt.boss_name == "Doomtrain"


class TestCallbacks:
    """Tests for parser callbacks."""

    def test_attempt_complete_callback(
        self, sample_zone_change_combat, sample_commence, sample_victory
    ):
        parser = LogParser()
        completed_attempts = []

        def on_complete(attempt):
            completed_attempts.append(attempt)

        parser.set_on_attempt_complete(on_complete)
        parser.parse_line(sample_zone_change_combat)
        parser.parse_line(sample_commence)
        parser.parse_line(sample_victory)

        assert len(completed_attempts) == 1
        assert completed_attempts[0].outcome == AttemptOutcome.VICTORY

    def test_state_change_callback(self, sample_zone_change_combat, sample_commence):
        parser = LogParser()
        state_changes = []

        def on_state_change(new_state):
            state_changes.append(new_state)

        parser.set_on_state_change(on_state_change)
        parser.parse_line(sample_zone_change_combat)
        parser.parse_line(sample_commence)

        assert ParserState.IN_INSTANCE in state_changes
        assert ParserState.IN_COMBAT in state_changes


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_line_ignored(self):
        parser = LogParser()
        parser.parse_line("")
        parser.parse_line("   ")
        assert parser.lines_processed == 2

    def test_malformed_line_ignored(self):
        parser = LogParser()
        parser.parse_line("not|enough")
        assert parser.state == ParserState.IDLE

    def test_unknown_line_type_ignored(self):
        parser = LogParser()
        parser.parse_line("99|2026-01-03T14:22:00.0000000-06:00|some|data|here")
        assert parser.state == ParserState.IDLE

    def test_commence_without_zone_creates_fight(self, sample_commence):
        """Commence from IDLE should create a placeholder fight."""
        parser = LogParser()
        parser.parse_line(sample_commence)

        assert parser.state == ParserState.IN_COMBAT
        assert parser.session.current_fight is not None
        assert parser.session.current_fight.zone_name == "Unknown Zone"
