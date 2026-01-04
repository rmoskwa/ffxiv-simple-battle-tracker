"""Mitigation buff database for FFXIV damage calculations.

This database contains effect IDs and mitigation percentages for defensive buffs.
Data sourced from FFXIV_ACT_Plugin Definitions (Patch 7.10).

Effect IDs are stored as uppercase hex strings to match ACT log format.
Mitigation values are stored as positive percentages (e.g., 20 = 20% reduction).

Two categories of effects:
1. MITIGATION_BUFFS: Applied to players, reduce damage taken
2. BOSS_DEBUFFS: Applied to enemies, reduce damage dealt by the enemy
"""

from dataclasses import dataclass
from typing import Literal

DamageType = Literal["all", "physical", "magic"]


@dataclass(frozen=True)
class MitigationEffect:
    """A mitigation buff applied to a player."""

    effect_id: str  # Hex string (uppercase)
    name: str
    mitigation_percent: float  # Positive value, e.g., 20 = 20% reduction
    damage_type: DamageType = "all"  # Which damage types this mitigates
    job: str = ""  # Source job, empty for role actions
    is_party_wide: bool = False  # True if affects whole party
    notes: str = ""


@dataclass(frozen=True)
class BossDebuff:
    """A debuff applied to a boss that reduces its damage dealt."""

    effect_id: str  # Hex string (uppercase)
    name: str
    mitigation_percent: float  # Positive value
    damage_type: DamageType = "all"
    job: str = ""  # Source job
    notes: str = ""


# =============================================================================
# MITIGATION BUFFS (Applied to Players)
# =============================================================================

