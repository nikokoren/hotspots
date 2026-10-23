"""Render the TRMNL Liquid templates against a generated site (python-liquid stand-in for trmnlp)."""

import importlib.util
import json
from pathlib import Path

import pytest

from conftest import AS_OF, det, volcano
from hotspots.pipeline import process, write_site

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "preview.py"
spec = importlib.util.spec_from_file_location("preview", SCRIPT)
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    from hotspots.config import load_config
    cfg = load_config()
    vols = [volcano("1", "Kilauea", 19.42, -155.29), volcano("2", "Etna", 37.75, 15.0)]
    dets = [det(19.42, -155.28, 3, 200), det(19.42, -155.28, 15, 50), det(37.75, 15.0, 40, 30), det(37.75, 15.0, 52, 30)]
    markers, acts, stats = process(dets, vols, cfg, AS_OF)
    out = tmp_path_factory.mktemp("site")
    write_site(out, cfg, markers, acts, stats, AS_OF, AS_OF, {"product": "VIIRS_SNPP_NRT"}, {})
    return out


@pytest.mark.parametrize("layout", ["full", "half_horizontal", "half_vertical", "quadrant"])
def test_layouts_render(site, layout):
    html = preview.render(site, layout, "world-pacific", labels=True, device="og_png")
    assert 'class="hs-map' in html and 'class="hs-strip" style="left: -44.444%;"' in html
    assert html.count("data:image/png;base64,iVBOR") == 2  # tiled world image
    assert html.count('class="hs-v"') == 2
    assert ">Kilauea<" in html  # labels on
    assert "Liquid" not in html and "{{" not in html and "{%" not in html


def test_closeup_uses_framework_map(site):
    html = preview.render(site, "full", "europe", labels=False, device="og_png")
    body = html.split("</style>")[1]
    assert 'id="hs-closeup" class="map' in body and "hs-strip" not in body
    assert "maplibre-gl/5.24.0/maplibre-gl.js" in body and 'tiles: "trmnl"' in body
    assert "var bbox = [-26, 27, 42, 67];" in body
    assert 'var showLabels = false;' in body
    assert '"n": "Kilauea"' in body and '"n": "Etna"' in body  # all markers; the browser filters
    assert "window.onload" not in body and "async function" not in body  # TRMNL lint rules


def test_unset_region_falls_back_to_europe_world(site):
    html = preview.render(site, "full", "", labels=False, device="og_png")
    assert 'class="hs-strip" style="left: -4.167%;"' in html


def test_payload_under_trmnl_limit(site):
    assert len((site / "latest.json").read_bytes()) < preview.MAX_PAYLOAD_KB * 1024
    payload = json.loads((site / "latest.json").read_text())
    assert set(payload["views"]) >= {"world-europe", "world-pacific", "europe"}
    assert payload["default_view"] == "world-europe"
    assert not (site / "masks" / "world-europe.png").exists()  # world views use the embedded image
