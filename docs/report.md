# Prototype validation report

**Data:** FIRMS VIIRS S-NPP NRT global 7-day file, downloaded 2026-10-23 (latest acquisition 10:06 UTC), evaluated at `--as-of 2026-10-23T12:00Z`.
**Catalogue:** Smithsonian GVP Holocene volcanoes, 1,214 entries.

## Decisions (agreed 2026-10-23)

| Topic | Decision |
|---|---|
| Backend | GitHub Actions, daily cron. Publishes static files to GitHub Pages. |
| Distribution | Public recipe. All installs poll one shared `latest.json`; nobody hits NASA but us. |
| Devices | All TRMNL panels. Map drawn in Liquid with framework classes (approach of the TRMNL earthquake recipe), so the framework handles 1-bit dithering through 16 greys and OG through X sizes. |
| Size vs age | Size = activity only; age shown only through shade. |
| Fade | Black ≤ 24 h, then `bg--gray-20/30/40/50` in 12 h steps, hidden after 72 h. Each dot has a white halo so it reads on both the white land and the dark water. |
| Labels | Boolean setting, off by default; labels up to 5 of the most recently observed volcanoes, placed to avoid overlaps. |
| Map | One "Map" setting. 4 *World – centred on …* views (Europe & Africa default, Americas, Asia & Australia, Pacific): 2:1 equirectangular, our own Natural Earth world mask re-centred, coloured with the framework map's native map-land / map-water slots. 8 *Close-up – …* views: TRMNL framework map (`TRMNLMaps`, Web Mercator, OSM tiles from TRMNL), the framework's `outline` preset unmodified, whole-number zoom fitted to the region box. |
| Markers | Dots for now (diameter by activity, shade by age, white halo); world views positioned in Liquid, close-ups projected with MapLibre in the browser. |

## Endpoints and credentials

| Source | Endpoint | Credential |
|---|---|---|
| FIRMS (default) | `https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_7d.csv` (~37 MB) | none |
| FIRMS (optional) | Area API `…/api/area/csv/{MAP_KEY}/VIIRS_SNPP_NRT/world/{days}` | `FIRMS_MAP_KEY` repo secret, used only if set |
| GVP catalogue | WFS `GVP-VOTW:Smithsonian_VOTW_Holocene_Volcanoes`, GeoJSON | none |
| World map | Generated from Natural Earth 50m land (public domain) by `scripts/build_world_map.py`, embedded | none |
| Close-up map | TRMNL framework map: `trmnl.com/js/maplibre-gl/5.24.0`, tiles from TRMNL (`tiles: "trmnl"`) | none |

**Finding:** FIRMS publishes keyless global files (24 h / 48 h / 7 d) for S-NPP, NOAA-20 and NOAA-21. That removes the need for an API key and covers the 72 h window in one request. The key path is kept as a fallback.

## Data freshness

- The file was regenerated within ~3 h of the latest acquisition. S-NPP passes each point roughly twice a day (≈01:30 and 13:30 local), so any one volcano is observed about every 12 h when skies are clear.
- `latest.json` records `generated_at` (run time) and `data_as_of` (newest FIRMS acquisition). The recipe shows the second and adds "stale" if the run is more than 36 h old.
- Failure policy: if FIRMS fails, the job fails and nothing is deployed, so Pages keeps serving the previous maps unchanged. Markers are never re-aged or removed by a failed fetch. If GVP fails, the run falls back to the previously published `catalogue.json`.

## Filtering and activity score

Pipeline per run (relative to run time `as_of`):

