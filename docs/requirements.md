# Volcano Watch: TRMNL Recipe Requirements

**Status:** Initial implementation specification  
**Working title:** Volcano Watch (recipe title: `hotspots`)  
**Platform:** TRMNL, with future support for larger displays such as TRMNL X  
**Primary objective:** Create a minimalist global volcano activity map using public data, with volcano icon size representing relative observed thermal activity and icon opacity fading as observations become older.

## 1. Product concept

Volcano Watch is a global monitoring display that visualizes recent volcanic activity using small volcano-shaped markers positioned at known volcano locations.

Unlike a static map of active volcanoes, the display should emphasize recent observations. Volcano markers should vary in size according to the relative strength of observed thermal activity and gradually fade as qualifying observations age.

The initial version should prioritize thermal activity detected by satellites, supplemented by a catalogue of known volcanoes and, where practical, recent official volcanic activity reports.

The recipe must not imply that satellite thermal measurements directly quantify eruption magnitude, volcanic danger, or the probability of an eruption.

### Design principles

- Minimalist, legible world map suitable for an e-paper display.
- One marker per volcano, not one marker per satellite detection.
- Marker size represents relative observed thermal activity.
- Marker opacity represents observation recency.
- Exclude weak, isolated, or unrelated thermal detections where possible.
- Avoid overwhelming the map with markers.
- Design the data model to accommodate additional activity sources in future versions.
- Cache data and handle temporary source failures gracefully.

## 2. Data sources

### 2.1 NASA FIRMS: primary thermal activity source

**Purpose:** Detect recent thermal anomalies that may be associated with volcanic activity.

Official resources:

- FIRMS API documentation: https://firms.modaps.eosdis.nasa.gov/api/area
- API key registration: https://firms.modaps.eosdis.nasa.gov/api/map_key
- FIRMS overview: https://firms.modaps.eosdis.nasa.gov/

Use the VIIRS Suomi-NPP near-real-time product (`VIIRS_SNPP_NRT`) initially. Other VIIRS products may be considered later.

The FIRMS Area API supports global requests over recent days and returns CSV data.

Relevant fields include:

- Latitude and longitude.
- Acquisition date and time.
- Confidence.
- Brightness temperature.
- Fire radiative power (FRP), measured in megawatts.
- Satellite and other observation metadata, where provided.

Example request structure:

`https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/VIIRS_SNPP_NRT/world/3`

Replace `{MAP_KEY}` with a valid NASA FIRMS API key.

**Requirements:**

1. Request global VIIRS observations covering the previous three days.
2. Parse the response server-side.
3. Apply spatial, temporal, and confidence filtering before rendering.
4. Associate qualifying detections with known volcanoes.
5. Aggregate multiple detections from the same volcano rather than rendering each detection separately.
6. Keep the NASA API key out of client-side code and public source files.
7. Cache responses and handle API errors, missing fields, and empty datasets.

FIRMS is a thermal-anomaly source, not a dedicated volcanic activity feed. Ordinary fires and other hot surfaces may generate detections. Geographic association with known volcanoes reduces false positives but does not eliminate them.

### 2.2 Smithsonian Global Volcanism Program: volcano catalogue

**Purpose:** Provide known volcano locations and contextual eruption information.

Official resources:

- Web services documentation: https://volcano.si.edu/database/webservices.cfm
- WFS capabilities: https://webservices.volcano.si.edu/geoserver/GVP-VOTW/wfs?request=GetCapabilities
- Weekly reports and feeds: https://volcano.si.edu/reports_weekly.cfm?vtab=feeds
- Current eruptions: https://volcano.si.edu/gvp_currenteruptions.cfm

The Global Volcanism Program provides a volcano database through an OGC Web Feature Service. Inspect the available layers, fields, formats, and terms before selecting the implementation.

**Requirements:**

