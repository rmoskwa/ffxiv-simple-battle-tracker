"""Data modules for FFXIV Battle Tracker."""

from .mitigation_db import (
    BOSS_DEBUFFS,
    MITIGATION_BUFFS,
    BossDebuff,
    MitigationEffect,
    get_boss_debuff_by_effect_id,
    get_mitigation_by_effect_id,
)

__all__ = [
    "MITIGATION_BUFFS",
    "BOSS_DEBUFFS",
    "get_mitigation_by_effect_id",
    "get_boss_debuff_by_effect_id",
    "MitigationEffect",
    "BossDebuff",
]
