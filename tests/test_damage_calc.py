"""Tests for damage calculation and flag parsing."""

from src.parser.damage_calc import (
    DAMAGE_FLAG_BLOCKED,
    DAMAGE_FLAG_DAMAGE,
    DAMAGE_FLAG_MISS,
    DAMAGE_FLAG_PARRIED,
    calculate_damage,
    is_damage_action,
    is_miss,
    parse_flags,
)


class TestCalculateDamage:
    """Tests for the calculate_damage function."""

    def test_empty_string_returns_zero(self):
        assert calculate_damage("") == 0

    def test_zero_returns_zero(self):
        assert calculate_damage("0") == 0

    def test_none_returns_zero(self):
        assert calculate_damage(None) == 0

    def test_invalid_hex_returns_zero(self):
        assert calculate_damage("ZZZZ") == 0

    def test_normal_damage_small(self):
        # Normal damage: first 2 bytes (4 hex chars) are the damage
        # "2D00000" -> padded to "02D00000" -> first 2 bytes = 0x02D0 = 720
        assert calculate_damage("2D00000") == 720

    def test_normal_damage_medium(self):
        # "5E3F0000" -> first 2 bytes = 0x5E3F = 24127
        assert calculate_damage("5E3F0000") == 24127

    def test_normal_damage_from_real_log(self):
        # From testlog: "A8450000" - should extract first 2 bytes
        # 0xA845 = 43077
        assert calculate_damage("A8450000") == 43077

    def test_big_damage_flag_set(self):
        # Big damage: when byte C has 0x40 flag set
        # "423F400F" -> byte C = 0x40 (has flag)
        # Calculation: D=0x0F, A=0x42, B=0x3F -> (D<<16)|(A<<8)|B
        # = (0x0F << 16) | (0x42 << 8) | 0x3F
        # = 0x0F0000 | 0x4200 | 0x3F = 0x0F423F = 999999
        assert calculate_damage("423F400F") == 999999

    def test_big_damage_another_example(self):
        # "01004001" -> byte C = 0x40 (has flag)
        # D=0x01, A=0x01, B=0x00 -> (1<<16)|(1<<8)|0 = 65792
        assert calculate_damage("01004001") == 65792

    def test_normal_damage_no_big_flag(self):
        # "12340000" -> byte C = 0x00, no big flag
        # First 2 bytes = 0x1234 = 4660
        assert calculate_damage("12340000") == 4660

    def test_case_insensitive(self):
        assert calculate_damage("2d00000") == calculate_damage("2D00000")
        assert calculate_damage("abcd0000") == calculate_damage("ABCD0000")

    def test_short_hex_string_padded(self):
        # "FF" -> padded to "000000FF" -> first 2 bytes = 0x0000 = 0
        assert calculate_damage("FF") == 0

    def test_max_normal_damage(self):
        # Maximum 2-byte value: 0xFFFF = 65535
        assert calculate_damage("FFFF0000") == 65535


class TestParseFlags:
    """Tests for the parse_flags function."""

    def test_empty_string(self):
        result = parse_flags("")
        assert result == (0, False, False, False, False)

    def test_zero(self):
        result = parse_flags("0")
        assert result == (0, False, False, False, False)

    def test_invalid_hex(self):
        result = parse_flags("ZZZZ")
        assert result == (0, False, False, False, False)

    def test_damage_flag(self):
        # 0x03 = DAMAGE_FLAG_DAMAGE
        damage_type, is_damage, is_crit, is_dh, is_blocked = parse_flags("03")
        assert damage_type == DAMAGE_FLAG_DAMAGE
        assert is_damage is True
        assert is_crit is False
        assert is_dh is False

    def test_miss_flag(self):
        damage_type, is_damage, _, _, _ = parse_flags("01")
        assert damage_type == DAMAGE_FLAG_MISS
        assert is_damage is False

    def test_blocked_flag(self):
        damage_type, is_damage, _, _, is_blocked = parse_flags("05")
        assert damage_type == DAMAGE_FLAG_BLOCKED
        assert is_blocked is True

    def test_parried_flag(self):
        damage_type, is_damage, _, _, is_blocked = parse_flags("06")
        assert damage_type == DAMAGE_FLAG_PARRIED
        assert is_blocked is True

    def test_critical_hit(self):
        # 0x2003 = severity 0x20 (crit) + damage type 0x03
        _, _, is_crit, is_dh, _ = parse_flags("2003")
        assert is_crit is True
        assert is_dh is False

    def test_direct_hit(self):
        # 0x4003 = severity 0x40 (DH) + damage type 0x03
        _, _, is_crit, is_dh, _ = parse_flags("4003")
        assert is_crit is False
        assert is_dh is True

    def test_critical_direct_hit(self):
        # 0x6003 = severity 0x60 (crit+DH) + damage type 0x03
        _, _, is_crit, is_dh, _ = parse_flags("6003")
        assert is_crit is True
        assert is_dh is True

    def test_real_log_flags(self):
        # From testlog: "750603" - analyze the flags
        damage_type, is_damage, is_crit, is_dh, _ = parse_flags("750603")
        assert damage_type == DAMAGE_FLAG_DAMAGE
        assert is_damage is True


class TestIsDamageAction:
    """Tests for the is_damage_action function."""

    def test_empty_string(self):
        assert is_damage_action("") is False

    def test_zero(self):
        assert is_damage_action("0") is False

    def test_damage_flag(self):
        assert is_damage_action("03") is True
        assert is_damage_action("750003") is True

    def test_blocked_flag(self):
        assert is_damage_action("05") is True

    def test_parried_flag(self):
        assert is_damage_action("06") is True

    def test_instant_death(self):
        assert is_damage_action("33") is True

    def test_miss_not_damage(self):
        assert is_damage_action("01") is False

    def test_heal_not_damage(self):
        assert is_damage_action("04") is False


class TestIsMiss:
    """Tests for the is_miss function."""

    def test_empty_string(self):
        assert is_miss("") is False

    def test_miss_flag(self):
        assert is_miss("01") is True

    def test_damage_not_miss(self):
        assert is_miss("03") is False