1. Retrieve volcano names and geographic coordinates from an appropriate catalogue layer.
2. Cache the catalogue locally or in the recipe backend rather than downloading it on every display refresh.
3. Use the catalogue to associate thermal detections with known volcanoes.
4. Where practical, ingest recent weekly activity reports as supplementary evidence.
5. Preserve source attribution and comply with the source's applicable terms.

The weekly report should not be treated as a comprehensive record of every volcanic event. It is a curated source of noteworthy activity and changes.

### 2.3 USGS: optional corroborating notices

**Purpose:** Add official evidence of noteworthy volcanic activity, particularly for US volcanoes.

Official resources:

- Hazard Notification System API: https://volcanoes.usgs.gov/vsc/api/hansApi/
- Volcanic aviation notices: https://volcanoes.usgs.gov/vsc/api/hansApi/vonas
- API documentation: https://volcanoes.usgs.gov/vsc/api/

The USGS provides public endpoints for volcanic notices and related information.

**Requirements:**

1. Investigate the available notice types and response schemas.
2. Where reliable, associate notices with known volcanoes.
3. Use official reports as supplementary context for activity that thermal observations may not capture.
4. Do not require this source for the initial recipe to function.
5. Handle schema changes and temporary failures gracefully.

Coverage is geographically limited compared with the global thermal feed, and official alert systems differ between jurisdictions.

### 2.4 Future source: seismic activity

The USGS provides public earthquake feeds:

https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php

Seismic information is explicitly out of scope for the first implementation.

Raw earthquake counts must not be treated as a direct measure of volcanic unrest. A future implementation should use volcano-specific monitoring information or suitably interpreted seismic data, with consideration of background seismicity and official observatory assessments.

## 3. Activity model

### 3.1 Objective

Create a relative activity score for each volcano that can be used to determine marker size.

This score is a visualization metric, not an established scientific measurement of eruption magnitude or danger.

### 3.2 Initial inputs

For each known volcano, collect qualifying thermal detections within the selected observation window.

Potential score inputs:

- **Accumulated FRP:** Sum of qualifying FRP measurements over a rolling 24-hour period.
- **Peak FRP:** Highest qualifying individual FRP observation within the period.
- **Recent change:** Change in thermal activity compared with the previous 24-hour period, where sufficient data exists.
- **Detection recency:** Time since the latest qualifying observation.
- **Corroborating evidence:** Recent eruption reports or official notices, if available.

Start with accumulated FRP and peak FRP. Add change and corroborating evidence only if the data supports a clear, testable implementation.

Avoid double-counting adjacent pixels or repeated observations of the same hotspot. Investigate grouping detections by volcano, observation time, and spatial proximity.

Different satellite products may have different detection characteristics. Do not blindly combine measurements from multiple products without checking their comparability.

### 3.3 Score normalization

Convert the chosen thermal activity metric into a bounded marker-size score.

Requirements:

- Define a minimum and maximum marker size.
- Ensure extreme FRP values do not make other volcanoes invisible.
- Prefer a logarithmic or otherwise compressed scale if the observed distribution is highly skewed.
- Handle missing, zero, and anomalous values.
- Document the chosen formula and its limitations.
- Do not assign numerical eruption magnitudes unless the data source explicitly supports them.

The exact formula and thresholds must be calibrated against real observations before release.

### 3.4 Activity thresholds

Do not render every FIRMS detection.

A volcano should qualify for display when it meets a minimum thermal activity threshold or another explicitly defined qualifying condition.

Investigate the following potential conditions:

- Sufficient accumulated or peak FRP.
- Multiple qualifying detections within a suitable time window.
- Corroborating evidence from an official volcanic activity report.

These conditions are candidates for testing, not mandatory alternatives that should automatically be combined.

The implementation should make thresholds configurable so they can be adjusted after inspecting real data.

A detection close to a volcano should not automatically be classified as volcanic. The initial spatial matching radius can be tested around 10 km, but it must be validated against real volcano locations and nearby non-volcanic heat sources. Handle ambiguous matches rather than silently attributing them to the nearest volcano.

