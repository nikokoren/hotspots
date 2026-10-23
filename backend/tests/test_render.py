import xml.etree.ElementTree as ET

from hotspots.models import Marker
from hotspots.render.map import VIEWS, VIEWS_BY_KEY, Frame, render_svg

MARKERS = [Marker(str(i), f"V{i}", -60 + i * 4, -170 + i * 11, size=i / 30, fade_step=i % 3, age_hours=i)
           for i in range(31)]


def test_all_views_render_valid_svg():
    for view in VIEWS:
        for labels in (0, 5):
            ET.fromstring(render_svg(MARKERS, view, labels=labels))


def test_marker_limit_and_labels():
    svg = render_svg(MARKERS, VIEWS_BY_KEY["world-pacific"], max_markers=10, labels=3)
    root = ET.fromstring(svg)
    ns = "{http://www.w3.org/2000/svg}"
    uses = root.findall(f"{ns}use")
    assert len(uses) == 2 * 10  # halo + icon per marker
    assert 1 <= len(root.findall(f"{ns}text")) <= 3


def test_regional_view_excludes_outside_markers():
    europe = VIEWS_BY_KEY["europe"]
    frame = Frame(europe, 800, 480)
    assert frame.contains(*frame.point(15.0, 37.75))      # Etna
    assert not frame.contains(*frame.point(-155.3, 19.4))  # Kilauea


def test_antimeridian_view_places_both_sides():
    sw = VIEWS_BY_KEY["southwest-pacific"]
    frame = Frame(sw, 800, 480)
    assert frame.contains(*frame.point(-175.4, -21.1))  # Tonga (west of 180°)
    assert frame.contains(*frame.point(148.4, -5.5))    # New Britain
