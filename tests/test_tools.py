"""Unit tests for MCP tool functions using mocked SimBrief API responses."""

import json

import pytest

import server

# ── shared fixture ────────────────────────────────────────────────────────────

MOCK_RESPONSE = {
    "fetch": {"userid": "1211629", "status": "Success"},
    "params": {
        "request_id": "169230419",
        "user_id": "1211629",
        "time_generated": "1775915602",
        "units": "kgs",
    },
    "general": {
        "icao_airline": "ITY",
        "flight_number": "610",
        "cruise_profile": "CI 50",
        "costindex": "50",
        "initial_altitude": "37000",
        "gc_distance": "1614",
        "route_distance": "1737",
        "avg_wind_comp": "44",
        "avg_wind_dir": "302",
        "passengers": "182",
        "total_burn": "7894",
        "route": "ROB5W ROBAS DCT IPDAB",
    },
    "origin": {
        "icao_code": "LIMC",
        "iata_code": "MXP",
        "elevation": "769",
        "plan_rwy": "35R",
        "metar": "LIMC 111320Z VRB03KT CAVOK 21/04 Q1015 NOSIG",
        "taf": "LIMC 111100Z 1112/1218 VRB05KT 9999 SCT045",
        "atis": {
            "network": "sayintentions",
            "letter": "T",
            "issued": "2026-04-11T13:20:00Z",
            "message": "INFORMATION TANGO. WIND CALM. CAVOK.",
        },
    },
    "destination": {
        "icao_code": "HESH",
        "iata_code": "SSH",
        "elevation": "115",
        "plan_rwy": "04R",
        "metar": "HESH 111300Z 07005KT CAVOK 28/05 Q1014 NOSIG",
        "taf": "HESH 111100Z 1112/1218 11010KT CAVOK",
        "atis": None,
    },
    "alternate": {
        "icao_code": "HEGN",
        "iata_code": "HRG",
        "elevation": "109",
        "plan_rwy": "34R",
        "metar": "HEGN 111300Z 01012KT CAVOK 27/06 Q1014 NOSIG",
        "taf": "HEGN 111100Z 1112/1218 01015KT CAVOK",
        "alternate_navlog": {
            "fix": [
                {"ident": "DEDEV", "type": "wpt", "altitude_feet": "37000", "distance": "10"},
                {"ident": "HEGN", "type": "apt", "altitude_feet": "109", "distance": "45"},
            ]
        },
    },
    "aircraft": {
        "icaocode": "A20N",
        "iata_code": "32N",
        "base_type": "A20N",
        "name": "A320-200N",
        "reg": "N251SB",
        "equip": "M-SDE2E3FGHIRWXY/LB1",
        "engines": "LEAP-1A26",
        "pax_count": "180",
        "supports_tlr": "2",
    },
    "fuel": {
        "taxi": {"kg": "230", "lbs": "507"},
        "enroute_burn": {"kg": "7894", "lbs": "17403"},
        "contingency": {"kg": "529", "lbs": "1166"},
        "alternate_burn": {"kg": "869", "lbs": "1916"},
        "reserve": {"kg": "944", "lbs": "2081"},
        "min_takeoff": {"kg": "10236", "lbs": "22566"},
        "plan_takeoff": {"kg": "10236", "lbs": "22566"},
    },
    "fuel_extra": {"bucket": []},
    "weights": {
        "oew": "44339",
        "payload": "18987",
        "pax_count": "182",
        "est_zfw": "63326",
        "est_tow": "73562",
        "est_ramp": "73792",
        "est_ldw": "65668",
    },
    "times": {
        "est_time_enroute": "13424",
        "sched_time_enroute": "13020",
        "sched_out": "1775917500",
        "sched_off": "1775918700",
        "sched_on": "1775931720",
        "sched_in": "1775932200",
        "est_block": "15104",
        "taxi_out": "1200",
        "taxi_in": "480",
        "reserve_time": "1800",
        "endurance": "17755",
    },
    "atc": {
        "callsign": "ITY610",
        "flight_type": "S",
        "flight_rules": "I",
        "initial_spd": "0450",
        "route": "N0450F370 ROB5W ROBAS DCT IPDAB",
        "flightplan_text": "(FPL-ITY610-IS\n-A20N/M-...\n-LIMC1425\n...)",
    },
    "navlog": {
        "fix": [
            {
                "ident": "MC604",
                "type": "wpt",
                "altitude_feet": "3100",
                "distance": "5",
                "time_leg": "137",
                "fuel_leg": "226",
            },
            {
                "ident": "ROBAS",
                "type": "wpt",
                "altitude_feet": "27100",
                "distance": "58",
                "time_leg": "502",
                "fuel_leg": "636",
            },
            {
                "ident": "TOC",
                "type": "ltlg",
                "altitude_feet": "37000",
                "distance": "36",
                "time_leg": "268",
                "fuel_leg": "207",
            },
            {
                "ident": "HESH",
                "type": "apt",
                "altitude_feet": "115",
                "distance": "0",
                "time_leg": "0",
                "fuel_leg": "0",
            },
        ]
    },
    "notams": {"notamdrec": []},
    "tlr": {},
    "crew": {
        "pilot_id": "1211629",
        "cpt": "JOHN DOE",
        "fo": "RUTH MEDINA",
        "dx": "CAMERON BAILEY",
        "pu": "MERCEDES MCCONNELL",
        "fa": ["KAYLA GARNER", "JOSEPHINE BRENNAN"],
    },
    "impacts": {
        "minus_6000ft": {
            "time_enroute": "13267",
            "time_difference": "-157",
            "enroute_burn": "8736",
            "burn_difference": "842",
            "ramp_fuel": "11372",
            "initial_fl": "310",
        },
        "minus_4000ft": {
            "time_enroute": "13291",
            "time_difference": "-133",
            "enroute_burn": "8396",
            "burn_difference": "502",
            "initial_fl": "330",
        },
        "plus_2000ft": {},
        "plus_4000ft": {},
        "lower_ci": {
            "time_enroute": "13927",
            "time_difference": "503",
            "enroute_burn": "7775",
            "burn_difference": "-119",
            "initial_fl": "370",
        },
        "higher_ci": {
            "time_enroute": "13424",
            "time_difference": "0",
            "enroute_burn": "7894",
            "burn_difference": "0",
            "initial_fl": "370",
        },
    },
}


