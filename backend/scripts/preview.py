"""Render the recipe's Liquid locally into a TRMNL-like HTML page.

A stand-in for trmnlp (which needs Ruby 4 or Docker): renders shared.liquid +
a layout with python-liquid, using TRMNL's real framework CSS/JS and the same
page wrapper as trmnlp, against a site built by `hotspots run`.

    hotspots run --out site
    python scripts/preview.py site --layout full --region europe --labels --list --device og_png > preview.html

Open the HTML over http:// (not file://) so the framework's module script, fonts
and the close-up map tiles load from trmnl.com, e.g. `python -m http.server`.
TRMNL's {% template %} tag is emulated by registering each block as a partial.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from liquid import DictLoader, Environment

SRC = Path(__file__).resolve().parents[2] / "trmnl" / "src"
TEMPLATE_BLOCK = re.compile(r"{%-?\s*template\s+(\w+)\s*-?%}(.*?){%-?\s*endtemplate\s*-?%}", re.S)
MASHUP = {"full": None, "half_horizontal": "mashup mashup--1Tx1B",
          "half_vertical": "mashup mashup--1Lx1R", "quadrant": "mashup mashup--2x2"}
DEVICES = {  # screen classes as trmnlp derives them from https://trmnl.com/api/models
    "og_png": ("screen screen--1bit screen--og_png screen--md", 800, 480, 1),
    "og_plus": ("screen screen--2bit screen--ogv2 screen--md", 800, 480, 1),
    "v2": ("screen screen--4bit screen--v2 screen--lg", 1040, 780, 1.8),
}
CSS = "https://trmnl.com/css/latest/plugins.css"
JS = "https://trmnl.com/js/latest/plugins.js"
MAX_PAYLOAD_KB = 100  # TRMNL's merge-variable limit


def render(site: Path, layout: str, region: str, labels: bool, device: str,
           css: str = CSS, js: str = JS, site_url: str | None = None, show_list: bool = False) -> str:
    shared = (SRC / "shared.liquid").read_text()
    partials = {name: body for name, body in TEMPLATE_BLOCK.findall(shared)}
    markup = TEMPLATE_BLOCK.sub("", shared) + (SRC / f"{layout}.liquid").read_text()

    payload = json.loads((site / "latest.json").read_text())
    size_kb = len(json.dumps(payload, separators=(",", ":")).encode()) / 1024
    if size_kb > MAX_PAYLOAD_KB:
        print(f"warning: payload {size_kb:.1f} KB exceeds TRMNL's {MAX_PAYLOAD_KB} KB limit", file=sys.stderr)
    payload["site_url"] = site_url or site.resolve().as_uri()
    values = {"labels": labels, "list": show_list}
    if region:
        values["region"] = region
    payload["trmnl"] = {"plugin_settings": {"custom_fields_values": values}}

    env = Environment(loader=DictLoader(partials))
    env.filters["json"] = lambda value: json.dumps(value)  # TRMNL Liquid's json filter
    body = env.from_string(markup).render(**payload)

    screen, *_ = DEVICES[device]
    mashup = MASHUP[layout]
    view = f'<div class="view view--{layout}">{body}</div>'
    if mashup:
        view = f'<div class="{mashup}">{view}</div>'
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8" /><link rel="stylesheet" href="{css}" />'
            f'<script type="module" src="{js}"></script></head>'
            f'<body class="environment trmnl"><div class="{screen} screen--fonts-trmnl">{view}</div></body></html>')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("site", type=Path)
    ap.add_argument("--layout", default="full", choices=list(MASHUP))
    ap.add_argument("--region", default="world-europe")
    ap.add_argument("--labels", action="store_true")
    ap.add_argument("--list", action="store_true", help="volcano list setting on")
    ap.add_argument("--device", default="og_png", choices=list(DEVICES))
    ap.add_argument("--css", default=CSS)
    ap.add_argument("--js", default=JS)
    args = ap.parse_args()
    print(render(args.site, args.layout, args.region, args.labels, args.device, args.css, args.js,
                 show_list=args.list))


if __name__ == "__main__":
    main()
