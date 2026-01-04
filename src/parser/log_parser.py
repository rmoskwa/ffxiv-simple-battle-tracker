"""Main log parser with state machine for tracking fight attempts."""

from collections.abc import Callable
from datetime import datetime

from ..models.data_models import (
    AttemptOutcome,
    FightAttempt,
    ParserState,
    Player,
    RaidSession,
)
from .line_handlers import LineHandlers, get_job_name

# Known non-combat zones (cities, housing, etc.) - these don't create Fight entries.
# TODO: generalize this list.
NON_COMBAT_ZONES = {
    "solution nine",
    "limsa lominsa",
    "ul'dah",
    "gridania",
    "ishgard",
    "kugane",
    "crystarium",
    "eulmore",
    "old sharlayan",
    "radz-at-han",
    "tuliyollal",
}


class LogParser:
    """Parser for ACT log files with state machine for fight tracking.

    The parser maintains state to track:
    - Current zone/instance
    - Players in the raid
    - Fight attempts (commence -> wipe/victory)
    - Events within each attempt
    - Player shield percentages for absorption tracking

    State Machine:
        IDLE -> (zone change) -> IN_INSTANCE
        IN_INSTANCE -> (commence) -> IN_COMBAT
        IN_COMBAT -> (wipe fadeout) -> WIPE_PENDING
        IN_COMBAT -> (victory) -> IN_INSTANCE
        WIPE_PENDING -> (barrier up) -> IN_INSTANCE
    """

    def __init__(self):
        """Initialize the parser."""
        self.state = ParserState.IDLE
        self.session = RaidSession()
        self.handlers = LineHandlers()
        self._boss_detected = False
        self._on_attempt_complete: Callable[[FightAttempt], None] | None = None
        self._on_state_change: Callable[[ParserState], None] | None = None
        self._pending_wipe_time: datetime | None = (
            None  # Store wipe time until barrier up
        )
        self.lines_processed = 0

        # Shield tracking for absorbed damage calculation
        # Maps player_id -> (shield_percent, max_hp)
        self._player_shields: dict[str, tuple[int, int]] = {}

        # Pending ability hits awaiting effect result (line 37) for absorption calc
        # Maps sequence_id -> list of (AbilityHit, shield_before_percent)
        self._pending_hits: dict[str, list[tuple]] = {}

    def set_on_attempt_complete(self, callback: Callable[[FightAttempt], None]) -> None:
        """Set callback for when an attempt completes (wipe or victory)."""
        self._on_attempt_complete = callback

    def set_on_state_change(self, callback: Callable[[ParserState], None]) -> None:
        """Set callback for state changes."""
        self._on_state_change = callback

    def _change_state(self, new_state: ParserState) -> None:
        """Change parser state and notify callback."""
        old_state = self.state
        self.state = new_state
        if self._on_state_change and old_state != new_state:
            self._on_state_change(new_state)

    def parse_line(self, line: str) -> None:
        """Parse a single log line and update state accordingly.

        Args:
            line: A single line from the ACT log file
        """
        self.lines_processed += 1

        # Skip empty lines
        line = line.strip()
        if not line:
            return

        # Split into fields
        fields = line.split("|")
        if len(fields) < 2:
            return

        line_type = fields[0]

        # Route to appropriate handler based on line type
        if line_type == "01":
            self._handle_zone_change(fields)
        elif line_type == "03":
            self._handle_add_combatant(fields)
        elif line_type in ("21", "22"):
            self._handle_ability(fields)
        elif line_type == "25":
            self._handle_death(fields)
        elif line_type == "26":
            self._handle_buff(fields)
        elif line_type == "33":
            self._handle_actor_control(fields)
        elif line_type == "37":
            self._handle_effect_result(fields)

    def _handle_zone_change(self, fields: list) -> None:
        """Handle zone change (Line 01)."""
        data = self.handlers.parse_line_01_zone_change(fields)
        if not data:
            return

        # Set session start time on first zone change
        if self.session.start_time is None:
            self.session.start_time = data.timestamp

        # Clear players on zone change
        self.session.players.clear()
        self._boss_detected = False

        # Check if this is a combat zone (instances, trials, raids)
        zone_name_lower = data.zone_name.lower()
        is_combat_zone = zone_name_lower not in NON_COMBAT_ZONES

        if is_combat_zone:
            # Create a new Fight for this zone
            self.session.start_new_fight(data.zone_id, data.zone_name, data.timestamp)
            # Transition to IN_INSTANCE
            self._change_state(ParserState.IN_INSTANCE)
        else:
            # Non-combat zone, return to IDLE
            self._change_state(ParserState.IDLE)

    def _handle_add_combatant(self, fields: list) -> None:
        """Handle AddCombatant (Line 03)."""
        data = self.handlers.parse_line_03_add_combatant(fields)
        if not data:
            return

        # Only add players (ID starts with 10)
        if data.is_player and data.name:
            player = Player(
                id=data.id,
                name=data.name,
                job_id=data.job_id,
                job_name=get_job_name(data.job_id),
            )
            self.session.add_player(player)
            # Also add to current fight if one exists
            if self.session.current_fight:
                self.session.current_fight.add_player(player)

    def _handle_ability(self, fields: list) -> None:
        """Handle ability (Line 21/22)."""
        # Only process in combat
        if self.state != ParserState.IN_COMBAT:
            return

        # Check for first player->boss damage (to set timeline start)
        if (
            self.session.current_attempt
            and not self.session.current_attempt.first_damage_time
        ):
            player_damage_time = self.handlers.parse_player_damage_timestamp(fields)
            if player_damage_time:
                self.session.current_attempt.first_damage_time = player_damage_time

        # Get target_id to look up current shield state
        target_id = fields[6] if len(fields) > 6 else ""
        shield_before = 0
        max_hp_before = 0
        if target_id in self._player_shields:
            shield_before, max_hp_before = self._player_shields[target_id]

        ability = self.handlers.parse_line_21_22_ability(fields, shield_before)
        if not ability:
            return

        # Detect boss from first enemy ability
        if not self._boss_detected and ability.source_name:
            # Set boss name on current fight and attempt
            if self.session.current_fight:
                self.session.current_fight.boss_name = ability.source_name
            self._boss_detected = True
            if self.session.current_attempt:
                self.session.current_attempt.boss_name = ability.source_name

        # Add to current attempt
        if self.session.current_attempt:
            self.session.current_attempt.ability_hits.append(ability)

            # Track pending hit for absorption calculation
            # The sequence_id links this ability to its effect result (line 37)
            if ability.sequence_id:
                if ability.sequence_id not in self._pending_hits:
                    self._pending_hits[ability.sequence_id] = []
                self._pending_hits[ability.sequence_id].append(
                    (ability, shield_before, max_hp_before)
                )

    def _handle_death(self, fields: list) -> None:
        """Handle death (Line 25)."""
        # Process deaths in combat or during wipe (deaths can occur as part of wipe)
        if self.state not in (ParserState.IN_COMBAT, ParserState.WIPE_PENDING):
            return

        death = self.handlers.parse_line_25_death(fields)
        if not death:
            return

        # Add to current attempt
        if self.session.current_attempt:
            self.session.current_attempt.deaths.append(death)

    def _handle_buff(self, fields: list) -> None:
        """Handle buff/debuff application (Line 26)."""
        # Only process in combat
        if self.state != ParserState.IN_COMBAT:
            return

        # Parse as boss->player debuff (for display in debuffs tab)
        debuff = self.handlers.parse_line_26_buff(fields)
        if debuff and self.session.current_attempt:
            self.session.current_attempt.debuffs_applied.append(debuff)

        # Also check for mitigation buffs (player/friendly → player)
        mitigation_buff = self.handlers.parse_line_26_mitigation_buff(fields)
        if mitigation_buff and self.session.current_attempt:
            self.session.current_attempt.active_mitigations.append(mitigation_buff)

        # Also check for boss debuffs (player → boss, like Reprisal)
        boss_debuff = self.handlers.parse_line_26_boss_debuff(fields)
        if boss_debuff and self.session.current_attempt:
            self.session.current_attempt.active_mitigations.append(boss_debuff)

    def _handle_effect_result(self, fields: list) -> None:
        """Handle effect result (Line 37).

        This line confirms when ability effects are applied and contains
        the target's current HP/shield values after the effect. We use this
        to calculate absorbed damage by comparing shield % before and after.

        For AOE abilities (line 22), all targets share the same sequence_id
        but each gets their own line 37 result. We process hits one target
        at a time, keeping unprocessed hits for other targets.
        """
        # Process effect results both in combat and during wipe
        # (effects can resolve during wipe sequence)
        if self.state not in (ParserState.IN_COMBAT, ParserState.WIPE_PENDING):
            return

        data = self.handlers.parse_line_37_effect_result(fields)
        if not data:
            return

        # Update player shield state for future hits
        self._player_shields[data.target_id] = (data.shield_percent, data.max_hp)

        # Check if we have pending hits for this sequence_id
        if data.sequence_id in self._pending_hits:
            pending = self._pending_hits[data.sequence_id]
            remaining = []

            for hit, shield_before, max_hp_before in pending:
                # Only calculate absorption for hits targeting this player
                if hit.target_id != data.target_id:
                    # Keep this hit for later (different target)
                    remaining.append((hit, shield_before, max_hp_before))
                    continue

                # Calculate absorbed damage
                # absorbed = (shield_before - shield_after) * max_hp / 100
                shield_after = data.shield_percent
                max_hp = data.max_hp if data.max_hp > 0 else max_hp_before

                if max_hp > 0 and shield_before > shield_after:
                    # Shield was consumed - calculate how much was absorbed
                    shield_hp_before = (shield_before * max_hp) // 100
                    shield_hp_after = (shield_after * max_hp) // 100
                    absorbed = shield_hp_before - shield_hp_after

                    # Sanity check: absorbed should be >= 0
                    if absorbed > 0:
                        hit.absorbed_damage = absorbed

            # Update or remove pending hits
            if remaining:
                self._pending_hits[data.sequence_id] = remaining
            else:
                del self._pending_hits[data.sequence_id]

    def _handle_actor_control(self, fields: list) -> None:
        """Handle ActorControl (Line 33)."""
        data = self.handlers.parse_line_33_actor_control(fields)
        if not data:
            return

        # Handle commence (fight start)
        if self.handlers.is_commence_command(data):
            if self.state in (ParserState.IN_INSTANCE, ParserState.IDLE):
                self._start_new_attempt(data.timestamp)
                self._change_state(ParserState.IN_COMBAT)

        # Handle wipe (fade out)
        elif self.handlers.is_wipe_command(data):
            if self.state == ParserState.IN_COMBAT:
                self._change_state(ParserState.WIPE_PENDING)
                # Store wipe time - wait for deaths during wipe sequence
                self._pending_wipe_time = data.timestamp

        # Handle victory
        elif self.handlers.is_victory_command(data):
            if self.state == ParserState.IN_COMBAT:
                self._finalize_attempt(data.timestamp, AttemptOutcome.VICTORY)
                self._change_state(ParserState.IN_INSTANCE)

        # Handle barrier up (reset ready after wipe)
        elif self.handlers.is_barrier_up_command(data):
            if self.state == ParserState.WIPE_PENDING:
                # Now finalize the wipe attempt (deaths have been recorded)
                if self._pending_wipe_time:
                    self._finalize_attempt(self._pending_wipe_time, AttemptOutcome.WIPE)
                    self._pending_wipe_time = None
                self._change_state(ParserState.IN_INSTANCE)

        # Handle recommence (retry)
        elif self.handlers.is_recommence_command(data):
            # Handle recommence from WIPE_PENDING (finalize previous wipe first)
            if self.state == ParserState.WIPE_PENDING:
                if self._pending_wipe_time:
                    self._finalize_attempt(self._pending_wipe_time, AttemptOutcome.WIPE)
                    self._pending_wipe_time = None
            if self.state in (ParserState.IN_INSTANCE, ParserState.WIPE_PENDING):
                self._start_new_attempt(data.timestamp)
                self._change_state(ParserState.IN_COMBAT)

    def _start_new_attempt(self, start_time: datetime) -> None:
        """Start a new fight attempt."""
        self._boss_detected = False
        # Clear shield tracking state for new attempt
        self._player_shields.clear()
        self._pending_hits.clear()
        # Ensure we have a current fight (create one if needed from IDLE state)
        if not self.session.current_fight:
            # This shouldn't normally happen, but handle gracefully
            self.session.start_new_fight("unknown", "Unknown Zone", start_time)
        attempt = self.session.start_new_attempt(start_time)
        # Inherit boss name from fight if already detected
        if self.session.current_fight and self.session.current_fight.boss_name:
            attempt.boss_name = self.session.current_fight.boss_name

    def _finalize_attempt(self, end_time: datetime, outcome: AttemptOutcome) -> None:
        """Finalize the current attempt."""
        self.session.finalize_current_attempt(end_time, outcome)

        # Process ability hits: first resolve hit types, then calculate unmitigated
        if self.session.current_attempt:
            # Resolve hit types (Physical/Magical) from XIVAPI cache FIRST
            # This is needed for accurate unmitigated damage calculation
            self.session.current_attempt.resolve_hit_types()
            # Calculate unmitigated damage using hit types for accurate mitigation
            self.session.current_attempt.calculate_unmitigated_damage()

        # Notify callback
        if self._on_attempt_complete and self.session.current_attempt:
            self._on_attempt_complete(self.session.current_attempt)

    def parse_file(self, filepath: str) -> RaidSession:
        """Parse an entire log file.

        Args:
            filepath: Path to the ACT log file

        Returns:
            The populated RaidSession with all parsed attempts
        """
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            for line in f:
                self.parse_line(line)

        return self.session

    def get_session(self) -> RaidSession:
        """Get the current raid session."""
        return self.session

    def get_current_attempt(self) -> FightAttempt | None:
        """Get the current fight attempt."""
        return self.session.current_attempt

    def get_state(self) -> ParserState:
        """Get the current parser state."""
        return self.state

    def reset(self) -> None:
        """Reset the parser to initial state."""
        self.state = ParserState.IDLE
        self.session = RaidSession()
        self._boss_detected = False
        self._pending_wipe_time = None
        self.lines_processed = 0
        self._player_shields.clear()
        self._pending_hits.clear()
