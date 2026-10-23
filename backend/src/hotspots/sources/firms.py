"""NASA FIRMS VIIRS thermal anomalies (primary source).

Two equivalent access paths to the same NRT product:

* Public global files (no key):
  https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_{24h,48h,7d}.csv
* Area API (needs MAP_KEY):
  https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/VIIRS_SNPP_NRT/world/{days}

The public 7-day file is the default: it covers the 72 h window in one request
and needs no credential. If a MAP_KEY is configured the API is used instead; the
key never leaves this process (see http.redact).
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from hotspots import http
from hotspots.models import Detection, SourceResult

PUBLIC_FILES = {
    "VIIRS_SNPP_NRT": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_{span}.csv",
    "VIIRS_NOAA20_NRT": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_{span}.csv",
    "VIIRS_NOAA21_NRT": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-21-viirs-c2/csv/J2_VIIRS_C2_Global_{span}.csv",
}
API_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{product}/world/{days}"

REQUIRED_COLUMNS = {"latitude", "longitude", "acq_date", "acq_time", "frp", "confidence"}
CONFIDENCE_RANK = {"l": 0, "low": 0, "n": 1, "nominal": 1, "h": 2, "high": 2}


def fetch(product: str, span: str = "7d", map_key: str | None = None, days: int = 5,
          timeout_s: float = 120, retries: int = 3) -> SourceResult:
    now = datetime.now(timezone.utc)
    url = API_URL.format(key=map_key, product=product, days=days) if map_key \
        else PUBLIC_FILES[product].format(span=span)
    try:
        text = http.get(url, timeout_s=timeout_s, retries=retries).decode("utf-8", "replace")
        detections, skipped = parse_csv(text)
    except Exception as exc:  # noqa: BLE001
        return SourceResult(ok=False, fetched_at=now, error=str(exc), meta={"url": http.redact(url)})
    return SourceResult(ok=True, fetched_at=now, items=detections,
                        meta={"url": http.redact(url), "rows_skipped": skipped, "product": product})


def parse_csv(text: str) -> tuple[list[Detection], int]:
    """Parse FIRMS CSV. Raises ValueError on an unexpected schema; skips bad rows."""
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return [], 0  # genuinely empty response
    missing = REQUIRED_COLUMNS - set(reader.fieldnames)
    if missing:
        raise ValueError(f"FIRMS CSV missing columns: {sorted(missing)}; first line: {text[:200]!r}")
    out: list[Detection] = []
    skipped = 0
    for row in reader:
        try:
            lat, lon = float(row["latitude"]), float(row["longitude"])
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError("coords out of range")
            t = row["acq_time"].zfill(4)
            acquired = datetime.strptime(f"{row['acq_date']} {t}", "%Y-%m-%d %H%M").replace(tzinfo=timezone.utc)
            frp = _float_or_none(row.get("frp"))
            if frp is not None and frp < 0:
                frp = None
            out.append(Detection(
                lat=lat, lon=lon, acquired_at=acquired, frp_mw=frp,
                confidence=(row.get("confidence") or "").strip().lower() or None,
                brightness_k=_float_or_none(row.get("bright_ti4") or row.get("brightness")),
                satellite=row.get("satellite") or None,
                daynight=row.get("daynight") or None,
            ))
        except (ValueError, KeyError):
            skipped += 1
    return out, skipped


def meets_confidence(det: Detection, minimum: str) -> bool:
    rank = CONFIDENCE_RANK.get(det.confidence or "", -1)
    return rank >= CONFIDENCE_RANK[minimum]


def _float_or_none(v: str | None) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None
