"""Marker encoding for the recipe.

Icon width is a percentage of the map width and the shade is a TRMNL
background class, so the same payload scales to every screen and layout.
World views also get positions (percent of the 2:1 map box) here; close-ups are projected
in the browser by the framework map. Labels are placed in the browser for every map, at
the size each layout gives it.
"""

from __future__ import annotations

from hotspots.models import Marker
from hotspots.render.views import Frame, View

# Icon geometry, shared with the recipe (trmnl/src/shared.liquid) and build_icons.py:
# both drawings sit on one 1345x1306 canvas (halo room included) so the cone lines up.
ICON_ASPECT = 1345 / 1306                  # canvas width / height
ICON_ANCHOR_Y = 0.683                      # the volcano's location: centre of the cone
ICON_BOX = {                               # visible shape, fractions of the canvas
    "lava": (0.052, 0.420, 0.948, 0.946),  # cone with lava channel: heat detected
    "erupt": (0.052, 0.054, 0.948, 0.946),  # cone with plume: GVP continuing eruption
}
# Short country names for the recipe's volcano list (GVP spells countries out in full).
COUNTRY_SHORT = {"United States": "USA", "Papua New Guinea": "PNG", "United Kingdom": "UK",
                 "Saint Vincent and the Grenadines": "St Vincent", "Saint Kitts and Nevis": "St Kitts & Nevis"}


def shade_class(fade_step: int, shades: list[str]) -> str:
    return "bg--black" if fade_step == 0 else shades[min(fade_step, len(shades)) - 1]


def marker_list(markers: list[Marker], *, min_pct: float, max_pct: float, max_markers: int,
                shades: list[str]) -> list[dict]:
    """All markers, ranked, for the framework map (projected in the browser) and the volcano list."""
    return [{"n": m.name, "lat": m.lat, "lon": m.lon, "w": icon_pct(m, min_pct, max_pct),
             "c": shade_class(m.fade_step, shades), "a": m.age_hours, "k": icon_kind(m),
             "co": COUNTRY_SHORT.get(m.country, m.country), "s": m.seen}
            for m in markers[:max_markers]]


def icon_kind(m: Marker) -> str:
    return "erupt" if m.erupting else "lava"


def icon_box(x: float, y: float, w: float, kind: str) -> tuple[float, float, float, float]:
    """Visible icon box for an icon of width w anchored at (x, y); any units, y down."""
    h = w / ICON_ASPECT
    left, top = x - w / 2, y - ICON_ANCHOR_Y * h
    bx0, by0, bx1, by1 = ICON_BOX[kind]
    return (left + bx0 * w, top + by0 * h, left + bx1 * w, top + by1 * h)


def icon_pct(m: Marker, min_pct: float, max_pct: float) -> float:
    return round(min_pct + (max_pct - min_pct) * m.size, 2)


def view_markers(markers: list[Marker], view: View, *, min_pct: float, max_pct: float,
                 max_markers: int, shades: list[str]) -> list[dict]:
    """World view: markers in drawing order, largest first; x/y are percent of the 2:1 box."""
    frame = Frame(view)
    inside = []
    for m in markers:
        u, v = frame.uv(m.lon, m.lat)
        if frame.contains(u, v):
            inside.append((m, u * 100, v * 100))
    inside = inside[:max_markers]

    entries = [{"n": m.name, "x": round(x, 2), "y": round(y, 2), "w": icon_pct(m, min_pct, max_pct),
                "c": shade_class(m.fade_step, shades), "a": m.age_hours, "k": icon_kind(m)}
               for m, x, y in inside]
    entries.sort(key=lambda e: -e["w"])
    return entries
