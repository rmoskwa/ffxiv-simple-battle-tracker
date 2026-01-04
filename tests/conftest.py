"""Shared test fixtures for FFXIV Battle Tracker tests."""

import pytest


# Sample log lines from real ACT logs for testing
@pytest.fixture
def sample_zone_change_combat():
    """Zone change line for a combat zone (trial)."""
    return (
        "01|2026-01-03T14:22:22.5320000-06:00|51C|"
        "Hell on Rails (Extreme)|f9c7f8c2922cd9e5"
    )


@pytest.fixture
def sample_zone_change_city():
    """Zone change line for a non-combat zone (city)."""
    return "01|2026-01-03T14:22:00.7540000-06:00|3C2|Old Sharlayan|a1ce20e7c8ad3193"


@pytest.fixture
def sample_add_combatant_player():
    """AddCombatant line for a player (Paladin)."""
    return (
        "03|2026-01-03T14:22:00.7540000-06:00|1075762D|Jalapeno Jeff|21|64|"
        "0000|28|Jenova|0|0|174686|174686|10000|10000|||"
        "28.29|-33.82|2.46|-0.74|c3899f731f15d677"
    )


@pytest.fixture
def sample_add_combatant_enemy():
    """AddCombatant line for an enemy/NPC."""
    return (
        "03|2026-01-03T14:22:28.0000000-06:00|4000A132|Doomtrain|00|FF|"
        "0000|00||0|0|98895160|98895160|10000|10000|||"
        "100.00|75.00|0.00|0.00|abcd1234"
    )


@pytest.fixture
def sample_ability_enemy_to_player():
    """Ability line: enemy -> player damage."""
    return (
        "21|2026-01-03T14:23:32.6960000-06:00|4000A13D|Doomtrain|B26F|"
        "Dead Man's Blastpipe|106ECCE2|Alfredo Saus|750603|A8450000|"
        "100140E|6FD0000|1B|B26F8000|0|0|0|0|0|0|0|0|0|0|287465|287465|"
        "10000|10000|||99.17|85.50|0.00|3.07|44|44|0|10000|||"
        "100.00|75.00|0.00|0.00|00002C2D|0|1|00||01|B26F|B26F|1.100|7FFF|"
        "f5784169a26a7ce9"
    )


@pytest.fixture
def sample_ability_player_to_enemy():
    """Ability line: player -> enemy damage."""
    return (
        "21|2026-01-03T14:22:49.6410000-06:00|10764E7E|Sir Bj|1CD8|"
        "Holy Spirit|4000A132|Doomtrain|750003|5E3F0000|200004|A19F8000|"
        "0|0|0|0|0|0|0|0|0|0|98895160|98895160|10000|10000|||"
        "100.00|75.00|0.00|0.00|294990|294990|10000|10000|||"
        "99.05|100.63|0.00|3.10|00002AA5|0|1|00||01|1CD8|1CD8|0.100|FE7B|"
        "be4d0e04d9ea8a41"
    )


@pytest.fixture
def sample_ability_autoattack():
    """Ability line: auto-attack (should be filtered out)."""
    return (
        "21|2026-01-03T14:22:50.0000000-06:00|4000A132|Doomtrain|0000|"
        "Attack|10764E7E|Sir Bj|750003|1000000|0|0|0|0|0|0|0|0|0|0|0|0|0|0|"
        "294990|294990|10000|10000|||100.00|75.00|0.00|0.00|294990|294990|"
        "10000|10000|||99.05|100.63|0.00|3.10|00002AA5|0|1|00|"
    )


@pytest.fixture
def sample_death():
    """Death line: player killed by enemy."""
    return (
        "25|2026-01-03T14:24:30.8900000-06:00|10719475|Gyodo Ohta|"
        "4000A13D|Doomtrain|1594c95763aee893"
    )


@pytest.fixture
def sample_debuff_enemy_source():
    """Debuff line: enemy -> player debuff."""
    return (
        "26|2026-01-03T14:23:00.0000000-06:00|ABC|Vulnerability Up|15.00|"
        "4000A132|Doomtrain|10764E7E|Sir Bj|02|294990|294990|hash123"
    )


@pytest.fixture
def sample_debuff_environment_source():
    """Debuff line: environment -> player debuff."""
    return (
        "26|2026-01-03T14:23:00.0000000-06:00|DEF|Doom|10.00|"
        "E0000000||10764E7E|Sir Bj|01|294990|294990|hash456"
    )


@pytest.fixture
def sample_commence():
    """ActorControl line: fight commence."""
    return (
        "33|2026-01-03T14:22:28.9740000-06:00|80034E8B|40000001|"
        "E10|00|00|00|34e379559349eb4c"
    )


@pytest.fixture
def sample_victory():
    """ActorControl line: victory."""
    return (
        "33|2026-01-03T14:31:35.8570000-06:00|80034E8B|40000003|"
        "00|00|00|00|de41720e572dce97"
    )


@pytest.fixture
def sample_wipe():
    """ActorControl line: wipe (fade out)."""
    return (
        "33|2026-01-03T15:21:02.2600000-06:00|80037569|40000005|"
        "00|00|00|00|f8bb8ab23c289094"
    )


@pytest.fixture
def sample_barrier_up():
    """ActorControl line: barrier up (reset ready)."""
    return "33|2026-01-03T15:21:10.0000000-06:00|80037569|40000011|00|00|00|00|hash789"


@pytest.fixture
def sample_recommence():
    """ActorControl line: recommence/retry."""
    return "33|2026-01-03T15:21:15.0000000-06:00|80037569|40000006|00|00|00|00|hashabc"
