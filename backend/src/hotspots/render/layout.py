"""Marker encoding for the recipe.

Icon width is a percentage of the map width and the shade is a TRMNL
background class, so the same payload scales to every screen and layout.
World views also get positions (percent of the 2:1 map box) and labels with
leader lines here (render/labels.py); close-ups are projected and labelled in the browser by the framework map.
"""

from __future__ import annotations

from hotspots.models import Marker
from hotspots.render.labels import place
from hotspots.render.views import Frame, View

# Icon geometry, shared with the recipe (trmnl/src/shared.liquid) and build_icons.py:
# both drawings sit on one 1345x1306 canvas (halo room included) so the cone lines up.
ICON_ASPECT = 1345 / 1306                  # canvas width / height
ICON_ANCHOR_Y = 0.683                      # the volcano's location: centre of the cone
ICON_BOX = {                               # visible shape, fractions of the canvas
    "lava": (0.052, 0.420, 0.948, 0.946),  # cone with lava channel: heat detected
    "erupt": (0.052, 0.054, 0.948, 0.946),  # cone with plume: GVP continuing eruption
}
LABEL_CHAR_PCT = 0.95      # approx. label character width, % of map width
LABEL_HEIGHT_PCT = 3.6     # approx. label height, % of map height


def shade_class(fade_step: int, shades: list[str]) -> str:
    return "bg--black" if fade_step == 0 else shades[min(fade_step, len(shades)) - 1]


def marker_list(markers: list[Marker], *, min_pct: float, max_pct: float, max_markers: int,
                shades: list[str]) -> list[dict]:
    """All markers, ranked, for close-up views (the browser projects and filters them)."""
    return [{"n": m.name, "lat": m.lat, "lon": m.lon, "w": icon_pct(m, min_pct, max_pct),
             "c": shade_class(m.fade_step, shades), "a": m.age_hours, "k": icon_kind(m)}
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
                 max_markers: int, max_labels: int, shades: list[str]) -> tuple[list[dict], list[dict]]:
    """World view: (markers in drawing order, largest first; labels with optional leader lines).

    Marker x/y are percent of the 2:1 box. Label and leader coordinates are in map-width
    units (x 0..100, y 0..50); see render/labels.py.
    """
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
    icons = [{"x": e["x"], "y": e["y"] / 2, "box": icon_box(e["x"], e["y"] / 2, e["w"], e["k"]),
              "n": e["n"], "a": e["a"]} for e in entries]
    labels = [{"t": entries[lb.pop("i")]["n"], **lb}
              for lb in place(icons, max_labels, char_w=LABEL_CHAR_PCT, text_h=LABEL_HEIGHT_PCT / 2)]
    entries.sort(key=lambda e: -e["w"])
    return entries, labels
