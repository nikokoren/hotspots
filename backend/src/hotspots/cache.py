"""Caching for the static catalogue, processed observations and last good output.

Static volcano data is cached separately from dynamic observations (spec §6).
"""

from __future__ import annotations

from pathlib import Path


def load_catalogue(cache_dir: Path):
    raise NotImplementedError


def save_catalogue(cache_dir: Path, volcanoes) -> None:
    raise NotImplementedError


def load_last_good(cache_dir: Path):
    raise NotImplementedError


def save_last_good(cache_dir: Path, payload) -> None:
    raise NotImplementedError