## 4. Map rendering and visual behavior

### 4.1 World map

Render a minimalist world map suitable for a TRMNL e-paper screen.

Requirements:

- Use known volcano coordinates.
- Render at most one volcano marker per volcano.
- Ensure markers remain distinguishable in dense volcanic regions.
- Keep labels and secondary information to a minimum in the initial version.
- Optimize the map for the target display's resolution and rendering constraints.
- Use a consistent volcano SVG silhouette.

The visual design should remain independent of the underlying data sources.

### 4.2 Volcano markers

Each qualifying volcano should be represented by a volcano-shaped icon.

**Marker size:** Represents relative observed thermal activity.

**Marker opacity:** Represents the age of the most recent qualifying observation.

**Marker position:** Represents the known geographic location of the volcano, not the location of every satellite detection.

Use a single consistent SVG silhouette scaled to a bounded range. Do not switch between different illustrations to represent activity levels.

Avoid adding decorative smoke or lava effects that could imply an observed eruption when the source only establishes a thermal anomaly.

### 4.3 Fading and expiration

Use the age of the latest qualifying observation to determine marker opacity.

Initial hypothesis:

- Observation age: 0 to 24 hours, fully visible.
- Observation age: 24 to 72 hours, progressively fading.
- Observation age: more than 72 hours, no longer displayed unless newer qualifying evidence exists.

The exact opacity curve can be tuned during prototyping.

These are initial design choices, not claims about how long an eruption lasts.

Important distinction: a fading marker means that recent qualifying observations have become older or are no longer available. It does not mean the volcano has stopped erupting. Satellite observations can be intermittent or obscured by clouds.

If official activity reports are used to keep a marker visible, define their effect on recency separately from thermal observations. Do not allow a report to silently reset the thermal observation timestamp.

### 4.4 Marker limits and overlap

Aim for a readable display with approximately 20 to 30 markers where the data allows.

This is a target, not a hard scientific limit.

If too many volcanoes qualify:

1. Apply the calibrated activity threshold.
2. Aggregate detections and remove duplicates.
3. Adjust the marker scale and placement to improve readability.
4. If necessary, limit displayed markers by a documented ranking of activity scores.

Do not discard strong activity simply because it is geographically inconvenient. If a marker limit is required, retain the highest-scoring candidates and make the limitation clear in the recipe's documentation.

Dense clusters in regions such as Indonesia and the Pacific may require special consideration.

## 5. Update cadence and data processing

### Initial target

Refresh the underlying data approximately once per day.

Faster updates may be supported later, but a frequent screen refresh does not guarantee fresh satellite observations. Actual latency depends on satellite passes and product publication.

### Processing pipeline

Implement the following logical steps:

1. Fetch recent FIRMS VIIRS data.
2. Validate and normalize timestamps, coordinates, and measurements.
3. Retrieve or load the cached volcano catalogue.
4. Associate qualifying detections with known volcanoes.
5. Filter likely non-volcanic detections and ambiguous associations.
6. Group multiple detections by volcano and observation period.
7. Calculate the activity score.
8. Incorporate supplementary official reports where available.
9. Determine marker size, opacity, and eligibility.
10. Render the world map.
11. Cache the processed dataset and the last successful output.

The implementation should avoid unnecessary API calls and should continue displaying the last valid result when a temporary upstream failure occurs.

Distinguish between an empty result and a failed request. A failed request must not cause all markers to disappear or incorrectly age as though a successful observation confirmed inactivity.

## 6. Technical and operational requirements

- Use a server-side component or suitable recipe backend for API requests and processing.
- Store API credentials securely.
- Do not expose NASA FIRMS credentials in public repositories, generated SVGs, or browser-visible requests.
- Use reasonable request timeouts and retries.
- Validate upstream response schemas.
- Handle missing measurements and malformed records.
- Cache static volcano data separately from dynamic observations.
- Record data timestamps so freshness can be inspected during development.
- Keep data acquisition and activity scoring separate from rendering.
- Make source integrations modular so USGS notices and future seismic sources can be added without rewriting the map.
- Document source attribution, data limitations, API requirements, and any applicable licensing or usage terms.

