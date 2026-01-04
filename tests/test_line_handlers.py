"""Tests for log line parsing handlers."""

from datetime import datetime

from src.parser.line_handlers import (
    LineHandlers,
    get_job_name,
    is_enemy_id,
    is_player_id,
    parse_timestamp,
)


class TestIsPlayerId:
    """Tests for player ID validation."""

    def test_valid_player_id(self):
        assert is_player_id("10764E7E") is True
        assert is_player_id("1075762D") is True
        assert is_player_id("10000000") is True

    def test_enemy_id_not_player(self):
        assert is_player_id("4000A132") is False
        assert is_player_id("40000000") is False

    def test_environment_id_not_player(self):
        assert is_player_id("E0000000") is False

    def test_case_insensitive(self):
        assert is_player_id("10abcdef") is True
        assert is_player_id("10ABCDEF") is True

    def test_short_id(self):
        assert is_player_id("10") is True
        assert is_player_id("1") is False


class TestIsEnemyId:
    """Tests for enemy ID validation."""

    def test_valid_enemy_id(self):
        assert is_enemy_id("4000A132") is True
        assert is_enemy_id("4000A13D") is True
        assert is_enemy_id("40000000") is True

    def test_player_id_not_enemy(self):
        assert is_enemy_id("10764E7E") is False
        assert is_enemy_id("10000000") is False

    def test_case_insensitive(self):
        assert is_enemy_id("40abcdef") is True
        assert is_enemy_id("40ABCDEF") is True


class TestParseTimestamp:
    """Tests for timestamp parsing."""

    def test_standard_timestamp(self):
        ts = parse_timestamp("2026-01-03T14:22:22.5320000-06:00")
        assert ts.year == 2026
        assert ts.month == 1
        assert ts.day == 3
        assert ts.hour == 14
        assert ts.minute == 22
        assert ts.second == 22

    def test_microseconds_truncated(self):
        # 7 decimal places should be truncated to 6
        ts = parse_timestamp("2026-01-03T14:22:22.1234567-06:00")
        assert ts.microsecond == 123456

    def test_different_timezone(self):
        # Timezone is stripped, so this should still parse
        ts = parse_timestamp("2026-01-03T14:22:22.0000000+09:00")
        assert ts.hour == 14

    def test_short_microseconds(self):
        # Shorter precision should be padded
        ts = parse_timestamp("2026-01-03T14:22:22.5-06:00")
        assert ts.microsecond == 500000

    def test_no_timezone(self):
        ts = parse_timestamp("2026-01-03T14:22:22.000000")
        assert ts.year == 2026


class TestGetJobName:
    """Tests for job name lookup."""

    def test_paladin(self):
        assert get_job_name("13") == "Paladin"

    def test_warrior(self):
        assert get_job_name("15") == "Warrior"

    def test_astrologian(self):
        assert get_job_name("21") == "Astrologian"

    def test_unknown_job(self):
        assert get_job_name("FF") == "Unknown"

    def test_case_insensitive(self):
        assert get_job_name("1c") == "Scholar"
        assert get_job_name("1C") == "Scholar"


class TestParseZoneChange:
    """Tests for zone change line parsing."""

    def test_valid_zone_change(self, sample_zone_change_combat):
        fields = sample_zone_change_combat.split("|")
        result = LineHandlers.parse_line_01_zone_change(fields)

        assert result is not None
        assert result.zone_id == "51C"
        assert result.zone_name == "Hell on Rails (Extreme)"
        assert result.timestamp.year == 2026

    def test_city_zone(self, sample_zone_change_city):
        fields = sample_zone_change_city.split("|")
        result = LineHandlers.parse_line_01_zone_change(fields)

        assert result is not None
        assert result.zone_name == "Old Sharlayan"

    def test_too_few_fields(self):
        result = LineHandlers.parse_line_01_zone_change(["01", "timestamp", "zone_id"])
        assert result is None


class TestParseAddCombatant:
    """Tests for AddCombatant line parsing."""

    def test_valid_player(self, sample_add_combatant_player):
        fields = sample_add_combatant_player.split("|")
        result = LineHandlers.parse_line_03_add_combatant(fields)

        assert result is not None
        assert result.id == "1075762D"
        assert result.name == "Jalapeno Jeff"
        assert result.job_id == "21"
        assert result.is_player is True
        assert result.max_hp == 174686

    def test_enemy_combatant(self, sample_add_combatant_enemy):
        fields = sample_add_combatant_enemy.split("|")
        result = LineHandlers.parse_line_03_add_combatant(fields)

        assert result is not None
        assert result.name == "Doomtrain"
        assert result.is_player is False

    def test_too_few_fields(self):
        result = LineHandlers.parse_line_03_add_combatant(["03"] * 5)
        assert result is None


