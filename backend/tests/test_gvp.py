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
