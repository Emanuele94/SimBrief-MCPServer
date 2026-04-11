"""Tests for server startup configuration."""

import importlib
import os
import sys

import pytest


def test_missing_pilot_id_raises():
    """Server must fail with a clear error if SIMBRIEF_PILOT_ID is not set."""
    env_backup = os.environ.pop("SIMBRIEF_PILOT_ID", None)
    sys.modules.pop("server", None)  # force re-import

    try:
        with pytest.raises(RuntimeError, match="SIMBRIEF_PILOT_ID"):
            importlib.import_module("server")
    finally:
        # Restore so other tests keep working
        if env_backup is not None:
            os.environ["SIMBRIEF_PILOT_ID"] = env_backup
        sys.modules.pop("server", None)


def test_valid_pilot_id_loads():
    """Server loads successfully when SIMBRIEF_PILOT_ID is set."""
    os.environ["SIMBRIEF_PILOT_ID"] = "1234567"
    sys.modules.pop("server", None)

    try:
        mod = importlib.import_module("server")
        assert mod.PILOT_ID == "1234567"
    finally:
        sys.modules.pop("server", None)
