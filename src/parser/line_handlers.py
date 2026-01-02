"""Line handlers for parsing specific ACT log line types.

Each handler parses a specific line type and extracts relevant data.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

from ..models.data_models import AbilityHit, DebuffApplied, Player, PlayerDeath
from .damage_calc import calculate_damage, is_damage_action, parse_flags


@dataclass
class ZoneChangeData:
    """Data extracted from a zone change line (Line 01)."""
    timestamp: datetime
    zone_id: str
    zone_name: str


@dataclass
class AddCombatantData:
    """Data extracted from an AddCombatant line (Line 03)."""
    timestamp: datetime
    id: str
    name: str
    job_id: str
    level: str
    max_hp: int
    is_player: bool  # True if ID starts with "10"


@dataclass
class ActorControlData:
    """Data extracted from an ActorControl line (Line 33)."""
    timestamp: datetime
    instance: str
    command: str
    data0: str
    data1: str
    data2: str
    data3: str


# ActorControl commands
COMMAND_COMMENCE = "40000001"      # Fight starts
COMMAND_VICTORY = "40000003"       # Victory
COMMAND_WIPE_FADEOUT = "40000005"  # Wipe (fade out)
COMMAND_RECOMMENCE = "40000006"    # Retry/recommence
COMMAND_BARRIER_UP = "40000011"    # Barrier up (reset ready)


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse an ACT timestamp string into a datetime object.

    Args:
        timestamp_str: Timestamp in format "2026-01-02T14:09:47.9710000-06:00"

    Returns:
        Parsed datetime object
    """
    # Remove the timezone offset for simpler parsing
    # The format is: 2026-01-02T14:09:47.9710000-06:00
    try:
        # Strip timezone and extra precision
        if "-" in timestamp_str[-6:] or "+" in timestamp_str[-6:]:
            # Has timezone offset
            base_ts = timestamp_str[:-6]  # Remove -06:00 or similar
        else:
            base_ts = timestamp_str

        # Handle variable precision in microseconds
        if "." in base_ts:
            date_part, time_part = base_ts.rsplit(".", 1)
            # Truncate or pad microseconds to 6 digits
            time_part = time_part[:6].ljust(6, "0")
            base_ts = f"{date_part}.{time_part}"

        return datetime.fromisoformat(base_ts)
    except (ValueError, IndexError):
        # Fallback to current time if parsing fails
        return datetime.now()


def is_player_id(actor_id: str) -> bool:
    """Check if an actor ID belongs to a player (starts with '10')."""
    return actor_id.upper().startswith("10")


def is_enemy_id(actor_id: str) -> bool:
    """Check if an actor ID belongs to an enemy/NPC (starts with '40')."""
    return actor_id.upper().startswith("40")


