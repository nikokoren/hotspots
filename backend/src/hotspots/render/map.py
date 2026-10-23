"""Minimalist e-paper world map with volcano silhouette markers."""

from __future__ import annotations

TRMNL_WIDTH = 800
TRMNL_HEIGHT = 480


def project(lat: float, lon: float, width: int, height: int) -> tuple[float, float]:
    raise NotImplementedError


def render_svg(markers, width: int = TRMNL_WIDTH, height: int = TRMNL_HEIGHT) -> str:
    raise NotImplementedError
