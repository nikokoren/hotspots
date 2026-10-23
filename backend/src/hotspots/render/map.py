"""Minimalist e-paper world map with volcano silhouette markers.

Projection: Equal Earth (equal-area, pleasant world shape) with a configurable
central meridian. Regional views crop the same projection. Output is plain
black-and-white SVG so it renders crisply on every TRMNL panel (1-bit through
16 greys); recency is shown with fill style instead of opacity:

    fade step 0 (≤ 24 h)  solid
    fade step 1 (≤ 48 h)  hatched
    fade step 2 (≤ 72 h)  outline

Rendering consumes models.Marker only, never raw source data.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from xml.sax.saxutils import escape

from hotspots.models import Marker

TRMNL_WIDTH = 800
TRMNL_HEIGHT = 480

# Equal Earth constants (Šavrič, Patterson & Jenny 2018).
A1, A2, A3, A4 = 1.340264, -0.081106, 0.000893, 0.003796
M = math.sqrt(3) / 2

# Volcano silhouette on a unit square centred at the origin (crater notch, no smoke).
VOLCANO_PATH = "M-1 .7 L-.32 -.62 L-.13 -.44 L0 -.6 L.13 -.44 L.32 -.62 L1 .7 Z"


@dataclass(frozen=True)
class View:
    key: str
    label: str
    center_lon: float
    lon_min: float = -180.0   # relative to nothing; may exceed ±180 to cross the antimeridian
    lon_max: float = 180.0
    lat_min: float = -90.0
    lat_max: float = 90.0
    detail: str = "110m"

    @property
    def is_world(self) -> bool:
        return self.lon_max - self.lon_min >= 360


VIEWS: tuple[View, ...] = (
    View("world-pacific", "World (Pacific centred)", 150),
    View("world-atlantic", "World (Atlantic centred)", 10),
    View("world-americas", "World (Americas centred)", -90),
    View("europe", "Europe & Mediterranean", 15, -30, 45, 26, 70, "50m"),
    View("africa-middle-east", "Africa & Middle East", 30, -25, 65, -38, 40, "50m"),
    View("north-america", "North America & Alaska", -125, -192, -55, 12, 70, "50m"),
    View("central-america", "Central America & Caribbean", -82, -110, -58, 6, 24, "50m"),
    View("south-america", "South America", -70, -95, -30, -56, 14, "50m"),
    View("east-asia", "Japan, Kurils & Kamchatka", 145, 120, 172, 22, 62, "50m"),
    View("southeast-asia", "Indonesia & Philippines", 115, 93, 135, -12, 21, "50m"),
    View("southwest-pacific", "Melanesia, Tonga & New Zealand", 168, 140, 190, -48, 0, "50m"),
)
VIEWS_BY_KEY = {v.key: v for v in VIEWS}


def equal_earth(lon: float, lat: float) -> tuple[float, float]:
    """lon is already relative to the central meridian (may exceed ±180 when unwrapped)."""
    lam, phi = math.radians(lon), math.radians(lat)
    th = math.asin(M * math.sin(phi))
    t2 = th * th
    t6 = t2 * t2 * t2
    x = lam * math.cos(th) / (M * (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2)))
    y = th * (A1 + A2 * t2 + t6 * (A3 + A4 * t2))
    return x, -y  # SVG y grows downward


def _rel(lon: float, center: float) -> float:
    return (lon - center + 180) % 360 - 180


@lru_cache(maxsize=None)
def _land(detail: str) -> list[list[float]]:
    with resources.files("hotspots.render.data").joinpath(f"land_{detail}.json").open() as f:
        return json.load(f)["rings"]


class Frame:
    """Maps projected coordinates of a view onto a width×height pixel canvas."""

    def __init__(self, view: View, width: int, height: int, pad_px: float = 6):
        self.view, self.width, self.height = view, width, height
        if view.is_world:
            xs, ys = [-2.7066, 2.7066], [-1.3173, 1.3173]
        else:
            xs, ys = [], []
            steps = 24
            for i in range(steps + 1):
                lon = view.lon_min + (view.lon_max - view.lon_min) * i / steps
                lat = view.lat_min + (view.lat_max - view.lat_min) * i / steps
                for lo, la in ((lon, view.lat_min), (lon, view.lat_max), (view.lon_min, lat), (view.lon_max, lat)):
                    x, y = equal_earth(lo - view.center_lon, la)
                    xs.append(x)
                    ys.append(y)
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        scale = min((width - 2 * pad_px) / (x1 - x0), (height - 2 * pad_px) / (y1 - y0))
        self.scale = scale
        self.ox = width / 2 - scale * (x0 + x1) / 2
        self.oy = height / 2 - scale * (y0 + y1) / 2

    def px(self, rel_lon: float, lat: float) -> tuple[float, float]:
        x, y = equal_earth(rel_lon, lat)
        return self.ox + self.scale * x, self.oy + self.scale * y

    def point(self, lon: float, lat: float) -> tuple[float, float]:
        return self.px(_rel(lon, self.view.center_lon), lat)

    def contains(self, x: float, y: float, margin: float = 0) -> bool:
        return -margin <= x <= self.width + margin and -margin <= y <= self.height + margin


def _land_path(frame: Frame) -> str:
    """Coastline path. Rings crossing the seam are unwrapped and drawn twice
    (±360°) and clipped by the sphere outline."""
    c = frame.view.center_lon
    parts = []
    for ring in _land(frame.view.detail):
        if max(abs(v) for v in ring[1::2]) >= 89.9:
            # Pole-encircling ring: start it at the map edge so the pole closure stays hidden.
            k = max(range(0, len(ring), 2), key=lambda i: abs(_rel(ring[i], c)))
            ring = ring[k:] + ring[:k]
        rel = []
        prev = None
        for i in range(0, len(ring), 2):
            r = _rel(ring[i], c)
            if prev is not None:
                while r - prev > 180:
                    r -= 360
                while prev - r > 180:
                    r += 360
            rel.append((r, ring[i + 1]))
            prev = r
        if abs(rel[-1][0] - rel[0][0]) > 180:
            # Ring encircles a pole (Antarctica): close it along the pole line.
            pole = -90.0 if sum(p[1] for p in rel) < 0 else 90.0
            rel += [(rel[-1][0], pole), (rel[0][0], pole)]
        lo, hi = min(p[0] for p in rel), max(p[0] for p in rel)
        shifts = [0.0]
        if lo < -180:
            shifts.append(360.0)
        if hi > 180:
            shifts.append(-360.0)
        for sh in shifts:
            pts = [frame.px(r + sh, lat) for r, lat in rel]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            if max(xs) < 0 or min(xs) > frame.width or max(ys) < 0 or min(ys) > frame.height:
                continue
            if max(xs) - min(xs) < 1.5 and max(ys) - min(ys) < 1.5:
                continue
            out = [pts[0]]
            for p in pts[1:]:
                if abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1]) >= 0.8:
                    out.append(p)
            if len(out) < 3:
                continue
            parts.append("M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in out) + "Z")
    return "".join(parts)


def _outline_path(frame: Frame) -> str:
    pts = [frame.px(180, lat) for lat in range(-90, 91, 3)] + [frame.px(-180, lat) for lat in range(90, -91, -3)]
    return "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z"


def _graticule(frame: Frame) -> str:
    """Equator only — a quiet orientation cue."""
    pts = [frame.px(lon, 0) for lon in range(-180, 181, 5)]
    return "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts)


def icon_px(size: float, min_px: float, max_px: float) -> float:
    return min_px + (max_px - min_px) * max(0.0, min(1.0, size))


def render_svg(markers: list[Marker], view: View, *, width: int = TRMNL_WIDTH, height: int = TRMNL_HEIGHT,
               min_px: float = 10, max_px: float = 34, max_markers: int = 30, labels: int = 0) -> str:
    frame = Frame(view, width, height)
    visible = []
    for m in markers:
        x, y = frame.point(m.lon, m.lat)
        if frame.contains(x, y):
            visible.append((m, x, y))
    visible = visible[:max_markers]  # markers arrive ranked by score

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        'font-family="Helvetica, Arial, sans-serif">',
        '<defs>',
        '<pattern id="hatch" patternUnits="userSpaceOnUse" width="3" height="3" patternTransform="rotate(45)">'
        '<rect width="3" height="3" fill="#fff"/><rect width="1.5" height="3" fill="#000"/></pattern>',
        f'<clipPath id="sphere"><path d="{_outline_path(frame)}"/></clipPath>',
        f'<path id="v" d="{VOLCANO_PATH}"/>',
        '</defs>',
        f'<rect width="{width}" height="{height}" fill="#fff"/>',
        '<g clip-path="url(#sphere)">',
        f'<path d="{_land_path(frame)}" fill="#fff" stroke="#000" stroke-width="0.8" stroke-linejoin="round"/>',
        f'<path d="{_graticule(frame)}" fill="none" stroke="#000" stroke-width="0.5" stroke-dasharray="1 4"/>',
        '</g>',
    ]
    if view.is_world:
        out.append(f'<path d="{_outline_path(frame)}" fill="none" stroke="#000" stroke-width="1"/>')

    # Largest first so smaller markers stay visible on top in dense clusters.
    for m, x, y in sorted(visible, key=lambda t: -t[0].size):
        s = icon_px(m.size, min_px, max_px) / 2
        fill = {0: "#000", 1: "url(#hatch)"}.get(m.fade_step, "#fff")
        tr = f'transform="translate({x:.1f} {y:.1f}) scale({s:.2f})"'
        out.append(f'<use href="#v" {tr} fill="none" stroke="#fff" stroke-width="{4 / s:.3f}" stroke-linejoin="round"/>')
        out.append(f'<use href="#v" {tr} fill="{fill}" stroke="#000" stroke-width="{1.4 / s:.3f}" stroke-linejoin="round">'
                   f'<title>{escape(m.name)}</title></use>')

    if labels:
        out.extend(_labels(visible, labels, width, height, min_px, max_px))

    out.append("</svg>")
    return "\n".join(out)


LABEL_FONT_PX = 13


def _labels(visible, limit: int, width: int, height: int, min_px: float, max_px: float) -> list[str]:
    """Greedy placement for the newest markers: right, left, above, below; skip if nothing fits."""
    boxes = []  # (x0, y0, x1, y1) already occupied
    for m, x, y in visible:
        s = icon_px(m.size, min_px, max_px) / 2
        boxes.append((x - s, y - s, x + s, y + s))
    out = []
    placed = 0
    for m, x, y in sorted(visible, key=lambda t: (t[0].age_hours, -t[0].size)):
        if placed >= limit:
            break
        s = icon_px(m.size, min_px, max_px) / 2
        w, h = 0.56 * LABEL_FONT_PX * len(m.name), LABEL_FONT_PX
        candidates = [  # (text x, baseline y, anchor, box)
            (x + s + 3, y + h / 3, "start", (x + s + 3, y - h / 2, x + s + 3 + w, y + h / 2)),
            (x - s - 3, y + h / 3, "end", (x - s - 3 - w, y - h / 2, x - s - 3, y + h / 2)),
            (x, y - s - 4, "middle", (x - w / 2, y - s - 4 - h, x + w / 2, y - s - 4)),
            (x, y + s + h, "middle", (x - w / 2, y + s + 2, x + w / 2, y + s + 2 + h)),
        ]
        for tx, ty, anchor, box in candidates:
            if box[0] < 2 or box[2] > width - 2 or box[1] < 2 or box[3] > height - 2:
                continue
            if any(_overlaps(box, b) for b in boxes):
                continue
            boxes.append(box)
            placed += 1
            out.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="{anchor}" font-size="{LABEL_FONT_PX}" '
                       f'stroke="#fff" stroke-width="3" paint-order="stroke" fill="#000">{escape(m.name)}</text>')
            break
    return out


def _overlaps(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
