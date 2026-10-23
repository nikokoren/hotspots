"""Build the recipe's world map image from Natural Earth and embed it in the template.

The image is an equirectangular land mask covering -180..180 / 90..-90: opaque
white over the ocean, transparent over land. The recipe lays it on a framework
grey box (so land renders as TRMNL grey on every panel), tiles it twice and
slides it to re-centre the world.

Natural Earth is public domain: https://www.naturalearthdata.com/about/terms-of-use/

    python scripts/build_world_map.py                    # download 50m land, write PNG, embed
    python scripts/build_world_map.py --geojson ne_50m_land.geojson --no-embed
"""

import argparse
import base64
import json
import math
import re
import struct
import urllib.request
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TEMPLATE = REPO / "trmnl" / "src" / "shared.liquid"
NE_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_{scale}_land.geojson"


def load_polygons(geojson: dict) -> list[list[list[tuple[float, float]]]]:
    polygons = []
    for feat in geojson["features"]:
        g = feat["geometry"]
        for poly in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
            polygons.append([[(lon, lat) for lon, lat in ring] for ring in poly])
    return polygons


def rasterize(polygons, width: int, height: int) -> list[bytearray]:
    """Rows of 0 (ocean) / 1 (land). Even-odd scanline fill per polygon (exterior + holes), OR-ed.

    Natural Earth splits polygons at the antimeridian and closes Antarctica along the
    pole, so raw lon/lat needs no unwrapping for a map centred on 0°.
    """
    rows = [bytearray(width) for _ in range(height)]
    for polygon in polygons:
        crossings: dict[int, list[float]] = {}
        for ring in polygon:
            pts = [((lon + 180) / 360 * width, (90 - lat) / 180 * height) for lon, lat in ring]
            for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
                if y1 == y2:
                    continue
                if y1 > y2:
                    x1, y1, x2, y2 = x2, y2, x1, y1
                r0, r1 = max(0, math.ceil(y1 - 0.5)), min(height - 1, math.ceil(y2 - 0.5) - 1)
                slope = (x2 - x1) / (y2 - y1)
                for r in range(r0, r1 + 1):
                    crossings.setdefault(r, []).append(x1 + (r + 0.5 - y1) * slope)
        for r, xs in crossings.items():
            xs.sort()
            for a, b in zip(xs[0::2], xs[1::2]):
                c0, c1 = max(0, math.ceil(a - 0.5)), min(width - 1, math.floor(b - 0.5))
                if c0 <= c1:
                    rows[r][c0:c1 + 1] = b"\x01" * (c1 - c0 + 1)
    return rows


def encode_png(rows: list[bytearray]) -> bytes:
    """1-bit palette PNG: index 0 = opaque white (ocean), 1 = transparent (land)."""
    height, width = len(rows), len(rows[0])

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    packed = bytearray()
    for row in rows:
        packed.append(0)  # filter: none
        bits = int("".join("1" if v else "0" for v in row).ljust((width + 7) // 8 * 8, "0"), 2)
        packed += bits.to_bytes((width + 7) // 8, "big")
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 1, 3, 0, 0, 0))
            + chunk(b"PLTE", bytes([255, 255, 255, 255, 255, 255]))
            + chunk(b"tRNS", bytes([255, 0]))
            + chunk(b"IDAT", zlib.compress(bytes(packed), 9))
            + chunk(b"IEND", b""))


def embed(png: bytes, template: Path = TEMPLATE) -> None:
    text = template.read_text()
    new, n = re.subn(r"(\{% assign world_mask = ')[A-Za-z0-9+/=]*('\s*%\})",
                     lambda m: m.group(1) + base64.b64encode(png).decode() + m.group(2), text)
    if n != 1:
        raise SystemExit(f"expected one world_mask assignment in {template}, found {n}")
    template.write_text(new)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--geojson", type=Path, help="Natural Earth land GeoJSON (default: download)")
    ap.add_argument("--scale", default="50m", choices=["110m", "50m", "10m"])
    ap.add_argument("--width", type=int, default=2048)
    ap.add_argument("--out", type=Path, default=REPO / "trmnl" / "assets" / "world.png")
    ap.add_argument("--no-embed", action="store_true")
    args = ap.parse_args()

    if args.geojson:
        data = json.loads(args.geojson.read_text())
    else:
        with urllib.request.urlopen(NE_URL.format(scale=args.scale), timeout=120) as resp:
            data = json.load(resp)
    png = encode_png(rasterize(load_polygons(data), args.width, args.width // 2))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(png)
    print(f"{args.out}: {args.width}x{args.width // 2}, {len(png)} bytes ({len(png) * 4 // 3} base64)")
    if not args.no_embed:
        embed(png)
        print(f"embedded in {TEMPLATE}")


if __name__ == "__main__":
    main()
