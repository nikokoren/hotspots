"""Match FIRMS detections to catalogue volcanoes.

A detection is attributed to a volcano when it lies within `radius_km` of it.
If a second volcano is also within radius and not much farther away
(distance ratio < ambiguity_ratio), the match is recorded as ambiguous rather
than silently given to the nearest.
"""

from __future__ import annotations

import math
from collections import defaultdict

from hotspots.models import Detection, Volcano

EARTH_RADIUS_KM = 6371.0088
CELL_DEG = 1.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


class VolcanoIndex:
    """1°-grid spatial index for fast radius lookup over ~10^5–10^6 detections."""

    def __init__(self, volcanoes: list[Volcano]):
        self._cells: dict[tuple[int, int], list[Volcano]] = defaultdict(list)
        for v in volcanoes:
            self._cells[self._cell(v.lat, v.lon)].append(v)

    @staticmethod
    def _cell(lat: float, lon: float) -> tuple[int, int]:
        return math.floor(lat / CELL_DEG), math.floor(lon / CELL_DEG)

    def within(self, lat: float, lon: float, radius_km: float) -> list[tuple[float, Volcano]]:
        cy, cx = self._cell(lat, lon)
        # Longitude cells shrink toward the poles; widen the search accordingly.
        span_x = 1 + int(radius_km / (111.0 * max(math.cos(math.radians(lat)), 0.05)))
        span_y = 1 + int(radius_km / 111.0)
        hits = []
        for dy in range(-span_y, span_y + 1):
            for dx in range(-span_x, span_x + 1):
                x = (cx + dx + 180) % 360 - 180
                for v in self._cells.get((cy + dy, x), ()):
                    d = haversine_km(lat, lon, v.lat, v.lon)
                    if d <= radius_km:
                        hits.append((d, v))
        hits.sort(key=lambda h: h[0])
        return hits


def associate(detections: list[Detection], volcanoes: list[Volcano], radius_km: float,
              ambiguity_ratio: float) -> tuple[dict[str, list[Detection]], dict[str, set[str]], int]:
    """Return (detections by volcano id, ambiguous neighbour ids by volcano id, unmatched count).

    Ambiguous detections are still attributed to the nearest volcano but the
    pairing is recorded so it can be reported and, if configured, excluded.
    """
    index = VolcanoIndex(volcanoes)
    matched: dict[str, list[Detection]] = defaultdict(list)
    ambiguous: dict[str, set[str]] = defaultdict(set)
    unmatched = 0
    for det in detections:
        hits = index.within(det.lat, det.lon, radius_km)
        if not hits:
            unmatched += 1
            continue
        d0, v0 = hits[0]
        matched[v0.volcano_id].append(det)
        for d1, v1 in hits[1:]:
            if d1 <= max(d0, 1.0) * ambiguity_ratio:
                ambiguous[v0.volcano_id].add(v1.volcano_id)
    return dict(matched), dict(ambiguous), unmatched
