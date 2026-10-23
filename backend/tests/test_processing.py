from conftest import det, volcano

from hotspots.pipeline import process
from hotspots.processing.association import associate, haversine_km
from hotspots.processing.scoring import aggregate, group_overpasses, normalized_size
from hotspots.processing.visual import fade_step

KILAUEA = volcano("332010", "Kilauea", 19.421, -155.287)
OLD = volcano("999", "Dormant", 10.0, 10.0, year=1800)


def test_haversine():
    assert abs(haversine_km(0, 0, 0, 1) - 111.2) < 0.2
    assert haversine_km(0, 179.95, 0, -179.95) < 12  # across the antimeridian


def test_association_radius_and_ambiguity():
    a = volcano("1", "A", 0.0, 0.0)
    b = volcano("2", "B", 0.0, 0.06)  # ~6.7 km east of A
    dets = [det(0.0, 0.03, 1), det(0.0, 0.5, 1)]  # midway; far away
    matched, ambiguous, unmatched = associate(dets, [a, b], radius_km=10, ambiguity_ratio=1.5)
    assert unmatched == 1
    assert sum(len(v) for v in matched.values()) == 1
    assert ambiguous  # equidistant → flagged, not silently resolved


def test_overpass_grouping_sums_pixels_not_passes():
    dets = [det(19.42, -155.28, 1.0, 10), det(19.43, -155.28, 1.0, 5),  # one pass, 2 pixels
            det(19.42, -155.28, 13.0, 8)]                               # another pass
    passes = group_overpasses(dets)
    assert [p.total_frp_mw for p in passes] == [8, 15]
    act = aggregate(KILAUEA, dets, score_window_hours=24)
    assert act.peak_overpass_frp_mw == 15


def test_score_window_anchored_to_latest_detection():
    # Latest detection 50 h ago; a 60 h old strong pass is within 24 h of it and counts.
    dets = [det(19.42, -155.28, 50, 20), det(19.42, -155.28, 60, 100)]
    act = aggregate(KILAUEA, dets, score_window_hours=24)
    assert act.peak_overpass_frp_mw == 100


def test_normalized_size_bounds():
    assert normalized_size(0, 1, 1000) == 0
    assert normalized_size(None, 1, 1000) == 0
    assert normalized_size(1e6, 1, 1000) == 1
    assert 0.3 < normalized_size(10, 1, 1000) < 0.4


def test_fade_steps():
    steps = [24, 48, 72]
    assert [fade_step(h, steps) for h in (0, 24, 30, 72, 72.1)] == [0, 0, 1, 2, None]


def test_process_end_to_end(cfg, as_of):
    dets = [
        det(19.42, -155.28, 3, 200), det(19.425, -155.28, 15, 50),   # Kilauea: 2 passes
        det(10.0, 10.01, 3, 500),                                     # near a dormant volcano → excluded
        det(19.42, -155.28, 80, 999),                                 # outside 72 h window
        det(45.0, 45.0, 3, 50),                                       # unmatched
    ]
    markers, acts, stats = process(dets, [KILAUEA, OLD], cfg, as_of)
    assert [m.name for m in markers] == ["Kilauea"]
    m = markers[0]
    assert m.fade_step == 0 and 0 < m.size < 1
    dormant = next(a for a in acts if a.volcano.name == "Dormant")
    assert "no_recent_eruption" in dormant.flags
    assert stats["detections_unmatched"] == 1


def test_isolated_far_detection_excluded(cfg, as_of):
    v = volcano("1", "V", 0.0, 0.0)
    markers, acts, _ = process([det(0.0, 0.07, 3, 50)], [v], cfg, as_of)  # 1 pass, ~7.8 km
    assert markers == [] and "isolated" in acts[0].flags


def test_expired_marker_dropped(cfg, as_of):
    markers, _, _ = process([det(19.42, -155.28, 70, 50)], [KILAUEA], cfg, as_of)
    assert markers and markers[0].fade_step == 2
    cfg["scoring"]["observation_window_hours"] = 96
    markers, _, _ = process([det(19.42, -155.28, 80, 50)], [KILAUEA], cfg, as_of)
    assert markers == []  # older than last fade step
