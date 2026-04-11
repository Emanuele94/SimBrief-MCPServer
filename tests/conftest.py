"""Shared pytest configuration — runs before any test module is imported."""

import os

# Must be set before `import server` to satisfy the startup env check.
os.environ.setdefault("SIMBRIEF_PILOT_ID", "0000000")
