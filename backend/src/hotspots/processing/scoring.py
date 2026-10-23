"""Relative activity score per volcano (spec §3).

Score input: the strongest single-overpass FRP within `score_window_hours`
ending at the volcano's latest detection.

* Pixels from the same overpass are distinct ground area → summed.
* Separate overpasses re-observe the same hotspot → never summed (avoids
  double counting where swaths overlap, which is frequent at high latitudes).
* The window ends at the latest detection, not at run time, so a marker keeps
  its size as it ages; only fading shows age.

This is a visualization metric, not a measure of eruption magnitude or danger.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta

from hotspots.models import Detection, Overpass, Volcano, VolcanoActivity

OVERPASS_GAP = timedelta(minutes=10)


def group_overpasses(detections: list[Detection]) -> list[Overpass]:
    by_sat: dict[str | None, list[Detection]] = defaultdict(list)
    for d in detections:
        by_sat[d.satellite].append(d)
    passes: list[Overpass] = []
    for dets in by_sat.values():
        dets.sort(key=lambda d: d.acquired_at)
        group: list[Detection] = []
        for d in dets:
            if group and d.acquired_at - group[-1].acquired_at > OVERPASS_GAP:
                passes.append(_overpass(group))
                group = []
            group.append(d)
        if group:
            passes.append(_overpass(group))
    passes.sort(key=lambda p: p.acquired_at)
    return passes


def _overpass(group: list[Detection]) -> Overpass:
    return Overpass(acquired_at=max(d.acquired_at for d in group), pixel_count=len(group),
                    total_frp_mw=sum(d.frp_mw or 0.0 for d in group))


def aggregate(volcano: Volcano, detections: list[Detection], score_window_hours: float) -> VolcanoActivity:
    act = VolcanoActivity(volcano=volcano, detections=detections)
    if not detections:
        return act
    act.overpasses = group_overpasses(detections)
    act.latest_observation = max(d.acquired_at for d in detections)
    start = act.latest_observation - timedelta(hours=score_window_hours)
    window = [d for d in detections if d.acquired_at >= start]
    act.accumulated_frp_mw = sum(d.frp_mw or 0.0 for d in window)
    act.peak_frp_mw = max((d.frp_mw or 0.0 for d in window), default=0.0)
    act.peak_overpass_frp_mw = max((p.total_frp_mw for p in act.overpasses if p.acquired_at >= start), default=0.0)
    return act


def normalized_size(frp_mw: float, floor_mw: float, cap_mw: float) -> float:
    """Log-scaled 0..1. Missing/zero/negative FRP → 0; extremes clamp to 1."""
    if not frp_mw or frp_mw <= floor_mw or math.isnan(frp_mw):
        return 0.0
    return min(1.0, math.log10(frp_mw / floor_mw) / math.log10(cap_mw / floor_mw))
