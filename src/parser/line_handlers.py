"""Line handlers for parsing specific ACT log line types.

Each handler parses a specific line type and extracts relevant data.
"""

from dataclasses import dataclass
from datetime import datetime

from ..data.mitigation_db import (
    get_boss_debuff_by_effect_id,
    get_mitigation_by_effect_id,
)
from ..models.data_models import (
    AbilityHit,
    ActiveMitigation,
    DebuffApplied,
    PlayerDeath,
    TargetingEvent,
)
from .damage_calc import calculate_damage, is_damage_action, parse_flags

# Known player pet names - these have IDs starting with "40" but are player-controlled
# and should be excluded from boss debuff tracking.
PLAYER_PET_NAMES = {
    # Scholar pets
    "eos",
    "selene",
    "seraph",
    # Astrologian
    "earthly star",
    # Summoner pets
    "carbuncle",
    "emerald carbuncle",
    "topaz carbuncle",
    "ruby carbuncle",
    "ifrit-egi",
    "titan-egi",
    "garuda-egi",
    "demi-bahamut",
    "demi-phoenix",
    "solar bahamut",
    # Machinist
    "automaton queen",
    "rook autoturret",
}


# Job ID to job name mapping (hex string -> job name). Most are unused, but included for
# completeness/potential future use.
JOB_NAMES = {
    "00": "Adventurer",
    # Base classes
    "01": "Gladiator",
    "02": "Pugilist",
    "03": "Marauder",
    "04": "Lancer",
    "05": "Archer",
    "06": "Conjurer",
    "07": "Thaumaturge",
    "1A": "Arcanist",
    "1D": "Rogue",
    # Tanks
    "13": "Paladin",
    "15": "Warrior",
    "20": "Dark Knight",
    "25": "Gunbreaker",
    # Healers
    "18": "White Mage",
    "1C": "Scholar",
    "21": "Astrologian",
    "28": "Sage",
    # Melee DPS
    "14": "Monk",
    "16": "Dragoon",
    "1E": "Ninja",
    "22": "Samurai",
    "27": "Reaper",
    "29": "Viper",
    # Physical Ranged DPS
    "17": "Bard",
    "1F": "Machinist",
    "26": "Dancer",
    # Magical Ranged DPS
    "19": "Black Mage",
    "1B": "Summoner",
    "23": "Red Mage",
    "2A": "Pictomancer",
    # Crafters
    "08": "Carpenter",
    "09": "Blacksmith",
    "0A": "Armorer",
    "0B": "Goldsmith",
    "0C": "Leatherworker",
    "0D": "Weaver",
    "0E": "Alchemist",
    "0F": "Culinarian",
    # Gatherers
    "10": "Miner",
    "11": "Botanist",
    "12": "Fisher",
    # Limited jobs
    "24": "Blue Mage",
}

# Head marker ID to name mapping
# Source: logGuide.md (cactbot documentation) + cactbot fight triggers
# Note: Since patch 5.2, high-end content uses offset headmarkers where IDs are
# shifted per-instance. We track raw IDs which are useful for identifying mechanics
# within a single log/session.
HEAD_MARKER_NAMES = {
    # Common mechanics (widely used)
    "0017": "Spread",
    "0064": "Stack",
    "003E": "Stack",
    "00A1": "Stack",
    "0048": "Stack",
    "005D": "Tank Stack",
    "0057": "Flare",
    "0028": "Earth Shaker",
    "004B": "Acceleration Bomb",
    "0061": "Chain Tether",
    "0037": "Red Dorito",
    # Spread circles
    "0039": "Spread (Purple Large)",
    "008A": "Spread (Orange Large)",
    "008B": "Spread (Purple Small)",
    "0060": "Spread (Orange Small)",
    "0078": "Spread (Orange Large)",
    "00A9": "Spread (Orange Small)",
    "00BD": "Spread (Purple Giant)",
    "004C": "Purple Fire Circle",
    # Prey/Target markers
    "0001": "Prey (Orange)",
    "0002": "Prey (Orange)",
    "0004": "Prey (Orange)",
    "000E": "Prey (Blue)",
    "001E": "Prey Sphere (Orange)",
    "001F": "Prey Sphere (Blue)",
    "005C": "Prey (Dark)",
    "0076": "Prey (Dark)",
    "0087": "Prey Sphere (Blue)",
    # Meteor markers
    "0007": "Green Meteor",
    "0008": "Ghost Meteor",
    "0009": "Red Meteor",
    "000A": "Yellow Meteor",
    "015A": "Meteor",
    # Pinwheels
    "0046": "Green Pinwheel",
    "00AE": "Blue Pinwheel",
    # Limit cut (common in ultimates)
    "004F": "Limit Cut 1",
    "0050": "Limit Cut 2",
    "0051": "Limit Cut 3",
    "0052": "Limit Cut 4",
    "0053": "Limit Cut 5",
    "0054": "Limit Cut 6",
    "0055": "Limit Cut 7",
    "0056": "Limit Cut 8",
    # Misc
    "000D": "Devour Flower",
    "0010": "Teal Crystal",
    "0011": "Heavenly Laser",
    "001C": "Gravity Puddle",
    "0032": "Sword Marker 1",
    "0033": "Sword Marker 2",
    "0034": "Sword Marker 3",
    "0035": "Sword Marker 4",
    "0065": "Spread Bubble",
    "006E": "Levinbolt",
    "007B": "Scatter",
    "007C": "Turn Away",
    "007E": "Green Crystal",
    "0083": "Sword Meteor",
    "008E": "Death From Above",
    "008F": "Death From Below",
    "00AB": "Green Poison",
    "00AC": "Reprobation Tether",
    "00B9": "Yellow Triangle",
    "00BA": "Orange Square",
    "00BB": "Blue Square",
    "00BF": "Granite Gaol",
    # Playstation markers (used in TOP, etc.)
    "01A0": "Circle (Playstation)",
    "01A1": "Triangle (Playstation)",
    "01A2": "Square (Playstation)",
    "01A3": "Cross (Playstation)",
    # Tank busters
    "0157": "Tank Buster",
    "01D4": "Duality of Death",
    # Other ultimates
    "014A": "Defamation",
    "01B3": "Comet Marker",
}


