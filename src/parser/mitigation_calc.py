"""Mitigation and unmitigated damage calculation.

This module calculates unmitigated damage by reversing the mitigation effects
that were active when damage was dealt.
"""

from ..data.mitigation_db import get_effective_mitigation_percent
from ..models.data_models import ActiveMitigation


def calculate_total_mitigation(
    mitigations: list[ActiveMitigation], hit_type: str | None = None
) -> float:
    """Calculate the total mitigation percentage from a list of active mitigations.

    Mitigations in FFXIV stack multiplicatively, not additively.
    For example, 10% + 20% mitigation = 1 - (0.9 * 0.8) = 28% total mitigation.

    This function also handles damage-type-specific mitigations like Feint and
    Addle, which have different values for physical vs magical damage.

    Args:
        mitigations: List of active mitigation effects
        hit_type: The damage type ("Physical", "Magical", or None for unknown)

    Returns:
        Total mitigation as a decimal (e.g., 0.28 for 28% mitigation)
    """
    if not mitigations:
        return 0.0

    # Calculate multiplicative stacking
    damage_multiplier = 1.0
    for mit in mitigations:
        # Get the effective mitigation percentage based on hit type
        effective_percent = get_effective_mitigation_percent(
            mit.effect_id, hit_type, mit.is_boss_debuff
        )
        # Convert percentage to multiplier (e.g., 20% -> 0.80)
        damage_multiplier *= 1.0 - (effective_percent / 100.0)

    # Total mitigation is the reduction from 100%
    return 1.0 - damage_multiplier


def calculate_unmitigated_damage(
    actual_damage: int,
    mitigations: list[ActiveMitigation],
    hit_type: str | None = None,
) -> int:
    """Calculate the unmitigated (base) damage from the actual damage taken.

    Formula: unmitigated = actual / (1 - total_mitigation)

    For example, if actual damage is 11,661 and total mitigation is 77.11%:
    unmitigated = 11,661 / (1 - 0.7711) = 11,661 / 0.2289 ≈ 50,942

    Args:
        actual_damage: The actual damage dealt after mitigation
        mitigations: List of active mitigation effects at the time of damage
        hit_type: The damage type ("Physical", "Magical", or None for unknown)

    Returns:
        The calculated unmitigated damage
    """
    if actual_damage <= 0:
        return 0

    total_mitigation = calculate_total_mitigation(mitigations, hit_type)

    # If no mitigation, unmitigated equals actual
    if total_mitigation <= 0:
        return actual_damage

    # Prevent division by zero (100% mitigation would mean 0 damage taken)
    if total_mitigation >= 1.0:
        # Can't reverse 100% mitigation, return actual as estimate
        return actual_damage

    # Reverse the mitigation: unmitigated = actual / (1 - mitigation)
    unmitigated = actual_damage / (1.0 - total_mitigation)

    return round(unmitigated)


def get_mitigation_summary(mitigations: list[ActiveMitigation]) -> dict:
    """Get a summary of active mitigations for debugging/display.

    Args:
        mitigations: List of active mitigation effects

    Returns:
        Dictionary with mitigation details
    """
    player_buffs = [m for m in mitigations if not m.is_boss_debuff]
    boss_debuffs = [m for m in mitigations if m.is_boss_debuff]

    return {
        "player_buffs": [
            {"name": m.effect_name, "percent": m.mitigation_percent}
            for m in player_buffs
        ],
        "boss_debuffs": [
            {"name": m.effect_name, "percent": m.mitigation_percent}
            for m in boss_debuffs
        ],
        "total_mitigation_percent": calculate_total_mitigation(mitigations) * 100,
    }
