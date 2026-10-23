"""Land-mask PNG per view, in the style of the TRMNL earthquake recipe.

The PNG is opaque white over the ocean and transparent over land. The recipe
places it on a box with a TRMNL grey class, so land shows as framework grey
and renders correctly on every panel bit depth.
"""

from __future__ import annotations

import json
import math
import struct
import zlib
from functools import lru_cache
from importlib import resources

from hotspots.render.views import Frame, View, wrap180

MASK_WIDTH = 1600
MASK_HEIGHT = 800


@lru_cache(maxsize=None)
def _land(detail: str) -> list[list[list[float]]]:
    with resources.files("hotspots.render.data").joinpath(f"land_{detail}.json").open() as f:
        return json.load(f)["polygons"]


def _unwrap(ring: list[float], center: float) -> list[tuple[float, float]]:
    """Ring as (lon relative to centre, lat), unwrapped so it never jumps 360°."""
    if max(abs(v) for v in ring[1::2]) >= 89.9:
        # Pole-encircling ring (Antarctica): start at the seam so the pole closure stays off-map.
        k = max(range(0, len(ring), 2), key=lambda i: abs(wrap180(ring[i] - center)))
        ring = ring[k:] + ring[:k]
    out, prev = [], None
    for i in range(0, len(ring), 2):
        r = wrap180(ring[i] - center)
        if prev is not None:
            while r - prev > 180:
                r -= 360
            while prev - r > 180:
                r += 360
        out.append((r, ring[i + 1]))
        prev = r
    if abs(out[-1][0] - out[0][0]) > 180:
        # Finish the lap with the real closing segment (start shifted by 360°), then close along the pole.
        pole = -90.0 if sum(p[1] for p in out) < 0 else 90.0
        lap = round((out[-1][0] - out[0][0]) / 360) * 360
        out += [(out[0][0] + lap, out[0][1]), (out[0][0] + lap, pole), (out[0][0], pole)]
    return out


def rasterize(view: View, width: int = MASK_WIDTH, height: int = MASK_HEIGHT) -> list[bytearray]:
    """Return rows of 0 (ocean) / 1 (land)."""
    frame = Frame(view)
    rows = [bytearray(width) for _ in range(height)]
    for polygon in _land(view.detail):
        rings = [_unwrap(r, frame.center_lon) for r in polygon]
        lo = min(p[0] for p in rings[0])
        hi = max(p[0] for p in rings[0])
        shifts = [0.0] + ([360.0] if lo < -180 else []) + ([-360.0] if hi > 180 else [])
        if view.is_world is False:
            shifts += [360.0, -360.0]  # regional frames may sit across the seam
        for sh in set(shifts):
            px_rings = []
            for ring in rings:
                pts = []
                for r, lat in ring:
                    u, v = frame.uv_rel(r + sh, lat)
                    pts.append((u * width, v * height))
                px_rings.append(pts)
            xs = [p[0] for p in px_rings[0]]
            ys = [p[1] for p in px_rings[0]]
            if max(xs) < 0 or min(xs) > width or max(ys) < 0 or min(ys) > height:
                continue
            _fill_polygon(rows, px_rings, width, height)
    return rows


def _fill_polygon(rows: list[bytearray], rings: list[list[tuple[float, float]]], width: int, height: int) -> None:
    """Even-odd scanline fill of one polygon (exterior + holes) into rows (OR)."""
    crossings: dict[int, list[float]] = {}
    for pts in rings:
        n = len(pts)
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            if y1 == y2:
                continue
            if y1 > y2:
                x1, y1, x2, y2 = x2, y2, x1, y1
            r0 = max(0, math.ceil(y1 - 0.5))
            r1 = min(height - 1, math.ceil(y2 - 0.5) - 1)
            if r0 > r1:
                continue
            slope = (x2 - x1) / (y2 - y1)
            for r in range(r0, r1 + 1):
                crossings.setdefault(r, []).append(x1 + (r + 0.5 - y1) * slope)
    for r, xs in crossings.items():
        xs.sort()
        row = rows[r]
        for a, b in zip(xs[0::2], xs[1::2]):
            c0 = max(0, math.ceil(a - 0.5))
            c1 = min(width - 1, math.floor(b - 0.5))
            if c0 <= c1:
                row[c0:c1 + 1] = b"\x01" * (c1 - c0 + 1)


def encode_png(rows: list[bytearray]) -> bytes:
    """8-bit palette PNG: index 0 = opaque white (ocean), 1 = transparent (land)."""
    height, width = len(rows), len(rows[0])

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 3, 0, 0, 0))
            + chunk(b"PLTE", bytes([255, 255, 255, 255, 255, 255]))
            + chunk(b"tRNS", bytes([255, 0]))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def render_mask(view: View) -> bytes:
    return encode_png(rasterize(view))
