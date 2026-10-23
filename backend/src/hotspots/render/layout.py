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

ICON_ASPECT = 1.5          # icon width / height (volcano silhouette)
LABEL_CHAR_PCT = 0.95      # approx. label character width, % of map width
LABEL_HEIGHT_PCT = 3.6     # approx. label height, % of map height


def shade_class(fade_step: int, shades: list[str]) -> str:
    return "bg--black" if fade_step == 0 else shades[min(fade_step, len(shades)) - 1]


def marker_list(markers: list[Marker], *, min_pct: float, max_pct: float, max_markers: int,
                shades: list[str]) -> list[dict]:
    """All markers, ranked, for close-up views (the browser projects and filters them)."""
    return [{"n": m.name, "lat": m.lat, "lon": m.lon, "w": icon_pct(m, min_pct, max_pct),
             "c": shade_class(m.fade_step, shades), "a": m.age_hours} for m in markers[:max_markers]]


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
                "c": shade_class(m.fade_step, shades), "a": m.age_hours} for m, x, y in inside]
    icons = [{"x": e["x"], "y": e["y"] / 2, "hw": e["w"] / 2, "hh": e["w"] / ICON_ASPECT / 2,
              "n": e["n"], "a": e["a"]} for e in entries]
    labels = [{"t": entries[lb.pop("i")]["n"], **lb}
              for lb in place(icons, max_labels, char_w=LABEL_CHAR_PCT, text_h=LABEL_HEIGHT_PCT / 2)]
    entries.sort(key=lambda e: -e["w"])
    return entries, labels
