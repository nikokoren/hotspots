# hotspots

**Working title:** Volcano Watch — a TRMNL recipe showing a minimalist world map of
recent volcanic thermal activity. One volcano-shaped marker per volcano; marker
size reflects relative observed thermal activity (NASA FIRMS VIIRS FRP) and
opacity fades as the latest qualifying observation ages.

> Status: **scaffolding only.** Modules are stubs; nothing fetches, scores or
> renders yet. See [`docs/requirements.md`](docs/requirements.md) for the full
> specification.

## Layout

```
.
├── backend/                  Python data pipeline (server-side; holds the FIRMS key)
│   ├── src/hotspots/
│   │   ├── config.py         Settings loaded from config/defaults.toml + env
│   │   ├── models.py         Shared data types (Volcano, Detection, VolcanoActivity, Marker)
│   │   ├── cache.py          Last-good-result and catalogue caching
│   │   ├── pipeline.py       Orchestrates the processing steps (spec §5)
│   │   ├── cli.py            `hotspots` command-line entry point
│   │   ├── sources/          Upstream integrations
│   │   │   ├── firms.py      NASA FIRMS VIIRS_SNPP_NRT (primary)
│   │   │   ├── gvp.py        Smithsonian GVP volcano catalogue + weekly reports
│   │   │   └── usgs.py       USGS HANS notices (optional, later)
│   │   ├── processing/
│   │   │   ├── association.py  Detection → volcano matching, ambiguity handling
│   │   │   ├── scoring.py      Activity score + normalization
│   │   │   └── visual.py       Marker size / opacity / eligibility / ranking
│   │   └── render/
│   │       └── map.py        World map + marker rendering (SVG)
│   ├── assets/               Volcano silhouette SVG, basemap data
│   └── tests/
├── config/defaults.toml      Tunable thresholds (window, radius, sizes, fading…)
├── trmnl/                    TRMNL recipe (Liquid markup, trmnlp-compatible)
│   ├── .trmnlp.yml
│   └── src/                  full / half / quadrant layouts + settings.yml
└── docs/
    ├── requirements.md       Product + technical specification
    └── report.md             Prototype validation report (to be written)
```

Data acquisition, scoring and rendering are kept in separate modules so new
sources (USGS notices, seismic) can be added without touching the map.

## Development

```sh
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
cp ../.env.example ../.env   # then add your FIRMS MAP_KEY
pytest
```

TRMNL markup can be previewed locally with
[`trmnlp`](https://github.com/usetrmnl/trmnlp) from the `trmnl/` directory.

## Credentials

The NASA FIRMS MAP_KEY (register at
https://firms.modaps.eosdis.nasa.gov/api/map_key) is read from the
`FIRMS_MAP_KEY` environment variable. Never commit it, and never put it in the
Liquid markup or generated output.

## Data sources & attribution

- NASA FIRMS — VIIRS S-NPP NRT active fire / thermal anomaly data.
- Smithsonian Institution Global Volcanism Program — Volcanoes of the World catalogue, weekly reports.
- USGS Volcano Hazards Program — HANS notices (optional, future).

Thermal anomalies are not a measure of eruption magnitude, danger, or
eruption probability. A fading marker means observations have aged, not that
activity has stopped.
