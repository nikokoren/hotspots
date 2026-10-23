"""Processing pipeline (spec §5).

fetch FIRMS → validate → load catalogue → associate → filter → group by
volcano/overpass → score → qualify → size/fade → render → write site.

Outputs (written to `out_dir`, published to GitHub Pages):
    latest.json             payload polled by the TRMNL recipe: views and markers
    diagnostics.json        every candidate volcano with metrics and flags (calibration)
    catalogue.json          cached GVP catalogue, reused by the next run

The recipe draws the map itself (see trmnl/src/shared.liquid).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hotspots.cache import load_catalogue
from hotspots.models import Detection, Marker, Volcano, VolcanoActivity
from hotspots.processing.association import associate
from hotspots.processing.scoring import aggregate
from hotspots.processing.visual import build_markers, qualify
from hotspots.render.layout import marker_list, view_markers
from hotspots.render.views import DEFAULT_VIEW, VIEWS, world_shift_pct
from hotspots.sources import firms

ATTRIBUTION = ("Thermal anomalies: NASA FIRMS VIIRS (LANCE). Volcanoes: Smithsonian Global Volcanism Program. "
               "Coastlines: Natural Earth.")


def process(detections: list[Detection], volcanoes: list[Volcano], cfg: dict,
            as_of: datetime) -> tuple[list[Marker], list[VolcanoActivity], dict]:
    """Pure processing step: no I/O. Returns (markers, all candidate activities, stats)."""
    s, a = cfg["scoring"], cfg["association"]
    window_start = as_of - timedelta(hours=s["observation_window_hours"])
    recent = [d for d in detections
              if window_start <= d.acquired_at <= as_of and firms.meets_confidence(d, cfg["firms"]["min_confidence"])]
    matched, ambiguous, unmatched = associate(recent, volcanoes, a["radius_km"], a["ambiguity_ratio"])
    by_id = {v.volcano_id: v for v in volcanoes}
    activities = []
    for vid, dets in matched.items():
        act = aggregate(by_id[vid], dets, s["score_window_hours"])
        act.ambiguous_with = sorted(by_id[x].name for x in ambiguous.get(vid, ()))
        qualify(act, cfg, as_of)
        activities.append(act)
    markers = build_markers(activities, cfg, as_of)
    stats = {
        "detections_total": len(detections),
        "detections_in_window": len(recent),
        "detections_matched": sum(len(d) for d in matched.values()),
        "detections_unmatched": unmatched,
        "candidate_volcanoes": len(activities),
        "qualifying_volcanoes": sum(a.qualifies for a in activities),
        "markers": len(markers),
    }
    return markers, activities, stats


def run(cfg: dict, out_dir: Path, cache_dir: Path, *, map_key: str | None = None,
        previous_url: str | None = None, as_of: datetime | None = None,
        firms_csv: Path | None = None, log=print) -> dict:
    as_of = as_of or datetime.now(timezone.utc)
    f = cfg["firms"]

    if firms_csv:
        detections, skipped = firms.parse_csv(firms_csv.read_text())
        firms_meta = {"url": str(firms_csv), "rows_skipped": skipped, "product": f["product"]}
    else:
        result = firms.fetch(f["product"], span=f["span"], map_key=map_key, days=f["api_days"],
                             timeout_s=f["request_timeout_s"], retries=f["max_retries"])
        if not result.ok:
            # Fail loudly: nothing is deployed, so the last good maps stay up unchanged.
            raise RuntimeError(f"FIRMS fetch failed: {result.error}")
        detections, firms_meta = result.items, result.meta
    log(f"FIRMS: {len(detections)} detections ({firms_meta.get('rows_skipped', 0)} malformed rows skipped)")

    volcanoes, cat_meta = load_catalogue(cache_dir / "catalogue.json", previous_url,
                                         cfg["catalogue"]["refresh_days"], log=log)
    log(f"Catalogue: {len(volcanoes)} volcanoes ({cat_meta['source']})")

    markers, activities, stats = process(detections, volcanoes, cfg, as_of)
    log("Stats: " + json.dumps(stats))

    data_as_of = max((d.acquired_at for d in detections), default=None)
    write_site(out_dir, cfg, markers, activities, stats, as_of, data_as_of, firms_meta, cat_meta)
    # Re-publish the catalogue so the next run (or a GVP outage) can reuse it.
    cached = cache_dir / "catalogue.json"
    if cached.exists():
        (out_dir / "catalogue.json").write_bytes(cached.read_bytes())
    return stats


def write_site(out_dir: Path, cfg: dict, markers: list[Marker], activities: list[VolcanoActivity],
               stats: dict, as_of: datetime, data_as_of: datetime | None, firms_meta: dict, cat_meta: dict) -> None:
    vis = cfg["visual"]
    out_dir.mkdir(parents=True, exist_ok=True)
    sizing = {"min_pct": vis["min_icon_pct"], "max_pct": vis["max_icon_pct"], "shades": vis["shades"]}
    views = {}
    for view in VIEWS:
        if view.is_world:
            world_markers, world_labels = view_markers(markers, view, max_markers=vis["max_markers"],
                                                       max_labels=vis["max_labels"], **sizing)
            views[view.key] = {"label": view.label, "world": True, "shift": world_shift_pct(view),
                               "markers": world_markers, "labels": world_labels}
        else:
            views[view.key] = {"label": view.label, "world": False,
                               "bbox": [view.lon_min, view.lat_min, view.lon_max, view.lat_max]}

    latest = {
        "generated_at": as_of.isoformat(timespec="seconds"),
        "data_as_of": data_as_of.isoformat(timespec="seconds") if data_as_of else None,
        "version": as_of.strftime("%Y%m%d%H%M"),
        "site_url": cfg["output"]["site_url"],
        "product": firms_meta.get("product"),
        "marker_count": len(markers),
        "default_view": DEFAULT_VIEW,
        "max_labels": vis["max_labels"],
        "views": views,
        "markers": marker_list(markers, max_markers=vis["max_markers"], **sizing),
        "attribution": ATTRIBUTION,
    }
    (out_dir / "latest.json").write_text(json.dumps(latest, separators=(",", ":")))

    diag = {
        "generated_at": latest["generated_at"],
        "data_as_of": latest["data_as_of"],
        "stats": stats,
        "firms": firms_meta,
        "catalogue": cat_meta,
        "config": cfg,
        "candidates": sorted((_diag_row(a, as_of) for a in activities), key=lambda r: -r["peak_overpass_frp_mw"]),
    }
    (out_dir / "diagnostics.json").write_text(json.dumps(diag, indent=1, default=str))


def _diag_row(a: VolcanoActivity, as_of: datetime) -> dict:
    v = a.volcano
    return {
        "volcano_id": v.volcano_id, "name": v.name, "country": v.country, "lat": v.lat, "lon": v.lon,
        "last_eruption_year": v.last_eruption_year,
        "detections": len(a.detections), "overpasses": len(a.overpasses),
        "peak_overpass_frp_mw": round(a.peak_overpass_frp_mw, 1),
        "peak_pixel_frp_mw": round(a.peak_frp_mw, 1),
        "accumulated_frp_24h_mw": round(a.accumulated_frp_mw, 1),
        "latest_observation": a.latest_observation.isoformat() if a.latest_observation else None,
        "age_hours": round((as_of - a.latest_observation).total_seconds() / 3600, 1) if a.latest_observation else None,
        "qualifies": a.qualifies, "flags": a.flags, "ambiguous_with": a.ambiguous_with,
        "score": round(a.score, 3),
    }
