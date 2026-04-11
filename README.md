# SimBrief MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that gives Claude Desktop direct access to your SimBrief flight plans — no Cloudflare, no OAuth, no infrastructure required.

## Features

14 tools covering every section of a SimBrief OFP:

| Tool | Description |
|---|---|
| `get_flight_summary` | Flight number, aircraft, route, distance, cruise, ETE, fuel |
| `get_weather` | METAR, TAF and ATIS for departure, arrival and alternate |
| `get_fuel_plan` | Full fuel breakdown: taxi, trip, contingency, alternate, reserve, extra |
| `get_weights` | OEW, payload, ZFW, TOW, ramp weight, landing weight |
| `get_times` | Scheduled OUT/OFF/ON/IN, ETE, block time, taxi, endurance |
| `get_atc_flightplan` | ATC flight plan string ready for filing |
| `get_aircraft_info` | Type, registration, engines, equipment codes |
| `get_navlog` | Full waypoint list with altitude, distance and fuel per leg |
| `get_notams` | All NOTAMs (departure, arrival, en-route) |
| `get_alternate_info` | Alternate airport details and navlog |
| `get_performance` | Takeoff & landing performance (TLR), if available |
| `get_crew` | Captain, first officer, dispatcher, purser, flight attendants |
| `get_impacts` | Fuel and time sensitivity to altitude and cost index changes |
| `get_full_flight_plan` | Complete raw JSON for custom analysis |

All tools accept an optional `plan_id` parameter — leave it empty to always fetch your latest dispatch.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- A [SimBrief](https://www.simbrief.com) account (free)

## Installation

```bash
git clone https://github.com/Emanuele94/SimBrief-MCPServer.git
cd SimBrief-MCPServer
uv sync
```

## Configuration

Open `server.py` and set your SimBrief Pilot ID (found under SimBrief → Account Settings → **Pilot ID**):

```python
PILOT_ID = "your_pilot_id_here"
```

## Claude Desktop integration

Add the following to your `claude_desktop_config.json`:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "simbrief": {
      "command": "uv",
      "args": [
        "run",
        "--project", "/absolute/path/to/SimBrief-MCPServer",
        "python",
        "/absolute/path/to/SimBrief-MCPServer/server.py"
      ]
    }
  }
}
```

Then restart Claude Desktop. The SimBrief tools will appear automatically.

## Usage examples

Once connected, you can ask Claude things like:

- *"What's my latest flight plan?"*
- *"Show me the weather for my next flight."*
- *"How much fuel do I have planned and what's the breakdown?"*
- *"Give me the full ATC flight plan string."*
- *"What happens to fuel burn if I fly 2000 ft lower?"*
- *"Show me the first 20 waypoints of my navlog."*

## Development

Install dev dependencies:

```bash
uv sync --all-extras
```

Run tests:

```bash
uv run pytest -v
```

Lint and format:

```bash
uv run ruff check .
uv run ruff format .
```

All tests run fully offline — the SimBrief API is mocked so no internet connection or real Pilot ID is required.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes and add tests
4. Ensure the CI pipeline passes locally (`uv run pytest && uv run ruff check .`)
5. Open a Pull Request against `main`

PRs must pass all checks (tests + lint) before they can be merged.

## License

MIT
