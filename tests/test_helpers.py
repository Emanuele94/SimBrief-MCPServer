"""Unit tests for server helper functions."""

from server import _atis, _kg, _lbs, _secs_to_hhmm, _unix_to_utc


class TestKg:
    def test_plain_int(self):
        assert _kg(7894) == "7894"

    def test_plain_string(self):
        assert _kg("7894") == "7894"

    def test_dict_with_kg(self):
        assert _kg({"kg": "7894", "lbs": "17403"}) == "7894"

    def test_dict_missing_kg_falls_back_to_str(self):
        result = _kg({"lbs": "17403"})
        assert "17403" in result

    def test_none_returns_dash(self):
        assert _kg(None) == "-"

    def test_empty_string_returns_dash(self):
        assert _kg("") == "-"


class TestLbs:
    def test_dict_with_lbs(self):
        assert _lbs({"kg": "100", "lbs": "220"}) == "220"

    def test_dict_missing_lbs(self):
        assert _lbs({"kg": "100"}) == ""

    def test_plain_value_returns_empty(self):
        assert _lbs("100") == ""

    def test_none_returns_empty(self):
        assert _lbs(None) == ""


class TestSecsToHhmm:
    def test_zero(self):
        assert _secs_to_hhmm(0) == "00:00"

    def test_one_hour(self):
        assert _secs_to_hhmm(3600) == "01:00"

    def test_three_hours_43_min(self):
        assert _secs_to_hhmm(13424) == "03:43"

    def test_string_input(self):
        assert _secs_to_hhmm("3600") == "01:00"

    def test_negative_seconds(self):
        # Negative time differences should not crash
        result = _secs_to_hhmm(-157)
        assert isinstance(result, str)

    def test_invalid_input_returns_string(self):
        assert _secs_to_hhmm("invalid") == "invalid"

    def test_none_returns_string(self):
        result = _secs_to_hhmm(None)
        assert isinstance(result, str)


class TestUnixToUtc:
    def test_known_timestamp(self):
        # 2026-04-11 13:53:22 UTC
        result = _unix_to_utc(1775915602)
        assert "2026-04-11" in result
        assert "UTC" in result

    def test_string_timestamp(self):
        result = _unix_to_utc("1775915602")
        assert "2026-04-11" in result

    def test_invalid_returns_original(self):
        assert _unix_to_utc("not-a-timestamp") == "not-a-timestamp"

    def test_none_returns_string(self):
        result = _unix_to_utc(None)
        assert isinstance(result, str)


class TestAtis:
    def test_none_returns_na(self):
        assert _atis(None) == "N/A"

    def test_empty_string_returns_na(self):
        assert _atis("") == "N/A"

    def test_plain_string_passthrough(self):
        assert _atis("ATIS INFO ALPHA") == "ATIS INFO ALPHA"

    def test_dict_with_message(self):
        obj = {
            "network": "sayintentions",
            "letter": "T",
            "issued": "2026-04-11T13:20:00Z",
            "message": "INFORMATION TANGO. WIND CALM. CAVOK.",
        }
        result = _atis(obj)
        assert "sayintentions" in result
        assert "TANGO" in result
        assert "CAVOK" in result

    def test_dict_without_letter(self):
        obj = {"network": "vatsim", "text": "ATIS text here"}
        result = _atis(obj)
        assert "vatsim" in result

    def test_dict_empty_message(self):
        obj = {"network": "ivao", "letter": "B", "issued": "2026-01-01T00:00:00Z"}
        result = _atis(obj)
        assert "ivao" in result
        assert "B" in result