class LineHandlers:
    """Collection of handlers for different log line types."""

    @staticmethod
    def parse_line_01_zone_change(fields: list) -> Optional[ZoneChangeData]:
        """Parse a zone change line (Line 01).

        Format: 01|timestamp|zone_id|zone_name|hash

        Args:
            fields: List of pipe-separated fields

        Returns:
            ZoneChangeData if valid, None otherwise
        """
        if len(fields) < 4:
            return None

        return ZoneChangeData(
            timestamp=parse_timestamp(fields[1]),
            zone_id=fields[2],
            zone_name=fields[3],
        )

    @staticmethod
    def parse_line_03_add_combatant(fields: list) -> Optional[AddCombatantData]:
        """Parse an AddCombatant line (Line 03).

        Format: 03|timestamp|id|name|job|level|...|max_hp|...

        Args:
            fields: List of pipe-separated fields

        Returns:
            AddCombatantData if valid, None otherwise
        """
        if len(fields) < 12:
            return None

        actor_id = fields[2]
        name = fields[3]

        # Skip empty names or system entries
        if not name or name == "":
            return None

        # Parse max HP (field index 11 or 12 depending on format)
        try:
            max_hp = int(fields[11]) if fields[11] else 0
        except (ValueError, IndexError):
            max_hp = 0

        return AddCombatantData(
            timestamp=parse_timestamp(fields[1]),
            id=actor_id,
            name=name,
            job_id=fields[4] if len(fields) > 4 else "",
            level=fields[5] if len(fields) > 5 else "",
            max_hp=max_hp,
            is_player=is_player_id(actor_id),
        )

    @staticmethod
    def parse_line_21_22_ability(fields: list) -> Optional[AbilityHit]:
        """Parse an ability line (Line 21 single target, Line 22 AOE).

        Format: 21|timestamp|source_id|source_name|ability_id|ability_name|
                target_id|target_name|flags|damage|...|target_hp|target_max_hp|...

        Args:
            fields: List of pipe-separated fields

        Returns:
            AbilityHit if valid and represents boss->player damage, None otherwise
        """
        if len(fields) < 24:
            return None

        source_id = fields[2]
        source_name = fields[3]
        ability_id = fields[4]
        ability_name = fields[5]
        target_id = fields[6]
        target_name = fields[7]
        flags = fields[8]
        damage_raw = fields[9]

        # Only process enemy -> player abilities
        if not is_enemy_id(source_id) or not is_player_id(target_id):
            return None

        # Skip if no target name (targetless AOE)
        if not target_name:
            return None

        # Parse damage and flags
        damage = calculate_damage(damage_raw)
        damage_type, is_damage, is_critical, is_direct_hit, _ = parse_flags(flags)

        # Only include if it actually dealt damage
        if not is_damage_action(flags):
            return None

        return AbilityHit(
            timestamp=parse_timestamp(fields[1]),
            ability_id=ability_id,
            ability_name=ability_name,
            source_id=source_id,
            source_name=source_name,
            target_id=target_id,
            target_name=target_name,
            damage=damage,
            flags=flags,
            is_critical=is_critical,
            is_direct_hit=is_direct_hit,
        )

    @staticmethod
    def parse_line_25_death(fields: list) -> Optional[PlayerDeath]:
        """Parse a death line (Line 25).

        Format: 25|timestamp|target_id|target_name|source_id|source_name|hash

        Args:
            fields: List of pipe-separated fields

        Returns:
            PlayerDeath if valid player death, None otherwise
        """
        if len(fields) < 5:
            return None

        target_id = fields[2]
        target_name = fields[3]
        source_id = fields[4] if len(fields) > 4 else ""
        source_name = fields[5] if len(fields) > 5 else ""

        # Only track player deaths
        if not is_player_id(target_id):
            return None

        return PlayerDeath(
            timestamp=parse_timestamp(fields[1]),
            player_id=target_id,
            player_name=target_name,
            source_id=source_id,
            source_name=source_name,
        )

    @staticmethod
    def parse_line_26_buff(fields: list) -> Optional[DebuffApplied]:
        """Parse a buff/debuff application line (Line 26).

        Format: 26|timestamp|effect_id|effect_name|duration|source_id|source_name|
                target_id|target_name|stack_count|target_max_hp|source_max_hp|hash

        Args:
            fields: List of pipe-separated fields

        Returns:
            DebuffApplied if valid boss->player debuff, None otherwise
        """
        if len(fields) < 10:
            return None

        effect_id = fields[2]
        effect_name = fields[3]
        duration_str = fields[4]
        source_id = fields[5]
        source_name = fields[6]
        target_id = fields[7]
        target_name = fields[8]
        stack_count_str = fields[9]

        # Only process enemy -> player debuffs
        if not is_enemy_id(source_id) or not is_player_id(target_id):
            return None

        # Skip if no effect name
        if not effect_name:
            return None

        # Parse duration
        try:
            duration = float(duration_str)
        except (ValueError, TypeError):
            duration = 0.0

        # Parse stack count
        try:
            stacks = int(stack_count_str, 16) if stack_count_str else 0
        except ValueError:
            stacks = 0

        return DebuffApplied(
            timestamp=parse_timestamp(fields[1]),
            effect_id=effect_id,
            effect_name=effect_name,
            duration=duration,
            source_id=source_id,
            source_name=source_name,
            target_id=target_id,
            target_name=target_name,
            stacks=stacks,
        )

    @staticmethod
    def parse_line_33_actor_control(fields: list) -> Optional[ActorControlData]:
        """Parse an ActorControl line (Line 33).

        Format: 33|timestamp|instance|command|data0|data1|data2|data3|hash

        Args:
            fields: List of pipe-separated fields

        Returns:
            ActorControlData if valid, None otherwise
        """
        if len(fields) < 8:
            return None

        return ActorControlData(
            timestamp=parse_timestamp(fields[1]),
            instance=fields[2],
            command=fields[3],
            data0=fields[4],
            data1=fields[5],
            data2=fields[6],
            data3=fields[7],
        )

    @staticmethod
    def is_commence_command(data: ActorControlData) -> bool:
        """Check if this ActorControl is a fight commence signal."""
        return data.command.upper() == COMMAND_COMMENCE.upper()

    @staticmethod
    def is_wipe_command(data: ActorControlData) -> bool:
        """Check if this ActorControl is a wipe (fade out) signal."""
        return data.command.upper() == COMMAND_WIPE_FADEOUT.upper()

    @staticmethod
    def is_victory_command(data: ActorControlData) -> bool:
        """Check if this ActorControl is a victory signal."""
        return data.command.upper() == COMMAND_VICTORY.upper()

    @staticmethod
    def is_barrier_up_command(data: ActorControlData) -> bool:
        """Check if this ActorControl is a barrier up (reset ready) signal."""
        return data.command.upper() == COMMAND_BARRIER_UP.upper()

    @staticmethod
    def is_recommence_command(data: ActorControlData) -> bool:
        """Check if this ActorControl is a recommence signal."""
        return data.command.upper() == COMMAND_RECOMMENCE.upper()
