"""Shared data types passed between sources, processing and rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Volcano:
    """A catalogue entry (Smithsonian GVP Holocene volcanoes)."""

    volcano_id: str
    name: str
    lat: float
    lon: float
    country: str = ""
    last_eruption_year: int | None = None
    landform: str = ""


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
    daynight: str | None = None


@dataclass(frozen=True)
class Overpass:
    """All of one volcano's detections from a single satellite pass.

    Adjacent pixels in one pass are distinct ground area, so their FRP is
    summed. Separate passes re-observe the same hotspot and are never summed
    for scoring.
    """

    acquired_at: datetime
    pixel_count: int
    total_frp_mw: float


@dataclass
class VolcanoActivity:
    """Aggregated thermal evidence for one volcano."""

    volcano: Volcano
    detections: list[Detection] = field(default_factory=list)
    overpasses: list[Overpass] = field(default_factory=list)
    accumulated_frp_mw: float = 0.0
    peak_frp_mw: float = 0.0
    peak_overpass_frp_mw: float = 0.0
    latest_observation: datetime | None = None
    ambiguous_with: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    score: float = 0.0
    qualifies: bool = False


@dataclass(frozen=True)
class Marker:
    """Render-ready marker; independent of the data sources."""

    volcano_id: str
    name: str
    lat: float
    lon: float
    size: float          # 0..1, relative activity (mapped to icon width by the renderer)
    fade_step: int       # 0 = solid (≤ full_hours); 1..n = fade levels toward expiry
    age_hours: float
    erupting: bool = False  # GVP lists a continuing eruption (official), not inferred from heat
    country: str = ""
    seen: int = 0           # latest observation, Unix seconds (the recipe shows its age at render time)


@dataclass
class SourceResult:
    """Outcome of one upstream fetch. Distinguishes empty from failed."""

    ok: bool
    fetched_at: datetime
    items: list = field(default_factory=list)
    error: str | None = None
    meta: dict = field(default_factory=dict)
