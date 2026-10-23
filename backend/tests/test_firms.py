import pytest

from hotspots import http
from hotspots.sources import firms

HEADER = "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,confidence,version,bright_ti5,frp,daynight\n"


def test_parse_valid_and_malformed_rows():
    text = HEADER + (
        "19.40,-155.28,367.0,0.4,0.4,2026-10-22,2350,N,nominal,2.0NRT,300.0,25.5,N\n"
        "bad,-155.28,367.0,0.4,0.4,2026-10-22,2350,N,nominal,2.0NRT,300.0,25.5,N\n"
        "95.0,0,367.0,0.4,0.4,2026-10-22,2350,N,nominal,2.0NRT,300.0,25.5,N\n"
        "19.40,-155.28,367.0,0.4,0.4,2026-10-22,45,N,high,2.0NRT,300.0,,D\n"
    )
    dets, skipped = firms.parse_csv(text)
    assert skipped == 2
    assert len(dets) == 2
    assert dets[0].frp_mw == 25.5 and dets[0].acquired_at.hour == 23
    assert dets[1].frp_mw is None and dets[1].acquired_at.minute == 45


def test_empty_response_is_empty_not_error():
    assert firms.parse_csv("") == ([], 0)
    assert firms.parse_csv(HEADER) == ([], 0)


def test_unexpected_schema_raises():
    with pytest.raises(ValueError):
        firms.parse_csv("Invalid MAP_KEY.\n")


def test_confidence_ranking():
    dets, _ = firms.parse_csv(HEADER + "1,1,1,1,1,2026-10-22,0000,N,low,x,1,1,N\n")
    assert not firms.meets_confidence(dets[0], "nominal")
    assert firms.meets_confidence(dets[0], "low")


def test_map_key_is_redacted():
    url = firms.API_URL.format(key="SECRET123", product="VIIRS_SNPP_NRT", days=5)
    assert "SECRET123" not in http.redact(url)
