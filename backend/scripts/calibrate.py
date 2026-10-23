"""Threshold sweep over a local FIRMS CSV (spec §8.6).

    python scripts/calibrate.py SUOMI_VIIRS_C2_Global_7d.csv --as-of 2026-10-23T12:00Z

Prints the number of qualifying volcanoes for each parameter variation, and
the volcanoes gained/lost against the defaults.
"""

import argparse
import copy
from datetime import datetime, timezone
from pathlib import Path

from hotspots.cache import load_catalogue
from hotspots.config import data_dir, load_config
from hotspots.pipeline import process
from hotspots.sources import firms

VARIATIONS = [
    ("defaults", {}),
    ("radius 5 km", {"association.radius_km": 5.0, "qualify.max_distance_km": 5.0}),
    ("radius 20 km", {"association.radius_km": 20.0, "qualify.max_distance_km": 20.0}),
    ("confidence low", {"firms.min_confidence": "low"}),
    ("confidence high", {"firms.min_confidence": "high"}),
    ("eruption ≤ 5 y", {"qualify.max_years_since_eruption": 5}),
    ("eruption ≤ 25 y", {"qualify.max_years_since_eruption": 25}),
    ("no eruption prior", {"qualify.max_years_since_eruption": None}),
    ("peak ≥ 5 MW", {"qualify.min_peak_overpass_frp_mw": 5.0}),
    ("≥ 2 overpasses", {"qualify.min_overpasses": 2}),
    ("no isolation rule", {"qualify.isolated_max_distance_km": 99.0}),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path)
    ap.add_argument("--as-of", required=True)
    args = ap.parse_args()
    as_of = datetime.fromisoformat(args.as_of.replace("Z", "+00:00")).astimezone(timezone.utc)
    base = load_config()
    detections, _ = firms.parse_csv(args.csv.read_text())
    volcanoes, _ = load_catalogue(data_dir() / "catalogue.json", None, base["catalogue"]["refresh_days"])

    baseline = None
    for label, overrides in VARIATIONS:
        cfg = copy.deepcopy(base)
        for key, value in overrides.items():
            section, name = key.split(".")
            cfg[section][name] = value
        markers, acts, stats = process(detections, volcanoes, cfg, as_of)
        names = {m.name for m in markers}
        if baseline is None:
            baseline = names
        gained, lost = sorted(names - baseline), sorted(baseline - names)
        print(f"{label:20s} candidates={stats['candidate_volcanoes']:3d} markers={len(markers):3d}"
              + (f"  +{gained}" if gained else "") + (f"  -{lost}" if lost else ""))


if __name__ == "__main__":
    main()
