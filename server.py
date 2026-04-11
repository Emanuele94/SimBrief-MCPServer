#!/usr/bin/env python3
"""SimBrief MCP Server — access your SimBrief flight plans from Claude."""

import json
from datetime import UTC, datetime

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SimBrief Flight Planning")

PILOT_ID = "1211629"
SIMBRIEF_API = "https://www.simbrief.com/api/xml.fetcher.php"


# ── helpers ──────────────────────────────────────────────────────────────────


def _atis(obj) -> str:
    """Format ATIS — may be a plain string or a structured dict from an online network."""
    if not obj:
        return "N/A"
    if isinstance(obj, dict):
        msg = obj.get("message") or obj.get("text") or ""
        letter = obj.get("letter", "")
        network = obj.get("network", "")
        issued = obj.get("issued", "")
        header = f"[{network}] Info {letter} ({issued})" if letter else f"[{network}]"
        return f"{header}\n    {msg}" if msg else header
    return str(obj)


def _kg(obj) -> str:
    """Extract kg value from a fuel object or return the value as-is."""
    if isinstance(obj, dict):
        return obj.get("kg", str(obj))
    return str(obj) if obj else "-"


def _lbs(obj) -> str:
    """Extract lbs value from a fuel object."""
    if isinstance(obj, dict):
        return obj.get("lbs", "")
    return ""


def _secs_to_hhmm(secs) -> str:
    """Convert seconds (int or str) to HH:MM format."""
    try:
        s = int(secs)
        return f"{s // 3600:02d}:{(s % 3600) // 60:02d}"
    except (ValueError, TypeError):
        return str(secs)


def _unix_to_utc(ts) -> str:
    """Convert a Unix timestamp to a readable UTC string."""
    try:
        return datetime.fromtimestamp(int(ts), tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, TypeError):
        return str(ts)


