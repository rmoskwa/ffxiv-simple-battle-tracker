"""Data models for FFXIV Battle Tracker."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


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
class Player:
    """Represents a player in the raid."""
    id: str           # e.g., "1075762D"
    name: str         # e.g., "Jalapeno Jeff"

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
    flags: str = ""        # for crit/direct hit info
    is_critical: bool = False
    is_direct_hit: bool = False

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
    end_time: Optional[datetime] = None
    outcome: AttemptOutcome = AttemptOutcome.IN_PROGRESS
    boss_name: str = ""
    ability_hits: List[AbilityHit] = field(default_factory=list)
    debuffs_applied: List[DebuffApplied] = field(default_factory=list)
    deaths: List[PlayerDeath] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        """Calculate the duration of the attempt in seconds."""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()

    def get_abilities_by_name(self) -> Dict[str, List[AbilityHit]]:
        """Group ability hits by ability name."""
        result: Dict[str, List[AbilityHit]] = {}
        for hit in self.ability_hits:
            if hit.ability_name not in result:
                result[hit.ability_name] = []
            result[hit.ability_name].append(hit)
        return result

    def get_hits_by_player(self) -> Dict[str, List[AbilityHit]]:
        """Group ability hits by target player name."""
        result: Dict[str, List[AbilityHit]] = {}
        for hit in self.ability_hits:
            if hit.target_name not in result:
                result[hit.target_name] = []
            result[hit.target_name].append(hit)
        return result

    def get_debuffs_by_player(self) -> Dict[str, List[DebuffApplied]]:
        """Group debuffs by target player name."""
        result: Dict[str, List[DebuffApplied]] = {}
        for debuff in self.debuffs_applied:
            if debuff.target_name not in result:
                result[debuff.target_name] = []
            result[debuff.target_name].append(debuff)
        return result

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "attempt_number": self.attempt_number,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "outcome": self.outcome.value,
            "boss_name": self.boss_name,
            "duration_seconds": self.duration_seconds,
            "ability_hits": [hit.to_dict() for hit in self.ability_hits],
            "debuffs_applied": [debuff.to_dict() for debuff in self.debuffs_applied],
            "deaths": [death.to_dict() for death in self.deaths],
            "summary": {
                "total_hits": len(self.ability_hits),
                "total_debuffs": len(self.debuffs_applied),
                "total_deaths": len(self.deaths),
                "unique_abilities": len(self.get_abilities_by_name()),
            }
        }


@dataclass
class RaidSession:
    """Represents a raid session with multiple attempts."""
    zone_id: str = ""
    zone_name: str = ""
    boss_name: str = ""
    start_time: Optional[datetime] = None
    players: Dict[str, Player] = field(default_factory=dict)
    attempts: List[FightAttempt] = field(default_factory=list)

    @property
    def current_attempt(self) -> Optional[FightAttempt]:
        """Get the current (most recent) attempt."""
        if self.attempts:
            return self.attempts[-1]
        return None

    @property
    def total_wipes(self) -> int:
        """Count total number of wipes."""
        return sum(1 for a in self.attempts if a.outcome == AttemptOutcome.WIPE)

    @property
    def total_victories(self) -> int:
        """Count total number of victories."""
        return sum(1 for a in self.attempts if a.outcome == AttemptOutcome.VICTORY)

    def get_player_by_id(self, player_id: str) -> Optional[Player]:
        """Look up a player by their ID."""
        return self.players.get(player_id)

    def add_player(self, player: Player) -> None:
        """Add a player to the session."""
        self.players[player.id] = player

    def start_new_attempt(self, start_time: datetime) -> FightAttempt:
        """Start a new fight attempt."""
        attempt = FightAttempt(
            attempt_number=len(self.attempts) + 1,
            start_time=start_time,
            boss_name=self.boss_name,
        )
        self.attempts.append(attempt)
        return attempt

    def finalize_current_attempt(self, end_time: datetime, outcome: AttemptOutcome) -> None:
        """Finalize the current attempt with an outcome."""
        if self.current_attempt:
            self.current_attempt.end_time = end_time
            self.current_attempt.outcome = outcome

    def get_cross_attempt_stats(self) -> dict:
        """Generate statistics across all attempts."""
        all_ability_hits: Dict[str, Dict[str, int]] = {}  # ability -> player -> count
        all_deaths: Dict[str, int] = {}  # player -> count
        all_debuffs: Dict[str, Dict[str, int]] = {}  # debuff -> player -> count

        for attempt in self.attempts:
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
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "boss_name": self.boss_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "players": {pid: {"id": p.id, "name": p.name} for pid, p in self.players.items()},
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "cross_attempt_stats": self.get_cross_attempt_stats(),
        }
