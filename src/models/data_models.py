"""Data models for FFXIV Battle Tracker."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ParserState(Enum):
    """State machine states for the log parser."""

    IDLE = "idle"
    IN_INSTANCE = "in_instance"
    IN_COMBAT = "in_combat"
    WIPE_PENDING = "wipe_pending"


class AttemptOutcome(Enum):
    """Possible outcomes for a fight attempt."""

    IN_PROGRESS = "in_progress"
    WIPE = "wipe"
    VICTORY = "victory"


@dataclass
class ActiveMitigation:
    """Represents an active mitigation buff on a player or debuff on a boss.

    Used for tracking mitigation state during combat to calculate unmitigated damage.
    """

    effect_id: str  # Hex string effect ID
    effect_name: str
    target_id: str  # Player ID for buffs, Boss ID for debuffs
    target_name: str
    source_id: str
    source_name: str
    start_time: datetime
    duration: float  # Duration in seconds
    mitigation_percent: float  # The mitigation percentage (e.g., 20 for 20%)
    is_boss_debuff: bool = False  # True if applied to boss (Reprisal, Feint, Addle)

    @property
    def end_time(self) -> datetime:
        """Calculate when this mitigation expires."""
        from datetime import timedelta

        return self.start_time + timedelta(seconds=self.duration)

    def is_active_at(self, timestamp: datetime) -> bool:
        """Check if this mitigation is active at the given timestamp."""
        return self.start_time <= timestamp < self.end_time


@dataclass
class Player:
    """Represents a player in the raid."""

    id: str  # e.g., "1075762D"
    name: str  # e.g., "Jalapeno Jeff"
    job_id: str = ""  # e.g., "21" for Astrologian
    job_name: str = ""  # e.g., "Astrologian"

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Player):
            return self.id == other.id
        return False


@dataclass
class AbilityHit:
    """Represents a boss ability hitting a player."""

    timestamp: datetime
    ability_id: str
    ability_name: str
    source_id: str
    source_name: str
    target_id: str
    target_name: str
    damage: int
    flags: str = ""
    is_critical: bool = False
    is_direct_hit: bool = False
    # New fields for unmitigated damage calculation
    unmitigated_damage: int | None = None  # Calculated from mitigation buffs
    hit_type: str | None = None  # "Magic", "Physical", or None if unknown

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "ability_id": self.ability_id,
            "ability_name": self.ability_name,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "damage": self.damage,
            "flags": self.flags,
            "is_critical": self.is_critical,
            "is_direct_hit": self.is_direct_hit,
            "unmitigated_damage": self.unmitigated_damage,
            "hit_type": self.hit_type,
        }


@dataclass
class DebuffApplied:
    """Represents a debuff applied to a player by the boss."""

    timestamp: datetime
    effect_id: str
    effect_name: str
    duration: float
    source_id: str
    source_name: str
    target_id: str
    target_name: str
    stacks: int = 0
    source_type: str = (
        "enemy"  # "enemy" for 40xxxxxx sources, "environment" for E0000000
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "effect_id": self.effect_id,
            "effect_name": self.effect_name,
            "duration": self.duration,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "stacks": self.stacks,
            "source_type": self.source_type,
        }


@dataclass
class PlayerDeath:
    """Represents a player death."""

    timestamp: datetime
    player_id: str
    player_name: str
    source_id: str = ""
    source_name: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "player_id": self.player_id,
            "player_name": self.player_name,
            "source_id": self.source_id,
            "source_name": self.source_name,
        }


@dataclass
class FightAttempt:
    """Represents a single attempt at a boss fight."""

    attempt_number: int
    start_time: datetime
    end_time: datetime | None = None
    outcome: AttemptOutcome = AttemptOutcome.IN_PROGRESS
    boss_name: str = ""
    first_damage_time: datetime | None = None  # When first player damage hits boss
    ability_hits: list[AbilityHit] = field(default_factory=list)
    debuffs_applied: list[DebuffApplied] = field(default_factory=list)
    deaths: list[PlayerDeath] = field(default_factory=list)
    # Active mitigations during this attempt (for unmitigated damage calculation)
    active_mitigations: list["ActiveMitigation"] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        """Calculate the duration of the attempt in seconds (from first damage)."""
        if self.end_time is None:
            return 0.0
        # Use first_damage_time if available for more accurate combat duration
        start = self.first_damage_time if self.first_damage_time else self.start_time
        return (self.end_time - start).total_seconds()

    def get_abilities_by_name(self) -> dict[str, list[AbilityHit]]:
        """Group ability hits by ability name."""
        result: dict[str, list[AbilityHit]] = {}
        for hit in self.ability_hits:
            if hit.ability_name not in result:
                result[hit.ability_name] = []
            result[hit.ability_name].append(hit)
        return result

    def get_hits_by_player(self) -> dict[str, list[AbilityHit]]:
        """Group ability hits by target player name."""
        result: dict[str, list[AbilityHit]] = {}
        for hit in self.ability_hits:
            if hit.target_name not in result:
                result[hit.target_name] = []
            result[hit.target_name].append(hit)
        return result

    def get_debuffs_by_player(self) -> dict[str, list[DebuffApplied]]:
        """Group debuffs by target player name."""
        result: dict[str, list[DebuffApplied]] = {}
        for debuff in self.debuffs_applied:
            if debuff.target_name not in result:
                result[debuff.target_name] = []
            result[debuff.target_name].append(debuff)
        return result

    def get_active_mitigations_at(
        self, timestamp: datetime, player_id: str
    ) -> list["ActiveMitigation"]:
        """Get all active mitigations affecting a player at a given timestamp.

        This includes:
        - Player buffs (mitigations applied directly to the player)
        - Boss debuffs (mitigations applied to the boss that reduce damage dealt)

        Args:
            timestamp: The time to check for active mitigations
            player_id: The player ID to check mitigations for

        Returns:
            List of ActiveMitigation objects that are active at the timestamp
        """
        active = []
        for mit in self.active_mitigations:
            if mit.is_active_at(timestamp):
                # Include player buffs that target this player
                if not mit.is_boss_debuff and mit.target_id == player_id:
                    active.append(mit)
                # Include all boss debuffs (they affect all player damage taken)
                elif mit.is_boss_debuff:
                    active.append(mit)
        return active

    @property
    def timeline_start(self) -> datetime:
        """Get the reference time for timeline (first damage or start time)."""
        return self.first_damage_time if self.first_damage_time else self.start_time

    def calculate_unmitigated_damage(self) -> None:
        """Calculate unmitigated damage for all ability hits in this attempt.

        This method updates each AbilityHit's unmitigated_damage field based on
        the active mitigations at the time of the hit.
        """
        # Import here to avoid circular imports
        from ..parser.mitigation_calc import calculate_unmitigated_damage

        for hit in self.ability_hits:
            if hit.damage > 0:
                # Get active mitigations at the time of this hit
                active_mits = self.get_active_mitigations_at(
                    hit.timestamp, hit.target_id
                )
                # Calculate unmitigated damage
                hit.unmitigated_damage = calculate_unmitigated_damage(
                    hit.damage, active_mits
                )
            else:
                # No damage, no unmitigated damage
                hit.unmitigated_damage = 0

    def _add_relative_time(self, event_dict: dict, event_timestamp: datetime) -> dict:
        """Add relative time (seconds from first damage) to an event dict."""
        relative_seconds = (event_timestamp - self.timeline_start).total_seconds()
        event_dict["relative_time_seconds"] = max(0, relative_seconds)
        return event_dict

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        # Add relative time to each event
        ability_hits_with_time = [
            self._add_relative_time(hit.to_dict(), hit.timestamp)
            for hit in self.ability_hits
        ]
        debuffs_with_time = [
            self._add_relative_time(debuff.to_dict(), debuff.timestamp)
            for debuff in self.debuffs_applied
        ]
        deaths_with_time = [
            self._add_relative_time(death.to_dict(), death.timestamp)
            for death in self.deaths
        ]

        return {
            "attempt_number": self.attempt_number,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "outcome": self.outcome.value,
            "boss_name": self.boss_name,
            "duration_seconds": self.duration_seconds,
            "ability_hits": ability_hits_with_time,
            "debuffs_applied": debuffs_with_time,
            "deaths": deaths_with_time,
            "summary": {
                "total_hits": len(self.ability_hits),
                "total_debuffs": len(self.debuffs_applied),
                "total_deaths": len(self.deaths),
                "unique_abilities": len(self.get_abilities_by_name()),
            },
        }


@dataclass
class Fight:
    """Represents a single boss fight encounter (may have multiple attempts)."""

    fight_id: int
    zone_id: str
    zone_name: str
    boss_name: str = ""
    start_time: datetime | None = None
    attempts: list[FightAttempt] = field(default_factory=list)
    players: dict[str, "Player"] = field(default_factory=dict)

    @property
    def current_attempt(self) -> FightAttempt | None:
        """Get the current (most recent) attempt."""
        if self.attempts:
            return self.attempts[-1]
        return None

    @property
    def completed_attempts(self) -> list[FightAttempt]:
        """Get only completed attempts (excludes in_progress)."""
        return [a for a in self.attempts if a.outcome != AttemptOutcome.IN_PROGRESS]

    @property
    def total_wipes(self) -> int:
        """Count total number of wipes."""
        return sum(1 for a in self.attempts if a.outcome == AttemptOutcome.WIPE)

    @property
    def total_victories(self) -> int:
        """Count total number of victories."""
        return sum(1 for a in self.attempts if a.outcome == AttemptOutcome.VICTORY)

    @property
    def total_deaths(self) -> int:
        """Count total number of deaths across completed attempts."""
        return sum(len(a.deaths) for a in self.completed_attempts)

    def start_new_attempt(self, start_time: datetime) -> FightAttempt:
        """Start a new fight attempt."""
        attempt = FightAttempt(
            attempt_number=len(self.attempts) + 1,
            start_time=start_time,
            boss_name=self.boss_name,
        )
        self.attempts.append(attempt)
        return attempt

    def finalize_current_attempt(
        self, end_time: datetime, outcome: AttemptOutcome
    ) -> None:
        """Finalize the current attempt with an outcome."""
        if self.current_attempt:
            self.current_attempt.end_time = end_time
            self.current_attempt.outcome = outcome

    def get_cross_attempt_stats(self) -> dict:
        """Generate statistics across completed attempts in this fight."""
        all_deaths: dict[str, int] = {}  # player -> count

        for attempt in self.completed_attempts:
            for death in attempt.deaths:
                if death.player_name not in all_deaths:
                    all_deaths[death.player_name] = 0
                all_deaths[death.player_name] += 1

        return {
            "total_attempts": len(self.completed_attempts),
            "total_wipes": self.total_wipes,
            "total_victories": self.total_victories,
            "deaths_by_player": all_deaths,
        }

    def add_player(self, player: "Player") -> None:
        """Add a player to this fight."""
        self.players[player.id] = player

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "fight_id": self.fight_id,
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "boss_name": self.boss_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "attempts": [attempt.to_dict() for attempt in self.completed_attempts],
            "total_attempts": len(self.completed_attempts),
            "total_wipes": self.total_wipes,
            "total_victories": self.total_victories,
            "total_deaths": self.total_deaths,
            "players": {
                pid: {
                    "id": p.id,
                    "name": p.name,
                    "job_id": p.job_id,
                    "job_name": p.job_name,
                }
                for pid, p in self.players.items()
            },
        }


@dataclass
class RaidSession:
    """Represents a raid session with multiple fights."""

    start_time: datetime | None = None
    players: dict[str, Player] = field(default_factory=dict)
    fights: list[Fight] = field(default_factory=list)

    # Legacy properties for backwards compatibility
    @property
    def zone_id(self) -> str:
        """Get zone_id of current fight."""
        return self.current_fight.zone_id if self.current_fight else ""

    @property
    def zone_name(self) -> str:
        """Get zone_name of current fight."""
        return self.current_fight.zone_name if self.current_fight else ""

    @property
    def boss_name(self) -> str:
        """Get boss_name of current fight."""
        return self.current_fight.boss_name if self.current_fight else ""

    @property
    def attempts(self) -> list[FightAttempt]:
        """Get all completed attempts across all fights."""
        all_attempts = []
        for fight in self.fights:
            all_attempts.extend(fight.completed_attempts)
        return all_attempts

    @property
    def current_fight(self) -> Fight | None:
        """Get the current (most recent) fight."""
        if self.fights:
            return self.fights[-1]
        return None

    @property
    def current_attempt(self) -> FightAttempt | None:
        """Get the current (most recent) attempt."""
        if self.current_fight:
            return self.current_fight.current_attempt
        return None

    @property
    def total_wipes(self) -> int:
        """Count total number of wipes across all fights."""
        return sum(f.total_wipes for f in self.fights)

    @property
    def total_victories(self) -> int:
        """Count total number of victories across all fights."""
        return sum(f.total_victories for f in self.fights)

    def get_player_by_id(self, player_id: str) -> Player | None:
        """Look up a player by their ID."""
        return self.players.get(player_id)

    def add_player(self, player: Player) -> None:
        """Add a player to the session."""
        self.players[player.id] = player

    def start_new_fight(
        self, zone_id: str, zone_name: str, start_time: datetime
    ) -> Fight:
        """Start a new fight in a new zone."""
        fight = Fight(
            fight_id=len(self.fights) + 1,
            zone_id=zone_id,
            zone_name=zone_name,
            start_time=start_time,
        )
        self.fights.append(fight)
        return fight

    def start_new_attempt(self, start_time: datetime) -> FightAttempt:
        """Start a new fight attempt in the current fight."""
        if not self.current_fight:
            raise RuntimeError("No current fight to start attempt in")
        return self.current_fight.start_new_attempt(start_time)

    def finalize_current_attempt(
        self, end_time: datetime, outcome: AttemptOutcome
    ) -> None:
        """Finalize the current attempt with an outcome."""
        if self.current_fight:
            self.current_fight.finalize_current_attempt(end_time, outcome)

    def get_cross_attempt_stats(self) -> dict:
        """Generate statistics across all completed attempts in all fights."""
        all_ability_hits: dict[str, dict[str, int]] = {}  # ability -> player -> count
        all_deaths: dict[str, int] = {}  # player -> count
        all_debuffs: dict[str, dict[str, int]] = {}  # debuff -> player -> count

        for fight in self.fights:
            for attempt in fight.completed_attempts:
                # Count ability hits per player per ability
                for hit in attempt.ability_hits:
                    if hit.ability_name not in all_ability_hits:
                        all_ability_hits[hit.ability_name] = {}
                    if hit.target_name not in all_ability_hits[hit.ability_name]:
                        all_ability_hits[hit.ability_name][hit.target_name] = 0
                    all_ability_hits[hit.ability_name][hit.target_name] += 1

                # Count deaths per player
                for death in attempt.deaths:
                    if death.player_name not in all_deaths:
                        all_deaths[death.player_name] = 0
                    all_deaths[death.player_name] += 1

                # Count debuffs per player
                for debuff in attempt.debuffs_applied:
                    if debuff.effect_name not in all_debuffs:
                        all_debuffs[debuff.effect_name] = {}
                    if debuff.target_name not in all_debuffs[debuff.effect_name]:
                        all_debuffs[debuff.effect_name][debuff.target_name] = 0
                    all_debuffs[debuff.effect_name][debuff.target_name] += 1

        return {
            "total_fights": len(self.fights),
            "total_attempts": len(self.attempts),
            "total_wipes": self.total_wipes,
            "total_victories": self.total_victories,
            "ability_hits_by_player": all_ability_hits,
            "deaths_by_player": all_deaths,
            "debuffs_by_player": all_debuffs,
        }

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "players": {
                pid: {
                    "id": p.id,
                    "name": p.name,
                    "job_id": p.job_id,
                    "job_name": p.job_name,
                }
                for pid, p in self.players.items()
            },
            "fights": [fight.to_dict() for fight in self.fights],
            "cross_attempt_stats": self.get_cross_attempt_stats(),
            # Legacy fields for backwards compatibility
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "boss_name": self.boss_name,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
        }