class TestParseAbility:
    """Tests for ability line parsing."""

    def test_enemy_to_player_damage(self, sample_ability_enemy_to_player):
        fields = sample_ability_enemy_to_player.split("|")
        result = LineHandlers.parse_line_21_22_ability(fields)

        assert result is not None
        assert result.source_name == "Doomtrain"
        assert result.target_name == "Alfredo Saus"
        assert result.ability_name == "Dead Man's Blastpipe"
        assert result.damage > 0

    def test_player_to_enemy_filtered(self, sample_ability_player_to_enemy):
        """Player -> enemy abilities should be filtered out."""
        fields = sample_ability_player_to_enemy.split("|")
        result = LineHandlers.parse_line_21_22_ability(fields)

        assert result is None

    def test_autoattack_filtered(self, sample_ability_autoattack):
        """Auto-attacks should be filtered out."""
        fields = sample_ability_autoattack.split("|")
        result = LineHandlers.parse_line_21_22_ability(fields)

        assert result is None

    def test_too_few_fields(self):
        result = LineHandlers.parse_line_21_22_ability(["21"] * 10)
        assert result is None


class TestParsePlayerDamageTimestamp:
    """Tests for detecting player -> boss damage."""

    def test_player_damage_returns_timestamp(self, sample_ability_player_to_enemy):
        fields = sample_ability_player_to_enemy.split("|")
        result = LineHandlers.parse_player_damage_timestamp(fields)

        assert result is not None
        assert isinstance(result, datetime)

    def test_enemy_damage_returns_none(self, sample_ability_enemy_to_player):
        fields = sample_ability_enemy_to_player.split("|")
        result = LineHandlers.parse_player_damage_timestamp(fields)

        assert result is None


class TestParseDeath:
    """Tests for death line parsing."""

    def test_player_death(self, sample_death):
        fields = sample_death.split("|")
        result = LineHandlers.parse_line_25_death(fields)

        assert result is not None
        assert result.player_name == "Gyodo Ohta"
        assert result.source_name == "Doomtrain"

    def test_enemy_death_filtered(self):
        """Enemy deaths should be filtered out."""
        line = (
            "25|2026-01-03T14:31:37.0000000-06:00|4000A132|Doomtrain|"
            "10764E7E|Sir Bj|hash"
        )
        fields = line.split("|")
        result = LineHandlers.parse_line_25_death(fields)

        assert result is None


class TestParseBuff:
    """Tests for buff/debuff line parsing."""

    def test_enemy_debuff(self, sample_debuff_enemy_source):
        fields = sample_debuff_enemy_source.split("|")
        result = LineHandlers.parse_line_26_buff(fields)

        assert result is not None
        assert result.effect_name == "Vulnerability Up"
        assert result.source_type == "enemy"
        assert result.duration == 15.0

    def test_environment_debuff(self, sample_debuff_environment_source):
        fields = sample_debuff_environment_source.split("|")
        result = LineHandlers.parse_line_26_buff(fields)

        assert result is not None
        assert result.effect_name == "Doom"
        assert result.source_type == "environment"

    def test_player_buff_filtered(self):
        """Player -> player buffs should be filtered out."""
        line = (
            "26|2026-01-03T14:23:00.0000000-06:00|123|Regen|30.00|"
            "10764E7E|Sir Bj|10764E7E|Sir Bj|00|294990|294990|hash"
        )
        fields = line.split("|")
        result = LineHandlers.parse_line_26_buff(fields)

        assert result is None


class TestParseActorControl:
    """Tests for ActorControl line parsing."""

    def test_commence_command(self, sample_commence):
        fields = sample_commence.split("|")
        result = LineHandlers.parse_line_33_actor_control(fields)

        assert result is not None
        assert LineHandlers.is_commence_command(result) is True
        assert LineHandlers.is_victory_command(result) is False
        assert LineHandlers.is_wipe_command(result) is False

    def test_victory_command(self, sample_victory):
        fields = sample_victory.split("|")
        result = LineHandlers.parse_line_33_actor_control(fields)

        assert result is not None
        assert LineHandlers.is_victory_command(result) is True
        assert LineHandlers.is_commence_command(result) is False

    def test_wipe_command(self, sample_wipe):
        fields = sample_wipe.split("|")
        result = LineHandlers.parse_line_33_actor_control(fields)

        assert result is not None
        assert LineHandlers.is_wipe_command(result) is True

    def test_barrier_up_command(self, sample_barrier_up):
        fields = sample_barrier_up.split("|")
        result = LineHandlers.parse_line_33_actor_control(fields)

        assert result is not None
        assert LineHandlers.is_barrier_up_command(result) is True

    def test_recommence_command(self, sample_recommence):
        fields = sample_recommence.split("|")
        result = LineHandlers.parse_line_33_actor_control(fields)

        assert result is not None
        assert LineHandlers.is_recommence_command(result) is True
