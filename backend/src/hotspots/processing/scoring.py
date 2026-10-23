"""Relative activity score per volcano (spec §3).

This is a visualization metric, not a measure of eruption magnitude or danger.
"""

from __future__ import annotations


def aggregate(activity, window_hours: float):
    raise NotImplementedError


def score(activity, formula: str) -> float:
    raise NotImplementedError
