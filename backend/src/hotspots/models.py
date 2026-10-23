"""Shared data types passed between sources, processing and rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Volcano:
    """A catalogue entry (Smithsonian GVP)."""

    volcano_id: str
    name: str
    lat: float
    lon: float


@dataclass(frozen=True)
class Detection:
    """A single FIRMS thermal anomaly pixel."""

    lat: float
    lon: float
    acquired_at: datetime
    frp_mw: float | None
    confidence: str | None
    brightness_k: float | None
    satellite: str | None = None


@dataclass
class VolcanoActivity:
    """Aggregated thermal evidence for one volcano."""

    volcano: Volcano
    detections: list[Detection] = field(default_factory=list)
    accumulated_frp_mw: float = 0.0
    peak_frp_mw: float = 0.0
    latest_observation: datetime | None = None
    ambiguous: bool = False
    score: float = 0.0


@dataclass(frozen=True)
class Marker:
    """Render-ready marker; independent of the data sources."""

    name: str
    lat: float
    lon: float
    size_px: float
    opacity: float


@dataclass
class SourceResult:
    """Outcome of one upstream fetch. Distinguishes empty from failed."""

    ok: bool
    fetched_at: datetime
    items: list = field(default_factory=list)
    error: str | None = None
