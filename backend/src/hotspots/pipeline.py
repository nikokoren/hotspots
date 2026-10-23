"""Processing pipeline (spec §5).

1. Fetch recent FIRMS VIIRS data.
2. Validate and normalize timestamps, coordinates and measurements.
3. Retrieve or load the cached volcano catalogue.
4. Associate qualifying detections with known volcanoes.
5. Filter likely non-volcanic detections and ambiguous associations.
6. Group detections by volcano and observation period.
7. Calculate the activity score.
8. Incorporate supplementary official reports where available.
9. Determine marker size, opacity and eligibility.
10. Render the world map.
11. Cache the processed dataset and last successful output.

A failed upstream request must fall back to the last good result rather than
emptying or prematurely ageing the map.
"""

from __future__ import annotations


def run(config: dict):
    raise NotImplementedError
