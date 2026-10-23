"""Match FIRMS detections to catalogue volcanoes within a radius, flagging ambiguity."""

from __future__ import annotations


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    raise NotImplementedError


def associate(detections, volcanoes, radius_km: float, ambiguity_ratio: float):
    raise NotImplementedError