def get_head_marker_name(marker_id: str) -> str:
    """Get human-readable name for a head marker ID."""
    marker_id_upper = marker_id.upper()
    return HEAD_MARKER_NAMES.get(marker_id_upper, f"Head Marker 0x{marker_id_upper}")


def get_job_name(job_id: str) -> str:
    """Get job name from job ID hex string."""
    return JOB_NAMES.get(job_id.upper(), "Unknown")


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


@dataclass
class EffectResultData:
    """Data extracted from an EffectResult line (Line 37).

    This line confirms when ability effects have been applied to a target.
    It contains the sequence ID referencing the original ability line (21/22)
    and the target's current HP/shield values after the effect.
    """

    timestamp: datetime
    target_id: str
    target_name: str
    sequence_id: str
    current_hp: int
    max_hp: int
    current_mp: int
    max_mp: int
    shield_percent: int  # Current shield as % of max HP (0-100)


# ActorControl commands
COMMAND_COMMENCE = "40000001"  # Fight starts
COMMAND_VICTORY = "40000003"  # Victory
COMMAND_WIPE_FADEOUT = "40000005"  # Wipe (fade out)
COMMAND_RECOMMENCE = "40000006"  # Retry/recommence
COMMAND_BARRIER_UP = "40000011"  # Barrier up (reset ready)


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
    def parse_line_01_zone_change(fields: list) -> ZoneChangeData | None:
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
    def parse_line_03_add_combatant(fields: list) -> AddCombatantData | None:
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
    def parse_line_21_22_ability(
        fields: list, shield_percent_before: int = 0
    ) -> AbilityHit | None:
        """Parse an ability line (Line 21 single target, Line 22 AOE).

        Format: 21|timestamp|source_id|source_name|ability_id|ability_name|
                target_id|target_name|flags|damage|...|target_hp|target_max_hp|...
                ...|sequence_id|target_index|target_count|...

        The sequence_id (field 43) links this ability to the corresponding
        EffectResult line (37) for shield absorption tracking.

        Args:
            fields: List of pipe-separated fields
            shield_percent_before: The target's shield % before this hit

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

        # Skip auto-attacks (not relevant for tracking major boss mechanics)
        if ability_name.lower() == "attack":
            return None

        # Parse damage and flags
        damage = calculate_damage(damage_raw)
        damage_type, is_damage, is_critical, is_direct_hit, _ = parse_flags(flags)

        # Only include if it actually dealt damage
        if not is_damage_action(flags):
            return None

        # Extract sequence_id (field 44) for correlating with line 37
        # Format: ...source_heading|sequence_id|target_index|target_count|...
        sequence_id = ""
        if len(fields) > 44:
            sequence_id = fields[44]

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
            sequence_id=sequence_id,
            shield_percent_before=shield_percent_before,
        )

    @staticmethod
    def parse_player_damage_timestamp(fields: list) -> datetime | None:
        """Check if this is a player->boss damage ability and return timestamp.

        Used to detect the first player damage to start the fight timeline.

        Args:
            fields: List of pipe-separated fields from Line 21/22

        Returns:
            Timestamp if this is player->boss damage, None otherwise
        """
        if len(fields) < 10:
            return None

        source_id = fields[2]
        target_id = fields[6]
        flags = fields[8]

        # Only process player -> enemy abilities
        if not is_player_id(source_id) or not is_enemy_id(target_id):
            return None

        # Check if it actually dealt damage
        if not is_damage_action(flags):
            return None

        return parse_timestamp(fields[1])

    @staticmethod
    def parse_line_25_death(fields: list) -> PlayerDeath | None:
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
    def parse_line_26_buff(fields: list) -> DebuffApplied | None:
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

        # Only process enemy/environment -> player debuffs
        # E0000000 is the "environment" source for mechanic-based debuffs
        is_valid_source = is_enemy_id(source_id) or source_id.upper() == "E0000000"
        if not is_valid_source or not is_player_id(target_id):
            return None

        # Skip player pets (they have "40" IDs but are player-controlled)
        if source_name.lower() in PLAYER_PET_NAMES:
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

        # Determine source type
        source_type = "environment" if source_id.upper() == "E0000000" else "enemy"

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
            source_type=source_type,
        )

    @staticmethod
    def parse_line_33_actor_control(fields: list) -> ActorControlData | None:
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

    @staticmethod
    def parse_line_26_mitigation_buff(fields: list) -> ActiveMitigation | None:
        """Parse a Line 26 for player mitigation buffs.

        This captures friendly → player buffs that provide mitigation
        (e.g., Rampart, Sentinel, Sacred Soil on the player).

        Format: 26|timestamp|effect_id|effect_name|duration|source_id|source_name|
                target_id|target_name|stack_count|target_max_hp|source_max_hp|hash

        Args:
            fields: List of pipe-separated fields

        Returns:
            ActiveMitigation if this is a known mitigation buff, None otherwise
        """
        if len(fields) < 10:
            return None

        effect_id = fields[2].upper()
        effect_name = fields[3]
        duration_str = fields[4]
        source_id = fields[5]
        target_id = fields[7]
        target_name = fields[8]

        # Only process player → player or friendly → player buffs
        # (source is player, target is player)
        if not is_player_id(target_id):
            return None

        # Check if this effect is a known mitigation buff
        mitigation = get_mitigation_by_effect_id(effect_id)
        if not mitigation:
            return None

        # Parse duration
        try:
            duration = float(duration_str)
        except (ValueError, TypeError):
            duration = 0.0

        # Skip zero-duration buffs (they're not real mitigations)
        if duration <= 0:
            return None

        return ActiveMitigation(
            effect_id=effect_id,
            effect_name=effect_name or mitigation.name,
            target_id=target_id,
            target_name=target_name,
            source_id=source_id,
            source_name=fields[6],
            start_time=parse_timestamp(fields[1]),
            duration=duration,
            mitigation_percent=mitigation.mitigation_percent,
            is_boss_debuff=False,
        )

    @staticmethod
    def parse_line_26_boss_debuff(fields: list) -> ActiveMitigation | None:
        """Parse a Line 26 for boss debuffs (mitigations applied TO the boss).

        This captures player → boss debuffs that reduce boss damage output
        (e.g., Reprisal, Feint, Addle applied to the boss).

        Format: 26|timestamp|effect_id|effect_name|duration|source_id|source_name|
                target_id|target_name|stack_count|target_max_hp|source_max_hp|hash

        Args:
            fields: List of pipe-separated fields

        Returns:
            ActiveMitigation if this is a known boss debuff, None otherwise
        """
        if len(fields) < 10:
            return None

        effect_id = fields[2].upper()
        effect_name = fields[3]
        duration_str = fields[4]
        source_id = fields[5]
        target_id = fields[7]
        target_name = fields[8]

        # Only process player → enemy debuffs
        if not is_player_id(source_id) or not is_enemy_id(target_id):
            return None

        # Check if this effect is a known boss debuff (Reprisal, Feint, Addle, etc.)
        debuff = get_boss_debuff_by_effect_id(effect_id)
        if not debuff:
            return None

        # Parse duration
        try:
            duration = float(duration_str)
        except (ValueError, TypeError):
            duration = 0.0

        if duration <= 0:
            return None

        return ActiveMitigation(
            effect_id=effect_id,
            effect_name=effect_name or debuff.name,
            target_id=target_id,
            target_name=target_name,
            source_id=source_id,
            source_name=fields[6],
            start_time=parse_timestamp(fields[1]),
            duration=duration,
            mitigation_percent=debuff.mitigation_percent,
            is_boss_debuff=True,
        )

    @staticmethod
    def parse_line_37_effect_result(fields: list) -> EffectResultData | None:
        """Parse an EffectResult line (Line 37).

        This line is sent when ability effects are applied to a target.
        It contains the sequence ID linking back to the ability line (21/22)
        and the target's current HP/shield values after the effect.

        Format: 37|timestamp|id|name|sequenceId|currentHp|maxHp|currentMp|maxMp|
                currentShield|?|x|y|z|heading|...

        The currentShield field is the shield percentage (0-100) of max HP.

        Args:
            fields: List of pipe-separated fields

        Returns:
            EffectResultData if valid player effect result, None otherwise
        """
        if len(fields) < 10:
            return None

        target_id = fields[2]
        target_name = fields[3]
        sequence_id = fields[4]

        # Only track player effect results
        if not is_player_id(target_id):
            return None

        # Skip if no target name
        if not target_name:
            return None

        # Parse HP values
        try:
            current_hp = int(fields[5]) if fields[5] else 0
            max_hp = int(fields[6]) if fields[6] else 0
            current_mp = int(fields[7]) if fields[7] else 0
            max_mp = int(fields[8]) if fields[8] else 0
        except ValueError:
            current_hp = 0
            max_hp = 0
            current_mp = 0
            max_mp = 0

        # Parse shield percentage (field 9)
        # This is an integer 0-100 representing shield % of max HP
        try:
            shield_percent = int(fields[9]) if fields[9] else 0
        except ValueError:
            shield_percent = 0

        return EffectResultData(
            timestamp=parse_timestamp(fields[1]),
            target_id=target_id,
            target_name=target_name,
            sequence_id=sequence_id,
            current_hp=current_hp,
            max_hp=max_hp,
            current_mp=current_mp,
            max_mp=max_mp,
            shield_percent=shield_percent,
        )

    @staticmethod
    def parse_line_20_starts_casting(fields: list) -> TargetingEvent | None:
        """Parse a StartsCasting line (Line 20) for boss->player targeting.

        Format: 20|timestamp|source_id|source_name|ability_id|ability_name|
                target_id|target_name|cast_time|x|y|z|heading|hash

        This tracks which player the boss is initially targeting with a cast,
        before the ability actually resolves.

        Args:
            fields: List of pipe-separated fields

        Returns:
            TargetingEvent if valid boss->player cast, None otherwise
        """
        if len(fields) < 8:
            return None

        source_id = fields[2]
        source_name = fields[3]
        ability_id = fields[4]
        ability_name = fields[5]
        target_id = fields[6]
        target_name = fields[7]

        # Only process enemy -> player casts
        if not is_enemy_id(source_id) or not is_player_id(target_id):
            return None

        # Skip self-casts (boss casting on itself)
        if source_id == target_id:
            return None

        # Skip if no ability name or target name
        if not ability_name or not target_name:
            return None

        # Skip auto-attacks
        if ability_name.lower() == "attack":
            return None

        return TargetingEvent(
            timestamp=parse_timestamp(fields[1]),
            source_id=source_id,
            source_name=source_name,
            target_id=target_id,
            target_name=target_name,
            ability_id=ability_id,
            ability_name=ability_name,
            event_type="cast_target",
        )

    @staticmethod
    def parse_line_27_head_marker(fields: list) -> TargetingEvent | None:
        """Parse a HeadMarker line (Line 27) for player targeting.

        Format: 27|timestamp|target_id|target_name|?|?|marker_id|data0|...

        This tracks head markers (visual indicators) placed on players for mechanics.

        Args:
            fields: List of pipe-separated fields

        Returns:
            TargetingEvent if valid player head marker, None otherwise
        """
        if len(fields) < 7:
            return None

        target_id = fields[2]
        target_name = fields[3]
        marker_id = fields[6]

        # Only process player head markers
        if not is_player_id(target_id):
            return None

        # Skip if no target name or marker ID
        if not target_name or not marker_id:
            return None

        # Get human-readable marker name
        marker_name = get_head_marker_name(marker_id)

        return TargetingEvent(
            timestamp=parse_timestamp(fields[1]),
            source_id="",  # Head markers don't have a source in the log
            source_name="",
            target_id=target_id,
            target_name=target_name,
            ability_id=marker_id,
            ability_name=marker_name,
            event_type="head_marker",
        )
