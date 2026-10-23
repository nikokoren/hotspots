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
    assert 'class="hs-map' in html and "masks/world-pacific.png" in html
    assert html.count('class="hs-v"') == 2
    assert ">Kilauea<" in html  # labels on
    assert "Liquid" not in html and "{{" not in html and "{%" not in html


def test_labels_off_and_region_switch(site):
    html = preview.render(site, "full", "europe", labels=False, device="og_png")
    assert html.count('class="hs-v"') == 1  # Etna only
    assert "<span class=\"hs-l " not in html


def test_payload_under_trmnl_limit(site):
    assert len((site / "latest.json").read_bytes()) < preview.MAX_PAYLOAD_KB * 1024
    payload = json.loads((site / "latest.json").read_text())
    assert set(payload["views"]) >= {"world-pacific", "europe"}