MITIGATION_BUFFS: dict[str, MitigationEffect] = {
    # -------------------------------------------------------------------------
    # Role Actions (All Tanks)
    # -------------------------------------------------------------------------
    "4A7": MitigationEffect(
        effect_id="4A7",
        name="Rampart",
        mitigation_percent=20,
        job="Tank",
        notes="Role action, 20s duration",
    ),
    # -------------------------------------------------------------------------
    # Paladin
    # -------------------------------------------------------------------------
    "4A": MitigationEffect(
        effect_id="4A",
        name="Sentinel",
        mitigation_percent=30,
        job="PLD",
        notes="15s duration",
    ),
    "EF5": MitigationEffect(
        effect_id="EF5",
        name="Guardian",
        mitigation_percent=40,
        job="PLD",
        notes="Upgraded Sentinel, 15s duration",
    ),
    "740": MitigationEffect(
        effect_id="740",
        name="Sheltron",
        mitigation_percent=15,
        job="PLD",
        notes="6s duration",
    ),
    "A72": MitigationEffect(
        effect_id="A72",
        name="Holy Sheltron",
        mitigation_percent=15,
        job="PLD",
        notes="8s duration",
    ),
    "498": MitigationEffect(
        effect_id="498",
        name="Arms Up",
        mitigation_percent=15,
        job="PLD",
        is_party_wide=True,
        notes="Passage of Arms effect on party members",
    ),
    "496": MitigationEffect(
        effect_id="496",
        name="Intervention",
        mitigation_percent=10,
        job="PLD",
        notes="Target mitigation, 10% base + more with oath gauge",
    ),
    "A73": MitigationEffect(
        effect_id="A73",
        name="Knight's Resolve",
        mitigation_percent=10,
        job="PLD",
        notes="From Intervention upgrade",
    ),
    # -------------------------------------------------------------------------
    # Warrior
    # -------------------------------------------------------------------------
    "59": MitigationEffect(
        effect_id="59",
        name="Vengeance",
        mitigation_percent=30,
        job="WAR",
        notes="15s duration",
    ),
    "EF8": MitigationEffect(
        effect_id="EF8",
        name="Damnation",
        mitigation_percent=40,
        job="WAR",
        notes="Upgraded Vengeance, 15s duration",
    ),
    "2DF": MitigationEffect(
        effect_id="2DF",
        name="Raw Intuition",
        mitigation_percent=10,
        job="WAR",
        notes="6s duration",
    ),
    "A76": MitigationEffect(
        effect_id="A76",
        name="Bloodwhetting",
        mitigation_percent=10,
        job="WAR",
        notes="Upgraded Raw Intuition, 8s duration",
    ),
    "A77": MitigationEffect(
        effect_id="A77",
        name="Stem the Flow",
        mitigation_percent=10,
        job="WAR",
        notes="From Bloodwhetting on target",
    ),
    "742": MitigationEffect(
        effect_id="742",
        name="Nascent Glint",
        mitigation_percent=10,
        job="WAR",
        notes="From Nascent Flash on target",
    ),
    "57": MitigationEffect(
        effect_id="57",
        name="Thrill of Battle",
        mitigation_percent=0,
        job="WAR",
        notes="HP increase + heal received bonus, no direct mitigation",
    ),
    # -------------------------------------------------------------------------
    # Dark Knight
    # -------------------------------------------------------------------------
    "2EB": MitigationEffect(
        effect_id="2EB",
        name="Shadow Wall",
        mitigation_percent=30,
        job="DRK",
        notes="15s duration",
    ),
    "EFB": MitigationEffect(
        effect_id="EFB",
        name="Shadowed Vigil",
        mitigation_percent=40,
        job="DRK",
        notes="Upgraded Shadow Wall, 15s duration",
    ),
    "2EA": MitigationEffect(
        effect_id="2EA",
        name="Dark Mind",
        mitigation_percent=20,
        damage_type="magic",
        job="DRK",
        notes="Magic only, 10s duration",
    ),
    "A7A": MitigationEffect(
        effect_id="A7A",
        name="Oblation",
        mitigation_percent=10,
        job="DRK",
        notes="10s duration, can target others",
    ),
    "766": MitigationEffect(
        effect_id="766",
        name="Dark Missionary",
        mitigation_percent=10,
        damage_type="magic",
        job="DRK",
        is_party_wide=True,
        notes="Magic damage only, 15s duration",
    ),
    # -------------------------------------------------------------------------
    # Gunbreaker
    # -------------------------------------------------------------------------
    "728": MitigationEffect(
        effect_id="728",
        name="Camouflage",
        mitigation_percent=10,
        job="GNB",
        notes="20s duration, also increases parry rate",
    ),
    "72A": MitigationEffect(
        effect_id="72A",
        name="Nebula",
        mitigation_percent=30,
        job="GNB",
        notes="15s duration",
    ),
    "EFE": MitigationEffect(
        effect_id="EFE",
        name="Great Nebula",
        mitigation_percent=40,
        job="GNB",
        notes="Upgraded Nebula, 15s duration",
    ),
    "730": MitigationEffect(
        effect_id="730",
        name="Heart of Stone",
        mitigation_percent=15,
        job="GNB",
        notes="7s duration",
    ),
    "A7B": MitigationEffect(
        effect_id="A7B",
        name="Heart of Corundum",
        mitigation_percent=15,
        job="GNB",
        notes="Upgraded Heart of Stone, 8s duration",
    ),
    "A7C": MitigationEffect(
        effect_id="A7C",
        name="Clarity of Corundum",
        mitigation_percent=15,
        job="GNB",
        notes="Additional effect from Heart of Corundum",
    ),
    "72F": MitigationEffect(
        effect_id="72F",
        name="Heart of Light",
        mitigation_percent=10,
        damage_type="magic",
        job="GNB",
        is_party_wide=True,
        notes="Magic damage only, 15s duration",
    ),
    # -------------------------------------------------------------------------
    # White Mage
    # -------------------------------------------------------------------------
    "751": MitigationEffect(
        effect_id="751",
        name="Temperance",
        mitigation_percent=10,
        job="WHM",
        is_party_wide=True,
        notes="Party effect, 22s duration",
    ),
    "A94": MitigationEffect(
        effect_id="A94",
        name="Aquaveil",
        mitigation_percent=15,
        job="WHM",
        notes="Single target, 8s duration",
    ),
    # -------------------------------------------------------------------------
    # Scholar
    # -------------------------------------------------------------------------
    "12B": MitigationEffect(
        effect_id="12B",
        name="Sacred Soil",
        mitigation_percent=10,
        job="SCH",
        is_party_wide=True,
        notes="Ground effect, 15s duration",
    ),
    "A98": MitigationEffect(
        effect_id="A98",
        name="Expedience",
        mitigation_percent=10,
        job="SCH",
        is_party_wide=True,
        notes="From Expedient, 20s duration",
    ),
    "13D": MitigationEffect(
        effect_id="13D",
        name="Fey Illumination",
        mitigation_percent=5,
        damage_type="magic",
        job="SCH",
        is_party_wide=True,
        notes="Magic only, from fairy",
    ),
    "753": MitigationEffect(
        effect_id="753",
        name="Seraphic Illumination",
        mitigation_percent=5,
        damage_type="magic",
        job="SCH",
        is_party_wide=True,
        notes="Magic only, from Seraph",
    ),
    # -------------------------------------------------------------------------
    # Astrologian
    # -------------------------------------------------------------------------
    "351": MitigationEffect(
        effect_id="351",
        name="Collective Unconscious",
        mitigation_percent=10,
        job="AST",
        is_party_wide=True,
        notes="Channeled, effect persists briefly after",
    ),
    "A9D": MitigationEffect(
        effect_id="A9D",
        name="Exaltation",
        mitigation_percent=10,
        job="AST",
        notes="Single target, 8s duration",
    ),
    "75D": MitigationEffect(
        effect_id="75D",
        name="The Spear",
        mitigation_percent=10,
        job="AST",
        notes="Card effect",
    ),
    "F38": MitigationEffect(
        effect_id="F38",
        name="Sun Sign",
        mitigation_percent=10,
        job="AST",
        is_party_wide=True,
        notes="From Divination upgrade",
    ),
    # -------------------------------------------------------------------------
    # Sage
    # -------------------------------------------------------------------------
    "A3A": MitigationEffect(
        effect_id="A3A",
        name="Kerachole",
        mitigation_percent=10,
        job="SGE",
        is_party_wide=True,
        notes="15s duration",
    ),
    "A3B": MitigationEffect(
        effect_id="A3B",
        name="Taurochole",
        mitigation_percent=10,
        job="SGE",
        notes="Single target, 15s duration",
    ),
    "BBB": MitigationEffect(
        effect_id="BBB",
        name="Holos",
        mitigation_percent=10,
        job="SGE",
        is_party_wide=True,
        notes="20s duration",
    ),
    # -------------------------------------------------------------------------
    # Physical Ranged DPS
    # -------------------------------------------------------------------------
    "78E": MitigationEffect(
        effect_id="78E",
        name="Troubadour",
        mitigation_percent=15,
        job="BRD",
        is_party_wide=True,
        notes="15s duration",
    ),
    "79F": MitigationEffect(
        effect_id="79F",
        name="Tactician",
        mitigation_percent=15,
        job="MCH",
        is_party_wide=True,
        notes="15s duration",
    ),
    "722": MitigationEffect(
        effect_id="722",
        name="Shield Samba",
        mitigation_percent=15,
        job="DNC",
        is_party_wide=True,
        notes="15s duration",
    ),
    # -------------------------------------------------------------------------
    # Caster DPS
    # -------------------------------------------------------------------------
    "A93": MitigationEffect(
        effect_id="A93",
        name="Magick Barrier",
        mitigation_percent=10,
        damage_type="magic",
        job="RDM",
        is_party_wide=True,
        notes="Magic only, 10s duration",
    ),
}


