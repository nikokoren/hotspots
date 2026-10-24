from hotspots.models import Marker
from hotspots.render.layout import marker_list, shade_class, view_markers
from hotspots.render.views import VIEWS, VIEWS_BY_KEY, Frame, world_shift_pct

SHADES = ["bg--gray-20", "bg--gray-30", "bg--gray-40", "bg--gray-50"]


def _marker(name, lat, lon, size=0.5, step=0, age=1.0):
    return Marker(name, name, lat, lon, size=size, fade_step=step, age_hours=age)


def test_world_frame_wraps_around_centre():
    f = Frame(VIEWS_BY_KEY["world-pacific"])  # centred on 160°E
    u, v = f.uv(160, 0)
    assert abs(u - 0.5) < 1e-9 and abs(v - 0.5) < 1e-9
    assert f.uv(-20.0001, 0)[0] > 0.99 and f.uv(-19.999, 0)[0] < 0.01  # seam at 20°W


def test_world_shift_matches_marker_positions():
    """The tiled world image slid left by `shift` must put every longitude where Frame.uv puts markers."""
    for view in VIEWS:
        if not view.is_world:
            continue
        shift, f = world_shift_pct(view) / 100, Frame(view)
        for lon in (-170, -80, 0, 15, 110, 179):
            image_x = (lon + 180) / 360            # position in one copy of the -180..180 image
            screen = (image_x - shift) % 1.0       # after sliding the two-copy strip left by shift
            assert abs(screen - f.uv(lon, 0)[0]) < 1e-4, (view.key, lon)  # shift is rounded to 0.001%


def test_default_view_is_europe_centred_world():
    from hotspots.render.views import DEFAULT_VIEW
    assert DEFAULT_VIEW == "world-europe" and VIEWS_BY_KEY[DEFAULT_VIEW].is_world


def test_closeup_boxes_are_sane():
    for view in VIEWS:
        if view.is_world:
            continue
        assert view.lon_min < view.lon_max and view.lat_min < view.lat_max, view.key
        assert view.lon_max - view.lon_min < 180, view.key


def test_view_markers_filter_limit_and_order():
    markers = [_marker("Etna", 37.75, 15.0, 0.2), _marker("Kilauea", 19.4, -155.3, 0.8),
               _marker("Stromboli", 38.79, 15.21, 0.5)]
    world = view_markers(markers, VIEWS_BY_KEY["world-pacific"], min_pct=1, max_pct=5,
                         max_markers=2, shades=SHADES)
    assert len(world) == 2 and world[0]["w"] >= world[1]["w"]


def test_marker_list_for_closeups():
    from dataclasses import replace
    markers = [replace(_marker("Etna", 37.75, 15.0, 0.25, step=2), country="Italy", seen=1792756800),
               _marker("Kilauea", 19.4, -155.3, 1.0)]
    out = marker_list(markers, min_pct=1, max_pct=5, max_markers=1, shades=SHADES)
    assert out == [{"n": "Etna", "lat": 37.75, "lon": 15.0, "w": 2.0, "c": "bg--gray-30", "a": 1.0, "k": "lava",
                    "co": "Italy", "s": 1792756800}]


def test_icon_kind_follows_official_eruption_flag():
    from dataclasses import replace
    from hotspots.render.layout import icon_box, icon_kind
    m = _marker("Etna", 37.75, 15.0)
    assert icon_kind(m) == "lava" and icon_kind(replace(m, erupting=True)) == "erupt"
    lava, erupt = icon_box(50, 25, 4, "lava"), icon_box(50, 25, 4, "erupt")
    assert lava[1] > erupt[1] and lava[3] == erupt[3]  # plume extends upward only
    assert lava[1] < 25 < lava[3]                       # anchor inside the cone


def test_shade_classes():
    assert shade_class(0, SHADES) == "bg--black"
    assert shade_class(1, SHADES) == "bg--gray-20"
    assert shade_class(4, SHADES) == "bg--gray-50"
