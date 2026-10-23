from datetime import datetime, timedelta, timezone

import pytest

from hotspots.config import load_config
from hotspots.models import Detection, Volcano

AS_OF = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def cfg():
    return load_config()


@pytest.fixture
def as_of():
    return AS_OF


def det(lat, lon, hours_ago, frp=10.0, conf="nominal", sat="N"):
    return Detection(lat=lat, lon=lon, acquired_at=AS_OF - timedelta(hours=hours_ago), frp_mw=frp,
                     confidence=conf, brightness_k=330.0, satellite=sat)


def volcano(vid, name, lat, lon, year=2026):
    return Volcano(volcano_id=vid, name=name, lat=lat, lon=lon, last_eruption_year=year)
