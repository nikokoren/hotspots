"""Catalogue caching and reuse of previously published output.

Static volcano data is cached separately from dynamic observations (spec §6).
The published site doubles as the durable cache: each run can re-read the
previous catalogue.json from GitHub Pages, so a GVP outage never blocks a run.

Last-good output: if FIRMS fails, the run exits non-zero and nothing is
deployed, so GitHub Pages keeps serving the previous maps unchanged. Markers
therefore never age or vanish because of an upstream failure.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hotspots import http
from hotspots.models import Volcano
from hotspots.sources import gvp


def load_catalogue(cache_path: Path, previous_url: str | None, refresh_days: int,
                   log=print) -> tuple[list[Volcano], dict]:
    """Return (volcanoes, meta). Order: fresh local cache → GVP → stale local/previous site."""
    cached = _read_local(cache_path)
    if cached is None and previous_url:
        try:
            cached = json.loads(http.get(f"{previous_url.rstrip('/')}/catalogue.json", timeout_s=30, retries=1))
        except Exception as exc:  # noqa: BLE001
            log(f"no previous catalogue at {previous_url}: {exc}")
    if cached and _age(cached) < timedelta(days=refresh_days):
        return gvp.from_json(cached["volcanoes"]), {**_meta(cached), "source": "cache"}

    result = gvp.fetch_catalogue()
    if result.ok:
        payload = {"fetched_at": result.fetched_at.isoformat(), "layer": gvp.LAYER,
                   "volcanoes": gvp.to_json(result.items)}
        save_catalogue(cache_path, payload)
        return result.items, {**_meta(payload), "source": "gvp"}
    if cached:
        log(f"GVP fetch failed ({result.error}); using stale catalogue")
        return gvp.from_json(cached["volcanoes"]), {**_meta(cached), "source": "stale-cache"}
    raise RuntimeError(f"no volcano catalogue available: {result.error}")


def save_catalogue(cache_path: Path, payload: dict) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(payload, separators=(",", ":")))


def _read_local(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _age(payload: dict) -> timedelta:
    try:
        return datetime.now(timezone.utc) - datetime.fromisoformat(payload["fetched_at"])
    except (KeyError, ValueError):
        return timedelta.max


def _meta(payload: dict) -> dict:
    return {"fetched_at": payload.get("fetched_at"), "count": len(payload.get("volcanoes", []))}