The final implementation must follow the actual TRMNL recipe runtime, supported data-fetching mechanisms, scheduling constraints, and rendering capabilities. These should be verified against the existing recipe environment before choosing specific libraries or deployment infrastructure.

## 7. Configuration and future extensibility

Keep the following parameters configurable where practical:

- Observation window, initially 72 hours.
- Minimum thermal activity threshold.
- Spatial association radius.
- Activity score formula.
- Minimum and maximum icon size.
- Opacity and fading curve.
- Expiration window.
- Maximum displayed marker count.
- Data refresh interval.

Do not build a complicated settings interface for the first version unless the existing recipe framework makes it straightforward. Sensible defaults are sufficient for the initial prototype.

### Future extensions, out of scope for the first release

1. Official alert-level markers for selected volcanoes.
2. USGS and other observatory notices.
3. Volcano-specific seismic unrest.
4. Ground deformation and gas measurements where accessible.
5. Separate views optimized for larger TRMNL X displays.
6. Additional satellite products, after validating their measurements and coverage.
7. Optional per-volcano details, such as the latest report and observed thermal activity.

Additional signals must retain their distinct meanings. Thermal intensity, seismic unrest, official alert level, and eruption magnitude must not be presented as interchangeable measurements.

## 8. Prototype validation

Before finalizing the visual design, build a small data-processing prototype using real observations.

The prototype should:

1. Fetch the previous 72 hours of FIRMS VIIRS data.
2. Associate detections with the Smithsonian volcano catalogue.
3. Produce a list of matched volcanoes with their names, coordinates, detection counts, peak FRP, accumulated FRP, and latest observation time.
4. Identify ambiguous matches and obvious non-volcanic detections.
5. Calculate a preliminary activity score.
6. Test different thresholds and generate a count of qualifying volcanoes.
7. Render a preliminary world map using scaled markers and age-based opacity.

Test the output against a few known volcanic regions and periods with reported activity. Include cases with continuing eruptions, weaker thermal signals, clustered volcanoes, and no recent qualifying detections.

The prototype should establish whether the activity thresholds and fading behavior produce a useful, legible map before the full recipe is implemented.

### Acceptance criteria

The first version is ready for release when:

- The map is generated from real, publicly available data.
- Volcano markers correspond to known volcano locations.
- Multiple detections associated with one volcano produce one marker.
- Marker size is determined by a documented, bounded activity score.
- Marker opacity reflects the age of the latest qualifying thermal observation.
- Old observations expire according to the configured policy.
- Non-qualifying detections are excluded.
- Missing or failed upstream requests do not cause misleading disappearance of existing data.
- Credentials are protected.
- The map remains readable at the target TRMNL resolution.
- Source attribution and data limitations are documented.

## 9. Explicit non-goals

The initial recipe is not intended to:

- Predict volcanic eruptions.
- Measure eruption magnitude using satellite FRP.
- Estimate volcanic danger or risk from thermal detections alone.
- Display every active volcano regardless of recent activity.
- Interpret raw global earthquake counts as volcanic unrest.
- Claim that an absence of satellite detections means a volcano is inactive.
- Provide a complete or authoritative real-time account of global volcanic activity.

## 10. Deliverables

The implementing agent should provide:

1. A working TRMNL recipe prototype.
2. A reusable data-fetching and processing module.
3. A documented activity score and filtering strategy.
4. A preliminary world map with volcano markers sized by activity and faded by recency.
5. A concise report describing the selected API endpoints, required credentials, data freshness, filtering thresholds, known limitations, and results of prototype validation.
6. A list of recommended adjustments based on real data.

**Implementation priority:** Validate the data and scoring model first. Optimize the map and icon design second. Add observatory alerts and other activity signals only after the thermal-first implementation produces reliable, readable results.
