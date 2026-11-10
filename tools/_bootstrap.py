"""Load dependency-free integration modules without importing Home Assistant."""

import importlib
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "commax_wallpad_core"


def core(name):
    if PACKAGE not in sys.modules:
        module = types.ModuleType(PACKAGE)
        module.__path__ = [str(ROOT / "custom_components" / "commax_wallpad")]
        sys.modules[PACKAGE] = module
    return importlib.import_module(f"{PACKAGE}.{name}")