@pytest.fixture(autouse=True)
def mock_fetch(monkeypatch):
    """Patch _fetch so all tool tests run offline."""

    async def fake_fetch(plan_id=None):
        return MOCK_RESPONSE

    monkeypatch.setattr(server, "_fetch", fake_fetch)


# ── tool tests ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_flight_summary_contains_key_fields():
    result = await server.get_flight_summary()
    assert "ITY610" in result
    assert "LIMC" in result
    assert "HESH" in result
    assert "1614" in result  # GC distance
    assert "FL37000" in result
    assert "03:43" in result  # ETE formatted
    assert "7894" in result  # trip fuel
    assert "169230419" in result  # plan ID
    assert "2026-04-11" in result  # generated date


@pytest.mark.asyncio
async def test_get_weather_departure_and_arrival():
    result = await server.get_weather()
    assert "LIMC" in result
    assert "HESH" in result
    assert "CAVOK" in result
    assert "METAR" in result
    assert "TAF" in result


@pytest.mark.asyncio
async def test_get_weather_includes_alternate():
    result = await server.get_weather()
    assert "HEGN" in result
    assert "ALTERNATE" in result


@pytest.mark.asyncio
async def test_get_weather_atis_dict_formatted():
    result = await server.get_weather()
    # ATIS dict should be formatted, not printed as raw Python dict
    assert "{'network'" not in result
    assert "sayintentions" in result
    assert "TANGO" in result


@pytest.mark.asyncio
async def test_get_weather_atis_none_shows_na():
    result = await server.get_weather()
    # HESH has atis=None — should show N/A, not "None"
    lines = result.splitlines()
    arrival_atis = next(
        (ln for ln in lines if "ATIS" in ln and "sayintentions" not in ln and "HEGN" not in ln), ""
    )
    assert "None" not in arrival_atis


@pytest.mark.asyncio
async def test_get_fuel_plan_all_items_present():
    result = await server.get_fuel_plan()
    for label in [
        "Taxi",
        "Trip Burn",
        "Contingency",
        "Alternate Burn",
        "Reserve",
        "Min Takeoff",
        "Plan Takeoff",
    ]:
        assert label in result
    assert "230" in result  # taxi kg
    assert "7894" in result  # trip burn kg
    assert "10236" in result  # takeoff fuel kg


@pytest.mark.asyncio
async def test_get_fuel_plan_extra_bucket_empty():
    result = await server.get_fuel_plan()
    assert "Extra fuel" not in result


@pytest.mark.asyncio
async def test_get_weights_all_items_with_units():
    result = await server.get_weights()
    assert "44339 kg" in result  # OEW
    assert "63326 kg" in result  # ZFW
    assert "73562 kg" in result  # TOW
    assert "65668 kg" in result  # LDW
    assert "182" in result  # passengers (no kg suffix)


@pytest.mark.asyncio
async def test_get_times_formatted_utc():
    result = await server.get_times()
    assert "2026-04-11" in result
    assert "UTC" in result
    assert "03:43" in result  # ETE
    assert "04:11" in result  # block time
    assert "00:20" in result  # taxi out
    assert "00:08" in result  # taxi in


@pytest.mark.asyncio
async def test_get_atc_flightplan_contains_string():
    result = await server.get_atc_flightplan()
    assert "ITY610" in result
    assert "A20N" in result
    assert "ROBAS" in result
    assert "FPL" in result


