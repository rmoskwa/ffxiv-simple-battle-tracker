"""Damage calculation utilities for FFXIV log parsing.

Based on the ACT log guide documentation for ability damage decoding.
The damage value in ability log lines is encoded and needs special handling.
"""

# Damage type flags (rightmost byte)
DAMAGE_FLAG_MISS = 0x01
DAMAGE_FLAG_DAMAGE = 0x03
DAMAGE_FLAG_HEAL = 0x04
DAMAGE_FLAG_BLOCKED = 0x05
DAMAGE_FLAG_PARRIED = 0x06
DAMAGE_FLAG_INSTANT_DEATH = 0x33

# Severity flags (second byte from right)
SEVERITY_CRIT = 0x20
SEVERITY_DIRECT_HIT = 0x40
SEVERITY_CRIT_DIRECT_HIT = 0x60

# Damage bitmasks
DAMAGE_HALLOWED = 0x0100  # No damage (invuln)
DAMAGE_BIG = 0x4000  # "A lot" of damage - special calculation needed


def calculate_damage(damage_str: str) -> int:
    """Calculate the actual damage value from the encoded hex string.

    The damage value in the log is not literal. The calculation:
    1. Left-extend to 8 hex chars (4 bytes)
    2. If 0x4000 mask is present (byte C is 0x40), use special calculation
    3. Otherwise, first 2 bytes (4 chars) are the damage

    Args:
        damage_str: Hex string of the damage value (e.g., "2D00000" or "423F400F")

    Returns:
        The actual damage value as an integer
    """
    if not damage_str or damage_str == "0":
        return 0

    # Left-extend to 8 characters (4 bytes)
    damage_hex = damage_str.upper().zfill(8)

    try:
        damage_value = int(damage_hex, 16)
    except ValueError:
        return 0

    # Check for "big damage" mask (0x4000 in the position)
    # The bytes are ABCD where if C contains 0x40, it's big damage
    byte_c = (damage_value >> 8) & 0xFF

    if byte_c & 0x40:  # Big damage flag
        # For big damage: bytes ABCD where C is 0x40
        # Total damage = D A B as three bytes
        byte_a = (damage_value >> 24) & 0xFF
        byte_b = (damage_value >> 16) & 0xFF
        byte_d = damage_value & 0xFF

        # Combine as D A B (D is high byte, B is low byte)
        actual_damage = (byte_d << 16) | (byte_a << 8) | byte_b
    else:
        # Normal damage: first 2 bytes (4 chars) are the damage
        actual_damage = (damage_value >> 16) & 0xFFFF

    return actual_damage


def parse_flags(flags_str: str) -> tuple[int, bool, bool, bool, bool]:
    """Parse the flags field from an ability line.

    Args:
        flags_str: Hex string of the flags value (e.g., "750003" or "430003")

    Returns:
        Tuple of (damage_type, is_damage, is_critical, is_direct_hit,
        is_blocked_or_parried)
    """
    if not flags_str or flags_str == "0":
        return (0, False, False, False, False)

    try:
        flags_value = int(flags_str, 16)
    except ValueError:
        return (0, False, False, False, False)

    # Rightmost byte is the damage type
    damage_type = flags_value & 0xFF

    # Check if this is actual damage
    is_damage = damage_type == DAMAGE_FLAG_DAMAGE

    # Check severity (second byte from right)
    severity = (flags_value >> 8) & 0xFF
    is_critical = (severity & SEVERITY_CRIT) != 0
    is_direct_hit = (severity & SEVERITY_DIRECT_HIT) != 0

    # Check for blocked/parried
    is_blocked_or_parried = damage_type in (DAMAGE_FLAG_BLOCKED, DAMAGE_FLAG_PARRIED)

    return (damage_type, is_damage, is_critical, is_direct_hit, is_blocked_or_parried)


def is_damage_action(flags_str: str) -> bool:
    """Check if the flags indicate this action dealt damage.

    Args:
        flags_str: Hex string of the flags value

    Returns:
        True if this action dealt damage (including blocked/parried)
    """
    if not flags_str or flags_str == "0":
        return False

    try:
        flags_value = int(flags_str, 16)
    except ValueError:
        return False

    damage_type = flags_value & 0xFF
    return damage_type in (
        DAMAGE_FLAG_DAMAGE,
        DAMAGE_FLAG_BLOCKED,
        DAMAGE_FLAG_PARRIED,
        DAMAGE_FLAG_INSTANT_DEATH,
    )


def is_miss(flags_str: str) -> bool:
    """Check if the flags indicate a miss/dodge.

    Args:
        flags_str: Hex string of the flags value

    Returns:
        True if this action was a miss
    """
    if not flags_str or flags_str == "0":
        return False

    try:
        flags_value = int(flags_str, 16)
    except ValueError:
        return False

    damage_type = flags_value & 0xFF
    return damage_type == DAMAGE_FLAG_MISS
