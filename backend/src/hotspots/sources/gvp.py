"""Smithsonian Global Volcanism Program — Volcanoes of the World catalogue.

WFS:   https://webservices.volcano.si.edu/geoserver/GVP-VOTW/wfs
Layer: GVP-VOTW:Smithsonian_VOTW_Holocene_Volcanoes (~1,200 volcanoes active in the last ~12,000 years)
Docs:  https://volcano.si.edu/database/webservices.cfm

Citation: Global Volcanism Program, Volcanoes of the World (v. 5.x), Smithsonian Institution.

Weekly reports (https://volcano.si.edu/reports_weekly.cfm?vtab=feeds) are deferred:
they cover Wed–Tue and publish after the week closes, too coarse for recency.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from hotspots import http
from hotspots.models import SourceResult, Volcano

WFS_URL = "https://webservices.volcano.si.edu/geoserver/GVP-VOTW/wfs"
LAYER = "GVP-VOTW:Smithsonian_VOTW_Holocene_Volcanoes"


def catalogue_url() -> str:
    return (f"{WFS_URL}?service=WFS&version=2.0.0&request=GetFeature"
            f"&typeNames={LAYER}&outputFormat=application/json")


def fetch_catalogue(timeout_s: float = 120, retries: int = 3) -> SourceResult:
    now = datetime.now(timezone.utc)
    try:
        data = json.loads(http.get(catalogue_url(), timeout_s=timeout_s, retries=retries))
        volcanoes = parse_geojson(data)
        if not volcanoes:
            raise ValueError("catalogue parsed to zero volcanoes")
    except Exception as exc:  # noqa: BLE001
        return SourceResult(ok=False, fetched_at=now, error=str(exc))
    return SourceResult(ok=True, fetched_at=now, items=volcanoes, meta={"layer": LAYER})


def parse_geojson(data: dict) -> list[Volcano]:
    out = []
    for feat in data.get("features", []):
        p = feat.get("properties") or {}
        coords = (feat.get("geometry") or {}).get("coordinates") or [p.get("Longitude"), p.get("Latitude")]
        try:
            lon, lat = float(coords[0]), float(coords[1])
            vid = str(int(p["Volcano_Number"]))
        except (TypeError, ValueError, KeyError, IndexError):
            continue
        year = p.get("Last_Eruption_Year")
        out.append(Volcano(
            volcano_id=vid,
            name=str(p.get("Volcano_Name") or vid).strip(),
            lat=lat, lon=lon,
            country=str(p.get("Country") or ""),
            last_eruption_year=int(year) if isinstance(year, (int, float)) else None,
            landform=str(p.get("Volcanic_Landform") or p.get("Primary_Volcano_Type") or ""),
        ))
    return out


def to_json(volcanoes: list[Volcano]) -> list[dict]:
    return [v.__dict__ for v in volcanoes]


def from_json(rows: list[dict]) -> list[Volcano]:
    return [Volcano(**r) for r in rows]
