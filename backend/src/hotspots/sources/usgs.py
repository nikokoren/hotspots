"""USGS Hazard Notification System (HANS) — optional corroborating notices.

API: https://volcanoes.usgs.gov/vsc/api/hansApi/
Not required for the first release; the pipeline must work without it.
"""

from __future__ import annotations

HANS_URL = "https://volcanoes.usgs.gov/vsc/api/hansApi"


def fetch_notices(timeout_s: float):
    raise NotImplementedError
