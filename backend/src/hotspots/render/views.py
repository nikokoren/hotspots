"""Map views and their projection.

Every view is a 2:1 frame in an equirectangular projection (the same family
as the TRMNL earthquake recipe). Regional views use a standard parallel at
their mid-latitude so shapes are not stretched sideways. World views wrap
around a configurable central meridian.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

ASPECT = 2.0  # width / height of every view


@dataclass(frozen=True)
class View:
    key: str
    label: str
    lon_min: float          # may exceed ±180 to cross the antimeridian
    lon_max: float
    lat_min: float = -90.0
    lat_max: float = 90.0
    detail: str = "50m"

    @property
    def is_world(self) -> bool:
        return self.lon_max - self.lon_min >= 360


def world(key: str, label: str, center_lon: float) -> View:
    return View(key, label, center_lon - 180, center_lon + 180, detail="110m")


VIEWS: tuple[View, ...] = (
    world("world-pacific", "World (Pacific centred)", 150),
    world("world-atlantic", "World (Atlantic centred)", 10),
    world("world-americas", "World (Americas centred)", -90),
    View("europe", "Europe & Mediterranean", -28, 45, 27, 68),
    View("africa-middle-east", "Africa & Middle East", -22, 62, -38, 40),
    View("north-america", "North America & Alaska", -190, -58, 12, 72),
    View("central-america", "Central America & Caribbean", -112, -58, 5, 26),
    View("south-america", "South America", -95, -30, -56, 14),
    View("east-asia", "Japan, Kurils & Kamchatka", 122, 172, 22, 62),
    View("southeast-asia", "Indonesia & Philippines", 93, 135, -12, 21),
    View("southwest-pacific", "Melanesia, Tonga & New Zealand", 140, 190, -48, 2),
)
VIEWS_BY_KEY = {v.key: v for v in VIEWS}


def wrap180(lon: float) -> float:
    return (lon + 180) % 360 - 180


class Frame:
    """Maps lon/lat to normalized (u, v) in [0, 1] across the view's 2:1 box."""

    def __init__(self, view: View):
        self.view = view
        self.center_lon = (view.lon_min + view.lon_max) / 2
        if view.is_world:
            self.kx = 1.0
            width, height = 360.0, 180.0
            self.lat_top = 90.0
        else:
            self.kx = math.cos(math.radians((view.lat_min + view.lat_max) / 2))
            width = (view.lon_max - view.lon_min) * self.kx
            height = view.lat_max - view.lat_min
            if width / height < ASPECT:
                width = height * ASPECT
            else:
                height = width / ASPECT
            mid = (view.lat_min + view.lat_max) / 2
            self.lat_top = min(90.0, mid + height / 2)
            if self.lat_top - height < -90:
                self.lat_top = -90 + height
        self.width, self.height = width, height

    def rel_lon(self, lon: float) -> float:
        return wrap180(lon - self.center_lon)

    def uv_rel(self, rel_lon: float, lat: float) -> tuple[float, float]:
        """rel_lon is relative to the centre and may lie outside ±180 (unwrapped rings)."""
        return 0.5 + rel_lon * self.kx / self.width, (self.lat_top - lat) / self.height

    def uv(self, lon: float, lat: float) -> tuple[float, float]:
        return self.uv_rel(self.rel_lon(lon), lat)

    @staticmethod
    def contains(u: float, v: float) -> bool:
        return 0.0 <= u <= 1.0 and 0.0 <= v <= 1.0
