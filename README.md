# hotspots

**Working title:** Volcano Watch. A public TRMNL recipe showing a minimalist map of
recent volcanic heat. Each qualifying volcano gets one marker:

- **size** shows relative observed thermal activity (NASA FIRMS VIIRS fire radiative power, log scale);
- **shade** shows the age of the latest observation: black ≤ 24 h, then four lighter TRMNL greys until 72 h, then hidden.

The map follows the TRMNL earthquake recipe's approach: a land mask on a framework grey box with
markers positioned in Liquid, so it renders natively on every TRMNL panel (1-bit to 16 greys, OG to X).

Marker size is not eruption size, danger or probability, and no marker does not mean a volcano is inactive.

Spec: [`docs/requirements.md`](docs/requirements.md). Data validation and threshold
results: [`docs/report.md`](docs/report.md).

## How it works

```
GitHub Actions (daily)                     GitHub Pages                        TRMNL (every install)
  FIRMS VIIRS 7-day CSV ─┐                   latest.json  ◄──── polling ─────── recipe (Liquid draws
  GVP volcano catalogue ─┼─► hotspots run ─► masks/<view>.png ◄── <img> ──────┘  map + markers)
  Natural Earth (vendored)┘                  diagnostics.json, catalogue.json
```

Only the GitHub Actions job contacts NASA and the Smithsonian; every recipe install reads that shared
output. `latest.json` (~12 KB, under TRMNL's 100 KB limit) carries, per view, each marker's position
(% of the map box), icon width (% of map width), grey class and label side. If the FIRMS fetch fails,
nothing is deployed and the previous data stays up unchanged.

## Layout

```
backend/src/hotspots/
  sources/firms.py, gvp.py, usgs.py    upstream integrations (USGS still a stub)
  processing/association.py            detection → volcano matching, ambiguity flags
  processing/scoring.py                overpass grouping, activity score, size normalization
  processing/visual.py                 qualification rules, fade steps, ranking
  render/views.py                      map views, 2:1 equirectangular frames
  render/mask.py                       land-mask PNG per view (pure Python rasterizer)
  render/layout.py                     per-view marker positions, sizes, shades, label sides
  pipeline.py, cache.py, cli.py
backend/scripts/                       basemap builder, calibration sweep, Liquid preview
config/defaults.toml                   all thresholds
trmnl/src/                             recipe: settings.yml + Liquid layouts
.github/workflows/                     publish (daily → Pages), CI (tests)
```

## Development

```sh
pip install -e './backend[dev]'
pytest backend
hotspots run --out site                       # live data → site/
hotspots run --out site --firms-csv f.csv --as-of 2026-10-23T12:00Z   # replay saved data
python backend/scripts/calibrate.py f.csv --as-of 2026-10-23T12:00Z    # threshold sweep
```

Recipe markup can be previewed with [`trmnlp`](https://github.com/usetrmnl/trmnlp) from `trmnl/`
(needs Ruby 4 or Docker), or with the bundled stand-in that uses python-liquid and TRMNL's real CSS/JS:

```sh
python backend/scripts/preview.py site --layout full --region europe --labels --device og_png > preview.html
```

## Deployment

1. Repo **Settings → Pages → Source: GitHub Actions**.
2. Run the **Publish maps** workflow once (Actions tab → Run workflow).
3. Optional: add a `FIRMS_MAP_KEY` repository secret to use the FIRMS Area API instead of the public files.

## Recipe settings

- **Map view:** World (Pacific / Atlantic / Americas centred), Europe & Mediterranean, Africa & Middle East,
  North America & Alaska, Central America & Caribbean, South America, Japan–Kurils–Kamchatka,
  Indonesia & Philippines, Melanesia–Tonga–New Zealand.
- **Labels:** toggle, off by default; on names up to 5 of the most recently observed volcanoes.

## Data sources and attribution

- NASA FIRMS: VIIRS S-NPP NRT active fire / thermal anomaly data (LANCE). https://firms.modaps.eosdis.nasa.gov/
- Global Volcanism Program, Smithsonian Institution: Volcanoes of the World database. https://volcano.si.edu/
- Natural Earth: land polygons, public domain. https://www.naturalearthdata.com/
