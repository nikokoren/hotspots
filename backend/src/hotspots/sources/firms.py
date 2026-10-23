"""NASA FIRMS Area API — VIIRS_SNPP_NRT thermal anomalies (primary source).

Endpoint: https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{product}/{area}/{days}
Docs:     https://firms.modaps.eosdis.nasa.gov/api/area

The MAP_KEY must stay server-side and must never be logged or written to output.
"""

from __future__ import annotations

BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


def fetch(map_key: str, product: str, area: str, day_range: int, timeout_s: float):
    raise NotImplementedError


def parse_csv(text: str):
    raise NotImplementedError