1. Keep detections from the last **72 h** with confidence **≥ nominal**.
2. Match each detection to the nearest volcano within **10 km**. If a second volcano is within 1.5× that distance, flag it as ambiguous (shown in diagnostics; the nearest volcano keeps the detection).
3. Group each volcano's detections into **overpasses**: same satellite, ≤ 10 min apart. Pixels within one pass are summed (distinct ground area). Separate passes are never summed, which avoids double counting where swaths overlap.
4. **Score input:** the strongest single-overpass FRP within the 24 h ending at that volcano's latest detection. Because the window is anchored to the latest detection, the size stays constant while the marker fades.
5. **Size:** `clamp(log10(FRP / 1 MW) / log10(1000), 0, 1)`, mapped to 10–34 px. The fixed reference (not the day's maximum) keeps sizes comparable from day to day. Nyamulagira's 1,392 MW clamps to the maximum, so it doesn't shrink everything else.
6. **Qualifying conditions** (all required):
   - the volcano erupted within the last **10 years** per GVP;
   - peak overpass FRP **≥ 1 MW**;
   - at least one detection within **10 km**, or within **5 km** if seen on only one overpass ("isolated" rule).
7. At most **30 markers per view**, ranked by score.

The score is a visualization metric. It is not eruption magnitude, danger or probability.

## Validation results

84 volcanoes had at least one detection within 10 km; **30 qualify**.

### Excluded as likely non-volcanic: 54

The largest were landscape fires near long-dormant volcanoes (Java dry season; East African grass-fire season):

| Volcano | Peak pass MW | Last eruption | Why excluded |
|---|---:|---|---|
| Lawu (Java) | 142 | unknown | no recent eruption |
| Longonot (Kenya) | 128 | 1863 | no recent eruption |
| Iyang-Argapura (Java) | 85 | unknown | no recent eruption |
| Rungwe / Kyejo (Tanzania) | 77 / 66 | 1250 / 1800 | no recent eruption, ambiguous pair |
| Sumbing, Arjuno-Welirang, Ijen, Baluran (Java) | 28–75 | ≤ 1999 | no recent eruption |
| Dempo, Lewotobi, Sangeang Api, Etna | 1.5–14 | 2022–2026 | isolated: single pass 5–9 km from summit |

### Qualifying volcanoes: 30

Nyamulagira, Kilauea, Raung, Langila, Ibu, Sangay, Krasheninnikov, Reventador, Tengger Caldera, Lewotolok, Bagana, Krakatau, Ambrym, Karangetang, Sirung, Semeru, Stromboli, Iliwerung, Dukono, Nyiragongo, Merapi, Manam, Ulawun, Taal, Yasur, Heard, Telica, Purace, Fuego, Tofua.

These include the known long-running eruptions (Kilauea, Sangay, Ibu, Lewotolok, Semeru, Dukono, Stromboli, Reventador, Bagana, Manam) and the strongest signal of the week (Nyamulagira lava, 1.4 GW).

### Threshold sweep (`backend/scripts/calibrate.py`)

| Variation | Markers | Change vs defaults |
|---|---:|---|
| defaults | 30 | — |
| radius 5 km | 28 | loses Langila, Sirung (catalogue points ~5 km from active vents) |
| radius 20 km | 32 | gains Rinjani, Suoh |
| confidence high | 6 | loses 24 real eruptions (VIIRS "high" mostly marks saturated pixels) |
| eruption ≤ 25 y | 35 | gains Rabaul, Witori, Egon… (likely fires) |
| no eruption prior | 59 | gains 29 fire-driven candidates |
| peak ≥ 5 MW | 21 | loses Fuego, Yasur, Taal, Ulawun… (weak but real) |
| ≥ 2 overpasses | 22 | loses Nyiragongo, Fuego, Yasur, Taal… |
| no isolation rule | 34 | gains Dempo, Etna, Lewotobi, Sangeang Api |

## Known limitations

- **Eruption-history prior.** A volcano reawakening after more than 10 years quiet is hidden until GVP updates its last-eruption year (the catalogue refreshes monthly). This is the main trade-off for suppressing fires.
- **Fires on active volcanoes** (for example Tengger's caldera grassland) can still pass.
- **Weak or cloud-covered activity is missed.** Absence of a marker does not mean inactivity.
- **Dense clusters** (Java, Lesser Sunda Islands) overlap on world views. Regional views separate them.
- **One satellite only.** S-NPP is aging. NOAA-20/21 are configured as alternatives but not merged.
- **Not yet checked with trmnlp or on a device.** Templates were rendered with a python-liquid stand-in and TRMNL's real framework CSS/JS in headless Chromium for OG (1-bit), OG Plus (2-bit) and X (4-bit), in all four layouts.
- **Half-vertical layout** shows the 2:1 world map with much empty space; a portrait-specific view would use it better.
- **Close-up zoom is whole-number only** (the framework keeps dither on the pixel grid), so a region shows either somewhat more or up to ~20% less than its box, depending on the screen size.
- **Close-ups need WebGL** in TRMNL's renderer; without it the framework shows the "Map unavailable" fallback.
- **Two Hotspots close-ups in one mashup** would share an element id; not supported yet.

## Recommended adjustments

1. Re-run the calibration sweep weekly for a month, especially during other fire seasons (Australia, the Americas), before locking thresholds.
2. Check marker legibility and the grey steps on a physical OG panel; adjust `shades` / icon sizes if needed.
3. Consider an "unconfirmed" tier for strong, compact, repeated signals at dormant volcanoes (for example ≥ 3 passes within 2 km), drawn distinctly, so reawakenings aren't completely hidden.
4. Add NOAA-20 as an automatic fallback when S-NPP data is missing.
5. Add portrait-aspect views for the half-vertical layout and TRMNL X portrait orientation.
