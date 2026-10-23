from datetime import datetime, timezone

from hotspots.sources.gvp import parse_continuing

AS_OF = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)


def _feat(num, continuing, end):
    return {"properties": {"VolcanoNumber": num, "ContinuingEruption": continuing, "EndDate": end}}


def test_continuing_eruption_needs_recent_recorded_activity():
    data = {"features": [
        _feat(1, "True", "20261020"),   # recent
        _feat(2, "True", "20260725"),   # exactly 90 days
        _feat(3, "True", "20260318"),   # stale: database not updated since March
        _feat(4, "True", None),         # no activity date
        _feat(5, "False", "20261020"),  # ended
    ]}
    ids, stale = parse_continuing(data, AS_OF, 90)
    assert ids == {"1", "2"}
    assert stale == 2


def test_manual_list_matches_report_lines_to_catalogue():
    from hotspots.models import Volcano
    from hotspots.sources.manual import parse
    cat = [Volcano("1", "Dukono", 1.7, 127.9), Volcano("2", "Ruiz, Nevado del", 4.9, -75.3),
           Volcano("3", "Kilauea", 19.4, -155.3), Volcano("4", "Poás", 10.2, -84.2),
           Volcano("5", "San Jose", 0, 0), Volcano("6", "San Jose", 1, 1)]
    text = """# comment
Dukono, Halmahera (Indonesia)
Nevado del Ruiz (Colombia)
KILAUEA
Poas
San Jose
Atlantis
"""
    out = parse(text, cat)
    assert out.ids == {"1", "2", "3", "4", "5", "6"}
    assert out.unmatched == ["Atlantis"]
    assert out.ambiguous == {"San Jose": ["5", "6"]}


def test_manual_list_ignored_when_stale(tmp_path):
    from datetime import timedelta

    from hotspots import pipeline
    from hotspots.models import Volcano
    f = tmp_path / "eruptions.txt"
    f.write_text("Dukono\n")
    cat = [Volcano("1", "Dukono", 1.7, 127.9)]
    updated = pipeline.manual.last_updated(f)
    ids, meta = pipeline.load_manual_eruptions(f, cat, updated + timedelta(days=3), 14, log=lambda m: None)
    assert ids == {"1"} and meta["used"]
    ids, meta = pipeline.load_manual_eruptions(f, cat, updated + timedelta(days=15), 14, log=lambda m: None)
    assert ids == set() and meta["reason"] == "stale"
