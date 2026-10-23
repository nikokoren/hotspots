import struct
import zlib

from hotspots.models import Marker
from hotspots.render.layout import shade_class, view_markers
from hotspots.render.mask import encode_png, rasterize
from hotspots.render.views import VIEWS, VIEWS_BY_KEY, Frame

SHADES = ["bg--gray-20", "bg--gray-30", "bg--gray-40", "bg--gray-50"]


def _marker(name, lat, lon, size=0.5, step=0, age=1.0):
    return Marker(name, name, lat, lon, size=size, fade_step=step, age_hours=age)


def test_world_frame_wraps_around_centre():
    f = Frame(VIEWS_BY_KEY["world-pacific"])  # centred on 150°E
    u, v = f.uv(150, 0)
    assert abs(u - 0.5) < 1e-9 and abs(v - 0.5) < 1e-9
    assert f.uv(-30.0001, 0)[0] > 0.99 and f.uv(-29.999, 0)[0] < 0.01  # seam at 30°W


def test_regional_frames_are_two_to_one_and_contain_their_box():
    for view in VIEWS:
        f = Frame(view)
        assert abs(f.width / f.height - 2) < 1e-9
        for lon, lat in ((view.lon_min, view.lat_min), (view.lon_max, view.lat_max)):
            u, v = f.uv(lon, lat)
            assert -1e-9 <= u <= 1 + 1e-9 and -1e-9 <= v <= 1 + 1e-9, view.key


def test_antimeridian_region():
    f = Frame(VIEWS_BY_KEY["southwest-pacific"])
    assert f.contains(*f.uv(-175.4, -21.1))  # Tonga
    assert f.contains(*f.uv(148.4, -5.5))    # New Britain
    assert not f.contains(*f.uv(15.0, 37.7))


def test_mask_marks_land_and_ocean():
    rows = rasterize(VIEWS_BY_KEY["world-atlantic"], 360, 180)
    f = Frame(VIEWS_BY_KEY["world-atlantic"])

    def at(lon, lat):
        u, v = f.uv(lon, lat)
        return rows[min(179, int(v * 180))][min(359, int(u * 360))]

    assert at(20, 5) == 1        # central Africa
    assert at(-30, 0) == 0       # mid-Atlantic
    assert at(-155, 10) == 0     # Pacific
    assert at(0, -85) == 1       # Antarctica interior
    assert at(-40, -60) == 0     # Southern Ocean (pole closure must not flood it)


def test_png_is_valid_palette_with_transparency():
    png = encode_png([bytearray([0, 1, 0]), bytearray([1, 1, 0])])
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    w, h, depth, ctype = struct.unpack(">IIBB", png[16:26])
    assert (w, h, depth, ctype) == (3, 2, 8, 3)
    idat = png.index(b"IDAT")
    length = struct.unpack(">I", png[idat - 4:idat])[0]
    assert zlib.decompress(png[idat + 4:idat + 4 + length]) == b"\x00\x00\x01\x00\x00\x01\x01\x00"
    assert b"tRNS" in png


def test_view_markers_filter_limit_and_order():
    markers = [_marker("Etna", 37.75, 15.0, 0.2), _marker("Kilauea", 19.4, -155.3, 0.8),
               _marker("Stromboli", 38.79, 15.21, 0.5)]
    europe = view_markers(markers, VIEWS_BY_KEY["europe"], min_pct=1, max_pct=5,
                          max_markers=30, max_labels=5, shades=SHADES)
    assert [e["n"] for e in europe] == ["Stromboli", "Etna"]  # Kilauea outside; largest drawn first
    assert europe[0]["w"] == 3.0
    world = view_markers(markers, VIEWS_BY_KEY["world-pacific"], min_pct=1, max_pct=5,
                         max_markers=2, max_labels=0, shades=SHADES)
    assert len(world) == 2 and all(e["l"] == "" for e in world)


def test_labels_do_not_overlap_and_respect_limit():
    markers = [_marker(f"V{i}", 0.0, 100.0 + i * 0.2, 0.5, age=i) for i in range(6)]
    out = view_markers(markers, VIEWS_BY_KEY["southeast-asia"], min_pct=1, max_pct=5,
                       max_markers=30, max_labels=3, shades=SHADES)
    labelled = [e for e in out if e["l"]]
    assert 1 <= len(labelled) <= 3
    assert labelled[0]["a"] == min(e["a"] for e in labelled)


def test_shade_classes():
    assert shade_class(0, SHADES) == "bg--black"
    assert shade_class(1, SHADES) == "bg--gray-20"
    assert shade_class(4, SHADES) == "bg--gray-50"
