"""Convert Natural Earth land GeoJSON into the compact basemap files shipped with the package.

Natural Earth is public domain (https://www.naturalearthdata.com/about/terms-of-use/).

    python scripts/build_basemap.py ne_110m_land.geojson src/hotspots/render/data/land_110m.json
    python scripts/build_basemap.py ne_50m_land.geojson  src/hotspots/render/data/land_50m.json

Source: https://github.com/nvkelso/natural-earth-vector/tree/master/geojson
Output: {"rings": [[lon0, lat0, lon1, lat1, ...], ...]} rounded to 0.01°.
"""

import json
import sys


def main(src: str, dst: str) -> None:
    data = json.load(open(src))
    rings = []
    for feat in data["features"]:
        g = feat["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            for ring in poly:
                flat, prev = [], None
                for lon, lat in ring:
                    pt = (round(lon, 2), round(lat, 2))
                    if pt != prev:
                        flat.extend(pt)
                        prev = pt
                if len(flat) >= 8:
                    rings.append(flat)
    with open(dst, "w") as f:
        json.dump({"source": "Natural Earth (public domain)", "rings": rings}, f, separators=(",", ":"))


if __name__ == "__main__":
    main(*sys.argv[1:3])
