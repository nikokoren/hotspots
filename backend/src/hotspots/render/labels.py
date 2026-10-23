"""Label placement with leader lines (world views; mirrored in the recipe's close-up JS).

Geometry is in map-width units: x and y both measured in percent of the map width,
so the 2:1 map spans x 0..100, y 0..50 and distances are isotropic.

Each label, newest volcano first:
1. sits right next to its icon (right, left, above, below) if that spot is free;
2. otherwise moves out to the nearest free spot in one of eight directions and gets a
   leader line back to its icon; the line may not cross another icon or label;
3. otherwise is dropped.
"""

from __future__ import annotations

import math

GAP = 0.4                       # icon edge to label, map-width %
LEADER_STEPS = (4.0, 7.0, 10.0)  # leader lengths beyond the icon edge, map-width %
# Leader directions in degrees (0 = right, 90 = down), in order of preference.
ANGLES = (0, 180, -45, -135, 45, 135, -90, 90)
SAMPLES = 12                    # points checked along each leader line


def place(icons: list[dict], limit: int, *, char_w: float, text_h: float,
          width: float = 100.0, height: float = 50.0) -> list[dict]:
    """icons: {"x", "y", "hw", "hh", "n", "a"} (centre, half sizes, name, age h).

    Returns labels: {"i": icon index, "x", "y", "a": "start"|"end"|"middle", "ld": [x1, y1, x2, y2] | None},
    where (x, y) is the label anchor: left edge (start), right edge (end) or centre (middle),
    vertically centred.
    """
    boxes = [(c["x"] - c["hw"], c["y"] - c["hh"], c["x"] + c["hw"], c["y"] + c["hh"]) for c in icons]
    lines: list[tuple[float, float, float, float]] = []
    out = []
    order = sorted(range(len(icons)), key=lambda i: (icons[i]["a"], -icons[i]["hw"]))
    for i in order:
        if len(out) >= limit:
            break
        c = icons[i]
        tw, th = char_w * len(c["n"]), text_h
        own = boxes[i]
        others = [b for j, b in enumerate(boxes) if j != i]

        def fits(box) -> bool:
            if box[0] < 0 or box[1] < 0 or box[2] > width or box[3] > height:
                return False
            return not any(_overlaps(box, b) for b in boxes) and not any(_box_hits_line(box, ln) for ln in lines)

        placed = None
        x, y, hw, hh = c["x"], c["y"], c["hw"], c["hh"]
        for anchor, ax, box in (
            ("start", x + hw + GAP, (x + hw + GAP, y - th / 2, x + hw + GAP + tw, y + th / 2)),
            ("end", x - hw - GAP, (x - hw - GAP - tw, y - th / 2, x - hw - GAP, y + th / 2)),
            ("middle", x, (x - tw / 2, y - hh - GAP - th, x + tw / 2, y - hh - GAP)),
            ("middle", x, (x - tw / 2, y + hh + GAP, x + tw / 2, y + hh + GAP + th)),
        ):
            if fits(box):
                placed = {"i": i, "x": ax, "y": (box[1] + box[3]) / 2, "a": anchor, "ld": None}, box
                break

        if placed is None:
            for step in LEADER_STEPS:
                for deg in ANGLES:
                    dx, dy = math.cos(math.radians(deg)), math.sin(math.radians(deg))
                    # Leader starts at the icon edge and runs `step` further out.
                    r0 = _edge_distance(hw, hh, dx, dy)
                    ex, ey = x + dx * (r0 + step), y + dy * (r0 + step)
                    if dx > 0.3:
                        anchor, ax, box = "start", ex, (ex, ey - th / 2, ex + tw, ey + th / 2)
                    elif dx < -0.3:
                        anchor, ax, box = "end", ex, (ex - tw, ey - th / 2, ex, ey + th / 2)
                    elif dy < 0:
                        anchor, ax, box = "middle", ex, (ex - tw / 2, ey - th, ex + tw / 2, ey)
                    else:
                        anchor, ax, box = "middle", ex, (ex - tw / 2, ey, ex + tw / 2, ey + th)
                    line = (x + dx * r0, y + dy * r0, ex, ey)
                    if not fits(box) or _line_hits_boxes(line, others + [b for b in boxes[len(icons):]]):
                        continue
                    placed = {"i": i, "x": ax, "y": (box[1] + box[3]) / 2, "a": anchor,
                              "ld": [round(v, 2) for v in line]}, box
                    lines.append(line)
                    break
                if placed:
                    break

        if placed:
            label, box = placed
            boxes.append(box)
            label["x"], label["y"] = round(label["x"], 2), round(label["y"], 2)
            out.append(label)
    return out


def _edge_distance(hw: float, hh: float, dx: float, dy: float) -> float:
    """Distance from a box centre to its edge along a unit direction."""
    tx = hw / abs(dx) if abs(dx) > 1e-9 else math.inf
    ty = hh / abs(dy) if abs(dy) > 1e-9 else math.inf
    return min(tx, ty)


def _overlaps(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _inside(px: float, py: float, b) -> bool:
    return b[0] < px < b[2] and b[1] < py < b[3]


def _line_hits_boxes(line, boxes) -> bool:
    x1, y1, x2, y2 = line
    for k in range(1, SAMPLES + 1):
        t = k / (SAMPLES + 1)
        px, py = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
        if any(_inside(px, py, b) for b in boxes):
            return True
    return False


def _box_hits_line(box, line) -> bool:
    return _line_hits_boxes(line, [box])
