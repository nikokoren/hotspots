"""Marker encoding for the recipe.

Icon width is a percentage of the map width and the shade is a TRMNL
background class, so the same payload scales to every screen and layout.
World views also get positions (percent of the 2:1 map box) and label sides
here; close-ups are projected and labelled in the browser by the framework map.
"""

from __future__ import annotations

from hotspots.models import Marker
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
                 max_markers: int, max_labels: int, shades: list[str]) -> list[dict]:
    """Markers inside the view, ranked list in; returned in drawing order (largest first)."""
    frame = Frame(view)
    inside = []
    for m in markers:
        u, v = frame.uv(m.lon, m.lat)
        if frame.contains(u, v):
            inside.append((m, u * 100, v * 100))
    inside = inside[:max_markers]

    out = []
    for m, x, y in inside:
        out.append({"n": m.name, "x": round(x, 2), "y": round(y, 2),
                    "w": icon_pct(m, min_pct, max_pct),
                    "c": shade_class(m.fade_step, shades), "a": m.age_hours, "l": ""})
    _place_labels(out, max_labels)
    out.sort(key=lambda e: -e["w"])
    return out


def _place_labels(entries: list[dict], limit: int) -> None:
    """Greedy: newest first; try right, left, above, below; skip if nothing fits."""
    boxes = []
    for e in entries:
        hw, hh = e["w"] / 2, e["w"] / ICON_ASPECT  # height in % of map height (2:1 box)
        boxes.append((e["x"] - hw, e["y"] - hh, e["x"] + hw, e["y"] + hh))
    placed = 0
    for e in sorted(entries, key=lambda e: (e["a"], -e["w"])):
        if placed >= limit:
            break
        hw, hh = e["w"] / 2, e["w"] / ICON_ASPECT
        tw, th = LABEL_CHAR_PCT * len(e["n"]), LABEL_HEIGHT_PCT
        x, y = e["x"], e["y"]
        options = {
            "r": (x + hw, y - th / 2, x + hw + tw, y + th / 2),
            "l": (x - hw - tw, y - th / 2, x - hw, y + th / 2),
            "t": (x - tw / 2, y - hh - th, x + tw / 2, y - hh),
            "b": (x - tw / 2, y + hh, x + tw / 2, y + hh + th),
        }
        for side, box in options.items():
            if box[0] < 0 or box[2] > 100 or box[1] < 0 or box[3] > 100:
                continue
            if any(_overlaps(box, b) for b in boxes):
                continue
            boxes.append(box)
            e["l"] = side
            placed += 1
            break


def _overlaps(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
