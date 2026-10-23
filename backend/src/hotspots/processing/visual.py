"""Map activity to marker size, recency opacity, eligibility and ranking (spec §4)."""

from __future__ import annotations


def marker_size(score: float, min_px: float, max_px: float) -> float:
    raise NotImplementedError


def recency_opacity(age_hours: float, full_hours: float, expire_hours: float) -> float:
    raise NotImplementedError


def build_markers(activities, config: dict):
    raise NotImplementedError