@pytest.mark.asyncio
async def test_get_aircraft_info():
    result = await server.get_aircraft_info()
    assert "A20N" in result
    assert "N251SB" in result
    assert "LEAP-1A26" in result


@pytest.mark.asyncio
async def test_get_navlog_shows_fixes():
    result = await server.get_navlog()
    assert "MC604" in result
    assert "ROBAS" in result
    assert "TOC" in result
    assert "4 fixes total" in result


@pytest.mark.asyncio
async def test_get_navlog_max_fixes_limits_output():
    result = await server.get_navlog(max_fixes=2)
    assert "showing 2" in result
    assert "2 more fixes" in result


@pytest.mark.asyncio
async def test_get_notams_empty():
    result = await server.get_notams()
    assert "No NOTAMs found" in result


@pytest.mark.asyncio
async def test_get_notams_with_records(monkeypatch):
    response = dict(MOCK_RESPONSE)
    response["notams"] = {
        "notamdrec": [
            {"icao": "LIMC", "notam_id": "A1234/26", "notam": "RWY 35R closed 0600-0800"},
            {"icao": "HESH", "notam_id": "B0001/26", "notam": "ILS out of service"},
        ]
    }

    async def fake_fetch(plan_id=None):
        return response

    monkeypatch.setattr(server, "_fetch", fake_fetch)

    result = await server.get_notams()
    assert "2 total" in result
    assert "LIMC" in result
    assert "A1234/26" in result
    assert "RWY 35R closed" in result
    assert "HESH" in result


@pytest.mark.asyncio
async def test_get_alternate_info():
    result = await server.get_alternate_info()
    assert "HEGN" in result
    assert "HRG" in result
    assert "34R" in result
    assert "DEDEV" in result


@pytest.mark.asyncio
async def test_get_alternate_info_missing(monkeypatch):
    response = dict(MOCK_RESPONSE)
    response["alternate"] = {}

    async def fake_fetch(plan_id=None):
        return response

    monkeypatch.setattr(server, "_fetch", fake_fetch)

    result = await server.get_alternate_info()
    assert "No alternate airport" in result


@pytest.mark.asyncio
async def test_get_performance_empty_tlr():
    result = await server.get_performance()
    assert "No TLR performance data" in result


@pytest.mark.asyncio
async def test_get_performance_with_data(monkeypatch):
    response = dict(MOCK_RESPONSE)
    response["tlr"] = {
        "takeoff": {"flex_temp": "55", "v1": "142", "vr": "146", "v2": "151"},
        "landing": {"vref": "138", "ldg_dist": "1450"},
    }

    async def fake_fetch(plan_id=None):
        return response

    monkeypatch.setattr(server, "_fetch", fake_fetch)

    result = await server.get_performance()
    assert "TAKEOFF" in result
    assert "LANDING" in result
    assert "flex_temp" in result
    assert "55" in result


@pytest.mark.asyncio
async def test_get_crew():
    result = await server.get_crew()
    assert "JOHN DOE" in result
    assert "RUTH MEDINA" in result
    assert "CAMERON BAILEY" in result
    assert "1211629" in result


@pytest.mark.asyncio
async def test_get_crew_empty(monkeypatch):
    response = dict(MOCK_RESPONSE)
    response["crew"] = {}

    async def fake_fetch(plan_id=None):
        return response

    monkeypatch.setattr(server, "_fetch", fake_fetch)

    result = await server.get_crew()
    assert "No crew information" in result


@pytest.mark.asyncio
async def test_get_impacts_shows_all_scenarios():
    result = await server.get_impacts()
    assert "FL -6000 ft" in result
    assert "FL -4000 ft" in result
    assert "Lower CI" in result
    assert "Higher CI" in result
    # Positive burn diff should have + prefix
    assert "+842" in result
    # Negative burn diff should be plain negative
    assert "-119" in result


@pytest.mark.asyncio
async def test_get_impacts_empty(monkeypatch):
    response = dict(MOCK_RESPONSE)
    response["impacts"] = {}

    async def fake_fetch(plan_id=None):
        return response

    monkeypatch.setattr(server, "_fetch", fake_fetch)

    result = await server.get_impacts()
    assert "No impact analysis" in result


@pytest.mark.asyncio
async def test_get_full_flight_plan_is_valid_json():
    result = await server.get_full_flight_plan()
    parsed = json.loads(result)
    assert "general" in parsed
    assert "fuel" in parsed
    # Verbose sections should be stripped
    assert "navlog" not in parsed
    assert "notams" not in parsed
    assert "alternate" not in parsed


@pytest.mark.asyncio
async def test_fetch_error_raises(monkeypatch):
    async def fake_fetch(plan_id=None):
        raise ValueError("SimBrief error: No OFP found")

    monkeypatch.setattr(server, "_fetch", fake_fetch)

    with pytest.raises(ValueError, match="SimBrief error"):
        await server.get_flight_summary()
