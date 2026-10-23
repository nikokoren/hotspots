"""Configuration: config/defaults.toml overlaid with environment variables."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = REPO_ROOT / "config" / "defaults.toml"


def load_config(path: Path | None = None) -> dict:
    path = path or Path(os.environ.get("HOTSPOTS_CONFIG", DEFAULT_CONFIG))
    with open(path, "rb") as f:
        return tomllib.load(f)


def firms_map_key() -> str | None:
    """FIRMS key comes only from the environment; never from config files."""
    return os.environ.get("FIRMS_MAP_KEY") or None


def data_dir() -> Path:
    return Path(os.environ.get("HOTSPOTS_DATA_DIR", REPO_ROOT / "data"))
