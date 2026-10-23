"""Activity → qualification, marker size, fade step and ranking (spec §3.4, §4)."""

from __future__ import annotations

from datetime import datetime

from hotspots.models import Marker, VolcanoActivity
from hotspots.processing.association import haversine_km
from hotspots.processing.scoring import normalized_size


def qualify(act: VolcanoActivity, cfg: dict, as_of: datetime) -> bool:
    """Apply the configured qualifying conditions; record reasons in act.flags."""
    q = cfg["qualify"]
    v = act.volcano
    ok = True
    years = q.get("max_years_since_eruption")
    if years is not None:
        if v.last_eruption_year is None or v.last_eruption_year < as_of.year - years:
            act.flags.append("no_recent_eruption")
            ok = False
    if act.peak_overpass_frp_mw < q["min_peak_overpass_frp_mw"]:
        act.flags.append("weak")
        ok = False
    if len(act.overpasses) < q["min_overpasses"]:
        act.flags.append("too_few_overpasses")
        ok = False
    nearest = min((haversine_km(d.lat, d.lon, v.lat, v.lon) for d in act.detections), default=float("inf"))
    if nearest > q["max_distance_km"]:
        act.flags.append("far_from_summit")
        ok = False
    elif len(act.overpasses) == 1 and nearest > q["isolated_max_distance_km"]:
        act.flags.append("isolated")
        ok = False
    if act.ambiguous_with:
        act.flags.append("ambiguous")  # informational; nearest volcano keeps the detections
    act.qualifies = ok
    return ok


def fade_step(age_hours: float, steps: list[float]) -> int | None:
    """0 = freshest. None = expired (older than the last step)."""
    for i, limit in enumerate(steps):
        if age_hours <= limit:
            return i
    return None


def build_markers(activities: list[VolcanoActivity], cfg: dict, as_of: datetime) -> list[Marker]:
    s, vis = cfg["scoring"], cfg["visual"]
    markers = []
    for act in activities:
        if not act.qualifies or act.latest_observation is None:
            continue
        age = max(0.0, (as_of - act.latest_observation).total_seconds() / 3600)
        step = fade_step(age, vis["fade_step_hours"])
        if step is None:
            continue
        act.score = normalized_size(act.peak_overpass_frp_mw, s["frp_floor_mw"], s["frp_cap_mw"])
        v = act.volcano
        markers.append(Marker(volcano_id=v.volcano_id, name=v.name, lat=v.lat, lon=v.lon,
                              size=round(act.score, 4), fade_step=step, age_hours=round(age, 1)))
    markers.sort(key=lambda m: (-m.size, m.age_hours, m.volcano_id))
    return markers