async def _fetch(plan_id: str | None = None) -> dict:
    """Fetch flight plan data from the SimBrief API."""
    params: dict = {"userid": PILOT_ID, "json": "1"}
    if plan_id:
        params["id"] = plan_id
    async with httpx.AsyncClient() as client:
        resp = await client.get(SIMBRIEF_API, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    status = data.get("fetch", {}).get("status", "")
    if "error" in status.lower():
        raise ValueError(f"SimBrief error: {status}")
    return data


# ── tools ─────────────────────────────────────────────────────────────────────


@mcp.tool()
async def get_flight_summary(plan_id: str | None = None) -> str:
    """
    High-level summary of a flight plan: flight number, aircraft, route, distance,
    cruise altitude, estimated times and total fuel.
    Leave plan_id empty to get the latest dispatch.
    """
    d = await _fetch(plan_id)
    g = d.get("general", {})
    orig = d.get("origin", {})
    dest = d.get("destination", {})
    t = d.get("times", {})
    fuel = d.get("fuel", {})
    ac = d.get("aircraft", {})
    p = d.get("params", {})

    return "\n".join(
        [
            "═══ FLIGHT SUMMARY ═══",
            f"  Flight:       {g.get('icao_airline', '')}{g.get('flight_number', '')}",
            f"  Aircraft:     {ac.get('icaocode', '')} ({ac.get('base_type', '')})  Reg: {ac.get('reg', '')}",
            f"  Route:        {orig.get('icao_code', '')} RWY {orig.get('plan_rwy', '')} → "
            f"{dest.get('icao_code', '')} RWY {dest.get('plan_rwy', '')}",
            f"  Distance:     {g.get('gc_distance', '-')} nm GC / {g.get('route_distance', '-')} nm route",
            f"  Cruise:       FL{g.get('initial_altitude', '')}  {g.get('cruise_profile', '')}",
            f"  Avg wind:     {g.get('avg_wind_comp', '')} kt  Dir {g.get('avg_wind_dir', '')}",
            f"  ETE:          {_secs_to_hhmm(t.get('est_time_enroute', 0))}  |  Block: {_secs_to_hhmm(t.get('est_block', 0))}",
            f"  PAX:          {g.get('passengers', '-')}",
            f"  Trip Fuel:    {g.get('total_burn', '-')} kg",
            f"  Takeoff Fuel: {_kg(fuel.get('plan_takeoff'))} kg",
            f"  Plan ID:      {p.get('request_id', '')}",
            f"  Generated:    {_unix_to_utc(p.get('time_generated', ''))}",
        ]
    )


@mcp.tool()
async def get_weather(plan_id: str | None = None) -> str:
    """
    Current weather: METAR, TAF and ATIS for departure, arrival and alternate airports.
    Leave plan_id empty to get the latest dispatch.
    """
    d = await _fetch(plan_id)
    orig = d.get("origin", {})
    dest = d.get("destination", {})
    altn = d.get("alternate", {})

    lines = [
        "═══ WEATHER ═══",
        "",
        f"▶ DEPARTURE: {orig.get('icao_code', '')} / {orig.get('iata_code', '')}",
        f"  METAR: {orig.get('metar') or 'N/A'}",
        f"  TAF:   {orig.get('taf') or 'N/A'}",
        f"  ATIS:  {_atis(orig.get('atis'))}",
        "",
        f"▶ ARRIVAL: {dest.get('icao_code', '')} / {dest.get('iata_code', '')}",
        f"  METAR: {dest.get('metar') or 'N/A'}",
        f"  TAF:   {dest.get('taf') or 'N/A'}",
        f"  ATIS:  {_atis(dest.get('atis'))}",
    ]
    if altn.get("icao_code"):
        lines += [
            "",
            f"▶ ALTERNATE: {altn.get('icao_code', '')} / {altn.get('iata_code', '')}",
            f"  METAR: {altn.get('metar') or 'N/A'}",
            f"  TAF:   {altn.get('taf') or 'N/A'}",
        ]
    return "\n".join(lines)


@mcp.tool()
async def get_fuel_plan(plan_id: str | None = None) -> str:
    """
    Detailed fuel breakdown: taxi, trip burn, contingency, alternate burn, reserve,
    minimum and planned takeoff fuel, plus any extra fuel buckets.
    Leave plan_id empty to get the latest dispatch.
    """
    d = await _fetch(plan_id)
    fuel = d.get("fuel", {})
    fuel_extra = d.get("fuel_extra", {})

    lines = [
        "═══ FUEL PLAN ═══",
        f"  {'Item':<22} {'kg':>8}   {'lbs':>10}",
        "  " + "─" * 45,
    ]
    for key, label in [
        ("taxi", "Taxi"),
        ("enroute_burn", "Trip Burn"),
        ("contingency", "Contingency"),
        ("alternate_burn", "Alternate Burn"),
        ("reserve", "Reserve"),
        ("min_takeoff", "Min Takeoff"),
        ("plan_takeoff", "Plan Takeoff"),
    ]:
        obj = fuel.get(key, {})
        kg = _kg(obj)
        lbs = _lbs(obj)
        lines.append(f"  {label:<22} {kg:>8}   {lbs:>10}")

    buckets = fuel_extra.get("bucket", [])
    if buckets:
        if isinstance(buckets, dict):
            buckets = [buckets]
        extra = [
            b
            for b in buckets
            if isinstance(b, dict) and _kg(b.get("fuel", "")) not in ("-", "0", "")
        ]
        if extra:
            lines += ["", "  Extra fuel:"]
            for b in extra:
                lines.append(f"    {b.get('label', '?'):<20} {_kg(b.get('fuel'))} kg")

    return "\n".join(lines)


@mcp.tool()
async def get_weights(plan_id: str | None = None) -> str:
    """
    Aircraft weight breakdown: OEW, payload, passenger count, ZFW, TOW,
    ramp weight and landing weight.
    Leave plan_id empty to get the latest dispatch.
    """
    d = await _fetch(plan_id)
    w = d.get("weights", {})

    lines = ["═══ WEIGHTS ═══", ""]
    for key, label in [
        ("oew", "Operating Empty Weight"),
        ("payload", "Payload"),
        ("pax_count", "Passengers"),
        ("est_zfw", "Zero Fuel Weight"),
        ("est_tow", "Takeoff Weight"),
        ("est_ramp", "Ramp Weight"),
        ("est_ldw", "Landing Weight"),
    ]:
        val = w.get(key, "-")
        kg = _kg(val)
        lbs = _lbs(val)
        suffix = f" kg  ({lbs} lbs)" if lbs else " kg" if key != "pax_count" else ""
        lines.append(f"  {label:<25} {kg}{suffix}")
    return "\n".join(lines)


@mcp.tool()
async def get_times(plan_id: str | None = None) -> str:
    """
    All flight times in UTC: scheduled OUT/OFF/ON/IN, estimated time enroute,
    block time, taxi times, reserve and endurance.
    Leave plan_id empty to get the latest dispatch.
    """
    d = await _fetch(plan_id)
    t = d.get("times", {})
    orig = d.get("origin", {})
    dest = d.get("destination", {})

    return "\n".join(
        [
            "═══ TIMES (UTC) ═══",
            f"  Departure: {orig.get('icao_code', '')}  →  Arrival: {dest.get('icao_code', '')}",
            "",
            f"  Sched OUT:          {_unix_to_utc(t.get('sched_out'))}",
            f"  Sched OFF:          {_unix_to_utc(t.get('sched_off'))}",
            f"  Sched ON:           {_unix_to_utc(t.get('sched_on'))}",
            f"  Sched IN:           {_unix_to_utc(t.get('sched_in'))}",
            "",
            f"  Est. Time Enroute:  {_secs_to_hhmm(t.get('est_time_enroute', 0))}",
            f"  Block Time:         {_secs_to_hhmm(t.get('est_block', 0))}",
            f"  Taxi Out:           {_secs_to_hhmm(t.get('taxi_out', 0))}",
            f"  Taxi In:            {_secs_to_hhmm(t.get('taxi_in', 0))}",
            f"  Reserve Time:       {_secs_to_hhmm(t.get('reserve_time', 0))}",
            f"  Endurance:          {_secs_to_hhmm(t.get('endurance', 0))}",
        ]
    )


@mcp.tool()
async def get_atc_flightplan(plan_id: str | None = None) -> str:
    """
    ATC flight plan string ready for filing, including route, callsign,
    flight type, flight rules and equipment codes.
    Leave plan_id empty to get the latest dispatch.
    """
    d = await _fetch(plan_id)
    atc = d.get("atc", {})
    ac = d.get("aircraft", {})

    return "\n".join(
        [
            "═══ ATC FLIGHT PLAN ═══",
            "",
            f"  Callsign:    {atc.get('callsign', '')}",
            f"  Flight type: {atc.get('flight_type', '')} / {atc.get('flight_rules', '')}",
            f"  Aircraft:    {ac.get('icaocode', '')}  Equip: {ac.get('equip', '')}",
            f"  Speed:       {atc.get('initial_spd', '')}",
            "",
            "  Route:",
            f"    {atc.get('route', '')}",
            "",
            "  Full ATC string:",
            f"    {atc.get('flightplan_text', '')}",
        ]
    )


@mcp.tool()
async def get_aircraft_info(plan_id: str | None = None) -> str:
    """
    Aircraft details: ICAO/IATA type codes, registration, engines,
    equipment codes and passenger capacity.
    Leave plan_id empty to get the latest dispatch.
    """
    d = await _fetch(plan_id)
    ac = d.get("aircraft", {})

    lines = ["═══ AIRCRAFT ═══", ""]
    for key, label in [
        ("icaocode", "ICAO Code"),
        ("iata_code", "IATA Code"),
        ("base_type", "Base Type"),
        ("name", "Name"),
        ("reg", "Registration"),
        ("selcal", "SELCAL"),
        ("equip", "Equipment"),
        ("transponder", "Transponder"),
        ("engines", "Engines"),
        ("pax_count", "Max PAX"),
        ("supports_tlr", "Supports TLR"),
    ]:
        val = ac.get(key, "")
        if val:
            lines.append(f"  {label:<22} {val}")
    return "\n".join(lines)


@mcp.tool()
async def get_navlog(plan_id: str | None = None, max_fixes: int = 50) -> str:
    """
    Full navigation log with all waypoints: identifier, type, altitude,
    leg distance, leg time and fuel burn per leg.
    Use max_fixes to limit the number of fixes shown (default 50).
    Leave plan_id empty to get the latest dispatch.
    """
    d = await _fetch(plan_id)
    fixes = d.get("navlog", {}).get("fix", [])
    if isinstance(fixes, dict):
        fixes = [fixes]

    total = len(fixes)
    shown = fixes[:max_fixes]

    lines = [
        f"═══ NAVLOG — {total} fixes total, showing {len(shown)} ═══",
        f"  {'#':<4} {'IDENT':<8} {'TYPE':<10} {'ALT ft':<9} {'DIST nm':<9} {'TIME':<7} {'FUEL kg'}",
        "  " + "─" * 62,
    ]
    for i, fix in enumerate(shown, 1):
        ident = str(fix.get("ident") or fix.get("name") or "")[:7]
        ftype = str(fix.get("type", ""))[:9]
        alt = str(fix.get("altitude_feet", "-"))
        dist = str(fix.get("distance", "-"))
        tleg = str(fix.get("time_leg", "-"))
        fuel = _kg(fix.get("fuel_leg", "-"))
        lines.append(f"  {i:<4} {ident:<8} {ftype:<10} {alt:<9} {dist:<9} {tleg:<7} {fuel}")

    if total > max_fixes:
        lines.append(f"\n  … {total - max_fixes} more fixes not shown (increase max_fixes)")
    return "\n".join(lines)


@mcp.tool()
async def get_notams(plan_id: str | None = None) -> str:
    """
    All NOTAMs for the flight (departure, arrival and en-route).
    Leave plan_id empty to get the latest dispatch.
    """
    d = await _fetch(plan_id)
    recs = d.get("notams", {}).get("notamdrec", [])
    if isinstance(recs, dict):
        recs = [recs]

    if not recs:
        return "No NOTAMs found for this flight plan."

    lines = [f"═══ NOTAMs — {len(recs)} total ═══"]
    for i, n in enumerate(recs, 1):
        icao = n.get("icao", "")
        notam_id = n.get("notam_id", "")
        text = n.get("notam") or n.get("text") or ""
        lines.append(f"\n[{i}] {icao} — {notam_id}")
        if text:
            lines.append(f"  {str(text)[:500]}")
    return "\n".join(lines)


@mcp.tool()
async def get_alternate_info(plan_id: str | None = None) -> str:
    """
    Alternate airport details: ICAO code, planned runway, elevation,
    weather and alternate navlog.
    Leave plan_id empty to get the latest dispatch.
    """
    d = await _fetch(plan_id)
    altn = d.get("alternate", {})

    if not altn.get("icao_code"):
        return "No alternate airport in this flight plan."

    fixes = altn.get("alternate_navlog", {}).get("fix", [])
    if isinstance(fixes, dict):
        fixes = [fixes]

    lines = [
        "═══ ALTERNATE AIRPORT ═══",
        f"  ICAO:       {altn.get('icao_code', '')} / {altn.get('iata_code', '')}",
        f"  Runway:     {altn.get('plan_rwy', '')}",
        f"  Elevation:  {altn.get('elevation', '')} ft",
        f"  METAR: {altn.get('metar') or 'N/A'}",
        f"  TAF:   {altn.get('taf') or 'N/A'}",
        "",
        f"  Alternate navlog ({len(fixes)} fixes):",
    ]
    for fix in fixes[:15]:
        ident = fix.get("ident") or fix.get("name") or ""
        lines.append(
            f"    {ident:<8} {str(fix.get('altitude_feet', ''))} ft  "
            f"{str(fix.get('distance', ''))} nm"
        )
    return "\n".join(lines)


@mcp.tool()
async def get_performance(plan_id: str | None = None) -> str:
    """
    Takeoff and landing performance data (TLR): takeoff distance, climb performance
    and landing calculations, if available for this aircraft type.
    Leave plan_id empty to get the latest dispatch.
    """
    d = await _fetch(plan_id)
    tlr = d.get("tlr", {})

    if not tlr:
        return "No TLR performance data available for this flight plan."

    lines = ["═══ PERFORMANCE (TLR) ═══", ""]

    to_data = tlr.get("takeoff", {})
    if to_data:
        lines.append("TAKEOFF:")
        for k, v in to_data.items():
            if v and not isinstance(v, (dict, list)):
                lines.append(f"  {k:<35} {v}")

    ldg_data = tlr.get("landing", {})
    if ldg_data:
        lines += ["", "LANDING:"]
        for k, v in ldg_data.items():
            if v and not isinstance(v, (dict, list)):
                lines.append(f"  {k:<35} {v}")

    return "\n".join(lines)


@mcp.tool()
async def get_crew(plan_id: str | None = None) -> str:
    """
    Crew assignment for the flight: captain, first officer, dispatcher,
    purser and flight attendants.
    Leave plan_id empty to get the latest dispatch.
    """
    d = await _fetch(plan_id)
    crew = d.get("crew", {})

    if not any(v for v in crew.values() if v):
        return "No crew information in this flight plan."

    lines = ["═══ CREW ═══", ""]
    for key, label in [
        ("cpt", "Captain"),
        ("fo", "First Officer"),
        ("dx", "Dispatcher"),
        ("pu", "Purser"),
        ("fa", "Flight Attendants"),
    ]:
        val = crew.get(key, "")
        if val:
            lines.append(f"  {label:<22} {val}")
    pid = crew.get("pilot_id", "")
    if pid:
        lines.append(f"  {'Pilot ID':<22} {pid}")
    return "\n".join(lines)


@mcp.tool()
async def get_impacts(plan_id: str | None = None) -> str:
    """
    Performance sensitivity analysis: fuel and time impact of changing
    cruise altitude or cost index.
    Leave plan_id empty to get the latest dispatch.
    """
    d = await _fetch(plan_id)
    impacts = d.get("impacts", {})

    if not impacts:
        return "No impact analysis available for this flight plan."

    lines = [
        "═══ PERFORMANCE SENSITIVITY ═══",
        f"  {'Scenario':<15}  {'FL':>5}  {'Burn diff':>10}  {'Trip burn':>10}  {'Time diff':>10}",
        "  " + "─" * 57,
    ]
    for key, label in [
        ("minus_6000ft", "FL -6000 ft"),
        ("minus_4000ft", "FL -4000 ft"),
        ("minus_2000ft", "FL -2000 ft"),
        ("plus_2000ft", "FL +2000 ft"),
        ("plus_4000ft", "FL +4000 ft"),
        ("lower_ci", "Lower CI"),
        ("higher_ci", "Higher CI"),
    ]:
        val = impacts.get(key)
        if isinstance(val, dict) and val:
            fl = val.get("initial_fl", "-")
            burn_diff = val.get("burn_difference", "-")
            burn = val.get("enroute_burn", "-")
            time_diff = (
                _secs_to_hhmm(val.get("time_difference", 0)) if val.get("time_difference") else "-"
            )
            try:
                bd = int(burn_diff)
                burn_diff = f"+{bd}" if bd > 0 else str(bd)
            except (ValueError, TypeError):
                pass
            lines.append(
                f"  {label:<15}  {fl:>5}  {burn_diff:>8} kg  {burn:>8} kg  {time_diff:>10}"
            )
    return "\n".join(lines)


@mcp.tool()
async def get_full_flight_plan(plan_id: str | None = None) -> str:
    """
    Complete flight plan as raw JSON (all sections except navlog, notams and alternate navlog).
    Useful for deep analysis or accessing fields not covered by the other tools.
    Leave plan_id empty to get the latest dispatch.
    """
    d = await _fetch(plan_id)
    # Remove verbose sections — use dedicated tools for those
    for key in ("navlog", "notams", "alternate"):
        d.pop(key, None)
    return json.dumps(d, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
