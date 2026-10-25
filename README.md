# hotspots

**Working title:** Volcano Watch. A public TRMNL recipe showing a minimalist map of
recent volcanic heat. Each qualifying volcano gets one marker:

- **size** shows relative observed thermal activity (NASA FIRMS VIIRS fire radiative power, log scale);
- **shade** shows the age of the latest observation: black ≤ 24 h, then four lighter TRMNL greys until 72 h, then hidden.

Markers come in two drawings (`trmnl/assets/icons/`, built into the template by `backend/scripts/build_icons.py`):

- **lava cone:** a heat signal only;
- **cone with ash plume:** the volcano also has an eruption the Smithsonian GVP lists as continuing, with eruptive
  activity recorded in the last 90 days. GVP keeps an eruption "continuing" until three months pass without
  activity, and its database can lag, so the recency check stops a stalled list from keeping plumes on screen.
  If the list can't be fetched, every marker falls back to the lava cone, so a volcano is never shown as erupting by mistake.
  Because GVP's eruption database hasn't been updated since March 2026 and its weekly report blocks automated
  access, there is also a hand-maintained list: [`eruptions.txt`](eruptions.txt). Once a week, paste the volcano
  names from the [Weekly Volcanic Activity Report](https://volcano.si.edu/reports_weekly.cfm) and commit; the map
  republishes. A volcano on the list also gets the plume. The list is ignored once its last commit is more than
  14 days old, and names that don't match the catalogue are listed in the Publish maps log.

The eruption drawing is also the recipe icon.

Both map kinds use the TRMNL framework map's **native colours** (its `map-land` and `map-water` slots:
white land and a dark water dither on 1-bit, greys on 4-bit, theme and dark-mode aware).

- **World views:** the whole globe re-centred on the chosen region. On TRMNL X, TRMNL's framework map fills
  every layout, as in the close-ups, at the smallest whole-number zoom that covers the space (so narrow
  layouts crop longitudes at the map edges). On other devices the recipe draws its own 2:1 map. With the
  *Volcano list* setting on, our map is always used and the height or width it leaves holds a list of the
  volcanoes, newest first (name, country, erupting or heat only, time since last seen). For our own map, the
  box is painted with
  `map-water`, and a strip painted with `map-land` is masked to the land by our own world mask, generated
  from Natural Earth by `backend/scripts/build_world_map.py` (2048×1024, 1-bit, embedded in
  `trmnl/src/shared.liquid`; source PNG in `trmnl/assets/world.png`). Markers are positioned in Liquid.
- **Close-ups** use the TRMNL framework map ([`TRMNLMaps`](https://trmnl.com/framework/docs/3.4/map):
  MapLibre over TRMNL's OpenStreetMap tiles), its `outline` preset (coast, water, borders and main
  roads) with the map's own place names turned off so only volcano names are drawn, with markers projected in
  the browser.

Both render natively on every TRMNL panel (1-bit to 16 greys, OG to X).

Marker size is not eruption size, danger or probability, and no marker does not mean a volcano is inactive.

Spec: [`docs/requirements.md`](docs/requirements.md). Data validation and threshold
results: [`docs/report.md`](docs/report.md).

## How it works

```
GitHub Actions (daily)                     GitHub Pages                 TRMNL (every install)
  FIRMS VIIRS 7-day CSV ─┐                   latest.json  ◄─── polling ─── recipe: world image or
  GVP catalogue + eruptions ┴► hotspots run ─► diagnostics.json             TRMNLMaps close-up + icons
                                             catalogue.json
```

Only the GitHub Actions job contacts NASA and the Smithsonian; every recipe install reads that shared
output. `latest.json` (~13 KB, under TRMNL's 100 KB limit) carries the ranked markers (lat/lon, icon
width as % of map width, grey class) plus, for world views, pre-computed positions. Labels are placed in the
browser on every map, measured at the size each layout gives it, with leader lines where crowded. If the FIRMS fetch fails,
nothing is deployed and the previous data stays up unchanged.

## Layout

```
backend/src/hotspots/
  sources/firms.py, gvp.py, usgs.py    upstream integrations (USGS still a stub)
  processing/association.py            detection → volcano matching, ambiguity flags
  processing/scoring.py                overpass grouping, activity score, size normalization
  processing/visual.py                 qualification rules, fade steps, ranking
  render/views.py                      map views: world frames + re-centring shift, close-up boxes
  render/layout.py                     marker sizes and shades; world-view positions
  pipeline.py, cache.py, cli.py
backend/scripts/                       world map builder, calibration sweep, Liquid preview
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
python -m http.server   # open it over http://, so the framework JS, fonts and map tiles load
```

## Deployment

1. Repo **Settings → Pages → Source: GitHub Actions**.
2. Run the **Publish maps** workflow once (Actions tab → Run workflow).
3. Optional: add a `FIRMS_MAP_KEY` repository secret to use the FIRMS Area API instead of the public files.

## Recipe settings

- **Map:** one list, two kinds of option.
  - *World – centred on …* Europe & Africa (default), the Americas, Asia & Australia, the Pacific:
    the whole globe, rotated so that region is in the middle.
  - *Close-up – …* Europe & Mediterranean, Africa & Middle East, North America & Alaska,
    Central America & Caribbean, South America, Japan, Kurils & Kamchatka, Indonesia & Philippines,
    Melanesia, Tonga & New Zealand: one region only.
- **Labels:** toggle, off by default; on names up to 5 of the most recently observed volcanoes.
- **Volcano list:** toggle, off by default; world views only. Lists the volcanoes, newest first, in the
  space beside or below the map (as many rows as fit; none on the original TRMNL in full screen).

## Data sources and attribution

- NASA FIRMS: VIIRS S-NPP NRT active fire / thermal anomaly data (LANCE). https://firms.modaps.eosdis.nasa.gov/
- Global Volcanism Program, Smithsonian Institution: Volcanoes of the World database. https://volcano.si.edu/
- Close-up maps: © OpenStreetMap contributors (ODbL), tiles and styling by the TRMNL framework.
- World map: generated from Natural Earth land polygons, public domain. https://www.naturalearthdata.com/