# =============================================================================
# BOSS DEBUFFS (Applied to Enemies, reduce their damage dealt)
# =============================================================================

BOSS_DEBUFFS: dict[str, BossDebuff] = {
    # -------------------------------------------------------------------------
    # Tank Role Action
    # -------------------------------------------------------------------------
    "4A9": BossDebuff(
        effect_id="4A9",
        name="Reprisal",
        mitigation_percent=10,
        job="Tank",
        notes="10s duration, reduces all damage dealt by target",
    ),
    # -------------------------------------------------------------------------
    # Melee DPS Role Action
    # -------------------------------------------------------------------------
    "4AB": BossDebuff(
        effect_id="4AB",
        name="Feint",
        mitigation_percent=10,
        damage_type="physical",
        job="Melee",
        notes="Physical -10%, Magic -5%, 15s duration",
    ),
    # Note: Feint has different values for physical vs magic
    # We store the primary (physical) value; magic is 5%
    # -------------------------------------------------------------------------
    # Caster Role Action
    # -------------------------------------------------------------------------
    "4B3": BossDebuff(
        effect_id="4B3",
        name="Addle",
        mitigation_percent=10,
        damage_type="magic",
        job="Caster",
        notes="Magic -10%, Physical -5%, 15s duration",
    ),
    # Note: Addle has different values for magic vs physical
    # We store the primary (magic) value; physical is 5%
    # -------------------------------------------------------------------------
    # Machinist
    # -------------------------------------------------------------------------
    "35C": BossDebuff(
        effect_id="35C",
        name="Dismantle",
        mitigation_percent=10,
        job="MCH",
        notes="10s duration",
    ),
}


