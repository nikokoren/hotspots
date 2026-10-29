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
    assert 'id="hs-world" class="hs-map" data-map-slot="map-water"' in html
    assert ('class="hs-strip" data-map-slot="map-land" style="left: -44.444%; '
            '--hs-mask: url(data:image/png;base64,iVBOR') in html
    assert html.count('class="hs-v hs-v--') == 2
    assert 'HSMap.labelWorld("hs-world"' in html                       # labels on, placed in the browser
    assert "Liquid" not in html and "{{" not in html and "{%" not in html


def test_closeup_uses_framework_map(site):
    html = preview.render(site, "full", "europe", labels=False, device="og_png")
    body = html.split("</style>")[1]
    assert 'id="hs-closeup" class="map' in body and "hs-strip" not in body
    assert "maplibre-gl/5.24.0/maplibre-gl.js" in body and 'tiles: "trmnl"' in body
    assert "bbox: [-26, 27, 42, 67]," in body
    assert "showLabels: false," in body
    assert '"n": "Kilauea"' in body and '"n": "Etna"' in body  # all markers; the browser filters
    assert "window.onload" not in body and "async function" not in body  # TRMNL lint rules


def test_world_view_offers_framework_map_without_list(site):
    body = preview.render(site, "full", "world-europe", labels=False, device="v2").split("</style>")[1]
    assert 'HSMap.start("hs-native"' in body and "world: true" in body       # TRMNL X: framework map
    assert "hs-strip" in body                                                 # our map otherwise
    assert '<div class="item">' not in body                                   # list is off by default


def test_volcano_list_setting(site):
    body = preview.render(site, "full", "world-europe", labels=False, device="v2",
                          show_list=True).split("</style>")[1]
    assert 'id="hs-native" class="map stretch w--full rounded--base hidden">' in body  # list keeps our map
    assert body.count('<div class="item">') == 2 and 'data-overflow-counter="true"' in body
    assert 'data-overflow-max-cols="1" data-overflow-max-cols-md="3" data-overflow-max-cols-md-portrait="2" data-overflow-max-cols-lg="4" data-overflow-max-cols-lg-portrait="3"' in body
    assert '<span class="label label--small label--outline no-shrink">heat only</span>' in body
    assert body.index(">Kilauea<") < body.index(">Etna<")                     # newest first


def test_about_field_has_categories():
    settings = (SCRIPT.parents[2] / "trmnl" / "src" / "settings.yml").read_text()
    about = settings.split("field_type: author_bio", 1)[1].split("\n- keyname:", 1)[0]
    assert "\n  category: nature,environment\n" in about   # at most two, from trmnl.com/api/categories


def test_closeup_volcano_list_shows_only_its_region(site):
    body = preview.render(site, "full", "europe", labels=False, device="v2", show_list=True).split("</style>", 1)[1]
    assert 'id="hs-closeup" class="map grow basis--0' in body                 # map shares the space
    assert body.count('<div class="item">') == 1 and ">Etna<" in body and ">Kilauea<" not in body
    body = preview.render(site, "full", "europe", labels=False, device="v2").split("</style>", 1)[1]
    assert '<div class="item">' not in body                                     # list off by default


def test_title_bar_setting_off_by_default(site):
    assert 'class="title_bar"' not in preview.render(site, "full", "world-europe", labels=False, device="og_png")
    assert 'class="title_bar"' in preview.render(site, "full", "world-europe", labels=False, device="og_png",
                                                 title_bar=True)


def test_unset_region_falls_back_to_europe_world(site):
    html = preview.render(site, "full", "", labels=False, device="og_png")
    assert 'data-map-slot="map-land" style="left: -4.167%;' in html


def test_payload_under_trmnl_limit(site):
    assert len((site / "latest.json").read_bytes()) < preview.MAX_PAYLOAD_KB * 1024
    payload = json.loads((site / "latest.json").read_text())
    assert set(payload["views"]) >= {"world-europe", "world-pacific", "europe"}
    assert payload["default_view"] == "world-europe"
    assert not (site / "masks" / "world-europe.png").exists()  # world views use the embedded image


def test_embedded_world_map_matches_build_script():
    """The template's world image is the one build_world_map.py produces (no stray placeholder)."""
    import base64
    import re
    shared = (SCRIPT.parents[2] / "trmnl" / "src" / "shared.liquid").read_text()
    embedded = base64.b64decode(re.search(r"world_mask = '([^']+)'", shared).group(1))
    assert embedded == (SCRIPT.parents[2] / "trmnl" / "assets" / "world.png").read_bytes()
    assert embedded[16:24] == (2048).to_bytes(4, "big") + (1024).to_bytes(4, "big")


def test_world_and_closeup_use_the_native_map_colours():
    """Both map kinds take land and water from the framework map slots, never fixed greys."""
    shared = (SCRIPT.parents[2] / "trmnl" / "src" / "shared.liquid").read_text()
    assert 'data-map-slot="map-water"' in shared and 'data-map-slot="map-land"' in shared   # world
    assert "TRMNLMaps.applySwatches" in shared
    assert 'preset: "outline"' in shared and "l.paint =" not in shared   # close-up: preset paint kept
    assert "style.layers.filter" not in shared                                    # preset paint unmodified
    assert 'preset: "outline", tiles: "trmnl", labels: false,' in shared        # no place names under our labels
    assert "bg--gray-70" not in shared


def test_world_mask_is_opaque_land_transparent_ocean():
    png = (SCRIPT.parents[2] / "trmnl" / "assets" / "world.png").read_bytes()
    i = png.index(b"tRNS")
    assert png[i + 4:i + 6] == bytes([0, 255])  # index 0 (ocean) transparent, 1 (land) opaque