# =============================================================================
# Special Cases / Additional Data
# =============================================================================

# Feint and Addle have split mitigation values
FEINT_MAGIC_MITIGATION = 5  # Feint reduces magic by 5% (physical is 10%)
ADDLE_PHYSICAL_MITIGATION = 5  # Addle reduces physical by 5% (magic is 10%)

# Tank Mastery - passive trait that reduces damage taken by 20% for all tanks
# This is NOT a buff that appears in logs - it's always active on tank jobs
TANK_MASTERY_MITIGATION = 20  # 20% passive damage reduction for tanks

# Tank job IDs (hex values from ACT logs)
TANK_JOB_IDS = frozenset({"13", "15", "20", "25"})  # PLD, WAR, DRK, GNB


# =============================================================================
# Lookup Functions
# =============================================================================


def get_mitigation_by_effect_id(effect_id: str) -> MitigationEffect | None:
    """Look up a mitigation buff by its effect ID.

    Args:
        effect_id: Hex string effect ID (case-insensitive)

    Returns:
        MitigationEffect if found, None otherwise
    """
    return MITIGATION_BUFFS.get(effect_id.upper())


def get_boss_debuff_by_effect_id(effect_id: str) -> BossDebuff | None:
    """Look up a boss debuff by its effect ID.

    Args:
        effect_id: Hex string effect ID (case-insensitive)

    Returns:
        BossDebuff if found, None otherwise
    """
    return BOSS_DEBUFFS.get(effect_id.upper())


def get_all_mitigation_effect_ids() -> set[str]:
    """Get all known mitigation effect IDs.

    Returns:
        Set of effect ID hex strings (uppercase)
    """
    return set(MITIGATION_BUFFS.keys()) | set(BOSS_DEBUFFS.keys())


def get_party_wide_mitigations() -> list[MitigationEffect]:
    """Get all party-wide mitigation effects.

    Returns:
        List of MitigationEffect objects that affect the whole party
    """
    return [m for m in MITIGATION_BUFFS.values() if m.is_party_wide]


def is_tank_job(job_id: str) -> bool:
    """Check if a job ID corresponds to a tank job.

    Args:
        job_id: The job ID string (e.g., "13" for Paladin)

    Returns:
        True if the job is a tank (PLD, WAR, DRK, GNB), False otherwise
    """
    return job_id.upper() in TANK_JOB_IDS


def get_effective_mitigation_percent(
    effect_id: str, hit_type: str | None, is_boss_debuff: bool = False
) -> float:
    """Get the effective mitigation percentage based on hit type.

    Some mitigations like Feint and Addle have different values for
    physical vs magical damage. This function returns the correct value.

    Args:
        effect_id: Hex string effect ID (case-insensitive)
        hit_type: The damage type ("Physical", "Magical", or None/Unknown)
        is_boss_debuff: True if this is a boss debuff, False for player buff

    Returns:
        The effective mitigation percentage for the given damage type
    """
    effect_id_upper = effect_id.upper()

    if is_boss_debuff:
        debuff = BOSS_DEBUFFS.get(effect_id_upper)
        if not debuff:
            return 0.0

        # Handle Feint (4AB) - 10% physical, 5% magical
        if effect_id_upper == "4AB":
            if hit_type == "Magical":
                return FEINT_MAGIC_MITIGATION  # 5%
            return debuff.mitigation_percent  # 10% for physical/unknown

        # Handle Addle (4B3) - 10% magical, 5% physical
        if effect_id_upper == "4B3":
            if hit_type == "Physical":
                return ADDLE_PHYSICAL_MITIGATION  # 5%
            return debuff.mitigation_percent  # 10% for magical/unknown

        # For other boss debuffs, check if they're type-specific
        if debuff.damage_type != "all" and hit_type:
            # If the debuff only affects one type and hit is different, no effect
            if debuff.damage_type == "physical" and hit_type == "Magical":
                return 0.0
            if debuff.damage_type == "magic" and hit_type == "Physical":
                return 0.0

        return debuff.mitigation_percent

    else:
        buff = MITIGATION_BUFFS.get(effect_id_upper)
        if not buff:
            return 0.0

        # Check if buff only affects certain damage types
        if buff.damage_type != "all" and hit_type:
            if buff.damage_type == "physical" and hit_type == "Magical":
                return 0.0
            if buff.damage_type == "magic" and hit_type == "Physical":
                return 0.0

        return buff.mitigation_percent
